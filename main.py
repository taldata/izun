#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from database import DatabaseManager
from scheduler import CommitteeScheduler

class CommitteeSystemApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.scheduler = CommitteeScheduler(self.db)
        
    def display_menu(self):
        """Display the main menu"""
        print("\n" + "="*60)
        print("           איזון עומסים")
        print("="*60)
        print("1. ניהול חטיבות ומסלולים")
        print("2. ניהול תאריכי חריגים")
        print("3. צפייה בוועדות וזמנים")
        print("4. יצירת אירוע חדש")
        print("5. צפייה באירועים קיימים")
        print("6. לוח זמנים חודשי")
        print("7. הצעת תאריכים פנויים לוועדה")
        print("8. יציאה")
        print("="*60)
        
    def manage_hativot_maslulim(self):
        """Manage divisions and routes"""
        while True:
            print("\n--- ניהול חטיבות ומסלולים ---")
            print("1. הצגת חטיבות קיימות")
            print("2. הוספת חטיבה חדשה")
            print("3. הצגת מסלולים")
            print("4. הוספת מסלול חדש")
            print("5. חזרה לתפריט הראשי")
            
            choice = input("\nבחר אפשרות: ").strip()
            
            if choice == '1':
                self.display_hativot()
            elif choice == '2':
                self.add_hativa()
            elif choice == '3':
                self.display_maslulim()
            elif choice == '4':
                self.add_maslul()
            elif choice == '5':
                break
            else:
                print("אפשרות לא תקינה")
    
    def display_hativot(self):
        """Display all divisions"""
        hativot = self.db.get_hativot()
        if not hativot:
            print("אין חטיבות במערכת")
            return
            
        print("\nחטיבות במערכת:")
        print("-" * 50)
        for hativa in hativot:
            print(f"ID: {hativa['hativa_id']} | שם: {hativa['name']}")
            if hativa['description']:
                print(f"  תיאור: {hativa['description']}")
    
    def add_hativa(self):
        """Add a new division"""
        name = input("שם החטיבה: ").strip()
        if not name:
            print("שם החטיבה הוא שדה חובה")
            return
            
        description = input("תיאור החטיבה (אופציונלי): ").strip()
        
        try:
            hativa_id = self.db.add_hativa(name, description)
            print(f"חטיבה '{name}' נוספה בהצלחה (ID: {hativa_id})")
        except Exception as e:
            print(f"שגיאה בהוספת החטיבה: {e}")
    
    def display_maslulim(self):
        """Display all routes"""
        maslulim = self.db.get_maslulim()
        if not maslulim:
            print("אין מסלולים במערכת")
            return
            
        print("\nמסלולים במערכת:")
        print("-" * 70)
        current_hativa = None
        for maslul in maslulim:
            if current_hativa != maslul['hativa_name']:
                current_hativa = maslul['hativa_name']
                print(f"\n{current_hativa}:")
            print(f"  ID: {maslul['maslul_id']} | {maslul['name']}")
            if maslul['description']:
                print(f"    תיאור: {maslul['description']}")
    
    def add_maslul(self):
        """Add a new route"""
        # First show available divisions
        hativot = self.db.get_hativot()
        if not hativot:
            print("אין חטיבות במערכת. יש להוסיף חטיבה תחילה.")
            return
            
        print("\nחטיבות זמינות:")
        for hativa in hativot:
            print(f"{hativa['hativa_id']}. {hativa['name']}")
        
        try:
            hativa_id = int(input("\nבחר מספר חטיבה: ").strip())
            if not any(h['hativa_id'] == hativa_id for h in hativot):
                print("מספר חטיבה לא תקין")
                return
        except ValueError:
            print("מספר חטיבה לא תקין")
            return
            
        name = input("שם המסלול: ").strip()
        if not name:
            print("שם המסלול הוא שדה חובה")
            return
            
        description = input("תיאור המסלול (אופציונלי): ").strip()
        
        try:
            maslul_id = self.db.add_maslul(hativa_id, name, description)
            print(f"מסלול '{name}' נוסף בהצלחה (ID: {maslul_id})")
        except Exception as e:
            print(f"שגיאה בהוספת המסלול: {e}")
    
    def manage_exception_dates(self):
        """Manage exception dates"""
        while True:
            print("\n--- ניהול תאריכי חריגים ---")
            print("1. הצגת תאריכי חריגים")
            print("2. הוספת תאריך חריג")
            print("3. חזרה לתפריט הראשי")
            
            choice = input("\nבחר אפשרות: ").strip()
            
            if choice == '1':
                self.display_exception_dates()
            elif choice == '2':
                self.add_exception_date()
            elif choice == '3':
                break
            else:
                print("אפשרות לא תקינה")
    
    def display_exception_dates(self):
        """Display all exception dates"""
        exception_dates = self.db.get_exception_dates()
        if not exception_dates:
            print("אין תאריכי חריגים במערכת")
            return
            
        print("\nתאריכי חריגים:")
        print("-" * 50)
        for exc_date in exception_dates:
            date_str = exc_date['exception_date']
            print(f"{date_str} | {exc_date['type']} | {exc_date['description']}")
    
    def add_exception_date(self):
        """Add an exception date"""
        date_str = input("תאריך (YYYY-MM-DD): ").strip()
        try:
            exception_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print("פורמט תאריך לא תקין. השתמש ב-YYYY-MM-DD")
            return
            
        description = input("תיאור התאריך: ").strip()
        date_type = input("סוג התאריך (holiday/sabbath/special): ").strip() or "holiday"
        
        try:
            self.db.add_exception_date(exception_date, description, date_type)
            print(f"תאריך חריג {date_str} נוסף בהצלחה")
        except Exception as e:
            print(f"שגיאה בהוספת התאריך: {e}")
    
    def display_committees(self):
        """Display all committees and their schedules"""
        committees = self.db.get_vaadot()
        print("\nוועדות במערכת:")
        print("-" * 60)
        
        for committee in committees:
            print(f"שם: {committee['name']}")
            print(f"יום: {committee['scheduled_day_name']}")
            print(f"תדירות: {committee['frequency']}")
            if committee['week_of_month']:
                print(f"שבוע בחודש: {committee['week_of_month']}")
            print("-" * 30)
    
    def create_event(self):
        """Create a new event"""
        print("\n--- יצירת אירוע חדש ---")
        
        # Show available committees
        committees = self.db.get_vaadot()
        print("\nוועדות זמינות:")
        for i, committee in enumerate(committees, 1):
            print(f"{i}. {committee['name']} ({committee['scheduled_day_name']})")
        
        try:
            committee_choice = int(input("\nבחר מספר ועדה: ").strip()) - 1
            if committee_choice < 0 or committee_choice >= len(committees):
                print("מספר ועדה לא תקין")
                return
            selected_committee = committees[committee_choice]
        except ValueError:
            print("מספר ועדה לא תקין")
            return
        
        # Show available routes
        maslulim = self.db.get_maslulim()
        if not maslulim:
            print("אין מסלולים במערכת. יש להוסיף מסלולים תחילה.")
            return
            
        print("\nמסלולים זמינים:")
        current_hativa = None
        route_map = {}
        counter = 1
        
        for maslul in maslulim:
            if current_hativa != maslul['hativa_name']:
                current_hativa = maslul['hativa_name']
                print(f"\n{current_hativa}:")
            print(f"  {counter}. {maslul['name']}")
            route_map[counter] = maslul
            counter += 1
        
        try:
            route_choice = int(input("\nבחר מספר מסלול: ").strip())
            if route_choice not in route_map:
                print("מספר מסלול לא תקין")
                return
            selected_route = route_map[route_choice]
        except ValueError:
            print("מספר מסלול לא תקין")
            return
        
        # Get event details
        event_name = input("שם האירוע: ").strip()
        if not event_name:
            print("שם האירוע הוא שדה חובה")
            return
        
        print("\nסוג האירוע:")
        print("1. קו\"ק")
        print("2. שוטף")
        
        event_type_choice = input("בחר סוג אירוע (1-2): ").strip()
        if event_type_choice == '1':
            event_type = 'kokok'
        elif event_type_choice == '2':
            event_type = 'shotef'
        else:
            print("סוג אירוע לא תקין")
            return
        
        try:
            expected_requests = int(input("היקף בקשות צפוי (מספר): ").strip() or "0")
        except ValueError:
            expected_requests = 0
        
        # Validate event data
        event_data = {
            'vaadot_id': selected_committee['vaadot_id'],
            'maslul_id': selected_route['maslul_id'],
            'name': event_name,
            'event_type': event_type,
            'expected_requests': expected_requests
        }
        
        is_valid, message = self.scheduler.validate_event_scheduling(event_data)
        if not is_valid:
            print(f"שגיאה באימות האירוע: {message}")
            return
        
        # Create the event
        try:
            event_id = self.db.add_event(
                selected_committee['vaadot_id'],
                selected_route['maslul_id'],
                event_name,
                event_type,
                expected_requests
            )
            print(f"\nאירוע '{event_name}' נוצר בהצלחה!")
            print(f"ועדה: {selected_committee['name']}")
            print(f"מסלול: {selected_route['name']} ({selected_route['hativa_name']})")
            print(f"סוג: {'קו\"ק' if event_type == 'kokok' else 'שוטף'}")
            print(f"ID אירוע: {event_id}")
        except Exception as e:
            print(f"שגיאה ביצירת האירוע: {e}")
    
    def display_events(self):
        """Display all events"""
        events = self.db.get_events()
        if not events:
            print("אין אירועים במערכת")
            return
            
        print("\nאירועים במערכת:")
        print("-" * 80)
        
        for event in events:
            print(f"שם: {event['name']}")
            print(f"ועדה: {event['vaadot_name']}")
            print(f"מסלול: {event['maslul_name']} ({event['hativa_name']})")
            print(f"סוג: {'קו\"ק' if event['event_type'] == 'kokok' else 'שוטף'}")
            print(f"בקשות צפויות: {event['expected_requests']}")
            print(f"סטטוס: {event['status']}")
            if event['scheduled_date']:
                print(f"תאריך מתוזמן: {event['scheduled_date']}")
            print("-" * 40)
    
    def display_monthly_schedule(self):
        """Display monthly schedule"""
        try:
            year = int(input("שנה (YYYY): ").strip() or str(date.today().year))
            month = int(input("חודש (1-12): ").strip() or str(date.today().month))
        except ValueError:
            print("שנה או חודש לא תקינים")
            return
        
        try:
            schedule = self.scheduler.get_monthly_schedule(year, month)
            
            print(f"\nלוח זמנים לחודש {month}/{year}")
            print("=" * 60)
            
            print(f"ימי עסקים בחודש: {len(schedule['business_days'])}")
            print(f"ימי חריג: {len(schedule['exception_dates'])}")
            
            print("\nוועדות מתוזמנות:")
            for committee_name, dates in schedule['committees'].items():
                print(f"\n{committee_name}:")
                if not dates:
                    print("  אין תאריכים מתוזמנים")
                else:
                    for date_info in dates:
                        status = "✓" if date_info['can_schedule'] else "✗"
                        print(f"  {status} {date_info['date']} - {date_info['reason']}")
                        
        except Exception as e:
            print(f"שגיאה בהצגת הלוח: {e}")
    
    def suggest_committee_dates(self):
        """Suggest available dates for a committee"""
        committees = self.db.get_vaadot()
        print("\nוועדות זמינות:")
        for i, committee in enumerate(committees, 1):
            print(f"{i}. {committee['name']}")
        
        try:
            committee_choice = int(input("\nבחר מספר ועדה: ").strip()) - 1
            if committee_choice < 0 or committee_choice >= len(committees):
                print("מספר ועדה לא תקין")
                return
            selected_committee = committees[committee_choice]
        except ValueError:
            print("מספר ועדה לא תקין")
            return
        
        suggestions = self.scheduler.suggest_next_available_dates(
            selected_committee['name'], 
            date.today(), 
            10
        )
        
        print(f"\nתאריכים מוצעים עבור {selected_committee['name']}:")
        print("-" * 70)
        
        for suggestion in suggestions:
            status = "✓ זמין" if suggestion['can_schedule'] else "✗ לא זמין"
            week_info = f"({suggestion['week_committees']} וועדות בשבוע)"
            third_week = " [שבוע שלישי]" if suggestion['is_third_week'] else ""
            
            print(f"{suggestion['date']} | {status} {week_info}{third_week}")
            if not suggestion['can_schedule']:
                print(f"  סיבה: {suggestion['reason']}")
    
    def run(self):
        """Run the main application"""
        print("ברוכים הבאים למערכת איזון עומסים")
        
        while True:
            self.display_menu()
            choice = input("\nבחר אפשרות: ").strip()
            
            if choice == '1':
                self.manage_hativot_maslulim()
            elif choice == '2':
                self.manage_exception_dates()
            elif choice == '3':
                self.display_committees()
            elif choice == '4':
                self.create_event()
            elif choice == '5':
                self.display_events()
            elif choice == '6':
                self.display_monthly_schedule()
            elif choice == '7':
                self.suggest_committee_dates()
            elif choice == '8':
                print("להתראות!")
                break
            else:
                print("אפשרות לא תקינה, נסה שוב")

if __name__ == "__main__":
    app = CommitteeSystemApp()
    app.run()
