# Entity Relationship Diagram (ERD)

## Committee Management System Database Schema

### Tables Overview

#### 1. Hativot (Divisions)
```sql
hativot (
    hativa_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    color TEXT DEFAULT '#007bff',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```
- **Purpose**: Organizational divisions/departments
- **Features**: Custom colors for visual organization, soft delete support

#### 2. Maslulim (Routes/Tracks)
```sql
maslulim (
    maslul_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hativa_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE
)
```
- **Purpose**: Sub-units within divisions for specific programs/tracks
- **Relationship**: Many-to-One with Hativot

#### 3. Committee_Types (Committee Definitions)
```sql
committee_types (
    committee_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hativa_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    scheduled_day INTEGER NOT NULL, -- 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday
    frequency TEXT NOT NULL DEFAULT 'weekly' CHECK (frequency IN ('weekly', 'monthly')),
    week_of_month INTEGER DEFAULT NULL, -- For monthly: 1=first week, 2=second, etc.
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE,
    UNIQUE(hativa_id, name)
)
```
- **Purpose**: General committee definitions with scheduling rules
- **Features**: Division-specific committee types, flexible scheduling (weekly/monthly)

#### 4. Vaadot (Committee Meetings)
```sql
vaadot (
    vaadot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    committee_type_id INTEGER NOT NULL,
    hativa_id INTEGER NOT NULL,
    vaada_date DATE NOT NULL, -- actual date of the committee meeting
    status TEXT DEFAULT 'planned', -- planned, scheduled, completed, cancelled
    exception_date_id INTEGER, -- reference to exception_dates if meeting is affected
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (committee_type_id) REFERENCES committee_types (committee_type_id),
    FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id),
    FOREIGN KEY (exception_date_id) REFERENCES exception_dates (date_id),
    UNIQUE(committee_type_id, hativa_id, vaada_date)
)
```
- **Purpose**: Specific committee meeting instances
- **Features**: Links to committee types, tracks meeting status, exception handling

#### 5. Events
```sql
events (
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
```
- **Purpose**: Specific events/agenda items within committee meetings
- **Features**: Links events to specific meeting instances and routes

#### 6. Exception_Dates
```sql
exception_dates (
    date_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_date DATE NOT NULL UNIQUE,
    description TEXT,
    type TEXT DEFAULT 'holiday', -- holiday, sabbath, special
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```
- **Purpose**: Holidays, sabbaths, and other non-working days
- **Features**: Affects automatic scheduling and meeting planning

#### 7. Users (Authentication)
```sql
users (
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
```
- **Purpose**: User authentication and authorization
- **Features**: Role-based access control, division-based permissions

#### 8. System_Settings
```sql
system_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    FOREIGN KEY (updated_by) REFERENCES users (user_id)
)
```
- **Purpose**: Global system configuration
- **Features**: Configurable work days, SLA settings, academic year settings

### Relationships Diagram

```
┌─────────────┐    1:N    ┌─────────────────┐    1:N    ┌─────────────┐
│   Hativot   │ ────────→ │ Committee_Types │ ────────→ │   Vaadot    │
│ (Divisions) │           │  (Definitions)  │           │ (Meetings)  │
└─────────────┘           └─────────────────┘           └─────────────┘
       │                                                        │
       │ 1:N                                                    │ 1:N
       ↓                                                        ↓
┌─────────────┐                                          ┌─────────────┐
│  Maslulim   │                                          │   Events    │
│  (Routes)   │ ────────────────────────────────────────→│             │
└─────────────┘                    N:1                   └─────────────┘

┌─────────────────┐    1:N    ┌─────────────┐
│ Exception_Dates │ ────────→ │   Vaadot    │
│   (Holidays)    │           │ (Meetings)  │
└─────────────────┘           └─────────────┘

┌─────────────┐    1:N    ┌─────────────┐
│   Hativot   │ ────────→ │    Users    │
│ (Divisions) │           │             │
└─────────────┘           └─────────────┘
```

### Business Rules

1. **One Committee Per Day**: Only one committee meeting can be scheduled per day across all divisions
2. **Division Hierarchy**: Events can only link routes (maslulim) and committees from the same division
3. **Committee Scheduling**: Committee types define fixed days of the week and frequency (weekly/monthly)
4. **Business Days**: System operates on Sunday-Thursday schedule (Israeli business week)
5. **Division-Specific Committee Types**: Each division can define its own committee types with custom schedules
6. **Meeting Instance Model**: Vaadot represents specific meeting instances, not general committee definitions

### Key Features

- **Multi-Division Support**: Each division can have its own committees, routes, and users
- **Flexible Scheduling**: Support for both weekly and monthly committee frequencies with specific week-of-month for monthly committees
- **Exception Handling**: Holiday and special date management affects scheduling
- **Audit Trail**: Created timestamps on all entities
- **Soft Deletes**: is_active flags for logical deletion
- **Color Coding**: Visual organization with custom division colors
- **Role-Based Access**: Admin, manager, and user roles with division-based permissions
- **Automatic Scheduling**: AI-powered scheduling system respects all business constraints

### Data Integrity

- **Referential Integrity**: All foreign key relationships enforced with CASCADE deletes where appropriate
- **Data Validation**: Check constraints on enums (event_type, frequency, role, etc.)
- **Unique Constraints**: Prevent duplicate committee names within divisions, unique meeting instances
- **Business Logic Validation**: Server-side and client-side validation ensures data consistency

### System Configuration

The system includes configurable settings stored in `system_settings`:

- **work_days**: "0,1,2,3,4" (Sunday-Thursday)
- **editing_period_active**: Controls general user editing permissions
- **academic_year_start**: Start of current academic year
- **sla_days_before**: Default SLA days before committee meeting

This ERD represents a comprehensive committee management system designed for organizational scheduling and event tracking with proper data integrity, business rule enforcement, and modern features like automatic scheduling and role-based access control.
