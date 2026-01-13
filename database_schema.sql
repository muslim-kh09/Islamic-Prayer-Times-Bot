-- =====================================================
-- Islamic Prayer Times Telegram Bot - Database Schema
-- SQLite Database Structure
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
    calculation_method INTEGER DEFAULT 2,  -- Aladhan API calculation methods: 0-ShafiI, 1-Hanafi, 2-MWL, 3-Egypt, 4-Tehran, 5-Karachi, 6-Makkah, etc.
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

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_content_sent_log_group_date ON content_sent_log(group_chat_id, sent_date);

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

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_prayer_times_group_date ON prayer_times_per_group(group_chat_id, date);
CREATE INDEX IF NOT EXISTS idx_azan_sent_log_group_date ON azan_sent_log(group_chat_id, prayer_date);
CREATE INDEX IF NOT EXISTS idx_prayer_logs_user_date ON prayer_logs(user_id, prayer_date);
CREATE INDEX IF NOT EXISTS idx_prayer_logs_prayer_date ON prayer_logs(prayer_name, prayer_date);
CREATE INDEX IF NOT EXISTS idx_users_score ON users(score DESC);

-- Insert default settings
INSERT OR IGNORE INTO settings (setting_key, setting_value, description) VALUES
    ('bot_name', 'PrayerTimes Bot', 'Name of the bot'),
    ('athkar_morning_time', '05:00', 'Time to send morning athkar'),
    ('athkar_evening_time', '18:00', 'Time to send evening athkar'),
    ('hadith_time', '12:00', 'Time to send hadith'),
    ('broadcast_enabled', '1', 'Enable/disable automatic broadcasts');

-- =====================================================
-- Database Schema Complete
-- =====================================================
