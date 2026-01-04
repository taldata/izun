from database import DatabaseManager
from services.ad_service import ADService
from services.auto_schedule_service import AutoScheduleService
from services.audit_logger import AuditLogger
from services.constraints_service import ConstraintsService
from services.committee_types_service import CommitteeTypesService
from services.committee_recommendation_service import CommitteeRecommendationService
from services.calendar_service import CalendarService
from services.calendar_sync_scheduler import CalendarSyncScheduler
from auto_scheduler import AutoMeetingScheduler
from auth import AuthManager

# Initialize database
db = DatabaseManager()

# Initialize services
ad_service = ADService(db)
auto_scheduler = AutoMeetingScheduler(db)
auto_schedule_service = AutoScheduleService(db)
audit_logger = AuditLogger(db)
constraints_service = ConstraintsService(db, audit_logger)
committee_types_service = CommitteeTypesService(db)
committee_recommendation_service = CommitteeRecommendationService(db)
auth_manager = AuthManager(db, ad_service)

# Initialize calendar sync components
calendar_service = CalendarService(ad_service, db)
calendar_sync_scheduler = CalendarSyncScheduler(calendar_service, db, audit_logger)
