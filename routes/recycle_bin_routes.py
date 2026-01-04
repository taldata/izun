from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from services_init import db, auth_manager, audit_logger
from auth import editor_required

recycle_bin_bp = Blueprint('recycle_bin', __name__)

@recycle_bin_bp.route('/recycle_bin')
@editor_required
def recycle_bin():
    """Recycle bin view for deleted items"""
    try:
        current_user = auth_manager.get_current_user()
        
        # Managers and editors can only see their division's deleted items
        hativa_id = None
        if current_user['role'] in ['manager', 'editor'] and current_user.get('hativa_id'):
            hativa_id = current_user['hativa_id']
        
        deleted_vaadot = db.get_deleted_vaadot(hativa_id)
        deleted_events = db.get_deleted_events(hativa_id)
        
        return render_template('recycle_bin.html',
                             deleted_vaadot=deleted_vaadot,
                             deleted_events=deleted_events,
                             current_user=current_user)
    except Exception as e:
        flash(f'שגיאה בטעינת סל המחזור: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@recycle_bin_bp.route('/api/recycle_bin/restore_vaada/<int:vaadot_id>', methods=['POST'])
@editor_required
def restore_vaada_route(vaadot_id):
    """Restore a deleted committee meeting"""
    try:
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401
        
        # Users cannot restore
        if user['role'] == 'user':
            return jsonify({'success': False, 'message': 'משתמשים רגילים לא יכולים לשחזר פריטים'}), 403
        
        # Get the vaada to check permissions for managers/editors
        deleted_vaadot = db.get_deleted_vaadot()
        vaada = next((v for v in deleted_vaadot if v['vaadot_id'] == vaadot_id), None)
        
        if not vaada:
            return jsonify({'success': False, 'message': 'ועדה לא נמצאה בסל המחזור'}), 404
        
        # Check division permissions for managers/editors
        if user['role'] in ['manager', 'editor'] and vaada['hativa_id'] != user.get('hativa_id'):
            return jsonify({'success': False, 'message': 'ניתן לשחזר רק ועדות מהחטיבה שלך'}), 403
        
        success = db.restore_vaada(vaadot_id)
        if success:
            audit_logger.log_success(
                audit_logger.ACTION_CREATE,
                audit_logger.ENTITY_VAADA,
                details=f'שחזור ועדה מסל המחזור: {vaada["committee_name"]}'
            )
            return jsonify({'success': True, 'message': 'הועדה שוחזרה בהצלחה'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה בשחזור הועדה'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@recycle_bin_bp.route('/api/recycle_bin/restore_event/<int:event_id>', methods=['POST'])
@editor_required
def restore_event_route(event_id):
    """Restore a deleted event"""
    try:
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401
        
        # Users cannot restore
        if user['role'] == 'user':
            return jsonify({'success': False, 'message': 'משתמשים רגילים לא יכולים לשחזר פריטים'}), 403
        
        # Get the event to check permissions for managers/editors
        deleted_events = db.get_deleted_events()
        event = next((e for e in deleted_events if e['event_id'] == event_id), None)
        
        if not event:
            return jsonify({'success': False, 'message': 'אירוע לא נמצא בסל המחזור'}), 404
        
        # Check division permissions for managers/editors
        if user['role'] in ['manager', 'editor'] and event['maslul_hativa_id'] != user.get('hativa_id'):
            return jsonify({'success': False, 'message': 'ניתן לשחזר רק אירועים מהחטיבה שלך'}), 403
        
        success = db.restore_event(event_id)
        if success:
            audit_logger.log_success(
                audit_logger.ACTION_CREATE,
                audit_logger.ENTITY_EVENT,
                details=f'שחזור אירוע מסל המחזור: {event["name"]}'
            )
            return jsonify({'success': True, 'message': 'האירוע שוחזר בהצלחה'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה בשחזור האירוע'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@recycle_bin_bp.route('/api/recycle_bin/permanent_delete_vaada/<int:vaadot_id>', methods=['POST'])
@editor_required
def permanent_delete_vaada_route(vaadot_id):
    """Permanently delete a committee meeting"""
    try:
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401
        
        # Only admins can permanently delete
        if user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'רק מנהלי מערכת יכולים למחוק לצמיתות'}), 403
        
        # Get the vaada info for logging
        deleted_vaadot = db.get_deleted_vaadot()
        vaada = next((v for v in deleted_vaadot if v['vaadot_id'] == vaadot_id), None)
        
        if not vaada:
            return jsonify({'success': False, 'message': 'ועדה לא נמצאה בסל המחזור'}), 404
        
        success = db.permanently_delete_vaada(vaadot_id)
        if success:
            audit_logger.log_success(
                audit_logger.ACTION_DELETE,
                audit_logger.ENTITY_VAADA,
                details=f'מחיקה לצמיתות: {vaada["committee_name"]}'
            )
            return jsonify({'success': True, 'message': 'הועדה נמחקה לצמיתות'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה במחיקה לצמיתות'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@recycle_bin_bp.route('/api/recycle_bin/permanent_delete_event/<int:event_id>', methods=['POST'])
@editor_required
def permanent_delete_event_route(event_id):
    """Permanently delete an event"""
    try:
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401
        
        # Only admins can permanently delete
        if user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'רק מנהלי מערכת יכולים למחוק לצמיתות'}), 403
        
        # Get the event info for logging
        deleted_events = db.get_deleted_events()
        event = next((e for e in deleted_events if e['event_id'] == event_id), None)
        
        if not event:
            return jsonify({'success': False, 'message': 'אירוע לא נמצא בסל המחזור'}), 404
        
        success = db.permanently_delete_event(event_id)
        if success:
            audit_logger.log_success(
                audit_logger.ACTION_DELETE,
                audit_logger.ENTITY_EVENT,
                details=f'מחיקה לצמיתות: {event["name"]}'
            )
            return jsonify({'success': True, 'message': 'האירוע נמחק לצמיתות'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה במחיקה לצמיתות'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@recycle_bin_bp.route('/api/recycle_bin/empty', methods=['POST'])
@editor_required
def empty_recycle_bin_route():
    """Empty the recycle bin (permanently delete all items)"""
    try:
        user = auth_manager.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'נדרשת התחברות'}), 401
        
        # Only admins can empty recycle bin
        if user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'רק מנהלי מערכת יכולים לרוקן את סל המחזור'}), 403
        
        vaadot_deleted, events_deleted = db.empty_recycle_bin()
        
        audit_logger.log_success(
            audit_logger.ACTION_DELETE,
            'recycle_bin',
            details=f'ריקון סל מחזור: {vaadot_deleted} ועדות, {events_deleted} אירועים'
        )
        
        return jsonify({
            'success': True, 
            'message': f'סל המחזור רוקן בהצלחה',
            'vaadot_deleted': vaadot_deleted,
            'events_deleted': events_deleted
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
