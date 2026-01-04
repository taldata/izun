#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vaada (Committee Meeting) repository for database operations.
"""

from datetime import date, datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from models import Vaada, CommitteeType, Hativa, ExceptionDate


class VaadaRepository(BaseRepository[Vaada]):
    """Repository for Vaada (Committee Meeting) operations."""
    
    model_class = Vaada
    
    def get_all(self, hativa_id: Optional[int] = None,
                start_date: Optional[date] = None,
                end_date: Optional[date] = None,
                include_deleted: bool = False) -> List[Vaada]:
        """
        Get all committee meetings with optional filters.
        
        Args:
            hativa_id: Optional division ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            include_deleted: If True, include soft-deleted meetings
            
        Returns:
            List of Vaada instances
        """
        stmt = select(Vaada).options(
            joinedload(Vaada.committee_type),
            joinedload(Vaada.hativa),
            joinedload(Vaada.events)
        ).order_by(Vaada.vaada_date)
        
        if hativa_id is not None:
            stmt = stmt.where(Vaada.hativa_id == hativa_id)
        
        if start_date is not None:
            stmt = stmt.where(Vaada.vaada_date >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(Vaada.vaada_date <= end_date)
        
        if not include_deleted:
            stmt = stmt.where(or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None)))
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_by_date(self, vaada_date: date, include_deleted: bool = False) -> List[Vaada]:
        """
        Get committee meetings for a specific date.
        
        Args:
            vaada_date: Date to query
            include_deleted: If True, include soft-deleted meetings
            
        Returns:
            List of Vaada instances
        """
        stmt = select(Vaada).options(
            joinedload(Vaada.committee_type),
            joinedload(Vaada.hativa)
        ).where(Vaada.vaada_date == vaada_date)
        
        if not include_deleted:
            stmt = stmt.where(or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None)))
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_by_date_and_hativa(self, vaada_date: date, hativa_id: int) -> List[Vaada]:
        """
        Get committee meetings for a specific date and division.
        
        Args:
            vaada_date: Date to query
            hativa_id: Division ID
            
        Returns:
            List of Vaada instances
        """
        stmt = select(Vaada).options(
            joinedload(Vaada.committee_type),
            joinedload(Vaada.hativa)
        ).where(
            Vaada.vaada_date == vaada_date,
            Vaada.hativa_id == hativa_id,
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def create(self, committee_type_id: int, hativa_id: int, vaada_date: date,
               notes: str = "", start_time: Optional[str] = None,
               end_time: Optional[str] = None) -> Vaada:
        """
        Create a new committee meeting.
        
        Args:
            committee_type_id: Committee type ID
            hativa_id: Division ID
            vaada_date: Meeting date
            notes: Optional notes
            start_time: Optional start time (HH:MM)
            end_time: Optional end time (HH:MM)
            
        Returns:
            Created Vaada instance
        """
        vaada = Vaada(
            committee_type_id=committee_type_id,
            hativa_id=hativa_id,
            vaada_date=vaada_date,
            notes=notes,
            start_time=start_time or "09:00",
            end_time=end_time or "15:00",
            is_deleted=0
        )
        return self.add(vaada)
    
    def update_vaada(self, vaadot_id: int, committee_type_id: int,
                     hativa_id: int, vaada_date: date,
                     exception_date_id: Optional[int] = None,
                     notes: str = "", start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> bool:
        """
        Update committee meeting details.
        
        Args:
            vaadot_id: Meeting ID
            committee_type_id: Committee type ID
            hativa_id: Division ID
            vaada_date: Meeting date
            exception_date_id: Optional exception date ID
            notes: Notes
            start_time: Start time
            end_time: End time
            
        Returns:
            True if updated successfully
        """
        vaada = self.get_by_id(vaadot_id)
        if not vaada:
            return False
        
        vaada.committee_type_id = committee_type_id
        vaada.hativa_id = hativa_id
        vaada.vaada_date = vaada_date
        vaada.exception_date_id = exception_date_id
        vaada.notes = notes
        if start_time is not None:
            vaada.start_time = start_time
        if end_time is not None:
            vaada.end_time = end_time
        
        self.session.flush()
        return True
    
    def soft_delete(self, vaadot_id: int, user_id: Optional[int] = None) -> bool:
        """
        Soft delete a committee meeting.
        
        Args:
            vaadot_id: Meeting ID
            user_id: User performing the delete
            
        Returns:
            True if deleted successfully
        """
        vaada = self.get_by_id(vaadot_id)
        if not vaada:
            return False
        
        vaada.is_deleted = 1
        vaada.deleted_at = datetime.now()
        vaada.deleted_by = user_id
        self.session.flush()
        return True
    
    def restore(self, vaadot_id: int) -> bool:
        """
        Restore a soft-deleted committee meeting.
        
        Args:
            vaadot_id: Meeting ID
            
        Returns:
            True if restored successfully
        """
        vaada = self.get_by_id(vaadot_id)
        if not vaada:
            return False
        
        vaada.is_deleted = 0
        vaada.deleted_at = None
        vaada.deleted_by = None
        self.session.flush()
        return True
    
    def hard_delete(self, vaadot_id: int) -> bool:
        """
        Permanently delete a committee meeting.
        
        Args:
            vaadot_id: Meeting ID
            
        Returns:
            True if deleted successfully
        """
        vaada = self.get_by_id(vaadot_id)
        if not vaada:
            return False
        
        self.session.delete(vaada)
        self.session.flush()
        return True
    
    def get_deleted(self, hativa_id: Optional[int] = None) -> List[Vaada]:
        """
        Get all soft-deleted committee meetings.
        
        Args:
            hativa_id: Optional division filter
            
        Returns:
            List of deleted Vaada instances
        """
        stmt = select(Vaada).options(
            joinedload(Vaada.committee_type),
            joinedload(Vaada.hativa)
        ).where(Vaada.is_deleted == 1).order_by(Vaada.deleted_at.desc())
        
        if hativa_id is not None:
            stmt = stmt.where(Vaada.hativa_id == hativa_id)
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def count_meetings_on_date(self, vaada_date: date, is_operational: Optional[bool] = None) -> int:
        """
        Count meetings on a specific date.
        
        Args:
            vaada_date: Date to check
            is_operational: If True, count only operational committees. 
                            If False, count only non-operational.
                            If None, count all.
            
        Returns:
            Number of meetings
        """
        stmt = select(func.count()).select_from(Vaada).join(CommitteeType).where(
            Vaada.vaada_date == vaada_date,
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        
        if is_operational is True:
            stmt = stmt.where(CommitteeType.is_operational == 1)
        elif is_operational is False:
            stmt = stmt.where(or_(CommitteeType.is_operational == 0, CommitteeType.is_operational.is_(None)))
            
        return self.session.execute(stmt).scalar() or 0
    
    def count_in_range(self, start_date: date, end_date: date, is_operational: Optional[bool] = None) -> int:
        """
        Count meetings in a date range.
        
        Args:
            start_date: Range start
            end_date: Range end
            is_operational: Optional operational filter
            
        Returns:
            Number of meetings
        """
        stmt = select(func.count()).select_from(Vaada).join(CommitteeType).where(
            Vaada.vaada_date >= start_date,
            Vaada.vaada_date <= end_date,
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        
        if is_operational is True:
            stmt = stmt.where(CommitteeType.is_operational == 1)
        elif is_operational is False:
            stmt = stmt.where(or_(CommitteeType.is_operational == 0, CommitteeType.is_operational.is_(None)))
            
        return self.session.execute(stmt).scalar() or 0
    
    def is_date_available(self, vaada_date: date, 
                          exclude_vaadot_id: Optional[int] = None) -> bool:
        """
        Check if a date is available for a new meeting.
        
        Args:
            vaada_date: Date to check
            exclude_vaadot_id: Optional meeting ID to exclude
            
        Returns:
            True if date is available
        """
        stmt = select(func.count()).select_from(Vaada).where(
            Vaada.vaada_date == vaada_date,
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        
        if exclude_vaadot_id is not None:
            stmt = stmt.where(Vaada.vaadot_id != exclude_vaadot_id)
        
        count = self.session.execute(stmt).scalar() or 0
        return count == 0

    def get_week_bounds(self, check_date: date) -> Tuple[date, date]:
        """Return start (Sunday) and end (Saturday) of the week for the given date."""
        from datetime import timedelta
        # In Israel, week starts on Sunday (weekday 6 in Python if using ISO, but let's be careful)
        # Python weekday: 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
        days_to_subtract = (check_date.weekday() + 1) % 7
        week_start = check_date - timedelta(days=days_to_subtract)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    def get_weekly_count(self, week_start: date, week_end: date, 
                         exclude_vaada_id: Optional[int] = None) -> int:
        """Count active meetings in a given week."""
        stmt = select(func.count()).select_from(Vaada).where(
            Vaada.vaada_date >= week_start,
            Vaada.vaada_date <= week_end,
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        if exclude_vaada_id is not None:
            stmt = stmt.where(Vaada.vaadot_id != exclude_vaada_id)
            
        return self.session.execute(stmt).scalar() or 0

    def is_third_week_of_month(self, check_date: date) -> bool:
        """Check if a date falls in the third week of the month (Sun-Sat)."""
        # First day of month
        first_day = check_date.replace(day=1)
        # Weekbounds of the first day
        first_week_start, _ = self.get_week_bounds(first_day)
        # Third week start is 14 days after first week start
        third_week_start = first_week_start + timedelta(days=14)
        third_week_end = third_week_start + timedelta(days=6)
        
        return third_week_start <= check_date <= third_week_end

    def check_existing_match(self, committee_type_id: int, hativa_id: int, 
                             vaada_date: date, exclude_vaadot_id: Optional[int] = None) -> Optional[Vaada]:
        """Check if a meeting with same type/hativa/date already exists."""
        stmt = select(Vaada).where(
            Vaada.committee_type_id == committee_type_id,
            Vaada.hativa_id == hativa_id,
            Vaada.vaada_date == vaada_date,
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        if exclude_vaadot_id is not None:
            stmt = stmt.where(Vaada.vaadot_id != exclude_vaadot_id)
            
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
