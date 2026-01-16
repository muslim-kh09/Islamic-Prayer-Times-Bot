# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Prayer API Module
===================================================
Integration with Aladhan API for prayer times.

Includes API resilience with retry logic and exponential backoff.

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import requests
import time
from typing import Optional, Dict
from datetime import datetime
from pytz import timezone

import config
from database import get_group, save_group_prayer_times, get_group_prayer_times
from logger_config import logger


# =====================================================
# RETRY HELPER
# =====================================================

def retry_with_backoff(func, url: str, params: Dict = None, max_retries: int = None,
                     delay: int = None, backoff: int = None, timeout: int = None) -> Optional[Dict]:
    """
    Execute function with retry logic and exponential backoff.
    
    Args:
        func: Function to retry (requests.get, requests.post)
        url: URL to request
        params: Query parameters
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Exponential backoff multiplier
        timeout: Request timeout (seconds)
    
    Returns:
        Response data or None if all retries failed
    """
    if max_retries is None:
        max_retries = config.API_MAX_RETRIES if hasattr(config, 'API_MAX_RETRIES') else 3
    if delay is None:
        delay = config.API_RETRY_DELAY if hasattr(config, 'API_RETRY_DELAY') else 2
    if backoff is None:
        backoff = config.API_RETRY_BACKOFF if hasattr(config, 'API_RETRY_BACKOFF') else 2
    if timeout is None:
        timeout = config.ALADHAN_API_TIMEOUT if hasattr(config, 'ALADHAN_API_TIMEOUT') else 30
    
    for attempt in range(max_retries):
        try:
            response = func(url, params=params, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                wait_time = delay * (backoff ** attempt)
                logger.warning(f"API rate limit hit (attempt {attempt + 1}), waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif response.status_code >= 500:  # Server error
                wait_time = delay * (backoff ** attempt)
                logger.warning(f"API server error (attempt {attempt + 1}), waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"API request failed with status {response.status_code}")
                return None
                
        except requests.Timeout:
            wait_time = delay * (backoff ** attempt)
            logger.warning(f"API timeout (attempt {attempt + 1}), waiting {wait_time}s...")
            time.sleep(wait_time)
            if attempt == max_retries - 1:
                logger.error(f"API request failed after {max_retries} timeout attempts")
            continue
        except requests.ConnectionError:
            wait_time = delay * (backoff ** attempt)
            logger.warning(f"API connection error (attempt {attempt + 1}), waiting {wait_time}s...")
            time.sleep(wait_time)
            if attempt == max_retries - 1:
                logger.error(f"API request failed after {max_retries} connection attempts")
            continue
        except Exception as e:
            logger.error(f"API request failed with unexpected error: {e}")
            return None
    
    logger.error(f"API request failed after {max_retries} attempts")
    return None


# =====================================================
# API FUNCTIONS
# =====================================================

def fetch_and_save_prayer_times(chat_id: int) -> Optional[Dict[str, str]]:
    """
    Fetch prayer times from API and save to database for a specific group.
    """
    try:
        # Get group settings
        group = get_group(chat_id)

        if not group:
            logger.warning(f"Group {chat_id} not found in database")
            return None

        city = group['city']
        country = group['country']
        method = group['calculation_method']
        tz_str = group['timezone']

        # Determine correct date based on group timezone
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

        # Use retry logic with exponential backoff
        data = retry_with_backoff(
            func=requests.get,
            url=config.ALADHAN_API_BASE,
            params=params,
            timeout=config.ALADHAN_API_TIMEOUT if hasattr(config, 'ALADHAN_API_TIMEOUT') else 30
        )

        if not data:
            logger.error(f"Failed to fetch prayer times after {config.API_MAX_RETRIES if hasattr(config, 'API_MAX_RETRIES') else 3} attempts")
            return None

        if data.get('code') != 200:
            logger.error(f"API returned error: {data}")
            return None

        # Extract prayer times
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


def get_current_prayer(chat_id: int) -> Optional[Dict[str, any]]:
    """
    Get the current prayer based on current time.

    Handles edge cases:
    - Midnight boundary (after Isha, before Fajr)
    - DST transitions
    - Missing prayer times

    Args:
        chat_id: The group chat ID

    Returns:
        dict: Current prayer info {'name': 'Fajr', 'name_arabic': 'الفجر', 'time': '05:30'} or None
    """
    try:
        from utils import parse_time

        # Get group settings
        group = get_group(chat_id)
        if not group:
            return None

        # Get today's prayer times
        today = datetime.now().strftime('%Y-%m-%d')
        prayer_times_data = get_group_prayer_times(chat_id, today)

        if not prayer_times_data:
            logger.warning(f"No prayer times for group {chat_id} today ({today})")
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

        # Sort prayers by time
        sorted_prayers = sorted(prayer_times, key=lambda x: x['total_minutes'])

        # Edge Case 1: Before Fajr (midnight to early morning)
        # If current time is before the first prayer (Fajr),
        # return the last prayer (Isha) so users can still log it
        # This handles the "night before Fajr" period
        if current_total_minutes < sorted_prayers[0]['total_minutes']:
            logger.debug(f"Current time ({current_hour:02d}:{current_minute:02d}) is before Fajr")
            # Return Isha as the last prayer of the day
            return sorted_prayers[-1]

        # Normal case: Find current prayer
        # It's the last prayer where time <= current time
        # AND current time < next prayer time (if exists)
        current_prayer = None

        for i in range(len(sorted_prayers)):
            prayer = sorted_prayers[i]
            next_prayer = sorted_prayers[i + 1] if i < len(sorted_prayers) - 1 else None

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
