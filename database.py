# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Database Module
=================================================
All database operations with thread-safe connection pooling.

Optimizations:
- Thread-local connection pooling (one connection per thread)
- WAL mode enabled for concurrent read/write
- Context-managed transactions with auto-commit/rollback
- No connection leaks
- Optimized cache size for low-memory environments

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import sqlite3
from typing import Optional, Dict, List, Any
from datetime import datetime
from contextlib import contextmanager
import threading

import config
from logger_config import logger


# =====================================================
# DATABASE CONNECTION POOLING
# =====================================================

# Thread-local storage for connections (one connection per thread)
_local = threading.local()


def _get_thread_connection() -> sqlite3.Connection:
    """
    Get or create a connection for the current thread.
    Enables WAL mode and optimizations on first use.
    """
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(
            config.DATABASE_PATH,
            check_same_thread=False  # Allow sharing across scheduler threads
        )
        _local.conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        _local.conn.execute('PRAGMA journal_mode=WAL')
        _local.conn.execute(f'PRAGMA synchronous={config.DB_SYNCHRONOUS}')
        _local.conn.execute(f'PRAGMA cache_size={config.DB_CACHE_SIZE}')
        _local.conn.execute('PRAGMA temp_store=MEMORY')  # Memory for temp tables
        _local.conn.execute('PRAGMA mmap_size=268435456')  # 256MB mmap

        logger.debug(f"Created new DB connection for thread {threading.current_thread().name}")

    return _local.conn


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Ensures proper transaction handling and connection management.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            results = cursor.fetchall()
    """
    conn = _get_thread_connection()

    try:
        # Begin transaction
        conn.execute('BEGIN')
        yield conn
        # Auto-commit on success
        conn.commit()
    except Exception as e:
        # Rollback on error
        try:
            conn.rollback()
        except Exception:
            pass  # Rollback might fail if connection is broken
        logger.error(f"Database transaction error: {e}", exc_info=False)
        raise


def close_all_connections():
    """
    Close all database connections (call on shutdown).
    Note: In thread-local storage, this only closes current thread's connection.
    Other threads will close their connections on completion.
    """
    if hasattr(_local, 'conn') and _local.conn:
        try:
            _local.conn.close()
            logger.info("Closed database connection for current thread")
        except Exception as e:
            logger.error(f"Error closing DB connection: {e}", exc_info=False)
        _local.conn = None


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def initialize_database():
    """
    Initialize the database with required tables if they don't exist.
    Runs once on startup, then connection pooling takes over.
    """
    try:
        # Use context manager for initialization
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row['name'] for row in cursor.fetchall()}

            logger.info(f"Existing tables: {len(existing_tables)}")

            # Read and execute schema file
            schema_path = config.DATABASE_SCHEMA_PATH
            if schema_path and hasattr(config, 'DATABASE_SCHEMA_PATH'):
                import os
                if os.path.exists(schema_path):
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema = f.read()

                    # Execute each statement
                    for statement in schema.split(';'):
                        if statement.strip():
                            try:
                                cursor.execute(statement)
                            except sqlite3.Error as e:
                                if "already exists" not in str(e) and "duplicate" not in str(e).lower():
                                    logger.error(f"Schema error: {e}", exc_info=False)

                    logger.info("Database initialized successfully from schema file")
                    return

            # If schema file not found, create tables manually
            logger.warning(f"Schema file {schema_path} not found. Creating tables manually...")
            create_tables_manually(cursor)
            logger.info("Database initialized successfully with manual tables")

    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise


def create_tables_manually(cursor):
    """
    Create database tables manually if schema file is not available.
    Updated to include ALL required tables including hadith_send_log.
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

    # Content sent log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_chat_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            sent_date TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE,
            UNIQUE(group_chat_id, content_type, sent_date)
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

    # Broadcast queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broadcast_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            target_chat_id INTEGER,
            scheduled_at TIMESTAMP,
            sent_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # === Categories Index (Critical for Hadith System) ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories_index (
            id INTEGER PRIMARY KEY,
            category_id TEXT NOT NULL UNIQUE,
            category_name_ar TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # === Category Stats ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS category_stats (
            category_id TEXT NOT NULL,
            total_cached INTEGER DEFAULT 0,
            last_prefetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (category_id),
            FOREIGN KEY (category_id) REFERENCES categories_index(category_id) ON DELETE CASCADE
        )
    ''')

    # === Hadith Cache ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hadith_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hadith_id TEXT NOT NULL UNIQUE,
            category_id TEXT NOT NULL,
            hadith_text TEXT NOT NULL,
            attribution TEXT,
            grade TEXT,
            explanation TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usage_count INTEGER DEFAULT 0
        )
    ''')

    # === NEW: Hadith Send Log (Critical Fix - replaces log file reading) ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hadith_send_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            category_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            window_name TEXT,
            PRIMARY KEY (group_id, sent_at)
        )
    ''')

    # === Create Indexes for Performance ===
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_sent_log_group_date ON content_sent_log(group_chat_id, sent_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prayer_times_group_date ON prayer_times_per_group(group_chat_id, date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_azan_sent_log_group_date ON azan_sent_log(group_chat_id, prayer_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prayer_logs_user_date ON prayer_logs(user_id, prayer_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_score ON users(score DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hadith_cache_category ON hadith_cache(category_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hadith_cache_usage ON hadith_cache(usage_count DESC, last_used_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_index_active ON categories_index(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category_stats_prefetch ON category_stats(last_prefetched_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hadith_send_log_group_time ON hadith_send_log(group_id, sent_at DESC)')


# =====================================================
# USER OPERATIONS
# =====================================================

def get_or_create_user(telegram_id: int, username: str = None,
                       first_name: str = None, last_name: str = None) -> int:
    """
    Get existing user or create new one (with transaction).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

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
                logger.debug(f"Updated user {telegram_id}")
            else:
                # Create new user
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                user_id = cursor.lastrowid
                logger.debug(f"Created user {telegram_id}")

            return user_id

    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}", exc_info=False)
        raise


def get_top_users(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top users by score.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM users
                ORDER BY score DESC
                LIMIT ?
            ''', (limit,))

            users = [dict(row) for row in cursor.fetchall()]
            return users

    except Exception as e:
        logger.error(f"Error in get_top_users: {e}", exc_info=False)
        return []


# =====================================================
# GROUP OPERATIONS
# =====================================================

def get_group(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Get group settings by chat ID.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM groups WHERE chat_id = ?
            ''', (chat_id,))

            group = cursor.fetchone()
            if group:
                return dict(group)
            return None

    except Exception as e:
        logger.error(f"Error in get_group: {e}", exc_info=False)
        return None


def get_all_active_groups() -> List[Dict[str, Any]]:
    """
    Get all active groups.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM groups WHERE is_active = 1
            ''')

            groups = [dict(row) for row in cursor.fetchall()]
            return groups

    except Exception as e:
        logger.error(f"Error in get_all_active_groups: {e}", exc_info=False)
        return []


def create_group(chat_id: int, group_name: str, city: str = 'Riyadh',
                country: str = 'Saudi Arabia', timezone: str = 'Asia/Riyadh') -> bool:
    """
    Create a new group entry.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO groups (chat_id, group_name, city, country, timezone)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, group_name, city, country, timezone))

            logger.info(f"Group {chat_id} created successfully")
            return True

    except Exception as e:
        logger.error(f"Error in create_group: {e}", exc_info=False)
        return False


def update_group(chat_id: int, city: str, country: str, timezone: str) -> bool:
    """
    Update group settings.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE groups
                SET city = ?, country = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            ''', (city, country, timezone, chat_id))

            logger.info(f"Group {chat_id} updated successfully")
            return True

    except Exception as e:
        logger.error(f"Error in update_group: {e}", exc_info=False)
        return False


def update_group_calculation_method(chat_id: int, calculation_method: int) -> bool:
    """
    Update group's prayer time calculation method.

    Args:
        chat_id: The group chat ID
        calculation_method: The calculation method ID (0-14)

    Returns:
        bool: True if updated successfully
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE groups
                SET calculation_method = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            ''', (calculation_method, chat_id))

            logger.info(f"Group {chat_id} calculation method updated to {calculation_method}")
            return True

    except Exception as e:
        logger.error(f"Error in update_group_calculation_method: {e}", exc_info=False)
        return False


def delete_group(chat_id: int) -> bool:
    """
    Delete a group (cascades to related tables).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM groups WHERE chat_id = ?', (chat_id,))

            logger.info(f"Group {chat_id} deleted successfully")
            return True

    except Exception as e:
        logger.error(f"Error in delete_group: {e}", exc_info=False)
        return False


# =====================================================
# PRAYER TIMES OPERATIONS
# =====================================================

def save_group_prayer_times(chat_id: int, date: str, prayer_times: Dict[str, str],
                            hijri_date: str = None) -> bool:
    """
    Save prayer times for a specific group.
    """
    try:
        with get_db_connection() as conn:
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

            logger.debug(f"Saved prayer times for group {chat_id} on {date}")
            return True

    except Exception as e:
        logger.error(f"Error in save_group_prayer_times: {e}", exc_info=False)
        return False


def get_group_prayer_times(chat_id: int, date: str) -> Optional[Dict[str, Any]]:
    """
    Get prayer times for a specific group on a specific date.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM prayer_times_per_group
                WHERE group_chat_id = ? AND date = ?
            ''', (chat_id, date))

            result = cursor.fetchone()
            if result:
                return dict(result)
            return None

    except Exception as e:
        logger.error(f"Error in get_group_prayer_times: {e}", exc_info=False)
        return None


# =====================================================
# AZAN LOG OPERATIONS
# =====================================================

def has_azan_sent_today(chat_id: int, prayer_name: str, date: str) -> bool:
    """
    Check if azan has already been sent for a specific prayer on a specific date.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 1 FROM azan_sent_log
                WHERE group_chat_id = ? AND prayer_name = ? AND prayer_date = ?
            ''', (chat_id, prayer_name, date))

            result = cursor.fetchone()
            return result is not None

    except Exception as e:
        logger.error(f"Error in has_azan_sent_today: {e}", exc_info=False)
        return False


def log_azan_sent(chat_id: int, prayer_name: str, date: str) -> bool:
    """
    Log that azan has been sent for a specific prayer on a specific date.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Use INSERT OR IGNORE to handle unique constraint
            cursor.execute('''
                INSERT OR IGNORE INTO azan_sent_log
                (group_chat_id, prayer_name, prayer_date, sent_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (chat_id, prayer_name, date))

            logger.debug(f"Logged azan sent for {prayer_name} in group {chat_id} on {date}")
            return True

    except Exception as e:
        logger.error(f"Error in log_azan_sent: {e}", exc_info=False)
        return False


# =====================================================
# PRAYER LOG OPERATIONS
# =====================================================

def record_user_prayer(user_id: int, group_chat_id: int, prayer_name: str, date: str) -> bool:
    """
    Record a user's completed prayer and update their score (with transaction).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if prayer already recorded for today
            cursor.execute('''
                SELECT 1 FROM prayer_logs
                WHERE user_id = ? AND group_chat_id = ? AND prayer_name = ? AND prayer_date = ?
            ''', (user_id, group_chat_id, prayer_name, date))

            if cursor.fetchone():
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

            logger.info(f"Recorded prayer {prayer_name} for user {user_id}")
            return True

    except Exception as e:
        logger.error(f"Error in record_user_prayer: {e}", exc_info=False)
        return False


# =====================================================
# CONTENT LOG OPERATIONS
# =====================================================

def is_content_sent_today(chat_id: int, content_type: str, date: str) -> bool:
    """
    Check if content was already sent today to a group.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 1 FROM content_sent_log
                WHERE group_chat_id = ? AND content_type = ? AND sent_date = ?
            ''', (chat_id, content_type, date))

            result = cursor.fetchone()
            return result is not None

    except Exception as e:
        logger.error(f"Error in is_content_sent_today: {e}", exc_info=False)
        return False


def mark_content_as_sent(chat_id: int, content_type: str, date: str) -> bool:
    """
    Mark content as sent for today.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO content_sent_log
                (group_chat_id, content_type, sent_date)
                VALUES (?, ?, ?)
            ''', (chat_id, content_type, date))

            return True

    except Exception as e:
        logger.error(f"Error in mark_content_as_sent: {e}", exc_info=False)
        return False


# =====================================================
# HADITH SEND LOG OPERATIONS (NEW - replaces log file reading)
# =====================================================

def log_hadith_sent(group_id: int, category_id: str, window_name: str) -> bool:
    """
    Log that a hadith was sent to a group.
    This replaces the dangerous log file reading approach.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO hadith_send_log (group_id, category_id, window_name, sent_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (group_id, category_id, window_name))

            logger.debug(f"Logged hadith sent to group {group_id} (category: {category_id}, window: {window_name})")
            return True

    except Exception as e:
        logger.error(f"Error in log_hadith_sent: {e}", exc_info=False)
        return False


def get_last_hadith_sent_time(group_id: int, cooldown_minutes: int = 60) -> Optional[datetime]:
    """
    Get the timestamp of the last hadith sent to a group.
    Used to enforce cooldown period.

    Args:
        group_id: The group chat ID
        cooldown_minutes: Minutes to look back for cooldown check

    Returns:
        datetime: Timestamp of last hadith, or None if no hadith sent recently
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Query for the most recent hadith sent within the cooldown period
            cursor.execute('''
                SELECT sent_at FROM hadith_send_log
                WHERE group_id = ?
                  AND sent_at > datetime('now', '-' || ? || ' minutes')
                ORDER BY sent_at DESC
                LIMIT 1
            ''', (group_id, cooldown_minutes))

            result = cursor.fetchone()
            if result:
                # Parse the timestamp
                sent_at_str = result['sent_at']
                try:
                    # Handle different timestamp formats
                    if 'T' in sent_at_str:
                        # ISO format: 2024-01-01T12:00:00
                        return datetime.fromisoformat(sent_at_str)
                    else:
                        # SQLite format: 2024-01-01 12:00:00
                        return datetime.strptime(sent_at_str, '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logger.error(f"Error parsing hadith timestamp: {e}", exc_info=False)
                    return None
            return None

    except Exception as e:
        logger.error(f"Error in get_last_hadith_sent_time: {e}", exc_info=False)
        return None


def get_hadiths_sent_today_count(group_id: int, date: str) -> int:
    """
    Get the number of hadiths sent to a group on a specific date.
    Used to enforce MAX_HADITH_PER_DAY limit.

    Args:
        group_id: The group chat ID
        date: Date string in YYYY-MM-DD format

    Returns:
        int: Number of hadiths sent today
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) as count FROM hadith_send_log
                WHERE group_id = ?
                  AND date(sent_at) = ?
            ''', (group_id, date))

            result = cursor.fetchone()
            return result['count'] if result else 0

    except Exception as e:
        logger.error(f"Error in get_hadiths_sent_today_count: {e}", exc_info=False)
        return 0


# =====================================================
# GROUP DATA RESET
# =====================================================

def reset_group_data(chat_id: int) -> bool:
    """
    Reset ALL data for a specific group.

    Deletes:
    - All prayer logs for this group
    - All azan sent logs for this group
    - All content sent logs for this group
    - All hadith send logs for this group (NEW)
    - The group settings (will be recreated with defaults)
    - Prayer times for this group

    Args:
        chat_id: The group chat ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete prayer logs for this group
            cursor.execute('DELETE FROM prayer_logs WHERE group_chat_id = ?', (chat_id,))
            prayer_logs_deleted = cursor.rowcount
            logger.info(f"Deleted {prayer_logs_deleted} prayer logs for group {chat_id}")

            # Delete azan sent logs for this group
            cursor.execute('DELETE FROM azan_sent_log WHERE group_chat_id = ?', (chat_id,))
            azan_logs_deleted = cursor.rowcount
            logger.info(f"Deleted {azan_logs_deleted} azan logs for group {chat_id}")

            # Delete content sent logs for this group
            try:
                cursor.execute('DELETE FROM content_sent_log WHERE group_chat_id = ?', (chat_id,))
                content_logs_deleted = cursor.rowcount
                logger.info(f"Deleted {content_logs_deleted} content logs for group {chat_id}")
            except sqlite3.OperationalError:
                # Table doesn't exist, skip
                pass

            # Delete hadith send logs for this group (NEW)
            cursor.execute('DELETE FROM hadith_send_log WHERE group_id = ?', (chat_id,))
            hadith_logs_deleted = cursor.rowcount
            logger.info(f"Deleted {hadith_logs_deleted} hadith send logs for group {chat_id}")

            # Delete prayer times for this group
            cursor.execute('DELETE FROM prayer_times_per_group WHERE group_chat_id = ?', (chat_id,))
            prayer_times_deleted = cursor.rowcount
            logger.info(f"Deleted {prayer_times_deleted} prayer times for group {chat_id}")

            # Delete group itself
            cursor.execute('DELETE FROM groups WHERE chat_id = ?', (chat_id,))
            groups_deleted = cursor.rowcount
            logger.info(f"Deleted {groups_deleted} group settings for group {chat_id}")

            logger.info(f"Successfully reset all data for group {chat_id}")
            return True

    except Exception as e:
        logger.error(f"Error in reset_group_data: {e}", exc_info=False)
        return False


# =====================================================
# SYSTEM STATUS
# =====================================================

def get_system_status(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed system status for a specific group.

    Returns:
        dict: Dictionary containing all status information
    """
    try:
        with get_db_connection() as conn:
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
                'database_path': config.DATABASE_PATH
            }

    except Exception as e:
        logger.error(f"Error in get_system_status: {e}", exc_info=False)
        return None


# =====================================================
# HADITH CACHE OPERATIONS
# =====================================================

def cache_hadith(hadith_id: str, category_id: str, hadith_text: str,
                attribution: str = None, grade: str = None,
                explanation: str = None, source_url: str = None) -> bool:
    """
    Cache a hadith in the database.

    Args:
        hadith_id: Unique hadith identifier
        category_id: Category ID
        hadith_text: The hadith text
        attribution: Attribution/source
        grade: Hadith grade
        explanation: Hadith explanation
        source_url: Source URL

    Returns:
        bool: True if cached successfully
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO hadith_cache
                (hadith_id, category_id, hadith_text, attribution, grade, explanation, source_url, last_used_at, usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            ''', (hadith_id, category_id, hadith_text, attribution, grade, explanation, source_url))

            logger.debug(f"Cached hadith {hadith_id} for category {category_id}")
            return True

    except Exception as e:
        logger.error(f"Error in cache_hadith: {e}", exc_info=False)
        return False


def get_cached_hadith(category_id: str, limit: int = None) -> List[Dict[str, Any]]:
    """
    Get cached hadiths for a specific category.

    Args:
        category_id: The category ID
        limit: Maximum number of hadiths to return (optional)

    Returns:
        List[Dict]: List of cached hadiths
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT * FROM hadith_cache
                WHERE category_id = ?
                ORDER BY usage_count DESC, last_used_at DESC
            '''
            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query, (category_id,))
            results = cursor.fetchall()

            hadiths = []
            for row in results:
                hadiths.append({
                    'hadith_id': row['hadith_id'],
                    'id': row['hadith_id'],
                    'category_id': row['category_id'],
                    'hadith_text': row['hadith_text'],
                    'attribution': row['attribution'],
                    'grade': row['grade'],
                    'explanation': row['explanation'],
                    'source_url': row['source_url'],
                    'usage_count': row['usage_count'],
                    'last_used_at': row['last_used_at']
                })

            return hadiths

    except Exception as e:
        logger.error(f"Error in get_cached_hadith: {e}", exc_info=False)
        return []


def update_hadith_usage(hadith_id: str) -> bool:
    """
    Update hadith usage statistics when a hadith is sent.

    Args:
        hadith_id: The hadith ID

    Returns:
        bool: True if updated successfully
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE hadith_cache
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE hadith_id = ?
            ''', (hadith_id,))

            logger.debug(f"Updated usage for hadith {hadith_id}")
            return True

    except Exception as e:
        logger.error(f"Error in update_hadith_usage: {e}", exc_info=False)
        return False
