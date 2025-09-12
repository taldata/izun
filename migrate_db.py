#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime, date

def migrate_to_new_schema():
    """Migrate existing database to new committee structure"""
    db_path = "committee_system.db"
    
    if not os.path.exists(db_path):
        print("Database doesn't exist, creating new one...")
        from database import DatabaseManager
        db = DatabaseManager()
        return
    
    print("Starting migration to new committee structure...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if committee_types table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='committee_types'")
        if not cursor.fetchone():
            print("Creating committee_types table...")
            cursor.execute('''
                CREATE TABLE committee_types (
                    committee_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    scheduled_day INTEGER NOT NULL,
                    frequency TEXT DEFAULT 'weekly',
                    week_of_month INTEGER DEFAULT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default committee types
            default_types = [
                ('ועדת הזנק', 0, 'weekly', None, 'ועדת הזנק שבועית'),
                ('ועדת תשתיות', 2, 'weekly', None, 'ועדת תשתיות שבועית'),
                ('ועדת צמיחה', 3, 'weekly', None, 'ועדת צמיחה שבועית'),
                ('ייצור מתקדם', 1, 'monthly', 3, 'ועדת ייצור מתקדם חודשית')
            ]
            
            for name, day, frequency, week_of_month, description in default_types:
                cursor.execute('''
                    INSERT INTO committee_types (name, scheduled_day, frequency, week_of_month, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, day, frequency, week_of_month, description))
            
            print("Committee types created successfully")
        
        # Check current vaadot table structure
        cursor.execute("PRAGMA table_info(vaadot)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # If old structure exists, rename it and create new one
        if 'name' in columns and 'committee_type_id' not in columns:
            print("Migrating vaadot table structure...")
            
            # Rename old table
            cursor.execute("ALTER TABLE vaadot RENAME TO vaadot_old")
            
            # Create new vaadot table
            cursor.execute('''
                CREATE TABLE vaadot (
                    vaadot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    committee_type_id INTEGER NOT NULL,
                    hativa_id INTEGER NOT NULL,
                    vaada_date DATE NOT NULL,
                    status TEXT DEFAULT 'planned',
                    exception_date_id INTEGER,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (committee_type_id) REFERENCES committee_types (committee_type_id),
                    FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id),
                    FOREIGN KEY (exception_date_id) REFERENCES exception_dates (date_id),
                    UNIQUE(committee_type_id, hativa_id, vaada_date)
                )
            ''')
            
            print("New vaadot table structure created")
            
            # Note: We don't migrate old data automatically as the structure is fundamentally different
            # The old table is preserved as vaadot_old for manual review if needed
            
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_to_new_schema()
