-- =====================================================
-- Islamic Prayer Times Telegram Bot - Database Schema
-- SQLite Database Structure - Version 2.1 (Fixed)
-- =====================================================
--
-- Version 2.1 Changes:
-- - Fixed Primary Key conflict in hadith_sent_log
-- - Renamed hadith_send_log to hadith_sent_log for consistency
-- - Added categories_index table for 493 hadith categories
-- - Added category_stats table for prefetch tracking
-- - Enabled WAL mode for concurrent read/write
--
-- IMPORTANT: To enable WAL mode, execute:
--   PRAGMA journal_mode = WAL;
-- After database initialization
-- =====================================================

-- Users table: Stores user information and scores
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
);

-- Groups table: Stores group-specific settings
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,
    group_name TEXT,
    city TEXT DEFAULT 'Riyadh',
    country TEXT DEFAULT 'Saudi Arabia',
    timezone TEXT DEFAULT 'Asia/Riyadh',
    calculation_method INTEGER DEFAULT 2,  -- Aladhan API calculation methods
    is_active INTEGER DEFAULT 1,
    notification_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prayer times per group: Stores prayer times for each group by date
CREATE TABLE IF NOT EXISTS prayer_times_per_group (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id INTEGER NOT NULL,
    date TEXT NOT NULL,  -- Format: YYYY-MM-DD
    fajr_time TEXT NOT NULL,
    dhuhr_time TEXT NOT NULL,
    asr_time TEXT NOT NULL,
    maghrib_time TEXT NOT NULL,
    isha_time TEXT NOT NULL,
    hijri_date TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE,
    UNIQUE(group_chat_id, date)  -- Prevent duplicate prayer times for same group on same day
);

-- Azan sent log: Prevents duplicate azan notifications
CREATE TABLE IF NOT EXISTS azan_sent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id INTEGER NOT NULL,
    prayer_name TEXT NOT NULL,  -- fajr, dhuhr, asr, maghrib, isha
    prayer_date TEXT NOT NULL,  -- Format: YYYY-MM-DD
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE,
    UNIQUE(group_chat_id, prayer_name, prayer_date)  -- Prevent duplicate azan for same prayer on same day
);

-- Content sent log: Prevents duplicate content sends (athkar, hadiths)
CREATE TABLE IF NOT EXISTS content_sent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_chat_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,  -- morning_athkar, evening_athkar, hadiths, etc.
    sent_date TEXT NOT NULL,  -- Format: YYYY-MM-DD
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE,
    UNIQUE(group_chat_id, content_type, sent_date)  -- Prevent duplicate content for same type on same day
);

-- Prayer logs: Records users' completed prayers
CREATE TABLE IF NOT EXISTS prayer_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    group_chat_id INTEGER,
    prayer_name TEXT NOT NULL,  -- fajr, dhuhr, asr, maghrib, isha
    prayer_date TEXT NOT NULL,  -- Format: YYYY-MM-DD
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE SET NULL
);

-- Settings: General bot settings
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Broadcast queue: Queue for sending athkar/hadiths
CREATE TABLE IF NOT EXISTS broadcast_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,  -- 'athkar_morning', 'athkar_evening', 'hadith'
    content_json TEXT NOT NULL,
    target_chat_id INTEGER,
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending, sent, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- HADITH BRAIN TABLES (Merged from hadith_brain_v2.db)
-- =====================================================

-- Group affinity table: Learning profiles for smart hadith selection
CREATE TABLE IF NOT EXISTS group_affinity (
    group_id INTEGER,
    category_tag TEXT,
    affinity_score REAL DEFAULT 1.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, category_tag)
);

-- Hadith sent log: Records hadiths sent to groups for cooldown tracking
-- Critical Fix v2.0.0: Replaced log file reading with database tracking
-- FIXED: Renamed to hadith_sent_log and removed double primary key
CREATE TABLE IF NOT EXISTS hadith_sent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    category_id TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    window_name TEXT
);

-- Short-term memory: Recent messages for context analysis
CREATE TABLE IF NOT EXISTS short_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    message_text TEXT,
    sender_role TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- HADITH CACHE TABLE (Smart Caching)
-- =====================================================

-- Hadith cache: Stores API responses for intelligent caching
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
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_content_sent_log_group_date ON content_sent_log(group_chat_id, sent_date);
CREATE INDEX IF NOT EXISTS idx_prayer_times_group_date ON prayer_times_per_group(group_chat_id, date);
CREATE INDEX IF NOT EXISTS idx_azan_sent_log_group_date ON azan_sent_log(group_chat_id, prayer_date);
CREATE INDEX IF NOT EXISTS idx_prayer_logs_user_date ON prayer_logs(user_id, prayer_date);
CREATE INDEX IF NOT EXISTS idx_prayer_logs_prayer_date ON prayer_logs(prayer_name, prayer_date);
CREATE INDEX IF NOT EXISTS idx_users_score ON users(score DESC);

-- Indexes for hadith cache
CREATE INDEX IF NOT EXISTS idx_hadith_cache_category ON hadith_cache(category_id);
CREATE INDEX IF NOT EXISTS idx_hadith_cache_usage ON hadith_cache(usage_count DESC, last_used_at DESC);

-- Indexes for hadith brain (Updated table name to hadith_sent_log)
CREATE INDEX IF NOT EXISTS idx_hadith_sent_log_group_category ON hadith_sent_log(group_id, category_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_short_term_memory_group ON short_term_memory(group_id, timestamp DESC);

-- =====================================================
-- CATEGORIES INDEX (Version 2.1)
-- =====================================================

-- Categories index: Stores all 493 hadith categories from API
CREATE TABLE IF NOT EXISTS categories_index (
    id INTEGER PRIMARY KEY,
    category_id TEXT NOT NULL UNIQUE,
    category_name_ar TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Category stats: Tracks prefetch status for each category
CREATE TABLE IF NOT EXISTS category_stats (
    category_id TEXT NOT NULL,
    total_cached INTEGER DEFAULT 0,
    last_prefetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id),
    FOREIGN KEY (category_id) REFERENCES categories_index(category_id) ON DELETE CASCADE
);

-- Index for categories index
CREATE INDEX IF NOT EXISTS idx_categories_index_active ON categories_index(is_active);
CREATE INDEX IF NOT EXISTS idx_category_stats_prefetch ON category_stats(last_prefetched_at);

-- =====================================================
-- DEFAULT SETTINGS
-- =====================================================

-- Insert default settings
INSERT OR IGNORE INTO settings (setting_key, setting_value, description) VALUES
    ('bot_name', 'PrayerTimes Bot', 'Name of the bot'),
    ('broadcast_enabled', '1', 'Enable/disable automatic broadcasts');

-- =====================================================
-- Database Schema Complete - Version 2.1
-- =====================================================
