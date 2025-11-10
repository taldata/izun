#!/usr/bin/env python3
"""Export production database schema to JSON for comparison"""
import sqlite3
import json
import sys

db_path = '/var/data/committee_system.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema = {}
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        schema[table] = {'columns': []}
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns:
            cid, name, col_type, notnull, default, pk = col
            schema[table]['columns'].append({
                'name': name,
                'type': col_type,
                'notnull': bool(notnull),
                'default': str(default) if default else None,
                'pk': bool(pk)
            })
    
    conn.close()
    
    # Print as JSON
    print(json.dumps(schema, indent=2))
    
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)

