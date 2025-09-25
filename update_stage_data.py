#!/usr/bin/env python3
"""
סקריפט לעדכון נתוני השלבים במסלולים קיימים
מוסיף ערכי ברירת מחדל לשדות החדשים: stage_a_days, stage_b_days, stage_c_days, stage_d_days
"""

import sqlite3
import sys
import os

def update_stage_data():
    """עדכון נתוני השלבים במסלולים קיימים"""
    
    # התחבר למסד הנתונים
    db_path = "committee_system.db"
    if not os.path.exists(db_path):
        print(f"❌ מסד הנתונים {db_path} לא נמצא")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 בודק מסלולים קיימים...")
        
        # קבל את כל המסלולים הקיימים
        cursor.execute('''
            SELECT maslul_id, name, sla_days, stage_a_days, stage_b_days, stage_c_days, stage_d_days
            FROM maslulim 
            ORDER BY maslul_id
        ''')
        
        maslulim = cursor.fetchall()
        
        if not maslulim:
            print("ℹ️  לא נמצאו מסלולים במערכת")
            return True
        
        print(f"📊 נמצאו {len(maslulim)} מסלולים")
        
        updated_count = 0
        
        for maslul in maslulim:
            maslul_id, name, sla_days, stage_a, stage_b, stage_c, stage_d = maslul
            
            # בדוק אם השדות החדשים ריקים או None
            needs_update = (stage_a is None or stage_b is None or 
                          stage_c is None or stage_d is None)
            
            if needs_update:
                # חשב ערכי ברירת מחדל בהתבסס על SLA
                total_sla = sla_days or 45
                
                # חלוקה פרופורציונלית של SLA לשלבים
                # שלב א: 22% מה-SLA (בערך 10 ימים מתוך 45)
                # שלב ב: 33% מה-SLA (בערך 15 ימים מתוך 45)  
                # שלב ג: 22% מה-SLA (בערך 10 ימים מתוך 45)
                # שלב ד: 22% מה-SLA (בערך 10 ימים מתוך 45)
                
                new_stage_a = stage_a if stage_a is not None else max(1, int(total_sla * 0.22))
                new_stage_b = stage_b if stage_b is not None else max(1, int(total_sla * 0.33))
                new_stage_c = stage_c if stage_c is not None else max(1, int(total_sla * 0.22))
                
                # שלב ד יהיה השאר כדי שהסכום יהיה בדיוק SLA
                calculated_d = total_sla - new_stage_a - new_stage_b - new_stage_c
                new_stage_d = stage_d if stage_d is not None else max(1, calculated_d)
                
                # וודא שהסכום שווה ל-SLA
                total_stages = new_stage_a + new_stage_b + new_stage_c + new_stage_d
                if total_stages != total_sla:
                    # התאם את שלב ד כדי שהסכום יהיה מדויק
                    new_stage_d = total_sla - new_stage_a - new_stage_b - new_stage_c
                    new_stage_d = max(1, new_stage_d)  # וודא שהוא לפחות 1
                
                # עדכן את המסלול
                cursor.execute('''
                    UPDATE maslulim 
                    SET stage_a_days = ?, stage_b_days = ?, stage_c_days = ?, stage_d_days = ?
                    WHERE maslul_id = ?
                ''', (new_stage_a, new_stage_b, new_stage_c, new_stage_d, maslul_id))
                
                updated_count += 1
                
                print(f"✅ עודכן מסלול '{name}' (ID: {maslul_id}):")
                print(f"   SLA כולל: {total_sla} ימים")
                print(f"   שלב א: {new_stage_a} ימים")
                print(f"   שלב ב: {new_stage_b} ימים") 
                print(f"   שלב ג: {new_stage_c} ימים")
                print(f"   שלב ד: {new_stage_d} ימים")
                print(f"   סכום: {new_stage_a + new_stage_b + new_stage_c + new_stage_d} ימים")
                print()
            else:
                print(f"ℹ️  מסלול '{name}' כבר מעודכן")
        
        # שמור את השינויים
        conn.commit()
        
        print(f"🎉 עדכון הושלם בהצלחה!")
        print(f"📈 עודכנו {updated_count} מסלולים מתוך {len(maslulim)}")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בעדכון הנתונים: {str(e)}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def verify_stage_data():
    """אימות נתוני השלבים לאחר העדכון"""
    
    db_path = "committee_system.db"
    if not os.path.exists(db_path):
        print(f"❌ מסד הנתונים {db_path} לא נמצא")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 אימות נתוני השלבים...")
        
        cursor.execute('''
            SELECT m.name, h.name as hativa_name, m.sla_days, 
                   m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days,
                   (m.stage_a_days + m.stage_b_days + m.stage_c_days + m.stage_d_days) as total_stages
            FROM maslulim m
            JOIN hativot h ON m.hativa_id = h.hativa_id
            ORDER BY h.name, m.name
        ''')
        
        results = cursor.fetchall()
        
        print(f"\n📊 דוח נתוני שלבים ({len(results)} מסלולים):")
        print("=" * 100)
        
        current_hativa = None
        valid_count = 0
        invalid_count = 0
        
        for row in results:
            name, hativa_name, sla_days, stage_a, stage_b, stage_c, stage_d, total_stages = row
            
            if current_hativa != hativa_name:
                if current_hativa is not None:
                    print()
                print(f"\n🏢 חטיבת {hativa_name}:")
                print("-" * 50)
                current_hativa = hativa_name
            
            # בדוק אם הסכום תואם ל-SLA
            is_valid = (total_stages == sla_days)
            status = "✅" if is_valid else "❌"
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
            
            print(f"{status} {name}")
            print(f"    SLA: {sla_days} | שלבים: {stage_a}+{stage_b}+{stage_c}+{stage_d}={total_stages}")
            
            if not is_valid:
                print(f"    ⚠️  אי-התאמה: הפרש של {abs(total_stages - sla_days)} ימים")
        
        print("\n" + "=" * 100)
        print(f"📈 סיכום אימות:")
        print(f"✅ מסלולים תקינים: {valid_count}")
        print(f"❌ מסלולים עם אי-התאמה: {invalid_count}")
        
        if invalid_count == 0:
            print("🎉 כל המסלולים תקינים!")
        else:
            print("⚠️  יש מסלולים עם אי-התאמה שדורשים תיקון ידני")
        
    except Exception as e:
        print(f"❌ שגיאה באימות הנתונים: {str(e)}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 מתחיל עדכון נתוני השלבים במסלולים...")
    print("=" * 60)
    
    success = update_stage_data()
    
    if success:
        verify_stage_data()
    else:
        print("❌ העדכון נכשל")
        sys.exit(1)
    
    print("\n✨ הסקריפט הושלם בהצלחה!")
