#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to upload local database to Render
This creates a data export that can be imported on Render
"""

import sqlite3
import json
import sys

def export_database(db_path='committee_system.db'):
    """Export database to JSON format"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        data = {}
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📦 Exporting {len(tables)} tables...")
        
        # Export each table
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            data[table] = [dict(row) for row in rows]
            print(f"   ✓ {table}: {len(data[table])} records")
        
        conn.close()
        
        # Write to JSON file
        output_file = 'db_export.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ Database exported to: {output_file}")
        print(f"📊 Total records exported: {sum(len(records) for records in data.values())}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error exporting database: {e}")
        import traceback
        traceback.print_exc()
        return None

def import_database(json_file='db_export.json', db_path=None):
    """Import database from JSON format"""
    import os
    
    if db_path is None:
        db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
    
    try:
        print(f"📥 Importing data to: {db_path}")
        
        # Check if database already has data
        conn_check = sqlite3.connect(db_path)
        cursor_check = conn_check.cursor()
        cursor_check.execute("SELECT COUNT(*) FROM hativot")
        existing_count = cursor_check.fetchone()[0]
        conn_check.close()
        
        if existing_count > 0:
            print(f"   ℹ️  Database already contains {existing_count} hativot")
            print(f"   ⏭️  Skipping import to preserve existing data")
            return True
        
        print(f"   Database is empty - proceeding with import...")
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Disable foreign keys temporarily
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        for table in data.keys():
            try:
                cursor.execute(f"DELETE FROM {table}")
                print(f"   🗑️  Cleared {table}")
            except:
                pass
        
        # Import data
        imported_count = 0
        for table, records in data.items():
            if not records:
                continue
            
            # Get column names from first record
            columns = list(records[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            column_names = ','.join(columns)
            
            # Insert records
            for record in records:
                try:
                    values = [record[col] for col in columns]
                    cursor.execute(f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})", values)
                    imported_count += 1
                except sqlite3.IntegrityError as e:
                    # Skip duplicates
                    print(f"   ⚠️  Skipped duplicate in {table}: {e}")
                except Exception as e:
                    print(f"   ❌ Error importing to {table}: {e}")
            
            print(f"   ✓ {table}: {len(records)} records imported")
        
        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Import complete!")
        print(f"📊 Total records imported: {imported_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error importing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'import':
        # Import mode
        import_database()
    else:
        # Export mode (default)
        export_database()

