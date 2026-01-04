from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from services_init import db, auth_manager, audit_logger
from auth import admin_required, login_required

user_bp = Blueprint('users', __name__)

@user_bp.route('/admin/users')
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
    editor_count = len([u for u in users if u['role'] == 'editor'])
    viewer_count = len([u for u in users if u['role'] == 'viewer'])
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'admin_count': admin_count,
        'editor_count': editor_count,
        'viewer_count': viewer_count
    }
    
    return render_template('admin/users.html', 
                         users=users, 
                         hativot=hativot, 
                         stats=stats,
                         current_user=current_user)

@user_bp.route('/admin/permissions')
@login_required
def permissions_matrix():
    """Permissions management and matrix view"""
    current_user = auth_manager.get_current_user()
    return render_template('admin/permissions.html', current_user=current_user)

@user_bp.route('/admin/users/update', methods=['POST'])
@admin_required
def update_user():
    """Update user information with multiple hativot access"""
    try:
        user_id = int(request.form.get('user_id'))
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'viewer')
        hativa_ids = request.form.getlist('hativa_ids[]')  # Multiple hativot

        # Validation
        if not all([username, email, full_name]):
            flash('כל השדות הנדרשים חייבים להיות מלאים', 'error')
            return redirect(url_for('users.manage_users'))

        # Validate role
        if role not in ['admin', 'editor', 'viewer']:
            flash('תפקיד לא חוקי', 'error')
            return redirect(url_for('users.manage_users'))
        
        # Check if username exists (excluding current user)
        if db.check_username_exists(username, user_id):
            flash('שם המשתמש כבר קיים במערכת', 'error')
            return redirect(url_for('users.manage_users'))
        
        # Check if email exists (excluding current user)
        if db.check_email_exists(email, user_id):
            flash('כתובת האימייל כבר קיימת במערכת', 'error')
            return redirect(url_for('users.manage_users'))
        
        # Convert hativa_ids to integers
        hativa_ids_int = [int(hid) for hid in hativa_ids if hid] if hativa_ids else []
        
        # Update user
        success = db.update_user(user_id, username, email, full_name, role, hativa_ids_int)
        
        if success:
            audit_logger.log_user_updated(user_id, username)
            hativot_text = f' עם גישה ל-{len(hativa_ids_int)} חטיבות' if hativa_ids_int else ''
            flash(f'פרטי המשתמש {full_name} עודכנו בהצלחה{hativot_text}', 'success')
        else:
            flash('שגיאה בעדכון פרטי המשתמש', 'error')
            
    except Exception as e:
        flash(f'שגיאה בעדכון המשתמש: {str(e)}', 'error')
    
    return redirect(url_for('users.manage_users'))

@user_bp.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        # Check if trying to deactivate self
        current_user = auth_manager.get_current_user()
        if current_user['user_id'] == user_id:
            flash('לא ניתן להשבית את המשתמש הנוכחי', 'error')
            return redirect(url_for('users.manage_users'))
        
        success = db.toggle_user_status(user_id)
        
        if success:
            user = db.get_user_by_id(user_id)
            audit_logger.log_user_toggled(user_id, user['username'], user['is_active'])
            status = "הופעל" if user['is_active'] else "הושבת"
            flash(f'המשתמש {user["full_name"]} {status} בהצלחה', 'success')
        else:
            flash('שגיאה בשינוי סטטוס המשתמש', 'error')
            
    except Exception as e:
        flash(f'שגיאה בשינוי סטטוס המשתמש: {str(e)}', 'error')
    
    return redirect(url_for('users.manage_users'))
