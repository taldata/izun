#!/usr/bin/env python3
"""
Migration script to fix the role CHECK constraint in users table.
Changes from ('admin', 'manager', 'user') to ('admin', 'editor', 'viewer')
and migrates existing data accordingly.

Usage:
  Local: python3 fix_role_constraint.py
  Production (Render): python3 fix_role_constraint.py /var/data/committee_system.db
  Or set DATABASE_PATH environment variable
"""

import sqlite3
import sys
import os
from pathlib import Path

def migrate_roles(db_path='committee_system.db'):
    """Migrate roles from old system to new system"""
    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")

        # Step 1: Create new users table with correct CHECK constraint
        print("Creating new users table with updated CHECK constraint...")
        cursor.execute("""
            CREATE TABLE users_new (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
                hativa_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                auth_source TEXT DEFAULT 'local' CHECK (auth_source IN ('local', 'ad')),
                ad_dn TEXT,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id)
            )
        """)

        # Step 2: Copy data with role mapping
        print("Migrating user data with role mapping...")
        cursor.execute("""
            INSERT INTO users_new (
                user_id, username, email, password_hash, full_name,
                role, hativa_id, is_active, created_at, last_login,
                auth_source, ad_dn
            )
            SELECT
                user_id, username, email, password_hash, full_name,
                CASE
                    WHEN role = 'admin' THEN 'admin'
                    WHEN role = 'manager' THEN 'editor'
                    WHEN role = 'user' THEN 'viewer'
                    ELSE 'viewer'
                END as role,
                hativa_id, is_active, created_at, last_login,
                auth_source, ad_dn
            FROM users
        """)

        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM users")
        old_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users_new")
        new_count = cursor.fetchone()[0]

        if old_count != new_count:
            raise Exception(f"Migration failed: Old table has {old_count} rows, new table has {new_count} rows")

        print(f"Migrated {new_count} users successfully")

        # Step 3: Show role migration summary
        cursor.execute("""
            SELECT
                old.role as old_role,
                new.role as new_role,
                COUNT(*) as count
            FROM users old
            JOIN users_new new ON old.user_id = new.user_id
            GROUP BY old.role, new.role
        """)
        print("\nRole migration summary:")
        for old_role, new_role, count in cursor.fetchall():
            print(f"  {old_role} -> {new_role}: {count} users")

        # Step 4: Drop old table and rename new table
        print("\nReplacing old table with new table...")
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")

        # Commit transaction
        conn.commit()
        print("\n✅ Migration completed successfully!")

        # Show final user list
        cursor.execute("SELECT user_id, username, full_name, role FROM users ORDER BY user_id")
        print("\nFinal user list:")
        for user_id, username, full_name, role in cursor.fetchall():
            print(f"  [{user_id}] {full_name} ({username}) - {role}")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    # Determine database path (priority: CLI arg > ENV var > default)
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')

    print(f"Database path: {db_path}")

    if not Path(db_path).exists():
        print(f"Error: Database file '{db_path}' not found")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

    # Create backup
    import shutil
    from datetime import datetime
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_path}")
    try:
        shutil.copy2(db_path, backup_path)
        print(f"Backup created successfully")
    except Exception as e:
        print(f"Warning: Could not create backup: {e}")
        response = input("Continue without backup? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled")
            sys.exit(1)

    # Run migration
    success = migrate_roles(db_path)
    sys.exit(0 if success else 1)
