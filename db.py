#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Engine and Session Management for SQLAlchemy 2.0

This module provides database connection, session management with connection pooling,
and utility functions for both PostgreSQL and SQLite.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool, StaticPool

from models import Base


def get_database_url() -> str:
    """
    Get the database URL from environment variables.
    Exclusively supports PostgreSQL (DATABASE_URL).
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set. PostgreSQL is required.")
        
    # Handle Heroku/Render style postgres:// URLs
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return database_url


def create_database_engine(database_url: str = None):
    """
    Create SQLAlchemy engine with appropriate settings for PostgreSQL.
    
    Args:
        database_url: Optional database URL. If not provided, uses get_database_url().
    
    Returns:
        SQLAlchemy Engine instance
    """
    if database_url is None:
        database_url = get_database_url()
    
    # PostgreSQL configuration with connection pooling
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Enable connection health checks
        echo=False  # Set to True for SQL debugging
    )
    
    return engine


class DatabaseSession:
    """
    Database session manager with support for both PostgreSQL and SQLite.
    Provides thread-safe session management with scoped sessions.
    """
    
    _instance = None
    _engine = None
    _session_factory = None
    _scoped_session = None
    
    def __new__(cls):
        """Singleton pattern to ensure single engine instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the database engine and session factory."""
        self._engine = create_database_engine()
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        self._scoped_session = scoped_session(self._session_factory)
    
    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        return self._engine
    
    @property
    def session_factory(self):
        """Get the session factory."""
        return self._session_factory
    
    def get_session(self) -> Session:
        """
        Get a new session from the scoped session registry.
        For use in Flask request context.
        """
        return self._scoped_session()
    
    def remove_session(self):
        """
        Remove the current session from the registry.
        Call this at the end of each request.
        """
        self._scoped_session.remove()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Usage:
            with db.session_scope() as session:
                session.add(obj)
                # Auto-commits on success, rolls back on exception
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_all_tables(self):
        """Create all tables defined in models.py."""
        Base.metadata.create_all(self._engine)
    
    def drop_all_tables(self):
        """Drop all tables. Use with caution!"""
        Base.metadata.drop_all(self._engine)
    
    def get_db_type(self) -> str:
        """Return the database type ('postgresql' or 'sqlite')."""
        url = str(self._engine.url)
        if 'postgresql' in url:
            return 'postgresql'
        return 'sqlite'


# Global instance for easy access
db = DatabaseSession()


def get_db() -> Session:
    """
    Get a database session for use in Flask request handlers.
    
    Usage in Flask:
        from db import get_db
        
        @app.route('/example')
        def example():
            session = get_db()
            items = session.query(Model).all()
            return jsonify([item.to_dict() for item in items])
    """
    return db.get_session()


def cleanup_db():
    """
    Clean up the database session.
    Call this at the end of each Flask request.
    
    Usage in Flask:
        @app.teardown_appcontext
        def cleanup(exception=None):
            cleanup_db()
    """
    db.remove_session()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Provides automatic commit/rollback and session cleanup.
    
    Usage:
        from db import get_db_session
        
        with get_db_session() as session:
            hativa = Hativa(name='Test')
            session.add(hativa)
            # Auto-commits on success
    """
    with db.session_scope() as session:
        yield session


def init_database():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times - only creates tables that don't exist.
    """
    db.create_all_tables()


def execute_raw_sql(sql: str, params: dict = None) -> list:
    """
    Execute raw SQL for cases where ORM isn't suitable.
    
    Args:
        sql: The SQL query string
        params: Optional dictionary of parameters
    
    Returns:
        List of result rows
    """
    with db.session_scope() as session:
        result = session.execute(text(sql), params or {})
        return result.fetchall()


# Convenience exports
__all__ = [
    'db',
    'get_db',
    'cleanup_db',
    'get_db_session',
    'init_database',
    'execute_raw_sql',
    'DatabaseSession',
    'create_database_engine',
    'get_database_url',
]
