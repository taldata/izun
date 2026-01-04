from flask import Blueprint, jsonify, request, current_app
import json
import os
from datetime import datetime, date
from sqlalchemy import text
from services_init import db
from auth import admin_required

migration_bp = Blueprint('migration', __name__)

@migration_bp.route('/api/admin/export_all_data/<secret_key>')
def export_all_data(secret_key):
    """Export all data from database to JSON format - for migration"""
    if secret_key != 'izun-migrate-2024-aws':
        return jsonify({'success': False, 'message': 'Invalid key'}), 403
    
    try:
        data = {}
        
        # Export all tables
        tables = [
            'users', 'hativot', 'maslulim', 'committee_types', 
            'vaadot', 'events', 'exception_dates', 'system_settings',
            'audit_logs', 'user_hativot', 'hativa_day_constraints',
            'calendar_sync_events'
        ]
        
        with sa_db.engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT * FROM {table}"))
                    rows = result.fetchall()
                    data[table] = [dict(row._mapping) for row in rows]
                except Exception as e:
                    # Table might not exist, skip it
                    data[table] = []
        
        # Convert to JSON with proper date handling
        def json_serial(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        return jsonify({
            'success': True,
            'data': data,
            'counts': {table: len(records) for table, records in data.items()}
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'message': str(e), 'traceback': traceback.format_exc()}), 500

@migration_bp.route('/api/migrate/test/<secret_key>')
def test_migration_insert(secret_key):
    """Test migration - insert vaadot and events directly"""
    if secret_key != 'izun-migrate-2024-aws':
        return jsonify({'success': False, 'message': 'Invalid key'}), 403
    
    try:
        # Load data
        with open('db_export.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with sa_db.engine.connect() as conn:
            results = {}
            
            # Insert vaadot directly
            vaadot = data.get('vaadot', [])
            vaadot_inserted = 0
            vaadot_errors = []
            for v in vaadot:
                try:
                    conn.execute(text("""
                        INSERT INTO vaadot (vaadot_id, committee_type_id, hativa_id, vaada_date, status, exception_date_id, notes, created_at)
                        VALUES (:vaadot_id, :committee_type_id, :hativa_id, :vaada_date, :status, :exception_date_id, :notes, :created_at)
                        ON CONFLICT DO NOTHING
                    """), v)
                    vaadot_inserted += 1
                except Exception as e:
                    if len(vaadot_errors) < 5:
                        vaadot_errors.append(str(e))
            
            conn.commit()
            results['vaadot_inserted'] = vaadot_inserted
            results['vaadot_errors'] = vaadot_errors
            
            # Insert events directly
            events = data.get('events', [])
            events_inserted = 0
            events_errors = []
            for e in events:
                try:
                    conn.execute(text("""
                        INSERT INTO events (event_id, vaadot_id, maslul_id, name, event_type, expected_requests,
                                           scheduled_date, status, created_at, call_deadline_date, 
                                           intake_deadline_date, review_deadline_date, response_deadline_date,
                                           call_publication_date, actual_submissions, priority, notes)
                        VALUES (:event_id, :vaadot_id, :maslul_id, :name, :event_type, :expected_requests,
                               :scheduled_date, :status, :created_at, :call_deadline_date, 
                               :intake_deadline_date, :review_deadline_date, :response_deadline_date,
                               :call_publication_date, :actual_submissions, :priority, :notes)
                        ON CONFLICT DO NOTHING
                    """), e)
                    events_inserted += 1
                except Exception as ex:
                    if len(events_errors) < 5:
                        events_errors.append(str(ex))
            
            conn.commit()
            results['events_inserted'] = events_inserted
            results['events_errors'] = events_errors
            
            # Reset sequences
            for table, pk in [('vaadot', 'vaadot_id'), ('events', 'event_id')]:
                try:
                    conn.execute(text(f"""
                        SELECT setval(pg_get_serial_sequence('{table}', '{pk}'), 
                                      COALESCE((SELECT MAX({pk}) FROM {table}), 1))
                    """))
                except:
                    pass
            
            conn.commit()
            
            # Final counts
            results['vaadot_count'] = conn.execute(text("SELECT COUNT(*) FROM vaadot")).scalar()
            results['events_count'] = conn.execute(text("SELECT COUNT(*) FROM events")).scalar()
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as ex:
        import traceback
        return jsonify({'success': False, 'message': str(ex), 'traceback': traceback.format_exc()}), 500

@migration_bp.route('/api/migrate/run/<secret_key>', methods=['POST'])
def run_migration(secret_key):
    """Run migration with secret key (one-time use)"""
    # Simple secret key for one-time migration
    MIGRATION_SECRET = 'izun-migrate-2024-aws'
    
    if secret_key != MIGRATION_SECRET:
        return jsonify({'success': False, 'message': 'Invalid secret key'}), 403
    
    try:
        # Check if force clear is requested
        force_clear = request.args.get('clear', 'false').lower() == 'true'
        
        # Look for export file
        export_files = ['db_export.json', 'db_export_from_render.json']
        data = None
        used_file = None
        
        for export_file in export_files:
            if os.path.exists(export_file):
                try:
                    with open(export_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and len(data) > 0:
                        used_file = export_file
                        break
                except:
                    continue
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'לא נמצא קובץ ייצוא תקין (db_export.json)'
            }), 404
        
        current_app.logger.info(f"Running migration from {used_file}, force_clear={force_clear}")
        
        from services_init import db
        
        with sa_db.engine.connect() as conn:
            # Clear tables in reverse order if requested
            if force_clear:
                clear_order = [
                    'calendar_sync_events', 'audit_logs', 'events', 'vaadot',
                    'hativa_day_constraints', 'user_hativot', 'exception_dates',
                    'committee_types', 'maslulim', 'system_settings', 'hativot', 'users'
                ]
                for table in clear_order:
                    try:
                        conn.execute(text(f"DELETE FROM {table}"))
                        current_app.logger.info(f"Cleared table {table}")
                    except Exception as e:
                        current_app.logger.warning(f"Could not clear {table}: {e}")
                conn.commit()
        
        # Import order to respect foreign key relationships
        import_order = [
            'users', 'hativot', 'system_settings', 'maslulim', 
            'committee_types', 'exception_dates', 'user_hativot',
            'hativa_day_constraints', 'vaadot', 'events', 'audit_logs',
            'calendar_sync_events'
        ]
        
        for table in data.keys():
            if table not in import_order:
                import_order.append(table)
        
        imported_counts = {}
        
        with sa_db.engine.connect() as conn:
            for table in import_order:
                if table not in data:
                    continue
                
                records = data[table]
                if not records:
                    continue
                
                columns = list(records[0].keys())
                # Use named parameters for SQLAlchemy
                placeholders = ', '.join([f':{col}' for col in columns])
                column_names = ', '.join(columns)
                
                insert_query = f"""
                    INSERT INTO {table} ({column_names}) 
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """
                
                success_count = 0
                error_count = 0
                last_error = None
                for record in records:
                    try:
                        conn.execute(text(insert_query), record)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        last_error = str(e)
                        if error_count <= 3:
                            current_app.logger.warning(f"Error importing to {table}: {e}")
                
                imported_counts[table] = success_count
                if error_count > 0:
                    current_app.logger.info(f"Imported {success_count}/{len(records)} to {table} ({error_count} errors). Last: {last_error}")
                else:
                    current_app.logger.info(f"Imported {success_count} records to {table}")
        
            conn.commit()
            
            # Reset sequences for PostgreSQL
            sequence_tables = [
                ('hativot', 'hativa_id'), ('maslulim', 'maslul_id'),
                ('committee_types', 'committee_type_id'), ('vaadot', 'vaadot_id'),
                ('events', 'event_id'), ('users', 'user_id'),
                ('exception_dates', 'date_id'), ('system_settings', 'setting_id'),
            ]
            
            for table, pk_column in sequence_tables:
                try:
                    conn.execute(text(f"""
                        SELECT setval(pg_get_serial_sequence('{table}', '{pk_column}'), 
                                      COALESCE((SELECT MAX({pk_column}) FROM {table}), 1))
                    """))
                except:
                    pass
            conn.commit()
        
        total = sum(imported_counts.values())
        current_app.logger.info(f"Migration complete: {imported_counts}")
        
        # Get final counts
        final_stats = {
            'hativot': len(db.get_hativot()),
            'maslulim': len(db.get_maslulim()),
            'vaadot': len(db.get_vaadot()),
            'events': len(db.get_all_events()),
        }
        
        return jsonify({
            'success': True,
            'message': f'יובאו {total} רשומות בהצלחה',
            'imported': imported_counts,
            'source_file': used_file,
            'cleared': force_clear,
            'final_stats': final_stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error during migration: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@migration_bp.route('/api/admin/import_data', methods=['POST'])
@admin_required
def import_data_from_json():
    """Import data from db_export.json file (Admin only)"""
    try:
        import json
        import os
        
        # Look for export file
        export_files = ['db_export.json', 'db_export_from_render.json']
        data = None
        used_file = None
        
        for export_file in export_files:
            if os.path.exists(export_file):
                try:
                    with open(export_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and len(data) > 0:
                        used_file = export_file
                        break
                except:
                    continue
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'לא נמצא קובץ ייצוא תקין (db_export.json)'
            }), 404
        
        current_app.logger.info(f"Importing data from {used_file}")
        
        # Check current data counts
        current_hativot = len(db.get_hativot())
        current_events = len(db.get_all_events())
        
        if current_hativot > 0 and current_events > 5:
            return jsonify({
                'success': False,
                'message': f'מסד הנתונים כבר מכיל נתונים (חטיבות: {current_hativot}, אירועים: {current_events}). יש לרוקן לפני ייבוא.',
                'current_data': {'hativot': current_hativot, 'events': current_events}
            }), 400
        
        # Import order to respect foreign key relationships
        import_order = [
            'users', 'hativot', 'system_settings', 'maslulim', 
            'committee_types', 'exception_dates', 'user_hativot',
            'hativa_day_constraints', 'vaadot', 'events', 'audit_logs',
            'calendar_sync_events'
        ]
        
        # Add any tables not in the import order
        for table in data.keys():
            if table not in import_order:
                import_order.append(table)
        
        imported_counts = {}
        
        with sa_db.engine.connect() as conn:
            for table in import_order:
                if table not in data:
                    continue
                
                records = data[table]
                if not records:
                    continue
                
                columns = list(records[0].keys())
                # Use named parameters for safer execution with SQLAlchemy
                placeholders = ', '.join([f':{col}' for col in columns])
                column_names = ', '.join(columns)
                
                insert_query = f"""
                    INSERT INTO {table} ({column_names}) 
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """
                
                success_count = 0
                for record in records:
                    try:
                        conn.execute(text(insert_query), record)
                        success_count += 1
                    except Exception as e:
                        current_app.logger.warning(f"Error importing to {table}: {e}")
                
                imported_counts[table] = success_count
            
            conn.commit()
        
        # Reset sequences for PostgreSQL
        sequence_tables = [
            ('hativot', 'hativa_id'), ('maslulim', 'maslul_id'),
            ('committee_types', 'committee_type_id'), ('vaadot', 'vaadot_id'),
            ('events', 'event_id'), ('users', 'user_id'),
            ('exception_dates', 'date_id'), ('system_settings', 'setting_id'),
            ('audit_logs', 'log_id'), ('user_hativot', 'user_hativa_id'),
            ('hativa_day_constraints', 'constraint_id'),
            ('calendar_sync_events', 'sync_id'),
        ]
        
        with sa_db.engine.connect() as conn:
            for table, pk_column in sequence_tables:
                try:
                    conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_column}'), COALESCE((SELECT MAX({pk_column}) FROM {table}), 1))"))
                except:
                    pass
            conn.commit()
        
        total = sum(imported_counts.values())
        
        current_app.logger.info(f"Import complete: {imported_counts}")
        
        return jsonify({
            'success': True,
            'message': f'יובאו {total} רשומות בהצלחה',
            'imported': imported_counts,
            'source_file': used_file
        })
        
    except Exception as e:
        current_app.logger.error(f"Error importing data: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@migration_bp.route('/api/migrate/status')
def migration_status():
    """Check database status (no auth required, read-only)"""
    import os
    try:
        stats = {
            'hativot': len(db.get_hativot()),
            'maslulim': len(db.get_maslulim()),
            'vaadot': len(db.get_vaadot()),
            'events': len(db.get_all_events()),
        }
        
        # Check for export files
        export_files = {}
        for f in ['db_export.json', 'db_export_from_render.json']:
            if os.path.exists(f):
                export_files[f] = os.path.getsize(f)
        
        return jsonify({
            'success': True, 
            'stats': stats, 
            'needs_migration': stats['hativot'] == 0,
            'export_files': export_files,
            'cwd': os.getcwd()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@migration_bp.route('/api/migrate/fix-schema/<secret_key>', methods=['POST'])
def fix_schema(secret_key):
    """Add missing columns to tables"""
    if secret_key != 'izun-migrate-2024-aws':
        return jsonify({'success': False, 'message': 'Invalid key'}), 403
    
    try:
        with sa_db.engine.connect() as conn:
            fixes = []
            
            # Helper to execute and commit
            def exec_fix(sql_str, success_msg, error_prefix):
                try:
                    conn.execute(text(sql_str))
                    conn.commit()
                    fixes.append(success_msg)
                except Exception as e:
                    conn.rollback()
                    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                        fixes.append(f"{success_msg.split(' ')[1]} column already exists")
                    else:
                        fixes.append(f"{error_prefix}: {e}")

            exec_fix("ALTER TABLE vaadot ADD COLUMN status TEXT DEFAULT 'planned'", "Added status column to vaadot", "Error adding status to vaadot")
            exec_fix("ALTER TABLE events ADD COLUMN priority INTEGER DEFAULT 1", "Added priority column to events", "Error adding priority to events")
            exec_fix("ALTER TABLE events ADD COLUMN notes TEXT DEFAULT ''", "Added notes column to events", "Error adding notes to events")
            exec_fix("ALTER TABLE events ADD COLUMN status TEXT DEFAULT 'planned'", "Added status column to events", "Error adding status to events")
            exec_fix("ALTER TABLE events ADD COLUMN scheduled_date DATE", "Added scheduled_date column to events", "Error adding scheduled_date to events")
            exec_fix("ALTER TABLE events ADD COLUMN call_publication_date DATE", "Added call_publication_date column to events", "Error adding call_publication_date to events")
            exec_fix("ALTER TABLE events ADD COLUMN actual_submissions INTEGER DEFAULT 0", "Added actual_submissions column to events", "Error adding actual_submissions to events")
            exec_fix("ALTER TABLE events ADD COLUMN expected_requests INTEGER DEFAULT 0", "Added expected_requests column to events", "Error adding expected_requests to events")
        
        return jsonify({'success': True, 'fixes': fixes})
        
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'message': str(e), 'traceback': traceback.format_exc()}), 500
