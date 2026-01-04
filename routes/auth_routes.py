from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
import io
from services_init import db, ad_service, audit_logger, auth_manager
from auth import login_required
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login - Check if Azure AD is configured before redirecting"""
    # If user is already logged in, redirect to index to prevent loops
    if 'user_id' in session:
        current_app.logger.info(f"User {session.get('username')} already logged in, redirecting to index")
        return redirect(url_for('main.index'))
    
    # Check if Azure AD credentials are configured
    if not ad_service.azure_tenant_id or not ad_service.azure_client_id or not ad_service.azure_client_secret:
        # Azure AD not configured - provide options
        return render_template('errors/auth_error.html',
            title='אימות Azure AD לא מוגדר',
            message='המערכת דורשת הגדרת פרטי התחברות Azure AD כדי לפעול. אנא פנה למנהל המערכת.',
            error_type='warning',
            current_user=None)

    # Azure AD is configured - redirect to OAuth
    return redirect(url_for('auth.auth_azure'))

@auth_bp.route('/logout')
def logout():
    """User logout"""
    username = session.get('username', 'Unknown')
    
    # Clear flash messages explicitly to prevent them from persisting after session.clear()
    session.pop('_flashes', None)
    
    auth_manager.logout_user()
    
    # Log the logout
    audit_logger.log_logout(username)
    
    return redirect(url_for('auth.auth_azure'))

@auth_bp.route('/refresh_session')
@login_required
def refresh_session():
    """Refresh session data from database - useful after role changes"""
    if 'user_id' not in session:
        flash('נדרשת התחברות', 'error')
        return redirect(url_for('auth.auth_azure'))
    
    try:
        # Get fresh user data from database
        user = db.get_user_by_id(session['user_id'])
        
        if not user:
            flash('משתמש לא נמצא', 'error')
            auth_manager.logout_user()
            return redirect(url_for('auth.auth_azure'))
        
        if not user['is_active']:
            flash('חשבון המשתמש מושבת', 'error')
            auth_manager.logout_user()
            return redirect(url_for('auth.auth_azure'))
        
        # Update session with fresh data from database
        old_role = session.get('role')
        session['role'] = user['role']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['hativa_id'] = user.get('hativa_id')
        
        if old_role != user['role']:
            flash(f'הרשאות עודכנו: {old_role} → {user["role"]}', 'success')
        else:
            flash('Session עודכן בהצלחה', 'success')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error refreshing session: {e}", exc_info=True)
        flash(f'שגיאה בעדכון session: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@auth_bp.route('/auth/azure')
def auth_azure():
    """Redirect to Azure AD for authentication"""
    # If user is already logged in, redirect to index to prevent loops
    if 'user_id' in session:
        current_app.logger.info(f"User {session.get('username')} already logged in, redirecting to index")
        return redirect(url_for('main.index'))
    
    # Check if we're in a redirect loop (too many auth attempts)
    auth_attempts = session.get('auth_attempts', 0)
    if auth_attempts >= 3:
        current_app.logger.warning(f"Too many auth attempts ({auth_attempts}), preventing redirect loop")
        session['auth_attempts'] = 0  # Reset counter
        flash('יותר מדי ניסיונות התחברות. אנא נסה שוב מאוחר יותר.', 'error')
        return render_template('base.html', content="""
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="alert alert-danger text-center">
                    <h4><i class="bi bi-exclamation-triangle"></i> יותר מדי ניסיונות התחברות</h4>
                    <p>נדרשו יותר מדי ניסיונות התחברות. אנא נסה שוב מאוחר יותר.</p>
                    <p>אם הבעיה נמשכת, פנה למנהל המערכת.</p>
                </div>
            </div>
        </div>
        """)
    
    # Increment auth attempts counter
    session['auth_attempts'] = auth_attempts + 1
    session.modified = True

    # Check if Azure AD credentials are configured in .env
    if not ad_service.azure_tenant_id or not ad_service.azure_client_id or not ad_service.azure_client_secret:
        flash('אימות Azure AD לא מוגדר - נדרשת הגדרת פרטי התחברות בקובץ .env', 'error')
        return render_template('base.html', content="""
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="alert alert-danger text-center">
                    <h4><i class="bi bi-exclamation-triangle"></i> אימות Azure AD לא מוגדר</h4>
                    <p>המערכת דורשת הגדרת פרטי התחברות Azure AD כדי לפעול.</p>
                    <p>אנא פנה למנהל המערכת או הגדר את הפרטים בקובץ .env</p>
                    <div class="mt-3">
                        <small class="text-muted">קובץ .env.example נוצר בתיקיית הפרויקט</small>
                    </div>
                </div>
            </div>
        </div>
        """)

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session.permanent = True  # Make session persistent
    session['oauth_state'] = state
    session.modified = True  # Force session save

    current_app.logger.info(f"Generated state and saved to session: {state[:20]}...")

    # Get authorization URL
    auth_url = ad_service.get_azure_auth_url(state=state)

    if not auth_url:
        flash('שגיאה ביצירת קישור אימות Azure AD - בדוק הגדרות ב-.env', 'error')
        return render_template('base.html', content="""
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="alert alert-danger text-center">
                    <h4><i class="bi bi-exclamation-triangle"></i> שגיאה בהגדרות Azure AD</h4>
                    <p>לא ניתן ליצור קישור אימות. בדוק שהגדרות Azure AD תקינות.</p>
                </div>
            </div>
        </div>
        """)

    return redirect(auth_url)


@auth_bp.route('/auth/callback')
def auth_callback():
    """Handle Azure AD OAuth callback"""
    try:
        # Reset auth attempts counter on successful callback
        session.pop('auth_attempts', None)
        
        # Clear any existing flash messages
        session.pop('_flashes', None)
        
        if 'user_id' in session:
            current_app.logger.info(f"User {session.get('username')} already logged in, but proceeding with AD update")
        
        # Verify state parameter
        state = request.args.get('state')
        session_state = session.get('oauth_state')
        
        current_app.logger.info(f"Callback received - State from request: {state[:20] if state else 'None'}...")
        current_app.logger.info(f"State from session: {session_state[:20] if session_state else 'None'}...")
        
        if session_state and state != session_state:
            current_app.logger.warning("State mismatch detected but continuing (session lost during redirect)")
        
        session.pop('oauth_state', None)
        
        # Check for error from Azure AD
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', error)
            current_app.logger.error(f"Azure AD returned error: {error} - {error_description}")
            return render_template('errors/auth_error.html',
                title='שגיאת אימות Azure AD',
                message=error_description,
                show_retry=True,
                current_user=None)
    
        # Get authorization code
        auth_code = request.args.get('code')
        if not auth_code:
            current_app.logger.error("No authorization code received from Azure AD")
            return render_template('errors/auth_error.html',
                title='שגיאה באימות',
                message='לא התקבל קוד אימות מ-Azure AD',
                show_retry=True,
                current_user=None)
    
        # Authenticate with code
        current_app.logger.info("Authenticating with Azure AD code...")
        success, ad_user_info, message = ad_service.authenticate_with_code(auth_code)
        
        if not success or not ad_user_info:
            current_app.logger.error(f"Azure AD authentication failed: {message}")
            audit_logger.log_login(request.args.get('loginHint', 'unknown'), False, message)
            return render_template('errors/auth_error.html',
                title='שגיאה באימות',
                message=message,
                show_retry=True,
                current_user=None)
    
        # Validate user info from Azure AD
        username = ad_user_info.get('username') or ad_user_info.get('email', '').split('@')[0] if ad_user_info.get('email') else None
        if not username:
            current_app.logger.error("Cannot determine username from Azure AD user info")
            audit_logger.log_login('unknown', False, 'Missing username in Azure AD response')
            return render_template('errors/auth_error.html',
                title='שגיאה באימות',
                message='לא ניתן לקבוע שם משתמש מפרטי Azure AD',
                show_retry=True,
                current_user=None)
    
        email = ad_user_info.get('email', '')
        full_name = ad_user_info.get('full_name', '') or f"{ad_user_info.get('given_name', '')} {ad_user_info.get('surname', '')}".strip() or username
        
        current_app.logger.info(f"Azure AD auth successful. Username: {username}, Email: {email}, Full Name: {full_name}")
        
        # Check if user exists in local DB
        user = db.get_user_by_username_any_source(username)
        if not user and email:
            user = db.get_user_by_email(email)
        
        current_app.logger.info(f"User exists in DB: {user is not None}")
        
        if user:
            # User exists - check if active
            if not user['is_active']:
                audit_logger.log_login(username, False, 'User account disabled')
                return render_template('errors/auth_error.html',
                    title='חשבון מושבת',
                    message='חשבון המשתמש מושבת. אנא פנה למנהל המערכת.',
                    show_logout=True,
                    current_user=None)
        
            # Sync user info from Azure AD if configured
            if db.get_system_setting('ad_sync_on_login') == '1':
                ad_service.sync_user_to_local(
                    ad_user_info,
                    user['role'],
                    user.get('hativa_id')
                )
            
            user_id = user['user_id']
            role = user['role']
            hativa_id = user.get('hativa_id')
        else:
            # New Azure AD user - auto-create if configured
            auto_create = db.get_system_setting('ad_auto_create_users')
            current_app.logger.info(f"User not found. Auto-create setting: {auto_create}")
            
            if auto_create != '1':
                current_app.logger.warning(f"User {username} not authorized - auto-create disabled")
                audit_logger.log_login(username, False, 'Auto-create disabled for new user')
                return render_template('errors/auth_error.html',
                    title='משתמש לא מורשה',
                    message='משתמש לא מורשה להתחבר למערכת. אנא פנה למנהל המערכת כדי להוסיף את החשבון.',
                    error_type='warning',
                    show_logout=True,
                    current_user=None)
        
            # Determine role from Azure AD groups
            groups = ad_user_info.get('groups', [])
            role = ad_service.get_default_role_from_groups(groups)
            
            # Get default hativa
            default_hativa_str = db.get_system_setting('ad_default_hativa_id') or ''
            try:
                default_hativa_id = int(default_hativa_str) if default_hativa_str.strip() else None
            except ValueError:
                default_hativa_id = None
            
            if not email:
                current_app.logger.error(f"Missing email for user {username}")
                audit_logger.log_login(username, False, 'Missing email in Azure AD response')
                return render_template('errors/auth_error.html',
                    title='שגיאה באימות',
                    message='חסר אימייל בפרטי המשתמש מ-Azure AD',
                    show_retry=True,
                    current_user=None)
        
            # Create user
            try:
                user_id = ad_service.sync_user_to_local(
                    ad_user_info,
                    role,
                    default_hativa_id
                )
            except Exception as e:
                current_app.logger.error(f"Error creating user: {e}", exc_info=True)
                audit_logger.log_login(username, False, f'Error creating user: {str(e)}')
                return render_template('errors/auth_error.html',
                    title='שגיאה ביצירת חשבון',
                    message='אירעה שגיאה ביצירת חשבון המשתמש. אנא פנה למנהל המערכת.',
                    details=str(e),
                    show_logout=True,
                    current_user=None)
        
            if not user_id:
                current_app.logger.error(f"User creation failed")
                audit_logger.log_login(username, False, 'User creation returned None')
                return render_template('errors/auth_error.html',
                    title='שגיאה ביצירת חשבון',
                    message='שגיאה ביצירת חשבון משתמש. אנא פנה למנהל המערכת.',
                    show_logout=True,
                    current_user=None)
            
            hativa_id = default_hativa_id
        
        # Create session for Azure AD user
        session['user_id'] = user_id
        session['username'] = username
        session['role'] = role
        session['hativa_id'] = hativa_id
        session['full_name'] = full_name
        session['auth_source'] = 'azure_ad'
        
        # Update last login
        db.update_last_login(user_id)
        
        # Log successful login
        audit_logger.log_login(username, True, None)
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in auth_callback: {e}", exc_info=True)
        return render_template('errors/auth_error.html',
            title='שגיאה בתהליך האימות',
            message='אירעה שגיאה בלתי צפויה בתהליך האימות. אנא נסה שוב.',
            details=str(e),
            show_retry=True,
            current_user=None)

@auth_bp.route('/auth/user/photo')
def get_current_user_photo():
    """Get current user's profile photo"""
    try:
        if 'user_id' not in session:
            return redirect(url_for('static', filename='img/default-profile.png'))
        
        photo_data = db.get_user_photo(session['user_id'])
        if photo_data:
            return send_file(
                io.BytesIO(photo_data),
                mimetype='image/jpeg'
            )
        else:
            # Return 404 so the onerror handler in HTML can show the fallback
            return '', 404
    except Exception as e:
        current_app.logger.error(f"Error serving user photo: {e}")
        return '', 404
