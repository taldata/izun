# העברת נתונים מ-Render ל-AWS

## שיטה 1: דרך Render Shell (מומלץ)

### ב-Render Shell:
```bash
cd /opt/render/project/src
python upload_db.py export
cp db_export.json static/db_export.json
```

### ב-AWS EB SSH:
```bash
eb ssh
cd /var/app/current
curl -s "https://committee-management-izun.onrender.com/static/db_export.json" -o /tmp/db_export.json
python3 upload_db.py import /tmp/db_export.json
```

## שיטה 2: העתקה ישירה (אם JSON לא עובד)

אם יש בעיה עם JSON, אפשר להעתיק את הקובץ ישירות:

### ב-Render Shell:
```bash
# Export to JSON (more reliable)
cd /opt/render/project/src  
python upload_db.py export

# Download locally using Render CLI or copy manually
```

### אז העתק את db_export.json למחשב המקומי והעלה ל-AWS:
```bash
# On local machine
scp db_export.json ec2-user@your-eb-instance:/tmp/

# Then on AWS EB
eb ssh
cd /var/app/current
python3 upload_db.py import /tmp/db_export.json
```
