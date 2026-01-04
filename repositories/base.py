#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base repository class with common CRUD operations.
"""

from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from models import Base

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic base repository providing common CRUD operations.
    
    Usage:
        class HativaRepository(BaseRepository[Hativa]):
            model_class = Hativa
    """
    
    model_class: Type[T] = None
    
    def __init__(self, session: Session):
        """
        Initialize repository with a database session.
        
        Args:
            session: SQLAlchemy session instance
        """
        self.session = session
    
    def get_by_id(self, id: int) -> Optional[T]:
        """
        Get a single record by its primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        pk_column = self._get_primary_key_column()
        stmt = select(self.model_class).where(pk_column == id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_all(self) -> List[T]:
        """
        Get all records for this model.
        
        Returns:
            List of model instances
        """
        stmt = select(self.model_class)
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def add(self, entity: T) -> T:
        """
        Add a new record.
        
        Args:
            entity: Model instance to add
            
        Returns:
            The added entity with generated ID
        """
        self.session.add(entity)
        self.session.flush()  # Get the generated ID
        return entity
    
    def update(self, entity: T) -> T:
        """
        Update an existing record.
        
        Args:
            entity: Model instance to update
            
        Returns:
            The updated entity
        """
        self.session.merge(entity)
        self.session.flush()
        return entity
    
    def delete(self, entity: T) -> bool:
        """
        Delete a record.
        
        Args:
            entity: Model instance to delete
            
        Returns:
            True if deleted successfully
        """
        self.session.delete(entity)
        self.session.flush()
        return True
    
    def delete_by_id(self, id: int) -> bool:
        """
        Delete a record by its primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            True if a record was deleted
        """
        pk_column = self._get_primary_key_column()
        stmt = delete(self.model_class).where(pk_column == id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount > 0
    
    def exists(self, id: int) -> bool:
        """
        Check if a record with the given ID exists.
        
        Args:
            id: Primary key value
            
        Returns:
            True if record exists
        """
        return self.get_by_id(id) is not None
    
    def count(self) -> int:
        """
        Get the total count of records.
        
        Returns:
            Number of records
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model_class)
        result = self.session.execute(stmt)
        return result.scalar()
    
    def _get_primary_key_column(self):
        """Get the primary key column for this model."""
        pk_columns = self.model_class.__table__.primary_key.columns
        return list(pk_columns)[0]
    
    def to_dict(self, entity: T) -> Dict[str, Any]:
        """
        Convert entity to dictionary.
        Uses the model's to_dict() method if available.
        
        Args:
            entity: Model instance
            
        Returns:
            Dictionary representation
        """
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        
        # Fallback: Convert all columns to dict
        return {
            column.name: getattr(entity, column.name)
            for column in entity.__table__.columns
        }
    
    def to_dict_list(self, entities: List[T]) -> List[Dict[str, Any]]:
        """
        Convert list of entities to list of dictionaries.
        
        Args:
            entities: List of model instances
            
        Returns:
            List of dictionary representations
        """
        return [self.to_dict(e) for e in entities]
