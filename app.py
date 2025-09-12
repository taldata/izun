#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date, timedelta
import json
from database import DatabaseManager
from scheduler import CommitteeScheduler

app = Flask(__name__)
app.secret_key = 'committee_management_secret_key_2025'

# Initialize system components
db = DatabaseManager()
scheduler = CommitteeScheduler(db)

@app.route('/')
def index():
    """Main dashboard"""
    # Get summary statistics
    hativot = db.get_hativot()
    maslulim = db.get_maslulim()
    committee_types = db.get_committee_types()
    committees = db.get_vaadot()  # This now returns meeting instances
    events = db.get_events()
    exception_dates = db.get_exception_dates()
    
    # Get current month schedule
    today = date.today()
    monthly_schedule = scheduler.get_monthly_schedule(today.year, today.month)
    
    stats = {
        'hativot_count': len(hativot),
        'maslulim_count': len(maslulim),
        'committee_types_count': len(committee_types),
        'committees_count': len(committees),
        'events_count': len(events),
        'exception_dates_count': len(exception_dates),
        'business_days_this_month': len(monthly_schedule['business_days'])
    }
    
    return render_template('index.html', stats=stats, committee_types=committee_types, committees=committees)

@app.route('/hativot')
def hativot():
    """Manage divisions"""
    hativot_list = db.get_hativot()
    return render_template('hativot.html', hativot=hativot_list)

@app.route('/hativot/add', methods=['POST'])
def add_hativa():
    """Add new division"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('שם החטיבה הוא שדה חובה', 'error')
        return redirect(url_for('hativot'))
    
    try:
        hativa_id = db.add_hativa(name, description)
        flash(f'חטיבה "{name}" נוספה בהצלחה', 'success')
    except Exception as e:
        flash(f'שגיאה בהוספת החטיבה: {str(e)}', 'error')
    
    return redirect(url_for('hativot'))

@app.route('/maslulim')
def maslulim():
    """Manage routes"""
    maslulim_list = db.get_maslulim()
    hativot_list = db.get_hativot()
    return render_template('maslulim.html', maslulim=maslulim_list, hativot=hativot_list)

@app.route('/maslulim/add', methods=['POST'])
def add_maslul():
    """Add new route"""
    hativa_id = request.form.get('hativa_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not hativa_id or not name:
        flash('חטיבה ושם המסלול הם שדות חובה', 'error')
        return redirect(url_for('maslulim'))
    
    try:
        maslul_id = db.add_maslul(int(hativa_id), name, description)
        flash(f'מסלול "{name}" נוסף בהצלחה', 'success')
    except Exception as e:
        flash(f'שגיאה בהוספת המסלול: {str(e)}', 'error')
    
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

@app.route('/committees')
def committees():
    """View committees"""
    committee_types = db.get_committee_types()
    committees_list = db.get_vaadot()
    hativot = db.get_hativot()
    return render_template('committees.html', committee_types=committee_types, committees=committees_list, hativot=hativot)

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
        return redirect(url_for('committees'))
    
    try:
        meeting_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        vaadot_id = db.add_vaada(int(committee_type_id), int(hativa_id), meeting_date, status, notes=notes)
        flash('ישיבת ועדה נוספה בהצלחה', 'success')
    except ValueError:
        flash('פורמט תאריך לא תקין', 'error')
    except Exception as e:
        flash(f'שגיאה בהוספת הישיבה: {str(e)}', 'error')
    
    return redirect(url_for('committees'))

@app.route('/events')
def events():
    """Manage events"""
    events_list = db.get_events()
    committees_list = db.get_vaadot()
    committee_types = db.get_committee_types()
    maslulim_list = db.get_maslulim()
    return render_template('events.html', events=events_list, committees=committees_list, committee_types=committee_types, maslulim=maslulim_list)

@app.route('/events/add', methods=['POST'])
def add_event():
    """Add new event"""
    vaadot_id = request.form.get('vaadot_id')
    maslul_id = request.form.get('maslul_id')
    name = request.form.get('name', '').strip()
    event_type = request.form.get('event_type')
    expected_requests = request.form.get('expected_requests', '0')
    
    if not all([vaadot_id, maslul_id, name, event_type]):
        flash('כל השדות הם שדות חובה', 'error')
        return redirect(url_for('events'))
    
    try:
        expected_requests = int(expected_requests) if expected_requests else 0
        
        # Validate event data
        event_data = {
            'vaadot_id': int(vaadot_id),
            'maslul_id': int(maslul_id),
            'name': name,
            'event_type': event_type,
            'expected_requests': expected_requests
        }
        
        is_valid, message = scheduler.validate_event_scheduling(event_data)
        if not is_valid:
            flash(f'שגיאה באימות האירוע: {message}', 'error')
            return redirect(url_for('events'))
        
        event_id = db.add_event(int(vaadot_id), int(maslul_id), name, event_type, expected_requests)
        flash(f'אירוע "{name}" נוצר בהצלחה', 'success')
        
    except Exception as e:
        flash(f'שגיאה ביצירת האירוע: {str(e)}', 'error')
    
    return redirect(url_for('events'))

@app.route('/schedule')
def schedule():
    """Monthly schedule view"""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    try:
        monthly_schedule = scheduler.get_monthly_schedule(year, month)
        return render_template('schedule.html', schedule=monthly_schedule)
    except Exception as e:
        flash(f'שגיאה בטעינת הלוח: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/suggest_dates')
def suggest_dates():
    """Suggest available dates for committees"""
    committee_types = db.get_committee_types()
    hativot = db.get_hativot()
    
    committee_type_id = request.args.get('committee_type_id', type=int)
    suggestions = []
    
    if committee_type_id:
        committee_type = next((c for c in committee_types if c['committee_type_id'] == committee_type_id), None)
        if committee_type:
            suggestions = scheduler.suggest_next_available_dates(committee_type['name'], date.today(), 10)
    
    return render_template('suggest_dates.html', committee_types=committee_types, hativot=hativot, suggestions=suggestions, selected_committee_type_id=committee_type_id)

@app.route('/api/maslulim/<int:hativa_id>')
def api_maslulim_by_hativa(hativa_id):
    """API endpoint to get routes by division"""
    maslulim_list = db.get_maslulim(hativa_id)
    return jsonify([{
        'maslul_id': m['maslul_id'],
        'name': m['name'],
        'description': m['description']
    } for m in maslulim_list])

@app.route('/api/validate_date/<committee_name>/<date_str>')
def api_validate_date(committee_name, date_str):
    """API endpoint to validate committee date"""
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        can_schedule, reason = scheduler.can_schedule_committee(committee_name, check_date)
        return jsonify({
            'can_schedule': can_schedule,
            'reason': reason
        })
    except ValueError:
        return jsonify({
            'can_schedule': False,
            'reason': 'פורמט תאריך לא תקין'
        })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
