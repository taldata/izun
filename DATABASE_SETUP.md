# Quick Database Setup Guide

## What Changed?

Your app now uses **environment variables** to separate local and production databases:

### Local Development
- Database file: `committee_system.db` (in your project folder)
- This file is now **gitignored** - it won't be committed
- Uses local file system

### Production (Render)
- Database file: `/var/data/committee_system.db` (on persistent disk)
- Persists across deployments
- Won't be overwritten when you deploy new code

## Deploy to Render

1. **Commit and push your changes:**
   ```bash
   git add .
   git commit -m "Separate local and production databases with persistent disk"
   git push origin main
   ```

2. **Render will automatically:**
   - Create a 1GB persistent disk
   - Mount it at `/var/data`
   - Store your production database there
   - Your production data will now persist across all future deployments!

## Verify It's Working

After deployment, check in your Render Dashboard → Shell:
```bash
# Check the database location
echo $DATABASE_PATH
# Should show: /var/data/committee_system.db

# Verify it exists
ls -lh /var/data/committee_system.db
```

## Important Notes

✅ **Your local database is safe** - it's in your project folder  
✅ **Production database persists** - stored on Render's persistent disk  
✅ **No more overwrites** - deployments only update code, not data  
✅ **Database files ignored** - won't be committed to git  

## Backup Your Production Database

### Option 1: Using Render Shell
```bash
# In Render Shell
cp /var/data/committee_system.db /var/data/backup_$(date +%Y%m%d).db
```

### Option 2: Download for Local Inspection
```bash
# In Render Shell - copy to static folder temporarily
cp /var/data/committee_system.db static/db_download.db

# Download via browser:
# https://your-app.onrender.com/static/db_download.db

# Then delete the copy
rm static/db_download.db
```

## If You Have Existing Production Data

If you deployed before and have production data you want to keep:

1. **Before deploying these changes**, download your current production database
2. **After deploying**, upload it to the persistent disk via Render Shell
3. See full instructions in `DEPLOYMENT_GUIDE.md`

---

For detailed information, see `DEPLOYMENT_GUIDE.md`

