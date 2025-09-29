#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date, timedelta
import json
from database import DatabaseManager
from auto_scheduler import AutoMeetingScheduler
from services.auto_schedule_service import AutoScheduleService
from services.constraints_service import ConstraintsService
from services.committee_types_service import CommitteeTypesService, CommitteeTypeRequest
from auth import AuthManager, login_required, admin_required, editing_permission_required

app = Flask(__name__)
app.secret_key = 'committee_management_secret_key_2025'

# Initialize system components
db = DatabaseManager()
auto_scheduler = AutoMeetingScheduler(db)
auto_schedule_service = AutoScheduleService(db)
constraints_service = ConstraintsService(db)
committee_types_service = CommitteeTypesService(db)
auth_manager = AuthManager(db)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        success, message = auth_manager.login_user(username, password)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('index'))
        else:
            flash(message, 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    auth_manager.logout_user()
    flash('התנתקת מהמערכת בהצלחה', 'success')
    return redirect(url_for('login'))


# Admin API endpoints
@app.route('/api/toggle_editing_period', methods=['POST'])
@admin_required
def toggle_editing_period():
    """Toggle editing period for regular users"""
    try:
        current_status = db.get_system_setting('editing_period_active')
        new_status = '0' if current_status == '1' else '1'
        
        user_id = session['user_id']
        db.update_system_setting('editing_period_active', new_status, user_id)
        
        status_text = "פעילה" if new_status == '1' else "סגורה"
        return jsonify({
            'success': True,
            'message': f'תקופת העריכה הכללית עכשיו {status_text}',
            'editing_active': new_status == '1'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/editing_status')
@login_required
def get_editing_status():
    """Get current editing status for user"""
    try:
        user = auth_manager.get_current_user()
        can_edit, reason = auth_manager.can_edit()
        editing_period_active = db.get_system_setting('editing_period_active') == '1'
        
        return jsonify({
            'can_edit': can_edit,
            'reason': reason,
            'editing_period_active': editing_period_active,
            'user_role': user['role']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Soft Delete API endpoints
@app.route('/api/toggle_committee_type/<int:committee_type_id>', methods=['POST'])
@editing_permission_required
def toggle_committee_type(committee_type_id):
    """Toggle committee type active status"""
    try:
        # Check current status
        committee_types = db.get_committee_types()
        committee_type = next((ct for ct in committee_types if ct['committee_type_id'] == committee_type_id), None)
        
        if not committee_type:
            return jsonify({'success': False, 'error': 'סוג ועדה לא נמצא'}), 404
        
        # Toggle status
        if committee_type.get('is_active', 1):
            success = db.deactivate_committee_type(committee_type_id)
            action = 'הושבת'
        else:
            success = db.activate_committee_type(committee_type_id)
            action = 'הופעל'
        
        if success:
            return jsonify({
                'success': True,
                'message': f'סוג הועדה "{committee_type["name"]}" {action} בהצלחה',
                'is_active': not committee_type.get('is_active', 1)
            })
        else:
            return jsonify({'success': False, 'error': 'שגיאה בעדכון סטטוס'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle_hativa/<int:hativa_id>', methods=['POST'])
@admin_required
def toggle_hativa(hativa_id):
    """Toggle division active status (admin only)"""
    try:
        hativot = db.get_hativot()
        hativa = next((h for h in hativot if h['hativa_id'] == hativa_id), None)
        
        if not hativa:
            return jsonify({'success': False, 'error': 'חטיבה לא נמצאה'}), 404
        
        # Toggle status
        if hativa.get('is_active', 1):
            success = db.deactivate_hativa(hativa_id)
            action = 'הושבתה'
        else:
            success = db.activate_hativa(hativa_id)
            action = 'הופעלה'
        
        if success:
            return jsonify({
                'success': True,
                'message': f'החטיבה "{hativa["name"]}" {action} בהצלחה',
                'is_active': not hativa.get('is_active', 1)
            })
        else:
            return jsonify({'success': False, 'error': 'שגיאה בעדכון סטטוס'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle_maslul/<int:maslul_id>', methods=['POST'])
@editing_permission_required
def toggle_maslul(maslul_id):
    """Toggle route active status"""
    try:
        maslulim = db.get_maslulim()
        maslul = next((m for m in maslulim if m['maslul_id'] == maslul_id), None)
        
        if not maslul:
            return jsonify({'success': False, 'error': 'מסלול לא נמצא'}), 404
        
        # Toggle status
        if maslul.get('is_active', 1):
            success = db.deactivate_maslul(maslul_id)
            action = 'הושבת'
        else:
            success = db.activate_maslul(maslul_id)
            action = 'הופעל'
        
        if success:
            return jsonify({
                'success': True,
                'message': f'המסלול "{maslul["name"]}" {action} בהצלחה',
                'is_active': not maslul.get('is_active', 1)
            })
        else:
            return jsonify({'success': False, 'error': 'שגיאה בעדכון סטטוס'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Enhanced SLA and Business Days API
@app.route('/api/sla_info/<vaadot_id>')
@login_required
def get_sla_info(vaadot_id):
    """Get SLA information for a committee meeting"""
    try:
        # Get committee meeting details
        committees = db.get_vaadot()
        committee = next((c for c in committees if c['vaadot_id'] == int(vaadot_id)), None)
        
        if not committee:
            return jsonify({'error': 'ישיבת ועדה לא נמצאה'}), 404
        
        # Parse committee date
        committee_date = datetime.strptime(committee['vaada_date'], '%Y-%m-%d').date()
        
        # Calculate SLA dates
        sla_info = db.calculate_sla_dates(committee_date)
        
        # Format dates for display
        formatted_sla = {
            'committee_date': committee_date.strftime('%d/%m/%Y'),
            'committee_name': committee['committee_name'],
            'hativa_name': committee['hativa_name'],
            'sla_days': sla_info['sla_days'],
            'request_deadline': sla_info['request_deadline'].strftime('%d/%m/%Y'),
            'preparation_start': sla_info['preparation_start'].strftime('%d/%m/%Y'),
            'notification_date': sla_info['notification_date'].strftime('%d/%m/%Y'),
            'business_days_to_committee': sla_info['business_days_to_committee'],
            'is_overdue': sla_info['request_deadline'] < date.today(),
            'days_until_deadline': (sla_info['request_deadline'] - date.today()).days
        }
        
        return jsonify(formatted_sla)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/business_days/<int:year>/<int:month>')
@login_required
def get_business_days_info(year, month):
    """Get business days information for a specific month"""
    try:
        business_days_info = db.get_monthly_business_days(year, month)
        
        # Format dates for JSON
        formatted_info = {
            'year': business_days_info['year'],
            'month': business_days_info['month'],
            'total_days': business_days_info['total_days'],
            'business_days_count': business_days_info['business_days_count'],
            'business_days': [d.strftime('%Y-%m-%d') for d in business_days_info['business_days']],
            'first_business_day': business_days_info['first_business_day'].strftime('%d/%m/%Y') if business_days_info['first_business_day'] else None,
            'last_business_day': business_days_info['last_business_day'].strftime('%d/%m/%Y') if business_days_info['last_business_day'] else None,
            'weeks': {
                str(week): [d.strftime('%Y-%m-%d') for d in days] 
                for week, days in business_days_info['weeks'].items()
            }
        }
        
        return jsonify(formatted_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/available_dates')
@login_required
def get_available_dates():
    """Get upcoming available dates for a committee type within a division"""
    try:
        committee_type_id = request.args.get('committee_type_id', type=int)
        hativa_id = request.args.get('hativa_id', type=int)

        if not committee_type_id or not hativa_id:
            return jsonify({'success': False, 'message': 'נדרש לבחור סוג ועדה וחטיבה'}), 400

        # Validate that the committee type belongs to the given division
        committee_types = db.get_committee_types(hativa_id)
        committee_type = next((ct for ct in committee_types if ct['committee_type_id'] == committee_type_id), None)

        if not committee_type:
            return jsonify({'success': False, 'message': 'סוג הועדה אינו משויך לחטיבה שנבחרה'}), 400

        start_date_str = request.args.get('start_date')
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'פורמט תאריך התחלה אינו תקין'}), 400

        limit = request.args.get('limit', default=5, type=int)
        limit = max(1, min(limit or 5, 20))
        max_days = request.args.get('max_days', default=180, type=int)
        max_days = max(7, min(max_days or 180, 365))

        available_dates = auto_scheduler.find_available_dates(
            committee_type_id,
            hativa_id,
            start_date=start_date,
            max_results=limit,
            max_days=max_days
        )

        formatted_dates = [d.strftime('%Y-%m-%d') for d in available_dates]

        message = 'נמצאו תאריכים פנויים' if formatted_dates else 'לא נמצאו תאריכים פנויים בטווח שנבחר'

        return jsonify({
            'success': True,
            'dates': formatted_dates,
            'total': len(formatted_dates),
            'message': message,
            'committee_type': committee_type.get('name'),
            'hativa_id': hativa_id
        })

    except Exception as e:
        app.logger.error(f"Error fetching available dates: {str(e)}")
        return jsonify({'success': False, 'message': f'שגיאה בשליפת תאריכים פנויים: {str(e)}'}), 500


@app.route('/constraints')
@admin_required
def constraints():
    """Constraint management dashboard"""
    try:
        settings = constraints_service.get_constraints_overview()
        current_user = auth_manager.get_current_user()
        return render_template('constraints.html', settings=settings, errors={}, current_user=current_user)
    except Exception as e:
        flash(f'שגיאה בטעינת נתוני האילוצים: {e}', 'error')
        return redirect(url_for('index'))


@app.route('/constraints/update', methods=['POST'])
@admin_required
def update_constraints():
    """Update system constraint settings"""
    try:
        payload = constraints_service.parse_request(request.form)
        result = constraints_service.update_constraints(payload, session.get('user_id'))
        if result.success:
            flash(result.message, 'success')
            return redirect(url_for('constraints'))
        flash(result.message, 'error')
        settings = constraints_service.get_constraints_overview()
        settings = constraints_service.apply_form_values(settings, payload)
        current_user = auth_manager.get_current_user()
        status_code = 400 if result.errors else 200
        return render_template('constraints.html', settings=settings, errors=result.errors or {}, current_user=current_user), status_code
    except Exception as e:
        flash(f'שגיאה בעדכון האילוצים: {e}', 'error')
        return redirect(url_for('constraints'))

@app.route('/')
@login_required
def index():
    """Main dashboard"""
    # Get summary statistics
    hativot = db.get_hativot()
    maslulim = db.get_maslulim()
    committee_types = db.get_committee_types()
    committees = db.get_vaadot()  # This now returns meeting instances
    events = db.get_events()
    exception_dates = db.get_exception_dates()
    
    # Debug logging
    app.logger.info(f"Loaded {len(committees)} committees")
    app.logger.info(f"Loaded {len(events)} events")
    if committees:
        app.logger.info(f"First committee: {committees[0]}")
    if events:
        app.logger.info(f"First event: {events[0]}")
    
    # Get current month schedule
    today = date.today()
    monthly_schedule = []
    
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
    
    return render_template('index.html', 
                         hativot=hativot, 
                         maslulim=maslulim, 
                         committee_types=committee_types,
                         committees=committees,
                         events=events,
                         exception_dates=exception_dates,
                         stats=stats,
                         current_user=current_user)

@app.route('/hativot')
@login_required
def hativot():
    """Manage divisions"""
    hativot_list = db.get_hativot()
    current_user = auth_manager.get_current_user()
    return render_template('hativot.html', hativot=hativot_list, current_user=current_user)

@app.route('/hativot/add', methods=['POST'])
@editing_permission_required
def add_hativa():
    """Add new division"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#007bff')
    
    if not name:
        flash('שם החטיבה הוא שדה חובה', 'error')
        return redirect(url_for('hativot'))
    
    try:
        hativa_id = db.add_hativa(name, description, color)
        flash(f'חטיבה "{name}" נוספה בהצלחה', 'success')
    except Exception as e:
        flash(f'שגיאה בהוספת החטיבה: {str(e)}', 'error')
    
    return redirect(url_for('hativot'))

@app.route('/hativot/update', methods=['POST'])
@editing_permission_required
def update_hativa():
    """Update existing division"""
    hativa_id = request.form.get('hativa_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#007bff')
    
    if not all([hativa_id, name]):
        flash('מזהה החטיבה ושם החטיבה הם שדות חובה', 'error')
        return redirect(url_for('hativot'))
    
    try:
        success = db.update_hativa(int(hativa_id), name, description, color)
        if success:
            flash(f'חטיבה "{name}" עודכנה בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון החטיבה', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון החטיבה: {str(e)}', 'error')
    
    return redirect(url_for('hativot'))

@app.route('/maslulim')
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
        
        return render_template('maslulim.html', 
                             maslulim=maslulim_list, 
                             hativot=hativot_list,
                             maslulim_by_hativa=maslulim_by_hativa,
                             stats=stats)
    except Exception as e:
        flash(f'שגיאה בטעינת נתוני המסלולים: {str(e)}', 'error')
        return render_template('maslulim.html', maslulim=[], hativot=[], maslulim_by_hativa={}, stats={})

@app.route('/maslulim/add', methods=['POST'])
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
            return redirect(url_for('maslulim'))
            
        if not name:
            flash('שם המסלול הוא שדה חובה', 'error')
            return redirect(url_for('maslulim'))
            
        if len(name) < 2:
            flash('שם המסלול חייב להכיל לפחות 2 תווים', 'error')
            return redirect(url_for('maslulim'))
            
        # Check if hativa exists
        hativot = db.get_hativot()
        if not any(h['hativa_id'] == int(hativa_id) for h in hativot):
            flash('החטיבה שנבחרה לא קיימת במערכת', 'error')
            return redirect(url_for('maslulim'))
            
        # Check for duplicate names within the same hativa
        existing_maslulim = db.get_maslulim(int(hativa_id))
        if any(m['name'].lower() == name.lower() for m in existing_maslulim):
            flash(f'מסלול בשם "{name}" כבר קיים בחטיבה זו', 'error')
            return redirect(url_for('maslulim'))
        
        # Validate SLA and stage days
        try:
            sla_days = int(sla_days)
            stage_a_days = int(stage_a_days)
            stage_b_days = int(stage_b_days)
            stage_c_days = int(stage_c_days)
            stage_d_days = int(stage_d_days)
            
            if sla_days < 1 or sla_days > 365:
                flash('SLA חייב להיות בין 1 ל-365 ימים', 'error')
                return redirect(url_for('maslulim'))
                
            # Validate stage days
            for stage_name, days in [('שלב א', stage_a_days), ('שלב ב', stage_b_days), 
                                   ('שלב ג', stage_c_days), ('שלב ד', stage_d_days)]:
                if days < 1 or days > 365:
                    flash(f'{stage_name} חייב להיות בין 1 ל-365 ימים', 'error')
                    return redirect(url_for('maslulim'))
            
            # Check if sum of stages equals SLA
            total_stages = stage_a_days + stage_b_days + stage_c_days + stage_d_days
            if total_stages != sla_days:
                flash(f'סכום השלבים ({total_stages}) חייב להיות שווה ל-SLA ({sla_days})', 'error')
                return redirect(url_for('maslulim'))
                
        except (ValueError, TypeError):
            flash('כל השדות חייבים להיות מספרים תקינים', 'error')
            return redirect(url_for('maslulim'))
        
        # Add the maslul
        maslul_id = db.add_maslul(int(hativa_id), name, description, sla_days, 
                                 stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        hativa_name = next(h['name'] for h in hativot if h['hativa_id'] == int(hativa_id))
        flash(f'מסלול "{name}" נוסף בהצלחה לחטיבת {hativa_name}', 'success')
        
    except ValueError as e:
        flash('נתונים לא תקינים', 'error')
    except Exception as e:
        flash(f'שגיאה בהוספת המסלול: {str(e)}', 'error')
    
    return redirect(url_for('maslulim'))

@app.route('/maslulim/edit/<int:maslul_id>', methods=['POST'])
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
        
        if not name:
            flash('שם המסלול הוא שדה חובה', 'error')
            return redirect(url_for('maslulim'))
            
        if len(name) < 2:
            flash('שם המסלול חייב להכיל לפחות 2 תווים', 'error')
            return redirect(url_for('maslulim'))
        
        # Validate SLA and stage days
        try:
            sla_days = int(sla_days)
            stage_a_days = int(stage_a_days)
            stage_b_days = int(stage_b_days)
            stage_c_days = int(stage_c_days)
            stage_d_days = int(stage_d_days)
            
            if sla_days < 1 or sla_days > 365:
                flash('SLA חייב להיות בין 1 ל-365 ימים', 'error')
                return redirect(url_for('maslulim'))
                
            # Validate stage days
            for stage_name, days in [('שלב א', stage_a_days), ('שלב ב', stage_b_days), 
                                   ('שלב ג', stage_c_days), ('שלב ד', stage_d_days)]:
                if days < 1 or days > 365:
                    flash(f'{stage_name} חייב להיות בין 1 ל-365 ימים', 'error')
                    return redirect(url_for('maslulim'))
            
            # Check if sum of stages equals SLA
            total_stages = stage_a_days + stage_b_days + stage_c_days + stage_d_days
            if total_stages != sla_days:
                flash(f'סכום השלבים ({total_stages}) חייב להיות שווה ל-SLA ({sla_days})', 'error')
                return redirect(url_for('maslulim'))
                
        except (ValueError, TypeError):
            flash('כל השדות חייבים להיות מספרים תקינים', 'error')
            return redirect(url_for('maslulim'))
        
        # Update the maslul
        success = db.update_maslul(maslul_id, name, description, sla_days, 
                                 stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        if success:
            flash(f'מסלול "{name}" עודכן בהצלחה', 'success')
        else:
            flash('המסלול לא נמצא במערכת', 'error')
            
    except Exception as e:
        flash(f'שגיאה בעדכון המסלול: {str(e)}', 'error')
    
    return redirect(url_for('maslulim'))

@app.route('/maslulim/delete/<int:maslul_id>', methods=['POST'])
def delete_maslul(maslul_id):
    """Delete route with safety checks"""
    try:
        # Check if maslul is used in any events
        events = db.get_events()
        maslul_events = [e for e in events if e['maslul_id'] == maslul_id]
        
        if maslul_events:
            flash(f'לא ניתן למחוק מסלול המשויך ל-{len(maslul_events)} אירועים. יש למחוק תחילה את האירועים הקשורים.', 'error')
            return redirect(url_for('maslulim'))
        
        # Get maslul name before deletion
        maslulim = db.get_maslulim()
        maslul = next((m for m in maslulim if m['maslul_id'] == maslul_id), None)
        
        if not maslul:
            flash('המסלול לא נמצא במערכת', 'error')
            return redirect(url_for('maslulim'))
        
        # Delete the maslul
        success = db.delete_maslul(maslul_id)
        if success:
            flash(f'מסלול "{maslul["name"]}" נמחק בהצלחה', 'success')
        else:
            flash('שגיאה במחיקת המסלול', 'error')
            
    except Exception as e:
        flash(f'שגיאה במחיקת המסלול: {str(e)}', 'error')
    
    return redirect(url_for('maslulim'))

@app.route('/exception_dates')
def exception_dates():
    """Manage exception dates"""
    dates_list = db.get_exception_dates()
    return render_template('exception_dates.html', dates=dates_list)

@app.route('/exception_dates/add', methods=['POST'])
def add_exception_date():
    """Add exception date"""
    date_str = request.form.get('date', '').strip()
    description = request.form.get('description', '').strip()
    date_type = request.form.get('type', 'holiday').strip()
    
    if not date_str:
        flash('תאריך הוא שדה חובה', 'error')
        return redirect(url_for('exception_dates'))
    
    try:
        exception_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.add_exception_date(exception_date, description, date_type)
        flash(f'תאריך חריג {date_str} נוסף בהצלחה', 'success')
    except ValueError:
        flash('פורמט תאריך לא תקין', 'error')
    except Exception as e:
        flash(f'שגיאה בהוספת התאריך: {str(e)}', 'error')
    
    return redirect(url_for('exception_dates'))


@app.route('/committees/add', methods=['POST'])
def add_committee_meeting():
    """Add new committee meeting"""
    committee_type_id = request.form.get('committee_type_id')
    hativa_id = request.form.get('hativa_id')
    vaada_date = request.form.get('vaada_date')
    status = request.form.get('status', 'planned')
    notes = request.form.get('notes', '').strip()
    
    if not all([committee_type_id, hativa_id, vaada_date]):
        flash('סוג ועדה, חטיבה ותאריך הם שדות חובה', 'error')
        return redirect(url_for('index'))
    
    try:
        meeting_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        vaadot_id = db.add_vaada(int(committee_type_id), int(hativa_id), meeting_date, status, notes=notes)
        flash('ישיבת ועדה נוספה בהצלחה', 'success')
    except ValueError as e:
        # Check if it's a date format error or our constraint error
        if "כבר קיימת ועדה בתאריך" in str(e):
            flash(str(e), 'error')
        else:
            flash('פורמט תאריך לא תקין', 'error')
    except Exception as e:
        flash(f'שגיאה בהוספת הישיבה: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/committees/edit/<int:vaadot_id>', methods=['POST'])
def edit_committee_meeting(vaadot_id):
    """Edit existing committee meeting"""
    committee_type_id = request.form.get('committee_type_id')
    hativa_id = request.form.get('hativa_id')
    vaada_date = request.form.get('vaada_date')
    notes = request.form.get('notes', '').strip()
    
    if not all([committee_type_id, hativa_id, vaada_date]):
        flash('סוג ועדה, חטיבה ותאריך הם שדות חובה', 'error')
        return redirect(url_for('index'))
    
    try:
        meeting_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        success = db.update_vaada(vaadot_id, int(committee_type_id), int(hativa_id), meeting_date, notes=notes)
        if success:
            flash('ישיבת הועדה עודכנה בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון הישיבה', 'error')
    except ValueError:
        flash('פורמט תאריך לא תקין', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון הישיבה: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/committees/delete/<int:vaadot_id>', methods=['POST'])
def delete_committee_meeting(vaadot_id):
    """Delete committee meeting and its events"""
    try:
        # First delete all related events
        events = db.get_events()
        related_events = [e for e in events if e['vaadot_id'] == vaadot_id]
        
        for event in related_events:
            db.delete_event(event['event_id'])
        
        # Then delete the committee meeting
        success = db.delete_vaada(vaadot_id)
        if success:
            flash(f'ישיבת הועדה ו-{len(related_events)} אירועים נמחקו בהצלחה', 'success')
        else:
            flash('שגיאה במחיקת הישיבה', 'error')
    except Exception as e:
        flash(f'שגיאה במחיקת הישיבה: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/events/add', methods=['POST'])
def add_event():
    """Add new event"""
    vaadot_id = request.form.get('vaadot_id')
    maslul_id = request.form.get('maslul_id')
    name = request.form.get('name', '').strip()
    event_type = request.form.get('event_type')
    expected_requests = request.form.get('expected_requests', '0')
    call_publication_date = request.form.get('call_publication_date')
    
    if not all([vaadot_id, maslul_id, name, event_type]):
        flash('כל השדות הם שדות חובה', 'error')
        return redirect(url_for('index'))
    
    try:
        expected_requests = int(expected_requests) if expected_requests else 0
        
        # Validate that committee and route are from the same division
        vaada = db.get_vaadot()[0] if db.get_vaadot() else None
        for v in db.get_vaadot():
            if v['vaadot_id'] == int(vaadot_id):
                vaada = v
                break
        
        maslul = None
        for m in db.get_maslulim():
            if m['maslul_id'] == int(maslul_id):
                maslul = m
                break
        
        if not vaada or not maslul:
            flash('ועדה או מסלול לא נמצאו במערכת', 'error')
            return redirect(url_for('index'))
        
        if vaada['hativa_id'] != maslul['hativa_id']:
            flash(f'שגיאה: המסלול "{maslul["name"]}" מחטיבת "{maslul["hativa_name"]}" אינו יכול להיות משויך לועדה מחטיבת "{vaada["hativa_name"]}"', 'error')
            return redirect(url_for('index'))
        
        # Validate event data
        event_data = {
            'vaadot_id': int(vaadot_id),
            'maslul_id': int(maslul_id),
            'name': name,
            'event_type': event_type,
            'expected_requests': expected_requests,
            'call_publication_date': call_publication_date
        }
        
        event_id = db.add_event(int(vaadot_id), int(maslul_id), name, event_type, expected_requests, call_publication_date)
        flash(f'אירוע "{name}" נוצר בהצלחה', 'success')
        
    except Exception as e:
        flash(f'שגיאה ביצירת האירוע: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/events/edit/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    """Edit existing event"""
    vaadot_id = request.form.get('vaadot_id')
    maslul_id = request.form.get('maslul_id')
    name = request.form.get('name', '').strip()
    event_type = request.form.get('event_type')
    expected_requests = request.form.get('expected_requests', '0')
    call_publication_date = request.form.get('call_publication_date')

    if not all([vaadot_id, maslul_id, name, event_type]):
        flash('כל השדות הם שדות חובה', 'error')
        return redirect(url_for('index'))
    
    try:
        expected_requests = int(expected_requests) if expected_requests else 0
        
        # Validate that committee and route are from the same division
        vaada = None
        for v in db.get_vaadot():
            if v['vaadot_id'] == int(vaadot_id):
                vaada = v
                break
        
        maslul = None
        for m in db.get_maslulim():
            if m['maslul_id'] == int(maslul_id):
                maslul = m
                break
        
        if not vaada or not maslul:
            flash('ועדה או מסלול לא נמצאו במערכת', 'error')
            return redirect(url_for('index'))
        
        if vaada['hativa_id'] != maslul['hativa_id']:
            flash(f'שגיאה: המסלול "{maslul["name"]}" מחטיבת "{maslul["hativa_name"]}" אינו יכול להיות משויך לועדה מחטיבת "{vaada["hativa_name"]}"', 'error')
            return redirect(url_for('index'))
        
        success = db.update_event(event_id, int(vaadot_id), int(maslul_id), name, event_type, expected_requests, call_publication_date)
        if success:
            flash(f'אירוע "{name}" עודכן בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון האירוע', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון האירוע: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/events/delete/<int:event_id>', methods=['POST'])
def delete_event_route(event_id):
    """Delete event"""
    try:
        # Get event name before deletion
        events = db.get_events()
        event = next((e for e in events if e['event_id'] == event_id), None)
        
        if not event:
            flash('האירוע לא נמצא במערכת', 'error')
            return redirect(url_for('index'))
        
        success = db.delete_event(event_id)
        if success:
            flash(f'אירוע "{event["name"]}" נמחק בהצלחה', 'success')
        else:
            flash('שגיאה במחיקת האירוע', 'error')
    except Exception as e:
        flash(f'שגיאה במחיקת האירוע: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/hativot/update_color', methods=['POST'])
def update_hativa_color():
    """Update division color"""
    hativa_id = request.form.get('hativa_id')
    color = request.form.get('color')
    
    if not all([hativa_id, color]):
        flash('חטיבה וצבע הם שדות חובה', 'error')
        return redirect(url_for('index'))
    
    try:
        success = db.update_hativa_color(int(hativa_id), color)
        if success:
            flash('צבע החטיבה עודכן בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון צבע החטיבה', 'error')
    except Exception as e:
        flash(f'שגיאה בעדכון צבע החטיבה: {str(e)}', 'error')
    
    return redirect(url_for('index'))







@app.route('/api/maslulim/<int:hativa_id>')
def api_maslulim_by_hativa(hativa_id):
    """API endpoint to get routes by division with enhanced data"""
    try:
        maslulim_list = db.get_maslulim(hativa_id)
        return jsonify({
            'success': True,
            'data': [{
                'maslul_id': m['maslul_id'],
                'name': m['name'],
                'description': m['description'],
                'hativa_name': m['hativa_name']
            } for m in maslulim_list],
            'count': len(maslulim_list)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }), 500

@app.route('/api/vaadot/<int:vaadot_id>/hativa')
def api_vaadot_hativa(vaadot_id):
    """API endpoint to get division ID for a specific committee meeting"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT hativa_id FROM vaadot WHERE vaadot_id = ?', (vaadot_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'hativa_id': result[0]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Committee meeting not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/events/<int:event_id>')
def api_event_details(event_id):
    """API endpoint to get event details"""
    try:
        events = db.get_events()
        event = next((e for e in events if e['event_id'] == event_id), None)
        
        if event:
            return jsonify({
                'success': True,
                'event': event
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Event not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/maslulim/<int:maslul_id>/details')
def api_maslul_details(maslul_id):
    """API endpoint to get specific route details"""
    try:
        maslulim = db.get_maslulim()
        maslul = next((m for m in maslulim if m['maslul_id'] == maslul_id), None)
        
        if not maslul:
            return jsonify({
                'success': False,
                'error': 'מסלול לא נמצא'
            }), 404
            
        # Get related events count
        events = db.get_events()
        events_count = len([e for e in events if e['maslul_id'] == maslul_id])
        
        return jsonify({
            'success': True,
            'data': {
                'maslul_id': maslul['maslul_id'],
                'name': maslul['name'],
                'description': maslul['description'],
                'hativa_name': maslul['hativa_name'],
                'hativa_id': maslul['hativa_id'],
                'events_count': events_count,
                'can_delete': events_count == 0
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/validate_date/<committee_name>/<date_str>')
def api_validate_date(committee_name, date_str):
    """API endpoint to validate committee date"""
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # Use auto_scheduler to check if date is available
        can_schedule = auto_scheduler.is_business_day(check_date) and db.is_date_available_for_meeting(check_date)
        reason = "זמין" if can_schedule else "תאריך לא זמין"
        return jsonify({
            'can_schedule': can_schedule,
            'reason': reason
        })
    except ValueError:
        return jsonify({
            'can_schedule': False,
            'reason': 'פורמט תאריך לא תקין'
        })

@app.route('/auto_schedule')
def auto_schedule():
    """Automatic meeting scheduling interface"""
    hativot = db.get_hativot()
    committee_types = db.get_committee_types()
    
    # Get current month by default
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    return render_template('auto_schedule.html', 
                         hativot=hativot, 
                         committee_types=committee_types,
                         current_year=year,
                         current_month=month)

@app.route('/auto_schedule/generate', methods=['POST'])
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
            return redirect(url_for('auto_schedule'))
        
        # Determine hativa_id - if only one selected, use it; otherwise None for all
        hativa_id = None
        if len(selected_hativot) == 1:
            hativa_id = int(selected_hativot[0])
        elif len(selected_hativot) > 1:
            # Multiple hativot selected - will process all
            pass
        else:
            flash('יש לבחור לפחות חטיבה אחת', 'warning')
            return redirect(url_for('auto_schedule'))
        
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
                app.logger.info(f"Generated {len(result.suggested_meetings)} suggestions for {year}/{month}")
            else:
                app.logger.warning(f"Failed to generate schedule for {year}/{month}: {result.message}")
        
        if not all_suggestions:
            months_names = [['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                            'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'][m-1] 
                           for m in months_to_process]
            flash(f'לא ניתן ליצור תזמון עבור החודשים: {", ".join(months_names)}', 'warning')
            return redirect(url_for('auto_schedule'))
        
        # Store in session for review
        from flask import session
        session['pending_schedule'] = {
            'year': year,
            'months': successful_months,
            'month_selection_type': month_selection_type,
            'suggestions': all_suggestions,
            'selected_hativot': selected_hativot
        }
        
        app.logger.info(f"Stored in session: {len(all_suggestions)} suggestions for {year} months: {successful_months}")
        app.logger.info(f"First suggestion in session: {all_suggestions[0] if all_suggestions else 'None'}")
        
        months_names = [['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                        'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'][m-1] 
                       for m in successful_months]
        flash(f'נוצרו {len(all_suggestions)} הצעות ישיבות עבור {", ".join(months_names)} {year}', 'success')
        return redirect(url_for('review_auto_schedule'))
        
    except Exception as e:
        import traceback
        app.logger.error(f'Error generating auto schedule: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        flash('שגיאה פנימית ביצירת התזמון. אנא נסה שוב מאוחר יותר.', 'error')
        return redirect(url_for('auto_schedule'))

@app.route('/auto_schedule/review')
def review_auto_schedule():
    """Review generated schedule before approval"""
    from flask import session
    
    pending_schedule = session.get('pending_schedule')
    if not pending_schedule:
        flash('אין לוח זמנים ממתין לאישור', 'warning')
        return redirect(url_for('auto_schedule'))
    
    # Get hativot and committee types for display
    hativot = {h['hativa_id']: h for h in db.get_hativot()}
    committee_types = {ct['committee_type_id']: ct for ct in db.get_committee_types()}
    
    # Enrich suggestions with names
    enriched_suggestions = []
    for suggestion in pending_schedule['suggestions']:
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
    
    return render_template('review_auto_schedule.html',
                         suggestions=enriched_suggestions,
                         schedule_info=pending_schedule,
                         validation=validation_result)

@app.route('/auto_schedule/approve', methods=['POST'])
def approve_auto_schedule():
    """Approve and create selected meetings from the generated schedule"""
    from flask import session
    
    try:
        pending_schedule = session.get('pending_schedule')
        if not pending_schedule:
            flash('אין לוח זמנים ממתין לאישור', 'warning')
            return redirect(url_for('auto_schedule'))
        
        selected_meetings = request.form.getlist('selected_meetings')
        if not selected_meetings:
            flash('יש לבחור לפחות הצעה אחת', 'warning')
            return redirect(url_for('review_auto_schedule'))
        
        # Convert to integers and get selected suggestions
        selected_indices = [int(idx) for idx in selected_meetings]
        suggestions = pending_schedule.get('suggestions', [])
        
        # Filter selected suggestions
        selected_meeting_suggestions = []
        for idx in selected_indices:
            if 0 <= idx < len(suggestions):
                selected_meeting_suggestions.append(suggestions[idx])
        
        if not selected_meeting_suggestions:
            flash('לא נמצאו הצעות תקינות לאישור', 'error')
            return redirect(url_for('review_auto_schedule'))
        
        # Create approval request
        from services.auto_schedule_service import ApprovalRequest
        approval_request = ApprovalRequest(
            suggestions=selected_meeting_suggestions,
            auto_approve=True
        )
        
        # Approve meetings using service
        result = auto_schedule_service.approve_meetings(approval_request)
        
        # Clear session
        session.pop('pending_schedule', None)
        
        # Show results
        if result.success_count > 0:
            flash(f'נוצרו בהצלחה {result.success_count} ישיבות', 'success')
        
        if result.failure_count > 0:
            failed_reasons = [f"{m['committee_type']}: {m['reason']}" for m in result.failed_meetings[:3]]
            flash(f'נכשלו {result.failure_count} ישיבות: {"; ".join(failed_reasons)}', 'warning')
        
        return redirect(url_for('index'))
        
    except Exception as e:
        import traceback
        app.logger.error(f'Error approving auto schedule: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        flash('שגיאה פנימית באישור התזמון. אנא נסה שוב מאוחר יותר.', 'error')
        return redirect(url_for('review_auto_schedule'))

@app.route('/auto_schedule/validate/<int:year>/<int:month>')
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

@app.route('/committee_types')
def committee_types():
    """Manage committee types"""
    # Get hativa_id from query parameters
    hativa_id = request.args.get('hativa_id', type=int)
    
    # Get committee types with statistics (filtered by division if specified)
    response = committee_types_service.get_committee_types_with_statistics(hativa_id)
    
    # Get all hativot for the dropdown
    hativot = db.get_hativot()
    
    if not response.success:
        flash(response.message, 'error')
    
    return render_template('committee_types.html', 
                         committee_types=response.committee_types,
                         weekly_count=response.statistics['weekly_count'],
                         monthly_count=response.statistics['monthly_count'],
                         active_meetings_count=response.statistics['active_meetings_count'],
                         hativot=hativot,
                         selected_hativa_id=hativa_id)

@app.route('/committee_types/add', methods=['POST'])
def add_committee_type():
    """Add new committee type"""
    # Create request object from form data
    committee_type_request = CommitteeTypeRequest(
        hativa_id=request.form.get('hativa_id', type=int),
        name=request.form.get('name', '').strip(),
        scheduled_day=request.form.get('scheduled_day', type=int),
        frequency=request.form.get('frequency', '').strip(),
        week_of_month=request.form.get('week_of_month', type=int) if request.form.get('week_of_month') else None,
        description=request.form.get('description', '').strip()
    )
    
    # Use service to create committee type
    response = committee_types_service.create_committee_type(committee_type_request)
    
    # Flash appropriate message
    flash(response.message, 'success' if response.success else 'error')
    
    return redirect(url_for('committee_types'))

@app.route('/committee_types/update', methods=['POST'])
def update_committee_type():
    """Update existing committee type"""
    committee_type_id = request.form.get('committee_type_id', type=int)
    
    # Create request object from form data
    committee_type_request = CommitteeTypeRequest(
        hativa_id=request.form.get('hativa_id', type=int),
        name=request.form.get('name', '').strip(),
        scheduled_day=request.form.get('scheduled_day', type=int),
        frequency=request.form.get('frequency', '').strip(),
        week_of_month=request.form.get('week_of_month', type=int) if request.form.get('week_of_month') else None,
        description=request.form.get('description', '').strip()
    )
    
    # Use service to update committee type
    response = committee_types_service.update_committee_type(committee_type_id, committee_type_request)
    
    # Flash appropriate message
    flash(response.message, 'success' if response.success else 'error')
    
    return redirect(url_for('committee_types'))

@app.route('/committee_types/delete', methods=['POST'])
def delete_committee_type():
    """Delete committee type"""
    committee_type_id = request.form.get('committee_type_id', type=int)
    
    # Use service to delete committee type
    response = committee_types_service.delete_committee_type(committee_type_id)
    
    # Flash appropriate message
    flash(response.message, 'success' if response.success else 'error')
    
    return redirect(url_for('committee_types'))

# User Management Routes (Admin Only)
@app.route('/admin/users')
@admin_required
def manage_users():
    """User management page"""
    users = db.get_all_users()
    hativot = db.get_hativot()
    current_user = auth_manager.get_current_user()
    
    # Statistics
    total_users = len(users)
    active_users = len([u for u in users if u['is_active']])
    admin_count = len([u for u in users if u['role'] == 'admin'])
    manager_count = len([u for u in users if u['role'] == 'manager'])
    user_count = len([u for u in users if u['role'] == 'user'])
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'admin_count': admin_count,
        'manager_count': manager_count,
        'user_count': user_count
    }
    
    return render_template('admin/users.html', 
                         users=users, 
                         hativot=hativot, 
                         stats=stats,
                         current_user=current_user)

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def add_user():
    """Add new user"""
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'user')
        hativa_id = request.form.get('hativa_id')
        password = request.form.get('password', '').strip()
        
        # Validation
        if not all([username, email, full_name, password]):
            flash('כל השדות הנדרשים חייבים להיות מלאים', 'error')
            return redirect(url_for('manage_users'))
        
        # Check if username exists
        if db.check_username_exists(username):
            flash('שם המשתמש כבר קיים במערכת', 'error')
            return redirect(url_for('manage_users'))
        
        # Check if email exists
        if db.check_email_exists(email):
            flash('כתובת האימייל כבר קיימת במערכת', 'error')
            return redirect(url_for('manage_users'))
        
        # Convert hativa_id
        hativa_id = int(hativa_id) if hativa_id and hativa_id != '' else None
        
        # Hash password
        password_hash = auth_manager.hash_password(password)
        
        # Create user
        user_id = db.create_user(username, email, password_hash, full_name, role, hativa_id)
        
        if user_id:
            flash(f'המשתמש {full_name} נוצר בהצלחה', 'success')
        else:
            flash('שגיאה ביצירת המשתמש', 'error')
            
    except Exception as e:
        flash(f'שגיאה ביצירת המשתמש: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/admin/users/update', methods=['POST'])
@admin_required
def update_user():
    """Update user information"""
    try:
        user_id = int(request.form.get('user_id'))
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'user')
        hativa_id = request.form.get('hativa_id')
        
        # Validation
        if not all([username, email, full_name]):
            flash('כל השדות הנדרשים חייבים להיות מלאים', 'error')
            return redirect(url_for('manage_users'))
        
        # Check if username exists (excluding current user)
        if db.check_username_exists(username, user_id):
            flash('שם המשתמש כבר קיים במערכת', 'error')
            return redirect(url_for('manage_users'))
        
        # Check if email exists (excluding current user)
        if db.check_email_exists(email, user_id):
            flash('כתובת האימייל כבר קיימת במערכת', 'error')
            return redirect(url_for('manage_users'))
        
        # Convert hativa_id
        hativa_id = int(hativa_id) if hativa_id and hativa_id != '' else None
        
        # Update user
        success = db.update_user(user_id, username, email, full_name, role, hativa_id)
        
        if success:
            flash(f'פרטי המשתמש {full_name} עודכנו בהצלחה', 'success')
        else:
            flash('שגיאה בעדכון פרטי המשתמש', 'error')
            
    except Exception as e:
        flash(f'שגיאה בעדכון המשתמש: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        # Check if trying to deactivate self
        current_user = auth_manager.get_current_user()
        if current_user['user_id'] == user_id:
            flash('לא ניתן להשבית את המשתמש הנוכחי', 'error')
            return redirect(url_for('manage_users'))
        
        success = db.toggle_user_status(user_id)
        
        if success:
            user = db.get_user_by_id(user_id)
            status = "הופעל" if user['is_active'] else "הושבת"
            flash(f'המשתמש {user["full_name"]} {status} בהצלחה', 'success')
        else:
            flash('שגיאה בשינוי סטטוס המשתמש', 'error')
            
    except Exception as e:
        flash(f'שגיאה בשינוי סטטוס המשתמש: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user (soft delete)"""
    try:
        # Check if trying to delete self
        current_user = auth_manager.get_current_user()
        if current_user['user_id'] == user_id:
            flash('לא ניתן למחוק את המשתמש הנוכחי', 'error')
            return redirect(url_for('manage_users'))
        
        user = db.get_user_by_id(user_id)
        success = db.delete_user(user_id)
        
        if success:
            flash(f'המשתמש {user["full_name"]} נמחק בהצלחה', 'success')
        else:
            flash('שגיאה במחיקת המשתמש', 'error')
            
    except Exception as e:
        flash(f'שגיאה במחיקת המשתמש: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/admin/users/change_password', methods=['POST'])
@admin_required
def change_user_password():
    """Change user password"""
    try:
        user_id = int(request.form.get('user_id'))
        new_password = request.form.get('new_password', '').strip()
        
        if not new_password:
            flash('נדרשת סיסמה חדשה', 'error')
            return redirect(url_for('manage_users'))
        
        if len(new_password) < 6:
            flash('הסיסמה חייבת להכיל לפחות 6 תווים', 'error')
            return redirect(url_for('manage_users'))
        
        # Hash new password
        new_password_hash = auth_manager.hash_password(new_password)
        
        # Update password
        success = db.change_user_password(user_id, new_password_hash)
        
        if success:
            user = db.get_user_by_id(user_id)
            flash(f'הסיסמה של {user["full_name"]} שונתה בהצלחה', 'success')
        else:
            flash('שגיאה בשינוי הסיסמה', 'error')
            
    except Exception as e:
        flash(f'שגיאה בשינוי הסיסמה: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

# Drag & Drop API endpoints
@app.route('/api/move_committee', methods=['POST'])
@login_required
@editing_permission_required
def move_committee():
    """Move committee meeting to a different date"""
    try:
        data = request.get_json()
        vaada_id = data.get('vaada_id')
        new_date = data.get('new_date')
        
        if not vaada_id or not new_date:
            return jsonify({'success': False, 'message': 'נתונים חסרים'}), 400
        
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
        
        # Update committee meeting date
        try:
            success = db.update_vaada_date(vaada_id, new_date_obj)
        except ValueError as ve:
            return jsonify({'success': False, 'message': str(ve)}), 400
        
        if success:
            return jsonify({'success': True, 'message': 'הועדה הועברה בהצלחה'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה בהעברת הועדה'}), 500
            
    except Exception as e:
        app.logger.error(f"Error moving committee: {str(e)}")
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@app.route('/api/move_event', methods=['POST'])
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
        app.logger.info(f"Looking for event_id: {event_id}, target_vaada_id: {target_vaada_id}")
        event = db.get_event_by_id(event_id)
        target_committee = db.get_vaada_by_id(target_vaada_id)
        
        app.logger.info(f"Found event: {event}")
        app.logger.info(f"Found target_committee: {target_committee}")
        
        if not event or not target_committee:
            app.logger.error(f"Event or committee not found. Event: {event}, Committee: {target_committee}")
            return jsonify({'success': False, 'message': 'אירוע או ועדה לא נמצאו'}), 404
        
        # Validate that event's route belongs to target committee's division
        route = db.get_maslul_by_id(event['maslul_id'])
        if route['hativa_id'] != target_committee['hativa_id']:
            return jsonify({'success': False, 'message': 'לא ניתן להעביר אירוע לועדה מחטיבה אחרת'}), 400
        
        # Update event's committee meeting
        success = db.update_event_vaada(event_id, target_vaada_id)
        
        if success:
            return jsonify({'success': True, 'message': 'האירוע הועבר בהצלחה'})
        else:
            return jsonify({'success': False, 'message': 'שגיאה בהעברת האירוע'}), 500
            
    except Exception as e:
        app.logger.error(f"Error moving event: {str(e)}")
        return jsonify({'success': False, 'message': f'שגיאה: {str(e)}'}), 500

@app.route('/events_table')
@login_required
def events_table():
    """Events table view with advanced filtering"""
    try:
        # Get all events with extended information
        events = db.get_events()

        # Normalize date fields for consistent formatting in the template
        from datetime import datetime
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

        # Get filter options
        hativot = db.get_hativot()
        maslulim = db.get_maslulim()
        committee_types = db.get_committee_types()

        # Get unique event types
        event_types = list(set([event.get('event_type', '') for event in events if event.get('event_type')]))

        return render_template('events_table.html', 
                             events=events,
                             hativot=hativot,
                             maslulim=maslulim,
                             committee_types=committee_types,
                             event_types=event_types)
    except Exception as e:
        flash(f'שגיאה בטעינת נתוני האירועים: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
