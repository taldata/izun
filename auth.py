from functools import wraps
from flask import session, request, redirect, url_for, flash, jsonify
import hashlib
import bcrypt
from database import DatabaseManager
from typing import Optional

class AuthManager:
    def __init__(self, db_manager: DatabaseManager, ad_service=None):
        self.db = db_manager
        self.ad_service = ad_service
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt (preferred) or SHA-256 (legacy)"""
        # Use bcrypt for new passwords
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def hash_password_legacy(self, password: str) -> str:
        """Legacy SHA-256 hash (for backward compatibility)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash (supports both bcrypt and legacy SHA-256)"""
        if not password_hash:
            return False
            
        # Check if it's a bcrypt hash (starts with $2b$ or $2a$)
        if password_hash.startswith('$2'):
            try:
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            except Exception:
                return False
        else:
            # Legacy SHA-256 verification
            return self.hash_password_legacy(password) == password_hash
    
    def login_user(self, username: str, password: str) -> tuple[bool, str]:
        """
        Authenticate user and create session
        Supports both Active Directory and local authentication
        Returns (success, message)
        """
        if not username or not password:
            return False, "שם משתמש וסיסמה נדרשים"
        
        # Check if AD is enabled and try AD authentication first
        if self.ad_service and self.ad_service.is_enabled():
            ad_success, ad_user_info, ad_message = self.ad_service.authenticate(username, password)
            
            if ad_success and ad_user_info:
                # AD authentication successful
                # Check if user exists in local DB
                user = self.db.get_user_by_username_any_source(username)
                
                if user:
                    # User exists - check if active
                    if not user['is_active']:
                        return False, "חשבון המשתמש מושבת"
                    
                    # Sync user info from AD if configured
                    if self.db.get_system_setting('ad_sync_on_login') == '1':
                        self.ad_service.sync_user_to_local(
                            ad_user_info,
                            user['role'],
                            user['hativa_id']
                        )
                    
                    user_id = user['user_id']
                    role = user['role']
                    hativa_id = user['hativa_id']
                else:
                    # New AD user - auto-create if configured
                    if self.db.get_system_setting('ad_auto_create_users') == '1':
                        # Determine role from AD groups
                        role = self.ad_service.get_default_role_from_groups(ad_user_info.get('groups', []))
                        
                        # Get default hativa
                        default_hativa_str = self.db.get_system_setting('ad_default_hativa_id')
                        default_hativa_id = int(default_hativa_str) if default_hativa_str else None
                        
                        # Create user
                        user_id = self.ad_service.sync_user_to_local(
                            ad_user_info,
                            role,
                            default_hativa_id
                        )
                        
                        if not user_id:
                            return False, "שגיאה ביצירת חשבון משתמש"
                        
                        hativa_id = default_hativa_id
                    else:
                        return False, "משתמש לא מורשה להתחבר למערכת"
                
                # Create session for AD user
                session['user_id'] = user_id
                session['username'] = username
                session['role'] = role
                session['hativa_id'] = hativa_id
                session['full_name'] = ad_user_info['full_name']
                session['auth_source'] = 'ad'
                
                # Update last login
                self.db.update_last_login(user_id)
                
                return True, f"ברוך הבא, {ad_user_info['full_name']}"
        
        # Try local authentication (fallback or when AD is disabled)
        user = self.db.get_user_by_username(username)
        
        if not user:
            return False, "שם משתמש או סיסמה שגויים"
        
        # Only allow local auth for local users
        if user.get('auth_source') == 'ad':
            return False, "משתמש AD חייב להתחבר דרך Active Directory"
        
        if not user['is_active']:
            return False, "חשבון המשתמש מושבת"
        
        if not user.get('password_hash'):
            return False, "חשבון המשתמש לא הוגדר עם סיסמה"
        
        if not self.verify_password(password, user['password_hash']):
            return False, "שם משתמש או סיסמה שגויים"
        
        # Create session for local user
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['hativa_id'] = user['hativa_id']
        session['full_name'] = user['full_name']
        session['auth_source'] = 'local'
        
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
