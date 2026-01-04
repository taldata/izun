#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Settings repository for database operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select

from .base import BaseRepository
from models import SystemSetting


class SettingsRepository(BaseRepository[SystemSetting]):
    """Repository for SystemSetting operations."""
    
    model_class = SystemSetting
    
    def get_setting(self, setting_key: str) -> Optional[str]:
        """
        Get a system setting value by key.
        
        Args:
            setting_key: Setting key
            
        Returns:
            Setting value or None
        """
        stmt = select(SystemSetting).where(SystemSetting.setting_key == setting_key)
        result = self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        return setting.setting_value if setting else None
    
    def get_int_setting(self, setting_key: str, default: int) -> int:
        """
        Get an integer system setting with fallback.
        
        Args:
            setting_key: Setting key
            default: Default value if not found or not a valid integer
            
        Returns:
            Setting value as integer
        """
        value = self.get_setting(setting_key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool_setting(self, setting_key: str, default: bool = False) -> bool:
        """
        Get a boolean system setting.
        
        Args:
            setting_key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value as boolean
        """
        value = self.get_setting(setting_key)
        if value is None:
            return default
        return value == '1' or value.lower() == 'true'
    
    def update_setting(self, setting_key: str, setting_value: str,
                       user_id: Optional[int] = None) -> bool:
        """
        Update a system setting.
        
        Args:
            setting_key: Setting key
            setting_value: New value
            user_id: User performing the update
            
        Returns:
            True if updated successfully
        """
        stmt = select(SystemSetting).where(SystemSetting.setting_key == setting_key)
        result = self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.setting_value = setting_value
            setting.updated_at = datetime.now()
            setting.updated_by = user_id
        else:
            # Create new setting
            setting = SystemSetting(
                setting_key=setting_key,
                setting_value=setting_value,
                updated_by=user_id
            )
            self.session.add(setting)
        
        self.session.flush()
        return True
    
    def get_constraint_settings(self) -> Dict[str, Any]:
        """
        Get all constraint-related settings for scheduling.
        
        Returns:
            Dictionary of constraint settings
        """
        return {
            'max_meetings_per_day': self.get_int_setting('max_meetings_per_day', 1),
            'max_weekly_meetings': self.get_int_setting('max_weekly_meetings', 3),
            'max_third_week_meetings': self.get_int_setting('max_third_week_meetings', 4),
            'max_requests_committee_date': self.get_int_setting('max_requests_committee_date', 100),
            'sla_days_before': self.get_int_setting('sla_days_before', 14),
        }
    
    def get_work_days(self) -> list:
        """
        Get configured work days.
        
        Returns:
            List of work day numbers (Python weekday: 0=Monday, 6=Sunday)
        """
        work_days_str = self.get_setting('work_days')
        if not work_days_str:
            return [0, 1, 2, 3, 4, 6]  # Mon-Fri + Sun (Israeli week)
        
        try:
            return [int(d.strip()) for d in work_days_str.split(',')]
        except (ValueError, TypeError):
            return [0, 1, 2, 3, 4, 6]
    
    def is_editing_allowed(self, user_role: str) -> bool:
        """
        Check if editing is allowed for a user role.
        
        Args:
            user_role: User's role
            
        Returns:
            True if editing is allowed
        """
        # Admins can always edit
        if user_role == 'admin':
            return True
        
        # Check if editing period is active
        editing_active = self.get_bool_setting('editing_period_active', True)
        return editing_active
    
    def get_all_settings(self) -> Dict[str, str]:
        """
        Get all system settings as a dictionary.
        
        Returns:
            Dictionary of setting_key -> setting_value
        """
        stmt = select(SystemSetting)
        result = self.session.execute(stmt)
        settings = result.scalars().all()
        return {s.setting_key: s.setting_value for s in settings}
    
    def get_calendar_settings(self) -> Dict[str, Any]:
        """
        Get calendar sync related settings.
        
        Returns:
            Dictionary of calendar settings
        """
        return {
            'calendar_sync_enabled': self.get_bool_setting('calendar_sync_enabled', True),
            'calendar_sync_email': self.get_setting('calendar_sync_email') or 'plan@innovationisrael.org.il',
            'calendar_sync_interval_hours': self.get_int_setting('calendar_sync_interval_hours', 1),
        }
    
    def get_ad_settings(self) -> Dict[str, Any]:
        """
        Get Active Directory related settings.
        
        Returns:
            Dictionary of AD settings
        """
        return {
            'ad_enabled': self.get_bool_setting('ad_enabled', False),
            'ad_server_url': self.get_setting('ad_server_url') or '',
            'ad_port': self.get_int_setting('ad_port', 636),
            'ad_use_ssl': self.get_bool_setting('ad_use_ssl', True),
            'ad_use_tls': self.get_bool_setting('ad_use_tls', False),
            'ad_base_dn': self.get_setting('ad_base_dn') or '',
            'ad_bind_dn': self.get_setting('ad_bind_dn') or '',
            'ad_bind_password': self.get_setting('ad_bind_password') or '',
            'ad_user_search_base': self.get_setting('ad_user_search_base') or '',
            'ad_user_search_filter': self.get_setting('ad_user_search_filter') or '(sAMAccountName={username})',
            'ad_group_search_base': self.get_setting('ad_group_search_base') or '',
            'ad_admin_group': self.get_setting('ad_admin_group') or '',
            'ad_manager_group': self.get_setting('ad_manager_group') or '',
            'ad_auto_create_users': self.get_bool_setting('ad_auto_create_users', True),
            'ad_default_hativa_id': self.get_setting('ad_default_hativa_id') or '',
            'ad_sync_on_login': self.get_bool_setting('ad_sync_on_login', True),
        }
    
    def get_recommendation_settings(self) -> Dict[str, int]:
        """
        Get committee recommendation scoring settings.
        
        Returns:
            Dictionary of recommendation settings
        """
        return {
            'rec_base_score': self.get_int_setting('rec_base_score', 100),
            'rec_best_bonus': self.get_int_setting('rec_best_bonus', 25),
            'rec_space_bonus': self.get_int_setting('rec_space_bonus', 10),
            'rec_sla_bonus': self.get_int_setting('rec_sla_bonus', 20),
            'rec_optimal_range_bonus': self.get_int_setting('rec_optimal_range_bonus', 15),
            'rec_no_events_bonus': self.get_int_setting('rec_no_events_bonus', 5),
            'rec_high_load_penalty': self.get_int_setting('rec_high_load_penalty', 15),
            'rec_medium_load_penalty': self.get_int_setting('rec_medium_load_penalty', 5),
            'rec_no_space_penalty': self.get_int_setting('rec_no_space_penalty', 50),
            'rec_no_sla_penalty': self.get_int_setting('rec_no_sla_penalty', 30),
            'rec_tight_sla_penalty': self.get_int_setting('rec_tight_sla_penalty', 10),
            'rec_far_future_penalty': self.get_int_setting('rec_far_future_penalty', 10),
            'rec_week_full_penalty': self.get_int_setting('rec_week_full_penalty', 20),
            'rec_optimal_range_start': self.get_int_setting('rec_optimal_range_start', 0),
            'rec_optimal_range_end': self.get_int_setting('rec_optimal_range_end', 30),
            'rec_far_future_threshold': self.get_int_setting('rec_far_future_threshold', 60),
        }
