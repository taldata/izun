# Role Constraint Migration Instructions

## Overview
This migration fixes the role CHECK constraint in the users table from the old role system (`admin`, `manager`, `user`) to the new role system (`admin`, `editor`, `viewer`).

## What the Migration Does
1. Creates a backup of the database
2. Creates a new users table with the updated CHECK constraint
3. Migrates all user data with role mapping:
   - `admin` → `admin`
   - `manager` → `editor`
   - `user` → `viewer`
4. Replaces the old table with the new one

## Running on Render (Production)

### Option 1: Using Render Shell (Recommended)

1. Go to your Render dashboard: https://dashboard.render.com/
2. Navigate to your service: `committee-management-izun`
3. Click on the **Shell** tab (on the left sidebar)
4. Run the following commands:

```bash
# Navigate to the app directory
cd /opt/render/project/src

# Check the database exists
ls -la /var/data/committee_system.db

# Run the migration
python3 fix_role_constraint.py /var/data/committee_system.db
```

5. Review the output to confirm:
   - Backup was created successfully
   - User count matches (before and after)
   - Role migration summary shows correct mappings
   - Final user list displays correctly

### Option 2: Using SSH (if enabled)

If you have SSH access configured on Render:

```bash
# SSH into your Render instance
ssh <your-render-instance>

# Run the migration
cd /opt/render/project/src
python3 fix_role_constraint.py /var/data/committee_system.db
```

### Option 3: Temporary Deploy with Migration

If you want to run it as part of a deployment:

1. Add a one-time migration command to your `start.sh`:

```bash
# Add before the main app starts
python3 fix_role_constraint.py /var/data/committee_system.db || true
```

2. Deploy to Render
3. Remove the command after successful migration

## Verification Steps

After running the migration, verify it was successful:

### 1. Check the Migration Output
You should see:
```
✅ Migration completed successfully!

Final user list:
  [ID] Name (username) - role
```

### 2. Test User Role Updates via Web UI
1. Log in to the admin panel
2. Try to change a user's role to `viewer` or `editor`
3. Confirm no errors occur

### 3. Query the Database Directly (Optional)
```bash
# On Render shell
sqlite3 /var/data/committee_system.db "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
```

Should show:
```sql
CHECK (role IN ('admin', 'editor', 'viewer'))
```

## Backup Information

The migration automatically creates a backup with timestamp:
```
/var/data/committee_system.db.backup_YYYYMMDD_HHMMSS
```

If you need to restore from backup:
```bash
cp /var/data/committee_system.db.backup_YYYYMMDD_HHMMSS /var/data/committee_system.db
```

## Rollback Plan

If something goes wrong:

1. **Immediate rollback:**
   ```bash
   # Find the backup file
   ls -la /var/data/*.backup_*

   # Restore from backup
   cp /var/data/committee_system.db.backup_YYYYMMDD_HHMMSS /var/data/committee_system.db

   # Restart the service
   ```

2. **If no backup is available:**
   - Contact support
   - The migration is non-destructive (creates new table before dropping old)
   - Transaction-based (rolls back on any error)

## Expected Output

```
Database path: /var/data/committee_system.db
Creating backup: /var/data/committee_system.db.backup_20251029_142047
Backup created successfully
Migrating database: /var/data/committee_system.db
Creating new users table with updated CHECK constraint...
Migrating user data with role mapping...
Migrated 2 users successfully

Role migration summary:
  admin -> admin: 2 users

Replacing old table with new table...

✅ Migration completed successfully!

Final user list:
  [5] Shiran Ben Simhon (shiran.bs) - admin
  [6] Tal Sabag (tal.s) - admin
```

## Troubleshooting

### Error: Database file not found
- Verify the path: `/var/data/committee_system.db`
- Check the DATABASE_PATH environment variable in Render settings

### Error: Permission denied
- Ensure the app has write permissions to `/var/data/`
- Check Render disk mount configuration

### Error: No space left on device
- Check available disk space on the Render persistent disk
- Consider cleaning up old backups

### Migration runs but changes don't persist
- Ensure you're using the persistent disk path: `/var/data/`
- Verify the disk is mounted correctly in `render.yaml`

## Questions?
If you encounter any issues, check:
1. Render logs for any errors
2. The backup file was created successfully
3. The transaction completed without rollback
