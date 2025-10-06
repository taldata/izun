#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Script for Committee Management System

This script ensures the database is properly initialized and migrated
during deployment. It uses the same environment variable configuration
as the main application.
"""

import os
import sys
from database import DatabaseManager

def main():
    """Run database migrations"""
    try:
        # Get database path from environment variable
        db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
        
        print(f"Starting database migration...")
        print(f"Database path: {db_path}")
        
        # Initialize database manager (this will create/migrate the database)
        db = DatabaseManager(db_path=db_path)
        
        print(f"✓ Database initialized successfully at: {db_path}")
        print(f"✓ All tables created/migrated")
        print(f"✓ System settings configured")
        print(f"✓ Default admin user created (if needed)")
        
        return 0
        
    except Exception as e:
        print(f"✗ Error during database migration: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

