#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calendar sync repository for database operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from datetime import datetime

from .base import BaseRepository
from models import CalendarSyncEvent


class CalendarSyncRepository(BaseRepository[CalendarSyncEvent]):
    """Repository for CalendarSyncEvent operations."""
    model_class = CalendarSyncEvent

    def get_record(self, source_type: str, source_id: int, deadline_type: Optional[str] = None,
                   calendar_email: Optional[str] = None) -> Optional[CalendarSyncEvent]:
        """Get a specific sync record."""
        filters = [
            self.model_class.source_type == source_type,
            self.model_class.source_id == source_id
        ]
        
        if deadline_type:
            filters.append(self.model_class.deadline_type == deadline_type)
        if calendar_email:
            filters.append(self.model_class.calendar_email == calendar_email)
            
        stmt = select(self.model_class).where(and_(*filters))
        return self.session.execute(stmt).scalar_one_or_none()

    def create_record(self, source_type: str, source_id: int, deadline_type: Optional[str] = None,
                      calendar_email: Optional[str] = None, calendar_event_id: Optional[str] = None,
                      status: str = 'pending', content_hash: Optional[str] = None) -> CalendarSyncEvent:
        """Create a new sync record."""
        record = CalendarSyncEvent(
            source_type=source_type,
            source_id=source_id,
            deadline_type=deadline_type,
            calendar_email=calendar_email,
            calendar_event_id=calendar_event_id,
            status=status,
            content_hash=content_hash,
            last_synced=datetime.now()
        )
        self.session.add(record)
        self.session.commit()
        return record

    def update_status(self, sync_id: int, status: str, calendar_event_id: Optional[str] = None,
                      error_message: Optional[str] = None, content_hash: Optional[str] = None) -> bool:
        """Update sync status."""
        record = self.get_by_id(sync_id)
        if record:
            record.status = status
            record.last_synced = datetime.now()
            if calendar_event_id:
                record.calendar_event_id = calendar_event_id
            if error_message:
                record.error_message = error_message
            if content_hash:
                record.content_hash = content_hash
            self.session.commit()
            return True
        return False

    def get_pending(self, calendar_email: Optional[str] = None) -> List[CalendarSyncEvent]:
        """Get all pending sync records."""
        filters = [self.model_class.status == 'pending']
        if calendar_email:
            filters.append(self.model_class.calendar_email == calendar_email)
            
        stmt = select(self.model_class).where(and_(*filters))
        return list(self.session.execute(stmt).scalars().all())

    def delete_record(self, source_type: str, source_id: int, deadline_type: Optional[str] = None,
                      calendar_email: Optional[str] = None) -> bool:
        """Delete a sync record."""
        record = self.get_record(source_type, source_id, deadline_type, calendar_email)
        if record:
            self.session.delete(record)
            self.session.commit()
            return True
        return False
