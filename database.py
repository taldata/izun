import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any

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
        
        self._migrate_database(cursor)
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hativot (
                hativa_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                color TEXT DEFAULT '#007bff',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maslulim (
                maslul_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hativa_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS committee_types (
                committee_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hativa_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                scheduled_day INTEGER NOT NULL,
                frequency TEXT NOT NULL DEFAULT 'weekly' CHECK (frequency IN ('weekly', 'monthly')),
                week_of_month INTEGER DEFAULT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE,
                UNIQUE(hativa_id, name)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vaadot (
                vaadot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                committee_type_id INTEGER NOT NULL,
                hativa_id INTEGER NOT NULL,
                vaada_date DATE NOT NULL,
                status TEXT DEFAULT 'planned',
                exception_date_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (committee_type_id) REFERENCES committee_types (committee_type_id),
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id),
                FOREIGN KEY (exception_date_id) REFERENCES exception_dates (date_id),
                UNIQUE(committee_type_id, hativa_id, vaada_date)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exception_dates (
                date_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_date DATE NOT NULL UNIQUE,
                description TEXT,
                type TEXT DEFAULT 'holiday',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vaadot_id INTEGER NOT NULL,
                maslul_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN ('kokok', 'shotef')),
                expected_requests INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vaadot_id) REFERENCES vaadot (vaadot_id) ON DELETE CASCADE,
                FOREIGN KEY (maslul_id) REFERENCES maslulim (maslul_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'user')),
                hativa_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description)
            VALUES 
                ('editing_period_active', '1', 'Whether general editing is allowed (1=yes, 0=admin only)'),
                ('academic_year_start', '2024-09-01', 'Start of current academic year'),
                ('editing_deadline', '2024-10-31', 'Deadline for general user editing'),
                ('work_days', '6,0,1,2,3,4', 'Working days (Python weekday: 0=Monday ... 6=Sunday)'),
                ('work_start_time', '08:00', 'Daily work start time'),
                ('work_end_time', '17:00', 'Daily work end time'),
                ('sla_days_before', '14', 'Default SLA days before committee meeting'),
                ('max_meetings_per_day', '1', 'Maximum number of committee meetings per calendar day'),
                ('max_weekly_meetings', '3', 'Maximum number of committee meetings per standard week'),
                ('max_third_week_meetings', '4', 'Maximum number of committee meetings during the third week of a month')
        ''')
        
        conn.commit()
        conn.close()
        
        self._create_default_admin()
        
    
    def _create_default_admin(self):
        """Create default admin user if no users exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            import hashlib
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin@example.com', password_hash, 'מנהל מערכת', 'admin', 1))
            
        
        conn.commit()
        conn.close()
    
    def _migrate_database(self, cursor):
        """Migrate existing database to add new columns if they don't exist"""
        try:
            cursor.execute("PRAGMA table_info(vaadot)")
            vaadot_columns = [column[1] for column in cursor.fetchall()]
            
            if 'vaada_date' not in vaadot_columns:
                cursor.execute('ALTER TABLE vaadot ADD COLUMN vaada_date DATE')
            
            if 'exception_date_id' not in vaadot_columns:
                cursor.execute('ALTER TABLE vaadot ADD COLUMN exception_date_id INTEGER REFERENCES exception_dates(date_id)')
            
            cursor.execute("PRAGMA table_info(committee_types)")
            committee_types_columns = [column[1] for column in cursor.fetchall()]
            
            if 'hativa_id' not in committee_types_columns:
                cursor.execute('ALTER TABLE committee_types ADD COLUMN hativa_id INTEGER DEFAULT 1')
            
            cursor.execute("PRAGMA table_info(hativot)")
            hativot_columns = [column[1] for column in cursor.fetchall()]
            
            if 'color' not in hativot_columns:
                cursor.execute('ALTER TABLE hativot ADD COLUMN color TEXT DEFAULT "#007bff"')
            
            tables_columns = {
                'hativot': [('is_active', 'INTEGER DEFAULT 1')],
                'maslulim': [('is_active', 'INTEGER DEFAULT 1'), ('sla_days', 'INTEGER DEFAULT 45')],
                'committee_types': [('is_active', 'INTEGER DEFAULT 1')]
            }
            
            for table_name, columns in tables_columns.items():
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = [column[1] for column in cursor.fetchall()]
                
                for column_name, column_def in columns:
                    if column_name not in existing_columns:
                        cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}')
                
        except Exception as e:
            print(f"Migration error: {e}")
    
    def add_hativa(self, name: str, description: str = "", color: str = "#007bff") -> int:
        """Add a new division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO hativot (name, description, color) VALUES (?, ?, ?)', (name, description, color))
        hativa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return hativa_id
    
    def get_hativot(self) -> List[Dict]:
        """Get all divisions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT hativa_id, name, description, color, is_active, created_at FROM hativot ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        
        return [{'hativa_id': row[0], 'name': row[1], 'description': row[2], 'color': row[3], 
                'is_active': row[4], 'created_at': row[5]} for row in rows]
    
    def update_hativa_color(self, hativa_id: int, color: str) -> bool:
        """Update division color"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE hativot SET color = ? WHERE hativa_id = ?', (color, hativa_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_hativa(self, hativa_id: int, name: str, description: str = "", color: str = "#007bff") -> bool:
        """Update division details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE hativot 
            SET name = ?, description = ?, color = ?
            WHERE hativa_id = ?
        ''', (name, description, color, hativa_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # Maslulim operations
    def add_maslul(self, hativa_id: int, name: str, description: str = "", sla_days: int = 45) -> int:
        """Add a new route to a division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO maslulim (hativa_id, name, description, sla_days) VALUES (?, ?, ?, ?)', 
                      (hativa_id, name, description, sla_days))
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
                'description': row[3], 'created_at': row[4], 'is_active': row[5], 
                'sla_days': row[6] if len(row) > 6 else 45, 
                'hativa_name': row[7] if len(row) > 7 else 'לא ידוע'} for row in rows]
    
    def update_maslul(self, maslul_id: int, name: str, description: str = "", sla_days: int = 45) -> bool:
        """Update an existing route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE maslulim 
            SET name = ?, description = ?, sla_days = ? 
            WHERE maslul_id = ?
        ''', (name, description, sla_days, maslul_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_maslul(self, maslul_id: int) -> bool:
        """Delete a route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM maslulim WHERE maslul_id = ?', (maslul_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
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
    
    # Committee Types operations
    def add_committee_type(self, hativa_id: int, name: str, scheduled_day: int, frequency: str = 'weekly', 
                          week_of_month: Optional[int] = None, description: str = "") -> int:
        """Add a new committee type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO committee_types (hativa_id, name, scheduled_day, frequency, week_of_month, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (hativa_id, name, scheduled_day, frequency, week_of_month, description))
        committee_type_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return committee_type_id
    
    def get_committee_types(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get committee types, optionally filtered by division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if hativa_id:
            cursor.execute('''
                SELECT ct.committee_type_id, ct.hativa_id, ct.name, ct.scheduled_day, 
                       ct.frequency, ct.week_of_month, ct.description, h.name as hativa_name 
                FROM committee_types ct
                JOIN hativot h ON ct.hativa_id = h.hativa_id
                WHERE ct.hativa_id = ?
                ORDER BY ct.scheduled_day
            ''', (hativa_id,))
        else:
            cursor.execute('''
                SELECT ct.committee_type_id, ct.hativa_id, ct.name, ct.scheduled_day, 
                       ct.frequency, ct.week_of_month, ct.description, h.name as hativa_name 
                FROM committee_types ct
                JOIN hativot h ON ct.hativa_id = h.hativa_id
                ORDER BY h.name, ct.scheduled_day
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום ראשון', 'יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת']
        
        return [{'committee_type_id': row[0], 'hativa_id': row[1], 'name': row[2], 'scheduled_day': row[3],
                'scheduled_day_name': days[row[3]], 'frequency': row[4], 
                'week_of_month': row[5], 'description': row[6], 'hativa_name': row[7]} for row in rows]
    
    def update_committee_type(self, committee_type_id: int, hativa_id: int, name: str, scheduled_day: int, 
                             frequency: str = 'weekly', week_of_month: Optional[int] = None, 
                             description: str = "") -> bool:
        """Update an existing committee type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE committee_types 
            SET hativa_id = ?, name = ?, scheduled_day = ?, frequency = ?, week_of_month = ?, description = ?
            WHERE committee_type_id = ?
        ''', (hativa_id, name, scheduled_day, frequency, week_of_month, description, committee_type_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_committee_type(self, committee_type_id: int) -> bool:
        """Delete a committee type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if there are any vaadot using this committee type
        cursor.execute('SELECT COUNT(*) FROM vaadot WHERE committee_type_id = ?', (committee_type_id,))
        vaadot_count = cursor.fetchone()[0]
        
        if vaadot_count > 0:
            conn.close()
            return False  # Cannot delete committee type with existing meetings
        
        cursor.execute('DELETE FROM committee_types WHERE committee_type_id = ?', (committee_type_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # Vaadot operations (specific meeting instances)
    def add_vaada(self, committee_type_id: int, hativa_id: int, vaada_date: date, 
                  status: str = 'planned', exception_date_id: Optional[int] = None, 
                  notes: str = "") -> int:
        """Add a specific committee meeting instance"""
        # Ensure meeting date is an allowed business day
        if not self.is_work_day(vaada_date):
            raise ValueError(f"התאריך {vaada_date} אינו יום עסקים חוקי לועדות")

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            constraint_settings = self.get_constraint_settings()

            max_per_day = constraint_settings['max_meetings_per_day']
            cursor.execute('''
                SELECT COUNT(*) FROM vaadot WHERE vaada_date = ?
            ''', (vaada_date,))
            existing_count = cursor.fetchone()[0]
            if existing_count >= max_per_day:
                if max_per_day == 1:
                    raise ValueError(f"כבר קיימת ועדה בתאריך {vaada_date}. לא ניתן לקבוע יותר מועדה אחת ביום.")
                raise ValueError(f"כבר קיימות {existing_count} ועדות בתאריך {vaada_date}. המגבלה הנוכחית מאפשרת עד {max_per_day} ועדות ביום.")

            week_start, week_end = self._get_week_bounds(vaada_date)
            weekly_count = self._count_meetings_in_week(cursor, week_start, week_end)
            weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
            if weekly_count >= weekly_limit:
                raise ValueError(f"השבוע של {vaada_date} כבר מכיל {weekly_count} ועדות (המגבלה היא {weekly_limit})")

            cursor.execute('''
                INSERT INTO vaadot (committee_type_id, hativa_id, vaada_date, status, exception_date_id, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (committee_type_id, hativa_id, vaada_date, status, exception_date_id, notes))
            vaadot_id = cursor.lastrowid
            conn.commit()
            return vaadot_id
        except ValueError:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            print(f"Error adding vaada: {e}")
            raise
        finally:
            conn.close()
    
    def is_date_available_for_meeting(self, vaada_date) -> bool:
        """Check if a date is available for a committee meeting (no existing meetings)"""
        # Convert string to date if needed
        if isinstance(vaada_date, str):
            from datetime import datetime
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM vaadot WHERE vaada_date = ?', (vaada_date,))
        count = cursor.fetchone()[0]
        conn.close()
        max_per_day = self.get_int_setting('max_meetings_per_day', 1)
        return count < max_per_day
    
    def get_vaadot(self, hativa_id: Optional[int] = None, start_date: Optional[date] = None, 
                   end_date: Optional[date] = None) -> List[Dict]:
        """Get committee meetings with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT v.*, ct.name as committee_name, h.name as hativa_name,
                   ed.exception_date, ed.description as exception_description, ed.type as exception_type
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            LEFT JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            WHERE 1=1
        '''
        params = []
        
        if hativa_id:
            query += ' AND v.hativa_id = ?'
            params.append(hativa_id)
        
        if start_date:
            query += ' AND v.vaada_date >= ?'
            params.append(start_date)
            
        if end_date:
            query += ' AND v.vaada_date <= ?'
            params.append(end_date)
            
        query += ' ORDER BY v.vaada_date, ct.name'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{'vaadot_id': row[0], 'committee_type_id': row[1], 'hativa_id': row[2],
                'vaada_date': row[3], 'status': row[4], 'exception_date_id': row[5],
                'notes': row[6], 'created_at': row[7], 'committee_name': row[8], 'hativa_name': row[9],
                'exception_date': row[10], 'exception_description': row[11], 
                'exception_type': row[12]} for row in rows]
    
    def update_vaada_date(self, vaadot_id: int, vaada_date: date, exception_date_id: Optional[int] = None) -> bool:
        """Update the actual meeting date for a committee and optionally link to exception date"""
        conn = None
        try:
            if not self.is_work_day(vaada_date):
                raise ValueError(f"התאריך {vaada_date} אינו יום עסקים חוקי לועדות")

            conn = self.get_connection()
            cursor = conn.cursor()

            # Enforce daily limit excluding the current meeting
            constraint_settings = self.get_constraint_settings()
            max_per_day = constraint_settings['max_meetings_per_day']
            cursor.execute('''
                SELECT COUNT(*) FROM vaadot
                WHERE vaada_date = ? AND vaadot_id != ?
            ''', (vaada_date, vaadot_id))
            existing_count = cursor.fetchone()[0]
            if existing_count >= max_per_day:
                raise ValueError(f"התאריך {vaada_date} כבר מכיל {existing_count} ועדות (המגבלה היא {max_per_day})")

            week_start, week_end = self._get_week_bounds(vaada_date)
            weekly_count = self._count_meetings_in_week(cursor, week_start, week_end, exclude_vaada_id=vaadot_id)
            weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
            if weekly_count >= weekly_limit:
                raise ValueError(f"השבוע של {vaada_date} כבר מכיל {weekly_count} ועדות (המגבלה היא {weekly_limit})")

            cursor.execute('''
                UPDATE vaadot 
                SET vaada_date = ?, exception_date_id = ?
                WHERE vaadot_id = ?
            ''', (vaada_date, exception_date_id, vaadot_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
        except ValueError:
            if conn:
                conn.rollback()
            raise
        except Exception as e:
            print(f"Error updating vaada date: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def _get_week_bounds(self, check_date: date) -> Tuple[date, date]:
        """Return start (Sunday) and end (Saturday) dates for the week of the given date."""
        days_since_sunday = (check_date.weekday() + 1) % 7
        week_start = check_date - timedelta(days=days_since_sunday)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    def _get_weekly_limit(self, check_date: date, constraint_settings: Dict[str, Any]) -> int:
        """Return the applicable weekly meeting limit for a given date."""
        limit = constraint_settings['max_weekly_meetings']
        if self._is_third_week_of_month(check_date):
            limit = constraint_settings['max_third_week_meetings']
        return limit

    def _count_meetings_in_week(self, cursor, week_start: date, week_end: date, exclude_vaada_id: Optional[int] = None) -> int:
        """Count meetings within a week range, optionally excluding a specific meeting."""
        query = '''
            SELECT COUNT(*) FROM vaadot
            WHERE vaada_date BETWEEN ? AND ?
        '''
        params = [week_start, week_end]
        if exclude_vaada_id is not None:
            query += ' AND vaadot_id != ?'
            params.append(exclude_vaada_id)
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else 0

    def _is_third_week_of_month(self, check_date: date) -> bool:
        """Return True if date falls within the third week of its month (Sunday-Saturday)."""
        first_day = date(check_date.year, check_date.month, 1)
        days_to_first_sunday = (6 - first_day.weekday()) % 7
        first_sunday = first_day + timedelta(days=days_to_first_sunday)
        third_week_start = first_sunday + timedelta(weeks=2)
        third_week_end = third_week_start + timedelta(days=6)
        return third_week_start <= check_date <= third_week_end
    
    def get_vaada_by_date(self, vaada_date: date) -> List[Dict]:
        """Get committees scheduled for a specific date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.vaadot_id, v.committee_type_id, v.hativa_id, v.vaada_date, v.status, v.notes, v.exception_date_id,
                   ct.name, ct.scheduled_day, ct.frequency, ct.week_of_month,
                   h.name as hativa_name,
                   ed.exception_date, ed.description as exception_description, ed.type as exception_type
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            LEFT JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            WHERE v.vaada_date = ?
            ORDER BY ct.scheduled_day
        ''', (vaada_date,))
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום ראשון', 'יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת']
        
        return [{'vaadot_id': row[0], 'committee_type_id': row[1], 'hativa_id': row[2], 'vaada_date': row[3], 
                'status': row[4], 'notes': row[5], 'exception_date_id': row[6],
                'committee_name': row[7], 'scheduled_day': row[8], 'frequency': row[9], 'week_of_month': row[10],
                'hativa_name': row[11], 'exception_date': row[12], 'exception_description': row[13], 
                'exception_type': row[14]} for row in rows]
    
    def get_vaadot_by_date_and_hativa(self, vaada_date: str, hativa_id: int) -> List[Dict]:
        """Get committees scheduled for a specific date and hativa"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.*, ct.name as committee_name, h.name as hativa_name
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            WHERE v.vaada_date = ? AND v.hativa_id = ?
        ''', (vaada_date, hativa_id))
        rows = cursor.fetchall()
        conn.close()
        
        return [{'vaadot_id': row[0], 'committee_type_id': row[1], 'hativa_id': row[2],
                'vaada_date': row[3], 'status': row[4], 'notes': row[5],
                'committee_name': row[6], 'hativa_name': row[7]} for row in rows]
    
    def get_vaadot_affected_by_exception(self, exception_date_id: int) -> List[Dict]:
        """Get committees affected by a specific exception date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.vaadot_id, v.committee_type_id, v.hativa_id, v.vaada_date, v.status, v.notes, v.exception_date_id,
                   ct.name, ct.scheduled_day, ct.frequency, ct.week_of_month,
                   h.name as hativa_name,
                   ed.exception_date, ed.description as exception_description, ed.type as exception_type
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            WHERE v.exception_date_id = ?
            ORDER BY ct.scheduled_day
        ''', (exception_date_id,))
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום ראשון', 'יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת']
        
        return [{'vaadot_id': row[0], 'committee_type_id': row[1], 'hativa_id': row[2], 'vaada_date': row[3], 
                'status': row[4], 'notes': row[5], 'exception_date_id': row[6],
                'committee_name': row[7], 'scheduled_day': row[8], 'frequency': row[9], 'week_of_month': row[10],
                'hativa_name': row[11], 'exception_date': row[12], 'exception_description': row[13], 
                'exception_type': row[14]} for row in rows]
    
    # Events operations
    def add_event(self, vaadot_id: int, maslul_id: int, name: str, event_type: str, expected_requests: int = 0) -> int:
        """Add a new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Validate that the route belongs to the same division as the committee
        cursor.execute('''
            SELECT v.hativa_id as vaada_hativa_id, m.hativa_id as maslul_hativa_id,
                   h1.name as vaada_hativa_name, h2.name as maslul_hativa_name,
                   ct.name as committee_name, m.name as maslul_name
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h1 ON v.hativa_id = h1.hativa_id
            JOIN maslulim m ON m.maslul_id = ?
            JOIN hativot h2 ON m.hativa_id = h2.hativa_id
            WHERE v.vaadot_id = ?
        ''', (maslul_id, vaadot_id))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError("ועדה או מסלול לא נמצאו במערכת")
        
        vaada_hativa_id, maslul_hativa_id, vaada_hativa_name, maslul_hativa_name, committee_name, maslul_name = result
        
        if vaada_hativa_id != maslul_hativa_id:
            conn.close()
            raise ValueError(f'המסלול "{maslul_name}" מחטיבת "{maslul_hativa_name}" אינו יכול להיות משויך לועדה "{committee_name}" מחטיבת "{vaada_hativa_name}"')
        
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
                SELECT e.*, ct.name as committee_name, v.vaada_date, vh.name as vaada_hativa_name, 
                       m.name as maslul_name, h.name as hativa_name
                FROM events e
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
                JOIN hativot vh ON v.hativa_id = vh.hativa_id
                JOIN maslulim m ON e.maslul_id = m.maslul_id
                JOIN hativot h ON m.hativa_id = h.hativa_id
                WHERE e.vaadot_id = ?
                ORDER BY e.created_at DESC
            ''', (vaadot_id,))
        else:
            cursor.execute('''
                SELECT e.*, ct.name as committee_name, v.vaada_date, vh.name as vaada_hativa_name,
                       m.name as maslul_name, h.name as hativa_name
                FROM events e
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
                JOIN hativot vh ON v.hativa_id = vh.hativa_id
                JOIN maslulim m ON e.maslul_id = m.maslul_id
                JOIN hativot h ON m.hativa_id = h.hativa_id
                ORDER BY e.created_at DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'event_id': row[0], 'vaadot_id': row[1], 'maslul_id': row[2], 'name': row[3],
                'event_type': row[4], 'expected_requests': row[5], 'scheduled_date': row[6],
                'status': row[7], 'created_at': row[8], 'committee_name': row[9], 'vaada_date': row[10], 
                'vaada_hativa_name': row[11], 'maslul_name': row[12], 'hativa_name': row[13]} for row in rows]
    
    def update_event(self, event_id: int, vaadot_id: int, maslul_id: int, name: str, event_type: str, expected_requests: int = 0) -> bool:
        """Update an existing event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Validate that the route belongs to the same division as the committee
        cursor.execute('''
            SELECT v.hativa_id as vaada_hativa_id, m.hativa_id as maslul_hativa_id,
                   h1.name as vaada_hativa_name, h2.name as maslul_hativa_name,
                   ct.name as committee_name, m.name as maslul_name
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h1 ON v.hativa_id = h1.hativa_id
            JOIN maslulim m ON m.maslul_id = ?
            JOIN hativot h2 ON m.hativa_id = h2.hativa_id
            WHERE v.vaadot_id = ?
        ''', (maslul_id, vaadot_id))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError("ועדה או מסלול לא נמצאו במערכת")
        
        vaada_hativa_id, maslul_hativa_id, vaada_hativa_name, maslul_hativa_name, committee_name, maslul_name = result
        
        if vaada_hativa_id != maslul_hativa_id:
            conn.close()
            raise ValueError(f'המסלול "{maslul_name}" מחטיבת "{maslul_hativa_name}" אינו יכול להיות משויך לועדה "{committee_name}" מחטיבת "{vaada_hativa_name}"')
        
        cursor.execute('''
            UPDATE events 
            SET vaadot_id = ?, maslul_id = ?, name = ?, event_type = ?, expected_requests = ?
            WHERE event_id = ?
        ''', (vaadot_id, maslul_id, name, event_type, expected_requests, event_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # User Management and Permissions
    def create_user(self, username: str, email: str, password_hash: str, full_name: str, 
                   role: str = 'user', hativa_id: Optional[int] = None) -> int:
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, hativa_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, role, hativa_id))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, h.name as hativa_name
            FROM users u
            LEFT JOIN hativot h ON u.hativa_id = h.hativa_id
            WHERE u.username = ? AND u.is_active = 1
        ''', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0], 'username': row[1], 'email': row[2], 'password_hash': row[3],
                'full_name': row[4], 'role': row[5], 'hativa_id': row[6], 'is_active': row[7],
                'created_at': row[8], 'last_login': row[9], 'hativa_name': row[10]
            }
        return None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    def get_all_users(self) -> List[Dict]:
        """Get all users with their division information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.email, u.full_name, u.role, 
                   u.hativa_id, h.name as hativa_name, u.is_active, 
                   u.created_at, u.last_login
            FROM users u
            LEFT JOIN hativot h ON u.hativa_id = h.hativa_id
            ORDER BY u.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'user_id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'role': row[4],
                'hativa_id': row[5],
                'hativa_name': row[6],
                'is_active': row[7],
                'created_at': row[8],
                'last_login': row[9]
            })
        return users
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, h.name as hativa_name
            FROM users u
            LEFT JOIN hativot h ON u.hativa_id = h.hativa_id
            WHERE u.user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0], 'username': row[1], 'email': row[2], 'password_hash': row[3],
                'full_name': row[4], 'role': row[5], 'hativa_id': row[6], 'is_active': row[7],
                'created_at': row[8], 'last_login': row[9], 'hativa_name': row[10]
            }
        return None
    
    def update_user(self, user_id: int, username: str, email: str, full_name: str, 
                   role: str, hativa_id: Optional[int] = None) -> bool:
        """Update user information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET username = ?, email = ?, full_name = ?, role = ?, hativa_id = ?
                WHERE user_id = ?
            ''', (username, email, full_name, role, hativa_id, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def toggle_user_status(self, user_id: int) -> bool:
        """Toggle user active status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error toggling user status: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete by setting is_active to 0)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET is_active = 0 WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def check_username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username already exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if exclude_user_id:
            cursor.execute('''
                SELECT COUNT(*) FROM users WHERE username = ? AND user_id != ?
            ''', (username, exclude_user_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM users WHERE username = ?
            ''', (username,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def check_email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email already exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if exclude_user_id:
            cursor.execute('''
                SELECT COUNT(*) FROM users WHERE email = ? AND user_id != ?
            ''', (email, exclude_user_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM users WHERE email = ?
            ''', (email,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def change_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """Change user password"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE user_id = ?
            ''', (new_password_hash, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
            return False
    
    def get_system_setting(self, setting_key: str) -> Optional[str]:
        """Get system setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT setting_value FROM system_settings WHERE setting_key = ?
        ''', (setting_key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def update_system_setting(self, setting_key: str, setting_value: str, user_id: int):
        """Update system setting"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE system_settings 
            SET setting_value = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
            WHERE setting_key = ?
        ''', (setting_value, user_id, setting_key))
        conn.commit()
        conn.close()

    def get_int_setting(self, setting_key: str, default: int) -> int:
        """Get an integer system setting with fallback"""
        value = self.get_system_setting(setting_key)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_constraint_settings(self) -> Dict[str, Any]:
        """Return parsed constraint settings for the scheduling system"""
        return {
            'work_days': self.get_work_days(),
            'max_meetings_per_day': self.get_int_setting('max_meetings_per_day', 1),
            'max_weekly_meetings': self.get_int_setting('max_weekly_meetings', 3),
            'max_third_week_meetings': self.get_int_setting('max_third_week_meetings', 4)
        }
    
    def is_editing_allowed(self, user_role: str) -> bool:
        """Check if editing is allowed for user role"""
        # Admins can always edit
        if user_role == 'admin':
            return True
        
        # Check if general editing period is active
        editing_active = self.get_system_setting('editing_period_active')
        return editing_active == '1'
    
    def can_user_edit(self, user_role: str, target_hativa_id: Optional[int] = None, 
                     user_hativa_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Check if user can edit based on role and editing period
        Returns (can_edit, reason)
        """
        # Admin can always edit everything
        if user_role == 'admin':
            return True, "מנהל מערכת"
        
        # Check if general editing is allowed
        if not self.is_editing_allowed(user_role):
            return False, "תקופת העריכה הכללית הסתיימה. רק מנהלי מערכת יכולים לערוך"
        
        # Manager can edit within their division
        if user_role == 'manager':
            if target_hativa_id and user_hativa_id and target_hativa_id != user_hativa_id:
                return False, "מנהל יכול לערוך רק בחטיבה שלו"
            return True, "מנהל חטיבה"
        
        # Regular user can edit within their division during editing period
        if user_role == 'user':
            if target_hativa_id and user_hativa_id and target_hativa_id != user_hativa_id:
                return False, "משתמש יכול לערוך רק בחטיבה שלו"
            return True, "תקופת עריכה פעילה"
        
        return False, "הרשאות לא מספיקות"
    
    # Soft Delete Functions (Alternative to hard delete)
    def deactivate_hativa(self, hativa_id: int) -> bool:
        """Deactivate division instead of deleting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE hativot SET is_active = 0 WHERE hativa_id = ?', (hativa_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def activate_hativa(self, hativa_id: int) -> bool:
        """Reactivate division"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE hativot SET is_active = 1 WHERE hativa_id = ?', (hativa_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def deactivate_maslul(self, maslul_id: int) -> bool:
        """Deactivate route instead of deleting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE maslulim SET is_active = 0 WHERE maslul_id = ?', (maslul_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def activate_maslul(self, maslul_id: int) -> bool:
        """Reactivate route"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE maslulim SET is_active = 1 WHERE maslul_id = ?', (maslul_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def deactivate_committee_type(self, committee_type_id: int) -> bool:
        """Deactivate committee type instead of deleting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE committee_types SET is_active = 0 WHERE committee_type_id = ?', (committee_type_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def activate_committee_type(self, committee_type_id: int) -> bool:
        """Reactivate committee type"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE committee_types SET is_active = 1 WHERE committee_type_id = ?', (committee_type_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    # Updated get functions to filter by active status
    def get_hativot_active_only(self) -> List[Dict]:
        """Get only active divisions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT hativa_id, name, description, color, is_active, created_at FROM hativot WHERE is_active = 1 ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        return [{'hativa_id': row[0], 'name': row[1], 'description': row[2], 'color': row[3],
                'is_active': row[4], 'created_at': row[5]} for row in rows]
    
    def get_maslulim_active_only(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get only active routes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if hativa_id:
            cursor.execute('''
                SELECT m.*, h.name as hativa_name 
                FROM maslulim m 
                JOIN hativot h ON m.hativa_id = h.hativa_id 
                WHERE m.hativa_id = ? AND m.is_active = 1 AND h.is_active = 1
                ORDER BY m.name
            ''', (hativa_id,))
        else:
            cursor.execute('''
                SELECT m.*, h.name as hativa_name 
                FROM maslulim m 
                JOIN hativot h ON m.hativa_id = h.hativa_id 
                WHERE m.is_active = 1 AND h.is_active = 1
                ORDER BY h.name, m.name
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        return [{'maslul_id': row[0], 'hativa_id': row[1], 'name': row[2], 
                'description': row[3], 'created_at': row[4], 'is_active': row[5], 
                'sla_days': row[6] if len(row) > 6 else 45, 
                'hativa_name': row[7] if len(row) > 7 else 'לא ידוע'} for row in rows]
    
    def get_committee_types_active_only(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get only active committee types"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if hativa_id:
            cursor.execute('''
                SELECT ct.*, h.name as hativa_name 
                FROM committee_types ct 
                JOIN hativot h ON ct.hativa_id = h.hativa_id 
                WHERE ct.hativa_id = ? AND ct.is_active = 1 AND h.is_active = 1
                ORDER BY ct.name
            ''', (hativa_id,))
        else:
            cursor.execute('''
                SELECT ct.*, h.name as hativa_name 
                FROM committee_types ct 
                JOIN hativot h ON ct.hativa_id = h.hativa_id 
                WHERE ct.is_active = 1 AND h.is_active = 1
                ORDER BY h.name, ct.name
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        return [{'committee_type_id': row[0], 'hativa_id': row[1], 'name': row[2], 
                'scheduled_day': row[3], 'frequency': row[4], 'week_of_month': row[5],
                'is_active': row[6], 'created_at': row[7], 'hativa_name': row[8]} for row in rows]
    
    # Enhanced Business Days and SLA Calculations
    def get_work_days(self) -> List[int]:
        """Get configured work days"""
        work_days_str = self.get_system_setting('work_days') or '6,0,1,2,3,4'
        return [int(day) for day in work_days_str.split(',')]

    def get_meetings_count_on_date(self, vaada_date: Any) -> int:
        """Get the number of meetings scheduled for a specific date"""
        if isinstance(vaada_date, str):
            vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM vaadot WHERE vaada_date = ?', (vaada_date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_meetings_count_in_range(self, start_date: date, end_date: date) -> int:
        """Get number of meetings in an inclusive date range"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM vaadot 
            WHERE vaada_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def is_work_day(self, check_date: date) -> bool:
        """Check if date is a work day (not weekend, not holiday, configured work days)"""
        # Check if it's a configured work day
        work_days = self.get_work_days()
        if check_date.weekday() not in work_days:
            return False
        
        # Check if it's an exception date (holiday, special sabbath, etc.)
        return not self.is_exception_date(check_date)
    
    def get_business_days_in_range(self, start_date: date, end_date: date) -> List[date]:
        """Get all business days in a date range"""
        business_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_work_day(current_date):
                business_days.append(current_date)
            current_date += timedelta(days=1)
        
        return business_days
    
    def add_business_days(self, start_date: date, days_to_add: int) -> date:
        """Add business days to a date (skipping weekends and holidays)"""
        current_date = start_date
        days_added = 0
        
        while days_added < days_to_add:
            current_date += timedelta(days=1)
            if self.is_work_day(current_date):
                days_added += 1
        
        return current_date
    
    def subtract_business_days(self, start_date: date, days_to_subtract: int) -> date:
        """Subtract business days from a date (skipping weekends and holidays)"""
        current_date = start_date
        days_subtracted = 0
        
        while days_subtracted < days_to_subtract:
            current_date -= timedelta(days=1)
            if self.is_work_day(current_date):
                days_subtracted += 1
        
        return current_date
    
    def calculate_sla_dates(self, committee_date: date, sla_days: Optional[int] = None) -> Dict:
        """Calculate SLA dates based on committee meeting date"""
        if sla_days is None:
            sla_days = int(self.get_system_setting('sla_days_before') or '14')
        
        # Calculate key SLA milestones
        sla_dates = {
            'committee_date': committee_date,
            'sla_days': sla_days,
            'request_deadline': self.subtract_business_days(committee_date, sla_days),
            'preparation_start': self.subtract_business_days(committee_date, sla_days + 7),
            'notification_date': self.subtract_business_days(committee_date, sla_days + 14)
        }
        
        # Add business days count
        sla_dates['business_days_to_committee'] = len(
            self.get_business_days_in_range(date.today(), committee_date)
        )
        
        return sla_dates
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """Get event by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, m.name as maslul_name, m.hativa_id,
                       v.vaada_date, ct.name as committee_name, h.name as hativa_name
                FROM events e
                JOIN maslulim m ON e.maslul_id = m.maslul_id
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
                JOIN hativot h ON m.hativa_id = h.hativa_id
                WHERE e.event_id = ?
            """, (event_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'event_id': row[0],
                    'vaadot_id': row[1],
                    'maslul_id': row[2],
                    'name': row[3],
                    'event_type': row[4],
                    'expected_requests': row[5],
                    'scheduled_date': row[6],
                    'status': row[7],
                    'created_at': row[8],
                    'maslul_name': row[9],
                    'hativa_id': row[10],
                    'vaada_date': row[11],
                    'committee_name': row[12],
                    'hativa_name': row[13]
                }
            return None
        except Exception as e:
            print(f"Error getting event by ID: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def get_vaada_by_id(self, vaada_id: int) -> Optional[Dict]:
        """Get committee meeting by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, ct.name as committee_name, h.name as hativa_name
                FROM vaadot v
                JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
                JOIN hativot h ON v.hativa_id = h.hativa_id
                WHERE v.vaadot_id = ?
            """, (vaada_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'vaadot_id': row[0],
                    'committee_type_id': row[1],
                    'hativa_id': row[2],
                    'vaada_date': row[3],
                    'status': row[4],
                    'exception_date_id': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'committee_name': row[8],
                    'hativa_name': row[9]
                }
            return None
        except Exception as e:
            print(f"Error getting vaada by ID: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def get_maslul_by_id(self, maslul_id: int) -> Optional[Dict]:
        """Get route by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, h.name as hativa_name
                FROM maslulim m
                JOIN hativot h ON m.hativa_id = h.hativa_id
                WHERE m.maslul_id = ?
            """, (maslul_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'maslul_id': row[0],
                    'hativa_id': row[1],
                    'name': row[2],
                    'description': row[3],
                    'created_at': row[4],
                    'is_active': row[5],
                    'sla_days': row[6],
                    'hativa_name': row[7]
                }
            return None
        except Exception as e:
            print(f"Error getting maslul by ID: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def update_event_vaada(self, event_id: int, new_vaada_id: int) -> bool:
        """Update event's committee meeting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE events 
                SET vaadot_id = ?
                WHERE event_id = ?
            """, (new_vaada_id, event_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error updating event vaada: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
