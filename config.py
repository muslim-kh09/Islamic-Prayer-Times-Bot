# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Configuration
===============================================
Central configuration management for the entire application.

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import os
from pathlib import Path
from typing import Dict, List

# =====================================================
# ENVIRONMENT VARIABLES
# =====================================================

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'prayer_bot.db')
DATABASE_SCHEMA_PATH = 'database_schema.sql'

# Environment
ENV = os.getenv('ENV', 'development')  # development | production

# =====================================================
# API CONFIGURATION
# =====================================================

# Aladhan API (Prayer Times)
ALADHAN_API_BASE = 'https://api.aladhan.com/v1/timingsByCity'
ALADHAN_API_TIMEOUT = 10  # seconds

# Hadeethenc API (Hadiths)
HADEETHENC_API_BASE = 'https://hadeethenc.com/api/v1/hadeeths'
HADEETHENC_API_TIMEOUT = 10  # seconds

# =====================================================
# API RETRY CONFIGURATION
# =====================================================

# Retry settings for external API calls
API_MAX_RETRIES = 3
API_RETRY_DELAY = 2  # seconds between retries
API_RETRY_BACKOFF = 2  # exponential backoff multiplier

# Generic retry configuration (backward compatibility)
MAX_RETRIES = API_MAX_RETRIES
RETRY_DELAY = API_RETRY_DELAY

# =====================================================
# SCHEDULER CONFIGURATION
# =====================================================

# Hadith sending windows per day (randomized minutes within each window)
HADITH_WINDOWS: List[Dict[str, any]] = [
    {'name': 'morning', 'start_hour': 6, 'end_hour': 8},    # 06:00-08:00
    {'name': 'midday', 'start_hour': 11, 'end_hour': 13},   # 11:00-13:00
    {'name': 'afternoon', 'start_hour': 15, 'end_hour': 17}, # 15:00-17:00
    {'name': 'evening', 'start_hour': 19, 'end_hour': 21},   # 19:00-21:00
]

# Hadith cooldown between sends (minutes)
HADITH_COOLDOWN_MINUTES = 60  # Minimum 1 hour between hadiths

# Maximum hadiths per day per group
MAX_HADITH_PER_DAY = 5

# =====================================================
# CACHE CONFIGURATION
# =====================================================

# In-memory hadith cache per category (optimized for low memory usage)
HADITH_CACHE_SIZE = 2  # Keep 2 hadiths per category (reduced from 5)
HADITH_CACHE_TTL = 86400  # 24 hours

# Prayer times cache (24 hours)
PRAYER_CACHE_TTL = 86400  # 24 hours

# =====================================================
# LOGGING CONFIGURATION
# =====================================================

LOG_FILE = 'bot_debug.log'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
LOG_BACKUP_COUNT = 5  # Keep 5 backup files
LOG_FORMAT_DETAILED = '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s'
LOG_FORMAT_SIMPLE = '%(levelname)s: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# =====================================================
# DATABASE CONFIGURATION
# =====================================================

# Database optimization settings for low-memory environments
DB_CACHE_SIZE = -5000  # 5MB cache (reduced from 10MB)
DB_SYNCHRONOUS = 'NORMAL'  # Faster than FULL, safer than OFF

# =====================================================
# PRAYER NAMES MAPPING
# =====================================================

PRAYER_NAMES_ARABIC: Dict[str, str] = {
    'Fajr': 'الفجر',
    'Dhuhr': 'الظهر',
    'Asr': 'العصر',
    'Maghrib': 'المغرب',
    'Isha': 'العشاء'
}

PRAYER_NAMES_ENGLISH: Dict[str, str] = {
    'فجر': 'Fajr',
    'ظهر': 'Dhuhr',
    'عصر': 'Asr',
    'مغرب': 'Maghrib',
    'عشاء': 'Isha'
}

# =====================================================
# CITY CONFIGURATION
# =====================================================

# Available cities for selection
CITIES_CONFIG: List[Dict[str, str]] = [
    {'arabic': 'الرياض', 'english': 'Riyadh', 'country': 'Saudi Arabia', 'timezone': 'Asia/Riyadh'},
    {'arabic': 'مكة', 'english': 'Mecca', 'country': 'Saudi Arabia', 'timezone': 'Asia/Riyadh'},
    {'arabic': 'المدينة', 'english': 'Medina', 'country': 'Saudi Arabia', 'timezone': 'Asia/Riyadh'},
    {'arabic': 'القاهرة', 'english': 'Cairo', 'country': 'Egypt', 'timezone': 'Africa/Cairo'},
    {'arabic': 'الجزائر', 'english': 'Algiers', 'country': 'Algeria', 'timezone': 'Africa/Algiers'},
    {'arabic': 'الرباط', 'english': 'Rabat', 'country': 'Morocco', 'timezone': 'Africa/Casablanca'},
    {'arabic': 'تونس', 'english': 'Tunis', 'country': 'Tunisia', 'timezone': 'Africa/Tunis'},
    {'arabic': 'عمّان', 'english': 'Amman', 'country': 'Jordan', 'timezone': 'Asia/Amman'},
    {'arabic': 'بيروت', 'english': 'Beirut', 'country': 'Lebanon', 'timezone': 'Asia/Beirut'},
    {'arabic': 'دمشق', 'english': 'Damascus', 'country': 'Syria', 'timezone': 'Asia/Damascus'},
    {'arabic': 'بغداد', 'english': 'Baghdad', 'country': 'Iraq', 'timezone': 'Asia/Baghdad'},
    {'arabic': 'الكويت', 'english': 'Kuwait City', 'country': 'Kuwait', 'timezone': 'Asia/Kuwait'},
    {'arabic': 'الدوحة', 'english': 'Doha', 'country': 'Qatar', 'timezone': 'Asia/Qatar'},
    {'arabic': 'أبوظبي', 'english': 'Abu Dhabi', 'country': 'UAE', 'timezone': 'Asia/Dubai'},
    {'arabic': 'دبي', 'english': 'Dubai', 'country': 'UAE', 'timezone': 'Asia/Dubai'},
    {'arabic': 'موسكو', 'english': 'Moscow', 'country': 'Russia', 'timezone': 'Europe/Moscow'},
    {'arabic': 'لندن', 'english': 'London', 'country': 'UK', 'timezone': 'Europe/London'},
    {'arabic': 'نيويورك', 'english': 'New York', 'country': 'USA', 'timezone': 'America/New_York'},
]

# =====================================================
# CALCULATION METHOD CONFIGURATION
# =====================================================

# Available prayer time calculation methods
# These are standard methods used by Aladhan API
CALCULATION_METHODS: List[Dict[str, any]] = [
    {'id': 0, 'arabic': 'إثنا عشرية', 'english': 'Ithna Ashari', 'description': 'جعفری / شيعه اثنی عشریه'},
    {'id': 1, 'arabic': 'جامعة العلوم الإسلامية، كراتشي', 'english': 'University of Islamic Sciences, Karachi', 'description': 'جامعة كراتشي للعلوم الإسلامية'},
    {'id': 2, 'arabic': 'الجمعية الإسلامية بأمريكا الشمالية', 'english': 'Islamic Society of North America (ISNA)', 'description': 'طريقة ISNA - الافتراضية'},
    {'id': 3, 'arabic': 'رابطة العالم الإسلامي', 'english': 'Muslim World League', 'description': 'رابطة العالم الإسلامي'},
    {'id': 4, 'arabic': 'جامعة أم القرى، مكة', 'english': 'Umm Al-Qura University, Makkah', 'description': 'جامعة أم القرى - مكة المكرمة'},
    {'id': 5, 'arabic': 'الهيئة المصرية العامة للمساحة', 'english': 'Egyptian General Authority of Survey', 'description': 'الهيئة المصرية العامة للمساحة'},
    {'id': 7, 'arabic': 'معهد الجيوفيزياء، جامعة طهران', 'english': 'Institute of Geophysics, University of Tehran', 'description': 'جامعة طهران'},
    {'id': 8, 'arabic': 'منطقة الخليج', 'english': 'Gulf Region', 'description': 'منطقة الخليج'},
    {'id': 9, 'arabic': 'الكويت', 'english': 'Kuwait', 'description': 'دولة الكويت'},
    {'id': 10, 'arabic': 'قطر', 'english': 'Qatar', 'description': 'دولة قطر'},
    {'id': 11, 'arabic': 'مجلس أوقاف سنغافورة', 'english': 'Majlis Ugama Islam Singapura, Singapore', 'description': 'سنغافورة'},
    {'id': 12, 'arabic': 'المنظمة الإسلامية الفرنسية', 'english': 'Union Organization islamic de France', 'description': 'فرنسا'},
    {'id': 13, 'arabic': 'رئاسة الشؤون الدينية، تركيا', 'english': 'Diyanet İşleri Başkanlığı, Turkey', 'description': 'تركيا - رئاسة الشؤون الدينية'},
    {'id': 14, 'arabic': 'الإدارة الروحية للمسلمين في روسيا', 'english': 'Spiritual Administration of Muslims of Russia', 'description': 'روسيا'},
]

# =====================================================
# VALIDATION FUNCTIONS
# =====================================================

def validate_config() -> List[str]:
    """
    Validate all configuration on startup.

    Returns:
        List[str]: List of error messages (empty if valid)
    """
    errors: List[str] = []

    # 1. Validate BOT_TOKEN
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        errors.append("❌ BOT_TOKEN not set or using default value")
    elif len(BOT_TOKEN) < 30:  # Basic length check
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

    # 3. Validate API URLs
    if not ALADHAN_API_BASE.startswith('https://'):
        errors.append("❌ ALADHAN_API_BASE must use HTTPS")
    if not HADEETHENC_API_BASE.startswith('https://'):
        errors.append("❌ HADEETHENC_API_BASE must use HTTPS")

    return errors


def is_valid_config() -> bool:
    """
    Quick check if configuration is valid.

    Returns:
        bool: True if configuration is valid
    """
    return len(validate_config()) == 0
