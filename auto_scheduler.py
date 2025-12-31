#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import calendar
from database import DatabaseManager

class AutoMeetingScheduler:
    """
    מנגנון יצירה אוטומטית של ישיבות וועדות על בסיס אילוצים עסקיים
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def our_weekday_to_python_weekday(self, our_weekday: int) -> int:
        """
        המרה מימי השבוע שלנו (0=ראשון, 1=שני...) לימי השבוע של Python (0=שני, 6=ראשון)
        """
        # המערכת שלנו: 0=ראשון, 1=שני, 2=שלישי, 3=רביעי, 4=חמישי
        # Python: 0=שני, 1=שלישי, 2=רביעי, 3=חמישי, 4=שישי, 5=שבת, 6=ראשון
        mapping = {
            0: 6,  # ראשון -> 6
            1: 0,  # שני -> 0
            2: 1,  # שלישי -> 1
            3: 2,  # רביעי -> 2
            4: 3   # חמישי -> 3
        }
        return mapping.get(our_weekday, -1)
    
    def is_business_day(self, check_date: date) -> bool:
        """בדיקה האם התאריך הוא יום עסקים בהתאם להגדרות המערכת"""
        return self.db.is_work_day(check_date)
    
    def get_third_week_of_month(self, year: int, month: int) -> Tuple[date, date]:
        """
        חישוב השבוע השלישי של החודש
        מחזיר תאריך התחלה וסיום של השבוע השלישי
        """
        # מציאת היום הראשון של החודש
        first_day = date(year, month, 1)
        
        # מציאת יום ראשון הראשון של החודש
        days_to_first_sunday = (6 - first_day.weekday()) % 7
        first_sunday = first_day + timedelta(days=days_to_first_sunday)
        
        # השבוע השלישי מתחיל ביום ראשון השלישי
        third_week_start = first_sunday + timedelta(weeks=2)
        third_week_end = third_week_start + timedelta(days=6)
        
        return third_week_start, third_week_end
    
    def count_meetings_in_week(self, check_date: date) -> int:
        """
        ספירת מספר הישיבות בשבוע של התאריך הנתון
        """
        # מציאת תחילת השבוע (יום ראשון)
        days_since_sunday = (check_date.weekday() + 1) % 7
        week_start = check_date - timedelta(days=days_since_sunday)
        week_end = week_start + timedelta(days=6)
        
        # ספירת ישיבות בשבוע
        return self.db.get_meetings_count_in_range(week_start, week_end)
    
    def is_third_week_of_month(self, check_date: date) -> bool:
        """
        בדיקה האם התאריך נמצא בשבוע השלישי של החודש
        """
        third_week_start, third_week_end = self.get_third_week_of_month(
            check_date.year, check_date.month
        )
        return third_week_start <= check_date <= third_week_end
    
    def can_schedule_meeting(self, committee_type_id: int, target_date: date, hativa_id: int, is_admin: bool = False) -> Tuple[bool, str]:
        """
        בדיקה האם ניתן לתזמן ישיבה בתאריך נתון
        is_admin: אם True, אילוצים הופכים להתראות במקום חסימות
        """
        # בדיקת יום עסקים
        if not self.is_business_day(target_date):
            return False, "התאריך אינו יום עסקים (שבת/חג/יום שבתון)"
        
        # קבלת פרטי סוג הועדה מהמסד נתונים
        committee_types = self.db.get_committee_types(hativa_id)
        committee_type_data = next((ct for ct in committee_types if ct['committee_type_id'] == committee_type_id), None)
        
        if not committee_type_data:
            return False, f"סוג ועדה לא נמצא: {committee_type_id}"
        
        # ועדה תפעולית: עוקפים את כל האילוצים למעט יום עסקים
        if committee_type_data.get('is_operational'):
            if not self.is_business_day(target_date):
                return False, "התאריך אינו יום עסקים (שבת/חג/יום שבתון)"
            return True, "ועדה תפעולית - ללא אילוצי תדירות/שבוע/קיבולת"
        
        expected_weekday = committee_type_data['scheduled_day']
        committee_name = committee_type_data['name']
        frequency = committee_type_data['frequency']
        week_of_month = committee_type_data.get('week_of_month')
            
        # המרת יום השבוע שלנו ליום השבוע של Python
        expected_python_weekday = self.our_weekday_to_python_weekday(expected_weekday)
        if target_date.weekday() != expected_python_weekday:
            weekday_names = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
            expected_day_name = weekday_names[expected_weekday]
            return False, f"ועדה זו מתקיימת רק בימי {expected_day_name}"
        
        constraint_settings = self.db.get_constraint_settings()
        warnings = []

        # בדיקת ועדה אחת ביום (על פי מגבלת המערכת)
        if not self.db.is_date_available_for_meeting(target_date):
            max_per_day = constraint_settings['max_meetings_per_day']
            constraint_msg = "קיימת כבר ישיבה אחרת באותו תאריך" if max_per_day == 1 else f"מכסת הישיבות היומית ({max_per_day}) נוצלה בתאריך זה"
            if is_admin:
                warnings.append(f"⚠️ {constraint_msg}")
            else:
                return False, constraint_msg

        # בדיקת מגבלות שבועיות
        week_meetings = self.count_meetings_in_week(target_date)
        is_third_week = self.is_third_week_of_month(target_date)

        weekly_limit = constraint_settings['max_weekly_meetings']
        third_week_limit = constraint_settings['max_third_week_meetings']
        allowed_weekly = third_week_limit if is_third_week else weekly_limit
        if week_meetings >= allowed_weekly:
            constraint_msg = f"מכסת הישיבות השבועית ({allowed_weekly}) נוצלה השבוע"
            if is_admin:
                warnings.append(f"⚠️ {constraint_msg}")
            else:
                return False, constraint_msg
        
        # בדיקה מיוחדת לועדות חודשיות - רק בשבוע המתאים
        if frequency == 'monthly':
            if week_of_month:
                # בדיקה שהתאריך נמצא בשבוע הנכון של החודש
                week_num = (target_date.day - 1) // 7 + 1
                if week_num != week_of_month:
                    return False, f"ועדה חודשית זו מתקיימת רק בשבוע {week_of_month} של החודש"
        
        # בדיקה שאין כפילות לאותה ועדה ואותה חטיבה
        existing_meetings = self.db.get_vaadot()
        for meeting in existing_meetings:
            if (meeting.get('committee_type_id') == committee_type_id and 
                meeting.get('hativa_id') == hativa_id and 
                meeting.get('vaada_date')):
                try:
                    meeting_date = datetime.strptime(meeting['vaada_date'], '%Y-%m-%d').date()
                    # בדיקה שלא עברו פחות מ-7 ימים (למניעת כפילות שבועיות)
                    if frequency == 'weekly' and abs((meeting_date - target_date).days) < 7:
                        return False, "קיימת כבר ישיבה דומה לאותה חטיבה השבוע"
                    elif frequency == 'monthly' and meeting_date.month == target_date.month and meeting_date.year == target_date.year:
                        return False, "קיימת כבר ישיבה דומה לאותה חטיבה החודש"
                except (ValueError, TypeError):
                    continue
        
        # Return success with any warnings for admins
        if warnings:
            return True, f"ניתן לתזמן ישיבה. {' '.join(warnings)}"
        return True, "ניתן לתזמן ישיבה"
    
    def find_next_available_date(self, committee_type_id: int, hativa_id: int, 
                                start_date: date = None, max_days: int = 90) -> Optional[date]:
        """
        מציאת התאריך הזמין הבא לועדה
        """
        if start_date is None:
            start_date = date.today()
        
        # קבלת פרטי סוג הועדה מהמסד נתונים
        committee_types = self.db.get_committee_types(hativa_id)
        committee_type_data = next((ct for ct in committee_types if ct['committee_type_id'] == committee_type_id), None)
        
        if not committee_type_data:
            return None
        
        expected_weekday = committee_type_data['scheduled_day']
        frequency = committee_type_data['frequency']
        week_of_month = committee_type_data.get('week_of_month')
        
        current_date = start_date
        days_checked = 0
        
        while days_checked < max_days:
            # בדיקה שהיום הוא היום הנכון בשבוע
            expected_python_weekday = self.our_weekday_to_python_weekday(expected_weekday)
            if current_date.weekday() == expected_python_weekday:
                # בדיקה נוספת לועדות חודשיות - שהן בשבוע הנכון
                if frequency == 'monthly' and week_of_month:
                    week_num = (current_date.day - 1) // 7 + 1
                    if week_num != week_of_month:
                        current_date += timedelta(days=1)
                        days_checked += 1
                        continue
                
                can_schedule, _ = self.can_schedule_meeting(committee_type_id, current_date, hativa_id)
                if can_schedule:
                    return current_date
            
            current_date += timedelta(days=1)
            days_checked += 1
        
        return None
    
    def find_available_dates(self, committee_type_id: int, hativa_id: int,
                              start_date: Optional[date] = None, max_results: int = 5,
                              max_days: int = 180) -> List[date]:
        """
        מציאת רשימת תאריכים פנויים עבור ועדה נתונה
        """
        if start_date is None:
            start_date = date.today()

        if max_results <= 0:
            return []

        committee_types = self.db.get_committee_types(hativa_id)
        committee_type_data = next(
            (ct for ct in committee_types if ct['committee_type_id'] == committee_type_id),
            None
        )

        if not committee_type_data:
            return []

        expected_weekday = committee_type_data['scheduled_day']
        frequency = committee_type_data['frequency']
        week_of_month = committee_type_data.get('week_of_month')
        expected_python_weekday = self.our_weekday_to_python_weekday(expected_weekday)

        available_dates: List[date] = []
        current_date = start_date
        days_checked = 0

        while len(available_dates) < max_results and days_checked < max_days:
            if current_date.weekday() == expected_python_weekday:
                if frequency == 'monthly' and week_of_month:
                    week_num = (current_date.day - 1) // 7 + 1
                    if week_num != week_of_month:
                        current_date += timedelta(days=1)
                        days_checked += 1
                        continue

                can_schedule, _ = self.can_schedule_meeting(committee_type_id, current_date, hativa_id)
                if can_schedule:
                    available_dates.append(current_date)

            current_date += timedelta(days=1)
            days_checked += 1

        return available_dates

    def generate_monthly_schedule(self, year: int, month: int, 
                                 hativot_ids: List[int] = None) -> Dict:
        """
        יצירת לוח זמנים חודשי אוטומטי
        """
        if hativot_ids is None:
            hativot = self.db.get_hativot()
            hativot_ids = [h['hativa_id'] for h in hativot]
        
        # התחלה מהיום הראשון של החודש
        start_date = date(year, month, 1)
        
        # סיום בסוף החודש
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        suggested_meetings = []
        
        for hativa_id in hativot_ids:
            # קבלת סוגי הועדות הספציפיים לחטיבה זו
            committee_types = self.db.get_committee_types(hativa_id)
            
            for committee_type_data in committee_types:
                committee_type_id = committee_type_data['committee_type_id']
                committee_name = committee_type_data['name']
                frequency = committee_type_data['frequency']
                week_of_month = committee_type_data.get('week_of_month')
                
                if frequency == 'weekly':
                    # ישיבות שבועיות
                    current_date = start_date
                    while current_date <= end_date:
                        suggested_date = self.find_next_available_date(
                            committee_type_id, hativa_id, current_date, 7
                        )
                        if suggested_date and suggested_date <= end_date:
                            suggested_meetings.append({
                                'committee_type': committee_name,
                                'committee_type_id': committee_type_id,
                                'hativa_id': hativa_id,
                                'date': suggested_date.strftime('%Y-%m-%d'),
                                'suggested_date': suggested_date,
                                'frequency': frequency
                            })
                            current_date = suggested_date + timedelta(days=7)
                        else:
                            break
                            
                elif frequency == 'monthly':
                    # ישיבה חודשית - בשבוע המתאים
                    if week_of_month:
                        # חישוב תאריך התחלה של השבוע המתאים
                        first_day = date(year, month, 1)
                        days_to_target_week = (week_of_month - 1) * 7
                        week_start = first_day + timedelta(days=days_to_target_week)
                        
                        suggested_date = self.find_next_available_date(
                            committee_type_id, hativa_id, week_start, 7
                        )
                        if suggested_date and suggested_date.month == month:
                            suggested_meetings.append({
                                'committee_type': committee_name,
                                'committee_type_id': committee_type_id,
                                'hativa_id': hativa_id,
                                'date': suggested_date.strftime('%Y-%m-%d'),
                                'suggested_date': suggested_date,
                                'frequency': frequency
                            })
        
        return {
            'year': year,
            'month': month,
            'suggested_meetings': suggested_meetings,
            'total_suggestions': len(suggested_meetings)
        }
    
    def create_meetings_from_suggestions(self, suggestions: List[Dict]) -> Dict:
        """
        יצירת ישיבות מרשימת הצעות - כל הישיבות נוצרות בסטטוס 'scheduled'
        """
        created_meetings = []
        failed_meetings = []
        
        for suggestion in suggestions:
            try:
                # המרת תאריך לאובייקט date אם נדרש
                suggested_date = suggestion['suggested_date']
                if isinstance(suggested_date, str):
                    suggested_date = datetime.strptime(suggested_date, '%Y-%m-%d').date()
                
                # בדיקה נוספת לפני יצירה
                can_create, reason = self.can_schedule_meeting(
                    suggestion['committee_type_id'],
                    suggested_date,
                    suggestion['hativa_id']
                )
                
                if can_create:
                    # כל הישיבות נוצרות בסטטוס "מתוזמן"
                    meeting_id, warning = self.db.add_vaada(
                        committee_type_id=suggestion['committee_type_id'],
                        hativa_id=suggestion['hativa_id'],
                        vaada_date=suggested_date,
                        notes=f"נוצר אוטומטית - {suggestion['frequency']}"
                    )
                    
                    created_meetings.append({
                        'meeting_id': meeting_id,
                        'committee_type': suggestion['committee_type'],
                        'date': suggested_date,
                        'status': 'scheduled'
                    })
                else:
                    failed_meetings.append({
                        'committee_type': suggestion['committee_type'],
                        'date': suggested_date,
                        'reason': reason
                    })
                    
            except Exception as e:
                failed_meetings.append({
                    'committee_type': suggestion.get('committee_type', 'לא ידוע'),
                    'date': suggestion.get('suggested_date', 'לא ידוע'),
                    'reason': f"שגיאה ביצירה: {str(e)}"
                })
        
        return {
            'created_meetings': created_meetings,
            'failed_meetings': failed_meetings,
            'success_count': len(created_meetings),
            'failure_count': len(failed_meetings)
        }
    
    def validate_schedule_constraints(self, year: int, month: int) -> Dict:
        """
        אימות שהלוח הזמנים עומד באילוצים
        """
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        meetings = self.db.get_vaadot()
        monthly_meetings = []
        
        for meeting in meetings:
            if meeting.get('vaada_date'):
                try:
                    meeting_date = datetime.strptime(meeting['vaada_date'], '%Y-%m-%d').date()
                    if start_date <= meeting_date <= end_date:
                        monthly_meetings.append(meeting)
                except (ValueError, TypeError):
                    continue
        
        violations = []
        warnings = []
        
        # בדיקת אילוצים
        for meeting in monthly_meetings:
            if meeting.get('vaada_date'):
                try:
                    meeting_date = datetime.strptime(meeting['vaada_date'], '%Y-%m-%d').date()
                    
                    # בדיקת יום עסקים
                    if not self.is_business_day(meeting_date):
                        violations.append(f"ישיבה בתאריך {meeting_date} אינה ביום עסקים")
                except (ValueError, TypeError):
                    continue
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'total_meetings': len(monthly_meetings)
        }
