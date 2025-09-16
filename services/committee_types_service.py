"""
Committee Types Service Layer

This module provides business logic for committee types management,
separating concerns from Flask routes and providing better error handling.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import logging
from database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class CommitteeTypeError(Exception):
    """Raised when committee type operations fail"""
    pass


@dataclass
class CommitteeTypeRequest:
    """Data class for committee type creation/update requests"""
    hativa_id: int
    name: str
    scheduled_day: int
    frequency: str
    week_of_month: Optional[int] = None
    description: str = ""


@dataclass
class CommitteeTypeResponse:
    """Data class for committee type operation responses"""
    success: bool
    message: str
    committee_type_id: Optional[int] = None
    data: Optional[Dict] = None


@dataclass
class CommitteeTypesListResponse:
    """Data class for committee types list response"""
    success: bool
    message: str
    committee_types: List[Dict]
    statistics: Dict[str, int]


class CommitteeTypesService:
    """Service class for committee types business logic"""
    
    def __init__(self, database: DatabaseManager):
        self.db = database
        self.day_names = {
            0: 'יום שני',
            1: 'יום שלישי', 
            2: 'יום רביעי',
            3: 'יום חמישי',
            4: 'יום שישי'
        }
    
    def validate_committee_type_data(self, request: CommitteeTypeRequest) -> None:
        """Validate committee type data"""
        logger.info(f"Validating committee type data: {request.name}")
        
        # Validate hativa_id
        if not request.hativa_id:
            raise ValidationError('יש לבחור חטיבה')
        
        # Validate that hativa exists
        hativot = self.db.get_hativot()
        if not any(h['hativa_id'] == request.hativa_id for h in hativot):
            raise ValidationError('החטיבה שנבחרה לא קיימת במערכת')
        
        # Validate name
        if not request.name or not request.name.strip():
            raise ValidationError('שם הועדה הוא שדה חובה')
        
        # Validate scheduled day
        if request.scheduled_day is None or request.scheduled_day < 0 or request.scheduled_day > 4:
            raise ValidationError('יש לבחור יום תקין בשבוע (יום שני עד יום שישי)')
        
        # Validate frequency
        if request.frequency not in ['weekly', 'monthly']:
            raise ValidationError('יש לבחור תדירות תקינה (שבועית או חודשית)')
        
        # Validate week of month for monthly committees
        if request.frequency == 'monthly':
            if not request.week_of_month or request.week_of_month < 1 or request.week_of_month > 4:
                raise ValidationError('עבור ועדות חודשיות יש לבחור שבוע תקין בחודש (1-4)')
        
        logger.info(f"Validation successful for committee type: {request.name}")
    
    def get_committee_types_with_statistics(self, hativa_id: Optional[int] = None) -> CommitteeTypesListResponse:
        """Get committee types with statistics, optionally filtered by division"""
        try:
            logger.info(f"Fetching committee types with statistics for hativa_id: {hativa_id}")
            
            # Get committee types
            committee_types = self.db.get_committee_types(hativa_id)
            
            # Get vaadot for statistics
            vaadot_list = self.db.get_vaadot(hativa_id)
            
            # Calculate statistics
            statistics = {
                'total_count': len(committee_types),
                'weekly_count': len([ct for ct in committee_types if ct['frequency'] == 'weekly']),
                'monthly_count': len([ct for ct in committee_types if ct['frequency'] == 'monthly']),
                'active_meetings_count': len([v for v in vaadot_list if v['status'] in ['planned', 'scheduled']])
            }
            
            logger.info(f"Retrieved {len(committee_types)} committee types with statistics: {statistics}")
            
            return CommitteeTypesListResponse(
                success=True,
                message="נתוני סוגי הועדות נטענו בהצלחה",
                committee_types=committee_types,
                statistics=statistics
            )
            
        except Exception as e:
            logger.error(f"Error fetching committee types: {str(e)}")
            return CommitteeTypesListResponse(
                success=False,
                message=f"שגיאה בטעינת נתוני סוגי הועדות: {str(e)}",
                committee_types=[],
                statistics={'total_count': 0, 'weekly_count': 0, 'monthly_count': 0, 'active_meetings_count': 0}
            )
    
    def create_committee_type(self, request: CommitteeTypeRequest) -> CommitteeTypeResponse:
        """Create a new committee type"""
        try:
            logger.info(f"Creating new committee type: {request.name}")
            
            # Validate input data
            self.validate_committee_type_data(request)
            
            # Check if committee type with same name already exists in the same division
            existing_types = self.db.get_committee_types(request.hativa_id)
            if any(ct['name'].lower() == request.name.lower() for ct in existing_types):
                raise ValidationError(f'סוג ועדה בשם "{request.name}" כבר קיים בחטיבה זו')
            
            # Create committee type
            committee_type_id = self.db.add_committee_type(
                hativa_id=request.hativa_id,
                name=request.name.strip(),
                scheduled_day=request.scheduled_day,
                frequency=request.frequency,
                week_of_month=request.week_of_month,
                description=request.description.strip()
            )
            
            logger.info(f"Committee type created successfully with ID: {committee_type_id}")
            
            return CommitteeTypeResponse(
                success=True,
                message=f'סוג ועדה "{request.name}" נוסף בהצלחה',
                committee_type_id=committee_type_id
            )
            
        except ValidationError as e:
            logger.warning(f"Validation error creating committee type: {str(e)}")
            return CommitteeTypeResponse(
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.error(f"Error creating committee type: {str(e)}")
            return CommitteeTypeResponse(
                success=False,
                message=f'שגיאה בהוספת סוג הועדה: {str(e)}'
            )
    
    def update_committee_type(self, committee_type_id: int, request: CommitteeTypeRequest) -> CommitteeTypeResponse:
        """Update an existing committee type"""
        try:
            logger.info(f"Updating committee type ID: {committee_type_id}")
            
            # Validate committee type ID
            if not committee_type_id:
                raise ValidationError('מזהה סוג ועדה חסר')
            
            # Validate input data
            self.validate_committee_type_data(request)
            
            # Check if committee type exists
            existing_types = self.db.get_committee_types()
            current_type = next((ct for ct in existing_types if ct['committee_type_id'] == committee_type_id), None)
            if not current_type:
                raise ValidationError('סוג הועדה לא נמצא במערכת')
            
            # Check if another committee type with same name exists in the same division (excluding current one)
            division_types = self.db.get_committee_types(request.hativa_id)
            if any(ct['name'].lower() == request.name.lower() and ct['committee_type_id'] != committee_type_id 
                   for ct in division_types):
                raise ValidationError(f'סוג ועדה בשם "{request.name}" כבר קיים בחטיבה זו')
            
            # Update committee type
            success = self.db.update_committee_type(
                committee_type_id=committee_type_id,
                hativa_id=request.hativa_id,
                name=request.name.strip(),
                scheduled_day=request.scheduled_day,
                frequency=request.frequency,
                week_of_month=request.week_of_month,
                description=request.description.strip()
            )
            
            if success:
                logger.info(f"Committee type updated successfully: {committee_type_id}")
                return CommitteeTypeResponse(
                    success=True,
                    message=f'סוג ועדה "{request.name}" עודכן בהצלחה'
                )
            else:
                raise CommitteeTypeError('לא ניתן לעדכן את סוג הועדה')
            
        except ValidationError as e:
            logger.warning(f"Validation error updating committee type: {str(e)}")
            return CommitteeTypeResponse(
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.error(f"Error updating committee type: {str(e)}")
            return CommitteeTypeResponse(
                success=False,
                message=f'שגיאה בעדכון סוג הועדה: {str(e)}'
            )
    
    def delete_committee_type(self, committee_type_id: int) -> CommitteeTypeResponse:
        """Delete a committee type"""
        try:
            logger.info(f"Deleting committee type ID: {committee_type_id}")
            
            # Validate committee type ID
            if not committee_type_id:
                raise ValidationError('מזהה סוג ועדה חסר')
            
            # Check if committee type exists
            existing_types = self.db.get_committee_types()
            current_type = next((ct for ct in existing_types if ct['committee_type_id'] == committee_type_id), None)
            if not current_type:
                raise ValidationError('סוג הועדה לא נמצא במערכת')
            
            # Attempt to delete
            success = self.db.delete_committee_type(committee_type_id)
            
            if success:
                logger.info(f"Committee type deleted successfully: {committee_type_id}")
                return CommitteeTypeResponse(
                    success=True,
                    message='סוג הועדה נמחק בהצלחה'
                )
            else:
                logger.warning(f"Cannot delete committee type {committee_type_id} - has associated meetings")
                return CommitteeTypeResponse(
                    success=False,
                    message='לא ניתן למחוק סוג ועדה זה - קיימות פגישות המשויכות אליו'
                )
            
        except ValidationError as e:
            logger.warning(f"Validation error deleting committee type: {str(e)}")
            return CommitteeTypeResponse(
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.error(f"Error deleting committee type: {str(e)}")
            return CommitteeTypeResponse(
                success=False,
                message=f'שגיאה במחיקת סוג הועדה: {str(e)}'
            )
    
    def get_committee_type_by_id(self, committee_type_id: int) -> Optional[Dict]:
        """Get a specific committee type by ID"""
        try:
            logger.info(f"Fetching committee type by ID: {committee_type_id}")
            
            committee_types = self.db.get_committee_types()
            committee_type = next((ct for ct in committee_types if ct['committee_type_id'] == committee_type_id), None)
            
            if committee_type:
                logger.info(f"Committee type found: {committee_type['name']}")
            else:
                logger.warning(f"Committee type not found with ID: {committee_type_id}")
            
            return committee_type
            
        except Exception as e:
            logger.error(f"Error fetching committee type by ID: {str(e)}")
            return None
