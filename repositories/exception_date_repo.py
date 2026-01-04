#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exception Date repository for database operations.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from .base import BaseRepository
from models import ExceptionDate, Vaada


class ExceptionDateRepository(BaseRepository[ExceptionDate]):
    """Repository for Exception Date operations."""
    
    model_class = ExceptionDate
    
    def get_exception_dates(self, include_past: bool = False) -> List[ExceptionDate]:
        """
        Get exception dates, optionally including past dates.
        
        Args:
            include_past: If True, include past dates.
            
        Returns:
            List of ExceptionDate instances.
        """
        stmt = select(ExceptionDate)
        if not include_past:
            today = date.today()
            stmt = stmt.where(ExceptionDate.exception_date >= today)
        
        stmt = stmt.order_by(ExceptionDate.exception_date.asc())
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def get_by_date(self, check_date: date) -> Optional[ExceptionDate]:
        """Get exception date by its date."""
        stmt = select(ExceptionDate).where(ExceptionDate.exception_date == check_date)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def is_exception_date(self, check_date: date) -> bool:
        """Check if a date is an exception date."""
        return self.get_by_date(check_date) is not None
    
    def can_delete(self, date_id: int) -> bool:
        """
        Check if an exception date can be deleted.
        It cannot be deleted if there are active (not deleted) committees linked to it.
        """
        stmt = select(func.count()).select_from(Vaada).where(
            and_(
                Vaada.exception_date_id == date_id,
                Vaada.is_deleted == 0
            )
        )
        result = self.session.execute(stmt)
        count = result.scalar()
        return count == 0
    
    def create(self, exception_date: date, description: str = "", date_type: str = "holiday") -> ExceptionDate:
        """Create a new exception date."""
        item = ExceptionDate(
            exception_date=exception_date,
            description=description,
            type=date_type
        )
        return self.add(item)
    
    def update_date(self, date_id: int, exception_date: date, description: str = "", date_type: str = "holiday") -> bool:
        """Update an exception date."""
        item = self.get_by_id(date_id)
        if not item:
            return False
        
        item.exception_date = exception_date
        item.description = description
        item.type = date_type
        self.session.flush()
        return True

    def is_work_day(self, check_date: date, work_days: Optional[List[int]] = None) -> bool:
        """
        Check if a date is a work day.
        
        Args:
            check_date: Date to check
            work_days: List of weekday integers (0-6) that are work days. 
                       If None, assumes standard Sun-Thu (6, 0, 1, 2, 3, 4) in Israel.
        """
        if work_days is None:
            # Default Israel work days: Sun-Thu (6, 0, 1, 2, 3, 4)
            work_days = [6, 0, 1, 2, 3, 4]
            
        if check_date.weekday() not in work_days:
            return False
            
        return not self.is_exception_date(check_date)
        
    def add_business_days(self, start_date: date, days_to_add: int, 
                          work_days: Optional[List[int]] = None) -> date:
        """Add business days to a date, skipping weekends and exception dates."""
        from datetime import timedelta
        current_date = start_date
        days_added = 0
        
        while days_added < days_to_add:
            current_date += timedelta(days=1)
            if self.is_work_day(current_date, work_days):
                days_added += 1
                
        return current_date
        
    def subtract_business_days(self, start_date: date, days_to_subtract: int,
                               work_days: Optional[List[int]] = None) -> date:
        """Subtract business days from a date, skipping weekends and exception dates."""
        from datetime import timedelta
        current_date = start_date
        days_subtracted = 0
        
        while days_subtracted < days_to_subtract:
            current_date -= timedelta(days=1)
            if self.is_work_day(current_date, work_days):
                days_subtracted += 1
                
        return current_date
