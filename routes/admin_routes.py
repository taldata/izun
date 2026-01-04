from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from services_init import db, audit_logger, auth_manager, constraints_service
from auth import login_required, admin_required, editing_permission_required
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/hativot')
@login_required
def hativot():
    """Manage divisions"""
    hativot_list = db.get_hativot()
    current_user = auth_manager.get_current_user()
    return render_template('hativot.html', hativot=hativot_list, current_user=current_user)

@admin_bp.route('/hativot/add', methods=['POST'])
@editing_permission_required
def add_hativa():
    """Add new division"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#007bff')
    
    if not name:
        flash('שם החטיבה הוא שדה חובה', 'error')
        return redirect(url_for('admin.hativot'))
    
    try:
        hativa_id = db.add_hativa(name, description, color)
        audit_logger.log_hativa_created(hativa_id, name)
        flash(f'חטיבה "{name}" נוספה בהצלחה', 'success')
    except Exception as e:
        audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_HATIVA, str(e), entity_name=name)
        flash(f'שגיאה בהוספת החטיבה: {str(e)}', 'error')
    
    return redirect(url_for('admin.hativot'))

@admin_bp.route('/hativot/update', methods=['POST'])
@editing_permission_required
def update_hativa():
    """Update existing division"""
    hativa_id = request.form.get('hativa_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#007bff')
    
    if not all([hativa_id, name]):
        flash('מזהה החטיבה ושם החטיבה הם שדות חובה', 'error')
        return redirect(url_for('admin.hativot'))
    
    try:
        success = db.update_hativa(int(hativa_id), name, description, color)
        if success:
            audit_logger.log_hativa_updated(int(hativa_id), name)
            flash(f'חטיבה "{name}" עודכנה בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון החטיבה', 'error')
    except Exception as e:
        audit_logger.log_error(audit_logger.ACTION_UPDATE, audit_logger.ENTITY_HATIVA, str(e), int(hativa_id), name)
        flash(f'שגיאה בעדכון החטיבה: {str(e)}', 'error')
    
    return redirect(url_for('admin.hativot'))

@admin_bp.route('/hativot/set_day_constraints', methods=['POST'])
@editing_permission_required
def set_hativa_day_constraints():
    """Set allowed days for a division"""
    hativa_id = request.form.get('hativa_id')
    allowed_days = request.form.getlist('allowed_days')
    
    if not hativa_id:
        flash('שגיאה: מזהה חטיבה חסר', 'error')
        return redirect(url_for('admin.hativot'))
    
    try:
        # Convert string list to integers
        allowed_days_int = [int(day) for day in allowed_days] if allowed_days else []
        
        db.set_hativa_allowed_days(int(hativa_id), allowed_days_int)
        
        # Log the action
        hativa = next((h for h in db.get_hativot() if h['hativa_id'] == int(hativa_id)), None)
        if hativa:
            day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
            selected_days = [day_names[int(d)] for d in allowed_days] if allowed_days else []
            changes = f'עודכנו אילוצי ימים: {", ".join(selected_days) if selected_days else "ללא הגבלה (כל הימים)"}'
            audit_logger.log_hativa_updated(int(hativa_id), hativa['name'], changes)
        
        flash('אילוצי הימים עודכנו בהצלחה', 'success')
    except ValueError as e:
        flash(f'שגיאה בעדכון אילוצי הימים: {str(e)}', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון אילוצי הימים: {str(e)}', 'error')
        current_app.logger.error(f"Error setting day constraints: {e}", exc_info=True)
    
    return redirect(url_for('admin.hativot'))

@admin_bp.route('/hativot/update_color', methods=['POST'])
def update_hativa_color():
    """Update division color"""
    hativa_id = request.form.get('hativa_id')
    color = request.form.get('color')

    if not all([hativa_id, color]):
        flash('חטיבה וצבע הם שדות חובה', 'error')
        return redirect(url_for('main.index'))

    try:
        success = db.update_hativa_color(int(hativa_id), color)
        if success:
            # Log the color update
            hativa = next((h for h in db.get_hativot() if h['hativa_id'] == int(hativa_id)), None)
            if hativa:
                audit_logger.log_hativa_updated(int(hativa_id), hativa['name'], f'עדכון צבע ל-{color}')
            flash('צבע החטיבה עודכן בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון צבע החטיבה', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון צבע החטיבה: {str(e)}', 'error')

    return redirect(url_for('main.index'))

@admin_bp.route('/maslulim')
def maslulim():
    """Manage routes with enhanced functionality"""
    try:
        # Get data with error handling
        maslulim_list = db.get_maslulim()
        hativot_list = db.get_hativot()
        
        # Group maslulim by hativa for better organization and display control
        maslulim_by_hativa = []
        for hativa in hativot_list:
            grouped_maslulim = [m for m in maslulim_list if m['hativa_id'] == hativa['hativa_id']]
            maslulim_by_hativa.append({
                'hativa_id': hativa['hativa_id'],
                'hativa_name': hativa['name'],
                'color': hativa.get('color'),
                'maslulim': grouped_maslulim
            })
        
        # Calculate statistics with colors
        maslulim_per_hativa_with_colors = {}
        for hativa in hativot_list:
            count = len([m for m in maslulim_list if m['hativa_id'] == hativa['hativa_id']])
            maslulim_per_hativa_with_colors[hativa['name']] = {
                'count': count,
                'color': hativa['color']
            }
        
        stats = {
            'total_maslulim': len(maslulim_list),
            'total_hativot': len(hativot_list),
            'maslulim_per_hativa': {hativa['name']: len([m for m in maslulim_list if m['hativa_id'] == hativa['hativa_id']]) for hativa in hativot_list},
            'maslulim_per_hativa_with_colors': maslulim_per_hativa_with_colors
        }
        
        # Get current user info
        current_user = auth_manager.get_current_user()
        
        return render_template('maslulim.html', 
                             maslulim=maslulim_list, 
                             hativot=hativot_list,
                             maslulim_by_hativa=maslulim_by_hativa,
                             stats=stats,
                             current_user=current_user)
    except Exception as e:
        flash(f'שגיאה בטעינת נתוני המסלולים: {str(e)}', 'error')
        current_user = auth_manager.get_current_user()
        return render_template('maslulim.html', maslulim=[], hativot=[], maslulim_by_hativa={}, stats={}, current_user=current_user)

@admin_bp.route('/maslulim/add', methods=['POST'])
def add_maslul():
    """Add new route with enhanced validation"""
    try:
        hativa_id = request.form.get('hativa_id')
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        sla_days = request.form.get('sla_days', 45)
        stage_a_days = request.form.get('stage_a_days', 10)
        stage_b_days = request.form.get('stage_b_days', 15)
        stage_c_days = request.form.get('stage_c_days', 10)
        stage_d_days = request.form.get('stage_d_days', 10)
        
        # Enhanced validation
        if not hativa_id:
            flash('יש לבחור חטיבה', 'error')
            return redirect(url_for('admin.maslulim'))
            
        if not name:
            flash('שם המסלול הוא שדה חובה', 'error')
            return redirect(url_for('admin.maslulim'))
            
        if len(name) < 2:
            flash('שם המסלול חייב להכיל לפחות 2 תווים', 'error')
            return redirect(url_for('admin.maslulim'))
            
        # Check if hativa exists
        hativot = db.get_hativot()
        if not any(h['hativa_id'] == int(hativa_id) for h in hativot):
            flash('החטיבה שנבחרה לא קיימת במערכת', 'error')
            return redirect(url_for('admin.maslulim'))
            
        # Check for duplicate names within the same hativa
        existing_maslulim = db.get_maslulim(int(hativa_id))
        if any(m['name'].lower() == name.lower() for m in existing_maslulim):
            flash(f'מסלול בשם "{name}" כבר קיים בחטיבה זו', 'error')
            return redirect(url_for('admin.maslulim'))
        
        # Validate SLA and stage days
        try:
            sla_days = int(sla_days)
            stage_a_days = int(stage_a_days)
            stage_b_days = int(stage_b_days)
            stage_c_days = int(stage_c_days)
            stage_d_days = int(stage_d_days)
            
            if sla_days < 1 or sla_days > 365:
                flash('SLA חייב להיות בין 1 ל-365 ימים', 'error')
                return redirect(url_for('admin.maslulim'))
                
            # Validate stage days
            for stage_name, days in [('שלב א', stage_a_days), ('שלב ב', stage_b_days), 
                                   ('שלב ג', stage_c_days), ('שלב ד', stage_d_days)]:
                if days < 0 or days > 365:
                    flash(f'{stage_name} חייב להיות בין 0 ל-365 ימים', 'error')
                    return redirect(url_for('admin.maslulim'))
            
            # Check if sum of stages equals SLA
            total_stages = stage_a_days + stage_b_days + stage_c_days + stage_d_days
            if total_stages != sla_days:
                flash(f'סכום השלבים ({total_stages}) חייב להיות שווה ל-SLA ({sla_days})', 'error')
                return redirect(url_for('admin.maslulim'))
                
        except (ValueError, TypeError):
            flash('כל השדות חייבים להיות מספרים תקינים', 'error')
            return redirect(url_for('admin.maslulim'))
        
        # Add the maslul
        maslul_id = db.add_maslul(int(hativa_id), name, description, sla_days, 
                                 stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        hativa_name = next(h['name'] for h in hativot if h['hativa_id'] == int(hativa_id))
        audit_logger.log_maslul_created(maslul_id, name, hativa_name)
        flash(f'מסלול "{name}" נוסף בהצלחה לחטיבת {hativa_name}', 'success')
        
    except ValueError as e:
        audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_MASLUL, str(e), entity_name=name)
        flash('נתונים לא תקינים', 'error')
    except Exception as e:
        audit_logger.log_error(audit_logger.ACTION_CREATE, audit_logger.ENTITY_MASLUL, str(e), entity_name=name)
        flash(f'שגיאה בהוספת המסלול: {str(e)}', 'error')
    
    return redirect(url_for('admin.maslulim'))

@admin_bp.route('/maslulim/edit/<int:maslul_id>', methods=['POST'])
def edit_maslul(maslul_id):
    """Edit existing route"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        sla_days = request.form.get('sla_days', 45)
        stage_a_days = request.form.get('stage_a_days', 10)
        stage_b_days = request.form.get('stage_b_days', 15)
        stage_c_days = request.form.get('stage_c_days', 10)
        stage_d_days = request.form.get('stage_d_days', 10)
        is_active = request.form.get('is_active') == 'on'
        
        if not name:
            flash('שם המסלול הוא שדה חובה', 'error')
            return redirect(url_for('admin.maslulim'))
            
        if len(name) < 2:
            flash('שם המסלול חייב להכיל לפחות 2 תווים', 'error')
            return redirect(url_for('admin.maslulim'))
        
        # Validate SLA and stage days
        try:
            sla_days = int(sla_days)
            stage_a_days = int(stage_a_days)
            stage_b_days = int(stage_b_days)
            stage_c_days = int(stage_c_days)
            stage_d_days = int(stage_d_days)
            
            if sla_days < 1 or sla_days > 365:
                flash('SLA חייב להיות בין 1 ל-365 ימים', 'error')
                return redirect(url_for('admin.maslulim'))
                
            # Validate stage days
            for stage_name, days in [('שלב א', stage_a_days), ('שלב ב', stage_b_days), 
                                   ('שלב ג', stage_c_days), ('שלב ד', stage_d_days)]:
                if days < 0 or days > 365:
                    flash(f'{stage_name} חייב להיות בין 0 ל-365 ימים', 'error')
                    return redirect(url_for('admin.maslulim'))
            
            # Check if sum of stages equals SLA
            total_stages = stage_a_days + stage_b_days + stage_c_days + stage_d_days
            if total_stages != sla_days:
                flash(f'סכום השלבים ({total_stages}) חייב להיות שווה ל-SLA ({sla_days})', 'error')
                return redirect(url_for('admin.maslulim'))
                
        except (ValueError, TypeError):
            flash('כל השדות חייבים להיות מספרים תקינים', 'error')
            return redirect(url_for('admin.maslulim'))
        
        # Update the maslul
        success = db.update_maslul(maslul_id, name, description, sla_days,
                                 stage_a_days, stage_b_days, stage_c_days, stage_d_days, is_active)
        if success:
            # Recalculate deadlines for all events using this maslul
            updated_events = db.recalculate_event_deadlines_for_maslul(maslul_id)
            status_text = 'פעיל' if is_active else 'לא פעיל'

            # Log the update
            changes = f'SLA: {sla_days} ימים, שלבים: A={stage_a_days}, B={stage_b_days}, C={stage_c_days}, D={stage_d_days}, סטטוס: {status_text}'
            audit_logger.log_maslul_updated(maslul_id, name, changes)

            if updated_events > 0:
                flash(f'מסלול "{name}" עודכן בהצלחה (סטטוס: {status_text}). עודכנו תאריכי יעד ב-{updated_events} אירועים.', 'success')
            else:
                flash(f'מסלול "{name}" עודכן בהצלחה (סטטוס: {status_text})', 'success')
        else:
            flash('המסלול לא נמצא במערכת', 'error')

    except Exception as e:
        flash(f'שגיאה בעדכון המסלול: {str(e)}', 'error')
    
    return redirect(url_for('admin.maslulim'))

@admin_bp.route('/maslulim/delete/<int:maslul_id>', methods=['POST'])
def delete_maslul(maslul_id):
    """Delete route with safety checks"""
    try:
        # Get maslul name before deletion
        maslulim = db.get_maslulim()
        maslul = next((m for m in maslulim if m['maslul_id'] == maslul_id), None)
        
        if not maslul:
            flash('המסלול לא נמצא במערכת', 'error')
            return redirect(url_for('admin.maslulim'))
        
        # Check if maslul is used in any events (including deleted ones) and get examples
        events = db.get_all_events(include_deleted=True)
        maslul_events = [e for e in events if e.get('maslul_id') == maslul_id]
        
        if maslul_events:
            # Create examples list (up to 5 events)
            examples_list = []
            for e in maslul_events[:5]:
                event_name = e.get('name', 'ללא שם')
                event_date = e.get('vaada_date')
                if event_date:
                    formatted_date = str(event_date) # Simplified date formatting
                    examples_list.append(f'"{event_name}" (תאריך: {formatted_date})')
                else:
                    examples_list.append(f'"{event_name}" (ללא תאריך)')
            
            examples_text = ', '.join(examples_list)
            if len(maslul_events) > 5:
                examples_text += f' ועוד {len(maslul_events) - 5} אירועים'
            
            flash(f'לא ניתן למחוק מסלול המשויך ל-{len(maslul_events)} אירועים. יש למחוק תחילה את האירועים הקשורים. דוגמאות לאירועים: {examples_text}.', 'error')
            return redirect(url_for('admin.maslulim'))
        
        # Delete the maslul
        success = db.delete_maslul(maslul_id)
        if success:
            # Log the deletion
            audit_logger.log_maslul_deleted(maslul_id, maslul['name'])
            flash(f'מסלול "{maslul["name"]}" נמחק בהצלחה', 'success')
        else:
            flash('שגיאה במחיקת המסלול', 'error')
            
    except ValueError as ve:
        # This is our custom error from delete_maslul
        flash(str(ve), 'error')
    except Exception as e:
        flash(f'שגיאה במחיקת המסלול: {str(e)}', 'error')
    
    return redirect(url_for('admin.maslulim'))

@admin_bp.route('/exception_dates', methods=['GET', 'POST'])
def exception_dates():
    """Manage exception dates"""
    if request.method == 'POST':
        # Handle POST - add new exception date
        date_str = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()
        date_type = request.form.get('type', 'holiday').strip()
        
        if not date_str:
            flash('תאריך הוא שדה חובה', 'error')
            return redirect(url_for('admin.exception_dates'))
        
        try:
            exception_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            db.add_exception_date(exception_date, description, date_type)
            
            # Recalculate all event deadlines to account for the new exception date
            updated_count = db.recalculate_all_event_deadlines()
            
            # Get the date_id for logging (query just added record)
            exception_dates_list = db.get_exception_dates(include_past=True)
            added_date = next((ed for ed in exception_dates_list if ed['exception_date'] == date_str), None)
            date_id = added_date['date_id'] if added_date else None
            
            audit_logger.log_exception_date_added(date_id, date_str, description)
            flash(f'תאריך חריג {date_str} נוסף בהצלחה. עודכנו {updated_count} אירועים.', 'success')
        except ValueError:
            flash('פורמט תאריך לא תקין', 'error')
        except Exception as e:
            flash(f'שגיאה בהוספת תאריך: {str(e)}', 'error')
        
        return redirect(url_for('admin.exception_dates'))
    
    # Handle GET - display exception dates
    include_past = request.args.get('include_past', 'true') == 'true'
    dates_list = db.get_exception_dates(include_past=include_past)
    current_user = auth_manager.get_current_user()
    return render_template('exception_dates.html', dates=dates_list, current_user=current_user, include_past=include_past)

@admin_bp.route('/exception_dates/edit/<int:date_id>', methods=['POST'])
@login_required
def edit_exception_date(date_id):
    """Edit exception date"""
    try:
        # Get current user
        user = auth_manager.get_current_user()
        if not user:
            flash('נדרשת התחברות', 'error')
            return redirect(url_for('auth.login'))
        
        # Check permissions: Only admins can edit
        if user['role'] != 'admin':
            flash('רק מנהלי מערכת יכולים לערוך תאריכי חריגים', 'error')
            return redirect(url_for('admin.exception_dates'))
        
        date_str = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()
        date_type = request.form.get('type', 'holiday').strip()
        
        if not date_str:
            flash('תאריך הוא שדה חובה', 'error')
            return redirect(url_for('admin.exception_dates'))
        
        exception_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        success = db.update_exception_date(date_id, exception_date, description, date_type)
        
        if success:
            # Recalculate all event deadlines to account for the updated exception date
            updated_count = db.recalculate_all_event_deadlines()
            
            audit_logger.log_success(
                audit_logger.ACTION_UPDATE,
                'exception_date',
                details=f'עדכון תאריך חריג: {date_str} - {description}'
            )
            flash(f'תאריך חריג {date_str} עודכן בהצלחה. עודכנו {updated_count} אירועים.', 'success')
        else:
            flash('שגיאה בעדכון תאריך חריג', 'error')
    except ValueError:
        flash('פורמט תאריך לא תקין', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון תאריך: {str(e)}', 'error')
    
    return redirect(url_for('admin.exception_dates'))

@admin_bp.route('/exception_dates/delete/<int:date_id>', methods=['POST'])
@login_required
def delete_exception_date(date_id):
    """Delete exception date"""
    try:
        # Get current user
        user = auth_manager.get_current_user()
        if not user:
            flash('נדרשת התחברות', 'error')
            return redirect(url_for('auth.login'))
        
        # Check permissions: Only admins can delete
        if user['role'] != 'admin':
            flash('רק מנהלי מערכת יכולים למחוק תאריכי חריגים', 'error')
            return redirect(url_for('admin.exception_dates'))
        
        # Get date info before deletion for logging
        exception_date_obj = db.get_exception_date_by_id(date_id)
        
        if not exception_date_obj:
            flash('תאריך חריג לא נמצא במערכת', 'error')
            return redirect(url_for('admin.exception_dates'))
        
        success = db.delete_exception_date(date_id)
        
        if success:
            # Recalculate all event deadlines to account for the deleted exception date
            updated_count = db.recalculate_all_event_deadlines()
            
            audit_logger.log_success(
                audit_logger.ACTION_DELETE,
                'exception_date',
                details=f'מחיקת תאריך חריג: {exception_date_obj["exception_date"]} - {exception_date_obj.get("description", "")}'
            )
            flash(f'תאריך חריג {exception_date_obj["exception_date"]} נמחק בהצלחה. עודכנו {updated_count} אירועים.', 'success')
        else:
            flash('לא ניתן למחוק תאריך חריג שמשויכות אליו ועדות', 'error')
    except Exception as e:
        flash(f'שגיאה במחיקת תאריך: {str(e)}', 'error')
    
    return redirect(url_for('admin.exception_dates'))

@admin_bp.route('/constraints')
@admin_required
def constraints():
    """Constraint management dashboard"""
    try:
        settings = constraints_service.get_constraints_overview()
        current_user = auth_manager.get_current_user()
        return render_template('constraints.html', settings=settings, errors={}, current_user=current_user)
    except Exception as e:
        flash(f'שגיאה בטעינת נתוני האילוצים: {e}', 'error')
        return redirect(url_for('main.index'))


@admin_bp.route('/constraints/update', methods=['POST'])
@admin_required
def update_constraints():
    """Update system constraint settings"""
    try:
        payload = constraints_service.parse_request(request.form)
        result = constraints_service.update_constraints(payload, session.get('user_id'))
        if result.success:
            flash(result.message, 'success')
            return redirect(url_for('admin.constraints'))
        flash(result.message, 'error')
        settings = constraints_service.get_constraints_overview()
        settings = constraints_service.apply_form_values(settings, payload)
        current_user = auth_manager.get_current_user()
        status_code = 400 if result.errors else 200
        return render_template('constraints.html', settings=settings, errors=result.errors or {}, current_user=current_user), status_code
    except Exception as e:
        flash(f'שגיאה בעדכון האילוצים: {e}', 'error')
        return redirect(url_for('admin.constraints'))
