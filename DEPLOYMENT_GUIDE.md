# Deployment Guide - Separating Local and Production Databases

## Problem
Previously, the local SQLite database file was being uploaded with each deployment, overwriting the production database on Render.

## Solution
We've implemented environment-based database configuration with persistent storage for production.

### Local Development Setup

1. **Local Database**: Your local database is stored in `committee_system.db` in the project root
2. **Environment Variables**: Configuration is stored in `.env` file (already created)
3. **Git Ignore**: The local database file is now ignored by git and won't be committed

### Production (Render) Setup

1. **Persistent Disk**: Render now uses a persistent disk mounted at `/var/data`
   - The production database is stored at `/var/data/committee_system.db`
   - This disk persists across deployments
   - Size: 1GB (can be increased if needed)

2. **Environment Variable**: `DATABASE_PATH` is set to `/var/data/committee_system.db` in production

### How It Works

```python
# database.py now checks for DATABASE_PATH environment variable
db_path = os.environ.get('DATABASE_PATH', 'committee_system.db')
```

- **Local**: Uses `committee_system.db` in project directory
- **Render**: Uses `/var/data/committee_system.db` on persistent disk

### Deploying to Render

1. **First Deployment with Persistent Disk**:
   ```bash
   git add .
   git commit -m "Add persistent disk for production database"
   git push origin main
   ```
   
   **Important**: After the first deployment with the new `render.yaml`:
   - Go to your Render dashboard
   - Navigate to your service
   - You should see the persistent disk attached
   - The database will be initialized on the persistent disk

2. **Subsequent Deployments**:
   - Your production database will now persist across deployments
   - Only your code changes will be deployed
   - The database on `/var/data/` remains untouched

### Database Backup Recommendations

#### On Render (Production)
You can create backups using Render's shell:

1. Go to your Render dashboard
2. Open the Shell for your service
3. Run:
   ```bash
   cp /var/data/committee_system.db /var/data/committee_system_backup_$(date +%Y%m%d).db
   ```

#### Download Production Database (for inspection)
To download your production database for local inspection:

1. In Render Shell:
   ```bash
   # Create a backup in the web-accessible static folder temporarily
   cp /var/data/committee_system.db static/db_backup.db
   ```

2. Download via your web URL:
   ```
   https://your-app-name.onrender.com/static/db_backup.db
   ```

3. Delete the backup from static folder:
   ```bash
   rm static/db_backup.db
   ```

### Verifying the Setup

After deployment, verify in Render Shell:
```bash
# Check if persistent disk is mounted
ls -la /var/data/

# Check database location
echo $DATABASE_PATH

# Verify database exists
ls -lh /var/data/committee_system.db
```

### Migrating Existing Production Data (If Needed)

If you already have production data that needs to be preserved:

1. **Before deploying the changes**, download your current production database:
   - Use Render Shell to copy it to a downloadable location
   - Download the file

2. **After deploying the new configuration**:
   - The new persistent disk will be empty
   - Upload your backup database file using Render Shell:
   ```bash
   # You can upload via scp or use Render's file upload feature
   mv uploaded_database.db /var/data/committee_system.db
   ```

### Environment Variables Reference

| Variable | Local Value | Production Value |
|----------|-------------|------------------|
| `DATABASE_PATH` | `committee_system.db` | `/var/data/committee_system.db` |
| `FLASK_ENV` | `development` | `production` |
| `PORT` | `5001` | (set by Render) |

### Troubleshooting

**Database not persisting after deployment:**
- Check Render dashboard to ensure persistent disk is attached
- Verify `DATABASE_PATH` environment variable is set correctly
- Check Render logs for database initialization errors

**Permission errors:**
- The persistent disk should be writable by the application
- Render automatically handles permissions for mounted disks

**Database size issues:**
- Monitor your database size in Render Shell: `du -sh /var/data/committee_system.db`
- Increase disk size in `render.yaml` if needed (max 10GB for free tier)

### Best Practices

1. **Never commit database files**: The `.gitignore` now prevents this
2. **Regular backups**: Set up a backup routine for production data
3. **Test locally first**: Always test changes with your local database before deploying
4. **Separate test data**: Use different data for local development and production
5. **Monitor disk usage**: Keep an eye on the persistent disk usage in Render dashboard

### Additional Notes

- **Free Tier Limitation**: Render's free tier includes 1GB persistent disk
- **Database Migrations**: The `migrate_db.py` script will run during build and update the schema on the persistent disk
- **Local Database**: Your local `committee_system.db` will remain separate and is now gitignored

