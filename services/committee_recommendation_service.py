#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Committee Recommendation Service
מערכת המלצה לועדות מתאימות עבור אירועים חדשים
"""

from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass


@dataclass
class CommitteeRecommendation:
    """המלצה לועדה"""
    vaadot_id: int
    committee_name: str
    hativa_name: str
    vaada_date: str
    score: float
    reasons: List[str]
    warnings: List[str]
    is_available: bool


class CommitteeRecommendationService:
    """שירות המלצה לועדות מתאימות"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def recommend_committees(self, maslul_id: int, expected_requests: int = 0, 
                           event_name: str = "", limit: int = 5) -> List[Dict]:
        """
        מציע ועדות מתאימות לאירוע חדש
        
        Args:
            maslul_id: מזהה המסלול
            expected_requests: מספר בקשות צפויות
            event_name: שם האירוע (אופציונלי)
            limit: מספר מקסימלי של המלצות
            
        Returns:
            רשימת המלצות מסודרת לפי רלוונטיות
        """
        # קבל את המסלול
        maslul = self.db.get_maslul_by_id(maslul_id)
        if not maslul:
            return []
        
        hativa_id = maslul['hativa_id']
        sla_days = maslul.get('sla_days', 45)
        
        # קבל את כל הועדות מהחטיבה הרלוונטית
        # נשתמש ב-start_date כדי לקבל רק ועדות עתידיות ישירות מהDB
        today = date.today()
        all_committees = self.db.get_vaadot(hativa_id=hativa_id, start_date=today)
        
        if not all_committees:
            return []
        
        # חשב ציון לכל ועדה
        recommendations = []
        for committee in all_committees:
            try:
                recommendation = self._score_committee(
                    committee, 
                    hativa_id, 
                    sla_days, 
                    expected_requests,
                    today
                )
                recommendations.append(recommendation)
            except Exception:
                # Skip committees that fail scoring
                continue
        
        # מיין לפי ציון (גבוה לנמוך)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # החזר את המלצות המובילות
        return recommendations[:limit]
    
    def _score_committee(self, committee: Dict, hativa_id: int, sla_days: int, 
                        expected_requests: int, today: date) -> Dict:
        """
        חשב ציון התאמה לועדה
        
        הקריטריונים:
        1. זמינות (האם יש מספיק מקום לבקשות)
        2. טיימינג (האם התאריך מתאים ל-SLA)
        3. עומס (כמה אירועים כבר יש בועדה)
        4. קרבה (ועדות קרובות יותר מקבלות ציון נמוך יותר)
        """
        vaada_date = self._parse_date(committee['vaada_date'])
        days_until_meeting = (vaada_date - today).days
        
        # Load recommendation settings from database
        rec_settings = {
            'base_score': self.db.get_int_setting('rec_base_score', 100),
            'best_bonus': self.db.get_int_setting('rec_best_bonus', 25),
            'space_bonus': self.db.get_int_setting('rec_space_bonus', 10),
            'sla_bonus': self.db.get_int_setting('rec_sla_bonus', 20),
            'optimal_range_bonus': self.db.get_int_setting('rec_optimal_range_bonus', 15),
            'no_events_bonus': self.db.get_int_setting('rec_no_events_bonus', 5),
            'high_load_penalty': self.db.get_int_setting('rec_high_load_penalty', 15),
            'medium_load_penalty': self.db.get_int_setting('rec_medium_load_penalty', 5),
            'no_space_penalty': self.db.get_int_setting('rec_no_space_penalty', 50),
            'no_sla_penalty': self.db.get_int_setting('rec_no_sla_penalty', 30),
            'tight_sla_penalty': self.db.get_int_setting('rec_tight_sla_penalty', 10),
            'far_future_penalty': self.db.get_int_setting('rec_far_future_penalty', 10),
            'week_full_penalty': self.db.get_int_setting('rec_week_full_penalty', 20),
            'optimal_range_start': self.db.get_int_setting('rec_optimal_range_start', 0),
            'optimal_range_end': self.db.get_int_setting('rec_optimal_range_end', 30),
            'far_future_threshold': self.db.get_int_setting('rec_far_future_threshold', 60)
        }
        
        score = float(rec_settings['base_score'])  # ציון התחלתי
        reasons = []
        warnings = []
        is_available = True
        
        # 1. בדיקת זמינות מקום
        max_requests = int(self.db.get_system_setting('max_requests_per_day') or '100')
        current_requests = self.db.get_total_requests_on_date(vaada_date)
        available_space = max_requests - current_requests
        
        if available_space >= expected_requests:
            # הודעה מותאמת לפי המצב האמיתי
            if current_requests == 0:
                # אין בקשות בכלל - זמינות מלאה
                reasons.append(f"זמינות מלאה - {available_space}/{max_requests} מקומות")
            elif expected_requests > 0:
                # יש בקשות והמשתמש מזין כמות ספציפית
                usage_percent = (current_requests / max_requests * 100) if max_requests > 0 else 0
                reasons.append(f"יש מקום ל-{expected_requests} בקשות (פנוי: {available_space}/{max_requests}, עומס: {usage_percent:.0f}%)")
            else:
                # יש בקשות אבל המשתמש לא הזין כמות
                usage_percent = (current_requests / max_requests * 100) if max_requests > 0 else 0
                reasons.append(f"יש {available_space} מקומות פנויים מתוך {max_requests} (עומס: {usage_percent:.0f}%)")
            score += rec_settings['space_bonus']
        else:
            warnings.append(f"אין מספיק מקום (פנוי: {available_space}, נדרש: {expected_requests})")
            score -= rec_settings['no_space_penalty']
            is_available = False
        
        # 2. בדיקת התאמה ל-SLA
        if days_until_meeting >= sla_days:
            time_buffer = days_until_meeting - sla_days
            reasons.append(f"זמן מספיק ל-SLA ({time_buffer} ימים נוספים)")
            score += min(time_buffer * 0.5, rec_settings['sla_bonus'])
        elif days_until_meeting >= sla_days * 0.8:
            warnings.append(f"זמן SLA צפוף ({days_until_meeting}/{sla_days} ימים)")
            score -= rec_settings['tight_sla_penalty']
        else:
            warnings.append(f"לא מספיק זמן ל-SLA (נדרש: {sla_days}, יש: {days_until_meeting})")
            score -= rec_settings['no_sla_penalty']
            is_available = False
        
        # 3. בדיקת עומס הועדה
        try:
            existing_events = self.db.get_events(vaadot_id=committee['vaadot_id'])
            num_events = len(existing_events) if existing_events else 0
        except TypeError:
            # Fallback if get_events doesn't support vaadot_id parameter
            all_events = self.db.get_events()
            existing_events = [e for e in all_events if e.get('vaadot_id') == committee['vaadot_id']]
            num_events = len(existing_events)
        
        if num_events == 0:
            reasons.append("אין אירועים קיימים - זמינות מלאה")
            score += rec_settings['no_events_bonus']
        elif num_events <= 3:
            reasons.append(f"עומס נמוך ({num_events} אירועים)")
        elif num_events <= 6:
            warnings.append(f"עומס בינוני ({num_events} אירועים)")
            score -= rec_settings['medium_load_penalty']
        else:
            warnings.append(f"עומס גבוה ({num_events} אירועים)")
            score -= rec_settings['high_load_penalty']
        
        # 4. העדפה לועדות בטווח אופטימלי (לא קרוב מדי, לא רחוק מדי)
        optimal_range_start = sla_days + rec_settings['optimal_range_start']
        optimal_range_end = sla_days + rec_settings['optimal_range_end']
        
        if optimal_range_start <= days_until_meeting <= optimal_range_end:
            reasons.append("בטווח זמן אופטימלי")
            score += rec_settings['optimal_range_bonus']
        elif days_until_meeting > optimal_range_end + rec_settings['far_future_threshold']:
            warnings.append(f"רחוק מדי בעתיד ({days_until_meeting} ימים)")
            score -= rec_settings['far_future_penalty']
        
        # 5. בדיקת אילוצים שבועיים
        week_start, week_end = self._get_week_bounds(vaada_date)
        weekly_count = self.db.get_meetings_count_in_range(week_start, week_end)
        constraint_settings = self.db.get_constraint_settings()
        weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
        
        if weekly_count >= weekly_limit:
            warnings.append(f"השבוע מלא ({weekly_count}/{weekly_limit} ועדות)")
            score -= rec_settings['week_full_penalty']
            is_available = False
        
        # 6. בונוס לועדה הראשונה הזמינה
        if is_available and not warnings:
            score += rec_settings['best_bonus']
            reasons.insert(0, "⭐ מומלץ ביותר")
        
        return {
            'vaadot_id': committee['vaadot_id'],
            'committee_name': committee['committee_name'],
            'hativa_name': committee['hativa_name'],
            'vaada_date': committee['vaada_date'],
            'days_until_meeting': days_until_meeting,
            'score': max(0, score),  # ציון לא יכול להיות שלילי
            'reasons': reasons,
            'warnings': warnings,
            'is_available': is_available,
            'current_requests': current_requests,
            'available_space': available_space,
            'num_events': num_events
        }
    
    def _parse_date(self, date_str: str) -> date:
        """המרת מחרוזת תאריך לאובייקט date"""
        if isinstance(date_str, date):
            return date_str
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return date.today()
    
    def _get_week_bounds(self, check_date: date) -> tuple:
        """החזר תחילת וסוף השבוע (ראשון-שבת)"""
        days_since_sunday = (check_date.weekday() + 1) % 7
        week_start = check_date - timedelta(days=days_since_sunday)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end
    
    def _get_weekly_limit(self, check_date: date, constraint_settings: Dict) -> int:
        """החזר את מגבלת הועדות השבועית"""
        limit = constraint_settings['max_weekly_meetings']
        if self._is_third_week_of_month(check_date):
            limit = constraint_settings['max_third_week_meetings']
        return limit
    
    def _is_third_week_of_month(self, check_date: date) -> bool:
        """בדוק אם התאריך נמצא בשבוע השלישי של החודש"""
        first_day = date(check_date.year, check_date.month, 1)
        days_to_first_sunday = (6 - first_day.weekday()) % 7
        first_sunday = first_day + timedelta(days=days_to_first_sunday)
        third_week_start = first_sunday + timedelta(weeks=2)
        third_week_end = third_week_start + timedelta(days=6)
        return third_week_start <= check_date <= third_week_end

