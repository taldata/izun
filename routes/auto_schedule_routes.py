from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify, current_app
from datetime import date, datetime
import json
from services_init import db, auth_manager, auto_schedule_service, auto_scheduler, committee_types_service
from auth import editor_required

auto_schedule_bp = Blueprint('auto_schedule', __name__)

@auto_schedule_bp.route('/auto_schedule')
@editor_required
def auto_schedule():
    """Automatic meeting scheduling interface"""
    hativot = db.get_hativot()
    committee_types = db.get_committee_types()
    
    # Get current month by default
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    # Get current user info
    current_user = auth_manager.get_current_user()
    
    return render_template('auto_schedule.html', 
                         hativot=hativot, 
                         committee_types=committee_types,
                         current_year=year,
                         current_month=month,
                         current_user=current_user)

@auto_schedule_bp.route('/auto_schedule/generate', methods=['POST'])
@editor_required
def generate_auto_schedule():
    try:
        # Get form data
        year = request.form.get('year', type=int)
        month_selection_type = request.form.get('month_selection_type', 'single')
        selected_hativot = request.form.getlist('hativot_ids')
        
        # Get months based on selection type
        months_to_process = []
        if month_selection_type == 'single':
            month = request.form.get('month', type=int)
            months_to_process = [month]
        elif month_selection_type == 'multiple':
            months_to_process = [int(m) for m in request.form.getlist('months')]
        elif month_selection_type == 'range':
            start_month = request.form.get('start_month', type=int)
            end_month = request.form.get('end_month', type=int)
            if start_month <= end_month:
                months_to_process = list(range(start_month, end_month + 1))
            else:
                # Handle year wrap-around (e.g., Nov-Feb)
                months_to_process = list(range(start_month, 13)) + list(range(1, end_month + 1))
        
        if not months_to_process:
            flash('יש לבחור לפחות חודש אחד', 'warning')
            return redirect(url_for('auto_schedule.auto_schedule'))
        
        # Determine hativa_id - if only one selected, use it; otherwise None for all
        hativa_id = None
        if len(selected_hativot) == 1:
            hativa_id = int(selected_hativot[0])
        elif len(selected_hativot) > 1:
            # Multiple hativot selected - will process all
            pass
        else:
            flash('יש לבחור לפחות חטיבה אחת', 'warning')
            return redirect(url_for('auto_schedule.auto_schedule'))
        
        # Generate schedules for all selected months
        all_suggestions = []
        successful_months = []
        
        from services.auto_schedule_service import ScheduleRequest
        
        for month in months_to_process:
            schedule_request = ScheduleRequest(
                year=year,
                month=month,
                hativa_id=hativa_id,
                auto_approve=False
            )
            
            # Generate schedule using service
            result = auto_schedule_service.generate_schedule(schedule_request)
            
            if result.success and result.suggested_meetings:
                all_suggestions.extend(result.suggested_meetings)
                successful_months.append(month)
                current_app.logger.info(f"Generated {len(result.suggested_meetings)} suggestions for {year}/{month}")
            else:
                current_app.logger.warning(f"Failed to generate schedule for {year}/{month}: {result.message}")
        
        if not all_suggestions:
            months_names = [['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                            'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'][m-1] 
                           for m in months_to_process]
            flash(f'לא ניתן ליצור תזמון עבור החודשים: {", ".join(months_names)}', 'warning')
            return redirect(url_for('auto_schedule.auto_schedule'))
        
        # Store in session for review (using DB draft to avoid cookie size limits)
        
        pending_schedule = {
            'year': year,
            'months': successful_months,
            'month_selection_type': month_selection_type,
            'suggestions': all_suggestions,
            'selected_hativot': selected_hativot
        }
        
        # Determine user_id safely
        user_id = session.get('user_id')
        if not user_id:
             # Fallback if somehow missing, though @editor_required checks it
             current_user = auth_manager.get_current_user()
             user_id = current_user['user_id'] if current_user else 0

        # Serialize using app.json to handle date/time objects
        # We need to access app.json from current_app
        json_data = current_app.json.dumps(pending_schedule)
        
        # Save to database
        draft_id = db.save_schedule_draft(user_id, json_data)
        
        # Clean up old drafts occasionally (1% chance or just do it)
        try:
             import random
             if random.random() < 0.1:
                 db.cleanup_old_drafts(24)
        except Exception:
             pass
        
        # Store only the ID in session
        session['pending_schedule_draft_id'] = draft_id
        session.pop('pending_schedule', None) # Clean up legacy key if exists
        
        current_app.logger.info(f"Stored draft in DB: id={draft_id}, {len(all_suggestions)} suggestions for {year}")
        
        months_names = [['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                        'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'][m-1] 
                       for m in successful_months]
        flash(f'נוצרו {len(all_suggestions)} הצעות ישיבות עבור {", ".join(months_names)} {year}', 'success')
        return redirect(url_for('auto_schedule.review_auto_schedule'))
        
    except Exception as e:
        import traceback
        current_app.logger.error(f'Error generating auto schedule: {str(e)}')
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        flash('שגיאה פנימית ביצירת התזמון. אנא נסה שוב מאוחר יותר.', 'error')
        return redirect(url_for('auto_schedule.auto_schedule'))

@auto_schedule_bp.route('/auto_schedule/review')
@editor_required
def review_auto_schedule():
    """Review generated schedule before approval"""
    
    # Try to get draft ID first
    draft_id = session.get('pending_schedule_draft_id')
    pending_schedule = None
    
    if draft_id:
        # Load from DB
        draft = db.get_schedule_draft(draft_id)
        if draft:
            try:
                pending_schedule = json.loads(draft['data'])
            except json.JSONDecodeError:
                current_app.logger.error(f"Failed to decode draft {draft_id}")
    
    # Fallback to session check (legacy)
    if not pending_schedule:
        pending_schedule = session.get('pending_schedule')

    if not pending_schedule:
        flash('אין לוח זמנים ממתין לאישור (פג תוקף או לא נמצא)', 'warning')
        return redirect(url_for('auto_schedule.auto_schedule'))
    
    # Get hativot and committee types for display
    hativot = {h['hativa_id']: h for h in db.get_hativot()}
    committee_types = {ct['committee_type_id']: ct for ct in db.get_committee_types()}
    
    # Enrich suggestions with names and parse dates
    enriched_suggestions = []
    for suggestion in pending_schedule['suggestions']:
        # Parse dates if they are strings (from JSON)
        if isinstance(suggestion.get('suggested_date'), str):
            suggestion['suggested_date'] = datetime.strptime(suggestion['suggested_date'], '%Y-%m-%dT%H:%M:%S' if 'T' in suggestion['suggested_date'] else '%Y-%m-%d').date()
            
        enriched_suggestions.append({
            **suggestion,
            'hativa_name': hativot.get(suggestion['hativa_id'], {}).get('name', 'לא ידוע'),
            'committee_type_name': suggestion['committee_type']
        })
    
    # Validate schedule constraints for all months
    validation_result = {'valid': True, 'violations': [], 'warnings': []}
    
    # If we have multiple months, validate each one
    months = pending_schedule.get('months', [pending_schedule.get('month')])
    for month in months:
        if month:  # Skip None values
            month_validation = auto_scheduler.validate_schedule_constraints(
                pending_schedule['year'], month
            )
            if not month_validation['valid']:
                validation_result['valid'] = False
                validation_result['violations'].extend(month_validation.get('violations', []))
            validation_result['warnings'].extend(month_validation.get('warnings', []))
    
    # Get current user info
    current_user = auth_manager.get_current_user()
    
    return render_template('review_auto_schedule.html',
                         suggestions=enriched_suggestions,
                         schedule_info=pending_schedule,
                         validation=validation_result,
                         current_user=current_user)

@auto_schedule_bp.route('/auto_schedule/approve', methods=['POST'])
@editor_required
def approve_auto_schedule():
    """Approve and create selected meetings from the generated schedule"""
    
    try:
        draft_id = session.get('pending_schedule_draft_id')
        pending_schedule = None
        
        if draft_id:
            draft = db.get_schedule_draft(draft_id)
            if draft:
                pending_schedule = json.loads(draft['data'])
        
        # Fallback
        if not pending_schedule:
            pending_schedule = session.get('pending_schedule')

        if not pending_schedule:
            flash('אין לוח זמנים ממתין לאישור', 'warning')
            return redirect(url_for('auto_schedule.auto_schedule'))
        
        selected_meetings = request.form.getlist('selected_meetings')
        if not selected_meetings:
            flash('יש לבחור לפחות הצעה אחת', 'warning')
            return redirect(url_for('auto_schedule.review_auto_schedule'))
        
        # Convert to integers and get selected suggestions
        selected_indices = [int(idx) for idx in selected_meetings]
        suggestions = pending_schedule.get('suggestions', [])
        
        # Filter selected suggestions
        selected_meeting_suggestions = []
        for idx in selected_indices:
            if 0 <= idx < len(suggestions):
                sug = suggestions[idx]
                # Ensure date objects
                if isinstance(sug.get('suggested_date'), str):
                     # Handle ISO format or simple date
                     date_str = sug['suggested_date']
                     if 'T' in date_str:
                         sug['suggested_date'] = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S').date()
                     else:
                         sug['suggested_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                selected_meeting_suggestions.append(sug)
        
        if not selected_meeting_suggestions:
            flash('לא נמצאו הצעות תקינות לאישור', 'error')
            return redirect(url_for('auto_schedule.review_auto_schedule'))
        
        # Create approval request
        from services.auto_schedule_service import ApprovalRequest
        approval_request = ApprovalRequest(
            suggestions=selected_meeting_suggestions
        )
        
        # Approve meetings using service
        result = auto_schedule_service.approve_meetings(approval_request)
        
        # Clear session and DB draft
        session.pop('pending_schedule', None)
        session.pop('pending_schedule_draft_id', None)
        if draft_id:
            db.delete_schedule_draft(draft_id)
        
        # Show results
        if result.success_count > 0:
            flash(f'נוצרו בהצלחה {result.success_count} ישיבות', 'success')
        
        if result.failure_count > 0:
            failed_reasons = [f"{m['committee_type']}: {m['reason']}" for m in result.failed_meetings[:3]]
            flash(f'נכשלו {result.failure_count} ישיבות: {"; ".join(failed_reasons)}', 'warning')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        import traceback
        current_app.logger.error(f'Error approving auto schedule: {str(e)}')
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        flash('שגיאה פנימית באישור התזמון. אנא נסה שוב מאוחר יותר.', 'error')
        return redirect(url_for('auto_schedule.review_auto_schedule'))

@auto_schedule_bp.route('/auto_schedule/validate/<int:year>/<int:month>')
def validate_monthly_schedule(year: int, month: int):
    """API endpoint to validate monthly schedule constraints"""
    try:
        validation_result = auto_schedule_service.get_schedule_validation(year, month)
        return jsonify(validation_result)
    except Exception as e:
        return jsonify({
            'valid': False,
            'violations': [f'שגיאה באימות: {str(e)}'],
            'warnings': [],
            'total_meetings': 0
        })
