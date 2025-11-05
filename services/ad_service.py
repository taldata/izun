#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Active Directory Authentication Service
Handles LDAP and Azure AD OAuth authentication and user synchronization
Supports both traditional AD (LDAP) and Azure AD (OAuth 2.0/OIDC)
"""

import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError
from typing import Optional, Dict, List, Tuple
import logging
import msal
import requests
import jwt
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class ADService:
    """Active Directory Authentication Service"""
    
    def __init__(self, db_manager):
        """
        Initialize AD Service
        
        Args:
            db_manager: DatabaseManager instance for storing AD settings and user mapping
        """
        self.db = db_manager
        self.enabled = False
        self.auth_method = 'ldap'  # 'ldap' or 'oauth'
        
        # LDAP Settings
        self.server_url = None
        self.base_dn = None
        self.bind_dn = None
        self.bind_password = None
        self.user_search_base = None
        self.user_search_filter = None
        self.group_search_base = None
        self.use_ssl = True
        self.use_tls = False
        self.port = 636  # Default LDAPS port
        
        # Azure AD OAuth Settings
        self.azure_tenant_id = None
        self.azure_client_id = None
        self.azure_client_secret = None
        self.azure_authority = None
        self.azure_redirect_uri = None
        # Note: openid, profile, offline_access are added automatically by MSAL
        self.azure_scope = ['User.Read']
        
        # Load settings from database
        self._load_settings()
    
    def _load_settings(self):
        """Load AD configuration from environment variables and database"""
        try:
            # General settings from database
            self.enabled = self.db.get_system_setting('ad_enabled') == '1'
            self.auth_method = 'oauth'  # Always OAuth for Azure AD
            
            # LDAP Settings (not used for Azure AD, kept for compatibility)
            self.server_url = ''
            self.base_dn = ''
            self.bind_dn = ''
            self.bind_password = ''
            self.user_search_base = ''
            self.user_search_filter = '(sAMAccountName={username})'
            self.group_search_base = ''
            self.use_ssl = True
            self.use_tls = False
            self.port = 636
            
            # Azure AD OAuth Settings from environment variables (.env)
            self.azure_tenant_id = os.getenv('AZURE_TENANT_ID', '')
            self.azure_client_id = os.getenv('AZURE_CLIENT_ID', '')
            self.azure_client_secret = os.getenv('AZURE_CLIENT_SECRET', '')
            self.azure_redirect_uri = os.getenv('AZURE_REDIRECT_URI', '')
            
            if self.azure_tenant_id:
                self.azure_authority = f"https://login.microsoftonline.com/{self.azure_tenant_id}"
            
            logger.info(f"Azure AD settings loaded from .env: Tenant={self.azure_tenant_id[:8]}..., Client={self.azure_client_id[:8]}...")
        except Exception as e:
            logger.error(f"Error loading AD settings: {e}")
            self.enabled = False
    
    def reload_settings(self):
        """Reload AD settings from database"""
        self._load_settings()
    
    def is_enabled(self) -> bool:
        """Check if AD authentication is enabled"""
        # For Azure AD OAuth, check if credentials are configured
        if self.auth_method == 'oauth':
            return bool(self.azure_tenant_id and self.azure_client_id and self.azure_client_secret)
        # For LDAP, check traditional settings
        return self.enabled and bool(self.server_url)
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to AD server
        
        Returns:
            Tuple of (success, message)
        """
        if not self.server_url:
            return False, "כתובת שרת AD לא הוגדרה"
        
        try:
            server = self._create_server()
            conn = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True,
                raise_exceptions=True
            )
            conn.unbind()
            return True, "החיבור ל-Active Directory הצליח"
        except LDAPBindError as e:
            # Check if it's an invalid credentials error
            if 'invalidCredentials' in str(e) or '49' in str(e):
                return False, "פרטי התחברות לשרת AD שגויים"
            return False, f"שגיאה בהתחברות לשרת AD: {str(e)}"
        except Exception as e:
            return False, f"שגיאת חיבור: {str(e)}"
    
    def _create_server(self) -> Server:
        """Create LDAP server object"""
        return Server(
            self.server_url,
            port=self.port,
            use_ssl=self.use_ssl,
            get_info=ALL
        )
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate user against Active Directory
        
        Args:
            username: Username (sAMAccountName)
            password: User password
            
        Returns:
            Tuple of (success, user_info_dict, message)
        """
        if not self.is_enabled():
            return False, None, "אימות Active Directory אינו פעיל"
        
        if not username or not password:
            return False, None, "שם משתמש וסיסמה נדרשים"
        
        try:
            # First, bind as service account to search for user
            server = self._create_server()
            
            # Search for user
            search_filter = self.user_search_filter.format(username=username)
            logger.info(f"Searching for user: {username} with filter: {search_filter}")
            
            with Connection(server, user=self.bind_dn, password=self.bind_password, auto_bind=True) as conn:
                # Apply STARTTLS if configured
                if self.use_tls and not self.use_ssl:
                    conn.start_tls()
                
                # Search for user
                conn.search(
                    search_base=self.user_search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['sAMAccountName', 'mail', 'displayName', 'cn', 'memberOf', 'givenName', 'sn']
                )
                
                if not conn.entries:
                    logger.warning(f"User not found in AD: {username}")
                    return False, None, "משתמש לא נמצא ב-Active Directory"
                
                # Get first entry
                user_entry = conn.entries[0]
                user_dn = user_entry.entry_dn
                
                logger.info(f"Found user DN: {user_dn}")
            
            # Now try to bind as the user to verify password
            with Connection(server, user=user_dn, password=password, auto_bind=True) as user_conn:
                if self.use_tls and not self.use_ssl:
                    user_conn.start_tls()
                
                # If we got here, authentication succeeded
                logger.info(f"AD authentication successful for user: {username}")
                
                # Extract user information
                user_info = {
                    'username': str(user_entry.sAMAccountName),
                    'email': str(user_entry.mail) if user_entry.mail else f"{username}@domain.local",
                    'full_name': str(user_entry.displayName) if user_entry.displayName else str(user_entry.cn),
                    'given_name': str(user_entry.givenName) if user_entry.givenName else '',
                    'surname': str(user_entry.sn) if user_entry.sn else '',
                    'dn': user_dn,
                    'groups': [str(group) for group in user_entry.memberOf] if user_entry.memberOf else []
                }
                
                return True, user_info, "אימות הצליח"
                
        except LDAPBindError as e:
            # Check if it's an invalid credentials error
            if 'invalidCredentials' in str(e) or '49' in str(e):
                logger.warning(f"Invalid credentials for AD user: {username}")
                return False, None, "שם משתמש או סיסמה שגויים"
            logger.error(f"LDAP bind error for user {username}: {e}")
            return False, None, "שגיאה באימות מול Active Directory"
        except LDAPException as e:
            logger.error(f"LDAP error during authentication: {e}")
            return False, None, f"שגיאת LDAP: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during AD authentication: {e}")
            return False, None, f"שגיאה לא צפויה: {str(e)}"
    
    def search_users(self, search_term: str, limit: int = 50) -> List[Dict]:
        """
        Search for users in Active Directory
        
        Args:
            search_term: Search term (partial username, name, or email)
            limit: Maximum number of results
            
        Returns:
            List of user dictionaries
        """
        if not self.is_enabled():
            return []
        
        try:
            server = self._create_server()
            
            # Build search filter
            search_filter = f"(&(objectClass=user)(objectCategory=person)(|(sAMAccountName=*{search_term}*)(mail=*{search_term}*)(displayName=*{search_term}*)))"
            
            with Connection(server, user=self.bind_dn, password=self.bind_password, auto_bind=True) as conn:
                if self.use_tls and not self.use_ssl:
                    conn.start_tls()
                
                conn.search(
                    search_base=self.user_search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['sAMAccountName', 'mail', 'displayName', 'cn'],
                    size_limit=limit
                )
                
                users = []
                for entry in conn.entries:
                    users.append({
                        'username': str(entry.sAMAccountName),
                        'email': str(entry.mail) if entry.mail else '',
                        'full_name': str(entry.displayName) if entry.displayName else str(entry.cn),
                        'dn': entry.entry_dn
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error searching AD users: {e}")
            return []
    
    def get_user_groups(self, username: str) -> List[str]:
        """
        Get groups for a user
        
        Args:
            username: sAMAccountName
            
        Returns:
            List of group DNs
        """
        if not self.is_enabled():
            return []
        
        try:
            server = self._create_server()
            search_filter = self.user_search_filter.format(username=username)
            
            with Connection(server, user=self.bind_dn, password=self.bind_password, auto_bind=True) as conn:
                if self.use_tls and not self.use_ssl:
                    conn.start_tls()
                
                conn.search(
                    search_base=self.user_search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['memberOf']
                )
                
                if conn.entries:
                    entry = conn.entries[0]
                    return [str(group) for group in entry.memberOf] if entry.memberOf else []
                
                return []
                
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []
    
    def sync_user_to_local(self, ad_user_info: Dict, default_role: str = 'user', 
                          hativa_id: Optional[int] = None) -> Optional[int]:
        """
        Sync AD user to local database
        
        Args:
            ad_user_info: User info from AD
            default_role: Default role for new users
            hativa_id: Division ID to assign
            
        Returns:
            User ID or None on error
        """
        try:
            username = ad_user_info.get('username')
            email = ad_user_info.get('email', '')
            full_name = ad_user_info.get('full_name', '')
            
            logger.info(f"Syncing user to local DB - Username: {username}, Email: {email}, Role: {default_role}, Hativa: {hativa_id}")
            
            # Validate required fields
            if not username:
                logger.error("Cannot sync user: username is missing from ad_user_info")
                raise ValueError("שם משתמש חסר")
            
            if not email:
                logger.error(f"Cannot sync user {username}: email is missing from ad_user_info")
                raise ValueError("אימייל חסר")
            
            # Check if user already exists (by username OR email)
            existing_user = self.db.get_user_by_username(username)
            if not existing_user:
                # Also check by email (in case username changed but email same)
                existing_user = self.db.get_user_by_email(email)
            
            if existing_user:
                # Update existing user info from AD
                user_id = existing_user['user_id']
                logger.info(f"User exists with ID: {user_id}. Updating info...")
                self.db.update_ad_user_info(
                    user_id=user_id,
                    email=email,
                    full_name=full_name
                )
                logger.info(f"Updated AD user info for: {username}")
                return user_id
            else:
                # Create new user
                logger.info(f"User does not exist. Creating new user with username={username}, email={email}, role={default_role}, hativa_id={hativa_id}")
                # AD users don't need a password hash in local DB
                try:
                    user_id = self.db.create_ad_user(
                        username=username,
                        email=email,
                        full_name=full_name,
                        role=default_role,
                        hativa_id=hativa_id,
                        ad_dn=ad_user_info.get('dn', '')
                    )
                    if not user_id:
                        logger.error(f"create_ad_user returned None for username={username}")
                        raise ValueError("יצירת משתמש נכשלה - לא התקבל ID משתמש")
                    logger.info(f"Created new AD user: {username} with ID: {user_id}")
                    return user_id
                except Exception as db_error:
                    logger.error(f"Database error creating user {username}: {db_error}", exc_info=True)
                    raise ValueError(f"שגיאה בבסיס הנתונים: {str(db_error)}")
                
        except ValueError as ve:
            # Re-raise validation errors as-is
            logger.error(f"Validation error syncing user: {ve}")
            raise
        except Exception as e:
            logger.error(f"Error syncing AD user to local DB: {e}", exc_info=True)
            raise ValueError(f"שגיאה בסנכרון משתמש: {str(e)}")
    
    def get_default_role_from_groups(self, groups: List[str]) -> str:
        """
        Determine user role based on AD group membership
        
        Args:
            groups: List of group DNs
            
        Returns:
            Role string ('admin', 'manager', 'user')
        """
        # Get configured group mappings from database
        admin_group = self.db.get_system_setting('ad_admin_group') or ''
        manager_group = self.db.get_system_setting('ad_manager_group') or ''
        
        # Check if user is in admin group
        if admin_group and any(admin_group.lower() in group.lower() for group in groups):
            return 'admin'
        
        # Check if user is in manager group
        if manager_group and any(manager_group.lower() in group.lower() for group in groups):
            return 'manager'
        
        # Default to regular user
        return 'user'
    
    # ============================================================================
    # Azure AD OAuth 2.0 Methods
    # ============================================================================
    
    def get_azure_auth_url(self, state: str = None) -> str:
        """
        Get Azure AD authorization URL for OAuth flow
        
        Args:
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        if not self.azure_client_id or not self.azure_tenant_id:
            logger.error("Azure AD not configured properly")
            return None
        
        logger.info(f"Creating Azure AD auth URL with redirect_uri: {self.azure_redirect_uri}")
        logger.info(f"Using scopes: {self.azure_scope}")
        
        msal_app = self._get_msal_app()
        
        # Request parameters for Azure AD OAuth
        auth_url = msal_app.get_authorization_request_url(
            scopes=self.azure_scope,
            state=state,
            redirect_uri=self.azure_redirect_uri,
            response_type='code',
            response_mode='query',
            prompt='select_account'
        )
        
        logger.info(f"Generated auth URL: {auth_url[:150]}...")
        
        return auth_url
    
    def _get_msal_app(self):
        """Create MSAL confidential client application"""
        return msal.ConfidentialClientApplication(
            client_id=self.azure_client_id,
            client_credential=self.azure_client_secret,
            authority=self.azure_authority
        )
    
    def authenticate_with_code(self, auth_code: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate user with authorization code from OAuth flow
        
        Args:
            auth_code: Authorization code from callback
            
        Returns:
            Tuple of (success, user_info_dict, message)
        """
        # Check if Azure AD credentials are configured
        if not self.azure_tenant_id or not self.azure_client_id or not self.azure_client_secret:
            return False, None, "אימות Azure AD לא מוגדר - חסרים פרטים ב-.env"
        
        try:
            msal_app = self._get_msal_app()
            
            # Exchange code for token
            result = msal_app.acquire_token_by_authorization_code(
                code=auth_code,
                scopes=self.azure_scope,
                redirect_uri=self.azure_redirect_uri
            )
            
            if "error" in result:
                error_desc = result.get("error_description", result.get("error"))
                logger.error(f"Azure AD token error: {error_desc}")
                return False, None, f"שגיאה באימות: {error_desc}"
            
            if "access_token" not in result:
                logger.error("No access token in Azure AD response")
                return False, None, "לא התקבל טוקן גישה"
            
            # Get user info from token or Graph API
            user_info = self._get_user_info_from_token(result)
            
            if not user_info:
                return False, None, "שגיאה בקבלת פרטי משתמש"
            
            return True, user_info, "אימות הצליח"
            
        except Exception as e:
            logger.error(f"Azure AD authentication error: {e}")
            return False, None, f"שגיאה באימות: {str(e)}"
    
    def _get_user_info_from_token(self, token_response: Dict) -> Optional[Dict]:
        """
        Extract user information from token response
        
        Args:
            token_response: MSAL token response
            
        Returns:
            User info dictionary
        """
        try:
            logger.info("Extracting user info from token response...")
            
            # Decode ID token (if present)
            if "id_token" in token_response:
                logger.info("ID token found. Decoding...")
                id_token = token_response["id_token"]
                # Decode without verification (already verified by MSAL)
                claims = jwt.decode(id_token, options={"verify_signature": False})
                
                logger.info(f"Token claims: {list(claims.keys())}")
                
                user_info = {
                    'username': claims.get('preferred_username', claims.get('upn', claims.get('email', ''))).split('@')[0],
                    'email': claims.get('preferred_username', claims.get('upn', claims.get('email', ''))),
                    'full_name': claims.get('name', ''),
                    'given_name': claims.get('given_name', ''),
                    'surname': claims.get('family_name', ''),
                    'oid': claims.get('oid', ''),  # Object ID in Azure AD
                    'tid': claims.get('tid', ''),  # Tenant ID
                    'groups': []
                }
                
                logger.info(f"Extracted user info: username={user_info['username']}, email={user_info['email']}, full_name={user_info['full_name']}")
                return user_info
            
            # Fallback: Use Graph API to get user info
            if "access_token" in token_response:
                logger.info("No ID token. Using Graph API to get user info...")
                return self._get_user_from_graph(token_response["access_token"])
            
            logger.error("No ID token or access token found in response")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting user info from token: {e}", exc_info=True)
            return None
    
    def _get_user_from_graph(self, access_token: str) -> Optional[Dict]:
        """
        Get user information from Microsoft Graph API
        
        Args:
            access_token: OAuth access token
            
        Returns:
            User info dictionary
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get user profile
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Graph API error: {response.status_code} - {response.text}")
                return None
            
            user_data = response.json()
            
            user_info = {
                'username': user_data.get('userPrincipalName', '').split('@')[0],
                'email': user_data.get('userPrincipalName', user_data.get('mail', '')),
                'full_name': user_data.get('displayName', ''),
                'given_name': user_data.get('givenName', ''),
                'surname': user_data.get('surname', ''),
                'oid': user_data.get('id', ''),
                'groups': []
            }
            
            # Optionally get group membership
            try:
                groups_response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/memberOf',
                    headers=headers
                )
                if groups_response.status_code == 200:
                    groups_data = groups_response.json()
                    user_info['groups'] = [g.get('displayName', '') for g in groups_data.get('value', [])]
            except Exception as ge:
                logger.warning(f"Could not fetch groups: {ge}")
            
            return user_info
            
        except Exception as e:
            logger.error(f"Error calling Graph API: {e}")
            return None
    
    def test_azure_connection(self) -> Tuple[bool, str]:
        """
        Test Azure AD configuration
        
        Returns:
            Tuple of (success, message)
        """
        if not self.azure_client_id or not self.azure_tenant_id:
            return False, "הגדרות Azure AD חסרות (Tenant ID או Client ID)"
        
        if not self.azure_client_secret:
            return False, "Client Secret חסר"
        
        if not self.azure_redirect_uri:
            return False, "Redirect URI חסר"
        
        try:
            # Try to create MSAL app and get auth URL
            msal_app = self._get_msal_app()
            auth_url = msal_app.get_authorization_request_url(
                scopes=self.azure_scope,
                redirect_uri=self.azure_redirect_uri
            )
            
            if auth_url:
                return True, "הגדרות Azure AD תקינות"
            else:
                return False, "לא ניתן ליצור URL אימות"
                
        except Exception as e:
            return False, f"שגיאה בבדיקת הגדרות: {str(e)}"

