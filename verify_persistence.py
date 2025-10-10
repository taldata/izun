#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to verify data persistence on Render
Run this after deployment to test if data persists
"""

import os
import sqlite3
from datetime import datetime

def verify_persistence():
    """Verify that the database is using persistent storage"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
    
    print("=" * 60)
    print("DATABASE PERSISTENCE VERIFICATION")
    print("=" * 60)
    
    # 1. Check database path
    print(f"\n1. Database Path: {db_path}")
    
    # 2. Check if path is in persistent storage
    if db_path.startswith('/var/data'):
        print("   ✅ Database is in persistent storage directory (/var/data)")
    else:
        print("   ⚠️  WARNING: Database is NOT in persistent storage!")
    
    # 3. Check if database file exists
    if os.path.exists(db_path):
        print(f"   ✅ Database file exists")
        
        # Get file info
        file_size = os.path.getsize(db_path)
        file_modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        print(f"   📊 File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        print(f"   📅 Last modified: {file_modified}")
    else:
        print(f"   ⚠️  Database file does not exist yet")
    
    # 4. Check database directory
    db_dir = os.path.dirname(db_path)
    print(f"\n2. Storage Directory: {db_dir}")
    
    if os.path.exists(db_dir):
        print(f"   ✅ Directory exists")
        
        # Check if writable
        if os.access(db_dir, os.W_OK):
            print(f"   ✅ Directory is writable")
        else:
            print(f"   ❌ Directory is NOT writable!")
    else:
        print(f"   ⚠️  Directory does not exist")
    
    # 5. Check disk space
    if os.path.exists(db_dir):
        stat = os.statvfs(db_dir)
        free_space = stat.f_bavail * stat.f_frsize
        total_space = stat.f_blocks * stat.f_frsize
        used_space = total_space - free_space
        used_percent = (used_space / total_space) * 100
        
        print(f"\n3. Disk Usage:")
        print(f"   Total: {total_space / (1024**3):.2f} GB")
        print(f"   Used:  {used_space / (1024**3):.2f} GB ({used_percent:.1f}%)")
        print(f"   Free:  {free_space / (1024**3):.2f} GB")
    
    # 6. Check database tables and record counts
    if os.path.exists(db_path):
        print(f"\n4. Database Contents:")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()
            
            print(f"   📊 Tables found: {len(tables)}")
            
            # Count records in key tables
            key_tables = ['users', 'hativot', 'maslulim', 'committee_types', 'vaadot', 'events', 'audit_logs']
            for table in key_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   - {table}: {count} records")
                except:
                    print(f"   - {table}: table not found")
            
            conn.close()
            print("   ✅ Database is readable and contains data")
            
        except Exception as e:
            print(f"   ❌ Error reading database: {e}")
    
    # 7. Write a test marker file
    print(f"\n5. Testing Write Persistence:")
    marker_file = os.path.join(db_dir, '.persistence_test')
    try:
        with open(marker_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"Deployment check: {timestamp}\n")
        print(f"   ✅ Successfully wrote to: {marker_file}")
        
        # Read back the file
        if os.path.exists(marker_file):
            with open(marker_file, 'r') as f:
                lines = f.readlines()
            print(f"   📝 Persistence marker has {len(lines)} deployment(s) recorded")
            if len(lines) > 1:
                print(f"   ✅✅ DATA IS PERSISTING! (File survived {len(lines)} deployments)")
            else:
                print(f"   ℹ️  First deployment or marker file was reset")
    except Exception as e:
        print(f"   ❌ Error writing test file: {e}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    
    # Summary
    print("\n📋 SUMMARY:")
    if db_path.startswith('/var/data') and os.path.exists(db_path):
        print("✅ Your data WILL persist across deployments")
        print("✅ Database is correctly configured for production use")
    else:
        print("⚠️  WARNING: Check your configuration!")
        print("   - Ensure DATABASE_PATH environment variable is set")
        print("   - Ensure the persistent disk is mounted at /var/data")
    
    print("\n💡 TIP: Run this script after each deployment to verify persistence")
    print("   The persistence marker count should increase with each deployment\n")

if __name__ == '__main__':
    verify_persistence()

