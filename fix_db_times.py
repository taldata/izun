#!/usr/bin/env python3
"""
Script to fix NULL start/end times in the database for 2026 committees.
Defaults:
- Operational: 09:00 - 11:00
- Regular: 09:00 - 15:00
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from database import DatabaseManager

def fix_db_times():
    db = DatabaseManager()
    
    if db.db_type != 'postgres':
        print("WARNING: Not connected to Postgres! Check .env")
        return

    conn = db.get_connection()
    cursor = conn.cursor()
    
    print("Finding committees with missing times in 2026...")
    
    # Select committees with missing times
    cursor.execute('''
        SELECT v.vaadot_id, v.committee_type_id, ct.is_operational, ct.name, h.name
        FROM vaadot v
        JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
        JOIN hativot h ON v.hativa_id = h.hativa_id
        WHERE v.vaada_date >= '2026-01-01' 
          AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
          AND (v.start_time IS NULL OR v.end_time IS NULL)
    ''')
    
    rows = cursor.fetchall()
    print(f"Found {len(rows)} committees to update.")
    
    updated_count = 0
    
    for row in rows:
        vaadot_id, committee_type_id, is_operational, type_name, hativa_name = row
        
        # Determine defaults
        start_time = '09:00'
        end_time = '11:00' if is_operational else '15:00'
        
        print(f"Updating {vaadot_id} ({type_name} - {hativa_name}): {start_time}-{end_time}")
        
        cursor.execute('''
            UPDATE vaadot
            SET start_time = ?, end_time = ?
            WHERE vaadot_id = ?
        ''', (start_time, end_time, vaadot_id))
        
        updated_count += 1
        
    conn.commit()
    conn.close()
    
    print(f"\nSuccessfully updated {updated_count} committees.")

if __name__ == "__main__":
    fix_db_times()
