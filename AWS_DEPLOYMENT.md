# AWS Elastic Beanstalk Deployment Guide

מדריך להעברת המערכת ל-AWS Elastic Beanstalk.

## דרישות מוקדמות

1. חשבון AWS פעיל
2. AWS CLI מותקן
3. EB CLI מותקן
4. גישה ל-AWS עם הרשאות מתאימות

## התקנת כלים נדרשים

### התקנת AWS CLI

```bash
# macOS
brew install awscli

# או באמצעות pip
pip install awscli
```

### התקנת EB CLI

```bash
pip install awsebcli
```

### אימות ב-AWS

```bash
aws configure
```

הזן:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (מומלץ: `us-east-1` או `eu-central-1`)
- Default output format: `json`

## פריסה ראשונית

### 1. אתחול פרויקט Elastic Beanstalk

```bash
cd /Users/talsabag/izun
eb init -p python-3.12 committee-management-izun
```

במהלך האתחול תתבקש לבחור:
- Region: בחר את ה-Region המתאים
- Application name: `committee-management-izun`
- Python version: `Python 3.12`

### 2. יצירת סביבת ייצור

```bash
eb create izun-production --single
```

הפקדה `--single` יוצרת סביבה עם instance אחד בלבד (חסכוני יותר). להסרה, השתמש ב-`eb create izun-production`.

### 3. הגדרת משתני סביבה

לפני הפריסה, הגדר את משתני הסביבה הדרושים:

```bash
eb setenv FLASK_ENV=production \
          DATABASE_PATH=/var/app/data/committee_system.db \
          AZURE_AD_CLIENT_ID=your_client_id \
          AZURE_AD_CLIENT_SECRET=your_client_secret \
          AZURE_AD_TENANT_ID=your_tenant_id \
          AZURE_AD_REDIRECT_URI=https://your-domain.elasticbeanstalk.com/auth/callback
```

**חשוב**: החלף את הערכים עם הערכים האמיתיים של Azure AD שלך.

### 4. פריסת האפליקציה

```bash
eb deploy
```

זה יבנה את האפליקציה ויפרוס אותה לסביבת ה-EB.

### 5. פתיחת האפליקציה בדפדפן

```bash
eb open
```

## ניהול משתני סביבה

### הצגת כל משתני הסביבה

```bash
eb printenv
```

### הוספת משתנה סביבה

```bash
eb setenv KEY=value
```

### מחיקת משתנה סביבה

```bash
eb unsetenv KEY
```

## ניהול סביבות

### רשימת סביבות

```bash
eb list
```

### החלפה בין סביבות

```bash
eb use izun-production
```

### הצגת מידע על הסביבה הנוכחית

```bash
eb status
```

### הצגת לוגים

```bash
eb logs
```

### הצגת לוגים בזמן אמת

```bash
eb logs --follow
```

### גישה ל-SSH

```bash
eb ssh
```

## מסד נתונים

### מיקום מסד הנתונים

מסד הנתונים SQLite נשמר ב-`/var/app/data/committee_system.db`.

**חשוב**: הנתונים נשמרים על ה-instance. אם ה-instance נמחק, הנתונים יאבדו!

### גיבוי מסד הנתונים

```bash
# התחבר ל-instance
eb ssh

# בתוך ה-instance, צור גיבוי
sudo cp /var/app/data/committee_system.db /var/app/data/backup_$(date +%Y%m%d).db

# או העתק למחשב המקומי
eb ssh -c "sudo cat /var/app/data/committee_system.db" > backup.db
```

### שחזור מסד נתונים

```bash
# העתק קובץ למחשב המקומי
scp backup.db ec2-user@your-instance:/tmp/

# התחבר ל-instance
eb ssh

# בתוך ה-instance, העתק לגיבוי
sudo cp /tmp/backup.db /var/app/data/committee_system.db
sudo chown webapp:webapp /var/app/data/committee_system.db
```

## עדכוני קוד

לאחר ביצוע שינויים בקוד:

```bash
git add .
git commit -m "Your commit message"
eb deploy
```

## הגדרת Domain מותאם אישית

### 1. רכישת Domain

רכש domain מ-AWS Route 53 או מכל ספק אחר.

### 2. יצירת SSL Certificate

```bash
# יצירת certificate ב-AWS Certificate Manager
aws acm request-certificate \
    --domain-name your-domain.com \
    --validation-method DNS \
    --region us-east-1
```

### 3. הגדרת Domain ב-EB

```bash
eb create izun-production \
    --envvars FLASK_ENV=production \
    --cname your-domain-name
```

או עבור סביבה קיימת:

```bash
eb config
```

ערוך את הקובץ והוסף:

```yaml
aws:elasticbeanstalk:environment:proxy:
  ProxyServer: apache
aws:elasticbeanstalk:environment:proxy:staticfiles:
  /static: static
```

### 4. הגדרת Route 53

צור CNAME record שמצביע ל-URL של ה-EB environment.

## עלויות משוערות

- **t3.micro instance**: ~$8-10/חודש (Free Tier: 750 שעות בחודש הראשון)
- **Application Load Balancer**: ~$16/חודש (אם לא משתמש ב-`--single`)
- **Storage (EBS)**: ~$0.10/GB/חודש
- **Data Transfer**: משתנה לפי שימוש

**הערה**: עם `--single` (ללא Load Balancer), העלות נמוכה יותר.

## פתרון בעיות

### האפליקציה לא עולה

```bash
# בדוק את הלוגים
eb logs

# בדוק את ה-status
eb status

# בדוק health
eb health
```

### בעיות עם מסד נתונים

```bash
# התחבר ל-instance
eb ssh

# בדוק אם התיקייה קיימת
ls -la /var/app/data

# בדוק הרשאות
sudo chown -R webapp:webapp /var/app/data
sudo chmod -R 755 /var/app/data
```

### בעיות עם migrations

```bash
eb ssh
cd /var/app/current
python migrate_db.py
```

### איפוס סביבה

אם יש בעיות קשות:

```bash
# מחיקת סביבה (זהירות - זה מוחק הכל!)
eb terminate izun-production

# יצירה מחדש
eb create izun-production --single
```

## הערות חשובות

1. **אחסון נתונים**: עם `--single`, הנתונים נשמרים על ה-instance. עבור ייצור, שקול העברה ל-RDS.
2. **גיבויים**: הקפד על גיבויים קבועים של מסד הנתונים.
3. **משתני סביבה**: לעולם אל תכלול secrets בקוד - השתמש ב-`eb setenv`.
4. **Monitoring**: השתמש ב-AWS CloudWatch לניטור הביצועים.

## מעבר מ-Render ל-AWS

אם אתה מעביר נתונים מ-Render:

1. **ייצא את הנתונים מ-Render**:
   ```bash
   # ב-Render Shell
   python upload_db.py export
   ```

2. **הורד את db_export.json**:
   ```bash
   # העתק למחשב המקומי
   scp render-user@your-render-instance:/opt/render/project/src/db_export.json ./
   ```

3. **העלה ל-AWS**:
   ```bash
   # העתק ל-AWS
   eb ssh
   # בתוך ה-instance
   # העלה את הקובץ (דרך S3 או scp)
   python upload_db.py import
   ```

## קישורים שימושיים

- [AWS Elastic Beanstalk Documentation](https://docs.aws.amazon.com/elasticbeanstalk/)
- [EB CLI Documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html)
- [Python on Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-apps.html)
