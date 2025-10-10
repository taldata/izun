#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick import script - imports missing data directly
"""

import os
import sqlite3
from datetime import datetime

def quick_import():
    """Import missing maslulim and events"""
    db_path = os.environ.get('DATABASE_PATH', '/var/data/committee_system.db')
    
    print(f"Quick import to: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM maslulim")
    maslulim_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events")
    events_count = cursor.fetchone()[0]
    
    print(f"Current state: maslulim={maslulim_count}, events={events_count}")
    
    if maslulim_count == 0:
        print("Importing maslulim from db_export.json...")
        import json
        with open('db_export.json', 'r') as f:
            data = json.load(f)
        
        for m in data['maslulim']:
            try:
                cursor.execute("""
                    INSERT INTO maslulim 
                    (maslul_id, hativa_id, name, description, created_at, is_active, sla_days, 
                     stage_a_days, stage_b_days, stage_c_days, stage_d_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (m['maslul_id'], m['hativa_id'], m['name'], m.get('description', ''), 
                      m['created_at'], m.get('is_active', 1), m.get('sla_days', 55),
                      m.get('stage_a_days', 10), m.get('stage_b_days', 15), 
                      m.get('stage_c_days', 10), m.get('stage_d_days', 10)))
                print(f"  ✓ Imported maslul: {m['name']}")
            except Exception as e:
                print(f"  ✗ Error importing {m['name']}: {e}")
        
        conn.commit()
        print(f"✅ Imported {len(data['maslulim'])} maslulim")
    
    if events_count == 0:
        print("Importing events from db_export.json...")
        import json
        with open('db_export.json', 'r') as f:
            data = json.load(f)
        
        for e in data['events']:
            try:
                cursor.execute("""
                    INSERT INTO events 
                    (event_id, vaadot_id, maslul_id, name, event_type, expected_requests, 
                     actual_submissions, call_publication_date, call_deadline_date, 
                     intake_deadline_date, review_deadline_date, response_deadline_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (e['event_id'], e['vaadot_id'], e['maslul_id'], e['name'], e['event_type'],
                      e.get('expected_requests', 0), e.get('actual_submissions', 0),
                      e.get('call_publication_date'), e.get('call_deadline_date'),
                      e.get('intake_deadline_date'), e.get('review_deadline_date'),
                      e.get('response_deadline_date'), e.get('created_at')))
                print(f"  ✓ Imported event: {e['name']}")
            except Exception as e_err:
                print(f"  ✗ Error importing {e.get('name', '?')}: {e_err}")
        
        conn.commit()
        print(f"✅ Imported {len(data['events'])} events")
    
    conn.close()
    print("\n✅ Quick import complete!")

if __name__ == '__main__':
    quick_import()

