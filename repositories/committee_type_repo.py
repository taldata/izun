#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CommitteeType repository for database operations.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from models import CommitteeType, Hativa


class CommitteeTypeRepository(BaseRepository[CommitteeType]):
    """Repository for CommitteeType operations."""
    
    model_class = CommitteeType
    
    def get_all(self, hativa_id: Optional[int] = None, 
                include_inactive: bool = True) -> List[CommitteeType]:
        """
        Get all committee types, optionally filtered by division.
        
        Args:
            hativa_id: Optional division ID filter
            include_inactive: If True, include inactive types
            
        Returns:
            List of CommitteeType instances
        """
        stmt = select(CommitteeType).options(
            joinedload(CommitteeType.hativa)
        ).order_by(CommitteeType.name)
        
        if hativa_id is not None:
            stmt = stmt.where(CommitteeType.hativa_id == hativa_id)
        
        if not include_inactive:
            stmt = stmt.where(CommitteeType.is_active == 1)
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_active_only(self, hativa_id: Optional[int] = None) -> List[CommitteeType]:
        """Get only active committee types."""
        return self.get_all(hativa_id=hativa_id, include_inactive=False)
    
    def get_by_hativa_and_name(self, hativa_id: int, name: str) -> Optional[CommitteeType]:
        """
        Get committee type by division and name.
        
        Args:
            hativa_id: Division ID
            name: Committee type name
            
        Returns:
            CommitteeType instance or None
        """
        stmt = select(CommitteeType).where(
            CommitteeType.hativa_id == hativa_id,
            CommitteeType.name == name
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def create(self, hativa_id: int, name: str, scheduled_day: int,
               frequency: str = 'weekly', week_of_month: Optional[int] = None,
               description: str = "", is_operational: int = 0) -> CommitteeType:
        """
        Create a new committee type.
        
        Args:
            hativa_id: Division ID
            name: Committee type name
            scheduled_day: Day of week (0=Sunday, etc.)
            frequency: 'weekly' or 'monthly'
            week_of_month: Week number for monthly frequency
            description: Optional description
            is_operational: Whether it's an operational committee
            
        Returns:
            Created CommitteeType instance
        """
        committee_type = CommitteeType(
            hativa_id=hativa_id,
            name=name,
            scheduled_day=scheduled_day,
            frequency=frequency,
            week_of_month=week_of_month,
            description=description,
            is_operational=is_operational,
            is_active=1
        )
        return self.add(committee_type)
    
    def update_committee_type(self, committee_type_id: int, hativa_id: int,
                               name: str, scheduled_day: int,
                               frequency: str = 'weekly',
                               week_of_month: Optional[int] = None,
                               description: str = "",
                               is_operational: int = 0) -> bool:
        """
        Update committee type details.
        
        Args:
            committee_type_id: Committee type ID
            hativa_id: Division ID
            name: New name
            scheduled_day: New scheduled day
            frequency: New frequency
            week_of_month: New week of month
            description: New description
            is_operational: Whether it's operational
            
        Returns:
            True if updated successfully
        """
        ct = self.get_by_id(committee_type_id)
        if not ct:
            return False
        
        ct.hativa_id = hativa_id
        ct.name = name
        ct.scheduled_day = scheduled_day
        ct.frequency = frequency
        ct.week_of_month = week_of_month
        ct.description = description
        ct.is_operational = is_operational
        self.session.flush()
        return True
    
    def deactivate(self, committee_type_id: int) -> bool:
        """
        Soft delete (deactivate) a committee type.
        
        Args:
            committee_type_id: Committee type ID
            
        Returns:
            True if deactivated successfully
        """
        ct = self.get_by_id(committee_type_id)
        if not ct:
            return False
        
        ct.is_active = 0
        self.session.flush()
        return True
    
    def activate(self, committee_type_id: int) -> bool:
        """
        Reactivate a committee type.
        
        Args:
            committee_type_id: Committee type ID
            
        Returns:
            True if activated successfully
        """
        ct = self.get_by_id(committee_type_id)
        if not ct:
            return False
        
        ct.is_active = 1
        self.session.flush()
        return True
    
    def get_by_scheduled_day(self, scheduled_day: int, 
                              hativa_id: Optional[int] = None) -> List[CommitteeType]:
        """
        Get committee types by scheduled day.
        
        Args:
            scheduled_day: Day number
            hativa_id: Optional division filter
            
        Returns:
            List of matching CommitteeType instances
        """
        stmt = select(CommitteeType).where(
            CommitteeType.scheduled_day == scheduled_day,
            CommitteeType.is_active == 1
        )
        
        if hativa_id is not None:
            stmt = stmt.where(CommitteeType.hativa_id == hativa_id)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
