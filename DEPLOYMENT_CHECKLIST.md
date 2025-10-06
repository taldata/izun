# 🚀 Deployment Checklist

## Pre-Deployment Verification

- [x] ✅ Local database works: `committee_system.db`
- [x] ✅ Database path uses environment variable
- [x] ✅ Migration script tested and working
- [x] ✅ Database files added to `.gitignore`
- [x] ✅ Render configuration includes persistent disk
- [x] ✅ Documentation created

## Deployment Steps

### Step 1: Review Changes
```bash
git status
```

You should see:
- Modified: `.gitignore`, `database.py`, `render.yaml`, `README.md`
- New: `migrate_db.py`, `DATABASE_SETUP.md`, `DEPLOYMENT_GUIDE.md`, and other docs

### Step 2: Commit Changes
```bash
git add .
git commit -m "Separate local and production databases with persistent disk

- Add environment-based database configuration
- Configure Render persistent disk for production database
- Update .gitignore to exclude database files
- Add database migration script
- Add comprehensive documentation"
```

### Step 3: Push to Deploy
```bash
git push origin main
```

### Step 4: Monitor Deployment

1. **Watch Render Dashboard**
   - Build should complete successfully
   - Look for: "✓ Database initialized successfully"
   
2. **Check for Persistent Disk**
   - Go to your service in Render
   - Look for "Disks" section
   - Should see: `committee-data` mounted at `/var/data`

### Step 5: Verify Deployment

Open Render Shell and run:

```bash
# 1. Check environment variable
echo $DATABASE_PATH
# Expected: /var/data/committee_system.db

# 2. Verify persistent disk is mounted
df -h /var/data
# Should show mounted disk

# 3. Check database file exists
ls -lh /var/data/committee_system.db
# Should show the database file

# 4. Verify database is functional
sqlite3 /var/data/committee_system.db "SELECT COUNT(*) FROM users;"
# Should return number of users
```

### Step 6: Test Application

1. **Open your application URL**
2. **Try logging in** (admin/admin123 or your credentials)
3. **Check that data is present** (if you had production data)
4. **Create a test entry** (committee, event, etc.)
5. **Verify it persists** after refreshing

## Post-Deployment

### Create a Backup (Recommended)

```bash
# In Render Shell
cp /var/data/committee_system.db /var/data/committee_system_backup_$(date +%Y%m%d).db
```

### Test Redeployment

1. Make a small code change (e.g., add a comment)
2. Commit and push
3. Verify data still exists after redeployment

```bash
# Example test
echo "# Test comment" >> README.md
git add README.md
git commit -m "Test: Verify database persistence"
git push origin main
```

After redeployment, verify your data is still there!

## Troubleshooting

### ❌ Build Fails

**Error**: `migrate_db.py not found`
```bash
# Make sure file is committed
git add migrate_db.py
git commit --amend --no-edit
git push origin main --force
```

**Error**: `Permission denied for /var/data`
- Render should handle permissions automatically
- Check Render logs for detailed error
- Verify persistent disk is properly configured in `render.yaml`

### ❌ Database Not Found

**Symptom**: Application can't find database after deployment

```bash
# In Render Shell
# 1. Check environment variable
printenv | grep DATABASE

# 2. Create database manually if needed
mkdir -p /var/data
touch /var/data/committee_system.db
python migrate_db.py
```

### ❌ Data Lost After Deployment

This should NOT happen with the new setup, but if it does:

1. **Stop** - Don't deploy again
2. **Check** if persistent disk is attached
3. **Verify** `render.yaml` has the disk configuration
4. **Restore** from backup if you have one

### ❌ Need to Migrate Existing Data

If you had production data before this change:

1. **Before this deployment**, download your old database
2. **After deployment**, upload it to `/var/data/` via Render Shell
3. See `DEPLOYMENT_GUIDE.md` for detailed instructions

## Success Indicators

✅ **Deployment successful** - No build errors  
✅ **Persistent disk attached** - Shows in Render dashboard  
✅ **Database exists** - At `/var/data/committee_system.db`  
✅ **Application works** - Can log in and see data  
✅ **Data persists** - Survives redeployments  

## What's Different Now?

### Before
- ❌ Database in app directory
- ❌ Overwritten on each deployment
- ❌ Data loss risk
- ❌ Local and production mixed

### After
- ✅ Database on persistent disk
- ✅ Survives deployments
- ✅ Data is safe
- ✅ Local and production separated

## Next Steps After Successful Deployment

1. **Delete local backup** if you created one for migration
2. **Update your team** about the new setup
3. **Schedule regular backups** of the production database
4. **Monitor disk usage** in Render dashboard
5. **Test disaster recovery** process once

## Support

- Quick reference: `DATABASE_SETUP.md`
- Detailed guide: `DEPLOYMENT_GUIDE.md`
- Changes summary: `CHANGES_SUMMARY.md`
- Application docs: `README.md`

---

**Ready to deploy?** Just follow the steps above! 🚀

Your local development database is safe at: `committee_system.db`  
Your production database will be at: `/var/data/committee_system.db`

