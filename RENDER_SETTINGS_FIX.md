# 🔧 הגדרות נכונות ל-Render Dashboard

## ⚠️ הבעיה שהייתה

`/var/data` הוא **read-only במהלך Build Phase**!
הדיסק הפרמננטי זמין רק ב-**Runtime**.

לכן צריך להריץ את המיגרציה **אחרי** שהשירות עולה, לא לפני.

---

## ✅ הגדרות נכונות ב-Render Dashboard

עכשיו לך ל: **https://dashboard.render.com**

### 1. Settings → Build Command

הגדר:
```bash
pip install -r requirements.txt
```

**זהו!** אל תוסיף migrate_db.py כאן.

---

### 2. Settings → Start Command

הגדר:
```bash
python migrate_db.py && python verify_persistence.py && gunicorn --bind 0.0.0.0:$PORT app:app
```

זה יריץ:
1. ✅ `migrate_db.py` - מיגרציה של DB (כשהדיסק זמין)
2. ✅ `verify_persistence.py` - בדיקה שהכל עובד
3. ✅ `gunicorn` - הרצת השרת

---

### 3. Environment Variables

וודא שיש:
```
DATABASE_PATH = /var/data/committee_system.db
```

---

### 4. Disks

וודא שיש Disk:
- **Name**: `sqlite-data`
- **Mount Path**: `/var/data`
- **Size**: `1 GB`

---

## 🚀 Redeploy

1. **שמור את השינויים** (Save Changes)
2. לחץ **Manual Deploy** → **Deploy latest commit**
3. **הלוגים צריכים להראות:**

```
==> Running build command 'pip install -r requirements.txt'...
[התקנת חבילות...]
==> Build successful 🎉
==> Deploying...
==> Running 'python migrate_db.py && python verify_persistence.py && gunicorn...'

============================================================
DATABASE PERSISTENCE VERIFICATION
============================================================

1. Database Path: /var/data/committee_system.db
   ✅ Database is in persistent storage directory (/var/data)
   ✅ Database file exists
   
[... עוד output ...]

==> Your service is live 🎉
```

---

## 📋 למה זה עובד עכשיו?

| שלב | זמן | גישה ל-/var/data | פעולה |
|-----|-----|-----------------|-------|
| **Build** | לפני העלאה | ❌ Read-only | התקנת חבילות בלבד |
| **Start** | אחרי העלאה | ✅ Read-write | מיגרציה + אימות + הרצה |

---

## ✅ אימות שזה עובד

אחרי deployment, תראה בלוגים:
```
✅ Database is in persistent storage directory (/var/data)
✅ Database file exists
✅ Directory is writable
📝 Persistence marker has X deployment(s) recorded
```

המספר X יגדל עם כל deployment!

---

## 💡 Tip

אם תרצה, אתה יכול לפשט את Start Command ל:
```bash
gunicorn --bind 0.0.0.0:$PORT app:app
```

והמיגרציה תרוץ אוטומטית מתוך `app.py` (ה-DatabaseManager כבר קורא ל-`init_database()`).

אבל עם הגרסה הנוכחית יש לך:
- ✅ בקרה מלאה
- ✅ לוגים ברורים
- ✅ אימות אוטומטי

