import sqlite3

conn = sqlite3.connect('prayer_bot.db')
cursor = conn.cursor()

try:
    # إنشاء الجدول بالاسم الصحيح الذي يبحث عنه البوت
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hadith_sent_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        category_id TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    print("✅ تم إنشاء جدول hadith_sent_log بنجاح!")
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
finally:
    conn.close()

