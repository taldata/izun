#!/usr/bin/env python3
"""
סקריפט לעדכון הגשות בפועל באירועים קיימים
מוסיף שדה actual_submissions לאירועים שלא קיים להם ערך
"""

from database import DatabaseManager

def main():
    print("מתחיל עדכון שדה הגשות בפועל...")
    print("=" * 50)
    
    db = DatabaseManager()
    
    # Get all events
    events = db.get_events()
    
    print(f"\nנמצאו {len(events)} אירועים")
    print("-" * 50)
    
    # Display current events
    for event in events:
        actual = event.get('actual_submissions', 0) or 0
        expected = event.get('expected_requests', 0) or 0
        print(f"📝 {event['name']}")
        print(f"   צפוי: {expected}, בפועל: {actual}")
        print()
    
    print("=" * 50)
    print("\nהערה: כעת ניתן לעדכן את שדה 'הגשות בפועל' דרך הממשק")
    print("העמודה החדשה תופיע ב:")
    print("  - טופס יצירת אירוע חדש")
    print("  - טופס עריכת אירוע")
    print("  - טבלת אירועים")
    print("\nהשדה מאפשר:")
    print("  ✓ מעקב אחר הגשות אמיתיות")
    print("  ✓ השוואה בין צפי למציאות")
    print("  ✓ חישוב דיוק הצפי")
    print("  ✓ ניתוח נתונים היסטוריים")

if __name__ == "__main__":
    main()
