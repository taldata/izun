"""
שירות לניהול תזמון אוטומטי של ועדות
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

from database import DatabaseManager
from auto_scheduler import AutoMeetingScheduler

# הגדרת לוגר
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """שגיאת אימות נתונים"""
    pass

class ScheduleGenerationError(Exception):
    """שגיאה ביצירת לוח זמנים"""
    pass

@dataclass
class ScheduleRequest:
    """בקשה ליצירת לוח זמנים"""
    year: int
    month: int
    hativa_id: Optional[int] = None
    auto_approve: bool = False

@dataclass
class ScheduleResult:
    """תוצאת יצירת לוח זמנים"""
    year: int
    month: int
    suggested_meetings: List[Dict]
    total_suggestions: int
    success: bool
    message: str

@dataclass
class ApprovalRequest:
    """בקשה לאישור ישיבות"""
    suggestions: List[Dict]
    auto_approve: bool = False

@dataclass
class ApprovalResult:
    """תוצאת אישור ישיבות"""
    created_meetings: List[Dict]
    failed_meetings: List[Dict]
    success_count: int
    failure_count: int
    success: bool
    message: str

class AutoScheduleService:
    """שירות לניהול תזמון אוטומטי של ועדות"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.scheduler = AutoMeetingScheduler(db)
        logger.info("AutoScheduleService initialized")
    
    def validate_schedule_request(self, request: ScheduleRequest) -> None:
        """אימות בקשה ליצירת לוח זמנים"""
        logger.debug(f"Validating schedule request: year={request.year}, month={request.month}, hativa_id={request.hativa_id}")
        
        # אימות שנה וחודש
        current_year = datetime.now().year
        if request.year < current_year or request.year > current_year + 2:
            raise ValidationError(f"שנה לא תקינה: {request.year}. יש לבחור שנה בין {current_year} ל-{current_year + 2}")
        
        if request.month < 1 or request.month > 12:
            raise ValidationError(f"חודש לא תקין: {request.month}. יש לבחור חודש בין 1 ל-12")
        
        # אימות חטיבה אם צוינה
        if request.hativa_id is not None:
            hativot = self.db.get_hativot()
            if not any(h['hativa_id'] == request.hativa_id for h in hativot):
                raise ValidationError(f"חטיבה לא קיימת: {request.hativa_id}")
        
        logger.debug("Schedule request validation passed")
    
    def generate_schedule(self, request: ScheduleRequest) -> ScheduleResult:
        """יצירת לוח זמנים אוטומטי"""
        try:
            logger.info(f"Generating schedule for {request.year}/{request.month}, hativa_id={request.hativa_id}")
            
            # אימות הבקשה
            self.validate_schedule_request(request)
            
            # קביעת רשימת החטיבות
            if request.hativa_id:
                hativot_ids = [request.hativa_id]
            else:
                hativot = self.db.get_hativot()
                hativot_ids = [h['hativa_id'] for h in hativot]
            
            # יצירת לוח הזמנים
            schedule_data = self.scheduler.generate_monthly_schedule(
                request.year, 
                request.month, 
                hativot_ids
            )
            
            logger.info(f"Generated {schedule_data['total_suggestions']} meeting suggestions")
            
            return ScheduleResult(
                year=schedule_data['year'],
                month=schedule_data['month'],
                suggested_meetings=schedule_data['suggested_meetings'],
                total_suggestions=schedule_data['total_suggestions'],
                success=True,
                message=f"נוצרו {schedule_data['total_suggestions']} הצעות לישיבות"
            )
            
        except ValidationError as e:
            logger.warning(f"Validation error in generate_schedule: {e}")
            return ScheduleResult(
                year=request.year,
                month=request.month,
                suggested_meetings=[],
                total_suggestions=0,
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.error(f"Error generating schedule: {e}")
            raise ScheduleGenerationError(f"שגיאה ביצירת לוח הזמנים: {str(e)}")
    
    def validate_approval_request(self, request: ApprovalRequest) -> None:
        """אימות בקשה לאישור ישיבות"""
        logger.debug(f"Validating approval request with {len(request.suggestions)} suggestions")
        
        if not request.suggestions:
            raise ValidationError("לא נבחרו ישיבות לאישור")
        
        # אימות כל הצעה
        for i, suggestion in enumerate(request.suggestions):
            required_fields = ['committee_type_id', 'hativa_id', 'suggested_date']
            for field in required_fields:
                if field not in suggestion:
                    raise ValidationError(f"הצעה {i+1}: חסר שדה {field}")
            
            # Validate and normalize date format
            try:
                suggested_date = suggestion['suggested_date']
                if isinstance(suggested_date, str):
                    # Try different date formats
                    if 'GMT' in suggested_date:
                        # Handle GMT format: 'Mon, 03 Nov 2025 00:00:00 GMT'
                        from datetime import datetime
                        parsed_date = datetime.strptime(suggested_date, '%a, %d %b %Y %H:%M:%S %Z')
                        suggestion['suggested_date'] = parsed_date.date()
                    else:
                        # Handle YYYY-MM-DD format
                        datetime.strptime(suggested_date, '%Y-%m-%d')
                elif not isinstance(suggestion['suggested_date'], date):
                    raise ValueError("Invalid date format")
            except (ValueError, TypeError) as e:
                logger.error(f"Date validation error for suggestion {i+1}: {e}, date: {suggestion.get('suggested_date')}")
                raise ValidationError(f"הצעה {i+1}: תאריך לא תקין")
        
        logger.debug("Approval request validation passed")
    
    def approve_meetings(self, request: ApprovalRequest) -> ApprovalResult:
        """אישור ויצירת ישיבות"""
        try:
            # אימות הבקשה
            self.validate_approval_request(request)
            
            # יצירת הישיבות
            result = self.scheduler.create_meetings_from_suggestions(
                request.suggestions,
                request.auto_approve
            )
            
            return ApprovalResult(
                created_meetings=result['created_meetings'],
                failed_meetings=result['failed_meetings'],
                success_count=result['success_count'],
                failure_count=result['failure_count'],
                success=result['success_count'] > 0,
                message=f"נוצרו {result['success_count']} ישיבות בהצלחה"
            )
            
        except ValidationError as e:
            logger.warning(f"Validation error in approve_meetings: {e}")
            return ApprovalResult(
                created_meetings=[],
                failed_meetings=[],
                success_count=0,
                failure_count=len(request.suggestions),
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.error(f"Error approving meetings: {e}")
            raise ScheduleGenerationError(f"שגיאה באישור הישיבות: {str(e)}")
    
    def get_schedule_validation(self, year: int, month: int) -> Dict:
        """קבלת אימות לוח זמנים"""
        try:
            logger.debug(f"Validating schedule for {year}/{month}")
            return self.scheduler.validate_schedule_constraints(year, month)
        except Exception as e:
            logger.error(f"Error validating schedule: {e}")
            return {
                'valid': False,
                'violations': [f"שגיאה באימות: {str(e)}"],
                'warnings': [],
                'total_meetings': 0
            }
    
    def get_available_hativot(self) -> List[Dict]:
        """קבלת רשימת החטיבות הזמינות"""
        try:
            return self.db.get_hativot()
        except Exception as e:
            logger.error(f"Error getting hativot: {e}")
            return []
    
    def get_committee_types_for_hativa(self, hativa_id: int) -> List[Dict]:
        """קבלת סוגי ועדות לחטיבה מסוימת"""
        try:
            return self.db.get_committee_types(hativa_id)
        except Exception as e:
            logger.error(f"Error getting committee types for hativa {hativa_id}: {e}")
            return []
