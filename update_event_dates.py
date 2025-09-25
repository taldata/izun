#!/usr/bin/env python3
"""
סקריפט לעדכון התאריכים הנגזרים באירועים קיימים
מחשב תאריכי דדליין בהתבסס על תאריך הועדה ושדות השלבים במסלול
"""

import sqlite3
import sys
import os
from datetime import date, timedelta

def update_event_dates():
    """עדכון התאריכים הנגזרים באירועים קיימים"""
    
    # התחבר למסד הנתונים
    db_path = "committee_system.db"
    if not os.path.exists(db_path):
        print(f"❌ מסד הנתונים {db_path} לא נמצא")
        return False
    
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("🔍 בודק אירועים קיימים...")
        
        # קבל את כל האירועים הקיימים עם נתוני הועדה והמסלול
        cursor.execute('''
            SELECT e.event_id, e.name as event_name, v.vaada_date,
                   m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days,
                   m.name as maslul_name, ct.name as committee_name,
                   e.call_deadline_date, e.intake_deadline_date, e.review_deadline_date
            FROM events e
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            ORDER BY e.event_id
        ''')
        
        events = cursor.fetchall()
        
        if not events:
            print("ℹ️  לא נמצאו אירועים במערכת")
            return True
        
        print(f"📊 נמצאו {len(events)} אירועים")
        
        updated_count = 0
        
        for event in events:
            event_id, event_name, vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days, maslul_name, committee_name, current_call_date, current_intake_date, current_review_date = event
            
            # בדוק אם התאריכים הנגזרים ריקים או None
            needs_update = (current_call_date is None or current_intake_date is None or current_review_date is None)
            
            if needs_update or True:  # עדכן תמיד כדי לוודא שהתאריכים נכונים
                # חשב את התאריכים הנגזרים
                stage_dates = db.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
                
                # עדכן את האירוע
                cursor.execute('''
                    UPDATE events 
                    SET call_deadline_date = ?, intake_deadline_date = ?, review_deadline_date = ?
                    WHERE event_id = ?
                ''', (stage_dates['call_deadline_date'], stage_dates['intake_deadline_date'], 
                      stage_dates['review_deadline_date'], event_id))
                
                updated_count += 1
                
                print(f"✅ עודכן אירוע '{event_name}' (ID: {event_id}):")
                print(f"   ועדה: {committee_name}")
                print(f"   מסלול: {maslul_name}")
                print(f"   תאריך ועדה: {vaada_date}")
                print(f"   תאריך סיום קול קורא: {stage_dates['call_deadline_date']}")
                print(f"   תאריך סיום קליטה: {stage_dates['intake_deadline_date']}")
                print(f"   תאריך סיום בדיקה: {stage_dates['review_deadline_date']}")
                print(f"   שלבים: {stage_a_days}+{stage_b_days}+{stage_c_days}+{stage_d_days} ימים")
                print()
            else:
                print(f"ℹ️  אירוע '{event_name}' כבר מעודכן")
        
        # שמור את השינויים
        conn.commit()
        
        print(f"🎉 עדכון הושלם בהצלחה!")
        print(f"📈 עודכנו {updated_count} אירועים מתוך {len(events)}")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בעדכון הנתונים: {str(e)}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def verify_event_dates():
    """אימות התאריכים הנגזרים לאחר העדכון"""
    
    db_path = "committee_system.db"
    if not os.path.exists(db_path):
        print(f"❌ מסד הנתונים {db_path} לא נמצא")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 אימות התאריכים הנגזרים...")
        
        cursor.execute('''
            SELECT e.name as event_name, ct.name as committee_name, m.name as maslul_name,
                   v.vaada_date, e.call_deadline_date, e.intake_deadline_date, e.review_deadline_date,
                   m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days,
                   h.name as hativa_name
            FROM events e
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            JOIN hativot h ON m.hativa_id = h.hativa_id
            ORDER BY h.name, ct.name, e.name
        ''')
        
        results = cursor.fetchall()
        
        print(f"\n📊 דוח תאריכים נגזרים ({len(results)} אירועים):")
        print("=" * 120)
        
        current_hativa = None
        valid_count = 0
        invalid_count = 0
        
        for row in results:
            event_name, committee_name, maslul_name, vaada_date, call_date, intake_date, review_date, stage_a, stage_b, stage_c, stage_d, hativa_name = row
            
            if current_hativa != hativa_name:
                if current_hativa is not None:
                    print()
                print(f"\n🏢 חטיבת {hativa_name}:")
                print("-" * 80)
                current_hativa = hativa_name
            
            # בדוק אם כל התאריכים קיימים
            is_valid = (call_date is not None and intake_date is not None and review_date is not None)
            status = "✅" if is_valid else "❌"
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
            
            print(f"{status} {event_name}")
            print(f"    ועדה: {committee_name} | מסלול: {maslul_name}")
            print(f"    תאריך ועדה: {vaada_date}")
            
            if is_valid:
                print(f"    📅 קול קורא: {call_date}")
                print(f"    📅 קליטה: {intake_date}")
                print(f"    📅 בדיקה: {review_date}")
                print(f"    ⏱️  שלבים: {stage_a}+{stage_b}+{stage_c}+{stage_d} ימים")
            else:
                print(f"    ⚠️  תאריכים חסרים!")
            print()
        
        print("=" * 120)
        print(f"📈 סיכום אימות:")
        print(f"✅ אירועים תקינים: {valid_count}")
        print(f"❌ אירועים עם תאריכים חסרים: {invalid_count}")
        
        if invalid_count == 0:
            print("🎉 כל האירועים תקינים!")
        else:
            print("⚠️  יש אירועים עם תאריכים חסרים שדורשים תיקון")
        
    except Exception as e:
        print(f"❌ שגיאה באימות הנתונים: {str(e)}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 מתחיל עדכון התאריכים הנגזרים באירועים...")
    print("=" * 70)
    
    success = update_event_dates()
    
    if success:
        verify_event_dates()
    else:
        print("❌ העדכון נכשל")
        sys.exit(1)
    
    print("\n✨ הסקריפט הושלם בהצלחה!")
