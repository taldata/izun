# AWS RDS PostgreSQL Setup Guide

Complete guide for setting up PostgreSQL RDS for the izun application.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- EB CLI installed

## Step 1: Create RDS PostgreSQL Instance

### Option A: Using AWS Console (Recommended)

1. Go to **AWS Console** → **RDS** → **Create database**
2. Choose **Standard create**
3. Select **PostgreSQL** (version 15.x recommended)
4. Choose template: **Free tier** or **Production**
5. Settings:
   - DB instance identifier: `izun-postgres`
   - Master username: `izun_admin`
   - Master password: *your secure password*
6. Instance configuration:
   - DB instance class: `db.t3.micro` (free tier eligible)
7. Storage:
   - Storage type: `gp2`
   - Allocated storage: `20 GiB`
8. Connectivity:
   - VPC: Same VPC as your Elastic Beanstalk environment
   - Public access: `Yes` (for initial setup, can be changed later)
   - VPC security group: Create new or use existing
9. Database options:
   - Initial database name: `izun`
10. Click **Create database**

### Option B: Using AWS CLI

```bash
# Set your password
export DB_PASSWORD="your-secure-password"

# Create the RDS instance
aws rds create-db-instance \
    --db-instance-identifier izun-postgres \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username izun_admin \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 20 \
    --storage-type gp2 \
    --db-name izun \
    --publicly-accessible \
    --backup-retention-period 7 \
    --region il-central-1

# Wait for the instance to be available (takes ~10 minutes)
aws rds wait db-instance-available --db-instance-identifier izun-postgres
```

## Step 2: Configure Security Group

Allow connections from Elastic Beanstalk to RDS:

1. Go to **RDS** → **Databases** → **izun-postgres** → **Connectivity & security**
2. Click on the VPC security group
3. Add inbound rule:
   - Type: `PostgreSQL`
   - Port: `5432`
   - Source: Security group of your EB environment (or `0.0.0.0/0` for testing)

## Step 3: Get RDS Endpoint

1. Go to **RDS** → **Databases** → **izun-postgres**
2. Copy the **Endpoint** (e.g., `izun-postgres.xxx.il-central-1.rds.amazonaws.com`)

## Step 4: Set Environment Variables

### Option A: Using the setup script (Interactive)

```bash
chmod +x scripts/setup_aws_env.sh
./scripts/setup_aws_env.sh
```

### Option B: Manual setup

```bash
# Replace values with your actual configuration
eb setenv \
    DATABASE_URL="postgresql://izun_admin:YOUR_PASSWORD@your-rds-endpoint:5432/izun" \
    FLASK_ENV=production \
    SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
    AZURE_TENANT_ID="your-tenant-id" \
    AZURE_CLIENT_ID="your-client-id" \
    AZURE_CLIENT_SECRET="your-client-secret" \
    AZURE_REDIRECT_URI="https://your-eb-url.elasticbeanstalk.com/auth/callback"
```

## Step 5: Migrate Data (if coming from Render)

### Export from Render
```bash
# On Render Shell or locally with Render DB connection
python upload_db.py
```

### Import to RDS
```bash
# Set your DATABASE_URL or pass as argument
export DATABASE_URL="postgresql://izun_admin:YOUR_PASSWORD@your-rds-endpoint:5432/izun"
python migrate_to_postgres.py db_export.json
```

## Step 6: Deploy Application

```bash
# Commit your changes
git add .
git commit -m "Add PostgreSQL support for AWS RDS"

# Deploy to Elastic Beanstalk
eb deploy
```

## Step 7: Verify Deployment

```bash
# Check environment status
eb status

# Check health
eb health

# View logs if issues
eb logs

# Open application
eb open
```

## Step 8: Update Azure AD Redirect URI

1. Go to **Azure Portal** → **App registrations** → **Your app**
2. Click **Authentication**
3. Add redirect URI: `https://your-eb-url.elasticbeanstalk.com/auth/callback`
4. Save

## Troubleshooting

### Connection Refused
- Check security group allows inbound on port 5432 from EB
- Verify RDS is publicly accessible (or in same VPC as EB)

### Database Does Not Exist
- Create the database manually:
  ```bash
  psql -h your-rds-endpoint -U izun_admin -c "CREATE DATABASE izun;"
  ```

### Authentication Failed
- Double-check the DATABASE_URL format
- Verify password doesn't contain special characters that need escaping

### Logs Show Import Errors
- Connect directly to verify:
  ```bash
  psql "postgresql://izun_admin:password@endpoint:5432/izun"
  \dt  # List tables
  SELECT COUNT(*) FROM users;
  ```

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| RDS db.t3.micro | ~$15 |
| Storage (20GB) | ~$2 |
| EB t3.micro | ~$8-10 |
| **Total** | ~$25-30/month |

## Backup Strategy

RDS automated backups are enabled with 7-day retention. For manual backups:

```bash
aws rds create-db-snapshot \
    --db-instance-identifier izun-postgres \
    --db-snapshot-identifier izun-backup-$(date +%Y%m%d)
```
