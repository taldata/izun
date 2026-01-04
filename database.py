import os
import re
import urllib.parse
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from zoneinfo import ZoneInfo

# SQLAlchemy ORM imports
from db import get_db_session
from repositories import (
    HativaRepository, MaslulRepository, CommitteeTypeRepository,
    VaadaRepository, EventRepository, UserRepository, SettingsRepository,
    AuditLogRepository, ScheduleDraftRepository, ExceptionDateRepository,
    CalendarSyncRepository
)

ISRAEL_TZ = ZoneInfo('Asia/Jerusalem')

class DatabaseManager:
    def __init__(self, db_path: str = None):
        # Database initialized via db.init_database() in app.py or manual calls
        self.init_database()

    def init_database(self):
        """Initialize database using SQLAlchemy and seed default settings"""
        from db import init_database as sa_init_database
        
        # Create all tables defined in models.py
        sa_init_database()
        
        # Seed default settings
        with get_db_session() as session:
            from repositories.settings_repo import SettingsRepository
            repo = SettingsRepository(session)
            
            default_settings = {
                'editing_period_active': ('1', 'Whether general editing is allowed (1=yes, 0=admin only)'),
                'academic_year_start': ('2024-09-01', 'Start of current academic year'),
                'editing_deadline': ('2024-10-31', 'Deadline for general user editing'),
                'work_days': ('6,0,1,2,3,4', 'Working days (Python weekday: 0=Monday ... 6=Sunday)'),
                'work_start_time': ('08:00', 'Daily work start time'),
                'work_end_time': ('17:00', 'Daily work end time'),
                'sla_days_before': ('14', 'Default SLA days before committee meeting'),
                'max_meetings_per_day': ('1', 'Maximum number of committee meetings per calendar day'),
                'max_weekly_meetings': ('3', 'Maximum number of committee meetings per standard week'),
                'max_third_week_meetings': ('4', 'Maximum number of committee meetings during the third week of a month'),
                'max_requests_committee_date': ('100', 'Maximum total expected requests on committee meeting date'),
                'show_deadline_dates_in_calendar': ('1', 'Show derived deadline dates in calendar (1=yes, 0=no)'),
                'ad_enabled': ('0', 'Enable Active Directory authentication (1=yes, 0=no)'),
                'calendar_sync_enabled': ('1', 'Enable automatic calendar synchronization (1=yes, 0=no)'),
                'calendar_sync_email': ('plan@innovationisrael.org.il', 'Email address of the shared calendar to sync to'),
                'calendar_sync_interval_hours': ('1', 'How often to sync calendar (in hours)')
            }
            
            for key, (value, desc) in default_settings.items():
                if not repo.get_setting(key):
                    repo.update_setting(key, value)
        
        
        
        
        
        

        
        

            


    
    
    def add_hativa(self, name: str, description: str = "", color: str = "#007bff") -> int:
        """Add a new division using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            hativa = repo.create(name, description, color)
            return hativa.hativa_id
    
    def get_hativot(self) -> List[Dict]:
        """Get all divisions using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            hativot = repo.get_all(include_inactive=True)
            result = []
            for h in hativot:
                allowed_days = repo.get_allowed_days(h.hativa_id)
                result.append({
                    'hativa_id': h.hativa_id,
                    'name': h.name,
                    'description': h.description,
                    'color': h.color,
                    'is_active': h.is_active,
                    'created_at': h.created_at,
                    'allowed_days': allowed_days
                })
            return result
    
    def get_hativa_allowed_days(self, hativa_id: int) -> List[int]:
        """Get allowed days of week for a division using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.get_allowed_days(hativa_id)
    
    def set_hativa_allowed_days(self, hativa_id: int, allowed_days: List[int]) -> bool:
        """Set allowed days of week for a division using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.set_allowed_days(hativa_id, allowed_days)
    
    def is_day_allowed_for_hativa(self, hativa_id: int, date_obj: date) -> bool:
        """Check if a date is allowed for a division based on day constraints"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.is_day_allowed(hativa_id, date_obj.weekday())
    
    def update_hativa_color(self, hativa_id: int, color: str) -> bool:
        """Update division color using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.update_color(hativa_id, color)
    
    def update_hativa(self, hativa_id: int, name: str, description: str = "", color: str = "#007bff") -> bool:
        """Update division details using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.update_hativa(hativa_id, name, description, color)
    
    # Maslulim operations
    def add_maslul(self, hativa_id: int, name: str, description: str = "", sla_days: int = 45, 
                   stage_a_days: int = 10, stage_b_days: int = 15, stage_c_days: int = 10, stage_d_days: int = 10) -> int:
        """Add a new route to a division using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            maslul = repo.create(hativa_id, name, description, sla_days,
                                stage_a_days, stage_b_days, stage_c_days, stage_d_days)
            return maslul.maslul_id
    
    def get_maslulim(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get routes, optionally filtered by division using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            maslulim = repo.get_all(hativa_id=hativa_id)
            return [m.to_dict() for m in maslulim]
    
    def update_maslul(self, maslul_id: int, name: str, description: str, sla_days: int, 
                     stage_a_days: int, stage_b_days: int, stage_c_days: int, stage_d_days: int, is_active: bool = True) -> bool:
        """Update an existing route using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            return repo.update_maslul(maslul_id, name, description, sla_days,
                                     stage_a_days, stage_b_days, stage_c_days, stage_d_days, is_active)
    
    def delete_maslul(self, maslul_id: int) -> bool:
        """Delete a route using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            return repo.hard_delete(maslul_id)
    
    # Exception dates operations
    def add_exception_date(self, exception_date: date, description: str = "", date_type: str = "holiday"):
        """Add an exception date using SQLAlchemy"""
        with get_db_session() as session:
            repo = ExceptionDateRepository(session)
            repo.create(exception_date, description, date_type)
    
    def get_exception_dates(self, include_past: bool = False) -> List[Dict]:
        """Get exception dates using SQLAlchemy"""
        with get_db_session() as session:
            repo = ExceptionDateRepository(session)
            items = repo.get_exception_dates(include_past)
            return [item.to_dict() for item in items]
    
    def get_exception_date_by_id(self, date_id: int) -> Optional[Dict]:
        """Get a specific exception date by ID using SQLAlchemy"""
        with get_db_session() as session:
            repo = ExceptionDateRepository(session)
            item = repo.get_by_id(date_id)
            return item.to_dict() if item else None
    
    def update_exception_date(self, date_id: int, exception_date: date, description: str = "", date_type: str = "holiday") -> bool:
        """Update an exception date using SQLAlchemy"""
        with get_db_session() as session:
            repo = ExceptionDateRepository(session)
            return repo.update_date(date_id, exception_date, description, date_type)
    
    def delete_exception_date(self, date_id: int) -> bool:
        """Delete an exception date using SQLAlchemy"""
        with get_db_session() as session:
            repo = ExceptionDateRepository(session)
            if not repo.can_delete(date_id):
                return False
            return repo.delete_by_id(date_id)
    
    def is_exception_date(self, check_date: date) -> bool:
        """Check if a date is an exception date using SQLAlchemy"""
        with get_db_session() as session:
            repo = ExceptionDateRepository(session)
            return repo.is_exception_date(check_date)
    
    def recalculate_all_event_deadlines(self) -> int:
        """Recalculate deadline dates for all existing events based on current exception dates using SQLAlchemy"""
        with get_db_session() as session:
            event_repo = EventRepository(session)
            exception_repo = ExceptionDateRepository(session)
            settings_repo = SettingsRepository(session)
            
            # 1. Get all active events
            active_events = event_repo.get_all_active()
            work_days = settings_repo.get_work_days()
            updated_count = 0
            
            for event in active_events:
                maslul = event.maslul
                vaada = event.vaada
                if not vaada:
                    continue
                    
                # 2. Recalculate stage dates
                stage_dates = event_repo.calculate_stage_dates(
                    vaada.vaada_date,
                    maslul.stage_a_days, maslul.stage_b_days, maslul.stage_c_days, maslul.stage_d_days,
                    lambda d: exception_repo.is_work_day(d, work_days)
                )
                
                # 3. Update the event with new deadline dates (skipping manual call deadlines if they were set)
                # Note: Original code updated ALL fields including call_deadline. 
                # If it was manual, we might want to preserve it, but original code didn't seem to care here.
                # However, calculate_stage_dates returns the base call_deadline.
                
                event.call_deadline_date = stage_dates['call_deadline_date']
                event.intake_deadline_date = stage_dates['intake_deadline_date']
                event.review_deadline_date = stage_dates['review_deadline_date']
                event.response_deadline_date = stage_dates['response_deadline_date']
                updated_count += 1
                
            session.flush()
            return updated_count

    def recalculate_event_deadlines_for_maslul(self, maslul_id: int) -> int:
        """Recalculate deadline dates for all events of a specific maslul using SQLAlchemy"""
        with get_db_session() as session:
            event_repo = EventRepository(session)
            exception_repo = ExceptionDateRepository(session)
            settings_repo = SettingsRepository(session)
            maslul_repo = MaslulRepository(session)
            
            maslul = maslul_repo.get_by_id(maslul_id)
            if not maslul:
                return 0
                
            # Get all events for this maslul
            events = event_repo.get_by_maslul(maslul_id)
            work_days = settings_repo.get_work_days()
            updated_count = 0
            
            for event in events:
                vaada = event.vaada
                if not vaada:
                    continue
                    
                # Recalculate using maslul's current values
                stage_dates = event_repo.calculate_stage_dates(
                    vaada.vaada_date,
                    maslul.stage_a_days, maslul.stage_b_days, maslul.stage_c_days, maslul.stage_d_days,
                    lambda d: exception_repo.is_work_day(d, work_days)
                )
                
                event.call_deadline_date = stage_dates['call_deadline_date']
                event.intake_deadline_date = stage_dates['intake_deadline_date']
                event.review_deadline_date = stage_dates['review_deadline_date']
                event.response_deadline_date = stage_dates['response_deadline_date']
                updated_count += 1
                
            session.flush()
            return updated_count

    # Committee Types operations
    def add_committee_type(self, hativa_id: int, name: str, scheduled_day: int, frequency: str = 'weekly',
                          week_of_month: Optional[int] = None, description: str = "", is_operational: int = 0) -> int:
        """Add a new committee type using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            ct = repo.create(hativa_id, name, scheduled_day, frequency, week_of_month, description, is_operational)
            return ct.committee_type_id
    
    def get_committee_types(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get committee types using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            cts = repo.get_all(hativa_id=hativa_id)
            days = ['יום ראשון', 'יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת']
            result = []
            for ct in cts:
                d = ct.to_dict()
                d['scheduled_day_name'] = days[ct.scheduled_day] if ct.scheduled_day is not None else ''
                result.append(d)
            return result
    
    def update_committee_type(self, committee_type_id: int, hativa_id: int, name: str, scheduled_day: int, 
                             frequency: str = 'weekly', week_of_month: Optional[int] = None, 
                             description: str = "", is_operational: int = 0) -> bool:
        """Update committee type using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            return repo.update_committee_type(committee_type_id, hativa_id, name, scheduled_day, 
                                             frequency, week_of_month, description, is_operational)
    
    def delete_committee_type(self, committee_type_id: int) -> bool:
        """Delete a committee type using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            return repo.hard_delete(committee_type_id)
    
    # Vaadot operations (specific meeting instances)
    def add_vaada(self, committee_type_id: int, hativa_id: int, vaada_date: date,
                  notes: str = "", start_time: str = None, end_time: str = None,
                  created_by: int = None, override_constraints: bool = False) -> tuple[int, str]:
        """
        Add a new committee meeting with constraint checking using SQLAlchemy
        Returns: (vaadot_id, warning_message)
        """
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()

        warning_message = ""
        
        with get_db_session() as session:
            vaada_repo = VaadaRepository(session)
            hativa_repo = HativaRepository(session)
            settings_repo = SettingsRepository(session)
            exception_repo = ExceptionDateRepository(session)
            ct_repo = CommitteeTypeRepository(session)
            
            # 1. Date Availability (One meeting per day)
            count_on_date = vaada_repo.count_meetings_on_date(vaada_date)
            max_per_day = settings_repo.get_int_setting('max_meetings_per_day', 1)
            if count_on_date >= max_per_day:
                msg = f'כבר קיימת ועדה בתאריך {vaada_date}. המערכת מאפשרת רק {max_per_day} ועדה ביום.'
                if override_constraints:
                    warning_message += f'⚠️ אזהרה: {msg} מנהל מערכת יכול לעקוף אילוץ זה.\n'
                else:
                    raise ValueError(msg)
            
            # 2. Business Day Check
            work_days = settings_repo.get_work_days()
            if not exception_repo.is_work_day(vaada_date, work_days):
                msg = f'התאריך {vaada_date} אינו יום עסקים חוקי לועדות (סופ"ש או חג).'
                if override_constraints:
                    warning_message += f'⚠️ אזהרה: {msg}\n'
                else:
                    raise ValueError(msg)
            
            # 3. Hativa allowed days check
            allowed_days = hativa_repo.get_allowed_days(hativa_id)
            if vaada_date.weekday() not in allowed_days:
                day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'יום שבת', 'יום ראשון']
                day_name = day_names[vaada_date.weekday()]
                allowed_day_names = [day_names[d] for d in sorted(allowed_days)]
                msg = f'התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}.'
                if override_constraints:
                    warning_message += f'⚠️ אזהרה: {msg}\n'
                else:
                    raise ValueError(msg)
            
            # 4. Weekly capacity check
            week_start, week_end = vaada_repo.get_week_bounds(vaada_date)
            weekly_count = vaada_repo.get_weekly_count(week_start, week_end)
            constraint_settings = settings_repo.get_constraint_settings()
            
            # Simplified weekly limit logic from DB manager
            limit_key = 'max_meetings_per_week_third' if vaada_repo.is_third_week_of_month(vaada_date) else 'max_meetings_per_week_regular'
            weekly_limit = int(constraint_settings.get(limit_key, 3))
            
            if weekly_count >= weekly_limit:
                msg = f'השבוע של {vaada_date} כבר מכיל {weekly_count} ועדות (המגבלה היא {weekly_limit}).'
                if override_constraints:
                    warning_message += f'⚠️ אזהרה: {msg}\n'
                # Weekly limit is usually a warning in original code if override_constraints=True
            
            # 5. Type duplication check
            existing = vaada_repo.check_existing_match(committee_type_id, hativa_id, vaada_date)
            if existing:
                msg = f'כבר קיימת ועדה מאותו סוג בחטיבה זו בתאריך {vaada_date}.'
                if override_constraints:
                    warning_message += f'⚠️ אזהרה: {msg}\n'
                else:
                    raise ValueError(msg)
            
            # 6. Set defaults from committee type
            if start_time is None or end_time is None:
                ct = ct_repo.get_by_id(committee_type_id)
                if ct:
                    if start_time is None:
                        start_time = "09:00"
                    if end_time is None:
                        end_time = "11:00" if ct.is_operational else "15:00"

            # 7. Create
            vaada = vaada_repo.create(
                committee_type_id=committee_type_id,
                hativa_id=hativa_id,
                vaada_date=vaada_date,
                notes=notes,
                start_time=start_time,
                end_time=end_time
            )
            
            return (vaada.vaadot_id, warning_message.strip())

    
    def is_date_available_for_meeting(self, vaada_date) -> bool:
        """Check if date available for meeting using SQLAlchemy"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        
        with get_db_session() as session:
            repo = VaadaRepository(session)
            count = repo.count_meetings_on_date(vaada_date)
            max_per_day = self.get_int_setting('max_meetings_per_day', 1)
            return count < max_per_day
    
    def get_vaadot(self, hativa_id: Optional[int] = None, start_date: Optional[date] = None, 
                   end_date: Optional[date] = None, include_deleted: bool = False) -> List[Dict]:
        """Get committee meetings using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            vaadot = repo.get_all(hativa_id=hativa_id, start_date=start_date, 
                                 end_date=end_date, include_deleted=include_deleted)
            return [v.to_dict() for v in vaadot]

    def duplicate_vaada_with_events(self, source_vaadot_id: int, target_date: date, created_by: Optional[int] = None,
                                    override_constraints: bool = False) -> dict:
        """
        Duplicate a committee meeting (vaada) and all its events to a new date using SQLAlchemy.
        Returns dict with new_vaadot_id and counts.
        """
        # Fetch source committee details
        source = self.get_vaada_by_id(source_vaadot_id)
        if not source:
            raise ValueError("ועדה מקורית לא נמצאה")

        # Create the new committee meeting using existing SQLAlchemy-based add_vaada
        new_vaadot_id, warning_message = self.add_vaada(
            committee_type_id=int(source['committee_type_id']),
            hativa_id=int(source['hativa_id']),
            vaada_date=target_date,
            notes=source.get('notes') or "",
            created_by=created_by,
            override_constraints=override_constraints
        )

        # Copy events
        events = self.get_events(vaadot_id=source_vaadot_id)
        created_events = 0
        for ev in events:
            # If the source event used a manual call deadline, carry it over; otherwise let it be auto-calculated
            is_manual = bool(ev.get('is_call_deadline_manual'))
            manual_date = ev.get('call_deadline_date') if is_manual else None

            self.add_event(
                vaadot_id=new_vaadot_id,
                maslul_id=int(ev['maslul_id']),
                name=ev['name'],
                event_type=ev['event_type'],
                expected_requests=int(ev.get('expected_requests') or 0),
                actual_submissions=int(ev.get('actual_submissions') or 0),
                call_publication_date=ev.get('call_publication_date'),
                is_call_deadline_manual=is_manual,
                manual_call_deadline_date=manual_date
            )
            created_events += 1

        return {
            'new_vaadot_id': new_vaadot_id,
            'copied_events': created_events,
            'warning_message': warning_message
        }
    
    def update_vaada(self, vaadot_id: int, committee_type_id: int, hativa_id: int,
                     vaada_date: date,
                     exception_date_id: Optional[int] = None, notes: str = "",
                     start_time: str = None, end_time: str = None,
                     user_role: Optional[str] = None) -> bool:
        """Update committee meeting details including date, type, division, and notes using SQLAlchemy"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()

        with get_db_session() as session:
            vaada_repo = VaadaRepository(session)
            hativa_repo = HativaRepository(session)
            ct_repo = CommitteeTypeRepository(session)
            settings_repo = SettingsRepository(session)
            exception_repo = ExceptionDateRepository(session)
            
            # 1. Basic Work Day Check
            work_days = settings_repo.get_work_days()
            if not exception_repo.is_work_day(vaada_date, work_days):
                raise ValueError(f"התאריך {vaada_date} אינו יום עסקים חוקי לועדות")

            # 2. Committee Type Belonging Check
            ct = ct_repo.get_by_id(committee_type_id)
            if not ct:
                raise ValueError("סוג הועדה לא נמצא")
            if ct.hativa_id != hativa_id:
                raise ValueError("סוג הועדה שנבחר אינו שייך לחטיבה שנבחרה")

            # 3. Get Current Record
            vaada = vaada_repo.get_by_id(vaadot_id)
            if not vaada:
                return False
                
            date_is_changing = vaada.vaada_date != vaada_date
            is_admin = user_role == 'admin'

            # 4. In-depth Constraints (if date changed)
            if date_is_changing:
                # 4a. Hativa Day Allowance
                if not is_admin:
                    allowed_days = hativa_repo.get_allowed_days(hativa_id)
                    if vaada_date.weekday() not in allowed_days:
                        day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'יום שבת', 'יום ראשון']
                        day_name = day_names[vaada_date.weekday()]
                        allowed_day_names = [day_names[d] for d in sorted(allowed_days)]
                        raise ValueError(f'התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}')

                # 4b. Daily Capacity
                max_per_day = settings_repo.get_int_setting('max_meetings_per_day', 1)
                count_on_date = vaada_repo.count_meetings_on_date(vaada_date)
                # Since we are excluding our current record, count_on_date is compared to max_per_day directly
                # Wait, count_on_date includes all active meetings on that date.
                # If we are changing to that date, we must make sure there's room.
                if count_on_date >= max_per_day:
                    if max_per_day == 1:
                        raise ValueError(f"כבר קיימת ועדה בתאריך {vaada_date}. לא ניתן לקבוע יותר מועדה אחת ביום.")
                    raise ValueError(f"כבר קיימות {count_on_date} ועדות בתאריך {vaada_date}. המגבלה הנוכחית מאפשרת עד {max_per_day} ועדות ביום.")

                # 4c. Weekly Capacity
                week_start, week_end = vaada_repo.get_week_bounds(vaada_date)
                weekly_count = vaada_repo.get_weekly_count(week_start, week_end, exclude_vaada_id=vaadot_id)
                constraint_settings = settings_repo.get_constraint_settings()
                limit_key = 'max_meetings_per_week_third' if vaada_repo.is_third_week_of_month(vaada_date) else 'max_meetings_per_week_regular'
                weekly_limit = int(constraint_settings.get(limit_key, 3))
                
                if weekly_count >= weekly_limit:
                    week_type = "שבוע שלישי" if vaada_repo.is_third_week_of_month(vaada_date) else "שבוע רגיל"
                    raise ValueError(f"השבוע של {vaada_date} ({week_type}) כבר מכיל {weekly_count} ועדות. העברת הועדה תגרום לסך של {weekly_count+1} ועדות (המגבלה היא {weekly_limit})")

            # 5. Set defaults if BOTH times are missing (legacy support or partial updates)
            if start_time is None and end_time is None:
                if start_time is None:
                    start_time = '09:00'
                if end_time is None:
                    end_time = '11:00' if ct.is_operational else '15:00'

            # 6. Apply Updates
            success = vaada_repo.update_vaada(
                vaadot_id=vaadot_id,
                committee_type_id=committee_type_id,
                hativa_id=hativa_id,
                vaada_date=vaada_date,
                exception_date_id=exception_date_id,
                notes=notes,
                start_time=start_time,
                end_time=end_time
            )
            return success

    def update_vaada_date(self, vaadot_id: int, vaada_date: date, exception_date_id: Optional[int] = None, user_role: Optional[str] = None) -> bool:
        """Update the actual meeting date for a committee and optionally link to exception date using SQLAlchemy"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()

        try:
            with get_db_session() as session:
                vaada_repo = VaadaRepository(session)
                event_repo = EventRepository(session)
                hativa_repo = HativaRepository(session)
                settings_repo = SettingsRepository(session)
                exception_repo = ExceptionDateRepository(session)
                
                # 1. Basic Work Day Check
                work_days = settings_repo.get_work_days()
                if not exception_repo.is_work_day(vaada_date, work_days):
                    raise ValueError(f"התאריך {vaada_date} אינו יום עסקים חוקי לועדות")

                # 2. Fetch Vaada
                vaada = vaada_repo.get_by_id(vaadot_id)
                if not vaada:
                    return False
                    
                # 3. Hativa Day Allowance (non-admin)
                if user_role != 'admin':
                    allowed_days = hativa_repo.get_allowed_days(vaada.hativa_id)
                    if vaada_date.weekday() not in allowed_days:
                        day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'יום שבת', 'יום ראשון']
                        day_name = day_names[vaada_date.weekday()]
                        allowed_day_names = [day_names[d] for d in sorted(allowed_days)]
                        raise ValueError(f'התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}')

                # 4. Daily Capacity
                max_per_day = settings_repo.get_int_setting('max_meetings_per_day', 1)
                count_on_date = vaada_repo.count_meetings_on_date(vaada_date)
                if vaada.vaada_date != vaada_date and count_on_date >= max_per_day:
                    raise ValueError(f"התאריך {vaada_date} כבר מכיל {count_on_date} ועדות (המגבלה היא {max_per_day})")

                # 5. Weekly Capacity
                week_start, week_end = vaada_repo.get_week_bounds(vaada_date)
                weekly_count = vaada_repo.get_weekly_count(week_start, week_end, exclude_vaada_id=vaadot_id)
                constraint_settings = settings_repo.get_constraint_settings()
                limit_key = 'max_meetings_per_week_third' if vaada_repo.is_third_week_of_month(vaada_date) else 'max_meetings_per_week_regular'
                weekly_limit = int(constraint_settings.get(limit_key, 3))
                
                if weekly_count >= weekly_limit:
                    week_type = "שבוע שלישי" if vaada_repo.is_third_week_of_month(vaada_date) else "שבוע רגיל"
                    raise ValueError(f"השבוע של {vaada_date} ({week_type}) כבר מכיל {weekly_count} ועדות. העברת הועדה תגרום לסך של {weekly_count+1} ועדות (המגבלה היא {weekly_limit})")

                # 6. Check derived constraints for each event
                events = [e for e in vaada.events if (e.is_deleted == 0 or e.is_deleted is None)]
                for event in events:
                    maslul = event.maslul
                    stage_dates = event_repo.calculate_stage_dates(
                        vaada_date,
                        maslul.stage_a_days, maslul.stage_b_days, maslul.stage_c_days, maslul.stage_d_days,
                        lambda d: exception_repo.is_work_day(d, work_days)
                    )
                    derived_error = event_repo.check_derived_dates_constraints(stage_dates, event.expected_requests, exclude_event_id=event.event_id)
                    if derived_error:
                        raise ValueError(f"העברת הועדה תגרום לחריגה באירוע {event.event_id}: {derived_error}")

                # 7. Apply Update
                vaada.vaada_date = vaada_date
                vaada.exception_date_id = exception_date_id
                session.flush()
                return True
        except ValueError:
            raise
        except Exception as e:
            print(f"Error updating vaada date: {e}")
            return False

    def delete_vaada(self, vaadot_id: int, user_id: Optional[int] = None) -> bool:
        """Soft delete a committee meeting using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            return repo.soft_delete(vaadot_id, user_id)

    def delete_vaadot_bulk(self, vaadot_ids: List[int], user_id: Optional[int] = None) -> Tuple[int, int]:
        """
        Bulk soft delete committee meetings (vaadot) by IDs using SQLAlchemy.
        Returns (deleted_committees_count, affected_events_count).
        """
        if not vaadot_ids:
            return 0, 0
            
        with get_db_session() as session:
            vaada_repo = VaadaRepository(session)
            event_repo = EventRepository(session)
            
            deleted_vaadot = 0
            affected_events = 0
            
            for vid in vaadot_ids:
                vaada = vaada_repo.get_by_id(int(vid))
                if vaada and (vaada.is_deleted == 0 or vaada.is_deleted is None):
                    # Soft delete related events first
                    for event in vaada.events:
                        if event.is_deleted == 0 or event.is_deleted is None:
                            event_repo.soft_delete(event.event_id, user_id)
                            affected_events += 1
                    
                    # Soft delete the committee
                    vaada_repo.soft_delete(vid, user_id)
                    deleted_vaadot += 1
            
            return deleted_vaadot, affected_events
    
    def get_vaada_by_date(self, vaada_date: date) -> List[Dict]:
        """Get committees scheduled for a specific date using SQLAlchemy"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
            
        with get_db_session() as session:
            repo = VaadaRepository(session)
            vaadot = repo.get_by_date(vaada_date)
            
            result = []
            for v in vaadot:
                d = v.to_dict()
                d['committee_name'] = v.committee_type.name
                d['scheduled_day'] = v.committee_type.scheduled_day
                d['frequency'] = v.committee_type.frequency
                d['week_of_month'] = v.committee_type.week_of_month
                d['hativa_name'] = v.hativa.name
                if v.exception_date:
                    d['exception_date'] = v.exception_date.exception_date
                    d['exception_description'] = v.exception_date.description
                    d['exception_type'] = v.exception_date.type
                result.append(d)
            return result
    
    def get_vaadot_by_date_and_hativa(self, vaada_date: str, hativa_id: int) -> List[Dict]:
        """Get committees scheduled for a specific date and hativa using SQLAlchemy"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
            
        with get_db_session() as session:
            repo = VaadaRepository(session)
            vaadot = repo.get_by_date_and_hativa(vaada_date, hativa_id)
            return [v.to_dict() for v in vaadot]
    
    def get_vaadot_affected_by_exception(self, exception_date_id: int) -> List[Dict]:
        """Get committees affected by a specific exception date using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            vaadot = repo.get_by_exception_date(exception_date_id)
            
            result = []
            for v in vaadot:
                d = v.to_dict()
                d['committee_name'] = v.committee_type.name
                d['scheduled_day'] = v.committee_type.scheduled_day
                d['frequency'] = v.committee_type.frequency
                d['week_of_month'] = v.committee_type.week_of_month
                d['hativa_name'] = v.hativa.name
                if v.exception_date:
                    d['exception_date'] = v.exception_date.exception_date
                    d['exception_description'] = v.exception_date.description
                    d['exception_type'] = v.exception_date.type
                result.append(d)
            return result
    
    # Events operations
    def add_event(self, vaadot_id: int, maslul_id: int, name: str, event_type: str,
                  expected_requests: int = 0, actual_submissions: int = 0, call_publication_date: Optional[date] = None,
                  is_call_deadline_manual: bool = False, manual_call_deadline_date: Optional[date] = None,
                  user_role: Optional[str] = None) -> int:
        """Add a new event using SQLAlchemy with constraint checks and deadline calculation"""
        
        # Date parsing logic from original method
        def parse_date(d):
            if d in ("", None): return None
            if isinstance(d, str): return datetime.strptime(d, '%Y-%m-%d').date()
            if isinstance(d, datetime): return d.date()
            return d

        call_publication_date = parse_date(call_publication_date)
        manual_call_deadline_date = parse_date(manual_call_deadline_date)
        
        with get_db_session() as session:
            event_repo = EventRepository(session)
            vaada_repo = VaadaRepository(session)
            maslul_repo = MaslulRepository(session)
            settings_repo = SettingsRepository(session)
            exception_repo = ExceptionDateRepository(session)
            
            # 1. Fetch Vaada and Maslul and validate
            vaada = vaada_repo.get_by_id(vaadot_id)
            maslul = maslul_repo.get_by_id(maslul_id)
            
            if not vaada or not maslul:
                raise ValueError("ועדה או מסלול לא נמצאו במערכת")
                
            if vaada.hativa_id != maslul.hativa_id:
                raise ValueError(f'המסלול "{maslul.name}" מחטיבת "{maslul.hativa.name}" אינו יכול להיות משויך לועדה "{vaada.committee_type.name}" מחטיבת "{vaada.hativa.name}"')
            
            # 2. Max requests constraint check
            if user_role != 'admin':
                max_requests = settings_repo.get_int_setting('max_requests_committee_date', 100)
                current_total = event_repo.get_total_requests_on_date(vaada.vaada_date)
                if current_total + expected_requests > max_requests:
                    raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום ועדה: התאריך {vaada.vaada_date} כבר מכיל {current_total} בקשות צפויות. הוספת {expected_requests} בקשות תגרום לסך של {current_total + expected_requests} (המגבלה היא {max_requests})')
            
            # 3. Calculate deadlines
            work_days = settings_repo.get_work_days()
            stage_dates = event_repo.calculate_stage_dates(
                vaada.vaada_date,
                maslul.stage_a_days, maslul.stage_b_days, maslul.stage_c_days, maslul.stage_d_days,
                lambda d: exception_repo.is_work_day(d, work_days)
            )
            
            # 4. Handle manual deadline
            final_call_deadline = manual_call_deadline_date if (is_call_deadline_manual and manual_call_deadline_date) else stage_dates['call_deadline_date']
            
            # 5. Check derived constraints (placeholder logic from original)
            derived_error = event_repo.check_derived_dates_constraints(stage_dates, expected_requests, user_role=user_role)
            if derived_error:
                raise ValueError(derived_error)
            
            # 6. Create event
            event = Event(
                vaadot_id=vaadot_id,
                maslul_id=maslul_id,
                name=name,
                event_type=event_type,
                expected_requests=expected_requests,
                actual_submissions=actual_submissions,
                call_publication_date=call_publication_date,
                call_deadline_date=final_call_deadline,
                intake_deadline_date=stage_dates['intake_deadline_date'],
                review_deadline_date=stage_dates['review_deadline_date'],
                response_deadline_date=stage_dates['response_deadline_date'],
                is_call_deadline_manual=1 if (is_call_deadline_manual and manual_call_deadline_date) else 0
            )
            event_repo.add(event)
            return event.event_id
    
    def get_events(self, vaadot_id: Optional[int] = None, include_deleted: bool = False) -> List[Dict]:
        """Get events using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            events = repo.get_all(vaadot_id=vaadot_id, include_deleted=include_deleted)
            return [e.to_dict() for e in events]
    
    def update_event(self, event_id: int, vaadot_id: int, maslul_id: int, name: str, event_type: str,
                     expected_requests: int = 0, actual_submissions: int = 0, call_publication_date: Optional[date] = None,
                     is_call_deadline_manual: bool = False, manual_call_deadline_date: Optional[date] = None,
                     user_role: Optional[str] = None) -> bool:
        """Update an existing event using SQLAlchemy with constraint checks and deadline calculation"""
        
        # Date parsing logic
        def parse_date(d):
            if d in ("", None): return None
            if isinstance(d, str): return datetime.strptime(d, '%Y-%m-%d').date()
            if isinstance(d, datetime): return d.date()
            return d

        call_publication_date = parse_date(call_publication_date)
        manual_call_deadline_date = parse_date(manual_call_deadline_date)
        
        with get_db_session() as session:
            event_repo = EventRepository(session)
            vaada_repo = VaadaRepository(session)
            maslul_repo = MaslulRepository(session)
            settings_repo = SettingsRepository(session)
            exception_repo = ExceptionDateRepository(session)
            
            # 1. Fetch Event and validate
            event = event_repo.get_by_id(event_id)
            if not event:
                raise ValueError("האירוע לא נמצא במערכת")

            # 2. Postponement Validation
            if is_call_deadline_manual and manual_call_deadline_date and event.call_deadline_date:
                if manual_call_deadline_date < event.call_deadline_date:
                    raise ValueError(f'אסור להקדים את תאריך סיום הקול קורא. התאריך הנוכחי הוא {event.call_deadline_date}, ניתן רק לדחות את התאריך (לא להקדים אותו)')

            # 3. Fetch Vaada and Maslul and validate division match
            vaada = vaada_repo.get_by_id(vaadot_id)
            maslul = maslul_repo.get_by_id(maslul_id)
            
            if not vaada or not maslul:
                raise ValueError("ועדה או מסלול לא נמצאו במערכת")
                
            if vaada.hativa_id != maslul.hativa_id:
                raise ValueError(f'המסלול "{maslul.name}" מחטיבת "{maslul.hativa.name}" אינו יכול להיות משויך לועדה "{vaada.committee_type.name}" מחטיבת "{vaada.hativa.name}"')
            
            # 4. Max requests constraint check (excluding current event)
            if user_role != 'admin':
                max_requests = settings_repo.get_int_setting('max_requests_committee_date', 100)
                current_total = event_repo.get_total_requests_on_date(vaada.vaada_date, exclude_event_id=event_id)
                if current_total + expected_requests > max_requests:
                    raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום ועדה: התאריך {vaada.vaada_date} כבר מכיל {current_total} בקשות צפויות (ללא האירוע הנוכחי). עדכון ל-{expected_requests} בקשות יגרום לסך של {current_total + expected_requests} (המגבלה היא {max_requests})')
            
            # 5. Calculate deadlines
            work_days = settings_repo.get_work_days()
            stage_dates = event_repo.calculate_stage_dates(
                vaada.vaada_date,
                maslul.stage_a_days, maslul.stage_b_days, maslul.stage_c_days, maslul.stage_d_days,
                lambda d: exception_repo.is_work_day(d, work_days)
            )
            
            # 6. Handle manual deadline
            final_call_deadline = manual_call_deadline_date if (is_call_deadline_manual and manual_call_deadline_date) else stage_dates['call_deadline_date']
            
            # 7. Check derived constraints (placeholder logic from original)
            derived_error = event_repo.check_derived_dates_constraints(stage_dates, expected_requests, exclude_event_id=event_id, user_role=user_role)
            if derived_error:
                raise ValueError(derived_error)
            
            # 8. Apply Updates
            event.vaadot_id = vaadot_id
            event.maslul_id = maslul_id
            event.name = name
            event.event_type = event_type
            event.expected_requests = expected_requests
            event.actual_submissions = actual_submissions
            event.call_publication_date = call_publication_date
            event.call_deadline_date = final_call_deadline
            event.intake_deadline_date = stage_dates['intake_deadline_date']
            event.review_deadline_date = stage_dates['review_deadline_date']
            event.response_deadline_date = stage_dates['response_deadline_date']
            event.is_call_deadline_manual = 1 if (is_call_deadline_manual and manual_call_deadline_date) else 0
            
            session.flush()
            return True
    
    def delete_event(self, event_id: int, user_id: Optional[int] = None) -> bool:
        """Soft delete an event using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            return repo.soft_delete(event_id, user_id)

    def delete_events_bulk(self, event_ids: List[int], user_id: Optional[int] = None) -> int:
        """Bulk soft delete events using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            return repo.bulk_soft_delete(event_ids, user_id)
    
    # User Management and Permissions
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_username(username)
            if user and user.is_active:
                return user.to_dict()
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_email(email)
            if user and user.is_active:
                return user.to_dict()
            return None
    
    def update_last_login(self, user_id: int):
        """Update user's last login using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            repo.update_last_login(user_id)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            users = repo.get_all()
            result = []
            for user in users:
                d = user.to_dict()
                d['hativa_names'] = ', '.join([h.name for h in user.hativot]) if user.hativot else ''
                result.append(d)
            return result
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_id(user_id)
            if user:
                d = user.to_dict()
                d['hativa_names'] = ', '.join([h.name for h in user.hativot]) if user.hativot else ''
                return d
            return None
    
    def update_user(self, user_id: int, username: str, email: str, full_name: str, 
                   role: str, hativa_ids: List[int] = None, auth_source: Optional[str] = None) -> bool:
        """Update user information using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.update_user(user_id, username, email, full_name, role, hativa_ids, auth_source)
    
    def toggle_user_status(self, user_id: int) -> bool:
        """Toggle user active status using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.toggle_status(user_id)
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete) using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.soft_delete(user_id)
    
    def check_username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username already exists using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.username_exists(username, exclude_user_id)
    
    def check_email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email already exists using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.email_exists(email, exclude_user_id)
    
    def get_user_hativot(self, user_id: int) -> List[Dict]:
        """Get all hativot for a user using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            hativot = repo.get_user_hativot(user_id)
            return [{'hativa_id': h.hativa_id, 'name': h.name, 
                    'description': h.description, 'color': h.color} for h in hativot]
    
    def user_has_access_to_hativa(self, user_id: int, hativa_id: int) -> bool:
        """Check if user has access to a hativa using SQLAlchemy"""
        with get_db_session() as session:
            # Check if admin
            repo = UserRepository(session)
            user = repo.get_by_id(user_id)
            if user and user.role == 'admin':
                return True
            return repo.has_access_to_hativa(user_id, hativa_id)
    
    def add_user_hativa(self, user_id: int, hativa_id: int) -> bool:
        """Add hativa access to user using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.add_hativa_access(user_id, hativa_id)
    
    def remove_user_hativa(self, user_id: int, hativa_id: int) -> bool:
        """Remove hativa access from user using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.remove_hativa_access(user_id, hativa_id)
    
    def get_system_setting(self, setting_key: str) -> Optional[str]:
        """Get system setting value using SQLAlchemy"""
        with get_db_session() as session:
            repo = SettingsRepository(session)
            return repo.get_setting(setting_key)
    
    def update_system_setting(self, setting_key: str, setting_value: str, user_id: int):
        """Update system setting using SQLAlchemy"""
        with get_db_session() as session:
            repo = SettingsRepository(session)
            repo.update_setting(setting_key, setting_value, user_id)

    def get_int_setting(self, setting_key: str, default: int) -> int:
        """Get an integer system setting with fallback using SQLAlchemy"""
        with get_db_session() as session:
            repo = SettingsRepository(session)
            return repo.get_int_setting(setting_key, default)

    def get_constraint_settings(self) -> Dict[str, Any]:
        """Return parsed constraint settings for the scheduling system using SQLAlchemy"""
        with get_db_session() as session:
            repo = SettingsRepository(session)
            constraints = repo.get_constraint_settings()
            constraints['work_days'] = repo.get_work_days()
            return constraints
    
    def is_editing_allowed(self, user_role: str) -> bool:
        """Check if editing is allowed for user role"""
        # Admins can always edit
        if user_role == 'admin':
            return True
        
        # Editors can edit when editing period is active
        if user_role == 'editor':
            editing_active = self.get_system_setting('editing_period_active')
            return editing_active == '1'
        
        # Viewers cannot edit
        if user_role == 'viewer':
            return False
        
        # Check if general editing period is active (backward compatibility)
        editing_active = self.get_system_setting('editing_period_active')
        return editing_active == '1'
    
    def can_user_edit(self, user_id: int, user_role: str, target_hativa_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Check if user can edit based on role, editing period, and hativa access
        Returns (can_edit, reason)
        """
        # Admin can always edit everything (but will get warnings about constraints)
        if user_role == 'admin':
            return True, "מנהל מערכת - אין הגבלות (מקבל התראות על אילוצים)"
        
        # Viewers can never edit
        if user_role == 'viewer':
            return False, "צופה - הרשאות קריאה בלבד"
        
        # Editors can edit if editing period is active
        if user_role == 'editor':
            editing_active = self.get_system_setting('editing_period_active')
            if editing_active != '1':
                return False, "תקופת העריכה הסתיימה. רק מנהלי מערכת יכולים לערוך"
            
            # Check if editor has access to target hativa
            if target_hativa_id:
                if not self.user_has_access_to_hativa(user_id, target_hativa_id):
                    return False, "אין לך הרשאה לערוך בחטיבה זו"
            
            return True, "עורך - תקופת עריכה פעילה"
        
        return False, "הרשאות לא מספיקות"
    
    # Soft Delete Functions (Alternative to hard delete)
    def deactivate_hativa(self, hativa_id: int) -> bool:
        """Deactivate division using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.deactivate(hativa_id)
    
    def activate_hativa(self, hativa_id: int) -> bool:
        """Reactivate division using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            return repo.activate(hativa_id)
    
    def can_delete_hativa(self, hativa_id: int) -> Tuple[bool, str, Dict[str, int]]:
        """
        Check if a hativa can be deleted using SQLAlchemy.
        Returns: (can_delete, reason, counts)
        """
        with get_db_session() as session:
            repo = HativaRepository(session)
            can_del, reason, counts = repo.can_delete(hativa_id)
            
            if not can_del:
                # Localize reason message to Hebrew to match original behavior
                blocking_items = []
                if counts.get('events', 0) > 0:
                    blocking_items.append(f"{counts['events']} אירועים")
                if counts.get('vaadot', 0) > 0:
                    blocking_items.append(f"{counts['vaadot']} ועדות")
                if counts.get('maslulim', 0) > 0:
                    blocking_items.append(f"{counts['maslulim']} מסלולים")
                if counts.get('committee_types', 0) > 0:
                    blocking_items.append(f"{counts['committee_types']} סוגי ועדות")
                if counts.get('users', 0) > 0:
                    blocking_items.append(f"{counts['users']} משתמשים משויכים")
                
                reason = f"לא ניתן למחוק את החטיבה. קיימים: {', '.join(blocking_items)}"
                return False, reason, counts
            
            return True, "ניתן למחוק את החטיבה", counts
    
    def delete_hativa(self, hativa_id: int) -> Tuple[bool, str]:
        """Permanently delete a hativa using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            success, reason = repo.hard_delete(hativa_id)
            if success:
                # Build success message in Hebrew
                return True, reason.replace("Division deleted successfully", f"החטיבה נמחקה בהצלחה")
            else:
                return False, f"שגיאה במחיקת החטיבה: {reason}"
    
    def deactivate_maslul(self, maslul_id: int) -> bool:
        """Deactivate route using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            return repo.deactivate(maslul_id)
    
    def activate_maslul(self, maslul_id: int) -> bool:
        """Reactivate route using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            return repo.activate(maslul_id)
    
    def deactivate_committee_type(self, committee_type_id: int) -> bool:
        """Deactivate committee type using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            return repo.deactivate(committee_type_id)
    
    def activate_committee_type(self, committee_type_id: int) -> bool:
        """Reactivate committee type using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            return repo.activate(committee_type_id)
    
    # Updated get functions to filter by active status
    def get_hativot_active_only(self) -> List[Dict]:
        """Get only active divisions using SQLAlchemy"""
        with get_db_session() as session:
            repo = HativaRepository(session)
            hativot = repo.get_active_only()
            return [{'hativa_id': h.hativa_id, 'name': h.name, 'description': h.description,
                    'color': h.color, 'is_active': h.is_active, 'created_at': h.created_at} for h in hativot]
    
    def get_maslulim_active_only(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get only active routes using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            maslulim = repo.get_active_only(hativa_id=hativa_id)
            return [m.to_dict() for m in maslulim]
    
    def get_committee_types_active_only(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get only active committee types using SQLAlchemy"""
        with get_db_session() as session:
            repo = CommitteeTypeRepository(session)
            cts = repo.get_active_only(hativa_id=hativa_id)
            return [ct.to_dict() for ct in cts]
    
    # Enhanced Business Days and SLA Calculations
    def get_work_days(self) -> List[int]:
        """Get configured work days"""
        work_days_str = self.get_system_setting('work_days') or '6,0,1,2,3,4'
        return [int(day) for day in work_days_str.split(',')]

    def get_meetings_count_on_date(self, vaada_date: Any) -> int:
        """Get the number of meetings scheduled for a specific date using SQLAlchemy"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        with get_db_session() as session:
            repo = VaadaRepository(session)
            return repo.count_meetings_on_date(vaada_date, is_operational=False)

    def get_meetings_count_in_range(self, start_date: date, end_date: date) -> int:
        """Get number of meetings in an inclusive date range using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            return repo.count_in_range(start_date, end_date, is_operational=False)
    
    def is_work_day(self, check_date: date) -> bool:
        """Check if date is a work day (not weekend, not holiday, configured work days)"""
        # Check if it's a configured work day
        work_days = self.get_work_days()
        if check_date.weekday() not in work_days:
            return False
        
        # Check if it's an exception date (holiday, special sabbath, etc.)
        return not self.is_exception_date(check_date)
    
    def get_business_days_in_range(self, start_date: date, end_date: date) -> List[date]:
        """Get all business days in a date range"""
        business_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_work_day(current_date):
                business_days.append(current_date)
            current_date += timedelta(days=1)
        
        return business_days
    
    def add_business_days(self, start_date: date, days_to_add: int) -> date:
        """Add business days to a date (skipping weekends and holidays)"""
        current_date = start_date
        days_added = 0
        
        while days_added < days_to_add:
            current_date += timedelta(days=1)
            if self.is_work_day(current_date):
                days_added += 1
        
        return current_date
    
    def subtract_business_days(self, start_date: date, days_to_subtract: int) -> date:
        """Subtract business days from a date (skipping weekends and holidays)"""
        current_date = start_date
        days_subtracted = 0
        
        while days_subtracted < days_to_subtract:
            current_date -= timedelta(days=1)
            if self.is_work_day(current_date):
                days_subtracted += 1
        
        return current_date
    
    def get_total_requests_on_date(self, check_date, exclude_event_id: Optional[int] = None) -> int:
        """Get total expected requests across all events on a specific date using SQLAlchemy"""
        if isinstance(check_date, str):
            check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        with get_db_session() as session:
            repo = EventRepository(session)
            return repo.get_total_requests_on_date(check_date, exclude_event_id=exclude_event_id)
    
    def get_total_requests_on_derived_date(self, check_date, date_type: str, exclude_event_id: Optional[int] = None) -> int:
        """Get total expected requests for a specific derived date using SQLAlchemy"""
        if isinstance(check_date, str):
            check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        with get_db_session() as session:
            repo = EventRepository(session)
            return repo.get_total_requests_on_derived_date(check_date, date_type, exclude_event_id=exclude_event_id)
    
    def check_derived_dates_constraints(self, stage_dates: Dict, expected_requests: int, 
                                       exclude_event_id: Optional[int] = None, user_role: Optional[str] = None) -> Optional[str]:
        """
        Check if adding/updating an event would violate max_requests constraints on derived dates.
        Currently no constraints are enforced on derived dates.
        
        Args:
            stage_dates: Dictionary with call_deadline_date, intake_deadline_date, review_deadline_date, response_deadline_date
            expected_requests: Number of expected requests for the event
            exclude_event_id: Optional event ID to exclude (for updates)
            user_role: Optional user role (kept for backward compatibility)
            
        Returns:
            None (no constraints enforced)
        """
        # No constraints on derived dates
        return None
    
    def calculate_stage_dates(self, committee_date, stage_a_days: int, stage_b_days: int, stage_c_days: int, stage_d_days: int) -> Dict:
        """Calculate stage deadline dates based on committee meeting date and stage durations"""
        
        # המר את תאריך הועדה לאובייקט date אם הוא מחרוזת
        if isinstance(committee_date, str):
            from datetime import datetime
            committee_date = datetime.strptime(committee_date, '%Y-%m-%d').date()
        
        # חישוב התאריכים אחורה מתאריך הועדה
        
        # תאריך הגשת תשובת ועדה = תאריך ועדה + שלב ד
        response_deadline = self.add_business_days(committee_date, stage_d_days)
        
        # תאריך סיום שלב בדיקה = תאריך ועדה - שלב ג
        review_deadline = self.subtract_business_days(committee_date, stage_c_days)
        
        # תאריך סיום שלב קליטה = תאריך סיום בדיקה - שלב ב  
        intake_deadline = self.subtract_business_days(review_deadline, stage_b_days)
        
        # תאריך סיום קול קורא = תאריך סיום קליטה - שלב א
        call_deadline = self.subtract_business_days(intake_deadline, stage_a_days)
        
        return {
            'call_deadline_date': call_deadline,      # תאריך סיום קול קורא
            'intake_deadline_date': intake_deadline,  # תאריך סיום קליטה
            'review_deadline_date': review_deadline,  # תאריך סיום בדיקה
            'response_deadline_date': response_deadline,  # תאריך הגשת תשובת ועדה
            'committee_date': committee_date          # תאריך הועדה
        }
    
    def calculate_sla_dates(self, committee_date: date, sla_days: Optional[int] = None) -> Dict:
        """Calculate SLA dates based on committee meeting date"""
        if sla_days is None:
            sla_days = int(self.get_system_setting('sla_days_before') or '14')
        
        # Calculate key SLA milestones
        sla_dates = {
            'committee_date': committee_date,
            'sla_days': sla_days,
            'request_deadline': self.subtract_business_days(committee_date, sla_days),
            'preparation_start': self.subtract_business_days(committee_date, sla_days + 7),
            'notification_date': self.subtract_business_days(committee_date, sla_days + 14)
        }
        
        # Add business days count
        sla_dates['business_days_to_committee'] = len(
            self.get_business_days_in_range(date.today(), committee_date)
        )
        
        return sla_dates
    
    def get_all_events(self, include_deleted: bool = False) -> List[Dict]:
        """Get all events using SQLAlchemy with extended information"""
        with get_db_session() as session:
            repo = EventRepository(session)
            events = repo.get_all(include_deleted=include_deleted)
            
            result = []
            for e in events:
                d = e.to_dict()
                # Manual corrections for backward compatibility with specific keys
                d['maslul_hativa_id'] = e.maslul.hativa_id if e.maslul else None
                d['sla_days'] = e.maslul.sla_days if e.maslul else 45
                d['committee_type_id'] = e.vaada.committee_type_id if e.vaada else None
                result.append(d)
            
            # Sort as in original SQL: ORDER BY v.vaada_date DESC, e.created_at DESC
            result.sort(key=lambda x: (str(x.get('vaada_date') or ''), str(x.get('created_at') or '')), reverse=True)
            return result

    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """Get event by ID using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            event = repo.get_by_id(event_id)
            if event:
                d = event.to_dict()
                # Maintain backward compatibility with specific keys
                d['hativa_id'] = event.maslul.hativa_id if event.maslul else None
                return d
            return None
    
    def get_vaada_by_id(self, vaada_id: int) -> Optional[Dict]:
        """Get committee meeting by ID using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            vaada = repo.get_by_id(vaada_id)
            if vaada:
                d = vaada.to_dict()
                d['committee_name'] = vaada.committee_type.name
                d['hativa_name'] = vaada.hativa.name
                return d
            return None
    
    def get_maslul_by_id(self, maslul_id: int) -> Optional[Dict]:
        """Get route by ID using SQLAlchemy"""
        with get_db_session() as session:
            repo = MaslulRepository(session)
            maslul = repo.get_by_id(maslul_id)
            if maslul:
                d = maslul.to_dict()
                # Maintain backward compatibility with default values if None
                if d.get('sla_days') is None: d['sla_days'] = 45
                if d.get('stage_a_days') is None: d['stage_a_days'] = 10
                if d.get('stage_b_days') is None: d['stage_b_days'] = 15
                if d.get('stage_c_days') is None: d['stage_c_days'] = 10
                if d.get('stage_d_days') is None: d['stage_d_days'] = 10
                return d
            return None
    
    # Audit Log Methods
    def add_audit_log(self, user_id: Optional[int], username: str, action: str, 
                     entity_type: str, entity_id: Optional[int] = None, 
                     entity_name: Optional[str] = None, details: Optional[str] = None,
                     ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                     status: str = 'success', error_message: Optional[str] = None) -> int:
        """Add an audit log entry using SQLAlchemy"""
        with get_db_session() as session:
            repo = AuditLogRepository(session)
            return repo.log(
                user_id=user_id, username=username, action=action, 
                entity_type=entity_type, entity_id=entity_id, 
                entity_name=entity_name, details=details,
                ip_address=ip_address, user_agent=user_agent,
                status=status, error_message=error_message
            )
    
    def get_audit_logs(self, limit: int = 100, offset: int = 0,
                       user_id: Optional[int] = None,
                       entity_type: Optional[str] = None,
                       action: Optional[str] = None,
                       search_text: Optional[str] = None,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> List[Dict]:
        """Get audit logs using SQLAlchemy"""
        with get_db_session() as session:
            repo = AuditLogRepository(session)
            logs = repo.get_logs(
                limit=limit, offset=offset, user_id=user_id,
                entity_type=entity_type, action=action,
                search_text=search_text, start_date=start_date, end_date=end_date
            )
            return [log.to_dict() for log in logs]
    
    def get_audit_logs_count(self, user_id: Optional[int] = None,
                             entity_type: Optional[str] = None,
                             action: Optional[str] = None,
                             search_text: Optional[str] = None,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> int:
        """Get total count of audit logs using SQLAlchemy"""
        with get_db_session() as session:
            repo = AuditLogRepository(session)
            return repo.get_logs_count(
                user_id=user_id, entity_type=entity_type, action=action,
                search_text=search_text, start_date=start_date, end_date=end_date
            )
    
    def get_audit_statistics(self) -> Dict:
        """Get audit statistics using SQLAlchemy"""
        with get_db_session() as session:
            repo = AuditLogRepository(session)
            return repo.get_statistics()
    
    def update_event_vaada(self, event_id: int, new_vaada_id: int, user_role: Optional[str] = None) -> bool:
        """Update event's committee meeting using SQLAlchemy with constraint validation"""
        with get_db_session() as session:
            event_repo = EventRepository(session)
            vaada_repo = VaadaRepository(session)
            settings_repo = SettingsRepository(session)
            exception_repo = ExceptionDateRepository(session)
            
            # 1. Fetch Event and Target Vaada
            event = event_repo.get_by_id(event_id)
            target_vaada = vaada_repo.get_by_id(new_vaada_id)
            
            if not event or not target_vaada:
                raise ValueError("האירוע או הועדה לא נמצאו במערכת")
                
            # 2. Check max requests constraint for target committee date (excluding this event, skip for admins)
            if user_role != 'admin':
                max_req = settings_repo.get_int_setting('max_requests_committee_date', 100)
                current_total = event_repo.get_total_requests_on_date(target_vaada.vaada_date, exclude_event_id=event_id)
                if current_total + event.expected_requests > max_req:
                    raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום ועדה: התאריך {target_vaada.vaada_date} כבר מכיל {current_total} בקשות צפויות. העברת אירוע זה עם {event.expected_requests} בקשות תגרום לסך של {current_total + event.expected_requests} (המגבלה היא {max_req})')
            
            # 3. Calculate derived dates for the target committee
            work_days = settings_repo.get_work_days()
            maslul = event.maslul
            stage_dates = event_repo.calculate_stage_dates(
                target_vaada.vaada_date,
                maslul.stage_a_days, maslul.stage_b_days, maslul.stage_c_days, maslul.stage_d_days,
                lambda d: exception_repo.is_work_day(d, work_days)
            )
            
            # 4. Check derived constraints
            derived_error = event_repo.check_derived_dates_constraints(stage_dates, event.expected_requests, exclude_event_id=event_id, user_role=user_role)
            if derived_error:
                raise ValueError(derived_error)
            
            # 5. Apply Update
            event.vaadot_id = new_vaada_id
            event.call_deadline_date = stage_dates['call_deadline_date']
            event.intake_deadline_date = stage_dates['intake_deadline_date']
            event.review_deadline_date = stage_dates['review_deadline_date']
            event.response_deadline_date = stage_dates['response_deadline_date']
            
            session.flush()
            return True
    
    # Active Directory User Management Methods
    def create_ad_user(self, username: str, email: str, full_name: str, 
                      role: str = 'viewer', hativa_id: Optional[int] = None,
                      ad_dn: str = '', profile_picture: bytes = None) -> int:
        """Create a new AD user using SQLAlchemy"""
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with get_db_session() as session:
                    repo = UserRepository(session)
                    # Azure AD users don't use password authentication, but DB requires a value
                    user = repo.create(
                        username=username,
                        email=email,
                        full_name=full_name,
                        role=role,
                        auth_source='ad',
                        ad_dn=ad_dn,
                        profile_picture=profile_picture,
                        hativa_ids=[hativa_id] if hativa_id else None
                    )
                    return user.user_id
            except Exception as e:
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                raise
    
    def update_ad_user_info(self, user_id: int, email: str, full_name: str, profile_picture: bytes = None) -> bool:
        """Update AD user information using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.update_ad_user_info(user_id, email, full_name, profile_picture)
    
    def get_user_photo(self, user_id: int) -> Optional[bytes]:
        """Get user profile picture using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            return repo.get_user_photo(user_id)

    def get_user_by_username_any_source(self, username: str) -> Optional[Dict]:
        """Get user by username using SQLAlchemy, including division context"""
        with get_db_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_username(username)
            if user:
                d = user.to_dict()
                # Join with user_hativot implicitly through relationship
                if user.hativot:
                    # Match original SQL: ORDER BY h.hativa_id ASC LIMIT 1
                    sorted_hativot = sorted(list(user.hativot), key=lambda h: h.hativa_id)
                    first_h = sorted_hativot[0]
                    d['hativa_id'] = first_h.hativa_id
                    d['hativa_name'] = first_h.name
                else:
                    d['hativa_id'] = None
                    d['hativa_name'] = None
                return d
            return None
    
    def get_ad_users(self) -> List[Dict]:
        """Get all Active Directory users using SQLAlchemy"""
        with get_db_session() as session:
            repo = UserRepository(session)
            users = repo.get_ad_users()
            return [u.to_dict() for u in users]
    
    
    # Recycle Bin Functions
    def get_deleted_vaadot(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get all deleted committee meetings using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            vaadot = repo.get_deleted(hativa_id=hativa_id)
            return [v.to_dict() for v in vaadot]
    
    def get_deleted_events(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get all deleted events using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            events = repo.get_deleted(hativa_id=hativa_id)
            return [e.to_dict() for e in events]
    
    def restore_vaada(self, vaadot_id: int) -> bool:
        """Restore a deleted committee meeting using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            return repo.restore(vaadot_id)
    
    def restore_event(self, event_id: int) -> bool:
        """Restore a deleted event using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            return repo.restore(event_id)
    
    def permanently_delete_vaada(self, vaadot_id: int) -> bool:
        """Permanently delete a committee meeting (hard delete) using SQLAlchemy"""
        with get_db_session() as session:
            repo = VaadaRepository(session)
            return repo.hard_delete(vaadot_id)
    
    def permanently_delete_event(self, event_id: int) -> bool:
        """Permanently delete an event (hard delete) using SQLAlchemy"""
        with get_db_session() as session:
            repo = EventRepository(session)
            return repo.hard_delete(event_id)
    
    def empty_recycle_bin(self, hativa_id: Optional[int] = None) -> Tuple[int, int]:
        """Permanently delete all items in recycle bin using SQLAlchemy"""
        with get_db_session() as session:
            vaada_repo = VaadaRepository(session)
            event_repo = EventRepository(session)
            vaadot_deleted = vaada_repo.empty_recycle_bin(hativa_id)
            events_deleted = event_repo.empty_recycle_bin(hativa_id)
            return vaadot_deleted, events_deleted

    # Calendar Sync Operations
    def create_calendar_sync_record(self, source_type: str, source_id: int, deadline_type: str = None,
                                     calendar_email: str = 'plan@innovationisrael.org.il',
                                     calendar_event_id: str = None) -> int:
        """Create calendar sync record using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            record = repo.create_record(source_type, source_id, deadline_type, calendar_email, calendar_event_id)
            return record.sync_id

    def update_calendar_sync_status(self, sync_id: int, status: str, calendar_event_id: str = None,
                                      error_message: str = None, content_hash: str = None) -> bool:
        """Update calendar sync status using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            return repo.update_status(sync_id, status, calendar_event_id, error_message, content_hash)

    def get_calendar_sync_record(self, source_type: str, source_id: int, deadline_type: str = None,
                                   calendar_email: str = 'plan@innovationisrael.org.il') -> Optional[Dict]:
        """Get calendar sync record using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            record = repo.get_record(source_type, source_id, deadline_type, calendar_email)
            return record.to_dict() if record else None

    def get_pending_calendar_syncs(self, calendar_email: str = 'plan@innovationisrael.org.il') -> List[Dict]:
        """Get pending calendar syncs using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            records = repo.get_pending(calendar_email)
            return [r.to_dict() for r in records]

    def delete_calendar_sync_record(self, source_type: str, source_id: int, deadline_type: str = None,
                                      calendar_email: str = 'plan@innovationisrael.org.il') -> bool:
        """Delete calendar sync record using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            return repo.delete_record(source_type, source_id, deadline_type, calendar_email)

    def mark_calendar_sync_deleted(self, source_type: str, source_id: int,
                                     calendar_email: str = 'plan@innovationisrael.org.il') -> List[Dict]:
        """Mark calendar sync records as deleted using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            records = repo.mark_deleted(source_type, source_id, calendar_email)
            return [r.to_dict() for r in records]

    def get_all_synced_calendar_events(self, calendar_email: str = 'plan@innovationisrael.org.il') -> List[Dict]:
        """Get all synced calendar events using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            records = repo.get_all_synced(calendar_email)
            return [r.to_dict() for r in records]

    def clear_all_calendar_sync_records(self, calendar_email: str = 'plan@innovationisrael.org.il') -> int:
        """Clear all calendar sync records using SQLAlchemy"""
        with get_db_session() as session:
            repo = CalendarSyncRepository(session)
            return repo.clear_all(calendar_email)

    # Schedule Drafts operations
    def save_schedule_draft(self, user_id: int, data: str) -> int:
        """Save a schedule draft using SQLAlchemy"""
        with get_db_session() as session:
            repo = ScheduleDraftRepository(session)
            return repo.save_draft(user_id, data)

    def get_schedule_draft(self, draft_id: int) -> Optional[Dict]:
        """Get a schedule draft using SQLAlchemy"""
        with get_db_session() as session:
            repo = ScheduleDraftRepository(session)
            draft = repo.get_draft(draft_id)
            return draft.to_dict() if draft else None

    def delete_schedule_draft(self, draft_id: int) -> bool:
        """Delete a schedule draft using SQLAlchemy"""
        with get_db_session() as session:
            repo = ScheduleDraftRepository(session)
            return repo.delete_by_id(draft_id)

    def cleanup_old_drafts(self, hours: int = 24) -> int:
        """Cleanup old schedule drafts using SQLAlchemy"""
        with get_db_session() as session:
            repo = ScheduleDraftRepository(session)
            return repo.cleanup_old_drafts(hours)
    

