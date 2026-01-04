#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maslul (Route/Track) repository for database operations.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from models import Maslul


class MaslulRepository(BaseRepository[Maslul]):
    """Repository for Maslul (Route) operations."""
    
    model_class = Maslul
    
    def get_all(self, hativa_id: Optional[int] = None, 
                include_inactive: bool = True) -> List[Maslul]:
        """
        Get all routes, optionally filtered by division.
        
        Args:
            hativa_id: Optional division ID filter
            include_inactive: If True, include inactive routes
            
        Returns:
            List of Maslul instances
        """
        stmt = select(Maslul).options(
            joinedload(Maslul.hativa)
        ).order_by(Maslul.name)
        
        if hativa_id is not None:
            stmt = stmt.where(Maslul.hativa_id == hativa_id)
        
        if not include_inactive:
            stmt = stmt.where(Maslul.is_active == 1)
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_active_only(self, hativa_id: Optional[int] = None) -> List[Maslul]:
        """Get only active routes."""
        return self.get_all(hativa_id=hativa_id, include_inactive=False)
    
    def create(self, hativa_id: int, name: str, description: str = "",
               sla_days: int = 45, stage_a_days: int = 10,
               stage_b_days: int = 15, stage_c_days: int = 10,
               stage_d_days: int = 10) -> Maslul:
        """
        Create a new route.
        
        Args:
            hativa_id: Division ID
            name: Route name
            description: Optional description
            sla_days: Total SLA days
            stage_a_days: Stage A duration
            stage_b_days: Stage B duration
            stage_c_days: Stage C duration
            stage_d_days: Stage D duration
            
        Returns:
            Created Maslul instance
        """
        maslul = Maslul(
            hativa_id=hativa_id,
            name=name,
            description=description,
            sla_days=sla_days,
            stage_a_days=stage_a_days,
            stage_b_days=stage_b_days,
            stage_c_days=stage_c_days,
            stage_d_days=stage_d_days,
            is_active=1
        )
        return self.add(maslul)
    
    def update_maslul(self, maslul_id: int, name: str, description: str,
                      sla_days: int, stage_a_days: int, stage_b_days: int,
                      stage_c_days: int, stage_d_days: int,
                      is_active: bool = True) -> bool:
        """
        Update route details.
        
        Args:
            maslul_id: Route ID
            name: New name
            description: New description
            sla_days: New SLA days
            stage_a_days: New stage A days
            stage_b_days: New stage B days
            stage_c_days: New stage C days
            stage_d_days: New stage D days
            is_active: Active status
            
        Returns:
            True if updated successfully
        """
        maslul = self.get_by_id(maslul_id)
        if not maslul:
            return False
        
        maslul.name = name
        maslul.description = description
        maslul.sla_days = sla_days
        maslul.stage_a_days = stage_a_days
        maslul.stage_b_days = stage_b_days
        maslul.stage_c_days = stage_c_days
        maslul.stage_d_days = stage_d_days
        maslul.is_active = 1 if is_active else 0
        self.session.flush()
        return True
    
    def deactivate(self, maslul_id: int) -> bool:
        """
        Soft delete (deactivate) a route.
        
        Args:
            maslul_id: Route ID
            
        Returns:
            True if deactivated successfully
        """
        maslul = self.get_by_id(maslul_id)
        if not maslul:
            return False
        
        maslul.is_active = 0
        self.session.flush()
        return True
    
    def activate(self, maslul_id: int) -> bool:
        """
        Reactivate a route.
        
        Args:
            maslul_id: Route ID
            
        Returns:
            True if activated successfully
        """
        maslul = self.get_by_id(maslul_id)
        if not maslul:
            return False
        
        maslul.is_active = 1
        self.session.flush()
        return True
    
    def get_by_hativa(self, hativa_id: int, active_only: bool = True) -> List[Maslul]:
        """
        Get all routes for a division.
        
        Args:
            hativa_id: Division ID
            active_only: If True, only return active routes
            
        Returns:
            List of Maslul instances
        """
        return self.get_all(hativa_id=hativa_id, include_inactive=not active_only)
