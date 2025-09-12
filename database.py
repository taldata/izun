import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

class DatabaseManager:
    def __init__(self, db_path: str = "committee_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Hativot (Divisions) table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hativot (
                hativa_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Maslulim (Routes) table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maslulim (
                maslul_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hativa_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id)
            )
        ''')
        
        # Vaadot (Committees) table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vaadot (
                vaadot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                scheduled_day INTEGER NOT NULL, -- 0=Monday, 1=Tuesday, etc.
                frequency TEXT DEFAULT 'weekly', -- weekly, monthly
                week_of_month INTEGER DEFAULT NULL, -- for monthly committees (1-4)
                vaada_date DATE, -- actual date of the committee meeting
                exception_date_id INTEGER, -- reference to exception_dates if meeting is affected
                hativa_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id),
                FOREIGN KEY (exception_date_id) REFERENCES exception_dates (date_id)
            )
        ''')
        
        # Exception dates table (holidays, sabbaths, special non-working days)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exception_dates (
                date_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_date DATE NOT NULL UNIQUE,
                description TEXT,
                type TEXT DEFAULT 'holiday', -- holiday, sabbath, special
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vaadot_id INTEGER NOT NULL,
                maslul_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                event_type TEXT NOT NULL, -- 'kokok' or 'shotef'
                expected_requests INTEGER DEFAULT 0,
                scheduled_date DATE,
                status TEXT DEFAULT 'planned', -- planned, scheduled, completed, cancelled
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vaadot_id) REFERENCES vaadot (vaadot_id),
                FOREIGN KEY (maslul_id) REFERENCES maslulim (maslul_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Insert default committees
        self._insert_default_committees()
    
    def _insert_default_committees(self):
        """Insert the default committees with their scheduled days"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        default_committees = [
            ('ועדת הזנק', 0),  # Monday
            ('ועדת תשתיות', 2),  # Wednesday  
            ('ועדת צמיחה', 3),  # Thursday
            ('ייצור מתקדם', 1)   # Tuesday (monthly, third week)
        ]
        
        for name, day in default_committees:
            frequency = 'monthly' if name == 'ייצור מתקדם' else 'weekly'
            week_of_month = 3 if name == 'ייצור מתקדם' else None
            
            cursor.execute('''
                INSERT OR IGNORE INTO vaadot (name, scheduled_day, frequency, week_of_month)
                VALUES (?, ?, ?, ?)
            ''', (name, day, frequency, week_of_month))
        
        conn.commit()
        conn.close()
    
    # Hativot operations
    def add_hativa(self, name: str, description: str = "") -> int:
        """Add a new division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO hativot (name, description) VALUES (?, ?)', (name, description))
        hativa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return hativa_id
    
    def get_hativot(self) -> List[Dict]:
        """Get all divisions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM hativot ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        
        return [{'hativa_id': row[0], 'name': row[1], 'description': row[2]} for row in rows]
    
    # Maslulim operations
    def add_maslul(self, hativa_id: int, name: str, description: str = "") -> int:
        """Add a new route to a division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO maslulim (hativa_id, name, description) VALUES (?, ?, ?)', 
                      (hativa_id, name, description))
        maslul_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return maslul_id
    
    def get_maslulim(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get routes, optionally filtered by division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if hativa_id:
            cursor.execute('''
                SELECT m.*, h.name as hativa_name 
                FROM maslulim m 
                JOIN hativot h ON m.hativa_id = h.hativa_id 
                WHERE m.hativa_id = ? 
                ORDER BY m.name
            ''', (hativa_id,))
        else:
            cursor.execute('''
                SELECT m.*, h.name as hativa_name 
                FROM maslulim m 
                JOIN hativot h ON m.hativa_id = h.hativa_id 
                ORDER BY h.name, m.name
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'maslul_id': row[0], 'hativa_id': row[1], 'name': row[2], 
                'description': row[3], 'hativa_name': row[5]} for row in rows]
    
    # Exception dates operations
    def add_exception_date(self, exception_date: date, description: str = "", date_type: str = "holiday"):
        """Add an exception date (holiday, sabbath, etc.)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO exception_dates (exception_date, description, type) VALUES (?, ?, ?)', 
                      (exception_date, description, date_type))
        conn.commit()
        conn.close()
    
    def get_exception_dates(self) -> List[Dict]:
        """Get all exception dates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM exception_dates ORDER BY exception_date')
        rows = cursor.fetchall()
        conn.close()
        
        return [{'date_id': row[0], 'exception_date': row[1], 'description': row[2], 'type': row[3]} for row in rows]
    
    def is_exception_date(self, check_date: date) -> bool:
        """Check if a date is an exception date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM exception_dates WHERE exception_date = ?', (check_date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    # Vaadot operations
    def get_vaadot(self) -> List[Dict]:
        """Get all committees"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.*, ed.exception_date, ed.description as exception_description, ed.type as exception_type
            FROM vaadot v
            LEFT JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            ORDER BY v.scheduled_day
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
        
        return [{'vaadot_id': row[0], 'name': row[1], 'scheduled_day': row[2], 
                'scheduled_day_name': days[row[2]], 'frequency': row[3], 
                'week_of_month': row[4], 'vaada_date': row[5], 'exception_date_id': row[6],
                'exception_date': row[9], 'exception_description': row[10], 
                'exception_type': row[11]} for row in rows]
    
    def update_vaada_date(self, vaadot_id: int, vaada_date: date, exception_date_id: Optional[int] = None):
        """Update the actual meeting date for a committee and optionally link to exception date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE vaadot 
            SET vaada_date = ?, exception_date_id = ?
            WHERE vaadot_id = ?
        ''', (vaada_date, exception_date_id, vaadot_id))
        conn.commit()
        conn.close()
    
    def get_vaada_by_date(self, vaada_date: date) -> List[Dict]:
        """Get committees scheduled for a specific date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.*, ed.exception_date, ed.description as exception_description, ed.type as exception_type
            FROM vaadot v
            LEFT JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            WHERE v.vaada_date = ?
            ORDER BY v.scheduled_day
        ''', (vaada_date,))
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
        
        return [{'vaadot_id': row[0], 'name': row[1], 'scheduled_day': row[2], 
                'scheduled_day_name': days[row[2]], 'frequency': row[3], 
                'week_of_month': row[4], 'vaada_date': row[5], 'exception_date_id': row[6],
                'exception_date': row[9], 'exception_description': row[10], 
                'exception_type': row[11]} for row in rows]
    
    def get_vaadot_affected_by_exception(self, exception_date_id: int) -> List[Dict]:
        """Get committees affected by a specific exception date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.*, ed.exception_date, ed.description as exception_description, ed.type as exception_type
            FROM vaadot v
            JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            WHERE v.exception_date_id = ?
            ORDER BY v.scheduled_day
        ''', (exception_date_id,))
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
        
        return [{'vaadot_id': row[0], 'name': row[1], 'scheduled_day': row[2], 
                'scheduled_day_name': days[row[2]], 'frequency': row[3], 
                'week_of_month': row[4], 'vaada_date': row[5], 'exception_date_id': row[6],
                'exception_date': row[9], 'exception_description': row[10], 
                'exception_type': row[11]} for row in rows]
    
    # Events operations
    def add_event(self, vaadot_id: int, maslul_id: int, name: str, event_type: str, expected_requests: int = 0) -> int:
        """Add a new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (vaadot_id, maslul_id, name, event_type, expected_requests)
            VALUES (?, ?, ?, ?, ?)
        ''', (vaadot_id, maslul_id, name, event_type, expected_requests))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_events(self, vaadot_id: Optional[int] = None) -> List[Dict]:
        """Get events, optionally filtered by committee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if vaadot_id:
            cursor.execute('''
                SELECT e.*, v.name as vaadot_name, m.name as maslul_name, h.name as hativa_name
                FROM events e
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                JOIN maslulim m ON e.maslul_id = m.maslul_id
                JOIN hativot h ON m.hativa_id = h.hativa_id
                WHERE e.vaadot_id = ?
                ORDER BY e.created_at DESC
            ''', (vaadot_id,))
        else:
            cursor.execute('''
                SELECT e.*, v.name as vaadot_name, m.name as maslul_name, h.name as hativa_name
                FROM events e
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                JOIN maslulim m ON e.maslul_id = m.maslul_id
                JOIN hativot h ON m.hativa_id = h.hativa_id
                ORDER BY e.created_at DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'event_id': row[0], 'vaadot_id': row[1], 'maslul_id': row[2], 'name': row[3],
                'event_type': row[4], 'expected_requests': row[5], 'scheduled_date': row[6],
                'status': row[7], 'vaadot_name': row[9], 'maslul_name': row[10], 
                'hativa_name': row[11]} for row in rows]
