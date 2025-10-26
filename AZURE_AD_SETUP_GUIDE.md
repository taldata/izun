# מדריך הגדרת Azure AD למערכת ניהול הועדות

## תוכן עניינים
1. [סקירה כללית](#סקירה-כללית)
2. [הגדרת Azure AD OAuth 2.0](#הגדרת-azure-ad-oauth-20)
3. [התקנת חבילות נדרשות](#התקנת-חבילות-נדרשות)
4. [הגדרת המערכת](#הגדרת-המערכת)
5. [בדיקה ואימות](#בדיקה-ואימות)
6. [פתרון בעיות](#פתרון-בעיות)

---

## סקירה כללית

המערכת תומכת באימות משתמשים דרך **Azure AD OAuth 2.0**:

### **Azure AD OAuth 2.0**
- ✅ אימות מודרני ומאובטח
- ✅ תומך ב-Multi-Factor Authentication (MFA)
- ✅ אינטגרציה מלאה עם Microsoft 365 / Azure AD
- ✅ לא דורש חיבור ישיר ל-AD מקומי
- ✅ מתאים לארגונים עם Azure Active Directory
- ✅ ניהול זהויות מרכזי דרך Microsoft

### דרישות מוקדמות
- ⚠️ גישה ל-Azure Portal עם הרשאות יצירת App Registration
- ⚠️ חשבון Azure AD / Microsoft 365 פעיל
- ⚠️ משתמשים חייבים להיות חלק מה-Azure AD tenant

---

## הגדרת Azure AD OAuth 2.0

### שלב 1: יצירת App Registration ב-Azure Portal

1. **התחבר ל-Azure Portal**
   - גש ל-[https://portal.azure.com](https://portal.azure.com)
   - התחבר עם חשבון בעל הרשאות מנהל

2. **נווט ל-App Registrations**
   - חפש "App registrations" בסרגל החיפוש העליון
   - או גש ל: [Azure AD > App registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)

3. **צור רישום אפליקציה חדש**
   - לחץ על **"New registration"**
   - הזן שם לאפליקציה: `Committee Management System`
   - **Supported account types:** בחר באפשרות המתאימה לארגון שלך:
     - `Accounts in this organizational directory only` - משתמשים מהארגון בלבד (מומלץ)
   - **Redirect URI:** השאר ריק בינתיים (נוסיף מאוחר יותר)
   - לחץ **"Register"**

### שלב 2: קבלת פרטי האפליקציה

1. **העתק את Application (client) ID**
   - בעמוד הראשי של האפליקציה, העתק את ה-**Application (client) ID**
   - שמור אותו - תצטרך אותו בהמשך

2. **העתק את Directory (tenant) ID**
   - באותו עמוד, העתק גם את ה-**Directory (tenant) ID**
   - שמור אותו - תצטרך אותו בהמשך

### שלב 3: יצירת Client Secret

1. **נווט ל-Certificates & secrets**
   - בתפריט הצד, לחץ על **"Certificates & secrets"**

2. **צור Client Secret חדש**
   - לחץ על **"New client secret"**
   - הזן תיאור: `Committee System Secret`
   - בחר תוקף: `24 months` (או כפי שמתאים למדיניות הארגון)
   - לחץ **"Add"**

3. **העתק את הSecret Value**
   - ⚠️ **חשוב מאוד:** העתק את ה-**Value** (ולא את Secret ID!)
   - זה יוצג רק פעם אחת - שמור אותו במקום בטוח
   - לא תוכל לראות אותו שוב אחרי שתעזוב את הדף

### שלב 4: הגדרת Redirect URI

1. **נווט ל-Authentication**
   - בתפריט הצד, לחץ על **"Authentication"**

2. **הוסף Platform**
   - לחץ על **"Add a platform"**
   - בחר **"Web"**

3. **הגדר Redirect URI**
   - הזן את הכתובת: `http://127.0.0.1:5001/auth/callback`
   - או
   - הזן את הכתובת: `https://yourdomain.com/auth/callback`
   - ✅ סמן **ID tokens (used for implicit and hybrid flows)**
   - **שמור**

4. **שמור את ההגדרות**
   - לחץ **"Configure"** ואז **"Save"**

### שלב 5: הגדרת API Permissions

1. **נווט ל-API permissions**
   - בתפריט הצד, לחץ על **"API permissions"**

2. **ודא שקיימת הרשאת User.Read**
   - אמורה להיות כבר הרשאה ל-**Microsoft Graph > User.Read**
   - זה מספיק לצורכי אימות בסיסי

3. **(אופציונלי) הוסף הרשאות נוספות**
   - אם רוצה לקרוא גם קבוצות, הוסף: `GroupMember.Read.All`
   - לחץ **"Add a permission"** > **Microsoft Graph** > **Delegated permissions**

4. **Grant Admin Consent** (אם נדרש)
   - אם ההרשאות דורשות אישור מנהל, לחץ על **"Grant admin consent for [Organization]"**

### שלב 6: הגדרת המערכת

1. **התחבר כמנהל למערכת**
   - גש למערכת ניהול הועדות
   - התחבר עם משתמש מקומי בעל הרשאות Admin

2. **פתח הגדרות Active Directory**
   - תפריט → הגדרות → הגדרות Active Directory
   - או `/admin/ad_settings`

3. **הפעל אימות Azure AD**
   - סמן ✅ **"הפעל אימות Active Directory"**
   - בחר שיטת אימות: **Azure AD OAuth 2.0**

4. **הזן את פרטי ה-App Registration**
   - **Tenant ID:** הדבק את ה-Directory (tenant) ID
   - **Application (Client) ID:** הדבק את ה-Application (client) ID
   - **Client Secret:** הדבק את ה-Secret Value שיצרת
   - **Redirect URI:** אמור להתמלא אוטומטית - ודא שהוא תואם למה שהגדרת ב-Azure

5. **הגדר אופציות נוספות**
   - ✅ **צור משתמשים אוטומטית בהתחברות ראשונה** - מומלץ
   - ✅ **סנכרן פרטי משתמש מ-AD בכל התחברות** - מומלץ
   - בחר **חטיבת ברירת מחדל** למשתמשים חדשים (אופציונלי)

6. **שמור והבדוק חיבור**
   - לחץ **"שמור הגדרות"**
   - לחץ **"בדוק הגדרות Azure AD"** לאימות

---

## התקנת חבילות נדרשות

### עדכון חבילות Python

```bash
# עבור ל-directory של המערכת
cd /path/to/izun

# התקן/עדכן חבילות נדרשות
pip install -r requirements.txt

# או התקנה ידנית:
pip install msal>=1.25.0
pip install requests>=2.31.0
pip install PyJWT>=2.8.0
pip install cryptography>=41.0.0
pip install bcrypt>=4.0.0
```

### אימות התקנה

```python
python3 -c "import msal; print('✅ All packages installed')"
```

---

## הגדרת המערכת

### מסד הנתונים

המערכת משתמשת בטבלת `system_settings` לשמירת הגדרות AD.
ההגדרות הבאות נשמרות:

**הגדרות כלליות:**
- `ad_enabled` - האם Azure AD מופעל (0/1)
- `ad_auth_method` - תמיד "oauth"
- `ad_auto_create_users` - יצירת משתמשים אוטומטית (0/1)
- `ad_sync_on_login` - סנכרון פרטים בכל התחברות (0/1)
- `ad_default_hativa_id` - חטיבת ברירת מחדל

**הגדרות Azure OAuth:**
- `azure_tenant_id` - מזהה ה-Tenant
- `azure_client_id` - מזהה האפליקציה
- `azure_client_secret` - סוד הלקוח
- `azure_redirect_uri` - כתובת החזרה

**מיפוי תפקידים:**
- `ad_admin_group` - קבוצת מנהלי מערכת
- `ad_manager_group` - קבוצת מנהלי חטיבות

---

## בדיקה ואימות

### בדיקת Azure AD OAuth

1. **בדיקה במסך ההגדרות**
   - לחץ על "בדוק הגדרות Azure AD"
   - אמור לקבל הודעה: "✅ הגדרות Azure AD תקינות"

2. **בדיקת התחברות מלאה**
   - התנתק מהמערכת
   - במסך ההתחברות, אמור לראות כפתור **"התחבר עם Azure AD"**
   - לחץ עליו - תועבר לדף אימות של Microsoft
   - התחבר עם חשבון ה-Azure AD שלך
   - אמור להיות מועבר חזרה למערכת מחוברים

### בדיקת יצירת משתמשים אוטומטית

1. התחבר עם משתמש Azure AD חדש (שלא קיים במערכת)
2. אם "צור משתמשים אוטומטית" מופעל:
   - המשתמש ייווצר אוטומטית
   - תקבל הודעה: "ברוך הבא, [שם מלא]"
3. אם לא מופעל:
   - תקבל שגיאה: "משתמש לא מורשה להתחבר למערכת"

### בדיקת מיפוי תפקידים

1. התחבר עם משתמש שחבר בקבוצת Admin
2. בדוק שהוא קיבל הרשאות admin במערכת
3. אמור לראות תפריט "ניהול משתמשים" ואפשרויות ניהול נוספות

---

## פתרון בעיות

### Azure AD OAuth

#### שגיאה: "אין Client Secret"
**פתרון:**
- ודא שהעתקת את ה-**Value** ולא את ה-Secret ID
- אם איבדת את ה-Value, צור secret חדש ב-Azure Portal

#### שגיאה: "invalid_client"
**פתרון:**
- ודא שה-Client ID וה-Client Secret נכונים
- ודא שה-Tenant ID נכון
- בדוק שה-Secret לא פג תוקפו

#### שגיאה: "redirect_uri_mismatch"
**פתרון:**
- ודא שה-Redirect URI במערכת תואם בדיוק למה שמוגדר ב-Azure Portal
- שים לב ל-https vs http
- ב-Azure Portal → Authentication, הוסף את ה-URI המדויק

#### משתמשים לא נוצרים אוטומטית
**פתרון:**
- בדוק שהאפשרות "צור משתמשים אוטומטית" מסומנת
- בדוק שהוגדרה חטיבת ברירת מחדל
- בדוק logs של המערכת לשגיאות

### כללי

#### לוגים לדיבאגינג
```bash
# צפה בלוגים
tail -f /var/log/committee_system.log

# או אם רץ עם gunicorn:
journalctl -u committee-system -f
```

---

## אבטחה ומומלצות

### Azure AD OAuth
✅ **מומלץ:**
- השתמש ב-HTTPS בלבד
- הגבל Redirect URIs רק לכתובות הנדרשות
- סובב Client Secrets באופן קבוע (כל 6-12 חודשים)
- הגדר expiration ל-Secrets
- השתמש ב-Conditional Access policies ב-Azure AD

❌ **אל תעשה:**
- אל תשתף Client Secrets בקוד או ב-version control
- אל תשתמש ב-wildcard ב-Redirect URIs
- אל תשאיר Secrets פגי תוקף
- אל תשמור את ה-Client Secret במקומות לא מאובטחים

---

## תמיכה ויצירת קשר

לשאלות או בעיות טכניות:
- פתח issue ב-GitHub repository
- צור קשר עם צוות הפיתוח

---

**גרסה:** 1.0  
**עדכון אחרון:** אוקטובר 2024  
**תאימות:** Python 3.8+, Flask 3.0+
