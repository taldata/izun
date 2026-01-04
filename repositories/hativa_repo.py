#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hativa (Division) repository for database operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from models import Hativa, HativaDayConstraint, UserHativa


class HativaRepository(BaseRepository[Hativa]):
    """Repository for Hativa (Division) operations."""
    
    model_class = Hativa
    
    def get_all(self, include_inactive: bool = False) -> List[Hativa]:
        """
        Get all divisions, optionally including inactive ones.
        
        Args:
            include_inactive: If True, include inactive divisions
            
        Returns:
            List of Hativa instances ordered by name
        """
        stmt = select(Hativa).options(
            joinedload(Hativa.day_constraints)
        ).order_by(Hativa.name)
        
        if not include_inactive:
            stmt = stmt.where(Hativa.is_active == 1)
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_active_only(self) -> List[Hativa]:
        """Get only active divisions."""
        return self.get_all(include_inactive=False)
    
    def get_by_name(self, name: str) -> Optional[Hativa]:
        """
        Get division by name.
        
        Args:
            name: Division name
            
        Returns:
            Hativa instance or None
        """
        stmt = select(Hativa).where(Hativa.name == name)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def create(self, name: str, description: str = "", color: str = "#007bff") -> Hativa:
        """
        Create a new division.
        
        Args:
            name: Division name
            description: Optional description
            color: Color hex code
            
        Returns:
            Created Hativa instance
        """
        hativa = Hativa(
            name=name,
            description=description,
            color=color,
            is_active=1
        )
        return self.add(hativa)
    
    def update_hativa(self, hativa_id: int, name: str, description: str = "", 
                      color: str = "#007bff") -> bool:
        """
        Update division details.
        
        Args:
            hativa_id: Division ID
            name: New name
            description: New description
            color: New color
            
        Returns:
            True if updated successfully
        """
        hativa = self.get_by_id(hativa_id)
        if not hativa:
            return False
        
        hativa.name = name
        hativa.description = description
        hativa.color = color
        self.session.flush()
        return True
    
    def update_color(self, hativa_id: int, color: str) -> bool:
        """
        Update division color.
        
        Args:
            hativa_id: Division ID
            color: New color hex code
            
        Returns:
            True if updated successfully
        """
        hativa = self.get_by_id(hativa_id)
        if not hativa:
            return False
        
        hativa.color = color
        self.session.flush()
        return True
    
    def deactivate(self, hativa_id: int) -> bool:
        """
        Soft delete (deactivate) a division.
        
        Args:
            hativa_id: Division ID
            
        Returns:
            True if deactivated successfully
        """
        hativa = self.get_by_id(hativa_id)
        if not hativa:
            return False
        
        hativa.is_active = 0
        self.session.flush()
        return True
    
    def activate(self, hativa_id: int) -> bool:
        """
        Reactivate a division.
        
        Args:
            hativa_id: Division ID
            
        Returns:
            True if activated successfully
        """
        hativa = self.get_by_id(hativa_id)
        if not hativa:
            return False
        
        hativa.is_active = 1
        self.session.flush()
        return True
    
    def get_allowed_days(self, hativa_id: int) -> List[int]:
        """
        Get allowed days of week for a division.
        
        Args:
            hativa_id: Division ID
            
        Returns:
            List of day numbers (0=Monday, 6=Sunday)
        """
        stmt = select(HativaDayConstraint.day_of_week).where(
            HativaDayConstraint.hativa_id == hativa_id
        ).order_by(HativaDayConstraint.day_of_week)
        
        result = self.session.execute(stmt)
        return [row[0] for row in result.all()]
    
    def set_allowed_days(self, hativa_id: int, allowed_days: List[int]) -> bool:
        """
        Set allowed days of week for a division.
        
        Args:
            hativa_id: Division ID
            allowed_days: List of day numbers (0-6)
            
        Returns:
            True if set successfully
        """
        # Validate days
        for day in allowed_days:
            if day < 0 or day > 6:
                raise ValueError(f'Invalid day: {day}. Must be between 0 (Monday) and 6 (Sunday)')
        
        # Delete existing constraints
        from sqlalchemy import delete
        stmt = delete(HativaDayConstraint).where(
            HativaDayConstraint.hativa_id == hativa_id
        )
        self.session.execute(stmt)
        
        # Insert new constraints
        for day in allowed_days:
            constraint = HativaDayConstraint(
                hativa_id=hativa_id,
                day_of_week=day
            )
            self.session.add(constraint)
        
        self.session.flush()
        return True
    
    def is_day_allowed(self, hativa_id: int, day_of_week: int) -> bool:
        """
        Check if a specific day is allowed for a division.
        
        Args:
            hativa_id: Division ID
            day_of_week: Day number (0=Monday, 6=Sunday)
            
        Returns:
            True if day is allowed
        """
        allowed_days = self.get_allowed_days(hativa_id)
        
        # If no constraints set, allow all days
        if not allowed_days:
            return True
        
        return day_of_week in allowed_days
    
    def can_delete(self, hativa_id: int) -> tuple[bool, str, Dict[str, int]]:
        """
        Check if a division can be deleted (no related data).
        
        Args:
            hativa_id: Division ID
            
        Returns:
            Tuple of (can_delete, reason_message, counts_dict)
        """
        from sqlalchemy import func
        from models import Maslul, CommitteeType, Vaada, Event, UserHativa
        
        counts = {}
        
        # Count maslulim
        stmt = select(func.count()).select_from(Maslul).where(Maslul.hativa_id == hativa_id)
        counts['maslulim'] = self.session.execute(stmt).scalar() or 0
        
        # Count committee types
        stmt = select(func.count()).select_from(CommitteeType).where(CommitteeType.hativa_id == hativa_id)
        counts['committee_types'] = self.session.execute(stmt).scalar() or 0
        
        # Count vaadot
        stmt = select(func.count()).select_from(Vaada).where(Vaada.hativa_id == hativa_id,
                                                           (Vaada.is_deleted == 0) | (Vaada.is_deleted == None))
        counts['vaadot'] = self.session.execute(stmt).scalar() or 0
        
        # Count events through maslulim
        stmt = select(func.count()).select_from(Event).join(Maslul).where(
            Maslul.hativa_id == hativa_id,
            (Event.is_deleted == 0) | (Event.is_deleted == None)
        )
        counts['events'] = self.session.execute(stmt).scalar() or 0
        
        # Count users assigned to this hativa
        stmt = select(func.count()).select_from(UserHativa).where(UserHativa.hativa_id == hativa_id)
        counts['users'] = self.session.execute(stmt).scalar() or 0
        
        total = sum(counts.values())
        
        if total > 0:
            return False, f"Cannot delete: has {total} related items", counts
        
        return True, "Can be deleted", counts
    
    def hard_delete(self, hativa_id: int) -> tuple[bool, str]:
        """
        Permanently delete a division (only if no related data).
        
        Args:
            hativa_id: Division ID
            
        Returns:
            Tuple of (success, message)
        """
        can_delete, reason, _ = self.can_delete(hativa_id)
        
        if not can_delete:
            return False, reason
        
        # Delete day constraints first
        from sqlalchemy import delete
        stmt = delete(HativaDayConstraint).where(
            HativaDayConstraint.hativa_id == hativa_id
        )
        self.session.execute(stmt)
        
        # Delete the hativa
        hativa = self.get_by_id(hativa_id)
        if hativa:
            self.session.delete(hativa)
            self.session.flush()
            return True, "Division deleted successfully"
        
        return False, "Division not found"
