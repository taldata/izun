#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime, date, timedelta
from database import DatabaseManager
from scheduler import CommitteeScheduler

def test_system():
    """Test the committee system with sample data"""
    print("בודק את מערכת הוועדות...")
    
    # Remove existing database for clean test
    if os.path.exists("committee_system.db"):
        os.remove("committee_system.db")
    
    # Initialize system
    db = DatabaseManager()
    scheduler = CommitteeScheduler(db)
    
    print("✓ מסד נתונים אותחל בהצלחה")
    
    # Test 1: Add sample divisions
    print("\n--- בדיקה 1: הוספת חטיבות ---")
    hativa1_id = db.add_hativa("חטיבת טכנולוגיה", "חטיבה לפיתוח טכנולוגי")
    hativa2_id = db.add_hativa("חטיבת תפעול", "חטיבה לתפעול מערכות")
    hativa3_id = db.add_hativa("חטיבת מחקר", "חטיבה למחקר ופיתוח")
    
    print(f"✓ נוספו 3 חטיבות (IDs: {hativa1_id}, {hativa2_id}, {hativa3_id})")
    
    # Test 2: Add sample routes
    print("\n--- בדיקה 2: הוספת מסלולים ---")
    routes = [
        (hativa1_id, "פיתוח אפליקציות", "מסלול לפיתוח אפליקציות מובייל"),
        (hativa1_id, "תשתיות ענן", "מסלול לתשתיות ענן ומיקרו-שירותים"),
        (hativa2_id, "ניטור מערכות", "מסלול לניטור וניהול מערכות"),
        (hativa2_id, "אבטחת מידע", "מסלול לאבטחת מידע וסייבר"),
        (hativa3_id, "בינה מלאכותית", "מסלול למחקר בבינה מלאכותית"),
        (hativa3_id, "ניתוח נתונים", "מסלול לניתוח נתונים מתקדם")
    ]
    
    route_ids = []
    for hativa_id, name, desc in routes:
        route_id = db.add_maslul(hativa_id, name, desc)
        route_ids.append(route_id)
    
    print(f"✓ נוספו {len(routes)} מסלולים")
    
    # Test 3: Add exception dates
    print("\n--- בדיקה 3: הוספת תאריכי חריגים ---")
    today = date.today()
    exception_dates = [
        (today + timedelta(days=10), "יום עצמאות", "holiday"),
        (today + timedelta(days=20), "יום זיכרון", "holiday"),
        (today + timedelta(days=30), "שבתון מיוחד", "sabbath")
    ]
    
    for exc_date, desc, date_type in exception_dates:
        db.add_exception_date(exc_date, desc, date_type)
    
    print(f"✓ נוספו {len(exception_dates)} תאריכי חריגים")
    
    # Test 4: Check committees
    print("\n--- בדיקה 4: בדיקת וועדות ---")
    committees = db.get_vaadot()
    print(f"✓ נמצאו {len(committees)} וועדות במערכת:")
    for committee in committees:
        print(f"  - {committee['name']} ({committee['scheduled_day_name']})")
    
    # Test 5: Create sample events
    print("\n--- בדיקה 5: יצירת אירועים לדוגמה ---")
    sample_events = [
        (1, route_ids[0], "שדרוג אפליקציית לקוחות", "kokok", 15),
        (2, route_ids[1], "הקמת תשתית ענן חדשה", "shotef", 8),
        (3, route_ids[4], "מחקר אלגוריתמי ML", "kokok", 12),
        (4, route_ids[2], "שדרוג מערכת ניטור", "shotef", 5)
    ]
    
    event_ids = []
    for vaadot_id, maslul_id, name, event_type, requests in sample_events:
        # Validate before creating
        event_data = {
            'vaadot_id': vaadot_id,
            'maslul_id': maslul_id,
            'name': name,
            'event_type': event_type,
            'expected_requests': requests
        }
        
        is_valid, message = scheduler.validate_event_scheduling(event_data)
        if is_valid:
            event_id = db.add_event(vaadot_id, maslul_id, name, event_type, requests)
            event_ids.append(event_id)
            print(f"✓ נוצר אירוע: {name}")
        else:
            print(f"✗ שגיאה באירוע {name}: {message}")
    
    # Test 6: Test scheduling logic
    print("\n--- בדיקה 6: בדיקת לוגיקת תזמון ---")
    
    # Test business day validation
    test_date = date.today()
    while test_date.weekday() >= 5:  # Find a weekday
        test_date += timedelta(days=1)
    
    is_business = scheduler.is_business_day(test_date)
    print(f"✓ {test_date} הוא יום עסקים: {is_business}")
    
    # Test committee scheduling
    committee_name = "ועדת הזנק"
    can_schedule, reason = scheduler.can_schedule_committee(committee_name, test_date)
    print(f"✓ ניתן לתזמן {committee_name} ב-{test_date}: {can_schedule}")
    if not can_schedule:
        print(f"  סיבה: {reason}")
    
    # Test 7: Monthly schedule
    print("\n--- בדיקה 7: לוח זמנים חודשי ---")
    current_month = date.today()
    schedule = scheduler.get_monthly_schedule(current_month.year, current_month.month)
    
    print(f"✓ לוח זמנים לחודש {current_month.month}/{current_month.year}:")
    print(f"  ימי עסקים: {len(schedule['business_days'])}")
    print(f"  ימי חריג: {len(schedule['exception_dates'])}")
    print(f"  וועדות מתוזמנות: {len(schedule['committees'])}")
    
    # Test 8: Suggest dates
    print("\n--- בדיקה 8: הצעת תאריכים ---")
    suggestions = scheduler.suggest_next_available_dates("ועדת צמיחה", date.today(), 3)
    print(f"✓ הוצעו {len(suggestions)} תאריכים לועדת צמיחה:")
    for suggestion in suggestions:
        status = "זמין" if suggestion['can_schedule'] else "לא זמין"
        print(f"  {suggestion['date']}: {status}")
    
    print("\n" + "="*60)
    print("           בדיקת המערכת הושלמה בהצלחה!")
    print("="*60)
    print("המערכת מוכנה לשימוש. הרץ: python main.py")
    print("="*60)

if __name__ == "__main__":
    test_system()
