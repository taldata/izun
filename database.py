import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any

from zoneinfo import ZoneInfo


ISRAEL_TZ = ZoneInfo('Asia/Jerusalem')

class DatabaseManager:
    def __init__(self, db_path: str = None):
        # Use environment variable for database path, with fallback to local development path
        if db_path is None:
            db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
        self.db_path = db_path
        # Ensure directory exists for database file
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            try:
                if not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                # On Render, /var/data might not be available during build phase
                # This is okay - it will be available during runtime
                print(f"Note: Could not create directory {db_dir}: {e}")
                # Don't fail - the directory might already exist or will be created later
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
                call_publication_date DATE,
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
                password_hash TEXT,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'user')),
                hativa_id INTEGER,
                is_active INTEGER DEFAULT 1,
                auth_source TEXT DEFAULT 'local' CHECK (auth_source IN ('local', 'ad')),
                ad_dn TEXT,
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
        
        # Create audit logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                entity_name TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                status TEXT DEFAULT 'success',
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create index for faster log queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs (user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs (entity_type, entity_id)
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
                ('max_third_week_meetings', '4', 'Maximum number of committee meetings during the third week of a month'),
                ('max_requests_per_day', '100', 'Maximum total expected requests per day across all events'),
                ('show_deadline_dates_in_calendar', '1', 'Show derived deadline dates in calendar (1=yes, 0=no)'),
                ('rec_base_score', '100', 'Committee recommendation base score'),
                ('rec_best_bonus', '25', 'Bonus for best recommendation'),
                ('rec_space_bonus', '10', 'Bonus for available space'),
                ('rec_sla_bonus', '20', 'Maximum bonus for SLA buffer'),
                ('rec_optimal_range_bonus', '15', 'Bonus for optimal time range'),
                ('rec_no_events_bonus', '5', 'Bonus for committee with no events'),
                ('rec_high_load_penalty', '15', 'Penalty for high event load (7+ events)'),
                ('rec_medium_load_penalty', '5', 'Penalty for medium event load (4-6 events)'),
                ('rec_no_space_penalty', '50', 'Penalty for no available space'),
                ('rec_no_sla_penalty', '30', 'Penalty for insufficient SLA time'),
                ('rec_tight_sla_penalty', '10', 'Penalty for tight SLA time'),
                ('rec_far_future_penalty', '10', 'Penalty for dates too far in future'),
                ('rec_week_full_penalty', '20', 'Penalty for full week'),
                ('rec_optimal_range_start', '0', 'Optimal range start (days after SLA)'),
                ('rec_optimal_range_end', '30', 'Optimal range end (days after SLA)'),
                ('rec_far_future_threshold', '60', 'Days considered too far in future (after optimal range)'),
                ('ad_enabled', '0', 'Enable Active Directory authentication (1=yes, 0=no)'),
                ('ad_server_url', '', 'Active Directory server URL (e.g., ad.domain.com)'),
                ('ad_port', '636', 'AD server port (636 for LDAPS, 389 for LDAP)'),
                ('ad_use_ssl', '1', 'Use SSL/LDAPS (1=yes, 0=no)'),
                ('ad_use_tls', '0', 'Use STARTTLS (1=yes, 0=no)'),
                ('ad_base_dn', '', 'Base DN (e.g., DC=domain,DC=com)'),
                ('ad_bind_dn', '', 'Service account DN for binding'),
                ('ad_bind_password', '', 'Service account password'),
                ('ad_user_search_base', '', 'User search base DN (defaults to base_dn)'),
                ('ad_user_search_filter', '(sAMAccountName={username})', 'LDAP filter for user search'),
                ('ad_group_search_base', '', 'Group search base DN (defaults to base_dn)'),
                ('ad_admin_group', '', 'AD group name/DN for admin role'),
                ('ad_manager_group', '', 'AD group name/DN for manager role'),
                ('ad_auto_create_users', '1', 'Automatically create users on first AD login (1=yes, 0=no)'),
                ('ad_default_hativa_id', '', 'Default division ID for new AD users'),
                ('ad_sync_on_login', '1', 'Sync user info from AD on each login (1=yes, 0=no)')
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
            
            # Migrate users table for AD support
            cursor.execute("PRAGMA table_info(users)")
            users_columns = [column[1] for column in cursor.fetchall()]
            
            if 'auth_source' not in users_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN auth_source TEXT DEFAULT 'local' CHECK (auth_source IN ('local', 'ad'))")
            
            if 'ad_dn' not in users_columns:
                cursor.execute('ALTER TABLE users ADD COLUMN ad_dn TEXT')
            
            tables_columns = {
                'hativot': [('is_active', 'INTEGER DEFAULT 1')],
                'maslulim': [
                    ('is_active', 'INTEGER DEFAULT 1'), 
                    ('sla_days', 'INTEGER DEFAULT 45'),
                    ('stage_a_days', 'INTEGER DEFAULT 10'),
                    ('stage_b_days', 'INTEGER DEFAULT 15'),
                    ('stage_c_days', 'INTEGER DEFAULT 10'),
                    ('stage_d_days', 'INTEGER DEFAULT 10'),
                    ('stage_a_easy_days', 'INTEGER DEFAULT 5'),
                    ('stage_a_review_days', 'INTEGER DEFAULT 5'),
                    ('stage_b_easy_days', 'INTEGER DEFAULT 8'),
                    ('stage_b_review_days', 'INTEGER DEFAULT 7'),
                    ('stage_c_easy_days', 'INTEGER DEFAULT 5'),
                    ('stage_c_review_days', 'INTEGER DEFAULT 5'),
                    ('stage_d_easy_days', 'INTEGER DEFAULT 5'),
                    ('stage_d_review_days', 'INTEGER DEFAULT 5'),
                    ('call_publication_date', 'DATE')
                ],
                'committee_types': [
                    ('is_active', 'INTEGER DEFAULT 1'),
                    ('description', 'TEXT')
                ],
                'events': [
                    ('call_publication_date', 'DATE'),
                    ('call_deadline_date', 'DATE'),
                    ('intake_deadline_date', 'DATE'),
                    ('review_deadline_date', 'DATE'),
                    ('response_deadline_date', 'DATE'),
                    ('actual_submissions', 'INTEGER DEFAULT 0'),
                    ('scheduled_date', 'DATE'),
                    ('status', 'TEXT DEFAULT "planned"')
                ]
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
    def add_maslul(self, hativa_id: int, name: str, description: str = "", sla_days: int = 45, 
                   stage_a_days: int = 10, stage_b_days: int = 15, stage_c_days: int = 10, stage_d_days: int = 10) -> int:
        """Add a new route to a division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO maslulim (hativa_id, name, description, sla_days, stage_a_days, stage_b_days, stage_c_days, stage_d_days) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (hativa_id, name, description, sla_days, stage_a_days, stage_b_days, stage_c_days, stage_d_days))
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
                SELECT m.maslul_id, m.hativa_id, m.name, m.description, m.is_active, m.created_at,
                       m.sla_days, m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days,
                       h.name as hativa_name
                FROM maslulim m 
                JOIN hativot h ON m.hativa_id = h.hativa_id 
                WHERE m.hativa_id = ? 
                ORDER BY m.name
            ''', (hativa_id,))
        else:
            cursor.execute('''
                SELECT m.maslul_id, m.hativa_id, m.name, m.description, m.is_active, m.created_at,
                       m.sla_days, m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days,
                       h.name as hativa_name
                FROM maslulim m 
                JOIN hativot h ON m.hativa_id = h.hativa_id 
                ORDER BY h.name, m.name
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'maslul_id': row[0], 'hativa_id': row[1], 'name': row[2], 
                'description': row[3], 'is_active': row[4], 'created_at': row[5],
                'sla_days': row[6] if row[6] is not None else 45,
                'stage_a_days': row[7] if row[7] is not None else 10,
                'stage_b_days': row[8] if row[8] is not None else 15,
                'stage_c_days': row[9] if row[9] is not None else 10,
                'stage_d_days': row[10] if row[10] is not None else 10,
                'hativa_name': row[11]} for row in rows]
    
    def update_maslul(self, maslul_id: int, name: str, description: str = "", sla_days: int = 45,
                      stage_a_days: int = 10, stage_b_days: int = 15, stage_c_days: int = 10, stage_d_days: int = 10) -> bool:
        """Update an existing route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE maslulim 
            SET name = ?, description = ?, sla_days = ?, stage_a_days = ?, stage_b_days = ?, stage_c_days = ?, stage_d_days = ?
            WHERE maslul_id = ?
        ''', (name, description, sla_days, stage_a_days, stage_b_days, stage_c_days, stage_d_days, maslul_id))
        
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
    
    def update_vaada(self, vaadot_id: int, committee_type_id: int, hativa_id: int,
                     vaada_date: date, status: str = 'planned',
                     exception_date_id: Optional[int] = None, notes: str = "") -> bool:
        """Update committee meeting details including date, type, division, and notes"""
        conn = None
        try:
            if not self.is_work_day(vaada_date):
                raise ValueError(f"התאריך {vaada_date} אינו יום עסקים חוקי לועדות")

            conn = self.get_connection()
            cursor = conn.cursor()

            # Ensure committee type belongs to the same division as selected hativa
            cursor.execute('SELECT hativa_id FROM committee_types WHERE committee_type_id = ?', (committee_type_id,))
            ct_row = cursor.fetchone()
            if not ct_row:
                raise ValueError("סוג הועדה לא נמצא")
            if ct_row[0] != hativa_id:
                raise ValueError("סוג הועדה שנבחר אינו שייך לחטיבה שנבחרה")

            # Check constraints (per-day and per-week limits) excluding current meeting
            constraint_settings = self.get_constraint_settings()

            max_per_day = constraint_settings['max_meetings_per_day']
            cursor.execute('''
                SELECT COUNT(*) FROM vaadot 
                WHERE vaada_date = ? AND vaadot_id != ?
            ''', (vaada_date, vaadot_id))
            existing_count = cursor.fetchone()[0]
            if existing_count >= max_per_day:
                if max_per_day == 1:
                    raise ValueError(f"כבר קיימת ועדה בתאריך {vaada_date}. לא ניתן לקבוע יותר מועדה אחת ביום.")
                raise ValueError(f"כבר קיימות {existing_count} ועדות בתאריך {vaada_date}. המגבלה הנוכחית מאפשרת עד {max_per_day} ועדות ביום.")

            week_start, week_end = self._get_week_bounds(vaada_date)
            weekly_count = self._count_meetings_in_week(cursor, week_start, week_end, exclude_vaada_id=vaadot_id)
            weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
            if weekly_count >= weekly_limit:
                raise ValueError(f"השבוע של {vaada_date} כבר מכיל {weekly_count} ועדות (המגבלה היא {weekly_limit})")

            cursor.execute('''
                UPDATE vaadot
                SET committee_type_id = ?, hativa_id = ?, vaada_date = ?, status = ?,
                    exception_date_id = ?, notes = ?
                WHERE vaadot_id = ?
            ''', (committee_type_id, hativa_id, vaada_date, status, exception_date_id, notes, vaadot_id))

            success = cursor.rowcount > 0
            conn.commit()
            return success
        except ValueError:
            if conn:
                conn.rollback()
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error updating vaada: {e}")
            raise
        finally:
            if conn:
                conn.close()

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

    def delete_vaada(self, vaadot_id: int) -> bool:
        """Delete a committee meeting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete the vaada (events will be cascade deleted due to foreign key)
            cursor.execute('DELETE FROM vaadot WHERE vaadot_id = ?', (vaadot_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error deleting vaada: {e}")
            if 'conn' in locals():
                conn.close()
            return False

    def delete_vaadot_bulk(self, vaadot_ids: List[int]) -> Tuple[int, int]:
        """
        Bulk delete committee meetings (vaadot) by IDs.
        Returns (deleted_committees_count, affected_events_count).
        Events are removed via FK ON DELETE CASCADE; we compute count beforehand.
        """
        if not vaadot_ids:
            return 0, 0
        ids = [int(vid) for vid in vaadot_ids]
        placeholders = ','.join(['?'] * len(ids))
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Count related events before deletion
            cursor.execute(f'SELECT COUNT(*) FROM events WHERE vaadot_id IN ({placeholders})', ids)
            events_count = cursor.fetchone()[0] or 0
            # Delete committees
            cursor.execute(f'DELETE FROM vaadot WHERE vaadot_id IN ({placeholders})', ids)
            deleted_committees = cursor.rowcount or 0
            conn.commit()
            return deleted_committees, events_count
        except Exception as e:
            conn.rollback()
            print(f"Error bulk deleting vaadot: {e}")
            raise
        finally:
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
    def add_event(self, vaadot_id: int, maslul_id: int, name: str, event_type: str,
                  expected_requests: int = 0, actual_submissions: int = 0, call_publication_date: Optional[date] = None) -> int:
        """Add a new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if call_publication_date in ("", None):
            call_publication_date = None
        elif isinstance(call_publication_date, str):
            call_publication_date = datetime.strptime(call_publication_date, '%Y-%m-%d').date()
        elif isinstance(call_publication_date, datetime):
            call_publication_date = call_publication_date.date()
        
        # Validate that the route belongs to the same division as the committee and get stage data
        cursor.execute('''
            SELECT v.hativa_id as vaada_hativa_id, m.hativa_id as maslul_hativa_id,
                   h1.name as vaada_hativa_name, h2.name as maslul_hativa_name,
                   ct.name as committee_name, m.name as maslul_name,
                   v.vaada_date, m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days
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
        
        vaada_hativa_id, maslul_hativa_id, vaada_hativa_name, maslul_hativa_name, committee_name, maslul_name, vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days = result
        
        if call_publication_date in ("", None):
            call_publication_date = None
        elif isinstance(call_publication_date, str):
            call_publication_date = datetime.strptime(call_publication_date, '%Y-%m-%d').date()
        elif isinstance(call_publication_date, datetime):
            call_publication_date = call_publication_date.date()
        
        if vaada_hativa_id != maslul_hativa_id:
            conn.close()
            raise ValueError(f'המסלול "{maslul_name}" מחטיבת "{maslul_hativa_name}" אינו יכול להיות משויך לועדה "{committee_name}" מחטיבת "{vaada_hativa_name}"')
        
        # Check max requests per day constraint
        max_requests_per_day = int(self.get_system_setting('max_requests_per_day') or '100')
        current_total_requests = self.get_total_requests_on_date(vaada_date, exclude_event_id=None)
        new_total_requests = current_total_requests + expected_requests
        
        if new_total_requests > max_requests_per_day:
            conn.close()
            raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום: התאריך {vaada_date} כבר מכיל {current_total_requests} בקשות צפויות. הוספת {expected_requests} בקשות תגרום לסך של {new_total_requests} (המגבלה היא {max_requests_per_day})')
        
        # Calculate derived dates based on stage durations
        stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        
        cursor.execute('''
            INSERT INTO events (vaadot_id, maslul_id, name, event_type, expected_requests, actual_submissions,
                              call_publication_date, call_deadline_date, intake_deadline_date, review_deadline_date, response_deadline_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vaadot_id, maslul_id, name, event_type, expected_requests, actual_submissions,
              call_publication_date, stage_dates['call_deadline_date'], stage_dates['intake_deadline_date'],
              stage_dates['review_deadline_date'], stage_dates['response_deadline_date']))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_events(self, vaadot_id: Optional[int] = None) -> List[Dict]:
        """Get events, optionally filtered by committee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        base_query = '''
            SELECT 
                e.event_id,
                e.vaadot_id,
                e.maslul_id,
                e.name,
                e.event_type,
                e.expected_requests,
                e.actual_submissions,
                e.call_publication_date,
                e.scheduled_date,
                e.status,
                e.created_at,
                e.call_deadline_date,
                e.intake_deadline_date,
                e.review_deadline_date,
                e.response_deadline_date,
                ct.name as committee_name,
                v.vaada_date,
                vh.name as vaada_hativa_name,
                m.name as maslul_name,
                h.name as hativa_name,
                h.hativa_id,
                ct.committee_type_id
            FROM events e
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot vh ON v.hativa_id = vh.hativa_id
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            JOIN hativot h ON m.hativa_id = h.hativa_id
        '''

        if vaadot_id:
            cursor.execute(base_query + ' WHERE e.vaadot_id = ? ORDER BY e.created_at DESC', (vaadot_id,))
        else:
            cursor.execute(base_query + ' ORDER BY e.created_at DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'event_id': row[0], 'vaadot_id': row[1], 'maslul_id': row[2], 'name': row[3],
                'event_type': row[4], 'expected_requests': row[5], 'actual_submissions': row[6], 'call_publication_date': row[7],
                'scheduled_date': row[8], 'status': row[9], 'created_at': row[10], 
                'call_deadline_date': row[11], 'intake_deadline_date': row[12], 'review_deadline_date': row[13],
                'response_deadline_date': row[14], 'committee_name': row[15], 'vaada_date': row[16], 
                'vaada_hativa_name': row[17], 'maslul_name': row[18], 'hativa_name': row[19],
                'hativa_id': row[20] if len(row) > 20 else None,
                'committee_type_id': row[21] if len(row) > 21 else None} for row in rows]
    
    def update_event(self, event_id: int, vaadot_id: int, maslul_id: int, name: str, event_type: str,
                     expected_requests: int = 0, actual_submissions: int = 0, call_publication_date: Optional[date] = None) -> bool:
        """Update an existing event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Validate that the route belongs to the same division as the committee and get stage data
        cursor.execute('''
            SELECT v.hativa_id as vaada_hativa_id, m.hativa_id as maslul_hativa_id,
                   h1.name as vaada_hativa_name, h2.name as maslul_hativa_name,
                   ct.name as committee_name, m.name as maslul_name,
                   v.vaada_date, m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days
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
        
        vaada_hativa_id, maslul_hativa_id, vaada_hativa_name, maslul_hativa_name, committee_name, maslul_name, vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days = result
        
        if call_publication_date in ("", None):
            call_publication_date = None
        elif isinstance(call_publication_date, str):
            call_publication_date = datetime.strptime(call_publication_date, '%Y-%m-%d').date()
        elif isinstance(call_publication_date, datetime):
            call_publication_date = call_publication_date.date()
        
        if vaada_hativa_id != maslul_hativa_id:
            conn.close()
            raise ValueError(f'המסלול "{maslul_name}" מחטיבת "{maslul_hativa_name}" אינו יכול להיות משויך לועדה "{committee_name}" מחטיבת "{vaada_hativa_name}"')
        
        # Check max requests per day constraint (excluding current event)
        max_requests_per_day = int(self.get_system_setting('max_requests_per_day') or '100')
        current_total_requests = self.get_total_requests_on_date(vaada_date, exclude_event_id=event_id)
        new_total_requests = current_total_requests + expected_requests
        
        if new_total_requests > max_requests_per_day:
            conn.close()
            raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום: התאריך {vaada_date} כבר מכיל {current_total_requests} בקשות צפויות (ללא האירוע הנוכחי). עדכון ל-{expected_requests} בקשות יגרום לסך של {new_total_requests} (המגבלה היא {max_requests_per_day})')
        
        # Calculate derived dates based on stage durations
        stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        
        cursor.execute('''
            UPDATE events 
            SET vaadot_id = ?, maslul_id = ?, name = ?, event_type = ?, expected_requests = ?, actual_submissions = ?,
                call_publication_date = ?, call_deadline_date = ?, intake_deadline_date = ?,
                review_deadline_date = ?, response_deadline_date = ?
            WHERE event_id = ?
        ''', (vaadot_id, maslul_id, name, event_type, expected_requests, actual_submissions,
              call_publication_date, stage_dates['call_deadline_date'], stage_dates['intake_deadline_date'],
              stage_dates['review_deadline_date'], stage_dates['response_deadline_date'], event_id))
        
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

    def delete_events_bulk(self, event_ids: List[int]) -> int:
        """Bulk delete events by IDs in a single transaction. Returns number of deleted rows."""
        if not event_ids:
            return 0
        ids = [int(eid) for eid in event_ids]
        placeholders = ','.join(['?'] * len(ids))
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM events WHERE event_id IN ({placeholders})', ids)
            deleted = cursor.rowcount or 0
            conn.commit()
            return deleted
        except Exception as e:
            conn.rollback()
            print(f"Error bulk deleting events: {e}")
            raise
        finally:
            conn.close()
    
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
                'stage_a_days': row[7] if len(row) > 7 else 10,
                'stage_b_days': row[8] if len(row) > 8 else 15,
                'stage_c_days': row[9] if len(row) > 9 else 10,
                'stage_d_days': row[10] if len(row) > 10 else 10,
                'hativa_name': row[11] if len(row) > 11 else 'לא ידוע'} for row in rows]
    
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
    
    def get_total_requests_on_date(self, check_date, exclude_event_id: Optional[int] = None) -> int:
        """Get total expected requests across all events on a specific date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # המר לאובייקט date אם צריך
        if isinstance(check_date, str):
            check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        
        query = '''
            SELECT COALESCE(SUM(e.expected_requests), 0)
            FROM events e
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            WHERE v.vaada_date = ?
        '''
        params = [check_date]
        
        if exclude_event_id is not None:
            query += ' AND e.event_id != ?'
            params.append(exclude_event_id)
        
        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        conn.close()
        
        return total if total else 0
    
    def calculate_stage_dates(self, committee_date, stage_a_days: int, stage_b_days: int, stage_c_days: int, stage_d_days: int) -> Dict:
        """Calculate stage deadline dates based on committee meeting date and stage durations"""
        
        # המר את תאריך הועדה לאובייקט date אם הוא מחרוזת
        if isinstance(committee_date, str):
            from datetime import datetime
            committee_date = datetime.strptime(committee_date, '%Y-%m-%d').date()
        
        # חישוב התאריכים אחורה מתאריך הועדה
        
        # תאריך הגשת תשובת ועדה = תאריך ועדה + שלב ד
        response_deadline = self.add_business_days(committee_date, stage_d_days)
        
        # תאריך סיום שלב בדיקה = תאריך ועדה - שלב ג
        review_deadline = self.subtract_business_days(committee_date, stage_c_days)
        
        # תאריך סיום שלב קליטה = תאריך סיום בדיקה - שלב ב  
        intake_deadline = self.subtract_business_days(review_deadline, stage_b_days)
        
        # תאריך סיום קול קורא = תאריך סיום קליטה - שלב א
        call_deadline = self.subtract_business_days(intake_deadline, stage_a_days)
        
        return {
            'call_deadline_date': call_deadline,      # תאריך סיום קול קורא
            'intake_deadline_date': intake_deadline,  # תאריך סיום קליטה
            'review_deadline_date': review_deadline,  # תאריך סיום בדיקה
            'response_deadline_date': response_deadline,  # תאריך הגשת תשובת ועדה
            'committee_date': committee_date          # תאריך הועדה
        }
    
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
    
    def get_events(self) -> List[Dict]:
        """Get all events with extended information including committee types and divisions"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT e.event_id, e.vaadot_id, e.maslul_id, e.name, e.event_type,
                   e.expected_requests, e.actual_submissions, e.call_publication_date,
                   e.call_deadline_date, e.intake_deadline_date, e.review_deadline_date,
                   e.response_deadline_date, e.created_at,
                   m.name as maslul_name, m.hativa_id as maslul_hativa_id, m.sla_days,
                   v.vaada_date, v.status as vaada_status,
                   ct.name as committee_name, ct.committee_type_id,
                   h.name as hativa_name, h.color as hativa_color,
                   ht.name as committee_type_name
            FROM events e
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON m.hativa_id = h.hativa_id
            JOIN hativot ht ON ct.hativa_id = ht.hativa_id
            ORDER BY v.vaada_date DESC, e.created_at DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        return [{
            'event_id': row[0],
            'vaadot_id': row[1],
            'maslul_id': row[2],
            'name': row[3],
            'event_type': row[4],
            'expected_requests': row[5],
            'actual_submissions': row[6],
            'call_publication_date': row[7],
            'call_deadline_date': row[8],
            'intake_deadline_date': row[9],
            'review_deadline_date': row[10],
            'response_deadline_date': row[11],
            'created_at': row[12],
            'maslul_name': row[13],
            'maslul_hativa_id': row[14],
            'sla_days': row[15],
            'vaada_date': row[16],
            'vaada_status': row[17],
            'committee_name': row[18],
            'committee_type_id': row[19],
            'hativa_name': row[20],
            'hativa_color': row[21],
            'committee_type_name': row[22]
        } for row in rows]

    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
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
                SELECT m.maslul_id, m.hativa_id, m.name, m.description, m.created_at, 
                       m.is_active, m.sla_days, m.stage_a_days, m.stage_b_days, 
                       m.stage_c_days, m.stage_d_days, h.name as hativa_name
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
                    'sla_days': row[6] if row[6] is not None else 45,
                    'stage_a_days': row[7] if row[7] is not None else 10,
                    'stage_b_days': row[8] if row[8] is not None else 15,
                    'stage_c_days': row[9] if row[9] is not None else 10,
                    'stage_d_days': row[10] if row[10] is not None else 10,
                    'hativa_name': row[11]
                }
            return None
        except Exception as e:
            print(f"Error getting maslul by ID: {e}")
            import traceback
            traceback.print_exc()
            if 'conn' in locals():
                conn.close()
            return None
    
    # Audit Log Methods
    def add_audit_log(self, user_id: Optional[int], username: str, action: str, 
                     entity_type: str, entity_id: Optional[int] = None, 
                     entity_name: Optional[str] = None, details: Optional[str] = None,
                     ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                     status: str = 'success', error_message: Optional[str] = None) -> int:
        """Add an audit log entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now(ISRAEL_TZ).strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO audit_logs 
            (timestamp, user_id, username, action, entity_type, entity_id, entity_name, details, 
             ip_address, user_agent, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, user_id, username, action, entity_type, entity_id, entity_name, details,
              ip_address, user_agent, status, error_message))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    
    def get_audit_logs(self, limit: int = 100, offset: int = 0, 
                       user_id: Optional[int] = None, 
                       entity_type: Optional[str] = None,
                       action: Optional[str] = None,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> List[Dict]:
        """Get audit logs with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT log_id, timestamp, user_id, username, action, entity_type, 
                   entity_id, entity_name, details, ip_address, user_agent, status, error_message
            FROM audit_logs
            WHERE 1=1
        '''
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if entity_type:
            query += ' AND entity_type = ?'
            params.append(entity_type)
        
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        if start_date:
            query += ' AND DATE(timestamp) >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND DATE(timestamp) <= ?'
            params.append(end_date)
        
        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'log_id': row[0],
            'timestamp': row[1],
            'user_id': row[2],
            'username': row[3],
            'action': row[4],
            'entity_type': row[5],
            'entity_id': row[6],
            'entity_name': row[7],
            'details': row[8],
            'ip_address': row[9],
            'user_agent': row[10],
            'status': row[11],
            'error_message': row[12]
        } for row in rows]
    
    def get_audit_logs_count(self, user_id: Optional[int] = None,
                            entity_type: Optional[str] = None,
                            action: Optional[str] = None,
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> int:
        """Get total count of audit logs matching filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT COUNT(*) FROM audit_logs WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if entity_type:
            query += ' AND entity_type = ?'
            params.append(entity_type)
        
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        if start_date:
            query += ' AND DATE(timestamp) >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND DATE(timestamp) <= ?'
            params.append(end_date)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_audit_statistics(self) -> Dict:
        """Get audit log statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total logs
        cursor.execute('SELECT COUNT(*) FROM audit_logs')
        total_logs = cursor.fetchone()[0]
        
        # Logs by action
        cursor.execute('''
            SELECT action, COUNT(*) as count 
            FROM audit_logs 
            GROUP BY action 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        actions = [{'action': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Logs by entity type
        cursor.execute('''
            SELECT entity_type, COUNT(*) as count 
            FROM audit_logs 
            GROUP BY entity_type 
            ORDER BY count DESC
        ''')
        entities = [{'entity_type': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Recent activity (last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) 
            FROM audit_logs 
            WHERE timestamp >= datetime('now', '-1 day')
        ''')
        last_24h = cursor.fetchone()[0]
        
        # Failed operations
        cursor.execute('''
            SELECT COUNT(*) 
            FROM audit_logs 
            WHERE status = 'error'
        ''')
        failed_ops = cursor.fetchone()[0]
        
        # Most active users
        cursor.execute('''
            SELECT username, COUNT(*) as count 
            FROM audit_logs 
            WHERE username IS NOT NULL
            GROUP BY username 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        active_users = [{'username': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_logs': total_logs,
            'actions': actions,
            'entities': entities,
            'last_24h': last_24h,
            'failed_ops': failed_ops,
            'active_users': active_users
        }
    
    def update_event_vaada(self, event_id: int, new_vaada_id: int) -> bool:
        """Update event's committee meeting with max requests constraint validation"""
        conn = None
        try:
            # Get max requests setting first (before opening connection)
            max_requests_per_day = int(self.get_system_setting('max_requests_per_day') or '100')
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get event's current expected_requests and source vaada
            cursor.execute("""
                SELECT e.expected_requests, e.vaadot_id, v.vaada_date
                FROM events e
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                WHERE e.event_id = ?
            """, (event_id,))
            
            event_data = cursor.fetchone()
            if not event_data:
                conn.close()
                raise ValueError("האירוע לא נמצא במערכת")
            
            expected_requests = event_data[0]
            source_vaada_id = event_data[1]
            
            # Get target committee date
            cursor.execute("SELECT vaada_date FROM vaadot WHERE vaadot_id = ?", (new_vaada_id,))
            target_data = cursor.fetchone()
            if not target_data:
                conn.close()
                raise ValueError("הועדה היעד לא נמצאה במערכת")
            
            target_vaada_date = target_data[0]
            
            # Close connection before calling get_total_requests_on_date (which opens its own connection)
            conn.close()
            conn = None
            
            # Check max requests per day constraint for target date (excluding this event)
            current_total_requests = self.get_total_requests_on_date(target_vaada_date, exclude_event_id=event_id)
            new_total_requests = current_total_requests + expected_requests
            
            if new_total_requests > max_requests_per_day:
                raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום: התאריך {target_vaada_date} כבר מכיל {current_total_requests} בקשות צפויות. העברת אירוע זה עם {expected_requests} בקשות תגרום לסך של {new_total_requests} (המגבלה היא {max_requests_per_day})')
            
            # Open new connection for the update
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update event's committee meeting
            cursor.execute("""
                UPDATE events 
                SET vaadot_id = ?
                WHERE event_id = ?
            """, (new_vaada_id, event_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
            
        except ValueError:
            if conn:
                conn.rollback()
                conn.close()
            raise
        except Exception as e:
            print(f"Error updating event vaada: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    # Active Directory User Management Methods
    def create_ad_user(self, username: str, email: str, full_name: str, 
                      role: str = 'user', hativa_id: Optional[int] = None,
                      ad_dn: str = '') -> int:
        """
        Create a new AD user (no password required)
        
        Args:
            username: AD username (sAMAccountName)
            email: User email
            full_name: User's full display name
            role: User role
            hativa_id: Division ID
            ad_dn: Active Directory Distinguished Name
            
        Returns:
            User ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, hativa_id, auth_source, ad_dn)
            VALUES (?, ?, NULL, ?, ?, ?, 'ad', ?)
        ''', (username, email, full_name, role, hativa_id, ad_dn))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def update_ad_user_info(self, user_id: int, email: str, full_name: str) -> bool:
        """
        Update AD user information from AD sync
        
        Args:
            user_id: User ID
            email: Updated email
            full_name: Updated full name
            
        Returns:
            Success boolean
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET email = ?, full_name = ?
                WHERE user_id = ? AND auth_source = 'ad'
            ''', (email, full_name, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating AD user info: {e}")
            return False
    
    def get_user_by_username_any_source(self, username: str) -> Optional[Dict]:
        """
        Get user by username regardless of auth source
        
        Args:
            username: Username to search for
            
        Returns:
            User dictionary or None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, h.name as hativa_name
            FROM users u
            LEFT JOIN hativot h ON u.hativa_id = h.hativa_id
            WHERE u.username = ?
        ''', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0], 'username': row[1], 'email': row[2], 'password_hash': row[3],
                'full_name': row[4], 'role': row[5], 'hativa_id': row[6], 'is_active': row[7],
                'auth_source': row[8], 'ad_dn': row[9], 
                'created_at': row[10], 'last_login': row[11], 'hativa_name': row[12]
            }
        return None
    
    def get_ad_users(self) -> List[Dict]:
        """Get all Active Directory users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.email, u.full_name, u.role, 
                   u.hativa_id, h.name as hativa_name, u.is_active, 
                   u.created_at, u.last_login, u.ad_dn
            FROM users u
            LEFT JOIN hativot h ON u.hativa_id = h.hativa_id
            WHERE u.auth_source = 'ad'
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
                'last_login': row[9],
                'ad_dn': row[10],
                'auth_source': 'ad'
            })
        return users
    
    def get_local_users(self) -> List[Dict]:
        """Get all local (non-AD) users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.email, u.full_name, u.role, 
                   u.hativa_id, h.name as hativa_name, u.is_active, 
                   u.created_at, u.last_login
            FROM users u
            LEFT JOIN hativot h ON u.hativa_id = h.hativa_id
            WHERE u.auth_source = 'local' OR u.auth_source IS NULL
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
                'last_login': row[9],
                'auth_source': 'local'
            })
        return users
