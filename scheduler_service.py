# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Event-Driven Scheduler Service
================================================================
Replaces polling with APScheduler for efficient, event-driven scheduling.

Critical Fixes (v2.0.0):
- REMOVED dangerous log file reading
- Now uses database for hadith cooldown tracking
- Improved error handling
- Better performance

Optimizations:
- No polling loops - schedules jobs once per day
- Event-driven: reschedules only when settings change
- Randomized hadith times to avoid predictable patterns
- Cooldown enforcement between hadiths (database-based)
- Job IDs include group_id for safe removal

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import random
from datetime import datetime, timedelta, time as time_module
from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

import threading
import config
from logger_config import logger
from database import (
    get_all_active_groups,
    get_group,
    get_group_prayer_times,
    has_azan_sent_today,
    log_azan_sent,
    is_content_sent_today,
    mark_content_as_sent,
    get_last_hadith_sent_time,
    get_hadiths_sent_today_count,
    log_hadith_sent
)
from prayer_api import fetch_and_save_prayer_times
from hadith_system import get_cached_hadith
from notification_service import send_azan_notification


# =====================================================
# GLOBAL VARIABLES
# =====================================================

# Global shutdown event (for external modules)
shutdown_event = threading.Event()

# Global bot instance (will be set on startup)
_bot_instance = None


# =====================================================
# SCHEDULER SETUP
# =====================================================

# Configure thread pool for concurrent job execution
executors = {
    'default': ThreadPoolExecutor(max_workers=10)
}

# Memory job store (non-persistent, rebuilds on restart)
jobstores = {
    'default': MemoryJobStore()
}

# Create APScheduler
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    timezone='UTC',
    job_defaults={
        'coalesce': True,  # Combine overlapping jobs
        'max_instances': 1,  # Run only one instance at a time
        'misfire_grace_time': 300  # 5 minutes grace for misfired jobs
    }
)


def set_bot_instance(bot):
    """
    Set bot instance for scheduler jobs to use.
    Must be called before starting scheduler.

    Args:
        bot: TeleBot instance
    """
    global _bot_instance
    _bot_instance = bot
    logger.info("Bot instance set for scheduler")


# =====================================================
# PRAYER SCHEDULING
# =====================================================

def schedule_prayer_notifications_for_group(chat_id: int):
    """
    Schedule all prayer notifications for a group.
    Creates one-time jobs for each prayer that run at exact times.

    Args:
        chat_id: Group chat ID
    """
    # Remove existing jobs for this group
    remove_group_prayer_jobs(chat_id)

    # Get group settings
    group = get_group(chat_id)
    if not group or not group.get('notification_enabled', True):
        logger.debug(f"Skipping prayer scheduling for group {chat_id} (inactive or disabled)")
        return

    # Get prayer times for today (fetch if needed)
    today = datetime.now().strftime('%Y-%m-%d')
    prayer_times_data = get_group_prayer_times(chat_id, today)

    if not prayer_times_data:
        logger.debug(f"No prayer times for group {chat_id}, fetching...")
        fetch_and_save_prayer_times(chat_id)
        prayer_times_data = get_group_prayer_times(chat_id, today)
        if not prayer_times_data:
            logger.error(f"Failed to get prayer times for group {chat_id}")
            return

    # Parse prayer times
    tz_str = group['timezone']
    group_tz = timezone(tz_str)

    prayers = [
        ('fajr', prayer_times_data['fajr_time']),
        ('dhuhr', prayer_times_data['dhuhr_time']),
        ('asr', prayer_times_data['asr_time']),
        ('maghrib', prayer_times_data['maghrib_time']),
        ('isha', prayer_times_data['isha_time'])
    ]

    for prayer_name, prayer_time_str in prayers:
        try:
            # Parse prayer time (HH:MM format)
            hour, minute = map(int, prayer_time_str.split(':'))

            # Create datetime in group's timezone
            prayer_time = datetime.now(group_tz).replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )

            # Convert to UTC for scheduler
            prayer_time_utc = prayer_time.astimezone(timezone('UTC'))

            # Create job ID
            job_id = f"prayer_{chat_id}_{prayer_name}"

            # Schedule one-time job at exact time
            scheduler.add_job(
                send_prayer_notification,
                trigger=DateTrigger(run_date=prayer_time_utc, timezone='UTC'),
                args=[chat_id, prayer_name, prayer_time_str],
                id=job_id,
                name=f"Prayer: {prayer_name} for group {chat_id}",
                replace_existing=True
            )

            logger.debug(f"Scheduled {prayer_name} for group {chat_id} at {prayer_time_str}")

        except Exception as e:
            logger.error(f"Error scheduling {prayer_name} for group {chat_id}: {e}", exc_info=False)


def send_prayer_notification(chat_id: int, prayer_name: str, prayer_time_str: str):
    """
    Send azan notification for a prayer.
    Called by scheduler when prayer time arrives.

    Args:
        chat_id: Group chat ID
        prayer_name: Prayer name (fajr, dhuhr, etc.)
        prayer_time_str: Prayer time string
    """
    try:
        # Get today's date in group's timezone
        group = get_group(chat_id)
        if not group:
            return

        tz_str = group['timezone']
        group_tz = timezone(tz_str)
        today = datetime.now(group_tz).strftime('%Y-%m-%d')

        # Check if already sent today
        if has_azan_sent_today(chat_id, prayer_name, today):
            logger.debug(f"Azan for {prayer_name} already sent to group {chat_id} today")
            return

        # Send notification
        if _bot_instance and send_azan_notification(_bot_instance, chat_id, prayer_name.capitalize(), prayer_time_str):
            # Log as sent
            log_azan_sent(chat_id, prayer_name, today)
            logger.info(f"Sent azan for {prayer_name} to group {chat_id}")

    except Exception as e:
        logger.error(f"Error sending prayer notification: {e}", exc_info=False)


def remove_group_prayer_jobs(chat_id: int):
    """
    Remove all prayer jobs for a group.

    Args:
        chat_id: Group chat ID
    """
    try:
        # Remove jobs with IDs starting with "prayer_{chat_id}_"
        scheduler.remove_job(f"prayer_{chat_id}_fajr")
        scheduler.remove_job(f"prayer_{chat_id}_dhuhr")
        scheduler.remove_job(f"prayer_{chat_id}_asr")
        scheduler.remove_job(f"prayer_{chat_id}_maghrib")
        scheduler.remove_job(f"prayer_{chat_id}_isha")
        logger.debug(f"Removed prayer jobs for group {chat_id}")
    except Exception as e:
        logger.debug(f"No prayer jobs to remove for group {chat_id}: {e}")


# =====================================================
# HADITH SCHEDULING
# =====================================================

def schedule_hadith_for_group(chat_id: int):
    """
    Schedule hadith sending for a group.
    Creates multiple jobs per day with randomized times.

    Args:
        chat_id: Group chat ID
    """
    # Remove existing hadith jobs for this group
    remove_group_hadith_jobs(chat_id)

    # Get group settings
    group = get_group(chat_id)
    if not group:
        return

    tz_str = group['timezone']
    group_tz = timezone(tz_str)

    # Schedule hadiths for each window
    for window in config.HADITH_WINDOWS:
        # Randomize time within window
        random_hour = random.randint(window['start_hour'], window['end_hour'] - 1)
        random_minute = random.randint(0, 59)

        # Create datetime in group's timezone
        hadith_time = datetime.now(group_tz).replace(
            hour=random_hour,
            minute=random_minute,
            second=random.randint(0, 59),  # Random seconds to avoid predictability
            microsecond=0
        )

        # Convert to UTC for scheduler
        hadith_time_utc = hadith_time.astimezone(timezone('UTC'))

        # Create job ID (include chat_id and window name)
        job_id = f"hadith_{chat_id}_{window['name']}"

        # Schedule job
        scheduler.add_job(
            send_hadith_with_cooldown,
            trigger=DateTrigger(run_date=hadith_time_utc, timezone='UTC'),
            args=[chat_id, window['name']],
            id=job_id,
            name=f"Hadith: {window['name']} for group {chat_id}",
            replace_existing=True
        )

        logger.debug(f"Scheduled hadith ({window['name']}) for group {chat_id} at {hadith_time}")


def send_hadith_with_cooldown(chat_id: int, window_name: str):
    """
    Send hadith with cooldown check.
    Prevents sending hadiths too frequently.

    CRITICAL FIX: Now uses DATABASE instead of log file reading!
    This is much safer and more reliable.

    Args:
        chat_id: Group chat ID
        window_name: Window name (morning, midday, etc.)
    """
    try:
        # Get group info
        group = get_group(chat_id)
        if not group:
            return

        tz_str = group['timezone']
        group_tz = timezone(tz_str)
        today = datetime.now(group_tz).strftime('%Y-%m-%d')

        # =====================================================
        # COOLDOWN CHECK (DATABASE-BASED - NOT LOG FILE!)
        # =====================================================
        last_sent_time = get_last_hadith_sent_time(chat_id, config.HADITH_COOLDOWN_MINUTES)

        if last_sent_time:
            time_diff = (datetime.now() - last_sent_time).total_seconds()
            if time_diff < config.HADITH_COOLDOWN_MINUTES * 60:
                logger.debug(f"Cooldown active for group {chat_id} ({int(time_diff/60)}min elapsed)")
                return  # Cooldown not passed

        # =====================================================
        # DAILY LIMIT CHECK
        # =====================================================
        today_count = get_hadiths_sent_today_count(chat_id, today)

        if today_count >= config.MAX_HADITH_PER_DAY:
            logger.debug(f"Daily limit reached for group {chat_id} ({today_count} sent)")
            return

        # =====================================================
        # FETCH AND SEND HADITH
        # =====================================================
        hadith_message = get_cached_hadith(chat_id, window_name)

        if hadith_message and _bot_instance:
            # Send message
            from utils import send_message_safe
            if send_message_safe(_bot_instance, chat_id, hadith_message, parse_mode='HTML'):
                # Log hadith as sent to database
                log_hadith_sent(chat_id, 'unknown', window_name)

                # Mark content as sent
                mark_content_as_sent(chat_id, 'hadith', today)

                logger.info(f"Sent hadith ({window_name}) to group {chat_id}")

    except Exception as e:
        logger.error(f"Error sending hadith: {e}", exc_info=False)


def remove_group_hadith_jobs(chat_id: int):
    """
    Remove all hadith jobs for a group.

    Args:
        chat_id: Group chat ID
    """
    try:
        # Remove jobs with IDs starting with "hadith_{chat_id}_"
        for window in config.HADITH_WINDOWS:
            job_id = f"hadith_{chat_id}_{window['name']}"
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass

        logger.debug(f"Removed hadith jobs for group {chat_id}")
    except Exception as e:
        logger.debug(f"No hadith jobs to remove for group {chat_id}: {e}")


# =====================================================
# DAILY RESCHEDULING
# =====================================================

def schedule_daily_reschedule():
    """
    Schedule daily rescheduling job.
    Runs at midnight to rebuild all schedules for new day.
    """
    scheduler.add_job(
        rebuild_all_schedules,
        trigger=CronTrigger(hour=0, minute=0, timezone='UTC'),
        id='daily_reschedule',
        name='Daily Schedule Rebuild',
        replace_existing=True
    )
    logger.info("Scheduled daily reschedule at midnight UTC")


# =====================================================
# SCHEDULER MANAGEMENT
# =====================================================

def rebuild_all_schedules():
    """
    Rebuild all schedules for all active groups.
    Called on startup and daily at midnight.
    """
    logger.info("Rebuilding all schedules...")

    # Get all active groups
    groups = get_all_active_groups()
    logger.info(f"Rebuilding schedules for {len(groups)} groups")

    # Schedule prayer notifications for each group
    for group in groups:
        try:
            schedule_prayer_notifications_for_group(group['chat_id'])
        except Exception as e:
            logger.error(f"Error scheduling prayers for group {group['chat_id']}: {e}", exc_info=False)

    # Schedule hadiths for each group
    for group in groups:
        try:
            schedule_hadith_for_group(group['chat_id'])
        except Exception as e:
            logger.error(f"Error scheduling hadiths for group {group['chat_id']}: {e}", exc_info=False)

    logger.info("All schedules rebuilt successfully")


def reschedule_group(chat_id: int):
    """
    Reschedule all jobs for a specific group.
    Called when group settings change (city, method, timezone, enable/disable).

    Args:
        chat_id: Group chat ID
    """
    logger.info(f"Rescheduling jobs for group {chat_id}")

    # Fetch new prayer times
    fetch_and_save_prayer_times(chat_id)

    # Remove existing jobs
    remove_group_prayer_jobs(chat_id)
    remove_group_hadith_jobs(chat_id)

    # Reschedule prayer notifications
    schedule_prayer_notifications_for_group(chat_id)

    # Reschedule hadiths
    schedule_hadith_for_group(chat_id)

    logger.info(f"Rescheduling complete for group {chat_id}")


def remove_all_group_jobs(chat_id: int):
    """
    Remove ALL jobs for a group (prayers and hadiths).

    Args:
        chat_id: Group chat ID
    """
    remove_group_prayer_jobs(chat_id)
    remove_group_hadith_jobs(chat_id)


# =====================================================
# STARTUP AND SHUTDOWN
# =====================================================

def start_schedulers():
    """
    Start APScheduler.
    Must be called after set_bot_instance().
    """
    if _bot_instance is None:
        raise ValueError("Bot instance not set! Call set_bot_instance() first.")

    logger.info("Starting APScheduler (event-driven mode)")

    # Rebuild all schedules from database
    rebuild_all_schedules()

    # Schedule daily reschedule at midnight
    schedule_daily_reschedule()

    # Start scheduler
    scheduler.start()
    logger.info("APScheduler started successfully")


def stop_schedulers():
    """
    Stop APScheduler gracefully.
    """
    logger.info("Stopping APScheduler...")

    # Shutdown scheduler
    scheduler.shutdown(wait=False)

    # Close database connections
    from database import close_all_connections
    close_all_connections()

    logger.info("Schedulers stopped")
