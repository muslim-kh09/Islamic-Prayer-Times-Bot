#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot
==================================
A multi-group Telegram bot for tracking prayer times, sending azan notifications,
and managing religious content (athkar, hadiths).

Author: Senior Python Developer
Version: 1.0.2 (Enhanced Logging)
"""
from telebot.apihelper import ApiTelegramException
import sqlite3
import telebot
import requests
import threading
import time
import logging
import json
import random
import re
import signal
import sys
from datetime import datetime
from typing import Optional, Dict, List, Any
from pytz import timezone
from pathlib import Path
import os

# =====================================================
# CONFIGURATION
# =====================================================

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'prayer_bot.db')
CONTENT_FILE = os.getenv('CONTENT_FILE', 'content.json')

# API Configuration
ALADHAN_API_BASE = 'https://api.aladhan.com/v1/timingsByCity'

# Retry configuration for sending messages
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries
CONTENT_WINDOW_MINUTES = 2  # Time window for sending content

# =====================================================
# LOGGING SETUP (Enhanced & Fixed)
# =====================================================

# ============================================
# 1. إعداد الـ Root Logger (الأساس)
# ============================================
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # السماح بمرور كل المستويات

# مسح أي handlers موجودة مسبقاً لتجنب التكرار
if root_logger.handlers:
    root_logger.handlers.clear()

# ============================================
# 2. إعداد ملف السجل التفصيلي (يحفظ كل شيء)
# ============================================
LOG_FILE = 'bot_debug.log'

# التأكد من وجود المجلد
log_path = Path(LOG_FILE)
log_path.parent.mkdir(parents=True, exist_ok=True)

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)  # تسجيل أدق التفاصيل

# فورمات مفصل مع معلومات الملف والسطر
file_formatter = logging.Formatter(
    fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# ============================================
# 3. إعداد شاشة التيرمنل (للمهم فقط)
# ============================================
class ConsoleFilter(logging.Filter):
    """
    فلتر مخصص لتقليل الضوضاء في التيرمنل
    - يعرض فقط رسائل INFO, WARNING, ERROR, CRITICAL
    - يخفي رسائل DEBUG في التيرمنل
    """
    def filter(self, record):
        # عرض الرسائل المهمة فقط في التيرمنل
        return record.levelno >= logging.INFO

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)  # عرض المعلومات المهمة والأخطاء فقط

# إضافة الفلتر للكونسول
console_handler.addFilter(ConsoleFilter())

# فورمات بسيط للترمنل - بدون تاريخ وتفاصيل معقدة
console_formatter = logging.Formatter(
    fmt='%(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(console_formatter)

# ============================================
# 4. إضافة الـ handlers للـ root logger
# ============================================
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# ============================================
# 5. إعداد logger خاص بالتطبيق
# ============================================
logger = logging.getLogger('IslamicPrayerBot')
logger.setLevel(logging.DEBUG)

# منع تكرار الرسائل (حيث أن root logger يعالجها بالفعل)
logger.propagate = True

# رسالة اختبار للتأكد من العمل
logger.info("=" * 60)
logger.info("🚀 تم تشغيل نظام السجلات المطور")
logger.info("📝 التيرمنل للمهم، والملف للتفاصيل الكاملة")
logger.info("=" * 60)
logger.debug("هذا رسالة DEBUG - تظهر فقط في الملف")
logger.info("✅ نظام الـ Logging جاهز للعمل")


# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================
# IN-MEMORY CACHE (For preventing rapid duplicate API calls)
# =====================================================
# Format: {chat_id: last_fetch_timestamp}
fetch_cache: Dict[int, float] = {}
MIN_FETCH_INTERVAL = 5  # Minimum seconds between API calls for same group

# =====================================================
# SHUTDOWN EVENT (For graceful shutdown)
# =====================================================
# Global event to signal all threads to stop
shutdown_event = threading.Event()

# =====================================================
# MESSAGE SENDING HELPER (With retry mechanism)
# =====================================================

def send_message_safe(chat_id: int, text: str, parse_mode: str = 'HTML',
                   disable_web_page_preview: bool = False) -> bool:
    """
    Send a message with retry mechanism for better resilience.
    """
    for attempt in range(MAX_RETRIES):
        try:
            bot.send_message(
                chat_id,
                text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            logger.debug(f"Message sent to {chat_id} on attempt {attempt + 1}")
            return True

        except Exception as e:
            error_type = type(e).__name__
            logger.warning(f"Send attempt {attempt + 1} failed: {error_type} - {e}")

            # If it's the last attempt, return False
            if attempt == MAX_RETRIES - 1:
                logger.error(f"All {MAX_RETRIES} attempts failed for chat {chat_id}: {e}")

                # Check if it's a connection error
                if 'Connection' in error_type or 'RemoteDisconnected' in error_type:
                    return False  # Don't show error to user
                else:
                    try:
                        bot.send_message(
                            chat_id,
                            "عذراً، حدث خطأ في إرسال الرسالة. يرجى المحاولة لاحقاً ❌"
                        )
                    except Exception:
                        pass
                return False

            # Wait before retry
            time.sleep(RETRY_DELAY)

    return False


# =====================================================
# DATABASE FUNCTIONS
# =====================================================

def get_db_connection() -> sqlite3.Connection:
    """
    Get a database connection.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """
    Initialize the database with required tables if they don't exist.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row['name'] for row in cursor.fetchall()}

        # Read and execute schema file
        schema_path = 'database_schema.sql'
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()

            # Execute each statement
            for statement in schema.split(';'):
                if statement.strip():
                    try:
                        cursor.execute(statement)
                    except sqlite3.Error as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Database init warning: {e}")

            conn.commit()
            logger.info("Database initialized successfully")
        else:
            logger.warning(f"Schema file {schema_path} not found. Creating tables manually...")

            # Create tables manually if schema file doesn't exist
            create_tables_manually(cursor)
            conn.commit()

        conn.close()
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)


def create_tables_manually(cursor):
    """
    Create database tables manually if schema file is not available.
    """
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            score INTEGER DEFAULT 0,
            prayer_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL UNIQUE,
            group_name TEXT,
            city TEXT DEFAULT 'Riyadh',
            country TEXT DEFAULT 'Saudi Arabia',
            timezone TEXT DEFAULT 'Asia/Riyadh',
            calculation_method INTEGER DEFAULT 2,
            is_active INTEGER DEFAULT 1,
            notification_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Prayer times per group table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prayer_times_per_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_chat_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            fajr_time TEXT NOT NULL,
            dhuhr_time TEXT NOT NULL,
            asr_time TEXT NOT NULL,
            maghrib_time TEXT NOT NULL,
            isha_time TEXT NOT NULL,
            hijri_date TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE,
            UNIQUE(group_chat_id, date)
        )
    ''')

    # Azan sent log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS azan_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_chat_id INTEGER NOT NULL,
            prayer_name TEXT NOT NULL,
            prayer_date TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE,
            UNIQUE(group_chat_id, prayer_name, prayer_date)
        )
    ''')

    # Prayer logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prayer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            group_chat_id INTEGER,
            prayer_name TEXT NOT NULL,
            prayer_date TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE SET NULL
        )
    ''')

    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')


def get_or_create_user(telegram_id: int, username: str = None,
                       first_name: str = None, last_name: str = None) -> int:
    """
    Get existing user or create new one (with transaction).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('BEGIN TRANSACTION')

        try:
            # Try to get existing user
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()

            if user:
                user_id = user['id']
                # Update user info and last_active
                cursor.execute('''
                    UPDATE users
                    SET username = ?, first_name = ?, last_name = ?, last_active = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (username, first_name, last_name, user_id))
            else:
                # Create new user
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                user_id = cursor.lastrowid

            conn.commit()
            return user_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}", exc_info=True)
        raise


def get_group(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Get group settings by chat ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM groups WHERE chat_id = ?
        ''', (chat_id,))

        group = cursor.fetchone()
        conn.close()

        if group:
            return dict(group)
        return None

    except Exception as e:
        logger.error(f"Error in get_group: {e}", exc_info=True)
        return None


def get_all_active_groups() -> List[Dict[str, Any]]:
    """
    Get all active groups.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM groups WHERE is_active = 1
        ''')

        groups = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return groups

    except Exception as e:
        logger.error(f"Error in get_all_active_groups: {e}", exc_info=True)
        return []


def save_group_prayer_times(chat_id: int, date: str, prayer_times: Dict[str, str],
                            hijri_date: str = None) -> bool:
    """
    Save prayer times for a specific group.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Use INSERT OR REPLACE to handle unique constraint
        cursor.execute('''
            INSERT OR REPLACE INTO prayer_times_per_group
            (group_chat_id, date, fajr_time, dhuhr_time, asr_time, maghrib_time, isha_time, hijri_date, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            chat_id,
            date,
            prayer_times.get('Fajr', ''),
            prayer_times.get('Dhuhr', ''),
            prayer_times.get('Asr', ''),
            prayer_times.get('Maghrib', ''),
            prayer_times.get('Isha', ''),
            hijri_date
        ))

        conn.commit()
        conn.close()
        logger.info(f"Saved prayer times for group {chat_id} on {date}")
        return True

    except Exception as e:
        logger.error(f"Error in save_group_prayer_times: {e}", exc_info=True)
        return False


def get_group_prayer_times(chat_id: int, date: str) -> Optional[Dict[str, Any]]:
    """
    Get prayer times for a specific group on a specific date.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM prayer_times_per_group
            WHERE group_chat_id = ? AND date = ?
        ''', (chat_id, date))

        result = cursor.fetchone()
        conn.close()

        if result:
            return dict(result)
        return None

    except Exception as e:
        logger.error(f"Error in get_group_prayer_times: {e}", exc_info=True)
        return None


def has_azan_sent_today(chat_id: int, prayer_name: str, date: str) -> bool:
    """
    Check if azan has already been sent for a specific prayer on a specific date.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 1 FROM azan_sent_log
            WHERE group_chat_id = ? AND prayer_name = ? AND prayer_date = ?
        ''', (chat_id, prayer_name, date))

        result = cursor.fetchone()
        conn.close()

        return result is not None

    except Exception as e:
        logger.error(f"Error in has_azan_sent_today: {e}", exc_info=True)
        return False


def log_azan_sent(chat_id: int, prayer_name: str, date: str) -> bool:
    """
    Log that azan has been sent for a specific prayer on a specific date.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Use INSERT OR IGNORE to handle unique constraint
        cursor.execute('''
            INSERT OR IGNORE INTO azan_sent_log
            (group_chat_id, prayer_name, prayer_date, sent_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (chat_id, prayer_name, date))

        conn.commit()
        conn.close()
        logger.info(f"Logged azan sent for {prayer_name} in group {chat_id} on {date}")
        return True

    except Exception as e:
        logger.error(f"Error in log_azan_sent: {e}", exc_info=True)
        return False


def record_user_prayer(user_id: int, group_chat_id: int, prayer_name: str, date: str) -> bool:
    """
    Record a user's completed prayer and update their score (with transaction).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('BEGIN TRANSACTION')

        try:
            # Check if prayer already recorded for today
            cursor.execute('''
                SELECT 1 FROM prayer_logs
                WHERE user_id = ? AND group_chat_id = ? AND prayer_name = ? AND prayer_date = ?
            ''', (user_id, group_chat_id, prayer_name, date))

            if cursor.fetchone():
                conn.rollback()
                conn.close()
                return False  # Already recorded

            # Record prayer
            cursor.execute('''
                INSERT INTO prayer_logs (user_id, group_chat_id, prayer_name, prayer_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, group_chat_id, prayer_name, date))

            # Update user score and prayer count
            cursor.execute('''
                UPDATE users
                SET score = score + 10, prayer_count = prayer_count + 1
                WHERE id = ?
            ''', (user_id,))

            conn.commit()
            logger.info(f"Recorded prayer {prayer_name} for user {user_id}")
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error in record_user_prayer: {e}", exc_info=True)
        return False


def get_top_users(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top users by score.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM users
            ORDER BY score DESC
            LIMIT ?
        ''', (limit,))

        users = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return users

    except Exception as e:
        logger.error(f"Error in get_top_users: {e}", exc_info=True)
        return []


# =====================================================
# API FUNCTIONS
# =====================================================

def fetch_and_save_prayer_times(chat_id: int) -> Optional[Dict[str, str]]:
    """
    Fetch prayer times from API and save to database for a specific group.
    """
    try:
        # Check if we recently fetched for this group (prevent rapid duplicate calls)
        current_time = time.time()
        if chat_id in fetch_cache:
            last_fetch = fetch_cache[chat_id]
            if current_time - last_fetch < MIN_FETCH_INTERVAL:
                logger.debug(f"Skipping fetch for group {chat_id} - called too recently")
                
                # Try to get existing data for today if cache is hit
                # Note: We need the timezone to know 'today' correctly even in cache hit
                group = get_group(chat_id)
                if group:
                    try:
                        group_tz = timezone(group['timezone'])
                        today = datetime.now(group_tz).strftime('%Y-%m-%d')
                        prayer_times_data = get_group_prayer_times(chat_id, today)
                        if prayer_times_data:
                            return {
                                'Fajr': prayer_times_data['fajr_time'],
                                'Dhuhr': prayer_times_data['dhuhr_time'],
                                'Asr': prayer_times_data['asr_time'],
                                'Maghrib': prayer_times_data['maghrib_time'],
                                'Isha': prayer_times_data['isha_time']
                            }
                    except Exception:
                        pass
                return None

        # Update fetch cache
        fetch_cache[chat_id] = current_time

        # Get group settings
        group = get_group(chat_id)

        if not group:
            logger.warning(f"Group {chat_id} not found in database")
            return None

        city = group['city']
        country = group['country']
        method = group['calculation_method']
        tz_str = group['timezone']

        # 1. Determine correct date based on Group Timezone
        try:
            group_tz = timezone(tz_str)
            today = datetime.now(group_tz).strftime('%Y-%m-%d')
        except Exception:
            # Fallback
            today = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"Fetching prayer times for {city}, {country} (Date: {today})")

        # Build API request
        params = {
            'city': city,
            'country': country,
            'method': method
        }

        response = requests.get(ALADHAN_API_BASE, params=params, timeout=10)

        if response.status_code != 200:
            logger.error(f"API request failed with status code {response.status_code}")
            return None

        data = response.json()

        if data.get('code') != 200:
            logger.error(f"API returned error: {data}")
            return None

        # =====================================================
        # الجزء الذي كان ناقصاً وتمت إعادته
        # =====================================================
        timings = data['data']['timings']
        date_data = data['data']['date']
        hijri_date = date_data['hijri']['date']

        prayer_times = {
            'Fajr': timings['Fajr'],
            'Dhuhr': timings['Dhuhr'],
            'Asr': timings['Asr'],
            'Maghrib': timings['Maghrib'],
            'Isha': timings['Isha']
        }
        # =====================================================

        # Save to database
        save_group_prayer_times(chat_id, today, prayer_times, hijri_date)

        logger.info(f"Successfully fetched and saved prayer times for group {chat_id}")
        return prayer_times

    except requests.RequestException as e:
        logger.error(f"Network error in fetch_and_save_prayer_times: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error in fetch_and_save_prayer_times: {e}", exc_info=True)
        return None


# =====================================================
# CONTENT FUNCTIONS
# =====================================================

def load_content() -> Dict[str, Any]:
    """
    Load religious content from JSON file.
    """
    try:
        if os.path.exists(CONTENT_FILE):
            with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'categories': {'morning_athkar': [], 'evening_athkar': [], 'hadiths': []}}
    except Exception as e:
        logger.error(f"Error loading content: {e}", exc_info=True)
        return {'categories': {'morning_athkar': [], 'evening_athkar': [], 'hadiths': []}}


def parse_time(time_str: str) -> tuple:
    """
    Parse time string in HH:MM format.
    """
    try:
        parts = time_str.split(':')
        return int(parts[0]), int(parts[1])
    except Exception:
        return 0, 0


def time_within_window(current_time: tuple, prayer_time: tuple,
                       window_minutes: int = 1) -> bool:
    """
    Check if current time is within the specified window of prayer time.
    """
    try:
        current_minutes = current_time[0] * 60 + current_time[1]
        prayer_minutes = prayer_time[0] * 60 + prayer_time[1]

        return abs(current_minutes - prayer_minutes) <= window_minutes

    except Exception as e:
        logger.error(f"Error in time_within_window: {e}", exc_info=True)
        return False


def send_azan_notification(chat_id: int, prayer_name: str, prayer_time: str) -> bool:
    """
    Send azan notification to a group with Smart Error Handling.
    """
    try:
        prayer_names_arabic = {
            'Fajr': 'الفجر', 'Dhuhr': 'الظهر', 'Asr': 'العصر',
            'Maghrib': 'المغرب', 'Isha': 'العشاء'
        }
        prayer_arabic = prayer_names_arabic.get(prayer_name, prayer_name)

        message = f"""
🕌 <b>الأذان - {prayer_arabic}</b> 🕌

حان الآن وقت صلاة {prayer_arabic} - {prayer_time}

حَيَّ عَلَى الصَّلاَةِ، حَيَّ عَلَى الْفَلاَحِ

🤲 اللَّهُمَّ اجْعَلْنَا مِنَ الْمُحْتَفِظِينَ بِالصَّلَوَاتِ 🤲
        """

        # Create inline keyboard for prayer logging
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        btn_prayed = telebot.types.InlineKeyboardButton(
            f'✅ صليت {prayer_arabic}',
            callback_data=f'prayed_{prayer_name.lower()}'
        )
        keyboard.add(btn_prayed)

        # محاولة الإرسال
        bot.send_message(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
        logger.info(f"✅ Sent azan notification for {prayer_name} to group {chat_id}")
        return True

    except ApiTelegramException as e:
        # التعامل الذكي مع أخطاء تليجرام
        error_code = e.result_json.get('error_code')
        description = e.result_json.get('description', '')

        if error_code == 403 or 'kicked' in description or 'blocked' in description:
            logger.warning(f"🚫 Bot was kicked/blocked from group {chat_id}. Deleting data now...")
            # حذف المجموعة فوراً من قاعدة البيانات لمنع تكرار الخطأ
            reset_group_data(chat_id)
        else:
            logger.error(f"⚠️ Telegram API Error for {chat_id}: {e}")
        
        return False

    except Exception as e:
        logger.error(f"❌ General Error sending azan notification: {e}", exc_info=True)
        return False


def azan_scheduler_loop():
    """
    Dynamic azan scheduler loop.
    Runs in a separate thread and checks all active groups every minute.
    """
    logger.info("Starting azan scheduler loop")

    while not shutdown_event.is_set():
        try:
            # Get all active groups
            groups = get_all_active_groups()

            for group in groups:
                try:
                    chat_id = group['chat_id']
                    tz_str = group['timezone']

                    # 1. Get current time in group's timezone
                    try:
                        group_tz = timezone(tz_str)
                        current_time_obj = datetime.now(group_tz)
                    except Exception:
                        logger.error(f"Invalid timezone {tz_str} for group {chat_id}")
                        continue

                    # 2. Calculate 'Today' based on THAT group's time
                    today = current_time_obj.strftime('%Y-%m-%d')
                    
                    current_hour = current_time_obj.hour
                    current_minute = current_time_obj.minute

                    # 3. Get prayer times for this specific date
                    prayer_times_data = get_group_prayer_times(chat_id, today)

                    # If no prayer times for today, fetch them
                    if not prayer_times_data:
                        logger.debug(f"No prayer times for group {chat_id} today ({today}), fetching...")
                        
                        prayer_times = fetch_and_save_prayer_times(chat_id)
                        
                        if prayer_times:
                            prayer_times_data = {
                                'fajr_time': prayer_times['Fajr'],
                                'dhuhr_time': prayer_times['Dhuhr'],
                                'asr_time': prayer_times['Asr'],
                                'maghrib_time': prayer_times['Maghrib'],
                                'isha_time': prayer_times['Isha']
                            }
                        else:
                            continue

                    # Check each prayer time
                    prayers = [
                        ('Fajr', prayer_times_data['fajr_time']),
                        ('Dhuhr', prayer_times_data['dhuhr_time']),
                        ('Asr', prayer_times_data['asr_time']),
                        ('Maghrib', prayer_times_data['maghrib_time']),
                        ('Isha', prayer_times_data['isha_time'])
                    ]

                    for prayer_name, prayer_time_str in prayers:
                        try:
                            # Parse prayer time
                            prayer_hour, prayer_minute = parse_time(prayer_time_str)

                            # Check if current time is within the azan window (1 minute)
                            if time_within_window((current_hour, current_minute),
                                                  (prayer_hour, prayer_minute),
                                                  window_minutes=1):
                                # Check if azan already sent today
                                if not has_azan_sent_today(chat_id, prayer_name.lower(), today):
                                    # Send azan notification
                                    if send_azan_notification(chat_id, prayer_name, prayer_time_str):
                                        # Log that azan was sent
                                        log_azan_sent(chat_id, prayer_name.lower(), today)
                                        logger.info(f"🕌 Azan sent: {prayer_name} in group {chat_id}")

                        except Exception as e:
                            logger.error(f"Error checking prayer {prayer_name}: {e}")

                except Exception as e:
                    logger.error(f"Error processing group {group.get('chat_id', 'unknown')}: {e}")
            
            # Sleep to reduce CPU usage (30 seconds is good enough for minute-precision)
            time.sleep(30)

        except Exception as e:
            logger.error(f"Error in azan scheduler loop: {e}", exc_info=True)
            time.sleep(5)  # Wait a bit if main loop crashes

    logger.info("Azan scheduler loop stopped gracefully")


# =====================================================
# CONTENT SCHEDULER
# =====================================================

# Content sent log to prevent duplicate sends in same day
# Format: {chat_id: {date: {category: sent_count}}}
content_sent_log: Dict[int, Dict[str, Dict[str, int]]] = {}


def get_random_content_from_category(category: str) -> Optional[str]:
    """
    Get a random content item from a specific category.
    """
    try:
        content = load_content()
        content_list = content['categories'].get(category, [])

        if not content_list:
            return None

        return random.choice(content_list)
    except Exception as e:
        logger.error(f"Error in get_random_content_from_category: {e}", exc_info=True)
        return None


def get_all_content_categories() -> List[str]:
    """
    Get all available content categories from content.json.
    """
    try:
        content = load_content()
        return list(content.get('categories', {}).keys())
    except Exception as e:
        logger.error(f"Error in get_all_content_categories: {e}", exc_info=True)
        return []


def get_schedule_config() -> Dict[str, Any]:
    """
    Get schedule configuration from content.json.
    """
    try:
        content = load_content()
        return content.get('schedule', {})
    except Exception as e:
        logger.error(f"Error in get_schedule_config: {e}", exc_info=True)
        return {}


def is_content_sent_today(chat_id: int, content_type: str, date: str) -> bool:
    """
    Check if content was already sent today to a group (from database).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 1 FROM content_sent_log
            WHERE group_chat_id = ? AND content_type = ? AND sent_date = ?
        ''', (chat_id, content_type, date))

        result = cursor.fetchone()
        conn.close()

        return result is not None

    except Exception as e:
        logger.error(f"Error in is_content_sent_today: {e}", exc_info=True)
        return False


def mark_content_as_sent(chat_id: int, content_type: str, date: str):
    """
    Mark content as sent for today (to database).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR IGNORE INTO content_sent_log
            (group_chat_id, content_type, sent_date)
            VALUES (?, ?, ?)
        ''', (chat_id, content_type, date))

        conn.commit()
        conn.close()
        logger.debug(f"Marked {content_type} as sent for group {chat_id} on {date}")

    except Exception as e:
        logger.error(f"Error in mark_content_as_sent: {e}")


def send_content_message(chat_id: int, content_type: str, content_text: str) -> bool:
    """
    Send content message to a group.
    """
    if send_message_safe(chat_id, content_text, parse_mode='HTML'):
        logger.info(f"Sent {content_type} to group {chat_id}")
        return True
    return False


def content_scheduler_loop():
    """
    Content scheduler loop.
    """
    logger.info("Starting content scheduler loop")

    while not shutdown_event.is_set():
        try:
            schedule_config = get_schedule_config()
            groups = get_all_active_groups()

            for group in groups:
                try:
                    chat_id = group['chat_id']
                    tz_str = group['timezone']

                    # Get current time in group's timezone
                    group_tz = timezone(tz_str)
                    current_time = datetime.now(group_tz)
                    
                    # =====================================================
                    # التعديل: حساب "اليوم" لكل مجموعة
                    # =====================================================
                    today = current_time.strftime('%Y-%m-%d')

                    current_hour = current_time.hour
                    current_minute = current_time.minute

                    # Check scheduled content
                    for content_type, schedule_info in schedule_config.items():
                        try:
                            # Check if content is enabled
                            if not schedule_info.get('enabled', False):
                                continue

                            # Get scheduled times for this content
                            scheduled_times = schedule_info.get('times', [])

                            # Check if current time matches any scheduled time
                            current_time_str = f"{current_hour:02d}:{current_minute:02d}"
                            
                            # Allow a small window (1 minute) for scheduled times
                            for scheduled_time in scheduled_times:
                                if time_within_window((current_hour, current_minute),
                                                      parse_time(scheduled_time),
                                                      window_minutes=1):
                                    # Check if already sent today
                                    if not is_content_sent_today(chat_id, content_type, today):
                                        # Get content
                                        content_text = get_random_content_from_category(content_type)
                                        
                                        if content_text:
                                            # Send content
                                            if send_content_message(chat_id, content_type, content_text):
                                                # Mark as sent
                                                mark_content_as_sent(chat_id, content_type, today)
                                                logger.info(f"📧 Content sent: {content_type} in group {chat_id}")

                        except Exception as e:
                            logger.error(f"Error processing content {content_type}: {e}")

                except Exception as e:
                    logger.error(f"Error processing group ... : {e}")
            
            # Sleep logic
            time.sleep(30)

        except Exception as e:
            logger.error(f"Error in content scheduler loop: {e}", exc_info=True)


# =====================================================
# BOT HANDLERS
# =====================================================

@bot.message_handler(commands=['test_azan'])
def handle_test_azan(message):
    """
    أمر تجريبي للمشرفين: إرسال أذان وهمي الآن للتأكد من عمل البوت
    """
    chat_id = message.chat.id
    user_id = message.from_user.id  # 1. نحتاج معرف المستخدم للتحقق منه

    try:
        if message.chat.type in ['group', 'supergroup']:
            
            # 2. هذا هو الشرط الناقص: التحقق من أن المستخدم مشرف
            if not is_user_admin(chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return

            # إرسال تجربة لصلاة الظهر (كمثال)
            bot.reply_to(message, "⏳ جاري تجربة إرسال الأذان...")
            success = send_azan_notification(chat_id, 'Dhuhr', '12:00 (تجربة)')
            
            if success:
                # لا داعي لإرسال رسالة نجاح إضافية لأن دالة send_azan_notification ترسل الأذان نفسه
                pass 
            else:
                bot.send_message(chat_id, "❌ فشلت التجربة. تأكد من صلاحيات البوت في الإرسال.")
        else:
             bot.reply_to(message, "هذا الأمر للمجموعات فقط.")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")



@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Handle /start command.
    """
    try:
        user = message.from_user
        chat_id = message.chat.id

        # Register user in database
        user_id = get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        welcome_message = f"""
🌸 <b>مرحباً بك في بوت أوقات الصلاة</b> 🌸

أهلاً {user.first_name}! 👋

🕌 هذا البوت يساعدك في:
• معرفة أوقات الصلاة في مدينتك
• استقبال إشعارات الأذان
• تسجيل صلواتك
• الاستفادة من الأذكار والأحاديث

<b>الأوامر المتاحة:</b>

/setup - إعداد إعدادات المجموعة
/setgroupcity - تغيير المدينة
/groupstatus - عرض إعدادات المجموعة
/top - لوحة المتصدرين
/rules - القوانين

استخدم الأوامر للاستفادة من البوت! 🚀
        """

        bot.send_message(chat_id, welcome_message, parse_mode='HTML')
        logger.info(f"User {user.id} started the bot")

    except Exception as e:
        logger.error(f"Error in handle_start: {e}", exc_info=True)


@bot.message_handler(commands=['setup'])
def handle_setup(message):
    """
    Handle /setup command.
    """
    try:
        chat_id = message.chat.id
        chat_type = message.chat.type

        if chat_type not in ['group', 'supergroup']:
            bot.reply_to(message, "هذا الأمر يعمل فقط في المجموعات! 👥")
            return

        # Check if group already exists
        existing_group = get_group(chat_id)

        if existing_group:
            bot.reply_to(message, "المجموعة مهيأة بالفعل! ✅")
            return

        # Create new group entry
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO groups (chat_id, group_name, city, country, timezone)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, message.chat.title, 'Riyadh', 'Saudi Arabia', 'Asia/Riyadh'))

        conn.commit()
        conn.close()

        setup_message = """
✅ <b>تم إعداد المجموعة بنجاح!</b>

الإعدادات الافتراضية:
📍 المدينة: الرياض
🇸🇦 الدولة: السعودية
🕐 التوقيت: السعودية

استخدم /setgroupcity لتغيير المدينة
استخدم /groupstatus لعرض الإعدادات الحالية
        """

        bot.send_message(chat_id, setup_message, parse_mode='HTML')
        logger.info(f"Group {chat_id} setup completed")

    except Exception as e:
        logger.error(f"Error in handle_setup: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ أثناء إعداد المجموعة! ❌")


@bot.message_handler(commands=['setgroupcity'])
def handle_setgroupcity(message):
    """
    Handle /setgroupcity command.
    RESTRICTED TO ADMINS ONLY.
    Show inline keyboard with city options.
    """
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        chat_type = message.chat.type

        # التحقق من أن المحادثة هي مجموعة
        if chat_type not in ['group', 'supergroup']:
            bot.reply_to(message, "هذا الأمر يعمل فقط في المجموعات! 👥")
            return

        # ---------------------------------------------------------
        # 🔒 التحقق من صلاحيات المشرف
        # ---------------------------------------------------------
        if not is_user_admin(chat_id, user_id):
            bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
            return
        # ---------------------------------------------------------

        # Check if group exists
        group = get_group(chat_id)

        if not group:
            bot.reply_to(message, "المجموعة غير مهيأة! استخدم /setup أولاً")
            return

        # Create inline keyboard with cities
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=3)

        cities = [
            ('الرياض', 'Riyadh', 'Saudi Arabia', 'Asia/Riyadh'),
            ('مكة', 'Mecca', 'Saudi Arabia', 'Asia/Riyadh'),
            ('المدينة', 'Medina', 'Saudi Arabia', 'Asia/Riyadh'),
            ('القاهرة', 'Cairo', 'Egypt', 'Africa/Cairo'),
            ('الجزائر', 'Algiers', 'Algeria', 'Africa/Algiers'),
            ('الرباط', 'Rabat', 'Morocco', 'Africa/Casablanca'),
            ('تونس', 'Tunis', 'Tunisia', 'Africa/Tunis'),
            ('عمّان', 'Amman', 'Jordan', 'Asia/Amman'),
            ('بيروت', 'Beirut', 'Lebanon', 'Asia/Beirut'),
            ('دمشق', 'Damascus', 'Syria', 'Asia/Damascus'),
            ('بغداد', 'Baghdad', 'Iraq', 'Asia/Baghdad'),
            ('الكويت', 'Kuwait City', 'Kuwait', 'Asia/Kuwait'),
            ('الدوحة', 'Doha', 'Qatar', 'Asia/Qatar'),
            ('أبوظبي', 'Abu Dhabi', 'UAE', 'Asia/Dubai'),
            ('دبي', 'Dubai', 'UAE', 'Asia/Dubai'),
            ('موسكو', 'Moscow', 'Russia', 'Europe/Moscow'),
            ('لندن', 'London', 'UK', 'Europe/London'),
            ('نيويورك', 'New York', 'USA', 'America/New_York'),
        ]

        for arabic_name, city, country, tz in cities:
            callback_data = f"city_{city}|{country}|{tz}"
            btn = telebot.types.InlineKeyboardButton(arabic_name, callback_data=callback_data)
            keyboard.add(btn)

        bot.send_message(
            chat_id,
            "📍 <b>إعدادات المدينة (للمشرفين فقط)</b>\nاختر مدينتك لضبط مواقيت الصلاة:",
            parse_mode='HTML',
            reply_markup=keyboard
        )

        logger.info(f"City selection menu sent to group {chat_id} by admin {user_id}")

    except Exception as e:
        logger.error(f"Error in handle_setgroupcity: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.callback_query_handler(func=lambda call: call.data.startswith('city_'))
def handle_city_selection(call):
    """
    Handle city selection from inline keyboard.
    """
    try:
        chat_id = call.message.chat.id

        # Parse callback data
        data = call.data[5:]  # Remove 'city_' prefix
        city, country, tz = data.split('|')

        # Get current group settings
        current_group = get_group(chat_id)

        # Check if city is the same as current
        if current_group and current_group['city'] == city:
            # Same city selected, just answer callback
            bot.answer_callback_query(
                call.id,
                f"المدينة الحالية هي بالفعل {city}! ✅",
                show_alert=True
            )
            logger.info(f"Group {chat_id} already set to city {city}")
            return

        # Update group settings
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE groups
            SET city = ?, country = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        ''', (city, country, tz, chat_id))

        conn.commit()
        conn.close()

        # Fetch and save new prayer times immediately
        fetch_and_save_prayer_times(chat_id)

        # Send confirmation
        confirmation_message = f"""
✅ <b>تم تحديث المدينة بنجاح!</b>

📍 المدينة الجديدة: {city}
🇸🇦 الدولة: {country}
🕐 التوقيت: {tz}

سيتم إرسال إشعارات الأذان حسب التوقيت الجديد!

استخدم /groupstatus لعرض الإعدادات والأوقات
        """

        bot.edit_message_text(confirmation_message, chat_id, call.message.message_id, parse_mode='HTML')
        bot.answer_callback_query(call.id, "تم تحديث المدينة بنجاح! ✅")
        logger.info(f"Group {chat_id} updated to city {city}, {country}")

    except Exception as e:
        logger.error(f"Error in handle_city_selection: {e}", exc_info=True)


@bot.message_handler(commands=['groupstatus'])
def handle_groupstatus(message):
    """
    Handle /groupstatus command.
    """
    try:
        chat_id = message.chat.id

        # Get group settings
        group = get_group(chat_id)

        if not group:
            bot.reply_to(message, "المجموعة غير مهيأة! استخدم /setup أولاً")
            return

        # Get today's prayer times
        today = datetime.now().strftime('%Y-%m-%d')
        prayer_times = get_group_prayer_times(chat_id, today)

        # Build status message
        status_message = f"""
📊 <b>إعدادات المجموعة</b> 📊

📍 المدينة: {group['city']}
🇸🇦 الدولة: {group['country']}
🕐 التوقيت: {group['timezone']}
✨ حالة الإشعارات: {'مفعّلة' if group['notification_enabled'] else 'معطّلة'}

"""

        if prayer_times:
            status_message += f"""
<b>أوقات الصلاة اليوم</b> 🕌

🌅 الفجر: {prayer_times['fajr_time']}
☀️ الظهر: {prayer_times['dhuhr_time']}
🌤️ العصر: {prayer_times['asr_time']}
🌅 المغرب: {prayer_times['maghrib_time']}
🌙 العشاء: {prayer_times['isha_time']}

"""
            if prayer_times['hijri_date']:
                status_message += f"📆 التاريخ الهجري: {prayer_times['hijri_date']}\n"
        else:
            status_message += "\n⏳ جاري جلب أوقات الصلاة...\n"

        bot.send_message(chat_id, status_message, parse_mode='HTML')
        logger.info(f"Group status displayed for {chat_id}")

    except Exception as e:
        logger.error(f"Error in handle_groupstatus: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.callback_query_handler(func=lambda call: call.data.startswith('prayed_'))
def handle_prayed_callback(call):
    """
    Handle prayed button callback.
    """
    try:
        user = call.from_user
        chat_id = call.message.chat.id
        prayer_name = call.data[7:]  # Remove 'prayed_' prefix

        # Get or create user
        user_id = get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')

        # Record prayer
        if record_user_prayer(user_id, chat_id, prayer_name, today):
            prayer_names_arabic = {
                'fajr': 'الفجر',
                'dhuhr': 'الظهر',
                'asr': 'العصر',
                'maghrib': 'المغرب',
                'isha': 'العشاء'
            }

            prayer_arabic = prayer_names_arabic.get(prayer_name, prayer_name)
            success_message = f"""
✅ <b>تم تسجيل صلاتك!</b>

شكراً لتسجيل صلاة {prayer_arabic} 🤲
+10 نقاط! 🌟
            """
        else:
            success_message = "تم تسجيل هذه الصلاة مسبقاً اليوم! ✅"

        bot.answer_callback_query(call.id, success_message, show_alert=True)

    except Exception as e:
        logger.error(f"Error in handle_prayed_callback: {e}", exc_info=True)


def get_current_prayer(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the current prayer based on current time.

    Args:
        chat_id: The group chat ID

    Returns:
        dict: Current prayer info {'name': 'Fajr', 'name_arabic': 'الفجر', 'time': '05:30'} or None
    """
    try:
        # Get group settings
        group = get_group(chat_id)
        if not group:
            return None

        # Get today's prayer times
        today = datetime.now().strftime('%Y-%m-%d')
        prayer_times_data = get_group_prayer_times(chat_id, today)

        if not prayer_times_data:
            return None

        # Get current time in group's timezone
        tz_str = group['timezone']
        group_tz = timezone(tz_str)
        current_time = datetime.now(group_tz)
        current_hour = current_time.hour
        current_minute = current_time.minute

        # Parse prayer times and convert to minutes
        prayers = [
            ('Fajr', 'الفجر', prayer_times_data['fajr_time']),
            ('Dhuhr', 'الظهر', prayer_times_data['dhuhr_time']),
            ('Asr', 'العصر', prayer_times_data['asr_time']),
            ('Maghrib', 'المغرب', prayer_times_data['maghrib_time']),
            ('Isha', 'العشاء', prayer_times_data['isha_time'])
        ]

        # Convert current time to minutes
        current_total_minutes = current_hour * 60 + current_minute

        # Parse all prayer times
        prayer_times = []
        for name, name_ar, time_str in prayers:
            hour, minute = parse_time(time_str)
            total_minutes = hour * 60 + minute
            prayer_times.append({
                'name': name,
                'name_arabic': name_ar,
                'time': time_str,
                'total_minutes': total_minutes
            })

        # Find current prayer - it's the last prayer where time <= current time
        current_prayer = None

        for i in range(len(prayer_times)):
            prayer = prayer_times[i]
            next_prayer = prayer_times[i + 1] if i < len(prayer_times) - 1 else None

            # Check if current time is past this prayer time
            if current_total_minutes >= prayer['total_minutes']:
                # If there's a next prayer, make sure current time is before it
                if next_prayer and current_total_minutes >= next_prayer['total_minutes']:
                    # Not this prayer, continue to next
                    continue
                # This is the current prayer
                current_prayer = prayer
                break

        return current_prayer

    except Exception as e:
        logger.error(f"Error in get_current_prayer: {e}", exc_info=True)
        return None


@bot.message_handler(commands=['prayed'])
def handle_prayed(message):
    """
    Handle /prayed command.
    Shows only the current prayer for logging.
    """
    try:
        chat_id = message.chat.id

        # Get current prayer
        current_prayer = get_current_prayer(chat_id)

        if not current_prayer:
            # No prayer times or no current prayer
            group = get_group(chat_id)
            if not group:
                bot.send_message(
                    chat_id,
                    "⚠️ لم يتم إعداد المجموعة بعد!\n\n"
                    "الرجاء استخدام /setup لإعداد المجموعة أولاً."
                )
            else:
                bot.send_message(
                    chat_id,
                    "⏰ لم يحن وقت أي صلاة بعد.\n\n"
                    "يمكنك استخدام هذا الأمر بعد دخول وقت الصلاة."
                )
            return

        # Display only the current prayer
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)

        btn = telebot.types.InlineKeyboardButton(
            f'✅ صليت {current_prayer["name_arabic"]}',
            callback_data=f'manual_prayed_{current_prayer["name"].lower()}'
        )
        keyboard.add(btn)

        bot.send_message(
            chat_id,
            f"⏰ الصلاة الحالية: <b>{current_prayer['name_arabic']}</b>\n"
            f"📅 الوقت: {current_prayer['time']}\n\n"
            "اضغط على الزر لتسجيل الصلاة:",
            parse_mode='HTML',
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in handle_prayed: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.callback_query_handler(func=lambda call: call.data.startswith('manual_prayed_'))
def handle_manual_prayed_callback(call):
    """
    Handle manual prayer recording callback.
    """
    try:
        prayer_name = call.data[14:]  # Remove 'manual_prayed_' prefix

        # Forward to the normal prayed handler
        call.data = f'prayed_{prayer_name}'
        handle_prayed_callback(call)

    except Exception as e:
        logger.error(f"Error in handle_manual_prayed_callback: {e}", exc_info=True)


@bot.message_handler(commands=['top'])
def handle_top(message):
    """
    Handle /top command.
    """
    try:
        top_users = get_top_users(10)

        if not top_users:
            bot.reply_to(message, "لا يوجد مستخدمين في السجل بعد! 📊")
            return

        leaderboard_message = "🏆 <b>لوحة المتصدرين</b> 🏆\n\n"

        for idx, user in enumerate(top_users, start=1):
            medal = ['🥇', '🥈', '🥉'][idx - 1] if idx <= 3 else f"{idx}."
            name = user['first_name'] or user['username'] or 'مستخدم'
            leaderboard_message += f"{medal} {name}\n"
            leaderboard_message += f"   📊 عدد الصلوات: {user['prayer_count']}\n"
            leaderboard_message += f"   ⭐ النقاط: {user['score']}\n\n"

        bot.send_message(message.chat.id, leaderboard_message, parse_mode='HTML')
        logger.info("Leaderboard displayed")

    except Exception as e:
        logger.error(f"Error in handle_top: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.message_handler(commands=['rules'])
def handle_rules(message):
    """
    Handle /rules command.
    """
    try:
        rules_message = """
📜 <b>قوانين البوت</b> 📜

<b>الاستخدام الصحيح للبوت:</b>

1️⃣ يجب أن يكون البوت مشرفاً في المجموعة
2️⃣ استخدم /setup لإعداد المجموعة لأول مرة
3️⃣ استخدم /setgroupcity لتحديد مدينتك
4️⃣ استخدم /groupstatus لعرض الإعدادات والأوقات

<b>تسجيل الصلوات:</b>

• يمكنك تسجيل صلواتك عبر زر الأذان
• أو استخدم /prayed لتسجيل يدوياً
• كل صلاة = +10 نقاط

<b>الإشعارات:</b>

• البوت يرسل إشعار الأذان قبل أو عند وقت الصلاة
• الإشعارات تعتمد على توقيت مدينتك
• يمكنك تغيير المدينة في أي وقت

<b>المحتوى الديني:</b>

• الأذكار والأحاديث تُرسل بشكل دوري
• المحتوى موثق من مصادر موثوقة

<b>المحتوى المجدول:</b>

• البوت يرسل المحتوى تلقائياً في أوقات محددة
• استخدم /contentstatus لعرض الجدول
• استخدم /sendcontent للإرسال اليدوي

🤲 نسأل الله أن ينفع بنا وبكم 🤲
        """

        send_message_safe(message.chat.id, rules_message)
        logger.info("Rules displayed")

    except Exception as e:
        logger.error(f"Error in handle_rules: {e}", exc_info=True)


@bot.message_handler(commands=['help'])
def handle_help(message):
    """
    Handle /help command.
    """
    try:
        help_message = """
🆘 <b>دليل المساعدة</b> 🆘

<b>الأوامر الأساسية:</b>

/start - بدء البوت والتسجيل
/setup - إعداد المجموعة
/setgroupcity - تغيير المدينة
/groupstatus - عرض الإعدادات والأوقات
/prayed - تسجيل صلاة
/top - لوحة المتصدرين
/rules - عرض القوانين
/help - عرض هذه الرسالة

<b>أوامر المحتوى:</b>

/contentstatus - عرض جدول المحتوى
/sendcontent - إرسال محتوى عشوائي للمجموعة

<b>الأزرار التفاعلية:</b>

📋 زر تسجيل الصلاة (يظهر مع كل أذان)
📍 اختيار المدينة (من قائمة المدن المتاحة)

<b>معلومات إضافية:</b>

• البوت يدعم عدد غير محدود من المجموعات
• كل مجموعة لها إعداداتها الخاصة
• الإشعارات تعمل حسب توقيت كل مجموعة
• المحتوى الديني يُرسل تلقائياً حسب الجدول

للدعم والتواصل، تواصل مع مشرف البوت
        """

        bot.send_message(message.chat.id, help_message, parse_mode='HTML')
        logger.info("Help displayed")

    except Exception as e:
        logger.error(f"Error in handle_help: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.message_handler(commands=['contentstatus'])
def handle_contentstatus(message):
    """
    Handle /contentstatus command.
    RESTRICTED TO ADMINS ONLY.
    """
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # ---------------------------------------------------------
        # 🔒 التحقق من صلاحيات المشرف (إذا كان في مجموعة)
        # ---------------------------------------------------------
        if message.chat.type in ['group', 'supergroup']:
            if not is_user_admin(chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return
        # ---------------------------------------------------------

        schedule_config = get_schedule_config()

        status_message = """
📋 <b>جدول المحتوى المجدول</b> 📋

"""

        if not schedule_config:
            status_message += "لا يوجد جدول محتوى في content.json\n\n"
            status_message += "استخدم /sendcontent لإرسال محتوى عشوائي"
        else:
            for content_type, schedule_info in schedule_config.items():
                enabled = schedule_info.get('enabled', False)
                times = schedule_info.get('times', [])

                status_emoji = "✅" if enabled else "❌"
                status_text = "مفعّل" if enabled else "معطّل"

                status_message += f"{status_emoji} <b>{content_type}</b>\n"
                status_message += f"الحالة: {status_text}\n"

                if times:
                    times_str = "، ".join(times)
                    status_message += f"الأوقات: {times_str}\n"
                else:
                    status_message += "الأوقات: غير محدد\n"

                status_message += "\n"

            status_message += """
<b>الفئات المتاحة:</b>

• morning_athkar - أذكار الصباح
• evening_athkar - أذكار المساء
• hadiths - أحاديث عامة
• hadiths_dunya - أحاديث عن الدنيا
• hadiths_hub - أحاديث عن الحب
• hadiths_akhlaq - أحاديث عن الأخلاق
• hadiths_sabr - أحاديث عن الصبر
• hadiths_jannah - أحاديث عن الجنة
• hadiths_qudsi - أحاديث قدسية

💡 يمكنك تعديل الجدول في ملف content.json
            """

        bot.send_message(message.chat.id, status_message, parse_mode='HTML')
        logger.info(f"Content status displayed to admin {user_id}")

    except Exception as e:
        logger.error(f"Error in handle_contentstatus: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.message_handler(commands=['sendcontent'])
def handle_sendcontent(message):
    """
    Handle /sendcontent command.
    """
    try:
        # Get all available categories
        categories = get_all_content_categories()

        if not categories:
            bot.reply_to(message, "لا يوجد محتوى متاح! ❌")
            return

        # Pick a random category (excluding scheduled ones that might be disabled)
        scheduled_categories = ['morning_athkar', 'evening_athkar', 'hadiths']
        other_categories = [cat for cat in categories if cat not in scheduled_categories]

        # Try to get content from other categories first
        if other_categories and random.random() < 0.7:  # 70% chance for special categories
            category = random.choice(other_categories)
        else:
            category = random.choice(categories)

        # Get content
        content_text = get_random_content_from_category(category)

        if not content_text:
            bot.reply_to(message, "حدث خطأ في جلب المحتوى! ❌")
            return

        # Send content
        bot.send_message(message.chat.id, content_text, parse_mode='HTML')

        category_names = {
            'morning_athkar': 'أذكار الصباح',
            'evening_athkar': 'أذكار المساء',
            'hadiths': 'أحاديث',
            'hadiths_dunya': 'أحاديث عن الدنيا',
            'hadiths_hub': 'أحاديث عن الحب',
            'hadiths_akhlaq': 'أحاديث عن الأخلاق',
            'hadiths_sabr': 'أحاديث عن الصبر',
            'hadiths_jannah': 'أحاديث عن الجنة',
            'hadiths_qudsi': 'أحاديث قدسية'
        }

        category_arabic = category_names.get(category, category)

        logger.info(f"Manual content sent: {category_arabic}")

    except Exception as e:
        logger.error(f"Error in handle_sendcontent: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


# =====================================================
# HELPER FUNCTIONS FOR NEW COMMANDS
# =====================================================

def is_user_admin(chat_id: int, user_id: int) -> bool:
    """
    Check if a user is an admin in the specified chat.

    Args:
        chat_id: The chat/group ID
        user_id: The user's Telegram ID

    Returns:
        bool: True if user is admin, False otherwise
    """
    try:
        # Get list of administrators
        admins = bot.get_chat_administrators(chat_id)

        # Check if user is in admin list
        for admin in admins:
            if admin.user.id == user_id:
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}", exc_info=True)
        return False


def reset_group_data(chat_id: int) -> bool:
    """
    Reset ALL data for a specific group.

    Deletes:
    - All prayer logs for this group
    - All azan sent logs for this group
    - All content sent logs for this group
    - The group settings (will be recreated with defaults)
    - Prayer times for this group

    Args:
        chat_id: The group chat ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('BEGIN TRANSACTION')

        try:
            # Delete prayer logs for this group
            cursor.execute('DELETE FROM prayer_logs WHERE group_chat_id = ?', (chat_id,))
            prayer_logs_deleted = cursor.rowcount
            logger.info(f"Deleted {prayer_logs_deleted} prayer logs for group {chat_id}")

            # Delete azan sent logs for this group
            cursor.execute('DELETE FROM azan_sent_log WHERE group_chat_id = ?', (chat_id,))
            azan_logs_deleted = cursor.rowcount
            logger.info(f"Deleted {azan_logs_deleted} azan logs for group {chat_id}")

            # Delete content sent logs for this group (if table exists)
            try:
                cursor.execute('DELETE FROM content_sent_log WHERE group_chat_id = ?', (chat_id,))
                content_logs_deleted = cursor.rowcount
                logger.info(f"Deleted {content_logs_deleted} content logs for group {chat_id}")
            except sqlite3.OperationalError:
                # Table doesn't exist, skip
                logger.debug("content_sent_log table doesn't exist, skipping")

            # Delete prayer times for this group
            cursor.execute('DELETE FROM prayer_times_per_group WHERE group_chat_id = ?', (chat_id,))
            prayer_times_deleted = cursor.rowcount
            logger.info(f"Deleted {prayer_times_deleted} prayer times for group {chat_id}")

            # Delete the group itself
            cursor.execute('DELETE FROM groups WHERE chat_id = ?', (chat_id,))
            groups_deleted = cursor.rowcount
            logger.info(f"Deleted {groups_deleted} group settings for group {chat_id}")

            conn.commit()

            logger.info(f"Successfully reset all data for group {chat_id}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error during reset transaction: {e}", exc_info=True)
            return False

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error in reset_group_data: {e}", exc_info=True)
        return False


def get_system_status(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed system status for a specific group.

    Returns:
        dict: Dictionary containing all status information
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get overall statistics
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM groups WHERE is_active = 1')
        total_groups = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM prayer_logs')
        total_prayers = cursor.fetchone()[0]

        cursor.execute('SELECT MIN(created_at) FROM users')
        first_registration = cursor.fetchone()[0]

        # Get current group information
        cursor.execute('SELECT * FROM groups WHERE chat_id = ?', (chat_id,))
        group = cursor.fetchone()
        group_info = dict(group) if group else None

        # Get prayer times for today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT * FROM prayer_times_per_group WHERE group_chat_id = ? AND date = ?',
                      (chat_id, today))
        prayer_times = cursor.fetchone()
        prayer_times_info = dict(prayer_times) if prayer_times else None

        # Get top users in this group
        cursor.execute('''
            SELECT u.*, COUNT(pl.id) as prayer_count
            FROM users u
            INNER JOIN prayer_logs pl ON u.id = pl.user_id
            WHERE pl.group_chat_id = ?
            GROUP BY u.id
            ORDER BY u.score DESC
            LIMIT 5
        ''', (chat_id,))
        top_users = [dict(row) for row in cursor.fetchall()]

        # Get group users count
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id)
            FROM prayer_logs
            WHERE group_chat_id = ?
        ''', (chat_id,))
        group_active_users = cursor.fetchone()[0]

        # Get prayer stats for this group
        cursor.execute('''
            SELECT prayer_name, COUNT(*) as count
            FROM prayer_logs
            WHERE group_chat_id = ?
            GROUP BY prayer_name
        ''', (chat_id,))
        prayer_stats = {row['prayer_name']: row['count'] for row in cursor.fetchall()}

        # Get azan sent count
        cursor.execute('''
            SELECT COUNT(*)
            FROM azan_sent_log
            WHERE group_chat_id = ?
        ''', (chat_id,))
        azan_sent_count = cursor.fetchone()[0]

        conn.close()

        # Check API connectivity
        api_status = "غير متاح"
        try:
            response = requests.get(ALADHAN_API_BASE, params={'city': 'Riyadh', 'country': 'Saudi Arabia', 'method': '2'}, timeout=5)
            api_status = "متاح ✓" if response.status_code == 200 else f"خطأ: {response.status_code}"
        except Exception:
            api_status = "فشل الاتصال ✗"

        # Check content file
        content_status = "متاح ✓" if os.path.exists(CONTENT_FILE) else "غير موجود ✗"

        return {
            'total_users': total_users,
            'total_groups': total_groups,
            'total_prayers': total_prayers,
            'first_registration': first_registration,
            'group_info': group_info,
            'prayer_times': prayer_times_info,
            'top_users': top_users,
            'group_active_users': group_active_users,
            'prayer_stats': prayer_stats,
            'azan_sent_count': azan_sent_count,
            'api_status': api_status,
            'content_status': content_status,
            'database_path': DATABASE_PATH
        }

    except Exception as e:
        logger.error(f"Error in get_system_status: {e}", exc_info=True)
        return None


# =====================================================
# RESET ALL COMMAND HANDLERS
# =====================================================

@bot.message_handler(commands=['reset_all'])
def handle_reset_all(message):
    """
    Handle /reset_all command - Admin only.

    Shows confirmation dialog before resetting.
    """
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Check if user is admin
        if not is_user_admin(chat_id, user_id):
            bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
            return

        # Check if chat is a group
        if message.chat.type not in ['group', 'supergroup']:
            bot.reply_to(message, "⛔ هذا الأمر متاح فقط في المجموعات!")
            return

        # Send confirmation message
        warning_text = f"""
⚠️ <b>تحذير هام!</b> ⚠️

أنت على وشك حذف <b>كل البيانات</b> لهذه المجموعة:

❌ جميع سجلات الصلاة
❌ جميع سجلات الأذان
❌ جميع سجلات المحتوى
❌ إعدادات المجموعة (المدينة، التوقيت، إلخ)
❌ أوقات الصلاة المحفوظة

<b>هذا الإجراء لا يمكن التراجع عنه!</b>

هل أنت متأكد من المتابعة؟
        """

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        btn_confirm = telebot.types.InlineKeyboardButton(
            '🗑️ نعم، احذف كل شيء',
            callback_data=f'reset_confirm_{chat_id}_{user_id}'
        )
        btn_cancel = telebot.types.InlineKeyboardButton(
            '❌ إلغاء',
            callback_data=f'reset_cancel_{chat_id}'
        )
        keyboard.add(btn_confirm, btn_cancel)

        bot.send_message(chat_id, warning_text, parse_mode='HTML', reply_markup=keyboard)
        logger.info(f"Reset confirmation requested by user {user_id} in group {chat_id}")

    except Exception as e:
        logger.error(f"Error in handle_reset_all: {e}", exc_info=True)
        bot.reply_to(message, "حدث خطأ! ❌")


@bot.callback_query_handler(func=lambda call: call.data.startswith('reset_confirm_'))
def handle_reset_confirm(call):
    """
    Handle reset confirmation callback.
    """
    try:
        # Parse callback data
        parts = call.data.split('_')
        chat_id = int(parts[2])
        requesting_user_id = int(parts[3])
        current_user_id = call.from_user.id

        # Verify it's the same user who requested the reset
        if requesting_user_id != current_user_id:
            bot.answer_callback_query(call.id, "⛔ هذا الإجراء غير مصرح لك!")
            return

        # Verify admin status again
        if not is_user_admin(chat_id, current_user_id):
            bot.answer_callback_query(call.id, "⛔ هذا الأمر متاح فقط للمشرفين!")
            return

        # Perform the reset
        bot.answer_callback_query(call.id, "جاري حذف البيانات...")

        success = reset_group_data(chat_id)

        if success:
            success_message = """
✅ <b>تم إعادة التعيين بنجاح!</b>

تم حذف جميع البيانات لهذه المجموعة. للبدء من جديد:

/start - لإعداد المجموعة مرة أخرى

⚠️ تأكد من إعداد المجموعة بشكل صحيح لتعمل جميع الميزات.
            """
            bot.send_message(chat_id, success_message, parse_mode='HTML')
            logger.info(f"Group {chat_id} reset successfully by admin {current_user_id}")
        else:
            bot.send_message(chat_id, "❌ حدث خطأ أثناء إعادة التعيين. يرجى المحاولة لاحقاً.")
            logger.error(f"Failed to reset group {chat_id}")

    except Exception as e:
        logger.error(f"Error in handle_reset_confirm: {e}", exc_info=True)
        try:
            bot.send_message(call.message.chat.id, "❌ حدث خطأ! ❌")
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('reset_cancel_'))
def handle_reset_cancel(call):
    """
    Handle reset cancellation callback.
    """
    try:
        bot.answer_callback_query(call.id, "تم إلغاء العملية")
        bot.edit_message_text(
            "✅ تم إلغاء عملية إعادة التعيين.",
            call.message.chat.id,
            call.message.message_id
        )
        logger.info(f"Reset cancelled by user {call.from_user.id}")
    except Exception as e:
        logger.error(f"Error in handle_reset_cancel: {e}", exc_info=True)


# =====================================================
# STATUS COMMAND HANDLER
# =====================================================
@bot.message_handler(commands=['status'])
def handle_status(message):
    """
    Handle /status command - Show detailed system status.
    RESTRICTED TO ADMINS ONLY.
    """
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        # ---------------------------------------------------------
        # 🔒 بداية التعديل: التحقق من الصلاحيات
        # ---------------------------------------------------------
        
        # إذا كانت المحادثة في مجموعة، تأكد أن المستخدم مشرف
        if message.chat.type in ['group', 'supergroup']:
            if not is_user_admin(chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return
        
        # ---------------------------------------------------------
        # 🔓 نهاية التعديل
        # ---------------------------------------------------------

        # Get system status
        status = get_system_status(chat_id)

        if not status:
            bot.reply_to(message, "❌ حدث خطأ في جلب حالة النظام!")
            return

        # Build status message
        status_text = "📊 <b>حالة النظام التفصيلية</b>\n\n"

        # --- Overall Statistics ---
        status_text += "📈 <b>الإحصائيات العامة:</b>\n"
        status_text += f"├─ المستخدمون: {status['total_users']}\n"
        status_text += f"├─ المجموعات النشطة: {status['total_groups']}\n"
        status_text += f"├─ إجمالي الصلوات: {status['total_prayers']}\n"
        status_text += f"└─ أول تسجيل: {status['first_registration'] or 'غير متوفر'}\n\n"

        # --- Group Information ---
        status_text += "👥 <b>معلومات المجموعة الحالية:</b>\n"
        if status['group_info']:
            group = status['group_info']
            status_text += f"├─ الاسم: {group['group_name'] or 'غير محدد'}\n"
            status_text += f"├─ المدينة: {group['city']}\n"
            status_text += f"├─ البلد: {group['country']}\n"
            status_text += f"├─ التوقيت: {group['timezone']}\n"
            status_text += f"├─ طريقة الحساب: {group['calculation_method']}\n"
            status_text += f"├─ حالة الإشعارات: {'مفعلة ✓' if group['notification_enabled'] else 'معطلة ✗'}\n"
            status_text += f"└─ حالة النشاط: {'نشطة ✓' if group['is_active'] else 'غير نشطة ✗'}\n"
        else:
            status_text += "└─ ⚠️ المجموعة غير موجودة في قاعدة البيانات!\n"
        status_text += "\n"

        # --- Prayer Times ---
        status_text += "⏰ <b>أوقات الصلاة اليوم:</b>\n"
        if status['prayer_times']:
            pt = status['prayer_times']
            status_text += f"├─ الفجر: {pt['fajr_time']}\n"
            status_text += f"├─ الظهر: {pt['dhuhr_time']}\n"
            status_text += f"├─ العصر: {pt['asr_time']}\n"
            status_text += f"├─ المغرب: {pt['maghrib_time']}\n"
            status_text += f"├─ العشاء: {pt['isha_time']}\n"
            status_text += f"└─ التاريخ الهجري: {pt['hijri_date'] or 'غير متوفر'}\n"
        else:
            status_text += "└─ ⚠️ لم يتم جلب أوقات الصلاة بعد\n"
        status_text += "\n"

        # --- Group Stats ---
        status_text += "📊 <b>إحصائيات المجموعة:</b>\n"
        status_text += f"├─ المستخدمون النشطون: {status['group_active_users']}\n"
        status_text += f"└─ الأذان المرسل: {status['azan_sent_count']}\n"

        if status['prayer_stats']:
            status_text += "\n🕌 <b>الصلوات المسجلة:</b>\n"
            prayer_names_ar = {
                'fajr': 'الفجر',
                'dhuhr': 'الظهر',
                'asr': 'العصر',
                'maghrib': 'المغرب',
                'isha': 'العشاء'
            }
            for prayer, count in status['prayer_stats'].items():
                prayer_ar = prayer_names_ar.get(prayer, prayer)
                status_text += f"├─ {prayer_ar}: {count}\n"
        status_text += "\n"

        # --- Top Users ---
        status_text += "🏆 <b>أفضل المستخدمين:</b>\n"
        if status['top_users']:
            for idx, user in enumerate(status['top_users'], 1):
                medals = ['🥇', '🥈', '🥉']
                medal = medals[idx - 1] if idx <= 3 else f'{idx}.'
                username_display = f"@{user['username']}" if user['username'] else user['first_name'] or 'مستخدم'
                status_text += f"{medal} {username_display} - {user['score']} نقطة\n"
        else:
            status_text += "└─ لا يوجد مستخدمين بعد\n"
        status_text += "\n"

        # --- System Health ---
        status_text += "✅ <b>صحة النظام:</b>\n"
        status_text += f"├─ قاعدة البيانات: {'متاحة ✓' if status['database_path'] else 'غير متاحة ✗'}\n"
        status_text += f"├─ API: {status['api_status']}\n"
        status_text += f"└─ ملف المحتوى: {status['content_status']}\n"

        # Send the message
        bot.send_message(chat_id, status_text, parse_mode='HTML', disable_web_page_preview=True)
        logger.info(f"Status viewed by ADMIN {message.from_user.id} in group {chat_id}")

    except Exception as e:
        logger.error(f"Error in handle_status: {e}", exc_info=True)
        bot.reply_to(message, "❌ حدث خطأ! ❌")


# =====================================================
# CONFIGURATION VALIDATION
# =====================================================

def validate_config() -> List[str]:
    """
    Validate all configuration on startup.
    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []

    # 1. Validate BOT_TOKEN
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        errors.append("❌ BOT_TOKEN not set or using default value")
    elif len(BOT_TOKEN) < 30: # Basic check length
        errors.append(f"❌ BOT_TOKEN too short: {len(BOT_TOKEN)} characters")

    # 2. Validate DATABASE_PATH
    try:
        db_dir = os.path.dirname(DATABASE_PATH)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"❌ Database directory error: {e}")
    except Exception as e:
        errors.append(f"❌ Database path error: {e}")

    # 3. Validate content.json
    if not os.path.exists(CONTENT_FILE):
        errors.append(f"❌ Content file not found: {CONTENT_FILE}")
    else:
        try:
            with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
                content = json.load(f)

            # Check for required sections
            if 'schedule' not in content:
                errors.append("❌ Missing 'schedule' section in content.json")
            if 'categories' not in content:
                errors.append("❌ Missing 'categories' section in content.json")

            # Validate schedule structure
            if 'schedule' in content:
                for category, config in content['schedule'].items():
                    # Check required keys
                    if 'times' not in config:
                        errors.append(f"❌ Missing 'times' for category '{category}'")
                    elif not isinstance(config['times'], list):
                        errors.append(f"❌ 'times' must be a list for category '{category}'")
                    elif not config.get('times', []):
                        errors.append(f"❌ 'times' cannot be empty for category '{category}'")

                    # Validate times format
                    for time_str in config.get('times', []):
                        if not re.match(r'^\d{2}:\d{2}$', time_str):
                            errors.append(f"❌ Invalid time format '{time_str}' in '{category}' (expected: HH:MM)")

                    # Validate enabled flag
                    enabled = config.get('enabled', True)
                    if not isinstance(enabled, bool):
                        errors.append(f"❌ 'enabled' must be boolean (true/false) for category '{category}'")

        except json.JSONDecodeError as e:
            errors.append(f"❌ Content file is not valid JSON: {e}")
        except Exception as e:
            errors.append(f"❌ Content validation error: {e}")

    return errors


# =====================================================
# MAIN ENTRY POINT
# =====================================================

def main():
    """
    Main entry point for bot.
    Validates configuration, handles graceful shutdown, manages daemon threads.
    """
    # Validate configuration before starting
    errors = validate_config()
    if errors:
        logger.error("❌ Configuration validation failed:")
        for error in errors:
            logger.error(f"  {error}")
        print("\n❌ Configuration validation failed. Check bot.log for details.")
        print("\n🔧 Fix following issues:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)

    logger.info("="*60)
    logger.info("Islamic Prayer Times Telegram Bot Starting...")
    logger.info("="*60)

    # Initialize database
    initialize_database()

    # Define signal handler with closure to access thread variables
    def signal_handler(signum, frame):
        """
        Handle system signals for graceful shutdown.
        SIGINT: Ctrl+C, SIGTERM: systemd/systemd stop
        """
        logger.info(f"Received signal {signum}, shutting down...")

        # Signal all threads to stop
        shutdown_event.set()

        # Wait for threads to finish (with timeout)
        logger.info("Waiting for threads to finish...")
        time.sleep(1)

        logger.info("Graceful shutdown complete")
        sys.exit(0)

    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start azan scheduler in a separate thread
    azan_scheduler_thread = threading.Thread(target=azan_scheduler_loop, daemon=True)
    azan_scheduler_thread.start()
    logger.info("Azan scheduler thread started")

    # Start content scheduler in a separate thread
    content_scheduler_thread = threading.Thread(target=content_scheduler_loop, daemon=True)
    content_scheduler_thread.start()
    logger.info("Content scheduler thread started")

    # Start bot polling
    logger.info("Starting bot polling...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=120)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, initiating shutdown...")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Bot polling error: {e}", exc_info=True)


if __name__ == '__main__':
    main()