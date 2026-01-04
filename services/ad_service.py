import msal
import requests
import jwt
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ADService:
    """Active Directory Authentication Service (Azure AD OAuth only)"""
    
    def __init__(self, db_manager):
        """
        Initialize AD Service
        
        Args:
            db_manager: DatabaseManager instance for storing AD settings and user mapping
        """
        self.db = db_manager
        self.enabled = False
        self.auth_method = 'oauth'
        
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
        return bool(self.azure_tenant_id and self.azure_client_id and self.azure_client_secret)
    
    def sync_user_to_local(self, ad_user_info: Dict, default_role: str = 'viewer', 
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
            
            # Extract profile picture
            profile_picture = ad_user_info.get('profile_picture')
            
            logger.info(f"Syncing user to local DB - Username: {username}, Email: {email}, Role: {default_role}, Hativa: {hativa_id}, Has Photo: {bool(profile_picture)}")
            
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
                    full_name=full_name,
                    profile_picture=profile_picture
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
                        ad_dn=ad_user_info.get('dn', ''),
                        profile_picture=profile_picture
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
            Role string ('admin', 'editor', 'viewer')
        """
        # Get configured group mappings from database
        admin_group = self.db.get_system_setting('ad_admin_group') or ''
        manager_group = self.db.get_system_setting('ad_manager_group') or ''
        
        # Check if user is in admin group
        if admin_group and any(admin_group.lower() in group.lower() for group in groups):
            return 'admin'
        
        # Check if user is in manager/editor group
        if manager_group and any(manager_group.lower() in group.lower() for group in groups):
            return 'editor'
        
        # Default to read-only viewer
        return 'viewer'
    
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

            # Always try to fetch profile picture if we have an access token
            # _get_user_info_from_token only returns basic info if id_token is present
            if "access_token" in result and not user_info.get('profile_picture'):
                try:
                    logger.info("Fetching profile picture from Graph API...")
                    headers = {
                        'Authorization': f'Bearer {result["access_token"]}',
                        'Content-Type': 'application/json'
                    }
                    photo_response = requests.get(
                        'https://graph.microsoft.com/v1.0/me/photo/$value',
                        headers=headers
                    )
                    if photo_response.status_code == 200:
                        user_info['profile_picture'] = photo_response.content
                        logger.info("Successfully fetched profile picture")
                    else:
                        logger.info(f"No profile photo found (status: {photo_response.status_code})")
                except Exception as pe:
                    logger.warning(f"Could not fetch profile photo: {pe}")
            
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
            
            # Fetch user photo
            try:
                photo_response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/photo/$value',
                    headers=headers
                )
                if photo_response.status_code == 200:
                    user_info['profile_picture'] = photo_response.content
                else:
                    logger.info(f"No profile photo found (status: {photo_response.status_code})")
            except Exception as pe:
                logger.warning(f"Could not fetch profile photo: {pe}")
            
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

    def get_app_only_token(self, scopes: List[str] = None) -> Optional[str]:
        """
        Get app-only access token for service-to-service authentication
        Used for calendar sync and other automated operations

        Args:
            scopes: List of permission scopes (e.g., ['https://graph.microsoft.com/.default'])
                   If None, defaults to Graph API with all app permissions

        Returns:
            Access token string or None on error
        """
        if not self.azure_client_id or not self.azure_tenant_id or not self.azure_client_secret:
            logger.error("Azure AD credentials not configured for app-only token")
            return None

        try:
            # Default to Graph API scope with all configured app permissions
            if scopes is None:
                scopes = ['https://graph.microsoft.com/.default']

            logger.info(f"Acquiring app-only token with scopes: {scopes}")

            msal_app = self._get_msal_app()

            # Acquire token using client credentials flow
            result = msal_app.acquire_token_for_client(scopes=scopes)

            if "error" in result:
                error_desc = result.get("error_description", result.get("error"))
                logger.error(f"App-only token error: {error_desc}")
                return None

            if "access_token" not in result:
                logger.error("No access token in app-only response")
                return None

            logger.info("Successfully acquired app-only access token")
            return result["access_token"]

        except Exception as e:
            logger.error(f"Error acquiring app-only token: {e}", exc_info=True)
            return None

