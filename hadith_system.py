# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Hadith System (Optimized)
===========================================================
Optimized hadith fetching with database-based cooldown tracking.

Critical Fixes (v2.0.0):
- Replaced dangerous log file reading with database queries
- Reduced memory cache size from 5 to 2 per category
- Added proper cooldown tracking via database
- Improved error handling and fallback mechanisms

Optimizations:
- Lazy loading of hadith data
- Smart cache management
- Reduced memory footprint for low-memory servers

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import requests
import random
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

import config
from logger_config import logger
from smart_hadith_engine import get_engine
# --- التعديل هنا: تغيير اسم الدالة المستوردة لتجنب التضارب ---
from database import (
    get_cached_hadith as db_get_cached_hadith,
    cache_hadith as db_cache_hadith,
    update_hadith_usage,
    log_hadith_sent,
    get_last_hadith_sent_time,
    get_hadiths_sent_today_count
)


# =====================================================
# LOCAL FALLBACK
# =====================================================

FALLBACK_FILE = "hadiths_fallback.json"


def fetch_local_fallback_hadith() -> Optional[str]:
    """
    Get a hadith from local fallback file when API fails completely.
    This provides offline capability when API is unavailable.
    """
    try:
        if not os.path.exists(FALLBACK_FILE):
            logger.warning(f"Fallback file {FALLBACK_FILE} not found")
            return None

        with open(FALLBACK_FILE, 'r', encoding='utf-8') as f:
            hadiths = json.load(f)

        if not hadiths:
            return None

        hadith = random.choice(hadiths)

        return f"""
🕌 <b>من مشكاة النبوة (أرشيف)</b>
ــــــــــــــــــــــــــــــــــــــــــــــــ

🍃 <b>قال رسول الله ﷺ:</b>
{hadith.get('hadith_text', '')}

📚 <b>الراوي/المصدر:</b> {hadith.get('source', '')}

💡 <b>فائدة:</b>
{hadith.get('explanation', '')}
"""
    except Exception as e:
        logger.error(f"Error reading local fallback: {e}")
        return None


# =====================================================
# CORE DATA FUNCTIONS (Internal)
# =====================================================

def _get_data_from_cache(category_id: str) -> Optional[List[Dict]]:
    """
    Internal function: Get cached hadiths from database.

    Uses database cache instead of in-memory cache to reduce RAM usage.
    """
    try:
        # Check Database cache
        # --- التعديل هنا: استخدام الاسم الجديد للدالة ---
        cached = db_get_cached_hadith(category_id, limit=config.HADITH_CACHE_SIZE)

        if cached:
            logger.debug(f"Using cached hadiths for category {category_id} ({len(cached)} items)")
            return cached

        return None
    except Exception as e:
        logger.error(f"Error in _get_data_from_cache: {e}")
        return None


def fetch_hadith_from_api(category_id: str) -> Optional[Dict]:
    """
    Fetch from API only if cache is empty.

    Args:
        category_id: The category ID to fetch hadiths for

    Returns:
        dict: Hadith data or None if failed
    """
    try:
        # Check cache first
        cached = _get_data_from_cache(category_id)
        if cached:
            return random.choice(cached)

        # API Fetch logic
        logger.debug(f"Fetching from API for category {category_id}")
        list_url = f"{config.HADEETHENC_API_BASE}/list/"

        # Try random page first (for variety)
        try:
            response = requests.get(
                list_url,
                params={'language': 'ar', 'category_id': category_id, 'page': random.randint(1, 5), 'per_page': 10},
                timeout=5
            )
            data = response.json()
            hadiths_list = data.get('data', [])
        except Exception:
            # Fallback to page 1 if random page fails
            hadiths_list = []

        # Retry page 1 if empty
        if not hadiths_list:
            response = requests.get(
                list_url,
                params={'language': 'ar', 'category_id': category_id, 'page': 1, 'per_page': 10},
                timeout=5
            )
            hadiths_list = response.json().get('data', [])

        if hadiths_list:
            hadith_summary = random.choice(hadiths_list)
            hadith_id = hadith_summary['id']

            # Get Details
            details_response = requests.get(
                f"{config.HADEETHENC_API_BASE}/one/",
                params={'language': 'ar', 'id': hadith_id},
                timeout=5
            )
            details = details_response.json()

            hadith_obj = {
                'hadith_id': hadith_id,
                'id': hadith_id,
                'hadith_text': details.get('title', ''),
                'attribution': details.get('attribution', ''),
                'grade': details.get('grade', ''),
                'explanation': details.get('explanation', '')
            }

            # Save to Cache (Database)
            db_cache_hadith(
                hadith_id=str(hadith_obj['id']),
                category_id=category_id,
                hadith_text=hadith_obj['hadith_text'],
                attribution=hadith_obj['attribution'],
                grade=hadith_obj['grade'],
                explanation=hadith_obj['explanation'],
                source_url=f"https://hadeethenc.com/ar/browse/hadith/{hadith_id}"
            )

            return hadith_obj

        return None

    except Exception as e:
        logger.error(f"Error fetching from API: {e}")
        return None


def cache_single_hadith(category_id: str, hadith: dict) -> bool:
    """
    Save hadith to database cache.

    Note: We use database instead of in-memory cache to reduce RAM usage.

    Args:
        category_id: Category ID
        hadith: Hadith dictionary

    Returns:
        bool: True if cached successfully
    """
    try:
        # Save to Database
        db_cache_hadith(
            hadith_id=str(hadith.get('id', hadith.get('hadith_id'))),
            category_id=category_id,
            hadith_text=hadith.get('hadith_text', ''),
            attribution=hadith.get('attribution', ''),
            grade=hadith.get('grade', ''),
            explanation=hadith.get('explanation', '')
        )
        return True
    except Exception as e:
        logger.error(f"Cache save error: {e}")
        return False


# =====================================================
# PUBLIC INTERFACE (Formatting & Logic)
# =====================================================

def format_hadith_message(hadith: dict) -> str:
    """
    Format the hadith dictionary into a beautiful message string.

    Args:
        hadith: Hadith dictionary

    Returns:
        str: Formatted HTML message
    """
    try:
        if not hadith or not isinstance(hadith, dict):
            return fetch_local_fallback_hadith() or "عذراً، حدث خطأ في جلب الحديث."

        hid = hadith.get('id', hadith.get('hadith_id', '0'))
        text = hadith.get('hadith_text', '')
        exp = hadith.get('explanation', '')

        msg = f"""
🕌 <b>من مشكاة النبوة</b>
ــــــــــــــــــــــــــــــــــــــــــــــــ

🍃 <b>قال رسول الله ﷺ:</b>
{text}

📚 <b>الدرجة:</b> {hadith.get('grade', '')}
✅ <b>الراوي:</b> {hadith.get('attribution', '')}

💡 <b>إضاءة:</b>
{exp[:600] + '...' if len(exp) > 600 else exp}

ــــــــــــــــــــــــــــــــــــــــــــــــ
🔗 <a href="https://hadeethenc.com/ar/browse/hadith/{hid}">قراءة الشرح كاملاً</a>
"""
        return msg
    except Exception as e:
        logger.error(f"Format error: {e}")
        return "خطأ في تنسيق الحديث."


def fetch_smart_hadith(chat_id: int = 0) -> Optional[str]:
    """
    Main function called by the bot to get a formatted hadith message.

    Includes:
    - Cooldown check (database-based, no log file reading!)
    - Daily limit check
    - Smart category selection
    - Fallback mechanisms

    Args:
        chat_id: Group chat ID (0 for manual commands)

    Returns:
        str: Formatted hadith message or None
    """
    try:
        # =====================================================
        # 1. Check cooldown using database (NOT log file!)
        # =====================================================
        last_sent_time = get_last_hadith_sent_time(chat_id, config.HADITH_COOLDOWN_MINUTES)

        if last_sent_time:
            time_diff = (datetime.now() - last_sent_time).total_seconds()
            if time_diff < config.HADITH_COOLDOWN_MINUTES * 60:
                logger.debug(f"Cooldown active for group {chat_id} ({int(time_diff/60)}min elapsed)")
                return None  # Cooldown not passed

        # =====================================================
        # 2. Check daily limit
        # =====================================================
        today = datetime.now().strftime('%Y-%m-%d')
        today_count = get_hadiths_sent_today_count(chat_id, today)

        if today_count >= config.MAX_HADITH_PER_DAY:
            logger.debug(f"Daily limit reached for group {chat_id} ({today_count} sent)")
            return None

        # =====================================================
        # 3. Select Category
        # =====================================================
        hadith_engine = get_engine()
        current_hour = datetime.now().hour
        category_id = hadith_engine.select_category(hour=current_hour, group_id=chat_id)

        if not category_id:
            category_id = '1'  # Fallback to first category

        # =====================================================
        # 4. Get Hadith Data
        # =====================================================
        hadith_data = None
        cached_list = _get_data_from_cache(category_id)

        if cached_list:
            # Use cached hadith
            hadith_data = random.choice(cached_list)
            logger.debug(f"Using cached hadith from category {category_id}")
        else:
            # Fetch from API
            hadith_data = fetch_hadith_from_api(category_id)
            if hadith_data:
                logger.debug(f"Fetched new hadith from API for category {category_id}")

        # =====================================================
        # 5. Format and Return
        # =====================================================
        if hadith_data:
            # Log hadith as sent
            log_hadith_sent(chat_id, category_id, 'manual')

            # Update usage count in cache
            update_hadith_usage(str(hadith_data.get('id', hadith_data.get('hadith_id'))))

            # Return formatted message
            return format_hadith_message(hadith_data)

        # Fallback to local file
        return fetch_local_fallback_hadith()

    except Exception as e:
        logger.error(f"Smart fetch critical error: {e}", exc_info=True)
        return fetch_local_fallback_hadith()


# =====================================================
# COMPATIBILITY LAYER (Fixes ImportError)
# =====================================================

def get_cached_hadith(chat_id: int = 0, window_name: str = None) -> Optional[str]:
    """
    Wrapper for scheduler compatibility.
    Redirects old function calls to the new smart system.

    Args:
        chat_id: Group chat ID
        window_name: Time window name (for compatibility)

    Returns:
        str: Formatted hadith message
    """
    return fetch_smart_hadith(chat_id)
