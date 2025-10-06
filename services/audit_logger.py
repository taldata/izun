#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit Logger Service - Centralized logging for all user actions

This service provides a clean interface for logging user activities
throughout the application.
"""

from typing import Optional, Dict, Any
from flask import session, request
from database import DatabaseManager


class AuditLogger:
    """Service for logging user actions and system events"""
    
    # Action types
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_VIEW = 'view'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_MOVE = 'move'
    ACTION_TOGGLE = 'toggle'
    ACTION_EXPORT = 'export'
    ACTION_IMPORT = 'import'
    ACTION_AUTO_SCHEDULE = 'auto_schedule'
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    
    # Entity types
    ENTITY_HATIVA = 'hativa'
    ENTITY_MASLUL = 'maslul'
    ENTITY_COMMITTEE_TYPE = 'committee_type'
    ENTITY_VAADA = 'vaada'
    ENTITY_EVENT = 'event'
    ENTITY_EXCEPTION_DATE = 'exception_date'
    ENTITY_USER = 'user'
    ENTITY_SYSTEM_SETTINGS = 'system_settings'
    ENTITY_SESSION = 'session'
    ENTITY_SCHEDULE = 'schedule'
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def log(self, action: str, entity_type: str, 
            entity_id: Optional[int] = None,
            entity_name: Optional[str] = None,
            details: Optional[str] = None,
            status: str = 'success',
            error_message: Optional[str] = None) -> int:
        """
        Log an action
        
        Args:
            action: Type of action (use ACTION_* constants)
            entity_type: Type of entity affected (use ENTITY_* constants)
            entity_id: ID of the entity (optional)
            entity_name: Name/description of the entity
            details: Additional details (optional)
            status: 'success' or 'error'
            error_message: Error message if status is 'error'
        
        Returns:
            log_id: ID of the created log entry
        """
        # Get user info from session
        user_id = session.get('user_id')
        username = session.get('username', 'Unknown')
        
        # Get request info
        ip_address = self._get_client_ip()
        user_agent = request.headers.get('User-Agent', '')[:200]  # Limit length
        
        return self.db.add_audit_log(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
    
    def log_success(self, action: str, entity_type: str,
                   entity_id: Optional[int] = None,
                   entity_name: Optional[str] = None,
                   details: Optional[str] = None) -> int:
        """Log a successful action"""
        return self.log(action, entity_type, entity_id, entity_name, details, 'success')
    
    def log_error(self, action: str, entity_type: str,
                 error_message: str,
                 entity_id: Optional[int] = None,
                 entity_name: Optional[str] = None,
                 details: Optional[str] = None) -> int:
        """Log a failed action"""
        return self.log(action, entity_type, entity_id, entity_name, details, 'error', error_message)
    
    def log_login(self, username: str, success: bool, reason: Optional[str] = None) -> int:
        """Log a login attempt"""
        return self.db.add_audit_log(
            user_id=None,
            username=username,
            action=self.ACTION_LOGIN if success else self.ACTION_LOGIN_FAILED,
            entity_type=self.ENTITY_SESSION,
            entity_name=username,
            details=reason,
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:200],
            status='success' if success else 'error',
            error_message=reason if not success else None
        )
    
    def log_logout(self, username: str) -> int:
        """Log a logout"""
        return self.log_success(
            self.ACTION_LOGOUT,
            self.ENTITY_SESSION,
            entity_name=username
        )
    
    # Convenience methods for common operations
    
    def log_hativa_created(self, hativa_id: int, name: str) -> int:
        """Log creation of a hativa"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_HATIVA,
            entity_id=hativa_id,
            entity_name=name
        )
    
    def log_hativa_updated(self, hativa_id: int, name: str, changes: Optional[str] = None) -> int:
        """Log update of a hativa"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_HATIVA,
            entity_id=hativa_id,
            entity_name=name,
            details=changes
        )
    
    def log_hativa_toggled(self, hativa_id: int, name: str, is_active: bool) -> int:
        """Log toggling of a hativa"""
        status = 'הופעלה' if is_active else 'הושבתה'
        return self.log_success(
            self.ACTION_TOGGLE,
            self.ENTITY_HATIVA,
            entity_id=hativa_id,
            entity_name=name,
            details=f'החטיבה {status}'
        )
    
    def log_maslul_created(self, maslul_id: int, name: str, hativa_name: str) -> int:
        """Log creation of a maslul"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_MASLUL,
            entity_id=maslul_id,
            entity_name=name,
            details=f'בחטיבת {hativa_name}'
        )
    
    def log_maslul_updated(self, maslul_id: int, name: str, changes: Optional[str] = None) -> int:
        """Log update of a maslul"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_MASLUL,
            entity_id=maslul_id,
            entity_name=name,
            details=changes
        )
    
    def log_maslul_deleted(self, maslul_id: int, name: str) -> int:
        """Log deletion of a maslul"""
        return self.log_success(
            self.ACTION_DELETE,
            self.ENTITY_MASLUL,
            entity_id=maslul_id,
            entity_name=name
        )
    
    def log_maslul_toggled(self, maslul_id: int, name: str, is_active: bool) -> int:
        """Log toggling of a maslul"""
        status = 'הופעל' if is_active else 'הושבת'
        return self.log_success(
            self.ACTION_TOGGLE,
            self.ENTITY_MASLUL,
            entity_id=maslul_id,
            entity_name=name,
            details=f'המסלול {status}'
        )
    
    def log_committee_type_created(self, ct_id: int, name: str, hativa_name: str) -> int:
        """Log creation of a committee type"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_COMMITTEE_TYPE,
            entity_id=ct_id,
            entity_name=name,
            details=f'בחטיבת {hativa_name}'
        )
    
    def log_committee_type_updated(self, ct_id: int, name: str) -> int:
        """Log update of a committee type"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_COMMITTEE_TYPE,
            entity_id=ct_id,
            entity_name=name
        )
    
    def log_committee_type_deleted(self, ct_id: int, name: str) -> int:
        """Log deletion of a committee type"""
        return self.log_success(
            self.ACTION_DELETE,
            self.ENTITY_COMMITTEE_TYPE,
            entity_id=ct_id,
            entity_name=name
        )
    
    def log_committee_type_toggled(self, ct_id: int, name: str, is_active: bool) -> int:
        """Log toggling of a committee type"""
        status = 'הופעל' if is_active else 'הושבת'
        return self.log_success(
            self.ACTION_TOGGLE,
            self.ENTITY_COMMITTEE_TYPE,
            entity_id=ct_id,
            entity_name=name,
            details=f'סוג הועדה {status}'
        )
    
    def log_vaada_created(self, vaada_id: int, committee_name: str, date: str) -> int:
        """Log creation of a vaada"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_VAADA,
            entity_id=vaada_id,
            entity_name=committee_name,
            details=f'תאריך: {date}'
        )
    
    def log_vaada_updated(self, vaada_id: int, committee_name: str, date: str) -> int:
        """Log update of a vaada"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_VAADA,
            entity_id=vaada_id,
            entity_name=committee_name,
            details=f'תאריך: {date}'
        )
    
    def log_vaada_moved(self, vaada_id: int, committee_name: str, old_date: str, new_date: str) -> int:
        """Log moving of a vaada"""
        return self.log_success(
            self.ACTION_MOVE,
            self.ENTITY_VAADA,
            entity_id=vaada_id,
            entity_name=committee_name,
            details=f'מ-{old_date} ל-{new_date}'
        )
    
    def log_vaada_deleted(self, vaada_id: int, committee_name: str) -> int:
        """Log deletion of a vaada"""
        return self.log_success(
            self.ACTION_DELETE,
            self.ENTITY_VAADA,
            entity_id=vaada_id,
            entity_name=committee_name
        )
    
    def log_event_created(self, event_id: int, name: str, committee_name: str) -> int:
        """Log creation of an event"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_EVENT,
            entity_id=event_id,
            entity_name=name,
            details=f'בועדה: {committee_name}'
        )
    
    def log_event_updated(self, event_id: int, name: str) -> int:
        """Log update of an event"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_EVENT,
            entity_id=event_id,
            entity_name=name
        )
    
    def log_event_moved(self, event_id: int, name: str, old_committee: str, new_committee: str) -> int:
        """Log moving of an event"""
        return self.log_success(
            self.ACTION_MOVE,
            self.ENTITY_EVENT,
            entity_id=event_id,
            entity_name=name,
            details=f'מ-{old_committee} ל-{new_committee}'
        )
    
    def log_event_deleted(self, event_id: int, name: str) -> int:
        """Log deletion of an event"""
        return self.log_success(
            self.ACTION_DELETE,
            self.ENTITY_EVENT,
            entity_id=event_id,
            entity_name=name
        )
    
    def log_user_created(self, user_id: int, username: str, role: str) -> int:
        """Log creation of a user"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_USER,
            entity_id=user_id,
            entity_name=username,
            details=f'תפקיד: {role}'
        )
    
    def log_user_updated(self, user_id: int, username: str) -> int:
        """Log update of a user"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_USER,
            entity_id=user_id,
            entity_name=username
        )
    
    def log_user_toggled(self, user_id: int, username: str, is_active: bool) -> int:
        """Log toggling of a user"""
        status = 'הופעל' if is_active else 'הושבת'
        return self.log_success(
            self.ACTION_TOGGLE,
            self.ENTITY_USER,
            entity_id=user_id,
            entity_name=username,
            details=f'המשתמש {status}'
        )
    
    def log_user_deleted(self, user_id: int, username: str) -> int:
        """Log deletion of a user"""
        return self.log_success(
            self.ACTION_DELETE,
            self.ENTITY_USER,
            entity_id=user_id,
            entity_name=username
        )
    
    def log_user_password_changed(self, user_id: int, username: str, by_admin: bool = False) -> int:
        """Log password change"""
        details = 'על ידי מנהל' if by_admin else 'על ידי המשתמש'
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_USER,
            entity_id=user_id,
            entity_name=username,
            details=f'שינוי סיסמה {details}'
        )
    
    def log_system_setting_updated(self, setting_key: str, old_value: str, new_value: str) -> int:
        """Log system setting update"""
        return self.log_success(
            self.ACTION_UPDATE,
            self.ENTITY_SYSTEM_SETTINGS,
            entity_name=setting_key,
            details=f'מ-"{old_value}" ל-"{new_value}"'
        )
    
    def log_auto_schedule_generated(self, year: int, month: int, count: int) -> int:
        """Log auto-schedule generation"""
        return self.log_success(
            self.ACTION_AUTO_SCHEDULE,
            self.ENTITY_SCHEDULE,
            entity_name=f'{year}-{month:02d}',
            details=f'נוצרו {count} הצעות ישיבות'
        )
    
    def log_schedule_approved(self, year: int, month: int, approved_count: int, total_count: int) -> int:
        """Log schedule approval"""
        return self.log_success(
            self.ACTION_APPROVE,
            self.ENTITY_SCHEDULE,
            entity_name=f'{year}-{month:02d}',
            details=f'אושרו {approved_count} מתוך {total_count} ישיבות'
        )
    
    def log_exception_date_added(self, date_id: int, date_str: str, description: str) -> int:
        """Log addition of exception date"""
        return self.log_success(
            self.ACTION_CREATE,
            self.ENTITY_EXCEPTION_DATE,
            entity_id=date_id,
            entity_name=date_str,
            details=description
        )
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address"""
        # Check for proxy headers first
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr

