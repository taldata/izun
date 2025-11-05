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
    
    # Password verification methods kept for backward compatibility with user management
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
    
    # Local authentication disabled - SSO only
    # login_user method removed - all authentication through Azure AD SSO
    
    def logout_user(self):
        """Clear user session"""
        session.clear()
    
    def get_current_user(self) -> dict:
        """Get current logged in user info with hativot access"""
        if 'user_id' not in session:
            return None
        
        # Get user's hativot from database
        user_hativot = self.db.get_user_hativot(session['user_id'])
        hativa_ids = [h['hativa_id'] for h in user_hativot]
        
        return {
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'hativa_ids': hativa_ids,
            'hativot': user_hativot,
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
            user['user_id'],
            user['role'], 
            target_hativa_id
        )

# Decorators for route protection
def login_required(f):
    """Decorator to require login - redirects to Azure AD SSO"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Prevent redirect loops - check if we're already on auth routes
            if request.path in ['/auth/azure', '/auth/callback', '/login']:
                # Already on auth route, don't redirect again
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Redirect directly to SSO instead of login page
            return redirect(url_for('auth_azure'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Prevent redirect loops - check if we're already on auth routes
            if request.path in ['/auth/azure', '/auth/callback', '/login']:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Redirect directly to SSO instead of login page
            return redirect(url_for('auth_azure'))
        
        if session.get('role') != 'admin':
            if request.is_json:
                return jsonify({'error': 'נדרשות הרשאות מנהל'}), 403
            flash('נדרשות הרשאות מנהל מערכת', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    """Decorator to require editor or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Prevent redirect loops - check if we're already on auth routes
            if request.path in ['/auth/azure', '/auth/callback', '/login']:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Redirect directly to SSO instead of login page
            return redirect(url_for('auth_azure'))
        
        role = session.get('role')
        if role not in ['editor', 'admin']:
            if request.is_json:
                return jsonify({'error': 'נדרשות הרשאות עורך'}), 403
            flash('נדרשות הרשאות עורך או מנהל', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def editing_permission_required(f):
    """Decorator to check editing permissions with hativa access control"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Prevent redirect loops - check if we're already on auth routes
            if request.path in ['/auth/azure', '/auth/callback', '/login']:
                return jsonify({'error': 'נדרשת התחברות'}), 401
            # Redirect directly to SSO instead of login page
            return redirect(url_for('auth_azure'))
        
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
