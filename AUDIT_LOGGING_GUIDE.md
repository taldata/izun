# 📋 מדריך מערכת יומן הביקורת (Audit Logging System)

## סקירה כללית

המערכת כוללת עכשיו יומן ביקורת מקיף (Audit Log) שמתעד את כל הפעולות שמבוצעות במערכת על ידי המשתמשים.

## ✨ מה נוסף למערכת?

### 1. **טבלת audit_logs** במסד הנתונים
טבלה חדשה ש���תעדת:
- מי ביצע את הפעולה (משתמש)
- מה בוצע (סוג פעולה)
- מתי בוצע (זמן מדויק)
- על מה בוצע (סוג וזהות הישות)
- מאיפה בוצע (IP וכתובת)
- האם הצליח או נכשל

### 2. **שירות AuditLogger**
מחלקה חכמה שמטפלת בכל הלוגים:
```python
audit_logger.log_hativa_created(hativa_id, name)
audit_logger.log_event_updated(event_id, name)
audit_logger.log_login(username, success)
```

### 3. **ממשק ניהול מתקדם**
דף אדמין מלא עם:
- ✅ צפייה בכל הלוגים
- ✅ סינון לפי משתמש, פעולה, תאריך, סוג ישות
- ✅ סטטיסטיקות וגרפים
- ✅ ייצוא ל-CSV
- ✅ דפדוף (pagination)

## 📊 מה מתועד?

### פעולות משתמש:
- ✅ **התחברות והתנתקות** - כל נסיון login (מוצלח ונכשל)
- ✅ **ניהול חטיבות** - יצירה, עדכון, שינוי סטטוס
- ✅ **ניהול מסלולים** - יצירה, עדכון, מחיקה
- ✅ **ניהול ועדות** - יצירה, עדכון, העברה, מחיקה
- ✅ **ניהול אירועים** - יצירה, עדכון, העברה, מחיקה
- ✅ **ניהול משתמשים** - יצירה, עדכון, שינוי סיסמה, השבתה
- ✅ **שינוי הגדרות** - כל שינוי בהגדרות המערכת

### מה נשמר בכל רשומה?
```
- זמן מדויק (timestamp)
- משתמש (username + user_id)
- סוג פעולה (create/update/delete/login/logout/move/toggle)
- סוג ישות (hativa/maslul/vaada/event/user/etc)
- שם הישות
- פרטים נוספים (details)
- כתובת IP
- סטטוס (success/error)
- הודעת שגיאה (אם רלוונטי)
```

## 🖥️ איך להשתמש בממשק הניהול?

### גישה למערכת
1. התחבר כ-**admin**
2. לחץ על תפריט המשתמש (שם המשתמש למעלה מימין)
3. בחר **"יומן ביקורת"**

### צפייה בלוגים
- **הכל מוצג בטבלה** עם 50 רשומות לעמוד
- **צבעים**: ירוק=הצלחה, אדום=שגיאה
- **תגיות** (badges) לסוגי פעולות שונים
- **IP וזמן** - כל המידע הנדרש לביקורת

### סינון מתקדם
לחץ על כפתור **"סינון"** ובחר:
- **משתמש** - חפש לפי שם משתמש
- **סוג פעולה** - create/update/delete/login/logout
- **סוג ישות** - hativa/maslul/event/user וכו'
- **סטטוס** - רק הצלחות או רק שגיאות
- **תאריכים** - מתאריך עד תאריך

### ייצוא נתונים
1. (אופציונלי) הגדר סינונים
2. לחץ **"ייצוא"**
3. יורד קובץ CSV עם כל הנתונים

## 📈 סטטיסטיקות

בראש הדף תראה 4 כרטיסים:
- **סה"כ רשומות** - כמה לוגים יש במערכת
- **פעילות 24 שעות** - כמה פעולות בוצעו ביום האחרון
- **פעולות שנכשלו** - כמה שגיאות היו
- **משתמשים פעילים** - כמה משתמשים שונים פעלו

בתחתית הדף:
- **משתמשים פעילים ביותר** - מי עושה הכי הרבה פעולות
- **פעולות נפוצות** - אילו פעולות מבוצעות הכי הרבה

## 🔍 דוגמאות שימוש

### מצא מי מחק ועדה
1. סנן לפי:
   - סוג פעולה: **delete**
   - סוג ישות: **vaada**
2. תראה את כל המחיקות עם שם המשתמש והזמן

### בדוק ניסיונות התחברות נכשלים
1. סנן לפי:
   - סוג פעולה: **login_failed**
   - או סטטוס: **error**
2. תראה כל ניסיון התחברות שנכשל

### עקוב אחרי פעילות משתמש מסוים
1. הכנס שם משתמש בסינון
2. תראה את כל הפעולות שהמשתמש ביצע

### בדוק שינויים באירוע מסוים
1. סנן לפי:
   - סוג ישות: **event**
   - הכנס את שם האירוע בחיפוש
2. תראה את כל העדכונים שנעשו

## 🔐 אבטחה והרשאות

- **גישה למנהלים בלבד** - רק admin יכול לראות את יומן הביקורת
- **לא ניתן לערוך** - רק צפייה, אי אפשר למחוק או לשנות לוגים
- **כתובות IP** - נשמרות לצרכי ביקורת אבטחה
- **שגיאות** - גם פעולות שנכשלו מתועדות

## 🛠️ טכני - למפתחים

### הוספת לוג חדש בקוד

#### דרך קלה (עם פונקציות מובנות):
```python
# התחברות
audit_logger.log_login(username, success=True)

# יצירת חטיבה
audit_logger.log_hativa_created(hativa_id, name)

# עדכון מסלול
audit_logger.log_maslul_updated(maslul_id, name, changes="שינוי SLA")

# מחיקת אירוע
audit_logger.log_event_deleted(event_id, name)
```

#### דרך גנרית (כל פעולה):
```python
audit_logger.log_success(
    action='my_action',
    entity_type='my_entity',
    entity_id=123,
    entity_name='Example',
    details='Additional info'
)

# או לשגיאה
audit_logger.log_error(
    action='my_action',
    entity_type='my_entity',
    error_message='What went wrong',
    entity_id=123
)
```

### שאילתות למסד נתונים

```python
# קבל 100 לוגים אחרונים
logs = db.get_audit_logs(limit=100)

# סנן לפי משתמש
logs = db.get_audit_logs(user_id=5)

# סנן לפי תאריכים
from datetime import date
logs = db.get_audit_logs(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31)
)

# קבל סטטיסטיקות
stats = db.get_audit_statistics()
```

### מבנה הטבלה

```sql
CREATE TABLE audit_logs (
    log_id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    entity_name TEXT,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    status TEXT DEFAULT 'success',
    error_message TEXT
);
```

### אינדקסים לביצועים
```sql
-- מהיר לשאילתות לפי זמן
CREATE INDEX idx_audit_logs_timestamp ON audit_logs (timestamp DESC);

-- מהיר לשאילתות לפי משתמש
CREATE INDEX idx_audit_logs_user ON audit_logs (user_id);

-- מהיר לשאילתות לפי ישות
CREATE INDEX idx_audit_logs_entity ON audit_logs (entity_type, entity_id);
```

## 📝 סוגי פעולות (Actions)

```python
ACTION_CREATE = 'create'          # יצירת ישות חדשה
ACTION_UPDATE = 'update'          # עדכון ישות קיימת
ACTION_DELETE = 'delete'          # מחיקת ישות
ACTION_VIEW = 'view'              # צפייה בישות
ACTION_LOGIN = 'login'            # התחברות מוצלחת
ACTION_LOGOUT = 'logout'          # התנתקות
ACTION_LOGIN_FAILED = 'login_failed'  # התחברות נכשלה
ACTION_MOVE = 'move'              # העברת ישות (drag & drop)
ACTION_TOGGLE = 'toggle'          # שינוי סטטוס (הפעלה/השבתה)
ACTION_EXPORT = 'export'          # ייצוא נתונים
ACTION_AUTO_SCHEDULE = 'auto_schedule'  # תזמון אוטומטי
ACTION_APPROVE = 'approve'        # אישור
```

## 📚 סוגי ישויות (Entity Types)

```python
ENTITY_HATIVA = 'hativa'                # חטיבה
ENTITY_MASLUL = 'maslul'                # מסלול
ENTITY_COMMITTEE_TYPE = 'committee_type'  # סוג ועדה
ENTITY_VAADA = 'vaada'                  # ועדה
ENTITY_EVENT = 'event'                  # אירוע
ENTITY_EXCEPTION_DATE = 'exception_date'  # תאריך חריג
ENTITY_USER = 'user'                    # משתמש
ENTITY_SYSTEM_SETTINGS = 'system_settings'  # הגדרות מערכת
ENTITY_SESSION = 'session'              # התחברות/התנתקות
ENTITY_SCHEDULE = 'schedule'            # תזמון אוטומטי
```

## 🎯 שימושים מומלצים

### ביקורת אבטחה
- עקוב אחרי ניסיונות התחברות נכשלים
- זהה פעילות חשודה (הרבה פעולות במהירות)
- בדוק מי ניגש למידע רגיש

### פתרון בעיות (Debugging)
- מצא מתי דבר מסוים השתנה
- עקוב אחרי שרשרת פעולות
- זהה מי ביצע שינוי שגרם לבעיה

### ציות ורגולציה (Compliance)
- שמור תיעוד מלא של כל הפעולות
- הוכח מי עשה מה ומתי
- ייצא דוחות לביקורת חיצונית

### ניהול ומעקב
- ראה מי המשתמשים הכי פעילים
- זהה בעיות בזרימת עבודה
- הבן דפוסי שימוש במערכת

## 🚀 טיפים ועצות

### ביצועים
- השתמש בסינונים כדי לצמצם תוצאות
- ייצא רק מה שצריך (אל תייצא הכל)
- הלוגים מאונדקסים - חיפוש מהיר!

### ניקיון
- שקול לנקות לוגים ישנים (מעל שנה) מדי פעם
- שמור גיבוי לפני ניקיון
- ייצא לארכיב לפני מחיקה

### אבטחה
- בדוק את יומן הביקורת באופן קבוע
- שים לב לדפוסים חריגים
- הגדר התראות לפעילות חשודה (בעתיד)

## 📊 דוגמאות דוחות שימושיים

### דוח פעילות יומי
```
סנן לפי: start_date=אתמול, end_date=היום
מטרה: ראה מה קרה בימים האחרונים
```

### דוח שינויים במשתמשים
```
סנן לפי: entity_type=user
מטרה: עקוב אחרי ניהול משתמשים
```

### דוח שגיאות
```
סנן לפי: status=error
מטרה: מצא בעיות שצריך לטפל בהן
```

### דוח פעילות משתמש
```
סנן לפי: username=john_doe
מטרה: תיעוד פעילות עובד ספציפי
```

## 🔄 פיצ'רים עתידיים (מומלץ)

- ⏰ התראות אוטומטיות על פעילות חשודה
- 📧 שליחת דוחות תקופתיים במייל
- 📊 גרפים וחיזואליזציה של הנתונים
- 🔍 חיפוש מתקדם full-text
- 📱 ממשק נייד לצפייה בלוגים
- 🤖 זיהוי אנומליות אוטומטי
- 📦 ארכוב אוטומטי של לוגים ישנים

## ✅ רשימת בדיקה למנהל מערכת

- [ ] גש ליומן הביקורת ווודא שהוא עובד
- [ ] נסה סינונים שונים
- [ ] ייצא CSV ובדוק שהוא תקין
- [ ] בדוק שלוגים נוצרים כשאתה מבצע פעולות
- [ ] הגדר מדיניות ניקיון לוגים
- [ ] הדרך את הצוות איך להשתמש
- [ ] שמור גיבוי של הלוגים באופן קבוע

---

## 📞 תמיכה

יש שאלות? בעיות? רעיונות לשיפור?
- בדוק את הקוד ב-`services/audit_logger.py`
- בדוק את הטבלה ב-`database.py`
- בדוק את הממשק ב-`templates/admin/audit_logs.html`

**המערכת מוכנה לשימוש! 🎉**

