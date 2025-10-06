# 🚀 Quick Start: Deploy with Persistent Database

## The Problem (Before)
```
Your App Deployment
├── app.py
├── database.py
└── committee_system.db  ← Gets OVERWRITTEN each deploy! 😱
```

## The Solution (After)
```
Local Development               Production (Render)
├── app.py                     ├── app.py
├── database.py                ├── database.py
└── committee_system.db        └── /var/data/committee_system.db
    (Local, gitignored)            (Persistent disk, safe!) ✅
```

## Deploy in 3 Steps

### 1️⃣ Commit Changes
```bash
git add .
git commit -m "Separate local and production databases"
```

### 2️⃣ Push to Deploy
```bash
git push origin main
```

### 3️⃣ Verify (After Deployment)
Open Render Shell:
```bash
ls -lh /var/data/committee_system.db
```

## What Happens Now?

### ✅ First Deployment
- Render creates persistent disk at `/var/data`
- Database initialized on persistent disk
- Application connects to persistent database

### ✅ Future Deployments
- Only code is updated
- Database stays on persistent disk
- **No more data loss!** 🎉

## Environment Variables

| Location | DATABASE_PATH | Where It Is |
|----------|--------------|-------------|
| **Local** | `committee_system.db` | Your project folder |
| **Render** | `/var/data/committee_system.db` | Persistent disk |

## Files Changed

- ✅ `.gitignore` - Database files won't be committed
- ✅ `database.py` - Uses environment variable
- ✅ `render.yaml` - Persistent disk configured
- ✅ `migrate_db.py` - Migration script added

## Verification Commands

### Before Deploying (Local)
```bash
# Test database still works locally
python migrate_db.py
# Should see: ✓ Database initialized successfully at: committee_system.db
```

### After Deploying (Render Shell)
```bash
# Check environment
echo $DATABASE_PATH

# Check persistent disk
df -h /var/data

# Check database file
ls -lh /var/data/committee_system.db

# Test database
sqlite3 /var/data/committee_system.db "SELECT COUNT(*) FROM users;"
```

## Quick Backup

```bash
# In Render Shell
cp /var/data/committee_system.db /var/data/backup_$(date +%Y%m%d).db
```

## Need More Help?

- 📋 **Checklist**: See `DEPLOYMENT_CHECKLIST.md`
- 🎯 **Quick Reference**: See `DATABASE_SETUP.md`  
- 📚 **Full Guide**: See `DEPLOYMENT_GUIDE.md`
- 📝 **What Changed**: See `CHANGES_SUMMARY.md`

---

**Ready?** Just commit and push! Your data is now safe! 🛡️

