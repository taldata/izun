#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date, timedelta
import json
from database import DatabaseManager
from scheduler import CommitteeScheduler
from auto_scheduler import AutoMeetingScheduler

app = Flask(__name__)
app.secret_key = 'committee_management_secret_key_2025'

# Initialize system components
db = DatabaseManager()
scheduler = CommitteeScheduler(db)
auto_scheduler = AutoMeetingScheduler(db)

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
    """Manage routes with enhanced functionality"""
    try:
        # Get data with error handling
        maslulim_list = db.get_maslulim()
        hativot_list = db.get_hativot()
        
        # Group maslulim by hativa for better organization
        maslulim_by_hativa = {}
        for maslul in maslulim_list:
            hativa_name = maslul['hativa_name']
            if hativa_name not in maslulim_by_hativa:
                maslulim_by_hativa[hativa_name] = []
            maslulim_by_hativa[hativa_name].append(maslul)
        
        # Calculate statistics
        stats = {
            'total_maslulim': len(maslulim_list),
            'total_hativot': len(hativot_list),
            'maslulim_per_hativa': {hativa['name']: len([m for m in maslulim_list if m['hativa_id'] == hativa['hativa_id']]) for hativa in hativot_list}
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
        
        # Add the maslul
        maslul_id = db.add_maslul(int(hativa_id), name, description)
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
        
        if not name:
            flash('שם המסלול הוא שדה חובה', 'error')
            return redirect(url_for('maslulim'))
            
        if len(name) < 2:
            flash('שם המסלול חייב להכיל לפחות 2 תווים', 'error')
            return redirect(url_for('maslulim'))
        
        # Update the maslul
        success = db.update_maslul(maslul_id, name, description)
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
        # Validate input parameters
        try:
            year = int(request.form['year'])
            month = int(request.form['month'])
        except (ValueError, KeyError):
            flash('שנה או חודש לא תקינים', 'error')
            return redirect(url_for('auto_schedule'))
        
        # Validate year and month ranges
        if year < 2020 or year > 2030:
            flash('השנה חייבת להיות בין 2020 ל-2030', 'error')
            return redirect(url_for('auto_schedule'))
        
        if month < 1 or month > 12:
            flash('החודש חייב להיות בין 1 ל-12', 'error')
            return redirect(url_for('auto_schedule'))
        
        selected_hativot = request.form.getlist('hativot_ids')
        
        if not selected_hativot:
            flash('יש לבחור לפחות חטיבה אחת', 'warning')
            return redirect(url_for('auto_schedule'))
        
        # Validate division IDs
        try:
            hativot_ids = [int(h_id) for h_id in selected_hativot]
            # Verify divisions exist in database
            existing_hativot = db.get_hativot()
            existing_ids = [div['hativa_id'] for div in existing_hativot]
            invalid_hativot = [h_id for h_id in hativot_ids if h_id not in existing_ids]
            
            if invalid_hativot:
                flash(f'חטיבות לא תקינות: {invalid_hativot}', 'error')
                return redirect(url_for('auto_schedule'))
                
        except ValueError:
            flash('מזהי חטיבות לא תקינים', 'error')
            return redirect(url_for('auto_schedule'))
        
        # Generate schedule
        schedule_result = auto_scheduler.generate_monthly_schedule(year, month, hativot_ids)
        
        if not schedule_result or not schedule_result.get('suggested_meetings'):
            flash('לא ניתן ליצור תזמון עבור התקופה והחטיבות שנבחרו', 'warning')
            return redirect(url_for('auto_schedule'))
        
        # Store in session for review
        from flask import session
        session['pending_schedule'] = {
            'year': year,
            'month': month,
            'suggestions': schedule_result['suggested_meetings']
        }
        
        flash(f'נוצרו {schedule_result["total_suggestions"]} הצעות ישיבות לחודש {month}/{year}', 'success')
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
    
    # Validate schedule constraints
    validation_result = auto_scheduler.validate_schedule_constraints(
        pending_schedule['year'], pending_schedule['month']
    )
    
    return render_template('review_auto_schedule.html',
                         suggestions=enriched_suggestions,
                         schedule_info=pending_schedule,
                         validation=validation_result)

@app.route('/auto_schedule/approve', methods=['POST'])
def approve_auto_schedule():
    """Approve and create selected meetings from the generated schedule"""
    from flask import session
    
    pending_schedule = session.get('pending_schedule')
    if not pending_schedule:
        flash('אין לוח זמנים ממתין לאישור', 'warning')
        return redirect(url_for('auto_schedule'))
    
    selected_suggestions = request.form.getlist('selected_suggestions')
    if not selected_suggestions:
        flash('יש לבחור לפחות הצעה אחת', 'warning')
        return redirect(url_for('review_auto_schedule'))
    
    try:
        # Convert to integers and validate
        try:
            selected_indices = [int(idx) for idx in selected_suggestions]
        except ValueError:
            flash('מזהי הצעות לא תקינים', 'error')
            return redirect(url_for('review_auto_schedule'))
        
        suggestions = pending_schedule.get('suggestions', [])
        if not suggestions:
            flash('אין הצעות זמינות', 'error')
            return redirect(url_for('auto_schedule'))
        
        created_count = 0
        failed_count = 0
        
        for idx in selected_indices:
            if 0 <= idx < len(suggestions):
                suggestion = suggestions[idx]
                try:
                    # Validate suggestion data
                    required_fields = ['committee_type_id', 'hativa_id', 'date']
                    if not all(field in suggestion for field in required_fields):
                        failed_count += 1
                        continue
                    
                    # Check if meeting already exists
                    existing_meetings = db.get_vaadot_by_date_and_hativa(
                        suggestion['date'], 
                        suggestion['hativa_id']
                    )
                    
                    if existing_meetings:
                        app.logger.warning(f"Meeting already exists for {suggestion['date']} and hativa {suggestion['hativa_id']}")
                        failed_count += 1
                        continue
                    
                    # Create the meeting
                    vaadot_id = db.create_vaada(
                        committee_type_id=suggestion['committee_type_id'],
                        hativa_id=suggestion['hativa_id'],
                        vaada_date=suggestion['date']
                    )
                    
                    if vaadot_id:
                        created_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    app.logger.error(f"Failed to create meeting: {str(e)}")
                    failed_count += 1
            else:
                failed_count += 1
        
        # Clear the pending schedule
        session.pop('pending_schedule', None)
        
        # Provide detailed feedback
        if created_count > 0 and failed_count == 0:
            flash(f'נוצרו {created_count} ישיבות בהצלחה', 'success')
        elif created_count > 0 and failed_count > 0:
            flash(f'נוצרו {created_count} ישיבות בהצלחה, {failed_count} נכשלו', 'warning')
        else:
            flash('לא ניתן היה ליצור אף ישיבה', 'error')
            
        return redirect(url_for('committees'))
        
    except Exception as e:
        app.logger.error(f'Error approving auto schedule: {str(e)}')
        flash('שגיאה פנימית באישור התזמון. אנא נסה שוב מאוחר יותר.', 'error')
        return redirect(url_for('review_auto_schedule'))

@app.route('/auto_schedule/validate/<int:year>/<int:month>')
def validate_monthly_schedule(year: int, month: int):
    """API endpoint to validate monthly schedule constraints"""
    try:
        validation_result = auto_scheduler.validate_schedule_constraints(year, month)
        return jsonify(validation_result)
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
