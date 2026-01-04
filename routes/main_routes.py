from flask import Blueprint, render_template, abort, current_app
from services_init import db, auth_manager
from auth import login_required
from datetime import date

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Main dashboard"""
    # Get summary statistics
    hativot = db.get_hativot()
    maslulim = db.get_maslulim()
    committee_types = db.get_committee_types()
    committees = db.get_vaadot()  # This now returns meeting instances
    events = db.get_all_events()
    exception_dates = db.get_exception_dates()
    
    # Debug logging
    current_app.logger.info(f"Loaded {len(committees)} committees")
    current_app.logger.info(f"Loaded {len(events)} events")
    if committees:
        current_app.logger.info(f"First committee: {committees[0]}")
    if events:
        current_app.logger.info(f"First event: {events[0]}")
    
    stats = {
        'hativot_count': len(hativot),
        'maslulim_count': len(maslulim),
        'committee_types_count': len(committee_types),
        'committees_count': len(committees),
        'events_count': len(events),
        'exception_dates_count': len(exception_dates),
        'business_days_this_month': 0
    }
    
    # Get current user info
    current_user = auth_manager.get_current_user()
    
    # Get deadline dates display setting
    show_deadline_dates = db.get_system_setting('show_deadline_dates_in_calendar') == '1'
    
    return render_template('index.html', 
                         hativot=hativot, 
                         maslulim=maslulim, 
                         committee_types=committee_types,
                         committees=committees,
                         events=events,
                         exception_dates=exception_dates,
                         stats=stats,
                         current_user=current_user,
                         show_deadline_dates=show_deadline_dates)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Analytics Dashboard - DISABLED"""
    abort(404)  # Dashboard is disabled

@main_bp.route('/user_guide')
def user_guide():
    """User guide page"""
    current_user = auth_manager.get_current_user()
    return render_template('user_guide.html', current_user=current_user)
