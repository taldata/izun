# סיכום אינטגרציה: Azure AD / Active Directory

## 📋 סקירה

נוספה תמיכה מלאה באימות משתמשים דרך **Azure AD OAuth 2.0** (בנוסף ל-LDAP הקיים).

המערכת כעת תומכת בשתי שיטות אימות:
1. **Azure AD OAuth 2.0** - אימות מודרני עם Microsoft Identity Platform (מומלץ)
2. **LDAP** - חיבור ישיר ל-Active Directory מקומי

---

## 🎯 קבצים שנוספו/עודכנו

### קבצים חדשים
1. **`AZURE_AD_SETUP_GUIDE.md`** - מדריך הגדרה מפורט (עברית)
2. **`AZURE_AD_INTEGRATION_SUMMARY.md`** - סיכום האינטגרציה (קובץ זה)

### קבצים שעודכנו

#### 1. **requirements.txt**
נוספו חבילות Python נדרשות:
```python
msal>=1.25.0          # Microsoft Authentication Library
requests>=2.31.0      # HTTP requests
PyJWT>=2.8.0          # JWT token handling
cryptography>=41.0.0  # Cryptographic operations
```

#### 2. **services/ad_service.py**
**תכונות חדשות:**
- תמיכה ב-OAuth 2.0 לצד LDAP
- `get_azure_auth_url()` - יצירת URL אימות Azure
- `authenticate_with_code()` - אימות עם authorization code
- `_get_user_from_graph()` - שליפת פרטי משתמש מ-Microsoft Graph API
- `test_azure_connection()` - בדיקת הגדרות Azure AD

**משתנים חדשים:**
- `auth_method` - ldap/oauth
- `azure_tenant_id`
- `azure_client_id`
- `azure_client_secret`
- `azure_redirect_uri`
- `azure_authority`

#### 3. **app.py**
**Routes חדשים:**

```python
@app.route('/login/azure')
def login_azure()
    # הפניה ל-Azure AD לאימות

@app.route('/login/azure/callback')
def login_azure_callback()
    # טיפול בתשובה מ-Azure AD

@app.route('/admin/ad_settings/test_azure', methods=['POST'])
@admin_required
def test_azure_connection()
    # בדיקת הגדרות Azure AD
```

**עדכוני Routes קיימים:**
- `login()` - נוסף `azure_oauth_enabled` לטמפלייט
- `ad_settings()` - נוספו הגדרות Azure OAuth ל-`ad_config`
- `update_ad_settings()` - שמירת הגדרות Azure OAuth

#### 4. **templates/login.html**
**תוספות:**
- כפתור "התחבר עם Azure AD" (מוצג כאשר OAuth מופעל)
- מפריד "או" בין Azure AD לאימות רגיל
- תמיכה דינמית בהצגת הכפתור

#### 5. **templates/admin/ad_settings.html**
**תוספות עיקריות:**

1. **בחירת שיטת אימות:**
   - Radio buttons: LDAP vs Azure AD OAuth
   - Toggle אוטומטי בין הסקציות

2. **סקציית Azure AD OAuth (חדשה):**
   - Tenant ID
   - Application (Client) ID
   - Client Secret
   - Redirect URI (אוטומטי)
   - קישור ישיר ל-Azure Portal
   - הנחיות הגדרה מפורטות

3. **JavaScript חדש:**
   - `toggleAuthMethod()` - החלפה בין LDAP ל-OAuth
   - `testAzureConnection()` - בדיקת הגדרות Azure
   - `copyRedirectUri()` - העתקת Redirect URI
   - מילוי אוטומטי של Redirect URI

---

## 🔧 הגדרות במסד הנתונים

### הגדרות חדשות ב-`system_settings`:

| Setting Key | תיאור | ערכים אפשריים |
|------------|-------|---------------|
| `ad_auth_method` | שיטת אימות | `ldap` / `oauth` |
| `azure_tenant_id` | מזהה Tenant | GUID |
| `azure_client_id` | מזהה Application | GUID |
| `azure_client_secret` | Client Secret | String |
| `azure_redirect_uri` | Redirect URI | URL |

### הגדרות קיימות (נשמרו):
- `ad_enabled`
- `ad_server_url`
- `ad_port`
- `ad_base_dn`
- `ad_bind_dn`
- `ad_bind_password`
- `ad_user_search_base`
- `ad_user_search_filter`
- `ad_group_search_base`
- `ad_use_ssl`
- `ad_use_tls`
- `ad_admin_group`
- `ad_manager_group`
- `ad_auto_create_users`
- `ad_default_hativa_id`
- `ad_sync_on_login`

---

## 🚀 התקנה והגדרה

### שלב 1: התקנת חבילות

```bash
cd /path/to/izun
pip install -r requirements.txt
```

### שלב 2: הגדרת Azure AD (אם נדרש)

1. **צור App Registration ב-Azure Portal**
   - גש ל: https://portal.azure.com
   - App registrations → New registration
   - שם: "Committee Management System"

2. **העתק פרטים:**
   - Application (Client) ID
   - Directory (Tenant) ID

3. **צור Client Secret:**
   - Certificates & secrets → New client secret
   - העתק את **Value** (לא Secret ID!)

4. **הוסף Redirect URI:**
   - Authentication → Add platform → Web
   - URI: `https://your-domain.com/login/azure/callback`

5. **הגדר הרשאות:**
   - API permissions → Microsoft Graph → User.Read

### שלב 3: הגדרת המערכת

1. **התחבר כמנהל**
2. **תפריט → הגדרות → הגדרות Active Directory**
3. **סמן "הפעל אימות Active Directory"**
4. **בחר שיטת אימות: Azure AD OAuth 2.0**
5. **הזן:**
   - Tenant ID
   - Application (Client) ID
   - Client Secret
   - Redirect URI (אוטומטי)
6. **שמור והבדוק חיבור**

---

## 🔐 זרימת אימות Azure AD OAuth

### תהליך ההתחברות:

```
1. משתמש → לחיצה "התחבר עם Azure AD"
           ↓
2. מערכת → redirect למערכת: /login/azure
           ↓
3. backend → יצירת state (CSRF protection)
           → יצירת authorization URL
           → redirect ל-Microsoft login
           ↓
4. משתמש → מתחבר ב-Microsoft
           ↓
5. Microsoft → redirect למערכת: /login/azure/callback?code=...&state=...
           ↓
6. backend → אימות state
           → החלפת code ב-token
           → קריאת פרטי משתמש מ-Graph API
           → יצירה/עדכון משתמש במסד נתונים
           → יצירת session
           ↓
7. משתמש → מחובר למערכת
```

---

## 📊 תכונות ואבטחה

### ✅ תכונות שנוספו

- **אימות מודרני:** OAuth 2.0 / OpenID Connect
- **MFA Support:** תמיכה ב-Multi-Factor Authentication
- **Token-based:** אבטחה משופרת עם JWT
- **Graph API:** שליפת פרטי משתמש מ-Microsoft Graph
- **CSRF Protection:** הגנה מפני CSRF attacks
- **Auto-provisioning:** יצירת משתמשים אוטומטית
- **Group mapping:** מיפוי תפקידים לפי קבוצות Azure AD
- **Hybrid support:** תמיכה ב-LDAP ו-OAuth במקביל

### 🔒 אבטחה

**מומלץ:**
- ✅ HTTPS בלבד בפרודקשן
- ✅ Client Secret עם תוקף מוגבל (6-12 חודשים)
- ✅ Redirect URI מדויק (לא wildcards)
- ✅ Conditional Access ב-Azure AD
- ✅ Audit logging לכל פעולות אימות

**אל תעשה:**
- ❌ אל תשמור Client Secret בקוד
- ❌ אל תשתף secrets ב-Git
- ❌ אל תשתמש ב-HTTP בפרודקשן

---

## 🧪 בדיקה

### בדיקת LDAP
```bash
# מסך ההגדרות:
כפתור "בדוק חיבור" → אמור להציג "✅ החיבור ל-Active Directory הצליח"
```

### בדיקת Azure AD
```bash
# מסך ההגדרות:
כפתור "בדוק הגדרות Azure AD" → אמור להציג "✅ הגדרות Azure AD תקינות"

# התחברות מלאה:
1. התנתק
2. לחץ "התחבר עם Azure AD"
3. התחבר עם חשבון Azure AD
4. אמור להיות מועבר חזרה מחובר
```

### בדיקת Auto-provisioning
```bash
1. התחבר עם משתמש Azure AD חדש (לא קיים במערכת)
2. אם "צור משתמשים אוטומטית" מופעל:
   ✅ משתמש נוצר אוטומטית
   ✅ הודעה: "ברוך הבא, [שם מלא]"
```

---

## 🐛 פתרון בעיות נפוצות

### Azure AD OAuth

| שגיאה | פתרון |
|-------|--------|
| `invalid_client` | בדוק Client ID, Client Secret, Tenant ID |
| `redirect_uri_mismatch` | ודא התאמה מדויקת ב-Azure Portal |
| `AADSTS50011` | הוסף Redirect URI ב-Azure Portal → Authentication |
| "לא התקבל טוקן" | בדוק שיש הרשאה ל-User.Read |

### LDAP

| שגיאה | פתרון |
|-------|--------|
| "שגיאה בהתחברות" | בדוק קישוריות: `telnet dc.domain.com 636` |
| "פרטי התחברות שגויים" | בדוק Bind DN וסיסמה |
| "משתמש לא נמצא" | בדוק User Search Base ו-Filter |

---

## 📝 Logs

### הפעלת Logs לדיבאגינג

```bash
# צפייה בלוגים בזמן אמת:
tail -f /var/log/committee_system.log

# או עם systemd:
journalctl -u committee-system -f
```

### לוגים חשובים:
- `Azure AD authentication error` - שגיאות אימות
- `LDAP bind error` - שגיאות LDAP
- `Token error` - בעיות עם tokens
- `Graph API error` - שגיאות ב-Microsoft Graph

---

## 📚 קבצי עזר

| קובץ | תיאור |
|------|-------|
| `AZURE_AD_SETUP_GUIDE.md` | מדריך הגדרה מפורט בעברית |
| `requirements.txt` | חבילות Python נדרשות |
| `services/ad_service.py` | שכבת שירות AD/Azure |
| `templates/admin/ad_settings.html` | ממשק ניהול הגדרות |

---

## 🎓 למידע נוסף

### Microsoft Documentation
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/overview)

### Internal Documentation
- ראה `AZURE_AD_SETUP_GUIDE.md` למדריך מפורט
- ראה `README.md` למידע כללי על המערכת

---

## ✅ סיכום שינויים

### ✨ תכונות חדשות
- אימות Azure AD OAuth 2.0
- תמיכה ב-Microsoft Graph API
- ממשק ניהול היברידי (LDAP + OAuth)
- Auto-provisioning משופר
- Redirect URI אוטומטי

### 🔧 שיפורים טכניים
- ארכיטקטורה היברידית גמישה
- הפרדת concerns (LDAP vs OAuth)
- Audit logging משופר
- CSRF protection
- Error handling משופר

### 📄 תיעוד
- מדריך הגדרה מקיף בעברית
- דוגמאות קוד וצילומי מסך
- פתרון בעיות נפוצות
- Best practices לאבטחה

---

**גרסה:** 1.0  
**תאריך:** אוקטובר 2024  
**תאימות:** Python 3.8+, Flask 3.0+, MSAL 1.25+
