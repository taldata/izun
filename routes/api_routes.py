from flask import Blueprint, jsonify, request, current_app, session
from services_init import db, audit_logger, auth_manager
from auth import admin_required, login_required, editing_permission_required
from datetime import datetime
from services.committee_service import get_committee_summary

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/toggle_editing_period', methods=['POST'])
@admin_required
def toggle_editing_period():
    """Toggle editing period active status"""
    try:
        new_status = db.toggle_system_setting('editing_period_active')
        
        # Log setting change
        user_id = auth_manager.get_current_user()['user_id']
        current_app.logger.info(f"Editing period toggled to {new_status} by user {user_id}")
        
        return jsonify({
            'success': True, 
            'is_active': new_status == '1',
            'message': 'תקופת העריכה הופעלה בהצלחה' if new_status == '1' else 'תקופת העריכה הושבתה בהצלחה'
        })
    except Exception as e:
        current_app.logger.error(f"Error toggling editing period: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/api/toggle_ad_sync', methods=['POST'])
@admin_required
def toggle_ad_sync():
    """Toggle AD sync active status"""
    try:
        new_status = db.toggle_system_setting('ad_sync_enabled')
        
        # Log setting change
        user_id = auth_manager.get_current_user()['user_id']
        
        status_msg = 'פעיל' if new_status == '1' else 'לא פעיל'
        audit_logger.log(
            'update_setting', 
            'system_settings', 
            None, 
            'ad_sync_enabled', 
            f'שינוי סטטוס סנכרון ל-{status_msg}'
        )
        
        return jsonify({
            'success': True, 
            'is_active': new_status == '1',
            'message': 'סנכרון AD הופעל בהצלחה' if new_status == '1' else 'סנכרון AD הושבת בהצלחה'
        })
    except Exception as e:
        current_app.logger.error(f"Error toggling AD sync: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/api/bulk_delete', methods=['POST'])
@login_required
@editing_permission_required
def bulk_delete():
    """Bulk delete committees and events"""
    try:
        current_app.logger.info("Bulk delete request received")
        current_app.logger.info(f"Form data: {request.form}")
        
        item_type = request.form.get('type')
        item_ids = request.form.getlist('ids[]')
        
        current_app.logger.info(f"Processing delete for type={item_type}, ids={item_ids}")
        
        if not item_ids:
            return jsonify({'success': False, 'message': 'לא נבחרו פריטים למחיקה'})
            
        success_count = 0
        error_count = 0
        
        if item_type == 'committee':
            for vaada_id in item_ids:
                if db.delete_vaada(int(vaada_id)):
                    success_count += 1
                else:
                    error_count += 1
            
            message = f'נמחקו בהצלחה {success_count} ועדות'
            if error_count > 0:
                message += f', {error_count} נכשלו'
                
        elif item_type == 'event':
            for event_id in item_ids:
                if db.delete_event(int(event_id)):
                    success_count += 1
                else:
                    error_count += 1
            
            message = f'נמחקו בהצלחה {success_count} אירועים'
            if error_count > 0:
                message += f', {error_count} נכשלו'
        else:
            return jsonify({'success': False, 'message': 'סוג פריט לא חוקי'})
            
        return jsonify({
            'success': True, 
            'message': message,
            'count': success_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in bulk delete: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'שגיאה במחיקה: {str(e)}'}), 500

@api_bp.route('/api/move_committee', methods=['POST'])
@login_required
def move_committee():
    """Move committee meeting to a different date"""
    try:
        data = request.get_json()
        vaada_id = data.get('vaada_id')
        new_date = data.get('new_date')
        
        if not vaada_id or not new_date:
            return jsonify({'success': False, 'message': 'נתונים חסרים'}), 400
        
        # Get current user
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401
        
        # Get committee details to check permissions
        vaada = db.get_vaada_by_id(vaada_id)
        if not vaada:
            return jsonify({'success': False, 'message': 'ועדה לא נמצאה'}), 404
        
        # Check permissions: Only managers and admins can move committees
        if user['role'] == 'user':
            return jsonify({'success': False, 'message': 'רק מנהלים ומנהלי מערכת יכולים להזיז ועדות'}), 403
        
        # Manager can only move committees in their division
        if user['role'] == 'manager':
            if vaada['hativa_id'] != user['hativa_id']:
                return jsonify({'success': False, 'message': 'מנהל יכול להזיז רק ועדות בחטיבה שלו'}), 403
        
        # Admin can move any committee (no additional checks needed)
        
        # Validate date format and convert to date object
        try:
            new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'פורמט תאריך לא תקין'}), 400
        
        # Ensure target date is an allowed business day
        if not db.is_work_day(new_date_obj):
            return jsonify({'success': False, 'message': 'לא ניתן להעביר ועדה ליום שאינו יום עסקים'}), 400

        # Check if target date is available (one meeting per day constraint)
        # But allow moving the same committee to a different date
        existing_meetings = db.get_vaada_by_date(new_date_obj)
        if existing_meetings and any(meeting['vaadot_id'] != vaada_id for meeting in existing_meetings):
            return jsonify({'success': False, 'message': 'התאריך תפוס - יש כבר ועדה ביום זה'}), 400
        
        # Store old date and committee name for logging
        old_date = vaada['vaada_date'] if vaada else 'Unknown'
        committee_name = vaada['committee_name'] if vaada else 'Unknown'
        
        # Update committee meeting date
        try:
            user_role = session.get('role')
            success = db.update_vaada_date(vaada_id, new_date_obj, user_role=user_role)
        except ValueError as ve:
            audit_logger.log_error(
                audit_logger.ACTION_MOVE,
                audit_logger.ENTITY_VAADA,
                str(ve),
                entity_id=vaada_id,
                entity_name=committee_name,
                details=f'נסיון העברה מ-{old_date} ל-{new_date}'
            )
            return jsonify({'success': False, 'message': str(ve)}), 400
        
        if success:
            # Log successful move
            audit_logger.log_vaada_moved(vaada_id, committee_name, old_date, new_date)
            return jsonify({'success': True, 'message': 'הועדה הועברה בהצלחה'})
        else:
            audit_logger.log_error(
                audit_logger.ACTION_MOVE,
                audit_logger.ENTITY_VAADA,
                'שגיאה בעדכון מסד נתונים',
                entity_id=vaada_id,
                entity_name=committee_name
            )
            return jsonify({'success': False, 'message': 'שגיאה בהעברת הועדה'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error moving committee: {str(e)}")
        audit_logger.log_error(
            audit_logger.ACTION_MOVE,
            audit_logger.ENTITY_VAADA,
            str(e),
            entity_id=vaada_id if 'vaada_id' in locals() else None
        )
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@api_bp.route('/api/duplicate_committee', methods=['POST'])
@login_required
def duplicate_committee():
    """Duplicate a committee (vaada) with all its events to a new date"""
    try:
        data = request.get_json(silent=True) or {}
        source_vaada_id = data.get('source_vaada_id')
        target_date = data.get('target_date')

        if not source_vaada_id or not target_date:
            return jsonify({'success': False, 'message': 'נתונים חסרים'}), 400

        # Get current user
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401

        # Validate target date
        try:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'פורמט תאריך לא תקין'}), 400

        if not db.is_work_day(target_date_obj):
            return jsonify({'success': False, 'message': 'לא ניתן לשכפל ליום שאינו יום עסקים'}), 400

        # Fetch source committee
        source_vaada = db.get_vaada_by_id(int(source_vaada_id))
        if not source_vaada:
            return jsonify({'success': False, 'message': 'ועדה מקורית לא נמצאה'}), 404

        # Permissions: user cannot duplicate; managers only within their division; admins allowed
        if user['role'] == 'user':
            return jsonify({'success': False, 'message': 'רק מנהלים ומנהלי מערכת יכולים לשכפל ועדות'}), 403
        if user['role'] == 'manager' and source_vaada['hativa_id'] != user.get('hativa_id'):
            return jsonify({'success': False, 'message': 'מנהל יכול לשכפל רק ועדות בחטיבה שלו'}), 403

        # Ensure no conflicting committee on target date (limit per day)
        if not db.is_date_available_for_meeting(target_date_obj):
            return jsonify({'success': False, 'message': 'התאריך תפוס - יש כבר ועדה ביום זה'}), 400

        # Perform duplication via DB helper (admin can override constraints as warnings)
        result = db.duplicate_vaada_with_events(
            source_vaadot_id=int(source_vaada_id),
            target_date=target_date_obj,
            created_by=user.get('user_id'),
            override_constraints=(user['role'] == 'admin')
        )

        # Log creation of the new vaada
        new_vaada = db.get_vaada_by_id(result['new_vaadot_id'])
        if new_vaada:
            audit_logger.log_vaada_created(result['new_vaadot_id'], new_vaada.get('committee_name', 'Unknown'), new_vaada.get('vaada_date', ''))

        message = f"הועדה שוכפלה בהצלחה ל-{target_date}. הועתקו {result['copied_events']} אירועים."
        if result.get('warning_message'):
            message += f"\n{result['warning_message']}"

        return jsonify({'success': True, 'message': message, 'new_vaadot_id': result['new_vaadot_id'], 'copied_events': result['copied_events']})

    except ValueError as e:
        audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_VAADA, str(e))
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error duplicating committee: {str(e)}")
        audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_VAADA, str(e))
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@api_bp.route('/api/move_event', methods=['POST'])
@login_required
@editing_permission_required
def move_event():
    """Move event to a different committee meeting"""
    try:
        data = request.get_json()
        event_id = data.get('event_id')
        target_vaada_id = data.get('target_vaada_id')
        
        if not event_id or not target_vaada_id:
            return jsonify({'success': False, 'message': 'נתונים חסרים'}), 400
        
        # Get event and target committee details for validation
        current_app.logger.info(f"Looking for event_id: {event_id}, target_vaada_id: {target_vaada_id}")
        event = db.get_event_by_id(event_id)
        target_committee = db.get_vaada_by_id(target_vaada_id)
        
        current_app.logger.info(f"Found event: {event}")
        current_app.logger.info(f"Found target_committee: {target_committee}")
        
        if not event or not target_committee:
            current_app.logger.error(f"Event or committee not found. Event: {event}, Committee: {target_committee}")
            return jsonify({'success': False, 'message': 'אירוע או ועדה לא נמצאו'}), 404
        
        # Validate that event's route belongs to target committee's division
        route = db.get_maslul_by_id(event['maslul_id'])
        if route['hativa_id'] != target_committee['hativa_id']:
            audit_logger.log_error(
                audit_logger.ACTION_MOVE,
                audit_logger.ENTITY_EVENT,
                'ניסיון להעביר אירוע לועדה מחטיבה אחרת',
                entity_id=event_id,
                entity_name=event.get('name', 'Unknown')
            )
            return jsonify({'success': False, 'message': 'לא ניתן להעביר אירוע לועדה מחטיבה אחרת'}), 400
        
        # Get source committee name for logging
        source_vaada = db.get_vaada_by_id(event.get('vaadot_id'))
        source_committee_name = source_vaada['committee_name'] if source_vaada else 'Unknown'
        
        # Update event's committee meeting (includes max requests validation)
        user_role = session.get('role')
        success = db.update_event_vaada(event_id, target_vaada_id, user_role=user_role)
        
        if success:
            # Log successful move
            audit_logger.log_event_moved(
                event_id,
                event.get('name', 'Unknown'),
                source_committee_name,
                target_committee['committee_name']
            )
            return jsonify({'success': True, 'message': 'האירוע הועבר בהצלחה'})
        else:
            audit_logger.log_error(
                audit_logger.ACTION_MOVE,
                audit_logger.ENTITY_EVENT,
                'שגיאה בעדכון מסד נתונים',
                entity_id=event_id,
                entity_name=event.get('name', 'Unknown')
            )
            return jsonify({'success': False, 'message': 'שגיאה בהעברת האירוע'}), 500
    
    except ValueError as e:
        # Handle constraint violations
        current_app.logger.warning(f"Event move blocked by constraint: {str(e)}")
        audit_logger.log_error(
            audit_logger.ACTION_MOVE,
            audit_logger.ENTITY_EVENT,
            str(e),
            entity_id=event_id if 'event_id' in locals() else None
        )
        return jsonify({'success': False, 'message': str(e)}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error moving event: {str(e)}")
        audit_logger.log_error(
            audit_logger.ACTION_MOVE,
            audit_logger.ENTITY_EVENT,
            str(e),
            entity_id=event_id if 'event_id' in locals() else None
        )
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@api_bp.route('/api/events_by_committee')
@login_required
def get_events_by_committee():
    """API endpoint to get events grouped by committee meetings"""
    try:
        # Get all events
        events = db.get_all_events()
        include_empty = request.args.get('include_empty') in ('1', 'true', 'True')

        # Group events by committee meeting (vaadot_id)
        events_by_committee = {}
        for event in events:
            vaadot_id = event.get('vaadot_id')
            if vaadot_id:
                if vaadot_id not in events_by_committee:
                    events_by_committee[vaadot_id] = {
                        'committee_info': {
                            'vaadot_id': vaadot_id,
                            'committee_name': event.get('committee_name', ''),
                            'hativa_name': event.get('hativa_name', ''),
                            'hativa_id': event.get('maslul_hativa_id') or event.get('hativa_id'),
                            'vaada_date': event.get('vaada_date', ''),
                            'committee_type': event.get('committee_type_name', ''),
                            'committee_type_id': event.get('committee_type_id')
                        },
                        'events': [],
                        'summary': {
                            'total_events': 0,
                            'total_expected_requests': 0,
                            'total_actual_submissions': 0,
                            'event_types': set()
                        }
                    }
                events_by_committee[vaadot_id]['events'].append(event)

                # Update summary
                summary = events_by_committee[vaadot_id]['summary']
                summary['total_events'] += 1
                summary['total_expected_requests'] += event.get('expected_requests', 0) or 0
                summary['total_actual_submissions'] += event.get('actual_submissions', 0) or 0
                if event.get('event_type'):
                    summary['event_types'].add(event.get('event_type'))

        # Optionally include committees without events
        if include_empty:
            committees = db.get_vaadot()
            for c in committees:
                vid = c.get('vaadot_id')
                if vid not in events_by_committee:
                    events_by_committee[vid] = {
                        'committee_info': {
                            'vaadot_id': vid,
                            'committee_name': c.get('committee_name', ''),
                            'hativa_name': c.get('hativa_name', ''),
                            'hativa_id': c.get('hativa_id'),
                            'vaada_date': c.get('vaada_date', ''),
                            'committee_type': '',
                            'committee_type_id': c.get('committee_type_id')
                        },
                        'events': [],
                        'summary': {
                            'total_events': 0,
                            'total_expected_requests': 0,
                            'total_actual_submissions': 0,
                            'event_types': set()
                        }
                    }

        # Convert to list and format for JSON response
        result = []
        for vaadot_id, data in events_by_committee.items():
            # Convert set to list for JSON serialization
            data['summary']['event_types'] = list(data['summary']['event_types'])
            result.append(data)

        # Sort by committee date (newest first)
        result.sort(key=lambda x: x['committee_info']['vaada_date'] or '', reverse=True)

        return jsonify({
            'success': True,
            'events_by_committee': result,
            'total_committees': len(result)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/api/committees/<int:committee_id>/summary')
@login_required
def committee_summary(committee_id: int):
    """Return committee details and up to 5 nearest events for hover popover"""
    try:
        summary = get_committee_summary(db, committee_id)
        status_code = 200 if summary.get('success') else 404
        return jsonify(summary), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/api/maslulim/<int:maslul_id>/details')
@login_required
def maslul_details(maslul_id):
    """Get details of a specific route including event count"""
    try:
        maslul = db.get_maslul_by_id(maslul_id)
        if not maslul:
            return jsonify({'success': False, 'error': 'המסלול לא נמצא'}), 404
            
        # Get count of events using this maslul
        events = db.get_all_events()
        maslul_events = [e for e in events if e.get('maslul_id') == maslul_id]
        events_count = len(maslul_events)
        
        # Add basic info
        data = {
            'maslul_id': maslul['maslul_id'],
            'name': maslul['name'],
            'hativa_name': maslul['hativa_name'],
            'description': maslul.get('description'),
            'events_count': events_count,
            'can_delete': events_count == 0
        }
        
        return jsonify({'success': True, 'data': data})
        
    except Exception as e:
        current_app.logger.error(f"Error getting maslul details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
