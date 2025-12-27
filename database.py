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
        """Get database connection with timeout and optimizations"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds timeout
        return conn
    
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
                is_operational INTEGER DEFAULT 0,
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
                role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
                is_active INTEGER DEFAULT 1,
                auth_source TEXT DEFAULT 'local' CHECK (auth_source IN ('local', 'ad')),
                ad_dn TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create user_hativot table for many-to-many relationship
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_hativot (
                user_hativa_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                hativa_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE,
                UNIQUE(user_id, hativa_id)
            )
        ''')
        
        # Create hativa_day_constraints table for division day constraints
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hativa_day_constraints (
                constraint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hativa_id INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE,
                UNIQUE(hativa_id, day_of_week)
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_hativa_day_constraints_hativa 
            ON hativa_day_constraints (hativa_id)
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

        # Create calendar sync tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_sync_events (
                sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL CHECK (source_type IN ('vaadot', 'event_deadline')),
                source_id INTEGER NOT NULL,
                deadline_type TEXT,
                calendar_event_id TEXT,
                calendar_email TEXT NOT NULL,
                last_synced TIMESTAMP,
                sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN ('pending', 'synced', 'failed', 'deleted')),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_type, source_id, deadline_type, calendar_email)
            )
        ''')

        # Create indexes for faster calendar sync queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_calendar_sync_source ON calendar_sync_events (source_type, source_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_calendar_sync_status ON calendar_sync_events (sync_status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_calendar_sync_calendar_id ON calendar_sync_events (calendar_event_id)
        ''')

        # Add content_hash column if it doesn't exist (for change detection)
        try:
            cursor.execute('ALTER TABLE calendar_sync_events ADD COLUMN content_hash TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists

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
                ('max_requests_committee_date', '100', 'Maximum total expected requests on committee meeting date'),
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
                ('ad_sync_on_login', '1', 'Sync user info from AD on each login (1=yes, 0=no)'),
                ('calendar_sync_enabled', '1', 'Enable automatic calendar synchronization (1=yes, 0=no)'),
                ('calendar_sync_email', 'plan@innovationisrael.org.il', 'Email address of the shared calendar to sync to'),
                ('calendar_sync_interval_hours', '1', 'How often to sync calendar (in hours)')
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
            
            # Migrate user roles from old system (admin/manager/user) to new system (admin/editor/viewer)
            try:
                # Check if hativa_id column exists in users table (legacy column)
                cursor.execute("PRAGMA table_info(users)")
                users_columns = [column[1] for column in cursor.fetchall()]
                has_hativa_id = 'hativa_id' in users_columns
                
                if has_hativa_id:
                    # Legacy migration: migrate hativa_id from users table to user_hativot
                    cursor.execute("SELECT user_id, role, hativa_id FROM users WHERE role IN ('manager', 'user')")
                    old_role_users = cursor.fetchall()
                    
                    for user_id, old_role, hativa_id in old_role_users:
                        # Map old roles to new roles
                        if old_role == 'manager':
                            new_role = 'editor'
                        elif old_role == 'user':
                            new_role = 'viewer'
                        else:
                            continue  # admin stays admin
                        
                        cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
                        
                        # If user had a hativa_id, migrate it to user_hativot table
                        if hativa_id:
                            cursor.execute("""
                                INSERT OR IGNORE INTO user_hativot (user_id, hativa_id) 
                                VALUES (?, ?)
                            """, (user_id, hativa_id))
                    
                    # Also migrate admin users with hativa_id
                    cursor.execute("SELECT user_id, hativa_id FROM users WHERE role = 'admin' AND hativa_id IS NOT NULL")
                    admin_users = cursor.fetchall()
                    for user_id, hativa_id in admin_users:
                        cursor.execute("""
                            INSERT OR IGNORE INTO user_hativot (user_id, hativa_id) 
                            VALUES (?, ?)
                        """, (user_id, hativa_id))
                else:
                    # New schema: just migrate old role names if they exist
                    cursor.execute("UPDATE users SET role = 'editor' WHERE role = 'manager'")
                    cursor.execute("UPDATE users SET role = 'viewer' WHERE role = 'user'")
                    
            except Exception as e:
                print(f"Role migration note: {e}")
            
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
                    ('description', 'TEXT'),
                    ('is_operational', 'INTEGER DEFAULT 0')
                ],
                'vaadot': [
                    ('is_deleted', 'INTEGER DEFAULT 0'),
                    ('deleted_at', 'TIMESTAMP'),
                    ('deleted_by', 'INTEGER'),
                    ('start_time', 'TIME'),
                    ('end_time', 'TIME')
                ],
                'events': [
                    ('call_publication_date', 'DATE'),
                    ('call_deadline_date', 'DATE'),
                    ('intake_deadline_date', 'DATE'),
                    ('review_deadline_date', 'DATE'),
                    ('response_deadline_date', 'DATE'),
                    ('is_call_deadline_manual', 'INTEGER DEFAULT 0'),
                    ('actual_submissions', 'INTEGER DEFAULT 0'),
                    ('scheduled_date', 'DATE'),
                    ('is_deleted', 'INTEGER DEFAULT 0'),
                    ('deleted_at', 'TIMESTAMP'),
                    ('deleted_by', 'INTEGER')
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
        
        hativot = [{'hativa_id': row[0], 'name': row[1], 'description': row[2], 'color': row[3], 
                'is_active': row[4], 'created_at': row[5]} for row in rows]
        
        # Add allowed days for each division
        for hativa in hativot:
            hativa['allowed_days'] = self.get_hativa_allowed_days(hativa['hativa_id'])
        
        return hativot
    
    def get_hativa_allowed_days(self, hativa_id: int) -> List[int]:
        """Get allowed days of week for a division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT day_of_week 
            FROM hativa_day_constraints 
            WHERE hativa_id = ?
            ORDER BY day_of_week
        ''', (hativa_id,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    
    def set_hativa_allowed_days(self, hativa_id: int, allowed_days: List[int]) -> bool:
        """Set allowed days of week for a division"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Validate days (0-6)
        for day in allowed_days:
            if day < 0 or day > 6:
                conn.close()
                raise ValueError(f'יום לא תקין: {day}. יש לבחור יום בין 0 (שני) ל-6 (ראשון)')
        
        # Delete existing constraints
        cursor.execute('DELETE FROM hativa_day_constraints WHERE hativa_id = ?', (hativa_id,))
        
        # Insert new constraints
        for day in allowed_days:
            cursor.execute('''
                INSERT INTO hativa_day_constraints (hativa_id, day_of_week)
                VALUES (?, ?)
            ''', (hativa_id, day))
        
        conn.commit()
        conn.close()
        return True
    
    def is_day_allowed_for_hativa(self, hativa_id: int, date_obj: date) -> bool:
        """Check if a date is allowed for a division based on day constraints"""
        # Get allowed days for this division
        allowed_days = self.get_hativa_allowed_days(hativa_id)
        
        # If no constraints set, allow all days (backward compatibility)
        if not allowed_days:
            return True
        
        # Get day of week (Python weekday: Monday=0, Sunday=6)
        day_of_week = date_obj.weekday()
        
        # Check if this day is allowed
        return day_of_week in allowed_days
    
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
    
    def update_maslul(self, maslul_id: int, name: str, description: str, sla_days: int, 
                     stage_a_days: int, stage_b_days: int, stage_c_days: int, stage_d_days: int, is_active: bool = True) -> bool:
        """Update an existing route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE maslulim 
            SET name = ?, description = ?, sla_days = ?, stage_a_days = ?, stage_b_days = ?, stage_c_days = ?, stage_d_days = ?, is_active = ?
            WHERE maslul_id = ?
        ''', (name, description, sla_days, stage_a_days, stage_b_days, stage_c_days, stage_d_days, 1 if is_active else 0, maslul_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_maslul(self, maslul_id: int) -> bool:
        """Delete a route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if maslul is used in any events (including deleted ones)
        cursor.execute('''
            SELECT COUNT(*) FROM events WHERE maslul_id = ?
        ''', (maslul_id,))
        events_count = cursor.fetchone()[0]
        
        if events_count > 0:
            conn.close()
            raise ValueError(f'לא ניתן למחוק מסלול המשויך ל-{events_count} אירועים. יש למחוק תחילה את האירועים הקשורים.')
        
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
    
    def get_exception_dates(self, include_past: bool = False) -> List[Dict]:
        """Get exception dates, optionally including past dates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if include_past:
            cursor.execute('SELECT * FROM exception_dates ORDER BY exception_date DESC')
        else:
            today = date.today()
            cursor.execute('SELECT * FROM exception_dates WHERE exception_date >= ? ORDER BY exception_date', (today,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'date_id': row[0], 'exception_date': row[1], 'description': row[2], 
                'type': row[3], 'created_at': row[4] if len(row) > 4 else None} for row in rows]
    
    def get_exception_date_by_id(self, date_id: int) -> Optional[Dict]:
        """Get a specific exception date by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM exception_dates WHERE date_id = ?', (date_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'date_id': row[0], 'exception_date': row[1], 'description': row[2], 
                   'type': row[3], 'created_at': row[4] if len(row) > 4 else None}
        return None
    
    def update_exception_date(self, date_id: int, exception_date: date, description: str = "", date_type: str = "holiday") -> bool:
        """Update an exception date"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE exception_dates 
                SET exception_date = ?, description = ?, type = ?
                WHERE date_id = ?
            ''', (exception_date, description, date_type, date_id))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error updating exception date: {e}")
            return False
    
    def delete_exception_date(self, date_id: int) -> bool:
        """Delete an exception date"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if any committees are linked to this exception date (excluding deleted)
            cursor.execute('SELECT COUNT(*) FROM vaadot WHERE exception_date_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)', (date_id,))
            linked_count = cursor.fetchone()[0]
            
            if linked_count > 0:
                conn.close()
                return False  # Cannot delete if committees are linked
            
            cursor.execute('DELETE FROM exception_dates WHERE date_id = ?', (date_id,))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error deleting exception date: {e}")
            return False
    
    def is_exception_date(self, check_date: date) -> bool:
        """Check if a date is an exception date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM exception_dates WHERE exception_date = ?', (check_date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def recalculate_all_event_deadlines(self) -> int:
        """Recalculate deadline dates for all existing events based on current exception dates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all events with their committee dates and maslul stage information
        cursor.execute('''
            SELECT e.event_id, v.vaada_date, 
                   m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days
            FROM events e
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            WHERE (e.is_deleted = 0 OR e.is_deleted IS NULL)
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
        ''')
        
        events = cursor.fetchall()
        updated_count = 0
        
        for event in events:
            event_id, vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days = event
            
            # Convert vaada_date to date object if it's a string
            if isinstance(vaada_date, str):
                from datetime import datetime
                vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()
            
            # Recalculate stage dates
            stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
            
            # Update the event with new deadline dates
            cursor.execute('''
                UPDATE events 
                SET call_deadline_date = ?,
                    intake_deadline_date = ?,
                    review_deadline_date = ?,
                    response_deadline_date = ?
                WHERE event_id = ?
            ''', (
                stage_dates['call_deadline_date'],
                stage_dates['intake_deadline_date'],
                stage_dates['review_deadline_date'],
                stage_dates['response_deadline_date'],
                event_id
            ))
            updated_count += 1
        
        conn.commit()
        conn.close()
        return updated_count

    def recalculate_event_deadlines_for_maslul(self, maslul_id: int) -> int:
        """Recalculate deadline dates for all events of a specific maslul based on updated stage days"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get the maslul's current stage information
        cursor.execute('''
            SELECT stage_a_days, stage_b_days, stage_c_days, stage_d_days
            FROM maslulim
            WHERE maslul_id = ?
        ''', (maslul_id,))

        maslul_row = cursor.fetchone()
        if not maslul_row:
            conn.close()
            return 0

        stage_a_days, stage_b_days, stage_c_days, stage_d_days = maslul_row

        # Get all events for this maslul with their committee dates
        cursor.execute('''
            SELECT e.event_id, v.vaada_date
            FROM events e
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            WHERE e.maslul_id = ?
              AND (e.is_deleted = 0 OR e.is_deleted IS NULL)
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
        ''', (maslul_id,))

        events = cursor.fetchall()
        updated_count = 0

        for event in events:
            event_id, vaada_date = event

            # Convert vaada_date to date object if it's a string
            if isinstance(vaada_date, str):
                from datetime import datetime
                vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()

            # Recalculate stage dates using maslul's updated values
            stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)

            # Update the event with new deadline dates
            cursor.execute('''
                UPDATE events
                SET call_deadline_date = ?,
                    intake_deadline_date = ?,
                    review_deadline_date = ?,
                    response_deadline_date = ?
                WHERE event_id = ?
            ''', (
                stage_dates['call_deadline_date'],
                stage_dates['intake_deadline_date'],
                stage_dates['review_deadline_date'],
                stage_dates['response_deadline_date'],
                event_id
            ))
            updated_count += 1

        conn.commit()
        conn.close()
        return updated_count

    # Committee Types operations
    def add_committee_type(self, hativa_id: int, name: str, scheduled_day: int, frequency: str = 'weekly',
                          week_of_month: Optional[int] = None, description: str = "", is_operational: int = 0) -> int:
        """Add a new committee type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO committee_types (hativa_id, name, scheduled_day, frequency, week_of_month, description, is_operational)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (hativa_id, name, scheduled_day, frequency, week_of_month, description, is_operational))
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
                       ct.frequency, ct.week_of_month, ct.description, ct.is_operational, h.name as hativa_name 
                FROM committee_types ct
                JOIN hativot h ON ct.hativa_id = h.hativa_id
                WHERE ct.hativa_id = ?
                ORDER BY ct.scheduled_day
            ''', (hativa_id,))
        else:
            cursor.execute('''
                SELECT ct.committee_type_id, ct.hativa_id, ct.name, ct.scheduled_day, 
                       ct.frequency, ct.week_of_month, ct.description, ct.is_operational, h.name as hativa_name 
                FROM committee_types ct
                JOIN hativot h ON ct.hativa_id = h.hativa_id
                ORDER BY h.name, ct.scheduled_day
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        days = ['יום ראשון', 'יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת']
        
        return [{'committee_type_id': row[0], 'hativa_id': row[1], 'name': row[2], 'scheduled_day': row[3],
                'scheduled_day_name': days[row[3]], 'frequency': row[4], 
                'week_of_month': row[5], 'description': row[6], 'is_operational': row[7], 'hativa_name': row[8]} for row in rows]
    
    def update_committee_type(self, committee_type_id: int, hativa_id: int, name: str, scheduled_day: int, 
                             frequency: str = 'weekly', week_of_month: Optional[int] = None, 
                             description: str = "", is_operational: int = 0) -> bool:
        """Update an existing committee type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE committee_types 
            SET hativa_id = ?, name = ?, scheduled_day = ?, frequency = ?, week_of_month = ?, description = ?, is_operational = ?
            WHERE committee_type_id = ?
        ''', (hativa_id, name, scheduled_day, frequency, week_of_month, description, is_operational, committee_type_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_committee_type(self, committee_type_id: int) -> bool:
        """Delete a committee type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if there are any vaadot using this committee type (excluding deleted)
        cursor.execute('SELECT COUNT(*) FROM vaadot WHERE committee_type_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)', (committee_type_id,))
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
                  notes: str = "", start_time: str = None, end_time: str = None,
                  created_by: int = None, override_constraints: bool = False) -> tuple[int, str]:
        """
        Add a new committee meeting with constraint checking
        Returns: (vaadot_id, warning_message)
        If override_constraints=True (for admins), constraints become warnings
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        warning_message = ""
        
        # Check if date is available for scheduling (one meeting per day constraint)
        if not self.is_date_available_for_meeting(vaada_date):
            if override_constraints:
                warning_message = f'⚠️ אזהרה: כבר קיימת ועדה בתאריך {vaada_date}. מנהל מערכת יכול לעקוף אילוץ זה.'
            else:
                conn.close()
                raise ValueError(f'כבר קיימת ועדה בתאריך {vaada_date}. המערכת מאפשרת רק ועדה אחת ביום.')
        
        # Ensure meeting date is an allowed business day
        if not self.is_work_day(vaada_date):
            if override_constraints:
                warning_message += f'\n⚠️ אזהרה: התאריך {vaada_date} אינו יום עסקים חוקי לועדות.'
            else:
                conn.close()
                raise ValueError(f'התאריך {vaada_date} אינו יום עסקים חוקי לועדות')
        
        # Check if the date is allowed for this division based on day constraints
        if not self.is_day_allowed_for_hativa(hativa_id, vaada_date):
            day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
            day_name = day_names[vaada_date.weekday()]
            allowed_days = self.get_hativa_allowed_days(hativa_id)
            allowed_day_names = [day_names[d] for d in sorted(allowed_days)]
            
            if override_constraints:
                warning_message += f'\n⚠️ אזהרה: התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}.'
            else:
                conn.close()
                raise ValueError(f'התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}')
        
        try:
            constraint_settings = self.get_constraint_settings()

            # Check weekly limit
            week_start, week_end = self._get_week_bounds(vaada_date)
            weekly_count = self._count_meetings_in_week(cursor, week_start, week_end)
            weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
            is_third_week = self._is_third_week_of_month(vaada_date)
            week_type = "שבוע שלישי" if is_third_week else "שבוע רגיל"
            if weekly_count >= weekly_limit:
                new_count = weekly_count + 1
                if override_constraints:
                    warning_message += f'\n⚠️ אזהרה: השבוע של {vaada_date} ({week_type}) כבר מכיל {weekly_count} ועדות. הוספת ועדה נוספת תגרום לסך של {new_count} ועדות (המגבלה היא {weekly_limit}).'

            # Check if a committee meeting with the same type, division, and date already exists
            cursor.execute('''
                SELECT vaadot_id, ct.name as committee_name, h.name as hativa_name
                FROM vaadot v
                JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
                JOIN hativot h ON v.hativa_id = h.hativa_id
                WHERE v.committee_type_id = ? AND v.hativa_id = ? AND v.vaada_date = ?
                  AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
            ''', (committee_type_id, hativa_id, vaada_date))
            existing = cursor.fetchone()
            
            if existing:
                existing_id, existing_name, existing_hativa = existing
                if override_constraints:
                    warning_message += f'\n⚠️ אזהרה: כבר קיימת ועדה מסוג "{existing_name}" בחטיבת "{existing_hativa}" בתאריך {vaada_date}. מנהל מערכת יכול לעקוף אילוץ זה.'
                else:
                    conn.close()
                    raise ValueError(f'כבר קיימת ועדה מסוג "{existing_name}" בחטיבת "{existing_hativa}" בתאריך {vaada_date}. לא ניתן ליצור ועדה נוספת מאותו סוג באותה חטיבה באותו תאריך.')

            cursor.execute('''
                INSERT INTO vaadot (committee_type_id, hativa_id, vaada_date, notes, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (committee_type_id, hativa_id, vaada_date, notes, start_time, end_time))
            vaadot_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return (vaadot_id, warning_message)
        except ValueError:
            conn.rollback()
            conn.close()
            raise
        except Exception as e:
            conn.rollback()
            conn.close()
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
        cursor.execute('''
            SELECT COUNT(*) 
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            WHERE v.vaada_date = ? AND COALESCE(ct.is_operational, 0) = 0
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
        ''', (vaada_date,))
        count = cursor.fetchone()[0]
        conn.close()
        max_per_day = self.get_int_setting('max_meetings_per_day', 1)
        return count < max_per_day
    
    def get_vaadot(self, hativa_id: Optional[int] = None, start_date: Optional[date] = None, 
                   end_date: Optional[date] = None, include_deleted: bool = False) -> List[Dict]:
        """Get committee meetings with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT v.vaadot_id, v.committee_type_id, v.hativa_id, v.vaada_date,
                   v.exception_date_id, v.notes, v.created_at,
                   ct.name as committee_name, ct.is_operational, h.name as hativa_name,
                   ed.exception_date, ed.description as exception_description, ed.type as exception_type,
                   v.start_time, v.end_time
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            LEFT JOIN exception_dates ed ON v.exception_date_id = ed.date_id
            WHERE 1=1
        '''
        params = []
        
        if not include_deleted:
            query += ' AND (v.is_deleted = 0 OR v.is_deleted IS NULL)'
        
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
                'vaada_date': row[3], 'exception_date_id': row[4],
                'notes': row[5], 'created_at': row[6], 'committee_name': row[7], 'is_operational': row[8], 'hativa_name': row[9],
                'exception_date': row[10], 'exception_description': row[11],
                'exception_type': row[12], 'start_time': row[13], 'end_time': row[14]} for row in rows]

    def duplicate_vaada_with_events(self, source_vaadot_id: int, target_date: date, created_by: Optional[int] = None,
                                    override_constraints: bool = False) -> Dict:
        """
        Duplicate a committee meeting (vaada) and all its events to a new date.
        Returns dict with new_vaadot_id and counts.
        """
        # Fetch source committee details
        source = self.get_vaada_by_id(source_vaadot_id)
        if not source:
            raise ValueError("ועדה מקורית לא נמצאה")

        # Create the new committee meeting using existing constraint checks
        new_vaadot_id, warning_message = self.add_vaada(
            committee_type_id=int(source['committee_type_id']),
            hativa_id=int(source['hativa_id']),
            vaada_date=target_date,
            notes=source.get('notes') or "",
            created_by=created_by,
            override_constraints=override_constraints
        )

        # Copy events
        events = self.get_events(vaadot_id=source_vaadot_id)
        created_events = 0
        for ev in events:
            # If the source event used a manual call deadline, carry it over; otherwise let it be auto-calculated
            is_manual = bool(ev.get('is_call_deadline_manual'))
            manual_date = ev.get('call_deadline_date') if is_manual else None

            self.add_event(
                vaadot_id=new_vaadot_id,
                maslul_id=int(ev['maslul_id']),
                name=ev['name'],
                event_type=ev['event_type'],
                expected_requests=int(ev.get('expected_requests') or 0),
                actual_submissions=int(ev.get('actual_submissions') or 0),
                call_publication_date=ev.get('call_publication_date'),
                is_call_deadline_manual=is_manual,
                manual_call_deadline_date=manual_date
            )
            created_events += 1

        return {
            'new_vaadot_id': new_vaadot_id,
            'copied_events': created_events,
            'warning_message': warning_message
        }
    
    def update_vaada(self, vaadot_id: int, committee_type_id: int, hativa_id: int,
                     vaada_date: date,
                     exception_date_id: Optional[int] = None, notes: str = "",
                     start_time: str = None, end_time: str = None,
                     user_role: Optional[str] = None) -> bool:
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

            # Check if the date is allowed for this division based on day constraints (only for non-admin users)
            is_admin = user_role == 'admin'
            if not is_admin and not self.is_day_allowed_for_hativa(hativa_id, vaada_date):
                day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
                day_name = day_names[vaada_date.weekday()]
                allowed_days = self.get_hativa_allowed_days(hativa_id)
                allowed_day_names = [day_names[d] for d in sorted(allowed_days)]
                raise ValueError(f'התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}')

            # Check constraints (per-day and per-week limits) excluding current meeting
            constraint_settings = self.get_constraint_settings()

            max_per_day = constraint_settings['max_meetings_per_day']
            cursor.execute('''
                SELECT COUNT(*) FROM vaadot 
                WHERE vaada_date = ? AND vaadot_id != ?
                  AND (is_deleted = 0 OR is_deleted IS NULL)
            ''', (vaada_date, vaadot_id))
            existing_count = cursor.fetchone()[0]
            if existing_count >= max_per_day:
                if max_per_day == 1:
                    raise ValueError(f"כבר קיימת ועדה בתאריך {vaada_date}. לא ניתן לקבוע יותר מועדה אחת ביום.")
                raise ValueError(f"כבר קיימות {existing_count} ועדות בתאריך {vaada_date}. המגבלה הנוכחית מאפשרת עד {max_per_day} ועדות ביום.")

            week_start, week_end = self._get_week_bounds(vaada_date)
            weekly_count = self._count_meetings_in_week(cursor, week_start, week_end, exclude_vaada_id=vaadot_id)
            weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
            is_third_week = self._is_third_week_of_month(vaada_date)
            week_type = "שבוע שלישי" if is_third_week else "שבוע רגיל"
            if weekly_count >= weekly_limit:
                new_count = weekly_count + 1
                raise ValueError(f"השבוע של {vaada_date} ({week_type}) כבר מכיל {weekly_count} ועדות. העברת הועדה תגרום לסך של {new_count} ועדות (המגבלה היא {weekly_limit})")

            cursor.execute('''
                UPDATE vaadot
                SET committee_type_id = ?, hativa_id = ?, vaada_date = ?,
                    exception_date_id = ?, notes = ?, start_time = ?, end_time = ?
                WHERE vaadot_id = ?
            ''', (committee_type_id, hativa_id, vaada_date, exception_date_id, notes, start_time, end_time, vaadot_id))

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

    def update_vaada_date(self, vaadot_id: int, vaada_date: date, exception_date_id: Optional[int] = None, user_role: Optional[str] = None) -> bool:
        """Update the actual meeting date for a committee and optionally link to exception date"""
        conn = None
        try:
            if not self.is_work_day(vaada_date):
                raise ValueError(f"התאריך {vaada_date} אינו יום עסקים חוקי לועדות")

            conn = self.get_connection()
            cursor = conn.cursor()

            # Get hativa_id for this committee to check day constraints
            cursor.execute('SELECT hativa_id FROM vaadot WHERE vaadot_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)', (vaadot_id,))
            hativa_row = cursor.fetchone()
            if hativa_row:
                hativa_id = hativa_row[0]
                # Check if the date is allowed for this division based on day constraints (only for non-admin users)
                is_admin = user_role == 'admin'
                if not is_admin and not self.is_day_allowed_for_hativa(hativa_id, vaada_date):
                    day_names = ['יום שני', 'יום שלישי', 'יום רביעי', 'יום חמישי', 'יום שישי', 'שבת', 'יום ראשון']
                    day_name = day_names[vaada_date.weekday()]
                    allowed_days = self.get_hativa_allowed_days(hativa_id)
                    allowed_day_names = [day_names[d] for d in sorted(allowed_days)]
                    raise ValueError(f'התאריך {vaada_date} ({day_name}) אינו יום מותר לקביעת ועדות עבור חטיבה זו. הימים המותרים: {", ".join(allowed_day_names)}')

            # Enforce daily limit excluding the current meeting
            constraint_settings = self.get_constraint_settings()
            max_per_day = constraint_settings['max_meetings_per_day']
            cursor.execute('''
                SELECT COUNT(*) FROM vaadot
                WHERE vaada_date = ? AND vaadot_id != ?
                  AND (is_deleted = 0 OR is_deleted IS NULL)
            ''', (vaada_date, vaadot_id))
            existing_count = cursor.fetchone()[0]
            if existing_count >= max_per_day:
                raise ValueError(f"התאריך {vaada_date} כבר מכיל {existing_count} ועדות (המגבלה היא {max_per_day})")

            week_start, week_end = self._get_week_bounds(vaada_date)
            weekly_count = self._count_meetings_in_week(cursor, week_start, week_end, exclude_vaada_id=vaadot_id)
            weekly_limit = self._get_weekly_limit(vaada_date, constraint_settings)
            is_third_week = self._is_third_week_of_month(vaada_date)
            week_type = "שבוע שלישי" if is_third_week else "שבוע רגיל"
            if weekly_count >= weekly_limit:
                new_count = weekly_count + 1
                raise ValueError(f"השבוע של {vaada_date} ({week_type}) כבר מכיל {weekly_count} ועדות. העברת הועדה תגרום לסך של {new_count} ועדות (המגבלה היא {weekly_limit})")

            # Check constraints on derived dates for all events in this committee
            cursor.execute('''
                SELECT e.event_id, e.expected_requests, m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days
                FROM events e
                JOIN maslulim m ON e.maslul_id = m.maslul_id
                WHERE e.vaadot_id = ? AND e.is_deleted = 0
            ''', (vaadot_id,))
            events = cursor.fetchall()
            
            # Close connection before calling constraint check functions
            conn.close()
            conn = None
            
            # Check derived date constraints for each event
            for event in events:
                event_id, expected_requests, stage_a_days, stage_b_days, stage_c_days, stage_d_days = event
                
                # Calculate new derived dates with the new committee date
                stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
                
                # Check constraints (excluding the current event)
                derived_constraint_error = self.check_derived_dates_constraints(stage_dates, expected_requests, exclude_event_id=event_id, user_role=user_role)
                if derived_constraint_error:
                    raise ValueError(f"העברת הועדה תגרום לחריגה באירוע {event_id}: {derived_constraint_error}")
            
            # Reopen connection for the update
            conn = self.get_connection()
            cursor = conn.cursor()

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

    def delete_vaada(self, vaadot_id: int, user_id: Optional[int] = None) -> bool:
        """Soft delete a committee meeting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Soft delete the vaada
            cursor.execute('''
                UPDATE vaadot 
                SET is_deleted = 1, deleted_at = ?, deleted_by = ? 
                WHERE vaadot_id = ?
            ''', (datetime.now(ISRAEL_TZ), user_id, vaadot_id))
            success = cursor.rowcount > 0
            
            # Also soft delete related events
            if success:
                cursor.execute('''
                    UPDATE events 
                    SET is_deleted = 1, deleted_at = ?, deleted_by = ? 
                    WHERE vaadot_id = ? AND is_deleted = 0
                ''', (datetime.now(ISRAEL_TZ), user_id, vaadot_id))
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error deleting vaada: {e}")
            if 'conn' in locals():
                conn.close()
            return False

    def delete_vaadot_bulk(self, vaadot_ids: List[int], user_id: Optional[int] = None) -> Tuple[int, int]:
        """
        Bulk soft delete committee meetings (vaadot) by IDs.
        Returns (deleted_committees_count, affected_events_count).
        Events are also soft deleted.
        """
        if not vaadot_ids:
            return 0, 0
        ids = [int(vid) for vid in vaadot_ids]
        placeholders = ','.join(['?'] * len(ids))
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Count related events before deletion
            cursor.execute(f'SELECT COUNT(*) FROM events WHERE vaadot_id IN ({placeholders}) AND is_deleted = 0', ids)
            events_count = cursor.fetchone()[0] or 0
            
            # Soft delete related events first
            cursor.execute(f'''
                UPDATE events 
                SET is_deleted = 1, deleted_at = ?, deleted_by = ? 
                WHERE vaadot_id IN ({placeholders}) AND is_deleted = 0
            ''', [datetime.now(ISRAEL_TZ), user_id] + ids)
            
            # Soft delete committees
            cursor.execute(f'''
                UPDATE vaadot 
                SET is_deleted = 1, deleted_at = ?, deleted_by = ? 
                WHERE vaadot_id IN ({placeholders}) AND is_deleted = 0
            ''', [datetime.now(ISRAEL_TZ), user_id] + ids)
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
              AND (is_deleted = 0 OR is_deleted IS NULL)
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
            WHERE v.vaada_date = ? AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
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
            WHERE v.vaada_date = ? AND v.hativa_id = ? AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
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
            WHERE v.exception_date_id = ? AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
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
                  expected_requests: int = 0, actual_submissions: int = 0, call_publication_date: Optional[date] = None,
                  is_call_deadline_manual: bool = False, manual_call_deadline_date: Optional[date] = None,
                  user_role: Optional[str] = None) -> int:
        """Add a new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if call_publication_date in ("", None):
            call_publication_date = None
        elif isinstance(call_publication_date, str):
            call_publication_date = datetime.strptime(call_publication_date, '%Y-%m-%d').date()
        elif isinstance(call_publication_date, datetime):
            call_publication_date = call_publication_date.date()
        
        # Process manual call deadline date if provided
        if manual_call_deadline_date in ("", None):
            manual_call_deadline_date = None
        elif isinstance(manual_call_deadline_date, str):
            manual_call_deadline_date = datetime.strptime(manual_call_deadline_date, '%Y-%m-%d').date()
        elif isinstance(manual_call_deadline_date, datetime):
            manual_call_deadline_date = manual_call_deadline_date.date()
        
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
        
        # Check max requests per day constraint on committee date (skip for admins)
        if user_role != 'admin':
            max_requests_committee = int(self.get_system_setting('max_requests_committee_date') or '100')
            current_total_requests = self.get_total_requests_on_date(vaada_date, exclude_event_id=None)
            new_total_requests = current_total_requests + expected_requests
            
            if new_total_requests > max_requests_committee:
                conn.close()
                raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום ועדה: התאריך {vaada_date} כבר מכיל {current_total_requests} בקשות צפויות. הוספת {expected_requests} בקשות תגרום לסך של {new_total_requests} (המגבלה היא {max_requests_committee})')
        
        # Calculate derived dates based on stage durations
        stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        
        # Use manual call deadline date if provided, otherwise use calculated
        if is_call_deadline_manual and manual_call_deadline_date:
            final_call_deadline = manual_call_deadline_date
        else:
            final_call_deadline = stage_dates['call_deadline_date']
            is_call_deadline_manual = False  # Ensure flag is False if no manual date
        
        # Check max requests per day constraint on derived dates
        derived_constraint_error = self.check_derived_dates_constraints(stage_dates, expected_requests, exclude_event_id=None, user_role=user_role)
        if derived_constraint_error:
            conn.close()
            raise ValueError(derived_constraint_error)
        
        cursor.execute('''
            INSERT INTO events (vaadot_id, maslul_id, name, event_type, expected_requests, actual_submissions,
                              call_publication_date, call_deadline_date, intake_deadline_date, review_deadline_date, 
                              response_deadline_date, is_call_deadline_manual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vaadot_id, maslul_id, name, event_type, expected_requests, actual_submissions,
              call_publication_date, final_call_deadline, stage_dates['intake_deadline_date'],
              stage_dates['review_deadline_date'], stage_dates['response_deadline_date'], 
              1 if is_call_deadline_manual else 0))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_events(self, vaadot_id: Optional[int] = None, include_deleted: bool = False) -> List[Dict]:
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
                e.created_at,
                e.call_deadline_date,
                e.intake_deadline_date,
                e.review_deadline_date,
                e.response_deadline_date,
                e.is_call_deadline_manual,
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
            WHERE (e.is_deleted = 0 OR e.is_deleted IS NULL)
        '''
        
        if not include_deleted:
            pass  # Already filtered in base query
        else:
            # If we want to include deleted, remove the WHERE clause
            base_query = base_query.replace('WHERE (e.is_deleted = 0 OR e.is_deleted IS NULL)', 'WHERE 1=1')

        if vaadot_id:
            cursor.execute(base_query + ' AND e.vaadot_id = ? ORDER BY e.created_at DESC', (vaadot_id,))
        else:
            cursor.execute(base_query + ' ORDER BY e.created_at DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'event_id': row[0], 'vaadot_id': row[1], 'maslul_id': row[2], 'name': row[3],
                'event_type': row[4], 'expected_requests': row[5], 'actual_submissions': row[6], 'call_publication_date': row[7],
                'scheduled_date': row[8], 'created_at': row[9], 
                'call_deadline_date': row[10], 'intake_deadline_date': row[11], 'review_deadline_date': row[12],
                'response_deadline_date': row[13], 'is_call_deadline_manual': row[14], 'committee_name': row[15], 
                'vaada_date': row[16], 'vaada_hativa_name': row[17], 'maslul_name': row[18], 'hativa_name': row[19],
                'hativa_id': row[20] if len(row) > 20 else None,
                'committee_type_id': row[21] if len(row) > 21 else None} for row in rows]
    
    def update_event(self, event_id: int, vaadot_id: int, maslul_id: int, name: str, event_type: str,
                     expected_requests: int = 0, actual_submissions: int = 0, call_publication_date: Optional[date] = None,
                     is_call_deadline_manual: bool = False, manual_call_deadline_date: Optional[date] = None,
                     user_role: Optional[str] = None) -> bool:
        """Update an existing event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Process manual call deadline date if provided
        if manual_call_deadline_date in ("", None):
            manual_call_deadline_date = None
        elif isinstance(manual_call_deadline_date, str):
            manual_call_deadline_date = datetime.strptime(manual_call_deadline_date, '%Y-%m-%d').date()
        elif isinstance(manual_call_deadline_date, datetime):
            manual_call_deadline_date = manual_call_deadline_date.date()
        
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
        
        # Check max requests per day constraint on committee date (excluding current event, skip for admins)
        if user_role != 'admin':
            max_requests_committee = int(self.get_system_setting('max_requests_committee_date') or '100')
            current_total_requests = self.get_total_requests_on_date(vaada_date, exclude_event_id=event_id)
            new_total_requests = current_total_requests + expected_requests
            
            if new_total_requests > max_requests_committee:
                conn.close()
                raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום ועדה: התאריך {vaada_date} כבר מכיל {current_total_requests} בקשות צפויות (ללא האירוע הנוכחי). עדכון ל-{expected_requests} בקשות יגרום לסך של {new_total_requests} (המגבלה היא {max_requests_committee})')
        
        # Calculate derived dates based on stage durations
        stage_dates = self.calculate_stage_dates(vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
        
        # Use manual call deadline date if provided, otherwise use calculated
        if is_call_deadline_manual and manual_call_deadline_date:
            final_call_deadline = manual_call_deadline_date
        else:
            final_call_deadline = stage_dates['call_deadline_date']
            is_call_deadline_manual = False  # Ensure flag is False if no manual date
        
        # Check max requests per day constraint on derived dates (excluding current event)
        derived_constraint_error = self.check_derived_dates_constraints(stage_dates, expected_requests, exclude_event_id=event_id, user_role=user_role)
        if derived_constraint_error:
            conn.close()
            raise ValueError(derived_constraint_error)
        
        cursor.execute('''
            UPDATE events 
            SET vaadot_id = ?, maslul_id = ?, name = ?, event_type = ?, expected_requests = ?, actual_submissions = ?,
                call_publication_date = ?, call_deadline_date = ?, intake_deadline_date = ?,
                review_deadline_date = ?, response_deadline_date = ?, is_call_deadline_manual = ?
            WHERE event_id = ?
        ''', (vaadot_id, maslul_id, name, event_type, expected_requests, actual_submissions,
              call_publication_date, final_call_deadline, stage_dates['intake_deadline_date'],
              stage_dates['review_deadline_date'], stage_dates['response_deadline_date'], 
              1 if is_call_deadline_manual else 0, event_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_event(self, event_id: int, user_id: Optional[int] = None) -> bool:
        """Soft delete an event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE events 
            SET is_deleted = 1, deleted_at = ?, deleted_by = ? 
            WHERE event_id = ? AND is_deleted = 0
        ''', (datetime.now(ISRAEL_TZ), user_id, event_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_events_bulk(self, event_ids: List[int], user_id: Optional[int] = None) -> int:
        """Bulk soft delete events by IDs in a single transaction. Returns number of deleted rows."""
        if not event_ids:
            return 0
        ids = [int(eid) for eid in event_ids]
        placeholders = ','.join(['?'] * len(ids))
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE events 
                SET is_deleted = 1, deleted_at = ?, deleted_by = ? 
                WHERE event_id IN ({placeholders}) AND is_deleted = 0
            ''', [datetime.now(ISRAEL_TZ), user_id] + ids)
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
                   role: str = 'viewer', hativa_ids: List[int] = None) -> int:
        """Create a new user with access to specified hativot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, role))
        user_id = cursor.lastrowid
        
        # Add hativot access
        if hativa_ids:
            for hativa_id in hativa_ids:
                cursor.execute('''
                    INSERT INTO user_hativot (user_id, hativa_id) 
                    VALUES (?, ?)
                ''', (user_id, hativa_id))
        
        conn.commit()
        conn.close()
        return user_id
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username with all their hativot (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, email, password_hash, full_name, role, 
                   is_active, auth_source, ad_dn, created_at, last_login
            FROM users
            WHERE LOWER(username) = LOWER(?) AND is_active = 1
        ''', (username,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        user_id = row[0]
        
        # Get all hativot for this user
        cursor.execute('''
            SELECT h.hativa_id, h.name
            FROM user_hativot uh
            JOIN hativot h ON uh.hativa_id = h.hativa_id
            WHERE uh.user_id = ?
            ORDER BY h.name
        ''', (user_id,))
        hativot_rows = cursor.fetchall()
        conn.close()
        
        hativot = [{'hativa_id': h[0], 'name': h[1]} for h in hativot_rows]
        hativa_ids = [h['hativa_id'] for h in hativot]
        
        return {
            'user_id': user_id,
            'username': row[1],
            'email': row[2],
            'password_hash': row[3],
            'full_name': row[4],
            'role': row[5],
            'is_active': row[6],
            'auth_source': row[7],
            'ad_dn': row[8],
            'created_at': row[9],
            'last_login': row[10],
            'hativot': hativot,
            'hativa_ids': hativa_ids
        }
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, email, password_hash, full_name, role, 
                   is_active, auth_source, ad_dn, created_at, last_login
            FROM users
            WHERE email = ? AND is_active = 1
        ''', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'user_id': row[0],
            'username': row[1],
            'email': row[2],
            'password_hash': row[3],
            'full_name': row[4],
            'role': row[5],
            'is_active': row[6],
            'auth_source': row[7],
            'ad_dn': row[8],
            'created_at': row[9],
            'last_login': row[10]
        }
    
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
                   u.is_active, u.created_at, u.last_login, u.auth_source
            FROM users u
            ORDER BY u.created_at DESC
        ''')
        rows = cursor.fetchall()
        
        users = []
        for row in rows:
            user_id = row[0]
            # Get all hativot for this user
            cursor.execute('''
                SELECT h.hativa_id, h.name
                FROM user_hativot uh
                JOIN hativot h ON uh.hativa_id = h.hativa_id
                WHERE uh.user_id = ?
                ORDER BY h.name
            ''', (user_id,))
            hativot_rows = cursor.fetchall()
            
            hativot = [{'hativa_id': h[0], 'name': h[1]} for h in hativot_rows]
            hativa_names = ', '.join([h['name'] for h in hativot]) if hativot else ''
            
            users.append({
                'user_id': user_id,
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'role': row[4],
                'is_active': row[5],
                'created_at': row[6],
                'last_login': row[7],
                'auth_source': row[8],
                'hativot': hativot,
                'hativa_names': hativa_names
            })
        
        conn.close()
        return users
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID with all their hativot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, email, password_hash, full_name, role, 
                   is_active, auth_source, ad_dn, created_at, last_login
            FROM users
            WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Get all hativot for this user
        cursor.execute('''
            SELECT h.hativa_id, h.name
            FROM user_hativot uh
            JOIN hativot h ON uh.hativa_id = h.hativa_id
            WHERE uh.user_id = ?
            ORDER BY h.name
        ''', (user_id,))
        hativot_rows = cursor.fetchall()
        conn.close()
        
        hativot = [{'hativa_id': h[0], 'name': h[1]} for h in hativot_rows]
        hativa_names = ', '.join([h['name'] for h in hativot]) if hativot else ''
        
        return {
            'user_id': row[0],
            'username': row[1],
            'email': row[2],
            'password_hash': row[3],
            'full_name': row[4],
            'role': row[5],
            'is_active': row[6],
            'auth_source': row[7],
            'ad_dn': row[8],
            'created_at': row[9],
            'last_login': row[10],
            'hativot': hativot,
            'hativa_names': hativa_names
        }
    
    def update_user(self, user_id: int, username: str, email: str, full_name: str, 
                   role: str, hativa_ids: List[int] = None, auth_source: Optional[str] = None) -> bool:
        """Update user information and their hativot access"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update basic user info
            update_fields = ['username = ?', 'email = ?', 'full_name = ?', 'role = ?']
            params: List = [username, email, full_name, role]

            if auth_source in ('local', 'ad'):
                update_fields.append('auth_source = ?')
                params.append(auth_source)

            params.append(user_id)

            cursor.execute(f'''
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE user_id = ?
            ''', params)
            
            # Update user_hativot relationships
            if hativa_ids is not None:
                # Remove existing hativot
                cursor.execute('DELETE FROM user_hativot WHERE user_id = ?', (user_id,))
                
                # Add new hativot
                for hativa_id in hativa_ids:
                    cursor.execute('''
                        INSERT INTO user_hativot (user_id, hativa_id) 
                        VALUES (?, ?)
                    ''', (user_id, hativa_id))
            
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
        """Check if username already exists (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if exclude_user_id:
            cursor.execute('''
                SELECT COUNT(*) FROM users WHERE LOWER(username) = LOWER(?) AND user_id != ?
            ''', (username, exclude_user_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM users WHERE LOWER(username) = LOWER(?)
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
    
    def get_user_hativot(self, user_id: int) -> List[Dict]:
        """Get all hativot that a user has access to"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT h.hativa_id, h.name, h.description, h.color
            FROM user_hativot uh
            JOIN hativot h ON uh.hativa_id = h.hativa_id
            WHERE uh.user_id = ?
            ORDER BY h.name
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{'hativa_id': row[0], 'name': row[1], 'description': row[2], 'color': row[3]} 
                for row in rows]
    
    def user_has_access_to_hativa(self, user_id: int, hativa_id: int) -> bool:
        """Check if user has access to a specific hativa"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Admin has access to everything
        cursor.execute('SELECT role FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user and user[0] == 'admin':
            conn.close()
            return True
        
        # Check if user has specific access to this hativa
        cursor.execute('''
            SELECT COUNT(*) FROM user_hativot 
            WHERE user_id = ? AND hativa_id = ?
        ''', (user_id, hativa_id))
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def add_user_hativa(self, user_id: int, hativa_id: int) -> bool:
        """Add hativa access to user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO user_hativot (user_id, hativa_id) 
                VALUES (?, ?)
            ''', (user_id, hativa_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding user hativa: {e}")
            return False
    
    def remove_user_hativa(self, user_id: int, hativa_id: int) -> bool:
        """Remove hativa access from user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM user_hativot 
                WHERE user_id = ? AND hativa_id = ?
            ''', (user_id, hativa_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error removing user hativa: {e}")
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
        
        # Editors can edit when editing period is active
        if user_role == 'editor':
            editing_active = self.get_system_setting('editing_period_active')
            return editing_active == '1'
        
        # Viewers cannot edit
        if user_role == 'viewer':
            return False
        
        # Check if general editing period is active (backward compatibility)
        editing_active = self.get_system_setting('editing_period_active')
        return editing_active == '1'
    
    def can_user_edit(self, user_id: int, user_role: str, target_hativa_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Check if user can edit based on role, editing period, and hativa access
        Returns (can_edit, reason)
        """
        # Admin can always edit everything (but will get warnings about constraints)
        if user_role == 'admin':
            return True, "מנהל מערכת - אין הגבלות (מקבל התראות על אילוצים)"
        
        # Viewers can never edit
        if user_role == 'viewer':
            return False, "צופה - הרשאות קריאה בלבד"
        
        # Editors can edit if editing period is active
        if user_role == 'editor':
            editing_active = self.get_system_setting('editing_period_active')
            if editing_active != '1':
                return False, "תקופת העריכה הסתיימה. רק מנהלי מערכת יכולים לערוך"
            
            # Check if editor has access to target hativa
            if target_hativa_id:
                if not self.user_has_access_to_hativa(user_id, target_hativa_id):
                    return False, "אין לך הרשאה לערוך בחטיבה זו"
            
            return True, "עורך - תקופת עריכה פעילה"
        
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
        cursor.execute('''
            SELECT COUNT(*) 
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            WHERE v.vaada_date = ? AND COALESCE(ct.is_operational, 0) = 0
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
        ''', (vaada_date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_meetings_count_in_range(self, start_date: date, end_date: date) -> int:
        """Get number of meetings in an inclusive date range"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) 
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            WHERE v.vaada_date BETWEEN ? AND ?
              AND COALESCE(ct.is_operational, 0) = 0
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
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
        """Get total expected requests across all events on a specific date (committee date)"""
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
              AND (e.is_deleted = 0 OR e.is_deleted IS NULL)
              AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
        '''
        params = [check_date]
        
        if exclude_event_id is not None:
            query += ' AND e.event_id != ?'
            params.append(exclude_event_id)
        
        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        conn.close()
        
        return total if total else 0
    
    def get_total_requests_on_derived_date(self, check_date, date_type: str, exclude_event_id: Optional[int] = None) -> int:
        """
        Get total expected requests for a specific derived date
        
        Args:
            check_date: The date to check
            date_type: One of 'call_deadline', 'intake_deadline', 'review_deadline', 'response_deadline'
            exclude_event_id: Optional event ID to exclude from the count
            
        Returns:
            Total expected requests on that date
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # המר לאובייקט date אם צריך
        if isinstance(check_date, str):
            check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        
        # Map date_type to column name
        column_map = {
            'call_deadline': 'call_deadline_date',
            'intake_deadline': 'intake_deadline_date',
            'review_deadline': 'review_deadline_date',
            'response_deadline': 'response_deadline_date'
        }
        
        if date_type not in column_map:
            conn.close()
            raise ValueError(f'Invalid date_type: {date_type}')
        
        column_name = column_map[date_type]
        
        query = f'''
            SELECT COALESCE(SUM(e.expected_requests), 0)
            FROM events e
            WHERE e.{column_name} = ? AND e.is_deleted = 0
        '''
        params = [check_date]
        
        if exclude_event_id is not None:
            query += ' AND e.event_id != ?'
            params.append(exclude_event_id)
        
        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        conn.close()
        
        return total if total else 0
    
    def check_derived_dates_constraints(self, stage_dates: Dict, expected_requests: int, 
                                       exclude_event_id: Optional[int] = None, user_role: Optional[str] = None) -> Optional[str]:
        """
        Check if adding/updating an event would violate max_requests constraints on derived dates.
        Currently no constraints are enforced on derived dates.
        
        Args:
            stage_dates: Dictionary with call_deadline_date, intake_deadline_date, review_deadline_date, response_deadline_date
            expected_requests: Number of expected requests for the event
            exclude_event_id: Optional event ID to exclude (for updates)
            user_role: Optional user role (kept for backward compatibility)
            
        Returns:
            None (no constraints enforced)
        """
        # No constraints on derived dates
        return None
    
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
    
    def get_all_events(self, include_deleted: bool = False) -> List[Dict]:
        """Get all events with extended information including committee types and divisions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        where_clause = '' if include_deleted else 'WHERE (e.is_deleted = 0 OR e.is_deleted IS NULL) AND (v.is_deleted = 0 OR v.is_deleted IS NULL)'

        cursor.execute(f'''
            SELECT e.event_id, e.vaadot_id, e.maslul_id, e.name, e.event_type,
                   e.expected_requests, e.actual_submissions, e.call_publication_date,
                   e.call_deadline_date, e.intake_deadline_date, e.review_deadline_date,
                   e.response_deadline_date, e.is_call_deadline_manual, e.created_at,
                   m.name as maslul_name, m.hativa_id as maslul_hativa_id, m.sla_days,
                   v.vaada_date,
                   ct.name as committee_name, ct.committee_type_id,
                   h.name as hativa_name, h.color as hativa_color,
                   ht.name as committee_type_name
            FROM events e
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON m.hativa_id = h.hativa_id
            JOIN hativot ht ON ct.hativa_id = ht.hativa_id
            {where_clause}
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
            'is_call_deadline_manual': row[12],
            'created_at': row[13],
            'maslul_name': row[14],
            'maslul_hativa_id': row[15],
            'sla_days': row[16],
            'vaada_date': row[17],
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
                  AND (e.is_deleted = 0 OR e.is_deleted IS NULL)
                  AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
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
                SELECT
                    v.vaadot_id, v.committee_type_id, v.hativa_id, v.vaada_date,
                    v.exception_date_id, v.notes, v.created_at,
                    ct.name as committee_name, h.name as hativa_name,
                    v.start_time, v.end_time
                FROM vaadot v
                JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
                JOIN hativot h ON v.hativa_id = h.hativa_id
                WHERE v.vaadot_id = ?
                  AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
            """, (vaada_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'vaadot_id': row[0],
                    'committee_type_id': row[1],
                    'hativa_id': row[2],
                    'vaada_date': row[3],
                    'exception_date_id': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'committee_name': row[7],
                    'hativa_name': row[8],
                    'start_time': row[9],
                    'end_time': row[10]
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
                       search_text: Optional[str] = None,
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

        if search_text:
            query += ' AND (entity_name LIKE ? OR details LIKE ? OR entity_type LIKE ?)'
            search_pattern = f'%{search_text}%'
            params.extend([search_pattern, search_pattern, search_pattern])

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
                            search_text: Optional[str] = None,
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

        if search_text:
            query += ' AND (entity_name LIKE ? OR details LIKE ? OR entity_type LIKE ?)'
            search_pattern = f'%{search_text}%'
            params.extend([search_pattern, search_pattern, search_pattern])

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
    
    def update_event_vaada(self, event_id: int, new_vaada_id: int, user_role: Optional[str] = None) -> bool:
        """Update event's committee meeting with max requests constraint validation on all dates"""
        conn = None
        try:
            # Get max requests setting for committee date (before opening connection)
            max_requests_committee = int(self.get_system_setting('max_requests_committee_date') or '100')
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get event's current expected_requests, maslul_id and source vaada
            cursor.execute("""
                SELECT e.expected_requests, e.vaadot_id, v.vaada_date, e.maslul_id
                FROM events e
                JOIN vaadot v ON e.vaadot_id = v.vaadot_id
                WHERE e.event_id = ?
                  AND (e.is_deleted = 0 OR e.is_deleted IS NULL)
                  AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
            """, (event_id,))
            
            event_data = cursor.fetchone()
            if not event_data:
                conn.close()
                raise ValueError("האירוע לא נמצא במערכת")
            
            expected_requests = event_data[0]
            source_vaada_id = event_data[1]
            maslul_id = event_data[3]
            
            # Get target committee date and maslul stage durations
            cursor.execute("""
                SELECT v.vaada_date, m.stage_a_days, m.stage_b_days, m.stage_c_days, m.stage_d_days
                FROM vaadot v
                JOIN maslulim m ON m.maslul_id = ?
                WHERE v.vaadot_id = ?
                  AND (v.is_deleted = 0 OR v.is_deleted IS NULL)
            """, (maslul_id, new_vaada_id))
            target_data = cursor.fetchone()
            if not target_data:
                conn.close()
                raise ValueError("הועדה היעד לא נמצאה במערכת")
            
            target_vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days = target_data
            
            # Close connection before calling constraint check functions (which open their own connections)
            conn.close()
            conn = None
            
            # Check max requests per day constraint for target committee date (excluding this event, skip for admins)
            if user_role != 'admin':
                current_total_requests = self.get_total_requests_on_date(target_vaada_date, exclude_event_id=event_id)
                new_total_requests = current_total_requests + expected_requests
                
                if new_total_requests > max_requests_committee:
                    raise ValueError(f'חריגה מאילוץ מקסימום בקשות ביום ועדה: התאריך {target_vaada_date} כבר מכיל {current_total_requests} בקשות צפויות. העברת אירוע זה עם {expected_requests} בקשות תגרום לסך של {new_total_requests} (המגבלה היא {max_requests_committee})')
            
            # Calculate derived dates for the target committee
            stage_dates = self.calculate_stage_dates(target_vaada_date, stage_a_days, stage_b_days, stage_c_days, stage_d_days)
            
            # Check max requests per day constraint on derived dates (excluding this event)
            derived_constraint_error = self.check_derived_dates_constraints(stage_dates, expected_requests, exclude_event_id=event_id, user_role=user_role)
            if derived_constraint_error:
                raise ValueError(derived_constraint_error)
            
            # Open new connection for the update
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update event's committee meeting and derived dates
            cursor.execute("""
                UPDATE events 
                SET vaadot_id = ?,
                    call_deadline_date = ?,
                    intake_deadline_date = ?,
                    review_deadline_date = ?,
                    response_deadline_date = ?
                WHERE event_id = ?
            """, (new_vaada_id, 
                  stage_dates['call_deadline_date'], 
                  stage_dates['intake_deadline_date'],
                  stage_dates['review_deadline_date'], 
                  stage_dates['response_deadline_date'], 
                  event_id))
            
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

                      role: str = 'viewer', hativa_id: Optional[int] = None,
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
        import time
        
        # Retry logic for database locked errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                # Azure AD users don't use password authentication, but DB requires a value
                # Use a placeholder that cannot be used for login
                dummy_password = 'AZURE_AD_NO_PASSWORD_AUTH'
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, full_name, role, auth_source, ad_dn)
                    VALUES (?, ?, ?, ?, ?, 'ad', ?)
                ''', (username, email, dummy_password, full_name, role, ad_dn))
                user_id = cursor.lastrowid
                
                # If hativa_id provided, add to user_hativot table
                if hativa_id:
                    cursor.execute('''
                        INSERT OR IGNORE INTO user_hativot (user_id, hativa_id)
                        VALUES (?, ?)
                    ''', (user_id, hativa_id))
                
                conn.commit()
                conn.close()
                return user_id
            except sqlite3.OperationalError as e:
                if 'locked' in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)  # Wait before retry
                    continue
                raise  # Re-raise if not a lock error or final attempt
    
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
        Get user by username regardless of auth source (case-insensitive)
        
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
            WHERE LOWER(u.username) = LOWER(?)
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
    
    # Recycle Bin Functions
    def get_deleted_vaadot(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get all deleted committee meetings"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT v.*, ct.name as committee_name, h.name as hativa_name,
                   u.full_name as deleted_by_name, u.username as deleted_by_username
            FROM vaadot v
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON v.hativa_id = h.hativa_id
            LEFT JOIN users u ON v.deleted_by = u.user_id
            WHERE v.is_deleted = 1
        '''
        params = []
        
        if hativa_id:
            query += ' AND v.hativa_id = ?'
            params.append(hativa_id)
        
        query += ' ORDER BY v.deleted_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{'vaadot_id': row[0], 'committee_type_id': row[1], 'hativa_id': row[2],
                'vaada_date': row[3], 'status': row[4], 'exception_date_id': row[5],
                'notes': row[6], 'created_at': row[7], 'is_deleted': row[8],
                'deleted_at': row[9], 'deleted_by': row[10],
                'committee_name': row[11], 'hativa_name': row[12],
                'deleted_by_name': row[13] if len(row) > 13 else None,
                'deleted_by_username': row[14] if len(row) > 14 else None} for row in rows]
    
    def get_deleted_events(self, hativa_id: Optional[int] = None) -> List[Dict]:
        """Get all deleted events"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT e.event_id, e.vaadot_id, e.maslul_id, e.name, e.event_type, 
                   e.expected_requests, e.call_publication_date, e.created_at,
                   e.call_deadline_date, e.intake_deadline_date, e.review_deadline_date, 
                   e.response_deadline_date, e.actual_submissions, e.scheduled_date, 
                   e.status, e.is_deleted, e.deleted_at, e.deleted_by,
                   m.name as maslul_name, m.hativa_id as maslul_hativa_id,
                   v.vaada_date, ct.name as committee_name, h.name as hativa_name,
                   u.full_name as deleted_by_name, u.username as deleted_by_username
            FROM events e
            JOIN maslulim m ON e.maslul_id = m.maslul_id
            JOIN vaadot v ON e.vaadot_id = v.vaadot_id
            JOIN committee_types ct ON v.committee_type_id = ct.committee_type_id
            JOIN hativot h ON m.hativa_id = h.hativa_id
            LEFT JOIN users u ON e.deleted_by = u.user_id
            WHERE e.is_deleted = 1
        '''
        params = []
        
        if hativa_id:
            query += ' AND m.hativa_id = ?'
            params.append(hativa_id)
        
        query += ' ORDER BY e.deleted_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{'event_id': row[0], 'vaadot_id': row[1], 'maslul_id': row[2],
                'name': row[3], 'event_type': row[4], 'expected_requests': row[5],
                'call_publication_date': row[6], 'created_at': row[7],
                'call_deadline_date': row[8], 'intake_deadline_date': row[9],
                'review_deadline_date': row[10], 'response_deadline_date': row[11],
                'actual_submissions': row[12], 'scheduled_date': row[13],
                'status': row[14], 'is_deleted': row[15], 'deleted_at': row[16],
                'deleted_by': row[17], 'maslul_name': row[18], 'maslul_hativa_id': row[19],
                'vaada_date': row[20], 'committee_name': row[21], 'hativa_name': row[22],
                'deleted_by_name': row[23], 'deleted_by_username': row[24]} for row in rows]
    
    def restore_vaada(self, vaadot_id: int) -> bool:
        """Restore a deleted committee meeting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Restore the vaada
            cursor.execute('''
                UPDATE vaadot 
                SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL 
                WHERE vaadot_id = ? AND is_deleted = 1
            ''', (vaadot_id,))
            success = cursor.rowcount > 0
            
            # Also restore related events
            if success:
                cursor.execute('''
                    UPDATE events 
                    SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL 
                    WHERE vaadot_id = ? AND is_deleted = 1
                ''', (vaadot_id,))
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error restoring vaada: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def restore_event(self, event_id: int) -> bool:
        """Restore a deleted event"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE events 
                SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL 
                WHERE event_id = ? AND is_deleted = 1
            ''', (event_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error restoring event: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def permanently_delete_vaada(self, vaadot_id: int) -> bool:
        """Permanently delete a committee meeting (hard delete)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete the vaada (events will be cascade deleted due to foreign key)
            cursor.execute('DELETE FROM vaadot WHERE vaadot_id = ? AND is_deleted = 1', (vaadot_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error permanently deleting vaada: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def permanently_delete_event(self, event_id: int) -> bool:
        """Permanently delete an event (hard delete)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM events WHERE event_id = ? AND is_deleted = 1', (event_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error permanently deleting event: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def empty_recycle_bin(self, hativa_id: Optional[int] = None) -> Tuple[int, int]:
        """Permanently delete all items in recycle bin"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete events
            if hativa_id:
                cursor.execute('''
                    DELETE FROM events 
                    WHERE is_deleted = 1 
                    AND maslul_id IN (SELECT maslul_id FROM maslulim WHERE hativa_id = ?)
                ''', (hativa_id,))
            else:
                cursor.execute('DELETE FROM events WHERE is_deleted = 1')
            events_deleted = cursor.rowcount or 0
            
            # Delete vaadot
            if hativa_id:
                cursor.execute('''
                    DELETE FROM vaadot 
                    WHERE is_deleted = 1 AND hativa_id = ?
                ''', (hativa_id,))
            else:
                cursor.execute('DELETE FROM vaadot WHERE is_deleted = 1')
            vaadot_deleted = cursor.rowcount or 0
            
            conn.commit()
            conn.close()
            return vaadot_deleted, events_deleted
        except Exception as e:
            print(f"Error emptying recycle bin: {e}")
            if 'conn' in locals():
                conn.close()
            return 0, 0

    # Calendar Sync Operations
    def create_calendar_sync_record(self, source_type: str, source_id: int, deadline_type: str = None,
                                     calendar_email: str = 'plan@innovationisrael.org.il',
                                     calendar_event_id: str = None) -> int:
        """Create a calendar sync tracking record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO calendar_sync_events
                (source_type, source_id, deadline_type, calendar_email, calendar_event_id, sync_status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (source_type, source_id, deadline_type, calendar_email, calendar_event_id))
            sync_id = cursor.lastrowid
            conn.commit()
            return sync_id
        except sqlite3.IntegrityError:
            # Record already exists, update it instead
            cursor.execute('''
                UPDATE calendar_sync_events
                SET sync_status = 'pending', updated_at = CURRENT_TIMESTAMP
                WHERE source_type = ? AND source_id = ? AND deadline_type = ? AND calendar_email = ?
            ''', (source_type, source_id, deadline_type, calendar_email))
            conn.commit()
            cursor.execute('''
                SELECT sync_id FROM calendar_sync_events
                WHERE source_type = ? AND source_id = ? AND deadline_type = ? AND calendar_email = ?
            ''', (source_type, source_id, deadline_type, calendar_email))
            sync_id = cursor.fetchone()[0]
            return sync_id
        finally:
            conn.close()

    def update_calendar_sync_status(self, sync_id: int, status: str, calendar_event_id: str = None,
                                      error_message: str = None, content_hash: str = None) -> bool:
        """Update calendar sync status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if calendar_event_id:
            if content_hash:
                cursor.execute('''
                    UPDATE calendar_sync_events
                    SET sync_status = ?, calendar_event_id = ?, error_message = ?, content_hash = ?,
                        last_synced = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE sync_id = ?
                ''', (status, calendar_event_id, error_message, content_hash, sync_id))
            else:
                cursor.execute('''
                UPDATE calendar_sync_events
                SET sync_status = ?, calendar_event_id = ?, error_message = ?,
                    last_synced = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE sync_id = ?
                ''', (status, calendar_event_id, error_message, sync_id))
        else:
            cursor.execute('''
                UPDATE calendar_sync_events
                SET sync_status = ?, error_message = ?,
                    last_synced = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE sync_id = ?
            ''', (status, error_message, sync_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_calendar_sync_record(self, source_type: str, source_id: int, deadline_type: str = None,
                                   calendar_email: str = 'plan@innovationisrael.org.il') -> Optional[Dict]:
        """Get calendar sync record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sync_id, source_type, source_id, deadline_type, calendar_event_id, calendar_email,
                   last_synced, sync_status, error_message, created_at, updated_at, content_hash
            FROM calendar_sync_events
            WHERE source_type = ? AND source_id = ? AND deadline_type IS ? AND calendar_email = ?
        ''', (source_type, source_id, deadline_type, calendar_email))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'sync_id': row[0], 'source_type': row[1], 'source_id': row[2],
                'deadline_type': row[3], 'calendar_event_id': row[4], 'calendar_email': row[5],
                'last_synced': row[6], 'sync_status': row[7], 'error_message': row[8],
                'created_at': row[9], 'updated_at': row[10], 'content_hash': row[11] if len(row) > 11 else None
            }
        return None

    def get_pending_calendar_syncs(self, calendar_email: str = 'plan@innovationisrael.org.il') -> List[Dict]:
        """Get all pending calendar sync records"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sync_id, source_type, source_id, deadline_type, calendar_event_id, calendar_email,
                   last_synced, sync_status, error_message, created_at, updated_at
            FROM calendar_sync_events
            WHERE sync_status = 'pending' AND calendar_email = ?
            ORDER BY created_at ASC
        ''', (calendar_email,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'sync_id': row[0], 'source_type': row[1], 'source_id': row[2],
                'deadline_type': row[3], 'calendar_event_id': row[4], 'calendar_email': row[5],
                'last_synced': row[6], 'sync_status': row[7], 'error_message': row[8],
                'created_at': row[9], 'updated_at': row[10]
            }
            for row in rows
        ]

    def delete_calendar_sync_record(self, source_type: str, source_id: int, deadline_type: str = None,
                                      calendar_email: str = 'plan@innovationisrael.org.il') -> bool:
        """Delete calendar sync record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM calendar_sync_events
            WHERE source_type = ? AND source_id = ? AND deadline_type IS ? AND calendar_email = ?
        ''', (source_type, source_id, deadline_type, calendar_email))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def mark_calendar_sync_deleted(self, source_type: str, source_id: int,
                                     calendar_email: str = 'plan@innovationisrael.org.il') -> List[Dict]:
        """Mark all calendar sync records for a source as deleted and return them"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get all sync records for this source
        cursor.execute('''
            SELECT sync_id, source_type, source_id, deadline_type, calendar_event_id, calendar_email,
                   last_synced, sync_status, error_message, created_at, updated_at
            FROM calendar_sync_events
            WHERE source_type = ? AND source_id = ? AND calendar_email = ? AND sync_status != 'deleted'
        ''', (source_type, source_id, calendar_email))

        rows = cursor.fetchall()

        # Mark them as deleted
        cursor.execute('''
            UPDATE calendar_sync_events
            SET sync_status = 'deleted', updated_at = CURRENT_TIMESTAMP
            WHERE source_type = ? AND source_id = ? AND calendar_email = ? AND sync_status != 'deleted'
        ''', (source_type, source_id, calendar_email))

        conn.commit()
        conn.close()

        return [
            {
                'sync_id': row[0], 'source_type': row[1], 'source_id': row[2],
                'deadline_type': row[3], 'calendar_event_id': row[4], 'calendar_email': row[5],
                'last_synced': row[6], 'sync_status': row[7], 'error_message': row[8],
                'created_at': row[9], 'updated_at': row[10]
            }
            for row in rows
        ]

    def get_all_synced_calendar_events(self, calendar_email: str = 'plan@innovationisrael.org.il') -> List[Dict]:
        """Get all calendar sync records that have been synced (have calendar_event_id)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sync_id, source_type, source_id, deadline_type, calendar_event_id, calendar_email,
                   last_synced, sync_status, error_message, created_at, updated_at
            FROM calendar_sync_events
            WHERE calendar_email = ? AND calendar_event_id IS NOT NULL AND calendar_event_id != ''
            ORDER BY created_at ASC
        ''', (calendar_email,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'sync_id': row[0], 'source_type': row[1], 'source_id': row[2],
                'deadline_type': row[3], 'calendar_event_id': row[4], 'calendar_email': row[5],
                'last_synced': row[6], 'sync_status': row[7], 'error_message': row[8],
                'created_at': row[9], 'updated_at': row[10]
            } for row in rows
        ]

    def clear_all_calendar_sync_records(self, calendar_email: str = 'plan@innovationisrael.org.il') -> int:
        """Delete all calendar sync records for a calendar (used when resetting sync)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM calendar_sync_events
            WHERE calendar_email = ?
        ''', (calendar_email,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count
