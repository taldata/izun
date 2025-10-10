# Data Persistence Testing Guide for Render

This guide will help you verify that your data persists across deployments on Render.

## Method 1: Automatic Verification Script

### Add verification to your build process:

1. **Update `render.yaml`** to run the verification script after deployment:

```yaml
buildCommand: pip install -r requirements.txt && python migrate_db.py && python verify_persistence.py
```

2. **Check Render logs** after deployment to see the verification output.

---

## Method 2: Manual Testing Steps

### Step 1: Check Render Dashboard

1. Go to your Render Dashboard: https://dashboard.render.com
2. Select your service: `committee-management-izun`
3. Click on **"Disks"** tab in the left sidebar
4. Verify you see:
   - Disk Name: `sqlite-data`
   - Mount Path: `/var/data`
   - Size: `1 GB`
   - Status: `Active`

### Step 2: Add Test Data

1. **Deploy your application**
2. **Log in** to your application
3. **Create some test data**:
   - Add a new Hativa (חטיבה)
   - Add a Maslul (מסלול)
   - Add a Committee Type (סוג ועדה)
   - Add a Committee Meeting (ועדה)
4. **Note the data** you created

### Step 3: Force a Redeploy

1. Go to Render Dashboard
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Wait for deployment to complete

### Step 4: Verify Data Persisted

1. **Log back into your application**
2. **Check if your test data is still there**
3. ✅ If data is there → Persistence is working!
4. ❌ If data is gone → Something is wrong

---

## Method 3: Use Render Shell

### Connect to your service:

1. Go to Render Dashboard
2. Select your service
3. Click **"Shell"** tab (or use Render CLI)
4. Run these commands:

```bash
# Check if persistent disk is mounted
df -h | grep /var/data

# Check if database exists
ls -lh /var/data/

# Check database file
ls -lh /var/data/committee_system.db

# Check database size and modification time
stat /var/data/committee_system.db

# Run verification script
python verify_persistence.py

# Check database records (optional)
python -c "
import sqlite3
conn = sqlite3.connect('/var/data/committee_system.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print(f'Users: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM hativot')
print(f'Hativot: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM vaadot')
print(f'Vaadot: {cursor.fetchone()[0]}')
conn.close()
"
```

---

## Method 4: Check Environment Variables

### Via Render Dashboard:

1. Go to your service settings
2. Click **"Environment"** tab
3. Verify `DATABASE_PATH` is set to: `/var/data/committee_system.db`

### Via Shell:

```bash
echo $DATABASE_PATH
# Should output: /var/data/committee_system.db
```

---

## Method 5: Test Deployment Persistence

### Full Test Procedure:

```bash
# 1. Before deployment - note current data
# Connect via Shell and run:
python -c "
import sqlite3
conn = sqlite3.connect('/var/data/committee_system.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print(f'Users before: {cursor.fetchone()[0]}')
conn.close()
"

# 2. Make a small code change (add a comment somewhere)
# 3. Commit and push to trigger deployment
# 4. After deployment completes, run the same command
# 5. Count should be the same = persistence working!
```

---

## Expected Results

### ✅ Persistence is Working If:

- `/var/data/` directory exists and is mounted
- Database file exists at `/var/data/committee_system.db`
- File modification time is from before the latest deployment
- Data you created before deployment is still accessible
- Disk usage in Render dashboard shows data (not 0 bytes)
- The `.persistence_test` marker file shows multiple deployments

### ❌ Persistence is NOT Working If:

- Database is in the root directory (not `/var/data/`)
- Data disappears after each deployment
- Database file is recreated on each deployment
- Disk is not mounted or shows as 0 bytes used

---

## Troubleshooting

### If data is not persisting:

1. **Check `render.yaml`**:
   ```yaml
   disk:
     name: sqlite-data
     mountPath: /var/data
     sizeGB: 1
   ```

2. **Check environment variable**:
   ```yaml
   envVars:
     - key: DATABASE_PATH
       value: /var/data/committee_system.db
   ```

3. **Verify disk is attached** in Render Dashboard

4. **Check logs** for any errors during startup

5. **Ensure directory is created** - Your `database.py` already handles this:
   ```python
   db_dir = os.path.dirname(self.db_path)
   if db_dir and not os.path.exists(db_dir):
       os.makedirs(db_dir, exist_ok=True)
   ```

---

## Quick Test Command

Run this one-liner in Render Shell to test everything:

```bash
python verify_persistence.py && echo "✅ Verification complete - check output above"
```

---

## Important Notes

⚠️ **Warning**: Data in `/var/data/` persists across deployments BUT:
- Manual deletion of the disk will delete all data
- Changing the disk name will create a new empty disk
- Deleting the service entirely will delete the disk

💡 **Recommendation**: Set up regular database backups!

---

## Setting Up Backups (Optional)

Add a backup endpoint to your application:

```python
# Add this to app.py
@app.route('/admin/backup-db', methods=['POST'])
@admin_required
def backup_database():
    """Create a database backup"""
    import shutil
    from datetime import datetime
    
    db_path = db.db_path
    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = os.path.join('/var/data/backups', backup_name)
    
    os.makedirs('/var/data/backups', exist_ok=True)
    shutil.copy2(db_path, backup_path)
    
    return jsonify({'success': True, 'backup': backup_name})
```

Or use a scheduled cron job (requires paid Render plan).

---

## Contact

If you continue to have issues with data persistence, check:
1. Render Status Page: https://status.render.com
2. Render Documentation: https://render.com/docs/disks
3. Your service logs in the Render Dashboard

