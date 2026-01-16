import sqlite3

def reset_database():
    conn = sqlite3.connect('prayer_bot.db')
    cursor = conn.cursor()
    
    print("🧹 جاري تنظيف الجداول القديمة...")
    try:
        # مسح الجداول القديمة تماماً لتجنب تضارب الـ Primary Key
        cursor.execute("DROP TABLE IF EXISTS hadith_send_log")
        cursor.execute("DROP TABLE IF EXISTS hadith_sent_log")
        
        # إنشاء الجدول الصحيح بالاسم والأعمدة اللي البوت بيدور عليها
        print("🏗️ إعادة إنشاء جدول hadith_sent_log بالتعريف الصحيح...")
        cursor.execute('''
        CREATE TABLE hadith_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            category_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_type TEXT DEFAULT 'manual'
        )
        ''')
        
        conn.commit()
        print("✅ تم الإصلاح بنجاح! قاعدة البيانات الآن جاهزة.")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الإصلاح: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_database()

