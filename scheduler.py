from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import calendar
from database import DatabaseManager

class CommitteeScheduler:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
        # Committee scheduling rules
        self.committee_days = {
            'ועדת הזנק': 0,      # Monday
            'ועדת תשתיות': 2,    # Wednesday  
            'ועדת צמיחה': 3,     # Thursday
            'ייצור מתקדם': 1     # Tuesday (monthly, third week)
        }
    
    def is_business_day(self, check_date: date) -> bool:
        """Check if a date is a business day (not weekend, not holiday)"""
        # Check if it's a weekend (Friday=4, Saturday=5 in Python's weekday())
        if check_date.weekday() >= 5:  # Friday or Saturday
            return False
        
        # Check if it's an exception date (holiday, special sabbath, etc.)
        if self.db.is_exception_date(check_date):
            return False
        
        return True
    
    def get_week_number_in_month(self, check_date: date) -> int:
        """Get the week number within the month (1-5)"""
        first_day = check_date.replace(day=1)
        first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)
        
        if check_date < first_monday:
            return 1
        
        weeks_passed = (check_date - first_monday).days // 7 + 2
        return min(weeks_passed, 5)
    
    def is_third_week_of_month(self, check_date: date) -> bool:
        """Check if the date falls in the third week of the month"""
        return self.get_week_number_in_month(check_date) == 3
    
    def get_valid_committee_dates(self, committee_name: str, start_date: date, end_date: date) -> List[date]:
        """Get all valid dates for a specific committee within a date range"""
        valid_dates = []
        
        if committee_name not in self.committee_days:
            return valid_dates
        
        target_weekday = self.committee_days[committee_name]
        current_date = start_date
        
        # Find first occurrence of the target weekday
        while current_date.weekday() != target_weekday:
            current_date += timedelta(days=1)
        
        while current_date <= end_date:
            if self.is_business_day(current_date):
                # Special handling for monthly committees
                if committee_name == 'ייצור מתקדם':
                    if self.is_third_week_of_month(current_date):
                        valid_dates.append(current_date)
                else:
                    # Weekly committees
                    valid_dates.append(current_date)
            
            # Move to next occurrence
            if committee_name == 'ייצור מתקדם':
                # Monthly - move to next month's third week
                next_month = current_date.replace(day=1) + timedelta(days=32)
                next_month = next_month.replace(day=1)
                current_date = next_month
                while current_date.weekday() != target_weekday:
                    current_date += timedelta(days=1)
                # Find third week
                while not self.is_third_week_of_month(current_date):
                    current_date += timedelta(days=7)
            else:
                # Weekly - move to next week
                current_date += timedelta(days=7)
        
        return valid_dates
    
    def get_weekly_schedule_conflicts(self, check_date: date) -> Dict:
        """Check for scheduling conflicts in a given week"""
        # Get the Monday of the week containing check_date
        monday = check_date - timedelta(days=check_date.weekday())
        week_dates = [monday + timedelta(days=i) for i in range(7)]
        
        conflicts = {
            'committees_this_week': [],
            'total_committees': 0,
            'is_third_week': self.is_third_week_of_month(check_date),
            'max_allowed': 4 if self.is_third_week_of_month(check_date) else 3
        }
        
        # Check each committee's potential scheduling for this week
        for committee_name, weekday in self.committee_days.items():
            committee_date = week_dates[weekday]
            
            if self.is_business_day(committee_date):
                if committee_name == 'ייצור מתקדם':
                    if self.is_third_week_of_month(committee_date):
                        conflicts['committees_this_week'].append({
                            'committee': committee_name,
                            'date': committee_date,
                            'weekday': weekday
                        })
                        conflicts['total_committees'] += 1
                else:
                    conflicts['committees_this_week'].append({
                        'committee': committee_name,
                        'date': committee_date,
                        'weekday': weekday
                    })
                    conflicts['total_committees'] += 1
        
        conflicts['has_conflict'] = conflicts['total_committees'] > conflicts['max_allowed']
        
        return conflicts
    
    def can_schedule_committee(self, committee_name: str, target_date: date) -> Tuple[bool, str]:
        """Check if a committee can be scheduled on a specific date"""
        # Basic validations
        if not self.is_business_day(target_date):
            return False, "התאריך אינו יום עסקים (סוף שבוע או חג)"
        
        if committee_name not in self.committee_days:
            return False, "ועדה לא מוכרת במערכת"
        
        # Check correct weekday
        expected_weekday = self.committee_days[committee_name]
        if target_date.weekday() != expected_weekday:
            weekday_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי']
            return False, f"ועדה זו מתקיימת ב{weekday_names[expected_weekday]}"
        
        # Special validation for monthly committees
        if committee_name == 'ייצור מתקדם':
            if not self.is_third_week_of_month(target_date):
                return False, "ועדת ייצור מתקדם מתקיימת רק בשבוע השלישי של החודש"
        
        # Check weekly limits
        week_conflicts = self.get_weekly_schedule_conflicts(target_date)
        
        # Check if there's already a committee on this specific date
        for committee_info in week_conflicts['committees_this_week']:
            if committee_info['date'] == target_date and committee_info['committee'] != committee_name:
                return False, f"כבר קיימת ועדה ביום זה: {committee_info['committee']}"
        
        # Check weekly committee limits
        if week_conflicts['has_conflict']:
            return False, f"חריגה ממספר הוועדות המותר בשבוע ({week_conflicts['max_allowed']})"
        
        return True, "ניתן לתזמן ועדה בתאריך זה"
    
    def suggest_next_available_dates(self, committee_name: str, from_date: date = None, count: int = 5) -> List[Dict]:
        """Suggest next available dates for a committee"""
        if from_date is None:
            from_date = date.today()
        
        # Look ahead up to 6 months
        end_date = from_date + timedelta(days=180)
        
        valid_dates = self.get_valid_committee_dates(committee_name, from_date, end_date)
        suggestions = []
        
        for valid_date in valid_dates[:count]:
            can_schedule, reason = self.can_schedule_committee(committee_name, valid_date)
            week_info = self.get_weekly_schedule_conflicts(valid_date)
            
            suggestions.append({
                'date': valid_date,
                'can_schedule': can_schedule,
                'reason': reason,
                'week_committees': len(week_info['committees_this_week']),
                'is_third_week': week_info['is_third_week']
            })
        
        return suggestions
    
    def get_monthly_schedule(self, year: int, month: int) -> Dict:
        """Get the complete schedule for a specific month"""
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        
        monthly_schedule = {
            'year': year,
            'month': month,
            'committees': {},
            'business_days': [],
            'exception_dates': []
        }
        
        # Get all business days in the month
        current_date = first_day
        while current_date <= last_day:
            if self.is_business_day(current_date):
                monthly_schedule['business_days'].append(current_date)
            elif self.db.is_exception_date(current_date):
                monthly_schedule['exception_dates'].append(current_date)
            current_date += timedelta(days=1)
        
        # Get scheduled committees for each committee type
        for committee_name in self.committee_days.keys():
            committee_dates = self.get_valid_committee_dates(committee_name, first_day, last_day)
            monthly_schedule['committees'][committee_name] = []
            
            for committee_date in committee_dates:
                can_schedule, reason = self.can_schedule_committee(committee_name, committee_date)
                monthly_schedule['committees'][committee_name].append({
                    'date': committee_date,
                    'can_schedule': can_schedule,
                    'reason': reason
                })
        
        return monthly_schedule
    
    def validate_event_scheduling(self, event_data: Dict) -> Tuple[bool, str]:
        """Validate if an event can be scheduled with the given committee"""
        vaadot_id = event_data.get('vaadot_id')
        
        # Get committee information
        committees = self.db.get_vaadot()
        committee = next((c for c in committees if c['vaadot_id'] == vaadot_id), None)
        
        if not committee:
            return False, "ועדה לא נמצאה במערכת"
        
        # Validate required fields
        required_fields = ['name', 'event_type', 'maslul_id']
        for field in required_fields:
            if not event_data.get(field):
                return False, f"שדה חובה חסר: {field}"
        
        # Validate event type
        if event_data['event_type'] not in ['kokok', 'shotef']:
            return False, "סוג אירוע חייב להיות 'קו\"ק' או 'שוטף'"
        
        # Validate route exists
        routes = self.db.get_maslulim()
        route = next((r for r in routes if r['maslul_id'] == event_data['maslul_id']), None)
        
        if not route:
            return False, "מסלול לא נמצא במערכת"
        
        return True, "האירוע תקין ויכול להיות מתוזמן"
