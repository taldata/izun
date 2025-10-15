#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Active Directory Authentication Service
Handles LDAP authentication and user synchronization with Active Directory
"""

import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError
from typing import Optional, Dict, List, Tuple
import logging

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
        
        # Load settings from database
        self._load_settings()
    
    def _load_settings(self):
        """Load AD configuration from database"""
        try:
            self.enabled = self.db.get_system_setting('ad_enabled') == '1'
            self.server_url = self.db.get_system_setting('ad_server_url') or ''
            self.base_dn = self.db.get_system_setting('ad_base_dn') or ''
            self.bind_dn = self.db.get_system_setting('ad_bind_dn') or ''
            self.bind_password = self.db.get_system_setting('ad_bind_password') or ''
            self.user_search_base = self.db.get_system_setting('ad_user_search_base') or self.base_dn
            self.user_search_filter = self.db.get_system_setting('ad_user_search_filter') or '(sAMAccountName={username})'
            self.group_search_base = self.db.get_system_setting('ad_group_search_base') or self.base_dn
            self.use_ssl = self.db.get_system_setting('ad_use_ssl') != '0'
            self.use_tls = self.db.get_system_setting('ad_use_tls') == '1'
            port_str = self.db.get_system_setting('ad_port')
            self.port = int(port_str) if port_str else (636 if self.use_ssl else 389)
        except Exception as e:
            logger.error(f"Error loading AD settings: {e}")
            self.enabled = False
    
    def reload_settings(self):
        """Reload AD settings from database"""
        self._load_settings()
    
    def is_enabled(self) -> bool:
        """Check if AD authentication is enabled"""
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
            # Check if user already exists
            existing_user = self.db.get_user_by_username(ad_user_info['username'])
            
            if existing_user:
                # Update existing user info from AD
                user_id = existing_user['user_id']
                self.db.update_ad_user_info(
                    user_id=user_id,
                    email=ad_user_info['email'],
                    full_name=ad_user_info['full_name']
                )
                logger.info(f"Updated AD user info for: {ad_user_info['username']}")
                return user_id
            else:
                # Create new user
                # AD users don't need a password hash in local DB
                user_id = self.db.create_ad_user(
                    username=ad_user_info['username'],
                    email=ad_user_info['email'],
                    full_name=ad_user_info['full_name'],
                    role=default_role,
                    hativa_id=hativa_id,
                    ad_dn=ad_user_info.get('dn', '')
                )
                logger.info(f"Created new AD user: {ad_user_info['username']}")
                return user_id
                
        except Exception as e:
            logger.error(f"Error syncing AD user to local DB: {e}")
            return None
    
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

