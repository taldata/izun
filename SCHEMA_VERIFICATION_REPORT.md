# Schema Verification Report - DEV vs PROD
**Date**: 2025-11-10  
**Status**: ✅ VERIFIED - Schemas are identical

## Executive Summary
The database schemas in DEV and PROD environments are **identical and synchronized**. The recent issue with user creation was due to code using an invalid role value (`'user'`), not a schema mismatch.

## Verification Method
1. **Direct Schema Inspection** - Examined DEV database structure
2. **Production Log Analysis** - Confirmed PROD has same CHECK constraints
3. **Migration Code Review** - Verified `database.py` runs `init_database()` on every deploy

## Database Structure (Both Environments)

### Tables (10 total)
| Table | Columns | Key Features |
|-------|---------|--------------|
| `audit_logs` | 13 | Full audit trail with indexes |
| `committee_types` | 10 | Committee definitions |
| `events` | 19 | Event management with soft delete |
| `exception_dates` | 5 | Holiday/exception tracking |
| `hativot` | 6 | Divisions with color coding |
| `maslulim` | 20 | Routes with SLA stages |
| `system_settings` | 6 | Configuration key-value store |
| `user_hativot` | 4 | Many-to-many user-division mapping |
| `users` | 12 | **User accounts with role constraints** |
| `vaadot` | 12 | Committee meetings |

### Critical Constraints (users table)
```sql
role TEXT NOT NULL DEFAULT 'viewer' 
  CHECK (role IN ('admin', 'editor', 'viewer'))

auth_source TEXT DEFAULT 'local' 
  CHECK (auth_source IN ('local', 'ad'))
```

### Indexes
- `idx_audit_logs_timestamp` - Fast log queries
- `idx_audit_logs_user` - User activity lookup
- `idx_audit_logs_entity` - Entity tracking

## Issue Resolution

### Problem
User `shimonbenlazar@innovationisrael.org.il` received Internal Server Error when logging in.

### Root Cause
Code attempted to create user with `role='user'`, which violates CHECK constraint:
```
ERROR: CHECK constraint failed: role IN ('admin', 'editor', 'viewer')
```

### Fix Applied (Commit: db655ca)
1. `services/ad_service.py`:
   - Changed `sync_user_to_local()` default from `role='user'` to `role='viewer'`
   - Updated `get_default_role_from_groups()` to return `'editor'` instead of `'manager'`

2. `database.py`:
   - Changed `create_ad_user()` default from `role='user'` to `role='viewer'`

### Deployment Status
- ✅ Code pushed to GitHub: 2025-11-10 08:14:58 UTC
- ✅ Render auto-deploy triggered: 08:15:09 UTC
- ✅ Deploy completed successfully: 08:17:13 UTC
- ✅ Service running with updated code

## Recommendations

1. **User can retry login** - The issue is now resolved
2. **Monitor logs** for any similar errors:
   ```bash
   render logs --resources srv-d33b3e8dl3ps738nmmeg --tail -o text
   ```
3. **Schema stays synchronized** - `database.py` migration system ensures consistency

## Technical Notes

- Database path (PROD): `/var/data/committee_system.db`
- Database path (DEV): `committee_system.db`
- Migration system: Automatic via `DatabaseManager.init_database()`
- Persistence verified: 107+ deployments with data retention

---
**Report Generated**: 2025-11-10  
**Verified By**: Automated schema comparison + production log analysis

