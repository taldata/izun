#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to delete all calendar events created by the system from Azure AD calendar
WITHOUT re-syncing (just delete)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.ad_service import ADService
from services.calendar_service import CalendarService

def main():
    print("=" * 60)
    print("מחיקת כל אירועי היומן שנוצרו על ידי המערכת")
    print("=" * 60)
    
    # Initialize services
    db = DatabaseManager()
    ad_service = ADService(db)
    calendar_service = CalendarService(ad_service, db)
    
    if not calendar_service.is_enabled():
        print("❌ שירות הסנכרון ליומן מושבת")
        return
    
    calendar_email = calendar_service.calendar_email
    print(f"📧 יומן יעד: {calendar_email}")
    
    # Get all synced calendar events
    sync_records = db.get_all_synced_calendar_events(calendar_email)
    print(f"📋 נמצאו {len(sync_records)} אירועים למחיקה")
    
    if len(sync_records) == 0:
        print("✅ אין אירועים למחיקה")
        return
    
    # Confirm
    response = input(f"\nהאם למחוק את כל {len(sync_records)} האירועים? (y/n): ")
    if response.lower() != 'y':
        print("❌ בוטל")
        return
    
    print("\n🗑️ מוחק אירועים...")
    
    events_deleted = 0
    deletion_failures = 0
    
    for i, record in enumerate(sync_records, 1):
        calendar_event_id = record.get('calendar_event_id')
        entity_type = record.get('entity_type', 'unknown')
        entity_id = record.get('entity_id', 'unknown')
        
        if calendar_event_id:
            try:
                success, message = calendar_service.delete_calendar_event(calendar_event_id)
                if success:
                    events_deleted += 1
                    print(f"  ✅ [{i}/{len(sync_records)}] נמחק: {entity_type} #{entity_id}")
                else:
                    deletion_failures += 1
                    print(f"  ❌ [{i}/{len(sync_records)}] נכשל: {entity_type} #{entity_id} - {message}")
            except Exception as e:
                deletion_failures += 1
                print(f"  ❌ [{i}/{len(sync_records)}] שגיאה: {entity_type} #{entity_id} - {e}")
        else:
            print(f"  ⚠️ [{i}/{len(sync_records)}] אין ID ליומן: {entity_type} #{entity_id}")
    
    # Clear sync records from database
    print("\n🧹 מנקה רשומות סנכרון מהמסד נתונים...")
    records_cleared = db.clear_all_calendar_sync_records(calendar_email)
    
    print("\n" + "=" * 60)
    print("📊 סיכום:")
    print(f"  ✅ אירועים שנמחקו: {events_deleted}")
    print(f"  ❌ כשלונות: {deletion_failures}")
    print(f"  🧹 רשומות סנכרון שנוקו: {records_cleared}")
    print("=" * 60)

if __name__ == '__main__':
    main()
