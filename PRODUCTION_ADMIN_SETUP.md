# Production Admin Users Setup

## להגדרת משתמשי Admin בסביבת Production (Render)

### 👥 משתמשי Admin:
- **tal.s@innovationisrael.org.il**
- **shiran.bs@innovationisrael.org.il**

---

## 🚀 הרצה ב-Render

### אופציה 1: דרך Render Shell (מומלץ)

1. **היכנס ל-Render Dashboard:**
   ```
   https://dashboard.render.com
   ```

2. **בחר את השירות (Service):**
   - לחץ על `izun` (או שם השירות שלך)

3. **פתח Shell:**
   - לחץ על Tab **Shell** בתפריט העליון
   - זה יפתח terminal ישירות על השרת

4. **הרץ את הסקריפט:**
   ```bash
   python set_production_admins.py
   ```

5. **בדוק את הפלט:**
   ```
   ✅ Found tal.s: tal.s (tal.s@innovationisrael.org.il) - Role: admin
   ✅ Found shiran.bs: shiran.bs (shiran.bs@innovationisrael.org.il) - Role: admin
   🔧 Updating users to admin role...
   ✅ Updated 2 user(s) to admin role
   ```

---

### אופציה 2: דרך Git Deploy

1. **Commit הקבצים:**
   ```bash
   git add set_production_admins.py PRODUCTION_ADMIN_SETUP.md
   git commit -m "Add production admin setup script"
   git push origin main
   ```

2. **Render יעשה Deploy אוטומטי**

3. **פתח Shell ב-Render והרץ:**
   ```bash
   python set_production_admins.py
   ```

---

### אופציה 3: דרך Render Dashboard Manual Command

1. **Render Dashboard → Service → Shell**

2. **הרץ פקודה ישירה:**
   ```bash
   python -c "
import sqlite3
conn = sqlite3.connect('committee_system.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE users SET role='admin', auth_source='ad', is_active=1 WHERE username IN ('tal.s', 'shiran.bs') OR email IN ('tal.s@innovationisrael.org.il', 'shiran.bs@innovationisrael.org.il')\")
conn.commit()
print(f'Updated {cursor.rowcount} users to admin')
conn.close()
"
   ```

---

## ✅ אימות

### בדוק שהעדכון עבר:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('committee_system.db')
cursor = conn.cursor()
cursor.execute('SELECT username, email, role FROM users WHERE role=\"admin\"')
for user in cursor.fetchall():
    print(f'{user[0]} - {user[1]} - {user[2]}')
conn.close()
"
```

**פלט מצופה:**
```
tal.s - tal.s@innovationisrael.org.il - admin
shiran.bs - shiran.bs@innovationisrael.org.il - admin
```

---

## 🔐 הרשאות Admin

לאחר ההתחברות, המשתמשים יוכלו:

✅ **ניהול משתמשים** (`/admin/users`)  
✅ **מטריצת הרשאות** (`/permissions_matrix`)  
✅ **יומן ביקורת** (`/admin/audit_logs`)  
✅ **ניהול חטיבות** (`/hativot`)  
✅ **ניהול מסלולים** (`/maslulim`)  
✅ **סוגי ועדות** (`/committee_types`)  
✅ **כל פונקציות המערכת**

---

## 📝 הערות חשובות:

1. **התחברות ראשונה:**
   - אם המשתמשים לא קיימים, הם ייווצרו אוטומטית בהתחברות הראשונה דרך SSO
   - לאחר מכן, הרץ את הסקריפט לעדכן אותם ל-admin

2. **Session קיים:**
   - אם המשתמשים כבר מחוברים, הם צריכים להתנתק ולהתחבר מחדש
   - זה יטען את ה-role החדש (admin) ל-session

3. **Database Persistence:**
   - ודא ש-Render משתמש ב-Persistent Disk
   - אחרת השינויים ימחקו בכל deployment

---

## 🔧 Troubleshooting

### בעיה: "Users not found"
**פתרון:** המשתמשים טרם התחברו. תן להם להתחבר פעם אחת דרך SSO ואז הרץ את הסקריפט.

### בעיה: "Database is locked"
**פתרון:** 
```bash
# Stop the web service temporarily
# Run the script
# Start the web service
```

### בעיה: "Changes not persisting"
**פתרון:** בדוק ש-Render יש Persistent Disk מוגדר:
- Dashboard → Service → Settings → Disk
- ודא שיש Disk מחובר ל-`/opt/render/project/src`

---

## 📞 Support

אם יש בעיות, בדוק:
1. Logs ב-Render Dashboard
2. Shell output
3. Database file permissions

---

**Created:** 2025-10-26  
**For:** Production Environment (Render)  
**Users:** tal.s, shiran.bs
