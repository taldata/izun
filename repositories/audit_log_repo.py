#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit Log repository for database operations.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from .base import BaseRepository
from models import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for Audit Log operations."""
    
    model_class = AuditLog
    
    def log(self, user_id: Optional[int], username: Optional[str], action: str,
            entity_type: str, entity_id: Optional[int] = None, 
            entity_name: Optional[str] = None, details: Optional[str] = None,
            ip_address: Optional[str] = None, user_agent: Optional[str] = None,
            status: str = 'success', error_message: Optional[str] = None) -> int:
        """
        Create a new audit log entry.
        
        Returns:
            Log ID
        """
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        self.add(log_entry)
        return log_entry.log_id
    
    def get_logs(self, limit: int = 100, offset: int = 0,
                 user_id: Optional[int] = None,
                 entity_type: Optional[str] = None,
                 action: Optional[str] = None,
                 search_text: Optional[str] = None,
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None) -> List[AuditLog]:
        """Get audit logs with optional filters."""
        stmt = select(AuditLog)
        
        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        if action:
            filters.append(AuditLog.action == action)
        if search_text:
            pattern = f"%{search_text}%"
            filters.append(or_(
                AuditLog.entity_name.ilike(pattern),
                AuditLog.details.ilike(pattern),
                AuditLog.entity_type.ilike(pattern)
            ))
        if start_date:
            stmt = stmt.where(func.date(AuditLog.timestamp) >= start_date)
        if end_date:
            stmt = stmt.where(func.date(AuditLog.timestamp) <= end_date)
            
        if filters:
            stmt = stmt.where(and_(*filters))
            
        stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def get_logs_count(self, user_id: Optional[int] = None,
                       entity_type: Optional[str] = None,
                       action: Optional[str] = None,
                       search_text: Optional[str] = None,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> int:
        """Get total count of audit logs matching filters."""
        stmt = select(func.count()).select_from(AuditLog)
        
        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        if action:
            filters.append(AuditLog.action == action)
        if search_text:
            pattern = f"%{search_text}%"
            filters.append(or_(
                AuditLog.entity_name.ilike(pattern),
                AuditLog.details.ilike(pattern),
                AuditLog.entity_type.ilike(pattern)
            ))
        if start_date:
            stmt = stmt.where(func.date(AuditLog.timestamp) >= start_date)
        if end_date:
            stmt = stmt.where(func.date(AuditLog.timestamp) <= end_date)
            
        if filters:
            stmt = stmt.where(and_(*filters))
            
        result = self.session.execute(stmt)
        return result.scalar()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        # Total logs
        total_logs = self.count()
        
        # Logs by action
        action_stmt = select(AuditLog.action, func.count(AuditLog.log_id)).group_by(
            AuditLog.action).order_by(func.count(AuditLog.log_id).desc()).limit(10)
        actions = [{'action': row[0], 'count': row[1]} for row in self.session.execute(action_stmt).all()]
        
        # Logs by entity type
        entity_stmt = select(AuditLog.entity_type, func.count(AuditLog.log_id)).group_by(
            AuditLog.entity_type).order_by(func.count(AuditLog.log_id).desc())
        entities = [{'entity_type': row[0], 'count': row[1]} for row in self.session.execute(entity_stmt).all()]
        
        # Recent activity (last 24 hours) - Generic approach for both SQLite and PG
        # In SQLAlchemy, we can use func.now() and compare with interval
        # But interval is dialect specific. A safer way is to use python to get the cutoff.
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=1)
        recent_stmt = select(func.count(AuditLog.log_id)).where(AuditLog.timestamp >= cutoff)
        last_24h = self.session.execute(recent_stmt).scalar()
        
        # Failed operations
        failed_stmt = select(func.count(AuditLog.log_id)).where(AuditLog.status == 'error')
        failed_ops = self.session.execute(failed_stmt).scalar()
        
        # Most active users
        user_stmt = select(AuditLog.username, func.count(AuditLog.log_id)).group_by(
            AuditLog.username).order_by(func.count(AuditLog.log_id).desc()).limit(10)
        active_users = [{'username': row[0], 'count': row[1]} for row in self.session.execute(user_stmt).all()]
        
        return {
            'total_logs': total_logs,
            'actions': actions,
            'entities': entities,
            'last_24h': last_24h,
            'failed_ops': failed_ops,
            'active_users': active_users
        }
