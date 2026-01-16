#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update Database Schema
=======================
Add missing hadith_send_log table to existing database.
This is a one-time migration script.
"""
import os
import sys

# Import database connection logic
try:
    from database import get_db_connection
    import config
    from logger_config import logger
except ImportError as e:
    print(f"❌ Error: Could not import database module.")
    print(f"Error: {e}")
    sys.exit(1)


def add_missing_tables():
    """Add missing tables to existing database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if hadith_send_log table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='hadith_sent_log'
            """)
            table_exists = cursor.fetchone()

            if table_exists:
                print("✅ Table 'hadith_sent_log' already exists. Nothing to do.")
                return

            # Create hadith_send_log table
            print("📝 Creating hadith_sent_log table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hadith_sent_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    category_id TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    window_name TEXT
                );
            ''')

            # Create index for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_hadith_send_log_group_time
                ON hadith_send_log(group_id, sent_at DESC);
            ''')

            # Verify creation
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='hadith_sent_log'
            """)
            result = cursor.fetchone()

            if result:
                print("✅ Table 'hadith_sent_log' created successfully!")
                print("✅ Index created successfully!")
                
                # Check if table is empty
                cursor.execute('SELECT COUNT(*) FROM hadith_sent_log')
                count = cursor.fetchone()[0]
                print(f"📊 Current records in hadith_sent_log: {count}")
            else:
                print("❌ Failed to create table")

            # List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"\n📋 All tables in database:")
            for table in tables:
                print(f"  - {table[0]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("=" * 60)
    print("Database Schema Update Script")
    print("=" * 60)
    print(f"📂 Database: {config.DATABASE_PATH}")
    print(f"🗂  Working directory: {os.getcwd()}")
    print("=" * 60)
    
    add_missing_tables()
    
    print("\n" + "=" * 60)
    print("✅ Update complete!")
    print("=" * 60)