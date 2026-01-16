import sqlite3
import os

db_name = 'prayer_bot.db'

if os.path.exists(db_name):
    os.remove(db_name)
    print("🗑️ تم حذف قاعدة البيانات القديمة.")

conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# قائمة بجميع أوامر إنشاء الجداول (مصححة)
schema_queries = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL UNIQUE, username TEXT, first_name TEXT, last_name TEXT, score INTEGER DEFAULT 0, prayer_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE groups (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL UNIQUE, group_name TEXT, city TEXT DEFAULT 'Riyadh', country TEXT DEFAULT 'Saudi Arabia', timezone TEXT DEFAULT 'Asia/Riyadh', calculation_method INTEGER DEFAULT 2, is_active INTEGER DEFAULT 1, notification_enabled INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE prayer_times_per_group (id INTEGER PRIMARY KEY AUTOINCREMENT, group_chat_id INTEGER NOT NULL, date TEXT NOT NULL, fajr_time TEXT NOT NULL, dhuhr_time TEXT NOT NULL, asr_time TEXT NOT NULL, maghrib_time TEXT NOT NULL, isha_time TEXT NOT NULL, hijri_date TEXT, fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE, UNIQUE(group_chat_id, date))",
    "CREATE TABLE azan_sent_log (id INTEGER PRIMARY KEY AUTOINCREMENT, group_chat_id INTEGER NOT NULL, prayer_name TEXT NOT NULL, prayer_date TEXT NOT NULL, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (group_chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE, UNIQUE(group_chat_id, prayer_name, prayer_date))",
    "CREATE TABLE hadith_sent_log (id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL, category_id TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, window_name TEXT)", # تم التصحيح هنا
    "CREATE TABLE hadith_cache (id INTEGER PRIMARY KEY AUTOINCREMENT, hadith_id TEXT NOT NULL UNIQUE, category_id TEXT NOT NULL, hadith_text TEXT NOT NULL, attribution TEXT, grade TEXT, explanation TEXT, source_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, usage_count INTEGER DEFAULT 0)",
    "CREATE TABLE categories_index (id INTEGER PRIMARY KEY, category_id TEXT NOT NULL UNIQUE, category_name_ar TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE category_stats (category_id TEXT PRIMARY KEY, total_cached INTEGER DEFAULT 0, last_prefetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (category_id) REFERENCES categories_index(category_id) ON DELETE CASCADE)"
]

print("🏗️ جاري إنشاء الجداول بالتعريفات الصحيحة...")
for query in schema_queries:
    cursor.execute(query)

conn.commit()
conn.close()
print("✅ تم تجهيز قاعدة البيانات بنجاح! جرب تشغيل bot.py الآن.")

