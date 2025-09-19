from functools import wraps
from flask import session, request, redirect, url_for, flash, jsonify
import hashlib
from database import DatabaseManager

class AuthManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == password_hash
    
    def login_user(self, username: str, password: str) -> tuple[bool, str]:
        """
        Authenticate user and create session
        Returns (success, message)
        """
        user = self.db.get_user_by_username(username)
        
        if not user:
            return False, "שם משתמש או סיסמה שגויים"
        
        if not self.verify_password(password, user['password_hash']):
            return False, "שם משתמש או סיסמה שגויים"
        
        # Create session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['hativa_id'] = user['hativa_id']
        session['full_name'] = user['full_name']
        
        # Update last login
        self.db.update_last_login(user['user_id'])
        
        return True, f"ברוך הבא, {user['full_name']}"
    
    def logout_user(self):
        """Clear user session"""
        session.clear()
    
    def get_current_user(self) -> dict:
        """Get current logged in user info"""
        if 'user_id' not in session:
            return None
        
        return {
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'hativa_id': session['hativa_id'],
            'full_name': session['full_name']
        }
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return 'user_id' in session
    
    def can_edit(self, target_hativa_id: int = None) -> tuple[bool, str]:
        """Check if current user can edit"""
        if not self.is_logged_in():
            return False, "נדרשת התחברות"
        
        user = self.get_current_user()
        return self.db.can_user_edit(
            user['role'], 
            target_hativa_id, 
            user['hativa_id']
        )

# Decorators for route protection
def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            flash('נדרשת התחברות למערכת', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            flash('נדרשת התחברות למערכת', 'error')
            return redirect(url_for('login'))
        
        if session.get('role') != 'admin':
            if request.is_json:
                return jsonify({'error': 'נדרשות הרשאות מנהל'}), 403
            flash('נדרשות הרשאות מנהל מערכת', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def editing_permission_required(f):
    """Decorator to check editing permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            flash('נדרשת התחברות למערכת', 'error')
            return redirect(url_for('login'))
        
        # Get target hativa_id from form data or URL params
        target_hativa_id = None
        if request.method == 'POST':
            target_hativa_id = request.form.get('hativa_id')
        elif request.args.get('hativa_id'):
            target_hativa_id = request.args.get('hativa_id')
        
        if target_hativa_id:
            target_hativa_id = int(target_hativa_id)
        
        # Check permissions
        from app import auth_manager
        can_edit, reason = auth_manager.can_edit(target_hativa_id)
        
        if not can_edit:
            if request.is_json:
                return jsonify({'error': reason}), 403
            flash(reason, 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function
