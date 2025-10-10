# Quick Persistence Check ✅

## 🎯 3-Minute Test

### Test 1: Check Deployment Logs
1. Push your code to deploy
2. Go to Render Dashboard → Logs
3. Look for this output from `verify_persistence.py`:
   ```
   ✅ Database is in persistent storage directory (/var/data)
   ✅ Database file exists
   ✅ Directory is writable
   ✅ Database is readable and contains data
   ```

### Test 2: Simple Data Test
1. **Before deployment**: Create a test user or hativa
2. **Deploy**: Push any small change
3. **After deployment**: Check if your test data is still there
4. ✅ Data still there = **Working!**

### Test 3: Check Render Dashboard
1. Go to: https://dashboard.render.com
2. Your Service → **Disks** tab
3. Should see:
   - ✅ Name: `sqlite-data`
   - ✅ Path: `/var/data`
   - ✅ Size: `1 GB`
   - ✅ Used: > 0 MB

---

## 🔧 If Something Seems Wrong

### Run in Render Shell:
```bash
python verify_persistence.py
```

### Quick checks:
```bash
# Check database location
echo $DATABASE_PATH
# Should show: /var/data/committee_system.db

# Check if disk is mounted
ls -lh /var/data/

# Check database size
du -h /var/data/committee_system.db
```

---

## 📊 What to Look For

### ✅ Good Signs:
- Database path is `/var/data/committee_system.db`
- File size grows over time (not reset to 0)
- Deployment logs show "DATA IS PERSISTING!"
- Data survives redeploys

### ⚠️ Bad Signs:
- Database in `/app/` or root directory
- File resets to same size each deploy
- Data disappears after redeploy
- Disk shows 0 bytes used

---

## 💡 Pro Tip

After your next deployment, check the logs for:
```
📝 Persistence marker has X deployment(s) recorded
```

If X increases with each deployment → **Everything is working perfectly!**

---

## 📞 Need Help?

1. Check full guide: [PERSISTENCE_TESTING_GUIDE.md](PERSISTENCE_TESTING_GUIDE.md)
2. Review Render disk docs: https://render.com/docs/disks
3. Check your render.yaml configuration

