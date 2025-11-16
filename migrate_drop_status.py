#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite migration: Drop 'status' columns from vaadot and events.
Safe process:
1) Backup DB file to backups/ with timestamp
2) For each table (vaadot, events): if column exists, recreate table without it and copy data

Usage:
  python migrate_drop_status.py [path/to/db.sqlite]
If no path is provided, the script will try these in order:
  izun.db, database.db, vaadot.db, committee_system.db
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime


POSSIBLE_DB_FILES = ["izun.db", "database.db", "vaadot.db", "committee_system.db"]


def find_db(start_dir: str) -> str:
    # If user provided an argument, use it
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return os.path.abspath(sys.argv[1].strip())
    # Otherwise try common files in project root
    for name in POSSIBLE_DB_FILES:
        candidate = os.path.join(start_dir, name)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Could not find a database file. Provide path explicitly.")


def backup_db(db_path: str) -> str:
    backups_dir = os.path.join(os.path.dirname(db_path) or ".", "backups")
    os.makedirs(backups_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(db_path)
    backup_path = os.path.join(backups_dir, f"{base}.pre_drop_status.{ts}.sqlite3")
    shutil.copy2(db_path, backup_path)
    return backup_path


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def drop_column_by_recreate(conn: sqlite3.Connection, table: str, columns_to_remove: list[str], create_sql: str, select_cols: list[str]):
    """
    Recreate table without the specified columns. Requires:
      - create_sql: CREATE TABLE statement for the new schema (without removed columns)
      - select_cols: list of columns to copy from old table into new table (in order)
    """
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    try:
        # Create temp table with new schema
        temp_table = f"{table}_new_nostatus"
        cursor.execute(create_sql.replace(table, temp_table, 1))

        # Copy data
        cols_csv = ", ".join(select_cols)
        cursor.execute(f"INSERT INTO {temp_table} ({cols_csv}) SELECT {cols_csv} FROM {table}")

        # Drop old and rename new
        cursor.execute(f"DROP TABLE {table}")
        cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table}")

        conn.commit()
    except Exception:
        conn.rollback()
        raise


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # VACUUM safety
    cursor.execute("PRAGMA foreign_keys=OFF")

    # 1) vaadot: drop status if exists
    if column_exists(cursor, "vaadot", "status"):
        create_sql_vaadot = """
        CREATE TABLE vaadot (
            vaadot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            committee_type_id INTEGER NOT NULL,
            hativa_id INTEGER NOT NULL,
            vaada_date DATE NOT NULL,
            exception_date_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by INTEGER,
            FOREIGN KEY (committee_type_id) REFERENCES committee_types (committee_type_id),
            FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id),
            FOREIGN KEY (exception_date_id) REFERENCES exception_dates (date_id),
            UNIQUE(committee_type_id, hativa_id, vaada_date)
        )
        """
        select_cols_vaadot = [
            "vaadot_id",
            "committee_type_id",
            "hativa_id",
            "vaada_date",
            # skip status
            "exception_date_id",
            "notes",
            "created_at",
            "is_deleted" if column_exists(cursor, "vaadot", "is_deleted") else "0 as is_deleted",
            "deleted_at" if column_exists(cursor, "vaadot", "deleted_at") else "NULL as deleted_at",
            "deleted_by" if column_exists(cursor, "vaadot", "deleted_by") else "NULL as deleted_by",
        ]
        drop_column_by_recreate(conn, "vaadot", ["status"], create_sql_vaadot, select_cols_vaadot)

    # 2) events: drop status if exists
    if column_exists(cursor, "events", "status"):
        create_sql_events = """
        CREATE TABLE events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vaadot_id INTEGER NOT NULL,
            maslul_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('kokok', 'shotef')),
            expected_requests INTEGER DEFAULT 0,
            call_publication_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            call_deadline_date DATE,
            intake_deadline_date DATE,
            review_deadline_date DATE,
            response_deadline_date DATE,
            is_call_deadline_manual INTEGER DEFAULT 0,
            actual_submissions INTEGER DEFAULT 0,
            scheduled_date DATE,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by INTEGER,
            FOREIGN KEY (vaadot_id) REFERENCES vaadot (vaadot_id) ON DELETE CASCADE,
            FOREIGN KEY (maslul_id) REFERENCES maslulim (maslul_id) ON DELETE CASCADE
        )
        """
        # Build select list, skipping status
        select_cols_events = [
            "event_id",
            "vaadot_id",
            "maslul_id",
            "name",
            "event_type",
            "expected_requests",
            "call_publication_date",
            "created_at",
            "call_deadline_date",
            "intake_deadline_date",
            "review_deadline_date",
            "response_deadline_date",
            "is_call_deadline_manual",
            "actual_submissions" if column_exists(cursor, "events", "actual_submissions") else "0 as actual_submissions",
            "scheduled_date" if column_exists(cursor, "events", "scheduled_date") else "NULL as scheduled_date",
            "is_deleted" if column_exists(cursor, "events", "is_deleted") else "0 as is_deleted",
            "deleted_at" if column_exists(cursor, "events", "deleted_at") else "NULL as deleted_at",
            "deleted_by" if column_exists(cursor, "events", "deleted_by") else "NULL as deleted_by",
        ]
        drop_column_by_recreate(conn, "events", ["status"], create_sql_events, select_cols_events)

    cursor.execute("PRAGMA foreign_keys=ON")
    conn.close()


def main():
    project_root = os.path.abspath(os.path.dirname(__file__) or ".")
    db_path = find_db(project_root)
    backup_path = backup_db(db_path)
    print(f"Backup created: {backup_path}")
    migrate(db_path)
    print("Migration completed successfully. You may VACUUM the database to reclaim space.")


if __name__ == "__main__":
    main()


