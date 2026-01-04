#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User repository for database operations.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from models import User, UserHativa, Hativa


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""
    
    model_class = User
    
    def get_all(self, include_deleted: bool = False) -> List[User]:
        """
        Get all users.
        
        Args:
            include_deleted: If True, include soft-deleted users
            
        Returns:
            List of User instances
        """
        stmt = select(User).options(
            joinedload(User.hativot)
        ).order_by(User.full_name)
        
        # Note: Not filtering by is_deleted for backward compatibility
        # The column may not exist in all database instances
        # if not include_deleted:
        #     stmt = stmt.where(or_(User.is_deleted == 0, User.is_deleted.is_(None)))
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username (case-insensitive).
        
        Args:
            username: Username to search
            
        Returns:
            User instance or None
        """
        stmt = select(User).options(
            joinedload(User.hativot)
        ).where(func.lower(User.username) == func.lower(username))
        
        result = self.session.execute(stmt)
        return result.unique().scalar_one_or_none()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email to search
            
        Returns:
            User instance or None
        """
        stmt = select(User).options(
            joinedload(User.hativot)
        ).where(func.lower(User.email) == func.lower(email))
        
        result = self.session.execute(stmt)
        return result.unique().scalar_one_or_none()
    
    def create(self, username: str, email: str, full_name: str,
               role: str = 'viewer', password_hash: Optional[str] = None,
               auth_source: str = 'local', ad_dn: Optional[str] = None,
               profile_picture: Optional[bytes] = None,
               hativa_ids: Optional[List[int]] = None) -> User:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            full_name: Full display name
            role: User role ('admin', 'editor', 'viewer')
            password_hash: Optional password hash
            auth_source: Auth source ('local' or 'ad')
            ad_dn: Optional AD distinguished name
            profile_picture: Optional profile picture bytes
            hativa_ids: Optional list of division IDs
            
        Returns:
            Created User instance
        """
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            password_hash=password_hash,
            auth_source=auth_source,
            ad_dn=ad_dn,
            profile_picture=profile_picture,
            is_active=1
        )
        self.session.add(user)
        self.session.flush()
        
        # Add hativa associations
        if hativa_ids:
            for hativa_id in hativa_ids:
                user_hativa = UserHativa(
                    user_id=user.user_id,
                    hativa_id=hativa_id
                )
                self.session.add(user_hativa)
            self.session.flush()
        
        return user
    
    def update_user(self, user_id: int, username: str, email: str,
                    full_name: str, role: str,
                    hativa_ids: Optional[List[int]] = None,
                    auth_source: Optional[str] = None) -> bool:
        """
        Update user information and hativa access.
        
        Args:
            user_id: User ID
            username: New username
            email: New email
            full_name: New full name
            role: New role
            hativa_ids: New list of division IDs
            auth_source: New auth source
            
        Returns:
            True if updated successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.username = username
        user.email = email
        user.full_name = full_name
        user.role = role
        if auth_source is not None:
            user.auth_source = auth_source
        
        # Update hativa associations if provided
        if hativa_ids is not None:
            # Delete existing associations
            from sqlalchemy import delete
            stmt = delete(UserHativa).where(UserHativa.user_id == user_id)
            self.session.execute(stmt)
            
            # Add new associations
            for hativa_id in hativa_ids:
                user_hativa = UserHativa(
                    user_id=user_id,
                    hativa_id=hativa_id
                )
                self.session.add(user_hativa)
        
        self.session.flush()
        return True
    
    def update_ad_user_info(self, user_id: int, email: str, full_name: str, 
                            profile_picture: Optional[bytes] = None) -> bool:
        """
        Update AD user information.
        
        Args:
            user_id: User ID
            email: New email
            full_name: New full name
            profile_picture: New profile picture bytes
            
        Returns:
            True if updated successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.email = email
        user.full_name = full_name
        if profile_picture is not None:
            user.profile_picture = profile_picture
            
        self.session.flush()
        return True
    
    def update_profile_picture(self, user_id: int, 
                                profile_picture: Optional[bytes]) -> bool:
        """
        Update user profile picture.
        
        Args:
            user_id: User ID
            profile_picture: Profile picture bytes
            
        Returns:
            True if updated successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.profile_picture = profile_picture
        self.session.flush()
        return True
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.last_login = datetime.now()
        self.session.flush()
        return True
    
    def toggle_status(self, user_id: int) -> bool:
        """
        Toggle user active status.
        
        Args:
            user_id: User ID
            
        Returns:
            True if toggled successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = 0 if user.is_active == 1 else 1
        self.session.flush()
        return True
    
    def soft_delete(self, user_id: int) -> bool:
        """
        Soft delete a user (sets is_active = 0).
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = 0
        self.session.flush()
        return True
    
    def restore(self, user_id: int) -> bool:
        """
        Restore a soft-deleted user (sets is_active = 1).
        
        Args:
            user_id: User ID
            
        Returns:
            True if restored successfully
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = 1
        self.session.flush()
        return True
    
    def hard_delete(self, user_id: int) -> bool:
        """
        Permanently delete a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        # Delete hativa associations first
        from sqlalchemy import delete
        stmt = delete(UserHativa).where(UserHativa.user_id == user_id)
        self.session.execute(stmt)
        
        # Delete user
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        self.session.delete(user)
        self.session.flush()
        return True
    
    def get_user_hativot(self, user_id: int) -> List[Hativa]:
        """
        Get all hativot that a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            List of Hativa instances
        """
        user = self.get_by_id(user_id)
        if not user:
            return []
        return list(user.hativot)
    
    def has_access_to_hativa(self, user_id: int, hativa_id: int) -> bool:
        """
        Check if user has access to a specific hativa.
        
        Args:
            user_id: User ID
            hativa_id: Division ID
            
        Returns:
            True if user has access
        """
        stmt = select(func.count()).select_from(UserHativa).where(
            UserHativa.user_id == user_id,
            UserHativa.hativa_id == hativa_id
        )
        count = self.session.execute(stmt).scalar() or 0
        return count > 0
    
    def add_hativa_access(self, user_id: int, hativa_id: int) -> bool:
        """
        Add hativa access to user.
        
        Args:
            user_id: User ID
            hativa_id: Division ID
            
        Returns:
            True if added successfully
        """
        # Check if already exists
        if self.has_access_to_hativa(user_id, hativa_id):
            return True
        
        user_hativa = UserHativa(
            user_id=user_id,
            hativa_id=hativa_id
        )
        self.session.add(user_hativa)
        self.session.flush()
        return True
    
    def remove_hativa_access(self, user_id: int, hativa_id: int) -> bool:
        """
        Remove hativa access from user.
        
        Args:
            user_id: User ID
            hativa_id: Division ID
            
        Returns:
            True if removed successfully
        """
        from sqlalchemy import delete
        stmt = delete(UserHativa).where(
            UserHativa.user_id == user_id,
            UserHativa.hativa_id == hativa_id
        )
        self.session.execute(stmt)
        self.session.flush()
        return True
    
    def username_exists(self, username: str, 
                        exclude_user_id: Optional[int] = None) -> bool:
        """
        Check if username already exists.
        
        Args:
            username: Username to check
            exclude_user_id: Optional user ID to exclude
            
        Returns:
            True if username exists
        """
        stmt = select(func.count()).select_from(User).where(
            func.lower(User.username) == func.lower(username)
        )
        
        if exclude_user_id is not None:
            stmt = stmt.where(User.user_id != exclude_user_id)
        
        count = self.session.execute(stmt).scalar() or 0
        return count > 0
    
    def email_exists(self, email: str,
                     exclude_user_id: Optional[int] = None) -> bool:
        """
        Check if email already exists.
        
        Args:
            email: Email to check
            exclude_user_id: Optional user ID to exclude
            
        Returns:
            True if email exists
        """
        stmt = select(func.count()).select_from(User).where(
            func.lower(User.email) == func.lower(email)
        )
        
        if exclude_user_id is not None:
            stmt = stmt.where(User.user_id != exclude_user_id)
        
        count = self.session.execute(stmt).scalar() or 0
        return count > 0
    
    def get_ad_users(self) -> List[User]:
        """Get all Active Directory users."""
        stmt = select(User).options(
            joinedload(User.hativot)
        ).where(User.auth_source == 'ad').order_by(User.full_name)
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_user_photo(self, user_id: int) -> Optional[bytes]:
        """
        Get user profile picture.
        
        Args:
            user_id: User ID
            
        Returns:
            Profile picture bytes or None
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        return user.profile_picture
