#!/usr/bin/env python3
"""
Script to update existing committee meetings with default times based on committee type.
- Regular committees (is_operational = 0): 09:00-15:00
- Operational committees (is_operational = 1): 09:00-11:00
"""
import sqlite3
import os
from datetime import datetime

def update_committee_times():
    """Update all existing committees that don't have times set"""

    # Get database path - use the same logic as the main application
    db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), db_path)

    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get all committees without times set
        cursor.execute('''
            SELECT
                v.vaadot_id,
                v.committee_type_id,
                ct.name,
                ct.is_operational,
                v.start_time,
                v.end_time,
                v.vaada_date
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            WHERE (v.start_time IS NULL OR v.end_time IS NULL)
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
            ORDER BY v.vaada_date
        ''')

        committees = cursor.fetchall()

        if not committees:
            print("✅ כל הועדות כבר מעודכנות עם שעות")
            print("   All committees already have times set")
            return

        print(f"\n📋 נמצאו {len(committees)} ועדות שצריכות עדכון")
        print(f"   Found {len(committees)} committees to update\n")

        updated_count = 0
        regular_count = 0
        operational_count = 0

        for vaadot_id, committee_type_id, name, is_operational, start_time, end_time, vaada_date in committees:
            # Determine default times based on committee type
            default_start = '09:00'
            default_end = '11:00' if is_operational else '15:00'

            # Use existing times if available, otherwise use defaults
            new_start = start_time if start_time else default_start
            new_end = end_time if end_time else default_end

            # Update the committee
            cursor.execute('''
                UPDATE vaadot
                SET start_time = ?, end_time = ?
                WHERE vaadot_id = ?
            ''', (new_start, new_end, vaadot_id))

            committee_type_name = "תפעולית" if is_operational else "רגילה"
            print(f"  ✓ עודכנה ועדה: {name} ({committee_type_name}) - תאריך: {vaada_date} - שעות: {new_start}-{new_end}")

            updated_count += 1
            if is_operational:
                operational_count += 1
            else:
                regular_count += 1

        conn.commit()

        print(f"\n✅ הושלם עדכון {updated_count} ועדות:")
        print(f"   • {regular_count} ועדות רגילות (09:00-15:00)")
        print(f"   • {operational_count} ועדות תפעוליות (09:00-11:00)")
        print(f"\n   Completed updating {updated_count} committees:")
        print(f"   • {regular_count} regular committees (09:00-15:00)")
        print(f"   • {operational_count} operational committees (09:00-11:00)")

    except Exception as e:
        conn.rollback()
        print(f"❌ שגיאה בעדכון: {e}")
        print(f"   Error during update: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("🕐 עדכון שעות ועדות קיימות / Updating existing committee times")
    print("=" * 70)
    update_committee_times()
    print("=" * 70)
