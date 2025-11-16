# Azure AD Calendar Sync Implementation

## Overview
This document describes the implementation of automatic calendar synchronization to the shared Microsoft 365 calendar at `plan@innovationisrael.org.il`.

## Implementation Date
November 16, 2025

## Features Implemented

### 1. Database Schema
- **New Table**: `calendar_sync_events`
  - Tracks synchronization state for each committee meeting and event deadline
  - Fields: sync_id, source_type, source_id, deadline_type, calendar_event_id, sync_status, error_message, timestamps
  - Indexes for efficient querying

- **System Settings** (added to `system_settings` table):
  - `calendar_sync_enabled`: Enable/disable calendar sync (default: enabled)
  - `calendar_sync_email`: Target calendar email (default: plan@innovationisrael.org.il)
  - `calendar_sync_interval_hours`: Sync frequency in hours (default: 1)

### 2. Calendar Service (`services/calendar_service.py`)
New service class for Microsoft Graph API calendar operations:
- `create_calendar_event()`: Create new calendar events
- `update_calendar_event()`: Update existing calendar events
- `delete_calendar_event()`: Delete calendar events
- `sync_committee_to_calendar()`: Sync individual committee meetings
- `sync_event_deadlines_to_calendar()`: Sync all event deadlines
- `sync_all()`: Full synchronization of all committees and events

**What Gets Synced:**
- **Committee Meetings**: All vaadot records → Calendar events with committee type and division info
- **Event Deadlines**: All 5 deadline types per event → Separate calendar events:
  - call_publication_date (פרסום קול קורא)
  - call_deadline_date (מועד אחרון להגשת בקשות)
  - intake_deadline_date (מועד אחרון לקליטה)
  - review_deadline_date (מועד אחרון לסיום בחינה)
  - response_deadline_date (מועד אחרון למתן תשובות)

**Event Details:**
- All calendar events are all-day events
- Rich HTML descriptions with all relevant data
- Automatic timezone handling (Asia/Jerusalem)

### 3. Authentication Updates (`services/ad_service.py`)
- Added `get_app_only_token()` method for service-to-service authentication
- Uses client credentials flow (application permissions)
- No user interaction required for automated sync

### 4. Background Scheduler (`services/calendar_sync_scheduler.py`)
- Automatic hourly synchronization using APScheduler
- Runs in background without blocking the main application
- Configurable sync interval via system settings
- Comprehensive logging and audit trail
- Prevents overlapping sync executions

### 5. API Endpoints (`app.py`)
New admin-only API endpoints:
- `POST /api/calendar/sync`: Manually trigger full sync
- `GET /api/calendar/sync/status`: Get sync status and next run time
- `POST /api/calendar/sync/committee/<vaadot_id>`: Sync single committee
- `POST /api/calendar/sync/event/<event_id>`: Sync single event

### 6. User Interface (`templates/base.html`)
- New menu item in admin dropdown: "סנכרון לוח שנה"
- Modal dialog showing:
  - Sync enabled/disabled status
  - Target calendar email
  - Scheduler running status
  - Next scheduled sync time
  - Manual sync trigger button

### 7. Database Methods (`database.py`)
New calendar sync tracking methods:
- `create_calendar_sync_record()`
- `update_calendar_sync_status()`
- `get_calendar_sync_record()`
- `get_pending_calendar_syncs()`
- `delete_calendar_sync_record()`
- `mark_calendar_sync_deleted()`

## Azure AD Configuration Required

### Application Permissions Needed
The Azure AD app registration must be granted the following **Application Permission**:
- `Calendars.ReadWrite.Shared` or `Calendars.ReadWrite`

**Important**: This requires admin consent in the Azure Portal.

### How to Configure:
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Select your app (Client ID: `7950149f-e90d-482e-9e12-1f5ff317beae`)
3. Navigate to "API permissions"
4. Click "Add a permission"
5. Select "Microsoft Graph"
6. Select "Application permissions"
7. Search for and select: `Calendars.ReadWrite.Shared`
8. Click "Add permissions"
9. **IMPORTANT**: Click "Grant admin consent for [Your Organization]"
10. Wait for the consent status to show "Granted"

## Sync Behavior

### One-Way Sync (Database → Calendar)
- Changes in the database are pushed to the calendar
- Calendar events are **not** pulled back to the database
- Updates to committees/events trigger calendar updates
- Deletions (is_deleted=1) or cancellations trigger calendar event deletion

### Sync Triggers
1. **Automatic**: Hourly background sync (default)
2. **Manual**: Admin can trigger sync via UI
3. **Per-item**: API endpoints allow syncing individual items

### Error Handling
- Failed syncs are logged with error messages
- Sync status tracked in `calendar_sync_events` table
- Retry logic on next scheduled sync
- Audit logging for all sync operations

## Files Modified

1. `/requirements.txt` - Added APScheduler>=3.10.0
2. `/database.py` - Added calendar sync table and methods
3. `/services/ad_service.py` - Added app-only token acquisition
4. `/services/calendar_service.py` - **NEW FILE** - Calendar sync service
5. `/services/calendar_sync_scheduler.py` - **NEW FILE** - Background scheduler
6. `/app.py` - Added API endpoints and scheduler initialization
7. `/templates/base.html` - Added UI controls and modal

## Testing Checklist

### Before First Use:
- [ ] Configure Azure AD app permissions (see above)
- [ ] Grant admin consent for Calendar permissions
- [ ] Verify .env has all Azure AD credentials
- [ ] Check `calendar_sync_enabled` setting is set to `1`
- [ ] Verify `calendar_sync_email` is set to `plan@innovationisrael.org.il`

### Testing Sync:
1. **Test Manual Sync**:
   - Log in as admin
   - Click on your user menu (top right)
   - Select "סנכרון לוח שנה"
   - View sync status in modal
   - Click "הפעל סנכרון כעת"
   - Wait for completion message

2. **Verify in Calendar**:
   - Open Outlook with plan@innovationisrael.org.il account
   - Check calendar for committee meetings
   - Check calendar for event deadlines
   - Verify all-day events show correct dates
   - Verify event descriptions contain all details

3. **Test Updates**:
   - Update a committee date in the system
   - Trigger manual sync or wait for hourly sync
   - Verify calendar event updated

4. **Test Deletions**:
   - Soft-delete a committee (is_deleted=1)
   - Trigger manual sync
   - Verify calendar event removed

5. **Check Audit Logs**:
   - Go to "יומן ביקורת" in admin menu
   - Filter for calendar_sync actions
   - Verify all sync operations are logged

### Monitoring:
- Check application logs for sync operations
- Monitor sync status via admin UI
- Review `calendar_sync_events` table for error messages
- Check audit logs for sync history

## Troubleshooting

### Sync Not Working
1. Check Azure AD permissions are granted
2. Verify .env credentials are correct
3. Check `calendar_sync_enabled` setting
4. Review error messages in `calendar_sync_events` table
5. Check application logs for errors

### Permission Errors
- Error: "Insufficient privileges to complete the operation"
  - Solution: Grant admin consent for Calendars.ReadWrite.Shared permission

### Token Errors
- Error: "Failed to acquire access token"
  - Solution: Verify Azure AD credentials in .env file
  - Check client secret hasn't expired

### Calendar Events Not Appearing
1. Verify correct calendar email in settings
2. Check if events are in the past (might be filtered in Outlook)
3. Verify sync status shows "synced" not "failed"
4. Check calendar permissions for the service account

## Architecture Notes

### Why App-Only Authentication?
- Allows automated sync without user interaction
- Service-to-service authentication using client credentials
- More reliable for scheduled background tasks
- No token expiration issues (auto-refresh by MSAL)

### Why Hourly Sync?
- Balances freshness vs. API rate limits
- Configurable via system settings
- Manual sync available for immediate updates
- Most committees/events don't change frequently

### Database Tracking
- Prevents duplicate calendar events
- Enables efficient updates (only changed items)
- Provides audit trail and error tracking
- Supports future features (two-way sync, selective sync)

## Future Enhancements (Not Implemented)

1. **Two-Way Sync**: Pull calendar changes back to database
2. **Selective Sync**: Sync only specific divisions or date ranges
3. **Email Notifications**: Alert admins of sync failures
4. **Batch Operations**: More efficient Graph API batch requests
5. **Conflict Resolution**: Handle manual calendar edits
6. **Multiple Calendars**: Sync to division-specific calendars
7. **Calendar Categories**: Color-code events by division

## Support

For issues or questions:
1. Check application logs
2. Review audit logs in admin panel
3. Verify Azure AD configuration
4. Contact system administrator

## Version
Implementation Version: 1.0
Date: November 16, 2025
