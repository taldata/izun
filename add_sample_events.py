#!/usr/bin/env python3
"""
Script to add sample events to the committee management system
"""

import sqlite3
from datetime import date, datetime
import random

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('committee_system.db')

def add_sample_events():
    """Add multiple sample events to the system"""
    
    # Sample event data
    sample_events = [
        # Technology Division Events
        {
            'name': 'סדנת פיתוח אפליקציות מובייל',
            'type': 'הכשרה',
            'expected_requests': 25,
            'description': 'סדנה מקיפה לפיתוח אפליקציות בטכנולוגיות חדישות'
        },
        {
            'name': 'הרצאה על אבטחת מידע',
            'type': 'הרצאה',
            'expected_requests': 40,
            'description': 'הרצאה על טכנולוגיות אבטחה מתקדמות'
        },
        {
            'name': 'ימי עיון בבינה מלאכותית',
            'type': 'כנס',
            'expected_requests': 60,
            'description': 'כנס דו-יומי על יישומי AI בתעשייה'
        },
        {
            'name': 'קורס פיתון מתקדם',
            'type': 'קורס',
            'expected_requests': 30,
            'description': 'קורס מתקדם בתכנות פיתון'
        },
        {
            'name': 'הכשרת DevOps',
            'type': 'הכשרה',
            'expected_requests': 20,
            'description': 'הכשרה מקיפה בכלי DevOps'
        },
        
        # Operations Division Events
        {
            'name': 'תרגיל חירום ארצי',
            'type': 'תרגיל',
            'expected_requests': 100,
            'description': 'תרגיל חירום רב-מערכתי'
        },
        {
            'name': 'הכשרת מפקדים',
            'type': 'הכשרה',
            'expected_requests': 35,
            'description': 'קורס הכשרה למפקדי יחידות'
        },
        {
            'name': 'סימולציה מבצעית',
            'type': 'תרגיל',
            'expected_requests': 50,
            'description': 'סימולציה מבצעית מתקדמת'
        },
        {
            'name': 'כנס בטיחות',
            'type': 'כנס',
            'expected_requests': 80,
            'description': 'כנס שנתי לבטיחות במקום העבודה'
        },
        {
            'name': 'הדרכת ציוד חדש',
            'type': 'הדרכה',
            'expected_requests': 25,
            'description': 'הדרכה על ציוד טכנולוגי חדש'
        },
        
        # Intelligence Division Events
        {
            'name': 'סדנת ניתוח מודיעיני',
            'type': 'סדנה',
            'expected_requests': 15,
            'description': 'סדנה מתקדמת לניתוח מודיעיני'
        },
        {
            'name': 'קורס הערכות מצב',
            'type': 'קורס',
            'expected_requests': 20,
            'description': 'קורס מתקדם להערכות מצב אסטרטגיות'
        },
        {
            'name': 'הכשרת אנליסטים',
            'type': 'הכשרה',
            'expected_requests': 18,
            'description': 'הכשרה מקצועית לאנליסטים'
        },
        {
            'name': 'ימי עיון בטכנולוגיות מודיעין',
            'type': 'כנס',
            'expected_requests': 45,
            'description': 'כנס על טכנולוגיות מודיעין מתקדמות'
        },
        
        # Logistics Division Events
        {
            'name': 'הכשרת רכש',
            'type': 'הכשרה',
            'expected_requests': 22,
            'description': 'הכשרה בתהליכי רכש ומכרזים'
        },
        {
            'name': 'סדנת ניהול מלאי',
            'type': 'סדנה',
            'expected_requests': 28,
            'description': 'סדנה לניהול מלאי יעיל'
        },
        {
            'name': 'כנס לוגיסטיקה',
            'type': 'כנס',
            'expected_requests': 70,
            'description': 'כנס שנתי לתחום הלוגיסטיקה'
        },
        {
            'name': 'הדרכת מערכות ERP',
            'type': 'הדרכה',
            'expected_requests': 30,
            'description': 'הדרכה על מערכות ERP חדשות'
        },
        
        # Training Division Events
        {
            'name': 'קורס מדריכים',
            'type': 'קורס',
            'expected_requests': 25,
            'description': 'קורס הכשרת מדריכים'
        },
        {
            'name': 'סדנת למידה דיגיטלית',
            'type': 'סדנה',
            'expected_requests': 35,
            'description': 'סדנה על כלי למידה דיגיטליים'
        },
        {
            'name': 'כנס חינוך והכשרה',
            'type': 'כנס',
            'expected_requests': 90,
            'description': 'כנס שנתי לחינוך והכשרה'
        },
        {
            'name': 'הכשרת מנהלי הכשרה',
            'type': 'הכשרה',
            'expected_requests': 15,
            'description': 'הכשרה למנהלי מחלקות הכשרה'
        }
    ]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get available committee meetings (vaadot)
        cursor.execute('''
            SELECT v.vaadot_id, v.vaada_date, ct.name as committee_name, h.name as hativa_name, v.hativa_id
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            WHERE v.status IN ('scheduled', 'planned')
            ORDER BY v.vaada_date
        ''')
        vaadot = cursor.fetchall()
        
        # Get available routes (maslulim)
        cursor.execute('''
            SELECT m.maslul_id, m.name, m.hativa_id, h.name as hativa_name
            FROM maslulim m
            JOIN hativot h ON m.hativa_id = h.hativa_id
        ''')
        maslulim = cursor.fetchall()
        
        if not vaadot or not maslulim:
            print("No committee meetings or routes found. Please ensure data exists.")
            return
        
        print(f"Found {len(vaadot)} committee meetings and {len(maslulim)} routes")
        
        events_added = 0
        
        # Add events
        for event_data in sample_events:
            # Randomly select a committee meeting
            vaada = random.choice(vaadot)
            vaadot_id, vaada_date, committee_name, hativa_name, hativa_id = vaada
            
            # Find routes from the same division as the committee
            matching_routes = [m for m in maslulim if m[2] == vaada[4]]  # Same hativa_id (vaada[4] is hativa_id)
            
            if not matching_routes:
                print(f"No matching routes found for committee {committee_name} in {hativa_name}")
                continue
            
            # Select a random route from the same division
            route = random.choice(matching_routes)
            maslul_id = route[0]
            
            # Insert the event
            cursor.execute('''
                INSERT INTO events (vaadot_id, maslul_id, name, event_type, expected_requests, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                vaadot_id,
                maslul_id,
                event_data['name'],
                event_data['type'],
                event_data['expected_requests'],
                datetime.now().isoformat()
            ))
            
            events_added += 1
            print(f"Added event: {event_data['name']} for {committee_name} - {hativa_name}")
        
        conn.commit()
        print(f"\nSuccessfully added {events_added} events to the system!")
        
    except Exception as e:
        print(f"Error adding events: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_sample_events()
