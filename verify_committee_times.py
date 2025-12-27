#!/usr/bin/env python3
"""
Script to verify that committee times are set correctly
"""
import sqlite3
import os

def verify_committee_times():
    """Verify committee times are set correctly"""

    db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check committees without times
        cursor.execute('''
            SELECT COUNT(*) FROM vaadot
            WHERE (start_time IS NULL OR end_time IS NULL)
              AND (is_deleted = 0 OR is_deleted IS NULL)
        ''')
        missing_times = cursor.fetchone()[0]

        print(f"ועדות ללא שעות: {missing_times}")
        print(f"Committees without times: {missing_times}\n")

        # Get sample of committees with times
        cursor.execute('''
            SELECT
                ct.name,
                ct.is_operational,
                v.vaada_date,
                v.start_time,
                v.end_time
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            WHERE v.start_time IS NOT NULL AND v.end_time IS NOT NULL
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
            ORDER BY v.vaada_date
            LIMIT 10
        ''')

        print("דוגמאות לועדות עם שעות / Sample committees with times:")
        print("-" * 80)
        for name, is_operational, date, start, end in cursor.fetchall():
            committee_type = "תפעולית" if is_operational else "רגילה"
            print(f"  {name:20} ({committee_type:10}) {date} -> {start}-{end}")

        # Statistics
        cursor.execute('''
            SELECT
                ct.is_operational,
                COUNT(*) as count,
                v.start_time,
                v.end_time
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            WHERE (v.is_deleted = 0 OR v.is_deleted IS NULL)
            GROUP BY ct.is_operational, v.start_time, v.end_time
            ORDER BY ct.is_operational, v.start_time
        ''')

        print("\n" + "=" * 80)
        print("סטטיסטיקות / Statistics:")
        print("=" * 80)
        for is_operational, count, start, end in cursor.fetchall():
            committee_type = "תפעולית" if is_operational else "רגילה"
            print(f"  {committee_type:15} {start or 'NULL':8} - {end or 'NULL':8}  ({count:3} ועדות)")

    finally:
        conn.close()

if __name__ == '__main__':
    verify_committee_times()
