import sqlite3

conn = sqlite3.connect('prayer_bot.db')
cursor = conn.cursor()

def fix_schema():
    print("🔍 جاري فحص وتحديث قاعدة البيانات...")
    
    try:
        # 1. تحديث جدول hadith_sent_log
        # سنتأكد من وجود عمود group_id
        cursor.execute("PRAGMA table_info(hadith_sent_log)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'group_id' not in columns:
            print("➕ إضافة عمود group_id لجدول hadith_sent_log...")
            cursor.execute("ALTER TABLE hadith_sent_log ADD COLUMN group_id INTEGER")
        
        # 2. التأكد من وجود عمود النوع (optional but good for safety)
        if 'sent_type' not in columns:
            cursor.execute("ALTER TABLE hadith_sent_log ADD COLUMN sent_type TEXT DEFAULT 'manual'")

        conn.commit()
        print("✅ تم تحديث الجداول وإضافة الأعمدة بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء التحديث: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_schema()

