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
    sla_days INTEGER DEFAULT 45,
    stage_a_days INTEGER DEFAULT 10,
    stage_b_days INTEGER DEFAULT 15,
    stage_c_days INTEGER DEFAULT 10,
    stage_d_days INTEGER DEFAULT 10,
    FOREIGN KEY (hativa_id) REFERENCES hativot (hativa_id) ON DELETE CASCADE
)
```
- **Purpose**: Sub-units within divisions for specific programs/tracks
- **Relationship**: Many-to-One with Hativot
- **SLA Configuration**: Each route has configurable SLA and stage duration settings:
  - `sla_days`: Total SLA days for the route
  - `stage_a_days`: Duration for call publication stage
  - `stage_b_days`: Duration for intake stage
  - `stage_c_days`: Duration for review stage
  - `stage_d_days`: Duration for response stage

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
    actual_submissions INTEGER DEFAULT 0,
    call_publication_date DATE,
    call_deadline_date DATE,
    intake_deadline_date DATE,
    review_deadline_date DATE,
    response_deadline_date DATE,
    scheduled_date DATE,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vaadot_id) REFERENCES vaadot (vaadot_id) ON DELETE CASCADE,
    FOREIGN KEY (maslul_id) REFERENCES maslulim (maslul_id) ON DELETE CASCADE
)
```
- **Purpose**: Specific events/agenda items within committee meetings
- **Features**: 
  - Links events to specific meeting instances and routes
  - Tracks expected vs actual submissions for capacity planning
  - **Automated Stage Date Calculation**: When an event is created or updated, the system automatically calculates stage deadline dates based on the committee meeting date and the route's stage duration settings:
    - `call_publication_date`: User-defined date when the call is published (optional)
    - `call_deadline_date`: Auto-calculated deadline for call publication stage
    - `intake_deadline_date`: Auto-calculated deadline for intake stage
    - `review_deadline_date`: Auto-calculated deadline for review stage
    - `response_deadline_date`: Auto-calculated deadline for response stage (after committee meeting)
  - All date calculations respect business days, weekends, and exception dates (holidays)

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

1. **Configurable Meeting Limits**: 
   - Maximum meetings per day (default: 1, configurable)
   - Maximum meetings per standard week (default: 3, configurable)
   - Maximum meetings during third week of month (default: 4, configurable)
   - System enforces these constraints when creating or updating meetings

2. **Request Load Management**: 
   - Maximum total expected requests per day across all events (default: 100, configurable)
   - System validates total request load when adding or updating events
   - Prevents system overload and ensures manageable workload

3. **Division Hierarchy**: Events can only link routes (maslulim) and committees from the same division

4. **Committee Scheduling**: Committee types define fixed days of the week and frequency (weekly/monthly)

5. **Business Days & Work Schedule**: 
   - System operates on configurable work days (default: Sunday-Friday morning, Israeli business week)
   - All date calculations respect business days, weekends, and exception dates (holidays)
   - Business day calculations automatically skip non-working days

6. **Division-Specific Committee Types**: Each division can define its own committee types with custom schedules

7. **Meeting Instance Model**: Vaadot represents specific meeting instances, not general committee definitions

8. **Automated Stage Date Calculation**: 
   - Event deadline dates are automatically calculated based on committee meeting date
   - Uses route-specific stage durations (stage_a_days, stage_b_days, etc.)
   - Respects business days and exception dates in all calculations
   - Recalculates automatically when meeting date or route is changed

### Key Features

- **Multi-Division Support**: Each division can have its own committees, routes, and users
- **Flexible Scheduling**: Support for both weekly and monthly committee frequencies with specific week-of-month for monthly committees
- **Exception Handling**: Holiday and special date management affects scheduling
- **Audit Trail**: Created timestamps on all entities
- **Soft Deletes**: is_active flags for logical deletion
- **Color Coding**: Visual organization with custom division colors
- **Role-Based Access**: Admin, manager, and user roles with division-based permissions
- **Automatic Scheduling**: AI-powered scheduling system respects all business constraints
- **Automated Stage Date Calculation**: 
  - Automatic calculation of all event stage deadlines based on committee meeting date
  - Route-specific stage duration configuration (stage_a_days, stage_b_days, stage_c_days, stage_d_days)
  - Business day calculations that skip weekends and holidays
  - Automatic recalculation when meeting dates or routes change
- **Capacity Management**:
  - Configurable limits on meetings per day and per week
  - Special capacity rules for third week of each month
  - Total request load tracking and validation per day
  - Prevents system overload and ensures manageable workload
- **Business Day Awareness**:
  - Configurable work days and work hours
  - Automatic business day calculations for all deadlines
  - Integration with exception dates (holidays, sabbaths, special days)
  - SLA calculations respect non-working days
- **Data Tracking & Analytics**:
  - Track expected vs actual submissions for each event
  - Monitor request load across different dates
  - Meeting distribution analytics (daily, weekly, monthly)

### Data Integrity

- **Referential Integrity**: All foreign key relationships enforced with CASCADE deletes where appropriate
- **Data Validation**: Check constraints on enums (event_type, frequency, role, etc.)
- **Unique Constraints**: Prevent duplicate committee names within divisions, unique meeting instances
- **Business Logic Validation**: Server-side and client-side validation ensures data consistency

### System Configuration

The system includes configurable settings stored in `system_settings`:

#### Work Schedule Settings
- **work_days**: "6,0,1,2,3,4" (Python weekday: 0=Monday ... 6=Sunday; Israeli business week: Sunday-Friday morning)
- **work_start_time**: "08:00" - Daily work start time
- **work_end_time**: "17:00" - Daily work end time

#### Editing & Academic Settings
- **editing_period_active**: Controls general user editing permissions (1=yes, 0=admin only)
- **editing_deadline**: Date when general user editing period ends (e.g., "2024-10-31")
- **academic_year_start**: Start of current academic year (e.g., "2024-09-01")

#### Scheduling Constraints
- **sla_days_before**: Default SLA days before committee meeting (default: 14)
- **max_meetings_per_day**: Maximum number of committee meetings per calendar day (default: 1)
- **max_weekly_meetings**: Maximum number of committee meetings per standard week (default: 3)
- **max_third_week_meetings**: Maximum number of committee meetings during the third week of a month (default: 4)
- **max_requests_per_day**: Maximum total expected requests per day across all events (default: 100)

These constraints ensure:
- Only one committee meeting per day (configurable)
- Maximum 3 meetings per week (standard weeks)
- Maximum 4 meetings during the third week of each month (allows for increased capacity)
- Total daily request load doesn't exceed system capacity

This ERD represents a comprehensive committee management system designed for organizational scheduling and event tracking with proper data integrity, business rule enforcement, and modern features like automatic scheduling and role-based access control.
