#!/usr/bin/env python3
"""
Script to delete ALL calendar events for a specific year.
"""

import os
import sys
from datetime import datetime
import time
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ad_service import ADService
from database import DatabaseManager

load_dotenv()

def delete_all_calendar_events(year=2026):
    """Delete ALL events from calendar for a specific year"""
    
    # Initialize services
    db = DatabaseManager()
    ad_service = ADService(db)
    
    calendar_email = db.get_system_setting('calendar_sync_email') or 'plan@innovationisrael.org.il'
    print(f"Deleting ALL events from calendar: {calendar_email}")
    print(f"Year: {year}")
    print("=" * 60)
    
    # Get access token
    token = ad_service.get_app_only_token(['https://graph.microsoft.com/.default'])
    if not token:
        print("ERROR: Could not get access token")
        return
    
    # Query events for the year
    start_date = f"{year}-01-01T00:00:00Z"
    end_date = f"{year}-12-31T23:59:59Z"
    
    url = f"https://graph.microsoft.com/v1.0/users/{calendar_email}/calendar/calendarView"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {
        'startDateTime': start_date,
        'endDateTime': end_date,
        '$top': 500,
        '$select': 'id,subject,start'
    }
    
    deleted_total = 0
    
    while True:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"ERROR: API returned {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        events = data.get('value', [])
        
        if not events:
            break
            
        print(f"\nFound {len(events)} events to delete (Total deleted so far: {deleted_total})\n")
        
        for i, event in enumerate(events, 1):
            event_id = event.get('id')
            subject = event.get('subject', 'No Subject')
            start = event.get('start', {}).get('dateTime', '')[:10]
            
            print(f"{i:3}/{len(events)} Deleting: {start} | {subject[:40]}...", end=" ")
            
            # Delete event
            delete_url = f"https://graph.microsoft.com/v1.0/users/{calendar_email}/calendar/events/{event_id}"
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code in [200, 204]:
                print("✓")
            else:
                print(f"✗ ({delete_response.status_code})")
            
            # Rate limiting
            if i % 20 == 0:
                time.sleep(1)
        
        deleted_total += len(events)
        time.sleep(2) # Pause between batches
    
    # Also clear sync records
    print("\nClearing sync records...")
    db.clear_all_calendar_sync_records(calendar_email)
    
    print(f"\n{'=' * 60}")
    print(f"Total Deleted: {deleted_total}")

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    delete_all_calendar_events(year)
