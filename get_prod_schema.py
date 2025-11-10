#!/usr/bin/env python3
"""Script to get production database schema"""
import sqlite3
import sys

db_path = '/var/data/committee_system.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print("=== PRODUCTION DATABASE SCHEMA ===\n")
    
    for (table_name,) in tables:
        print(f"\n--- Table: {table_name} ---")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        for col in columns:
            cid, name, col_type, notnull, default, pk = col
            print(f"  {name}: {col_type} {'NOT NULL' if notnull else ''} {'PRIMARY KEY' if pk else ''} {f'DEFAULT {default}' if default else ''}")
    
    # Get indexes
    print("\n\n=== INDEXES ===")
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
    indexes = cursor.fetchall()
    for idx_name, idx_sql in indexes:
        print(f"\n{idx_name}:")
        print(f"  {idx_sql}")
    
    conn.close()
    print("\n=== END ===")
    
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

