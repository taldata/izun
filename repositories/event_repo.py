#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event repository for database operations.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from models import Event, Vaada, Maslul, CommitteeType, Hativa


class EventRepository(BaseRepository[Event]):
    """Repository for Event operations."""
    
    model_class = Event
    
    def get_all(self, vaadot_id: Optional[int] = None,
                include_deleted: bool = False) -> List[Event]:
        """
        Get all events, optionally filtered by committee meeting.
        
        Args:
            vaadot_id: Optional committee meeting ID filter
            include_deleted: If True, include soft-deleted events
            
        Returns:
            List of Event instances
        """
        stmt = select(Event).options(
            joinedload(Event.vaada).joinedload(Vaada.committee_type).joinedload(CommitteeType.hativa),
            joinedload(Event.vaada).joinedload(Vaada.hativa),
            joinedload(Event.maslul).joinedload(Maslul.hativa)
        ).order_by(Event.event_id)
        
        if vaadot_id is not None:
            stmt = stmt.where(Event.vaadot_id == vaadot_id)
        
        if not include_deleted:
            stmt = stmt.where(and_(
                or_(Event.is_deleted == 0, Event.is_deleted.is_(None)),
                or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
            ))
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_by_vaada(self, vaadot_id: int, include_deleted: bool = False) -> List[Event]:
        """
        Get events for a specific committee meeting.
        
        Args:
            vaadot_id: Committee meeting ID
            include_deleted: If True, include soft-deleted events
            
        Returns:
            List of Event instances
        """
        return self.get_all(vaadot_id=vaadot_id, include_deleted=include_deleted)
    
    def create(self, vaadot_id: int, maslul_id: int, name: str,
               event_type: str, expected_requests: int = 0,
               actual_submissions: int = 0,
               call_publication_date: Optional[date] = None,
               is_call_deadline_manual: bool = False,
               manual_call_deadline_date: Optional[date] = None) -> Event:
        """
        Create a new event.
        
        Args:
            vaadot_id: Committee meeting ID
            maslul_id: Route ID
            name: Event name
            event_type: Event type ('kokok' or 'shotef')
            expected_requests: Expected number of requests
            actual_submissions: Actual submissions
            call_publication_date: Optional publication date
            is_call_deadline_manual: If True, use manual deadline
            manual_call_deadline_date: Manual deadline date
            
        Returns:
            Created Event instance
        """
        event = Event(
            vaadot_id=vaadot_id,
            maslul_id=maslul_id,
            name=name,
            event_type=event_type,
            expected_requests=expected_requests,
            actual_submissions=actual_submissions,
            call_publication_date=call_publication_date,
            is_call_deadline_manual=1 if is_call_deadline_manual else 0,
            call_deadline_date=manual_call_deadline_date if is_call_deadline_manual else None,
            is_deleted=0
        )
        return self.add(event)
    
    def update_event(self, event_id: int, vaadot_id: int, maslul_id: int,
                     name: str, event_type: str, expected_requests: int = 0,
                     actual_submissions: int = 0,
                     call_publication_date: Optional[date] = None,
                     is_call_deadline_manual: bool = False,
                     manual_call_deadline_date: Optional[date] = None) -> bool:
        """
        Update event details.
        
        Args:
            event_id: Event ID
            vaadot_id: Committee meeting ID
            maslul_id: Route ID
            name: Event name
            event_type: Event type
            expected_requests: Expected requests
            actual_submissions: Actual submissions
            call_publication_date: Publication date
            is_call_deadline_manual: Manual deadline flag
            manual_call_deadline_date: Manual deadline date
            
        Returns:
            True if updated successfully
        """
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        event.vaadot_id = vaadot_id
        event.maslul_id = maslul_id
        event.name = name
        event.event_type = event_type
        event.expected_requests = expected_requests
        event.actual_submissions = actual_submissions
        event.call_publication_date = call_publication_date
        event.is_call_deadline_manual = 1 if is_call_deadline_manual else 0
        if is_call_deadline_manual:
            event.call_deadline_date = manual_call_deadline_date
        
        self.session.flush()
        return True
    
    def update_deadlines(self, event_id: int,
                         call_deadline_date: Optional[date] = None,
                         intake_deadline_date: Optional[date] = None,
                         review_deadline_date: Optional[date] = None,
                         response_deadline_date: Optional[date] = None) -> bool:
        """
        Update event deadline dates.
        
        Args:
            event_id: Event ID
            call_deadline_date: Call deadline
            intake_deadline_date: Intake deadline
            review_deadline_date: Review deadline
            response_deadline_date: Response deadline
            
        Returns:
            True if updated successfully
        """
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        if call_deadline_date is not None:
            event.call_deadline_date = call_deadline_date
        if intake_deadline_date is not None:
            event.intake_deadline_date = intake_deadline_date
        if review_deadline_date is not None:
            event.review_deadline_date = review_deadline_date
        if response_deadline_date is not None:
            event.response_deadline_date = response_deadline_date
        
        self.session.flush()
        return True
    
    def soft_delete(self, event_id: int, user_id: Optional[int] = None) -> bool:
        """
        Soft delete an event.
        
        Args:
            event_id: Event ID
            user_id: User performing the delete
            
        Returns:
            True if deleted successfully
        """
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        event.is_deleted = 1
        event.deleted_at = datetime.now()
        event.deleted_by = user_id
        self.session.flush()
        return True
    
    def restore(self, event_id: int) -> bool:
        """
        Restore a soft-deleted event.
        
        Args:
            event_id: Event ID
            
        Returns:
            True if restored successfully
        """
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        event.is_deleted = 0
        event.deleted_at = None
        event.deleted_by = None
        self.session.flush()
        return True
    
    def hard_delete(self, event_id: int) -> bool:
        """
        Permanently delete an event.
        
        Args:
            event_id: Event ID
            
        Returns:
            True if deleted successfully
        """
        event = self.get_by_id(event_id)
        if not event:
            return False
        
        self.session.delete(event)
        self.session.flush()
        return True
    
    def get_deleted(self, hativa_id: Optional[int] = None) -> List[Event]:
        """
        Get all soft-deleted events.
        
        Args:
            hativa_id: Optional division filter
            
        Returns:
            List of deleted Event instances
        """
        stmt = select(Event).options(
            joinedload(Event.vaada).joinedload(Vaada.hativa),
            joinedload(Event.maslul)
        ).where(Event.is_deleted == 1).order_by(Event.deleted_at.desc())
        
        if hativa_id is not None:
            stmt = stmt.join(Event.vaada).where(Vaada.hativa_id == hativa_id)
        
        result = self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    def get_total_requests_on_date(self, check_date: date,
                                    exclude_event_id: Optional[int] = None) -> int:
        """
        Get total expected requests for events on a specific date.
        
        Args:
            check_date: Date to check
            exclude_event_id: Optional event ID to exclude
            
        Returns:
            Total expected requests
        """
        stmt = select(func.sum(Event.expected_requests)).join(Event.vaada).where(
            Vaada.vaada_date == check_date,
            or_(Event.is_deleted == 0, Event.is_deleted.is_(None)),
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        
        if exclude_event_id is not None:
            stmt = stmt.where(Event.event_id != exclude_event_id)
        
        return self.session.execute(stmt).scalar() or 0

    def get_total_requests_on_derived_date(self, check_date: date, date_type: str,
                                            exclude_event_id: Optional[int] = None) -> int:
        """
        Get total expected requests on a specific derived date.
        
        Args:
            check_date: Date to check
            date_type: 'call_deadline', 'intake_deadline', 'review_deadline', or 'response_deadline'
            exclude_event_id: Optional event ID to exclude
            
        Returns:
            Total expected requests
        """
        column_map = {
            'call_deadline': Event.call_deadline_date,
            'intake_deadline': Event.intake_deadline_date,
            'review_deadline': Event.review_deadline_date,
            'response_deadline': Event.response_deadline_date
        }
        
        if date_type not in column_map:
            raise ValueError(f"Invalid date_type: {date_type}")
            
        column = column_map[date_type]
        
        stmt = select(func.sum(Event.expected_requests)).join(Event.vaada).where(
            column == check_date,
            or_(Event.is_deleted == 0, Event.is_deleted.is_(None)),
            or_(Vaada.is_deleted == 0, Vaada.is_deleted.is_(None))
        )
        
        if exclude_event_id is not None:
            stmt = stmt.where(Event.event_id != exclude_event_id)
            
        return self.session.execute(stmt).scalar() or 0

    def calculate_stage_dates(self, committee_date: date, 
                             stage_a_days: int, stage_b_days: int, 
                             stage_c_days: int, stage_d_days: int,
                             is_work_day_fn) -> Dict[str, date]:
        """
        Calculate stage deadline dates.
        
        Args:
            committee_date: The date of the committee meeting
            stage_a_days: Days for stage A
            stage_b_days: Days for stage B
            stage_c_days: Days for stage C
            stage_d_days: Days for stage D
            is_work_day_fn: Function that takes a date and returns bool
        """
        from datetime import timedelta
        
        def add_bus_days(start: date, days: int) -> date:
            curr = start
            added = 0
            while added < days:
                curr += timedelta(days=1)
                if is_work_day_fn(curr):
                    added += 1
            return curr

        def sub_bus_days(start: date, days: int) -> date:
            curr = start
            subbed = 0
            while subbed < days:
                curr -= timedelta(days=1)
                if is_work_day_fn(curr):
                    subbed += 1
            return curr

        # Logic from database.py
        response_deadline = add_bus_days(committee_date, stage_d_days)
        review_deadline = sub_bus_days(committee_date, stage_c_days)
        intake_deadline = sub_bus_days(review_deadline, stage_b_days)
        call_deadline = sub_bus_days(intake_deadline, stage_a_days)
        
        return {
            'call_deadline_date': call_deadline,
            'intake_deadline_date': intake_deadline,
            'review_deadline_date': review_deadline,
            'response_deadline_date': response_deadline,
            'committee_date': committee_date
        }

    def check_derived_dates_constraints(self, stage_dates: Dict[str, date], 
                                       expected_requests: int, 
                                       exclude_event_id: Optional[int] = None) -> Optional[str]:
        """
        Check constraints on derived dates. 
        Current implementation in database.py does nothing, so we keep it as a placeholder.
        """
        return None
