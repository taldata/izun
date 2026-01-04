#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLAlchemy 2.0 ORM Models for Committee Management System

This module defines all database models using SQLAlchemy 2.0 declarative syntax
with full type annotations support.
"""

from datetime import datetime, date, time
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, Integer, String, Text, Date, Time, DateTime, 
    ForeignKey, CheckConstraint, UniqueConstraint, Index,
    LargeBinary, Boolean, func
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Association table for User <-> Hativa many-to-many relationship
class UserHativa(Base):
    """User-Hativa association table for many-to-many relationship."""
    __tablename__ = 'user_hativot'
    
    user_hativa_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    hativa_id: Mapped[int] = mapped_column(Integer, ForeignKey('hativot.hativa_id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'hativa_id', name='uq_user_hativa'),
    )


class Hativa(Base):
    """Division/Department model (חטיבות)."""
    __tablename__ = 'hativot'
    
    hativa_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), default='#007bff')
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    maslulim: Mapped[List["Maslul"]] = relationship(
        "Maslul", back_populates="hativa", cascade="all, delete-orphan"
    )
    committee_types: Mapped[List["CommitteeType"]] = relationship(
        "CommitteeType", back_populates="hativa", cascade="all, delete-orphan"
    )
    vaadot: Mapped[List["Vaada"]] = relationship(
        "Vaada", back_populates="hativa"
    )
    day_constraints: Mapped[List["HativaDayConstraint"]] = relationship(
        "HativaDayConstraint", back_populates="hativa", cascade="all, delete-orphan"
    )
    users: Mapped[List["User"]] = relationship(
        "User", secondary="user_hativot", back_populates="hativot"
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'hativa_id': self.hativa_id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'allowed_days': [c.day_of_week for c in self.day_constraints] if self.day_constraints else []
        }


class HativaDayConstraint(Base):
    """Day constraints for divisions."""
    __tablename__ = 'hativa_day_constraints'
    
    constraint_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hativa_id: Mapped[int] = mapped_column(Integer, ForeignKey('hativot.hativa_id', ondelete='CASCADE'), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationship
    hativa: Mapped["Hativa"] = relationship("Hativa", back_populates="day_constraints")
    
    __table_args__ = (
        UniqueConstraint('hativa_id', 'day_of_week', name='uq_hativa_day'),
        CheckConstraint('day_of_week >= 0 AND day_of_week <= 6', name='ck_day_of_week'),
        Index('idx_hativa_day_constraints_hativa', 'hativa_id'),
    )


class Maslul(Base):
    """Route/Track model (מסלולים)."""
    __tablename__ = 'maslulim'
    
    maslul_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hativa_id: Mapped[int] = mapped_column(Integer, ForeignKey('hativot.hativa_id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # SLA configuration
    sla_days: Mapped[int] = mapped_column(Integer, default=45)
    stage_a_days: Mapped[int] = mapped_column(Integer, default=10)
    stage_b_days: Mapped[int] = mapped_column(Integer, default=15)
    stage_c_days: Mapped[int] = mapped_column(Integer, default=10)
    stage_d_days: Mapped[int] = mapped_column(Integer, default=10)
    
    # Extended stage configuration
    stage_a_easy_days: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    stage_a_review_days: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    stage_b_easy_days: Mapped[Optional[int]] = mapped_column(Integer, default=8, nullable=True)
    stage_b_review_days: Mapped[Optional[int]] = mapped_column(Integer, default=7, nullable=True)
    stage_c_easy_days: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    stage_c_review_days: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    stage_d_easy_days: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    stage_d_review_days: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    call_publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Relationships
    hativa: Mapped["Hativa"] = relationship("Hativa", back_populates="maslulim")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="maslul", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'maslul_id': self.maslul_id,
            'hativa_id': self.hativa_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'sla_days': self.sla_days,
            'stage_a_days': self.stage_a_days,
            'stage_b_days': self.stage_b_days,
            'stage_c_days': self.stage_c_days,
            'stage_d_days': self.stage_d_days,
            'hativa_name': self.hativa.name if self.hativa else None,
            'hativa_color': self.hativa.color if self.hativa else None,
        }


class CommitteeType(Base):
    """Committee Type definition (סוגי ועדות)."""
    __tablename__ = 'committee_types'
    
    committee_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hativa_id: Mapped[int] = mapped_column(Integer, ForeignKey('hativot.hativa_id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_day: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default='weekly')
    week_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_operational: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    hativa: Mapped["Hativa"] = relationship("Hativa", back_populates="committee_types")
    vaadot: Mapped[List["Vaada"]] = relationship("Vaada", back_populates="committee_type")
    
    __table_args__ = (
        UniqueConstraint('hativa_id', 'name', name='uq_hativa_committee_name'),
        CheckConstraint("frequency IN ('weekly', 'monthly')", name='ck_frequency'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'committee_type_id': self.committee_type_id,
            'hativa_id': self.hativa_id,
            'name': self.name,
            'description': self.description,
            'scheduled_day': self.scheduled_day,
            'frequency': self.frequency,
            'week_of_month': self.week_of_month,
            'is_operational': self.is_operational,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'hativa_name': self.hativa.name if self.hativa else None,
            'hativa_color': self.hativa.color if self.hativa else None,
        }


class ExceptionDate(Base):
    """Exception dates (holidays, sabbaths, special days)."""
    __tablename__ = 'exception_dates'
    
    date_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), default='holiday')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    vaadot: Mapped[List["Vaada"]] = relationship("Vaada", back_populates="exception_date_rel")
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'date_id': self.date_id,
            'exception_date': self.exception_date,
            'description': self.description,
            'type': self.type,
            'created_at': self.created_at,
        }


class Vaada(Base):
    """Committee Meeting instance (ועדות)."""
    __tablename__ = 'vaadot'
    
    vaadot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    committee_type_id: Mapped[int] = mapped_column(Integer, ForeignKey('committee_types.committee_type_id'), nullable=False)
    hativa_id: Mapped[int] = mapped_column(Integer, ForeignKey('hativot.hativa_id'), nullable=False)
    vaada_date: Mapped[date] = mapped_column(Date, nullable=False)
    exception_date_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('exception_dates.date_id'), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    end_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    committee_type: Mapped["CommitteeType"] = relationship("CommitteeType", back_populates="vaadot")
    hativa: Mapped["Hativa"] = relationship("Hativa", back_populates="vaadot")
    exception_date_rel: Mapped[Optional["ExceptionDate"]] = relationship("ExceptionDate", back_populates="vaadot")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="vaada", cascade="all, delete-orphan")
    calendar_syncs: Mapped[List["CalendarSyncEvent"]] = relationship(
        "CalendarSyncEvent", 
        primaryjoin="and_(Vaada.vaadot_id==foreign(CalendarSyncEvent.source_id), CalendarSyncEvent.source_type=='vaadot')",
        viewonly=True
    )
    
    __table_args__ = (
        Index('idx_vaadot_unique_active', 'committee_type_id', 'hativa_id', 'vaada_date', 
              unique=True, postgresql_where='is_deleted = 0 OR is_deleted IS NULL'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'vaadot_id': self.vaadot_id,
            'committee_type_id': self.committee_type_id,
            'hativa_id': self.hativa_id,
            'vaada_date': self.vaada_date,
            'exception_date_id': self.exception_date_id,
            'notes': self.notes,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at,
            'deleted_by': self.deleted_by,
            'created_at': self.created_at,
            'committee_type_name': self.committee_type.name if self.committee_type else None,
            'committee_name': self.committee_type.name if self.committee_type else None,
            'hativa_name': self.hativa.name if self.hativa else None,
            'hativa_color': self.hativa.color if self.hativa else None,
        }


class Event(Base):
    """Event/agenda item within a committee meeting."""
    __tablename__ = 'events'
    
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vaadot_id: Mapped[int] = mapped_column(Integer, ForeignKey('vaadot.vaadot_id', ondelete='CASCADE'), nullable=False)
    maslul_id: Mapped[int] = mapped_column(Integer, ForeignKey('maslulim.maslul_id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_requests: Mapped[int] = mapped_column(Integer, default=0)
    actual_submissions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Deadline dates (auto-calculated)
    call_publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    call_deadline_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    intake_deadline_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_deadline_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    response_deadline_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_call_deadline_manual: Mapped[int] = mapped_column(Integer, default=0)
    
    # Soft delete
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    vaada: Mapped["Vaada"] = relationship("Vaada", back_populates="events")
    maslul: Mapped["Maslul"] = relationship("Maslul", back_populates="events")
    
    __table_args__ = (
        CheckConstraint("event_type IN ('kokok', 'shotef')", name='ck_event_type'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'event_id': self.event_id,
            'vaadot_id': self.vaadot_id,
            'maslul_id': self.maslul_id,
            'name': self.name,
            'event_type': self.event_type,
            'expected_requests': self.expected_requests,
            'actual_submissions': self.actual_submissions,
            'call_publication_date': self.call_publication_date,
            'call_deadline_date': self.call_deadline_date,
            'intake_deadline_date': self.intake_deadline_date,
            'review_deadline_date': self.review_deadline_date,
            'response_deadline_date': self.response_deadline_date,
            'scheduled_date': self.scheduled_date,
            'is_call_deadline_manual': self.is_call_deadline_manual,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at,
            'deleted_by': self.deleted_by,
            'created_at': self.created_at,
            'maslul_name': self.maslul.name if self.maslul else None,
            'hativa_name': self.vaada.hativa.name if self.vaada and self.vaada.hativa else None,
            'hativa_color': self.vaada.hativa.color if self.vaada and self.vaada.hativa else None,
            'committee_type_name': self.vaada.committee_type.name if self.vaada and self.vaada.committee_type else None,
            'committee_name': self.vaada.committee_type.name if self.vaada and self.vaada.committee_type else None,
            'vaada_date': self.vaada.vaada_date if self.vaada else None,
        }


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = 'users'
    
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default='viewer')
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    auth_source: Mapped[str] = mapped_column(String(20), default='ad')
    ad_dn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_picture: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Note: is_deleted and deleted_at columns will be added via Alembic migration
    # For now, using is_active for soft delete functionality
    
    # Relationships
    hativot: Mapped[List["Hativa"]] = relationship(
        "Hativa", secondary="user_hativot", back_populates="users"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    schedule_drafts: Mapped[List["ScheduleDraft"]] = relationship(
        "ScheduleDraft", back_populates="user", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'viewer')", name='ck_role'),
        CheckConstraint("auth_source = 'ad'", name='ck_auth_source'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'auth_source': self.auth_source,
            'ad_dn': self.ad_dn,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_deleted': 0 if self.is_active else 1,  # Derive from is_active
            'deleted_at': None,
            'hativot': [h.to_dict() for h in self.hativot] if self.hativot else [],
            'hativa_ids': [h.hativa_id for h in self.hativot] if self.hativot else [],
        }


class SystemSetting(Base):
    """System-wide configuration settings."""
    __tablename__ = 'system_settings'
    
    setting_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'setting_id': self.setting_id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'updated_at': self.updated_at,
            'updated_by': self.updated_by,
        }


class AuditLog(Base):
    """Audit log for tracking user actions."""
    __tablename__ = 'audit_logs'
    
    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.user_id'), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='success')
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_user', 'user_id'),
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'log_id': self.log_id,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'error_message': self.error_message,
        }


class CalendarSyncEvent(Base):
    """Calendar synchronization tracking."""
    __tablename__ = 'calendar_sync_events'
    
    sync_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    calendar_email: Mapped[str] = mapped_column(String(255), nullable=False)
    last_synced: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default='pending')
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('source_type', 'source_id', 'deadline_type', 'calendar_email', name='uq_calendar_sync'),
        CheckConstraint("source_type IN ('vaadot', 'event_deadline')", name='ck_source_type'),
        CheckConstraint("sync_status IN ('pending', 'synced', 'failed', 'deleted')", name='ck_sync_status'),
        Index('idx_calendar_sync_source', 'source_type', 'source_id'),
        Index('idx_calendar_sync_status', 'sync_status'),
        Index('idx_calendar_sync_calendar_id', 'calendar_event_id'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'sync_id': self.sync_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'deadline_type': self.deadline_type,
            'calendar_event_id': self.calendar_event_id,
            'calendar_email': self.calendar_email,
            'last_synced': self.last_synced,
            'sync_status': self.sync_status,
            'error_message': self.error_message,
            'content_hash': self.content_hash,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class ScheduleDraft(Base):
    """Temporary storage for auto-scheduler drafts."""
    __tablename__ = 'schedule_drafts'
    
    draft_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="schedule_drafts")
    
    __table_args__ = (
        Index('idx_schedule_drafts_created_at', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for backward compatibility."""
        return {
            'draft_id': self.draft_id,
            'user_id': self.user_id,
            'data': self.data,
            'created_at': self.created_at,
        }
