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
        
        # הגדרת ימי הועדות הקבועים
        self.committee_days = {
            'ועדת הזנק': 0,      # יום שני (Monday = 0)
            'ועדת תשתיות': 2,    # יום רביעי (Wednesday = 2)  
            'ועדת צמיחה': 3,     # יום חמישי (Thursday = 3)
            'ייצור מתקדם': 1     # יום שלישי (Tuesday = 1) - חודשי
        }
        
        # הגדרת תדירות הועדות
        self.committee_frequency = {
            'ועדת הזנק': 'weekly',
            'ועדת תשתיות': 'weekly',
            'ועדת צמיחה': 'weekly',
            'ייצור מתקדם': 'monthly'  # שבוע שלישי בחודש
        }
    
    def is_business_day(self, check_date: date) -> bool:
        """
        בדיקה האם התאריך הוא יום עסקים
        """
        # בדיקת שבת (יום 5 = שבת)
        if check_date.weekday() == 5:
            return False
            
        # בדיקת חגים ותאריכי חריגים
        exception_dates = self.db.get_exception_dates()
        for exc_date in exception_dates:
            exc_date_str = exc_date.get('exception_date')
            if exc_date_str:
                try:
                    exc_date_obj = datetime.strptime(exc_date_str, '%Y-%m-%d').date()
                    if exc_date_obj == check_date:
                        return False
                except (ValueError, TypeError):
                    continue
                
        return True
    
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
        meetings = self.db.get_vaadot()
        week_meetings = 0
        
        for meeting in meetings:
            meeting_date = datetime.strptime(meeting['vaada_date'], '%Y-%m-%d').date()
            if week_start <= meeting_date <= week_end:
                week_meetings += 1
                
        return week_meetings
    
    def is_third_week_of_month(self, check_date: date) -> bool:
        """
        בדיקה האם התאריך נמצא בשבוע השלישי של החודש
        """
        third_week_start, third_week_end = self.get_third_week_of_month(
            check_date.year, check_date.month
        )
        return third_week_start <= check_date <= third_week_end
    
    def can_schedule_meeting(self, committee_type: str, target_date: date, hativa_id: int) -> Tuple[bool, str]:
        """
        בדיקה האם ניתן לתזמן ישיבה בתאריך נתון
        """
        # בדיקת יום עסקים
        if not self.is_business_day(target_date):
            return False, "התאריך אינו יום עסקים (שבת/חג/יום שבתון)"
        
        # בדיקת יום השבוע הנכון לועדה
        expected_weekday = self.committee_days.get(committee_type)
        if expected_weekday is None:
            return False, f"סוג ועדה לא מוכר: {committee_type}"
            
        if target_date.weekday() != expected_weekday:
            weekday_names = ['שני', 'שלישי', 'רביעי', 'חמישי', 'חמישי', 'שישי', 'ראשון']
            expected_day_name = weekday_names[expected_weekday]
            return False, f"ועדה זו מתקיימת רק בימי {expected_day_name}"
        
        # בדיקת ועדה אחת ביום
        existing_meetings = self.db.get_vaadot()
        for meeting in existing_meetings:
            if meeting.get('vaada_date'):
                try:
                    meeting_date = datetime.strptime(meeting['vaada_date'], '%Y-%m-%d').date()
                    if meeting_date == target_date:
                        return False, "קיימת כבר ישיבה אחרת באותו תאריך"
                except (ValueError, TypeError):
                    continue
        
        # בדיקת מגבלות שבועיות
        week_meetings = self.count_meetings_in_week(target_date)
        is_third_week = self.is_third_week_of_month(target_date)
        
        max_weekly_meetings = 4 if is_third_week else 3
        if week_meetings >= max_weekly_meetings:
            return False, f"הושג מספר הישיבות המקסימלי השבועי ({max_weekly_meetings})"
        
        # בדיקה מיוחדת לייצור מתקדם - רק בשבוע השלישי
        if committee_type == 'ייצור מתקדם' and not is_third_week:
            return False, "ועדת ייצור מתקדם מתקיימת רק בשבוע השלישי של החודש"
        
        # בדיקה שאין כפילות לאותה ועדה ואותה חטיבה
        for meeting in existing_meetings:
            if (meeting.get('committee_name') == committee_type and 
                meeting.get('hativa_id') == hativa_id and 
                meeting.get('vaada_date')):
                try:
                    meeting_date = datetime.strptime(meeting['vaada_date'], '%Y-%m-%d').date()
                    # בדיקה שלא עברו פחות מ-7 ימים (למניעת כפילות שבועיות)
                    if abs((meeting_date - target_date).days) < 7:
                        return False, "קיימת כבר ישיבה דומה לאותה חטיבה השבוע"
                except (ValueError, TypeError):
                    continue
        
        return True, "ניתן לתזמן ישיבה"
    
    def find_next_available_date(self, committee_type: str, hativa_id: int, 
                                start_date: date = None, max_days: int = 90) -> Optional[date]:
        """
        מציאת התאריך הזמין הבא לועדה
        """
        if start_date is None:
            start_date = date.today()
            
        expected_weekday = self.committee_days.get(committee_type)
        if expected_weekday is None:
            return None
        
        current_date = start_date
        days_checked = 0
        
        while days_checked < max_days:
            # דילוג לתאריך הבא עם היום הנכון בשבוע
            if current_date.weekday() != expected_weekday:
                days_to_add = (expected_weekday - current_date.weekday()) % 7
                if days_to_add == 0:
                    days_to_add = 7  # השבוע הבא
                current_date += timedelta(days=days_to_add)
            
            # בדיקה האם ניתן לתזמן
            can_schedule, reason = self.can_schedule_meeting(committee_type, current_date, hativa_id)
            if can_schedule:
                return current_date
            
            # מעבר לשבוע הבא
            current_date += timedelta(days=7)
            days_checked += 7
            
        return None
    
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
        committee_types = self.db.get_committee_types()
        
        for committee_type_data in committee_types:
            committee_name = committee_type_data['name']
            frequency = self.committee_frequency.get(committee_name, 'weekly')
            
            for hativa_id in hativot_ids:
                if frequency == 'weekly':
                    # ישיבות שבועיות
                    current_date = start_date
                    while current_date <= end_date:
                        suggested_date = self.find_next_available_date(
                            committee_name, hativa_id, current_date, 7
                        )
                        if suggested_date and suggested_date <= end_date:
                            suggested_meetings.append({
                                'committee_type': committee_name,
                                'committee_type_id': committee_type_data['committee_type_id'],
                                'hativa_id': hativa_id,
                                'date': suggested_date.strftime('%Y-%m-%d'),
                                'suggested_date': suggested_date,
                                'frequency': frequency
                            })
                            current_date = suggested_date + timedelta(days=7)
                        else:
                            break
                            
                elif frequency == 'monthly':
                    # ישיבה חודשית - רק בשבוע השלישי
                    third_week_start, third_week_end = self.get_third_week_of_month(year, month)
                    suggested_date = self.find_next_available_date(
                        committee_name, hativa_id, third_week_start, 7
                    )
                    if suggested_date and third_week_start <= suggested_date <= third_week_end:
                        suggested_meetings.append({
                            'committee_type': committee_name,
                            'committee_type_id': committee_type_data['committee_type_id'],
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
    
    def create_meetings_from_suggestions(self, suggestions: List[Dict], 
                                       auto_approve: bool = False) -> Dict:
        """
        יצירת ישיבות מרשימת הצעות
        """
        created_meetings = []
        failed_meetings = []
        
        for suggestion in suggestions:
            try:
                # בדיקה נוספת לפני יצירה
                can_create, reason = self.can_schedule_meeting(
                    suggestion['committee_type'],
                    suggestion['suggested_date'],
                    suggestion['hativa_id']
                )
                
                if can_create:
                    status = 'scheduled' if auto_approve else 'planned'
                    meeting_id = self.db.add_vaada(
                        committee_type_id=suggestion['committee_type_id'],
                        hativa_id=suggestion['hativa_id'],
                        vaada_date=suggestion['suggested_date'],
                        status=status,
                        notes=f"נוצר אוטומטית - {suggestion['frequency']}"
                    )
                    
                    created_meetings.append({
                        'meeting_id': meeting_id,
                        'committee_type': suggestion['committee_type'],
                        'date': suggestion['suggested_date'],
                        'status': status
                    })
                else:
                    failed_meetings.append({
                        'committee_type': suggestion['committee_type'],
                        'date': suggestion['suggested_date'],
                        'reason': reason
                    })
                    
            except Exception as e:
                failed_meetings.append({
                    'committee_type': suggestion['committee_type'],
                    'date': suggestion['suggested_date'],
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
