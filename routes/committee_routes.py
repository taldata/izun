from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from services_init import db, audit_logger, auth_manager
from auth import login_required
from datetime import datetime

committee_bp = Blueprint('committees', __name__, url_prefix='/committees')

@committee_bp.route('/add', methods=['POST'])
def add_committee_meeting():
    """Add new committee meeting"""
    committee_type_id = request.form.get('committee_type_id')
    hativa_id = request.form.get('hativa_id')
    vaada_date = request.form.get('vaada_date')
    notes = request.form.get('notes', '').strip()
    start_time = request.form.get('start_time', '').strip() or None
    end_time = request.form.get('end_time', '').strip() or None

    if not all([committee_type_id, hativa_id, vaada_date]):
        flash('סוג ועדה, חטיבה ותאריך הם שדות חובה', 'error')
        return redirect(url_for('main.index'))

    current_user = auth_manager.get_current_user()
    if not current_user:
        flash('נדרשת התחברות', 'error')
        return redirect(url_for('auth.login'))

    try:
        target_hativa_id = int(hativa_id)
    except (TypeError, ValueError):
        flash('חטיבה לא תקינה', 'error')
        return redirect(url_for('main.index'))

    can_edit, reason = auth_manager.can_edit(target_hativa_id)
    if not can_edit:
        flash(reason, 'error')
        return redirect(url_for('main.index'))

    # Debug logging
    print(f"DEBUG: Received date value: '{vaada_date}' (type: {type(vaada_date).__name__})")

    try:
        # Try multiple date formats to handle different browser formats
        meeting_date = None
        date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
        
        for fmt in date_formats:
            try:
                meeting_date = datetime.strptime(vaada_date, fmt).date()
                break
            except ValueError:
                continue
        
        if meeting_date is None:
            raise ValueError(f'פורמט תאריך לא תקין: {vaada_date}. נא להזין תאריך בפורמט YYYY-MM-DD')
        
        # Check if user is admin for constraint override
        is_admin = current_user.get('role') == 'admin'
        
        # Try to add meeting (admins get warnings instead of errors)
        vaadot_id, warning_message = db.add_vaada(
            int(committee_type_id),
            int(hativa_id),
            meeting_date,
            notes=notes,
            start_time=start_time,
            end_time=end_time,
            override_constraints=is_admin
        )
        
        # Get committee name for logging
        committee_types = db.get_committee_types()
        committee_type = next((ct for ct in committee_types if ct['committee_type_id'] == int(committee_type_id)), None)
        committee_name = committee_type['name'] if committee_type else 'Unknown'
        
        audit_logger.log_vaada_created(vaadot_id, committee_name, meeting_date.strftime('%Y-%m-%d'))
        
        # Show success message with any warnings
        if warning_message:
            flash(f'ישיבת ועדה נוספה בהצלחה. {warning_message}', 'warning')
        else:
            flash('ישיבת ועדה נוספה בהצלחה', 'success')
    except ValueError as e:
        # Check if it's a date format error or our constraint error
        if "כבר קיימת ועדה בתאריך" in str(e):
            audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_VAADA, str(e), details=f'תאריך: {vaada_date}')
            flash(str(e), 'error')
        else:
            audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_VAADA, str(e), details=f'תאריך: {vaada_date}')
            flash(str(e), 'error')
    except Exception as e:
        error_msg = str(e)
        # Handle database constraint errors with user-friendly messages
        if 'UNIQUE constraint failed' in error_msg and 'vaadot' in error_msg:
            error_msg = 'כבר קיימת ועדה מאותו סוג באותה חטיבה באותו תאריך. לא ניתן ליצור ועדה כפולה.'
        audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_VAADA, error_msg, details=f'תאריך: {vaada_date}')
        flash(f'שגיאה בהוספת הישיבה: {error_msg}', 'error')
    
    return redirect(url_for('main.index'))

@committee_bp.route('/edit/<int:vaadot_id>', methods=['POST'])
def edit_committee_meeting(vaadot_id):
    """Edit existing committee meeting"""
    committee_type_id = request.form.get('committee_type_id')
    hativa_id = request.form.get('hativa_id')
    vaada_date = request.form.get('vaada_date')
    notes = request.form.get('notes', '').strip()
    start_time = request.form.get('start_time', '').strip() or None
    end_time = request.form.get('end_time', '').strip() or None

    if not all([committee_type_id, hativa_id, vaada_date]):
        flash('סוג ועדה, חטיבה ותאריך הם שדות חובה', 'error')
        return redirect(url_for('main.index'))

    current_user = auth_manager.get_current_user()
    if not current_user:
        flash('נדרשת התחברות', 'error')
        return redirect(url_for('auth.login'))

    try:
        target_hativa_id = int(hativa_id)
    except (TypeError, ValueError):
        flash('חטיבה לא תקינה', 'error')
        return redirect(url_for('main.index'))

    can_edit, reason = auth_manager.can_edit(target_hativa_id)
    if not can_edit:
        flash(reason, 'error')
        return redirect(url_for('main.index'))

    try:
        # Try multiple date formats to handle different browser formats
        meeting_date = None
        date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
        
        for fmt in date_formats:
            try:
                meeting_date = datetime.strptime(vaada_date, fmt).date()
                break
            except ValueError:
                continue
        
        if meeting_date is None:
            raise ValueError(f'פורמט תאריך לא תקין: {vaada_date}. נא להזין תאריך בפורמט YYYY-MM-DD')
        
        # Get user role for constraint checking
        user_role = session.get('role')
        success = db.update_vaada(vaadot_id, int(committee_type_id), target_hativa_id, meeting_date, notes=notes, start_time=start_time, end_time=end_time, user_role=user_role)
        if success:
            # Get committee name for logging
            committee_types = db.get_committee_types()
            committee_type = next((ct for ct in committee_types if ct['committee_type_id'] == int(committee_type_id)), None)
            committee_name = committee_type['name'] if committee_type else 'Unknown'
            
            audit_logger.log_vaada_updated(vaadot_id, committee_name, meeting_date.strftime('%Y-%m-%d'))
            flash('ישיבת הועדה עודכנה בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון הישיבה', 'error')
    except ValueError as e:
        audit_logger.log_error(audit_logger.ACTION_UPDATE, audit_logger.ENTITY_VAADA, str(e), vaadot_id)
        flash(str(e), 'error')
    except Exception as e:
        audit_logger.log_error(audit_logger.ACTION_UPDATE, audit_logger.ENTITY_VAADA, str(e), vaadot_id)
        flash(f'שגיאה בעדכון הישיבה: {str(e)}', 'error')
    
    return redirect(url_for('main.index'))

@committee_bp.route('/delete/<int:vaadot_id>', methods=['POST'])
def delete_committee_meeting(vaadot_id):
    """Delete committee meeting and its events"""
    try:
        # Get committee details before deletion for logging
        vaada = db.get_vaada_by_id(vaadot_id)
        committee_name = vaada['committee_name'] if vaada else 'Unknown'

        if not vaada:
            flash('ישיבת הועדה לא נמצאה', 'error')
            return redirect(url_for('main.index'))

        current_user = auth_manager.get_current_user()
        if not current_user:
            flash('נדרשת התחברות', 'error')
            return redirect(url_for('auth.login'))

        target_hativa_id = vaada.get('hativa_id')
        if target_hativa_id is None:
            flash('לא ניתן לאמת את חטיבת הועדה', 'error')
            return redirect(url_for('main.index'))

        can_edit, reason = auth_manager.can_edit(int(target_hativa_id))
        if not can_edit:
            flash(reason, 'error')
            return redirect(url_for('main.index'))

        # Get current user
        user_id = current_user['user_id']
        
        # First delete all related events
        events = db.get_all_events()
        related_events = [e for e in events if e['vaadot_id'] == vaadot_id]
        
        for event in related_events:
            db.delete_event(event['event_id'], user_id)
            audit_logger.log_event_deleted(event['event_id'], event['name'])
        
        # Then delete the committee meeting
        success = db.delete_vaada(vaadot_id, user_id)
        if success:
            audit_logger.log_vaada_deleted(vaadot_id, committee_name)
            flash(f'ישיבת הועדה ו-{len(related_events)} אירועים הועברו לסל המחזור בהצלחה', 'success')
        else:
            flash('שגיאה במחיקת הישיבה', 'error')
    except Exception as e:
        audit_logger.log_error(audit_logger.ACTION_DELETE, audit_logger.ENTITY_VAADA, str(e), vaadot_id)
        flash(f'שגיאה במחיקת הישיבה: {str(e)}', 'error')
    
    return redirect(url_for('main.index'))
