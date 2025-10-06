# דוגמאות שימוש - תכונות מובייל

## דוגמה 1: טבלה שהופכת לכרטיסים

### HTML המקורי:
```html
<div class="table-responsive">
    <table class="table table-hover">
        <thead>
            <tr>
                <th>שם</th>
                <th>תאריך</th>
                <th>סטטוס</th>
                <th>פעולות</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>ועדת הזנק</td>
                <td>15/10/2025</td>
                <td><span class="badge bg-success">פעיל</span></td>
                <td>
                    <button class="btn btn-sm btn-primary">ערוך</button>
                    <button class="btn btn-sm btn-danger">מחק</button>
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

### התוצאה במובייל:
הטבלה תוסב אוטומטית ל:

```html
<div class="mobile-card">
    <div class="mobile-card-header">ועדת הזנק</div>
    <div class="mobile-card-row">
        <div class="mobile-card-label">תאריך</div>
        <div class="mobile-card-value">15/10/2025</div>
    </div>
    <div class="mobile-card-row">
        <div class="mobile-card-label">סטטוס</div>
        <div class="mobile-card-value"><span class="badge bg-success">פעיל</span></div>
    </div>
    <div class="mobile-card-actions">
        <button class="btn btn-sm btn-primary">ערוך</button>
        <button class="btn btn-sm btn-danger">מחק</button>
    </div>
</div>
```

---

## דוגמה 2: הוספת Bottom Navigation

ה-Bottom Navigation מתווסף אוטומטית למסכים קטנים. אם תרצה להוסיף קישור נוסף:

```javascript
// ב-mobile.js, פונקציית createBottomNavigation
bottomNav.innerHTML = `
    <a href="/" class="bottom-nav-item">
        <i class="bi bi-house"></i>
        <span>בית</span>
    </a>
    <!-- הוסף פריט חדש כאן -->
    <a href="/my-new-page" class="bottom-nav-item">
        <i class="bi bi-star"></i>
        <span>מועדפים</span>
    </a>
    ...
`;
```

---

## דוגמה 3: שימוש ב-Pull to Refresh

אין צורך בקוד מיוחד - זה עובד אוטומטית! אבל אם תרצה לבצע פעולה מותאמת:

```javascript
// הוסף event listener מותאם
document.addEventListener('pullToRefreshComplete', function() {
    console.log('העמוד רוענן!');
    // בצע פעולה נוספת כאן
});
```

---

## דוגמה 4: Swipe Gestures על כרטיס מותאם

```html
<div class="mobile-card" data-swipeable="true" data-swipe-action="showOptions">
    <div class="mobile-card-header">כרטיס עם swipe</div>
    <div class="mobile-card-row">
        <div class="mobile-card-label">מידע</div>
        <div class="mobile-card-value">תוכן</div>
    </div>
</div>

<script>
function showOptions(cardElement) {
    // פעולה מותאמת כשמחליקים את הכרטיס
    alert('הצג אפשרויות נוספות!');
}
</script>
```

---

## דוגמה 5: התקנה מהירה של PWA

### הוספת כפתור התקנה מותאם:

```html
<button id="install-pwa-btn" style="display: none;">
    <i class="bi bi-download"></i>
    התקן אפליקציה
</button>

<script>
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    // מנע את ההודעה האוטומטית
    e.preventDefault();
    deferredPrompt = e;
    
    // הצג כפתור מותאם
    document.getElementById('install-pwa-btn').style.display = 'block';
});

document.getElementById('install-pwa-btn').addEventListener('click', async () => {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`User response: ${outcome}`);
        deferredPrompt = null;
    }
});
</script>
```

---

## דוגמה 6: הוספת הודעה מותאמת במובייל

```javascript
// שימוש בפונקציה המובנית
showNotification('הפעולה בוצעה בהצלחה!', 'success');

// סוגי הודעות: 'info', 'success', 'error'
```

---

## דוגמה 7: בדיקה אם המכשיר הוא מובייל

```javascript
// בקוד שלך
if (document.body.classList.contains('mobile-device')) {
    // זה מובייל - בצע משהו מיוחד
    console.log('Running on mobile');
}

// או בדיקה ישירה
const isMobile = window.innerWidth <= 768;
```

---

## דוגמה 8: Floating Action Button (FAB)

```html
<!-- הוסף FAB מותאם -->
<button class="fab" onclick="quickAddCommittee()">
    <i class="bi bi-plus"></i>
</button>

<script>
function quickAddCommittee() {
    // פתח טופס מהיר להוספת ועדה
    document.getElementById('addCommitteeModal').show();
}
</script>
```

---

## דוגמה 9: Bottom Sheet Modal

```html
<!-- Modal רגיל שהופך ל-Bottom Sheet במובייל -->
<div class="modal fade" id="myModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">כותרת</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                תוכן המודל
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-primary">שמור</button>
            </div>
        </div>
    </div>
</div>
```

במובייל, המודל הזה יופיע אוטומטית כ-Bottom Sheet!

---

## דוגמה 10: עדכון Service Worker

אם עדכנת את המערכת, הוסף זאת ל-`sw.js`:

```javascript
// שנה את הגרסה בכל עדכון
const CACHE_NAME = 'committee-system-v2'; // היה v1

// הוסף קבצים חדשים לקאש
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/mobile.js',
    '/my-new-page',  // הוסף דף חדש
    // ...
];
```

---

## 💡 טיפים מעשיים

### 1. בדיקת תכונות במהירות
```javascript
// בקונסול של DevTools
console.log('Mobile JS Loaded:', typeof initMobileFeatures !== 'undefined');
console.log('Service Worker:', 'serviceWorker' in navigator);
console.log('Touch Support:', 'ontouchstart' in window);
```

### 2. התאמה אישית של גרירה
```css
/* שנה את המרחק הנדרש לגרירה */
.mobile-card {
    --swipe-threshold: 80px;
}
```

### 3. השבתת תכונות ספציפיות
```javascript
// אם תרצה להשבית Pull to Refresh בדף מסוים
document.body.classList.add('disable-pull-refresh');
```

```css
.disable-pull-refresh .pull-to-refresh-indicator {
    display: none !important;
}
```

---

## 🎯 Best Practices

1. **תמיד בדוק במכשיר אמיתי** - אמולטורים לא תמיד מדויקים
2. **השתמש ב-lighthouse** לבדיקת PWA
3. **בדוק ב-3G Slow** את מהירות הטעינה
4. **התחשב בגודלי טקסט** - מינימום 16px
5. **השאר מרווח** בין אלמנטים ניתנים ללחיצה

---

**צריך עזרה נוספת?** בדוק את `MOBILE_FEATURES.md` לתיעוד מלא!
