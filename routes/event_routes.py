from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, session
from services_init import db, auth_manager, audit_logger
from auth import login_required, editing_permission_required

event_bp = Blueprint('events', __name__)

@event_bp.route('/api/add_event', methods=['POST'])
@login_required
@editing_permission_required
def add_event():
    """Add new event"""
    try:
        current_app.logger.info("Add event request received")
        current_app.logger.info(f"Form data: {request.form}")
        
        vaada_id = int(request.form.get('vaada_id'))
        
        # Check if committee exists and is not deleted
        committee = db.get_vaada_by_id(vaada_id)
        if not committee:
            current_app.logger.error(f"Committee {vaada_id} not found")
            return jsonify({'success': False, 'message': 'ועדה לא נמצאה'}), 404
        
        if committee.get('is_deleted', False):
            current_app.logger.error(f"Committee {vaada_id} is deleted")
            return jsonify({'success': False, 'message': 'לא ניתן להוסיף אירועים לועדה שנמחקה'}), 400
            
        maslul_id = int(request.form.get('maslul_id'))
        name = request.form.get('name')
        event_type = request.form.get('event_type')
        expected_requests = int(request.form.get('expected_requests', 0) or 0)
        priority = int(request.form.get('priority', 1) or 1)
        notes = request.form.get('notes', '')
        
        # Calculate derived values if needed (SLA dates etc)
        # Assuming database logic handles default dates or they are calculated here if not provided
        
        current_app.logger.info(f"Adding event: vaada_id={vaada_id}, maslul_id={maslul_id}, name={name}")
        
        user_role = session.get('role')
        event_id = db.add_event(vaada_id, maslul_id, name, event_type, expected_requests, priority=priority, notes=notes, user_role=user_role)
        
        if event_id:
            current_app.logger.info(f"Event added successfully, ID: {event_id}")
            return jsonify({'success': True, 'event_id': event_id, 'message': 'האירוע נוסף בהצלחה'})
        else:
            current_app.logger.error("Failed to add event - database returned None")
            return jsonify({'success': False, 'message': 'שגיאה בהוספת האירוע'}), 500
            
    except ValueError as e:
        # Business logic error (e.g. max requests exceeded)
        current_app.logger.warning(f"Validation error adding event: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error adding event: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@event_bp.route('/api/update_event', methods=['POST'])
@login_required
@editing_permission_required
def update_event():
    """Update existing event"""
    try:
        event_id = int(request.form.get('event_id'))
        maslul_id = int(request.form.get('maslul_id'))
        name = request.form.get('name')
        event_type = request.form.get('event_type')
        expected_requests = int(request.form.get('expected_requests', 0) or 0)
        actual_submissions = int(request.form.get('actual_submissions', 0) or 0)
        priority = int(request.form.get('priority', 1) or 1)
        notes = request.form.get('notes', '')
        
        # Get custom dates if provided
        custom_dates = {}
        for field in ['call_publication_date', 'call_deadline_date', 'intake_deadline_date', 'review_deadline_date', 'response_deadline_date']:
            val = request.form.get(field)
            if val:
                custom_dates[field] = val
        
        # Check permissions
        current_event = db.get_event_by_id(event_id)
        if not current_event:
            return jsonify({'success': False, 'message': 'אירוע לא נמצא'}), 404
            
        success = db.update_event(
            event_id, maslul_id, name, event_type, expected_requests,
            actual_submissions=actual_submissions,
            priority=priority,
            notes=notes,
            custom_dates=custom_dates
        )
        
        if success:
            audit_logger.log_event_updated(event_id, name)
            return jsonify({'success': True, 'message': 'האירוע עודכן בהצלחה'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה בעדכון האירוע'}), 500
            
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating event: {e}")
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@event_bp.route('/api/delete_event/<int:event_id>', methods=['POST'])
@login_required
@editing_permission_required
def delete_event(event_id):
    """Delete event (soft delete)"""
    try:
        # Get name for logging
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'success': False, 'message': 'אירוע לא נמצא'}), 404
            
        name = event.get('name', 'Unknown')
        vaadot_id = event.get('vaadot_id')
        
        if db.delete_event(event_id):
            return jsonify({'success': True, 'message': 'האירוע נמחק בהצלחה'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה במחיקת האירוע'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error deleting event: {e}")
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

# Event Table View
@event_bp.route('/events_table')
@login_required
def events_table():
    """Events table view with advanced filtering"""
    try:
        # Get all events with extended information
        events = db.get_all_events()

        # Normalize date fields for consistent formatting in the template
        from datetime import datetime, date
        for event in events:
            created_at = event.get('created_at')
            if isinstance(created_at, str):
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                    try:
                        event['created_at'] = datetime.strptime(created_at, fmt)
                        break
                    except ValueError:
                        continue

            for date_field in ['call_deadline_date', 'intake_deadline_date', 'review_deadline_date', 'response_deadline_date', 'vaada_date']:
                value = event.get(date_field)
                if isinstance(value, str):
                    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
                        try:
                            event[date_field] = datetime.strptime(value, fmt).date()
                            break
                        except ValueError:
                            continue

        # Apply chronological ordering (ascending/descending) by committee date
        order = (request.args.get('order') or 'asc').lower()
        order = 'desc' if order == 'desc' else 'asc'

        # Place events without a committee date at the end in both orders
        events_with_date = [e for e in events if e.get('vaada_date')]
        events_without_date = [e for e in events if not e.get('vaada_date')]
        events_with_date.sort(key=lambda e: e.get('vaada_date') or date.max, reverse=(order == 'desc'))
        events = events_with_date + events_without_date

        # Get filter options
        hativot = db.get_hativot()
        maslulim = db.get_maslulim()
        committee_types = db.get_committee_types()

        # Get unique event types
        event_types = list(set([event.get('event_type', '') for event in events if event.get('event_type')]))

        # Get current user info
        current_user = auth_manager.get_current_user()

        return render_template('events_table.html', 
                             events=events,
                             hativot=hativot,
                             maslulim=maslulim,
                             committee_types=committee_types,
                             event_types=event_types,
                             current_user=current_user,
                             order=order)
    except Exception as e:
        flash(f'שגיאה בטעינת נתוני האירועים: {str(e)}', 'error')
        return redirect(url_for('main.index'))
