#!/usr/bin/env python3
"""Dump database schema for comparison"""
import sqlite3
import os

db_path = os.environ.get('DATABASE_PATH', '/var/data/committee_system.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = cursor.fetchall()

print("=== DATABASE SCHEMA ===")
for (sql,) in tables:
    if sql:
        print(sql)
        print()

# Get indexes
cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
indexes = cursor.fetchall()

if indexes:
    print("=== INDEXES ===")
    for (sql,) in indexes:
        print(sql)
        print()

conn.close()

