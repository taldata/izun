#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to update SLA data for existing routes (maslulim) based on provided data
"""

from database import DatabaseManager

def update_sla_data():
    """Update SLA data for existing routes"""
    db = DatabaseManager()
    
    # SLA data mapping based on the provided information
    sla_data = {
        # הזנק Division
        'הזנק': 45,
        'זירה': 45,
        'זירה + מסלול': 45,
        'הזנק קרן פרה-סיד (מסלול 7)': 45,
        'הזנק קרן הון אנושי להייטק': 55,
        'הזנק הליך תחרותי': 55,
        'הזנק סיד היברידי': 20,
        'הזנק מעבדות חדשנות': 45,
        'הזנק חממות': 45,
        'הזנק תנופה': 45,
        
        # צמיחה Division
        'צמיחה': 55,
        'צמיחה קרן הסיד (מסלול 7)': 45,
        'צמיחה קרן A (מסלול 7)': 45,
        'צמיחה קרן המו"פ': 55,
        'צמיחה פיילוטים': 55,
        'צמיחה פיילוט רחפנים': 55,
        'צמיחה פליטת גזי חממה': 55,
        'צמיחה חדשנות משבשת': 55,
        'צמיחה ערוץ מהיר': 22,
        
        # תשתיות Division
        'תשתיות': 55,
        'תשתיות מאגדי מגנט (5א\')': 55,
        'תשתיות מאגד בהתקשרויות יחידניות תעשיה': 55,
        'תשתיות מאגד בהתקשרות יחידניות אקדמיה': 55,
        'תשתיות המסלול המשותף עם משרד הביטחון (מימ"ד)': 55,
        'תשתיות מסחור ידע (5ד\')': 55,
        'תשתיות מחקר יישומי באקדמיה (5ג\')': 55,
        'תשתיות תשתיות מו"פ לתעשייה (5ב\')': 55,
        'תשתיות מחקר יישומי בתעשיה (5ה\')': 55,
        
        # חצ Division (assuming this exists)
        'חצ אימפקט': 55,
        'חצ חרדים מיעוטים ואנשים': 55,
        'חצ עזרטק גדולה': 55,
        'חצ עזרטק בינונית': 55,
        'חצ עזרטק קטנה': 55,
        'חצ אתגר': 55,
        'חצ ממשל-טק מעל 300 אשח': 55,
        'חצ ממשל-טק עד 300 אשח': 55,
        'חצ הון אנושי': 55,
        'חצ הון אנושי - התמחות להייטק': 55,
        'חצ הון אנושי - הסדנה': 55,
        'חצ קרן הון אנושי - להייטק (הכשרות)': 55,
        
        # יצור מתקדם Division
        'ייצור מתקדם מופ"ת 36א\'': 55,
        'ייצור מתקדם מעבר מפיתוח לייצור': 55,
        'ייצור מתקדם מכינה': 55,
        'ייצור מתקדם בדיקת עמידה בתנאי סף': 55,
        
        # בינלאומי Division
        'בינלאומי יורוסטארס': 78,
        'בינלאומי EURKEA': 78,
        'בינלאומי Eranet במימון משותף (כולל יורוסטארס)': 78,
        'בינלאומי בילטראלי - דו לאומי (תמיכה מקבילה)': 78,
        'בינלאומי בינלאומי בדיקה מקדמית': 78,
        'בינלאומי פיילוטים אנרגיה': 78,
        'בינלאומי פיילוטים': 78,
        'בינלאומי התאמה לשווקים': 78,
        'בינלאומי שת"פ תאגידי MNC': 78,
        'בינלאומי מרכז פארק תעשייתי סין (CIP)': 78,
        'בינלאומי קרנות': 78,
        'בינלאומי I4F ישראל הודו': 78,
        'בינלאומי SIIRD קרן': 78,
        'בינלאומי קרן Ciirdf': 78,
        'בינלאומי Koril קרן': 78,
        'בינלאומי קרן Birdf': 78,
        
        # איסרד Division
        'איסרד': 55,
        'איסרד מקוצר': 30,
        'איסרד Horizon 2020': 55,
        
        # חט' תפעול Division
        'חט\' תפעול התקשרויות': 2,
        'חט\' תפעול בקשות שינויים': 15,  # Assuming default
        'חט\' תפעול סגירה': 15,  # Assuming default
        'חט\' תפעול קניין רוחני והשקעות': 6,
        'חט\' תפעול תמריצים - 20 א לפקודת מ"ה': 15,
        'חט\' תפעול תמריצים - הפחתת מחזור בסיס': 15,
        'חט\' תפעול תמריצים - לפי חוק האנג\'לים': 15,
        'חט\' תפעול תמריצים - הכרה כחברה המבצעת מו"פ לחברה זרה': 6,
        'חט\' תפעול תמריצים- הרשות לפיתוח ירושלים': 3,
        'חט\' תפעול תמריצים- סעיף 18 לחוק עידוד השקעות הון': 15,  # Assuming default
        'חט\' תפעול תמריצים- מפעל מקדם חדשנות': 15,  # Assuming default
        'חט\' תפעול תמריצים- הכרה כחברת מו"פ לבורסה': 6,
        'חט\' תפעול תמריצים- רשות האוכלוסין': 15,  # Assuming default
        'חט\' תפעול תמריצים- מימון המונים': 15,  # Assuming default
    }
    
    try:
        # Get all existing routes
        maslulim = db.get_maslulim()
        updated_count = 0
        
        print("מתחיל עדכון נתוני SLA למסלולים...")
        
        for maslul in maslulim:
            maslul_name = maslul['name']
            
            # Try to find exact match first
            if maslul_name in sla_data:
                sla_days = sla_data[maslul_name]
                success = db.update_maslul(maslul['maslul_id'], maslul_name, maslul['description'], sla_days)
                if success:
                    print(f"✅ עודכן: {maslul_name} -> SLA: {sla_days} ימים")
                    updated_count += 1
                else:
                    print(f"❌ שגיאה בעדכון: {maslul_name}")
            else:
                # Try partial matching for routes that might have slight variations
                found_match = False
                for sla_name, sla_days in sla_data.items():
                    if sla_name in maslul_name or maslul_name in sla_name:
                        success = db.update_maslul(maslul['maslul_id'], maslul_name, maslul['description'], sla_days)
                        if success:
                            print(f"✅ עודכן (התאמה חלקית): {maslul_name} -> SLA: {sla_days} ימים")
                            updated_count += 1
                            found_match = True
                            break
                        else:
                            print(f"❌ שגיאה בעדכון: {maslul_name}")
                
                if not found_match:
                    print(f"⚠️  לא נמצא SLA עבור: {maslul_name} (נשאר ברירת מחדל: 45)")
        
        print(f"\n✅ הושלם! עודכנו {updated_count} מתוך {len(maslulim)} מסלולים")
        
    except Exception as e:
        print(f"❌ שגיאה בעדכון נתוני SLA: {str(e)}")

if __name__ == '__main__':
    update_sla_data()
