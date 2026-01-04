#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schedule Draft repository for database operations.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from .base import BaseRepository
from models import ScheduleDraft


class ScheduleDraftRepository(BaseRepository[ScheduleDraft]):
    """Repository for Schedule Draft operations."""
    
    model_class = ScheduleDraft
    
    def save_draft(self, user_id: int, data: str) -> int:
        """
        Save a schedule draft.
        
        Returns:
            Draft ID
        """
        draft = ScheduleDraft(user_id=user_id, data=data)
        self.add(draft)
        return draft.draft_id
    
    def get_draft(self, draft_id: int) -> Optional[ScheduleDraft]:
        """Get a schedule draft by ID."""
        return self.get_by_id(draft_id)
    
    def cleanup_old_drafts(self, hours: int = 24) -> int:
        """
        Delete drafts older than specified hours.
        
        Returns:
            Number of deleted drafts
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        stmt = delete(ScheduleDraft).where(ScheduleDraft.created_at < cutoff)
        result = self.session.execute(stmt)
        return result.rowcount
