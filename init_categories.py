#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize Categories Database
==========================
Load categories from categories_list.txt into the database.
Uses the shared database connection logic to handle WAL mode correctly.
"""
import re
import os
import sys

# Import database connection logic to ensure WAL mode compatibility
try:
    from database import get_db_connection
    import config
except ImportError:
    print("❌ Error: Could not import database module.")
    print("Make sure you are running this from the bot directory.")
    sys.exit(1)


def load_categories_from_file(filepath: str):
    """Parse categories_list.txt file."""
    categories = []
    
    if not os.path.exists(filepath):
        print(f"❌ Error: File {filepath} not found!")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('عدد الأقسام') or line.startswith('==='):
                continue

            match = re.search(r'ID:\s*(\d+)\s*\|\s*القسم:\s*(.+)', line)
            if match:
                category_id = match.group(1)
                category_name = match.group(2).strip()
                categories.append((category_id, category_name))

    return categories


def insert_categories_to_db(categories):
    """Insert categories into the database using shared connection."""
    try:
        # Use the context manager from database.py
        # This handles transactions and WAL mode automatically
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # First, ensure the table exists (Safety check)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories_index (
                    id INTEGER PRIMARY KEY,
                    category_id TEXT NOT NULL UNIQUE,
                    category_name_ar TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            count = 0
            for category_id, category_name in categories:
                cursor.execute('''
                    INSERT OR REPLACE INTO categories_index
                    (category_id, category_name_ar, is_active, created_at)
                    VALUES (?, ?, 1, datetime('now'))
                ''', (category_id, category_name))
                count += 1

            # No need to commit manually, context manager does it
            
            # Check count
            cursor.execute('SELECT COUNT(*) FROM categories_index')
            db_count = cursor.fetchone()[0]

        print(f"✅ Successfully inserted/updated {count} categories.")
        print(f"📊 Total categories in DB: {db_count}")
        print(f"💾 Database: {config.DATABASE_PATH}")

    except Exception as e:
        print(f"❌ Error inserting categories: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    categories_file = 'categories_list.txt'

    print("=" * 60)
    print("Loading Categories Database (WAL Mode Compatible)")
    print("=" * 60)

    # Parse categories file
    print(f"\n📖 Reading categories from {categories_file}...")
    categories = load_categories_from_file(categories_file)
    
    if categories:
        print(f"✅ Parsed {len(categories)} categories")

        # Show first 3 examples
        print("\n📋 Examples:")
        for category_id, category_name in categories[:3]:
            print(f"  ID: {category_id} | {category_name}")

        # Insert into database
        print(f"\n💾 Inserting into database...")
        insert_categories_to_db(categories)
        print("\n✅ Done!")
    else:
        print("❌ No categories found to insert.")
