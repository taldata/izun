from flask import Blueprint, jsonify, session, current_app
from services_init import calendar_service, calendar_sync_scheduler, audit_logger
from auth import admin_required, login_required
import threading

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/api/calendar/sync', methods=['POST'])
@login_required
@admin_required
def trigger_calendar_sync():
    """Manually trigger full calendar sync (runs in background)"""
    
    def run_sync_async(username):
        """Run sync in background thread"""
        try:
            current_app.logger.info(f"Background sync started by {username}")
            result = calendar_service.sync_all()
            current_app.logger.info(f"Background sync completed: {result.get('committees_synced', 0)} committees, {result.get('events_synced', 0)} events")
        except Exception as e:
            current_app.logger.error(f"Error in background sync: {e}", exc_info=True)
    
    try:
        username = session.get('username', 'unknown')
        current_app.logger.info(f"Manual calendar sync triggered by user {username}")

        # Log audit BEFORE starting thread (while we have request context)
        audit_logger.log(
            action='calendar_sync',
            entity_type='calendar',
            entity_id=None,
            entity_name='manual_sync',
            details="Sync started in background",
            status='success'
        )
        
        # Start background thread since sync takes a while (Graph API is slow)
        thread = threading.Thread(target=run_sync_async, args=(username,))
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'סנכרון הותחל ברקע. התהליך יושלם תוך 1-2 דקות.',
            'committees_synced': 0,
            'events_synced': 0,
            'failures': 0,
            'background': True
        })

    except Exception as e:
        current_app.logger.error(f"Error in manual calendar sync: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@calendar_bp.route('/api/calendar/sync/reset', methods=['POST'])
@login_required
@admin_required
def reset_calendar_sync():
    """Reset calendar sync: clear sync records and re-sync everything (runs in background)"""
    
    def run_reset_async(username):
        """Run reset in background thread"""
        try:
            current_app.logger.info(f"Background reset started by {username}")
            result = calendar_service.delete_all_calendar_events_and_reset()
            current_app.logger.info(f"Background reset completed: {result.get('message')}")
        except Exception as e:
            current_app.logger.error(f"Error in background reset: {e}", exc_info=True)
    
    try:
        username = session.get('username', 'unknown')
        current_app.logger.info(f"Calendar sync reset triggered by user {username}")
        
        # Log audit BEFORE starting thread (while we have request context)
        audit_logger.log(
            action='calendar_sync_reset',
            entity_type='calendar',
            entity_id=None,
            entity_name='full_reset',
            details="Reset started in background",
            status='success'
        )
        
        # Start background thread since sync takes a while (Graph API is slow)
        thread = threading.Thread(target=run_reset_async, args=(username,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'איפוס וסנכרון הותחלו ברקע. התהליך יושלם תוך 1-2 דקות.',
            'events_deleted': 0,
            'deletion_failures': 0,
            'records_cleared': 0,
            'committees_synced': 0,
            'events_synced': 0,
            'failures': 0,
            'background': True
        })

    except Exception as e:
        current_app.logger.error(f"Error starting calendar reset: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@calendar_bp.route('/api/calendar/sync/status')
@login_required
@admin_required
def calendar_sync_status():
    """Get calendar sync status"""
    try:
        # Use existing methods
        next_run = calendar_sync_scheduler.get_next_run_time()
        is_running = calendar_sync_scheduler.is_scheduler_running()
        sync_enabled = calendar_service.is_enabled()

        return jsonify({
            'success': True,
            'sync_enabled': sync_enabled,
            'scheduler_running': is_running,
            'next_run_time': next_run.isoformat() if next_run else None,
            'calendar_email': calendar_service.calendar_email
        })
    except Exception as e:
        current_app.logger.error(f"Error getting calendar sync status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@calendar_bp.route('/api/calendar/sync/committee/<int:vaadot_id>', methods=['POST'])
@login_required
@admin_required
def sync_committee_to_calendar(vaadot_id):
    """Sync a single committee to calendar"""
    try:
        current_app.logger.info(f"Syncing committee {vaadot_id} to calendar by user {session.get('username')}")

        success, message = calendar_service.sync_committee_to_calendar(vaadot_id)

        # Log to audit
        audit_logger.log(
            action='calendar_sync_committee',
            entity_type='vaadot',
            entity_id=vaadot_id,
            entity_name=f'Committee {vaadot_id}',
            details=message,
            status='success' if success else 'error',
            error_message=message if not success else None
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 500

    except Exception as e:
        current_app.logger.error(f"Error syncing committee {vaadot_id}: {e}", exc_info=True)
        audit_logger.log_error('calendar_sync_committee', 'vaadot', str(e), entity_id=vaadot_id)
        return jsonify({'success': False, 'message': str(e)}), 500

@calendar_bp.route('/api/calendar/sync/event/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def sync_event_to_calendar(event_id):
    """Sync a single event's deadlines to calendar"""
    try:
        current_app.logger.info(f"Syncing event {event_id} to calendar by user {session.get('username')}")

        success, message = calendar_service.sync_event_deadlines_to_calendar(event_id)

        # Log to audit
        audit_logger.log(
            action='calendar_sync_event',
            entity_type='events',
            entity_id=event_id,
            entity_name=f'Event {event_id}',
            details=message,
            status='success' if success else 'error',
            error_message=message if not success else None
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 500

    except Exception as e:
        current_app.logger.error(f"Error syncing event {event_id}: {e}", exc_info=True)
        audit_logger.log_error('calendar_sync_event', 'events', str(e), entity_id=event_id)
        return jsonify({'success': False, 'message': str(e)}), 500

@calendar_bp.route('/api/calendar/delete_all', methods=['POST'])
@login_required
@admin_required
def delete_all_calendar_events():
    """Delete all events from the calendar"""
    try:
        current_app.logger.info(f"Delete all calendar events triggered by user {session.get('username')}")
        
        # Log to audit
        audit_logger.log(
            action='calendar_delete_all',
            entity_type='calendar',
            entity_id=None,
            entity_name='delete_all',
            details="User triggered delete all events",
            status='pending'
        )
        
        count = calendar_service.delete_all_events()
        
        audit_logger.log(
            action='calendar_delete_all',
            entity_type='calendar',
            entity_id=None,
            entity_name='delete_all',
            details=f"Deleted {count} events",
            status='success'
        )
        
        return jsonify({'success': True, 'message': f'נמחקו {count} אירועים מהיומן'})

    except Exception as e:
        current_app.logger.error(f"Error deleting all calendar events: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
