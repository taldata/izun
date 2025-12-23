#!/bin/bash
# AWS Elastic Beanstalk Environment Setup Script
# Run this script after creating your RDS instance

set -e

echo "🚀 AWS Elastic Beanstalk Environment Setup"
echo "==========================================="

# Check if eb cli is installed
if ! command -v eb &> /dev/null; then
    echo "❌ EB CLI not found. Please install it first:"
    echo "   pip install awsebcli"
    exit 1
fi

# Configuration - REPLACE THESE VALUES
echo ""
echo "📝 Please provide the following configuration values:"
echo ""

# PostgreSQL RDS Configuration
read -p "Enter RDS Endpoint (e.g., izun-postgres.xxx.il-central-1.rds.amazonaws.com): " RDS_ENDPOINT
read -p "Enter RDS Database Name (default: izun): " RDS_DBNAME
RDS_DBNAME=${RDS_DBNAME:-izun}
read -p "Enter RDS Username (default: izun_admin): " RDS_USER
RDS_USER=${RDS_USER:-izun_admin}
read -s -p "Enter RDS Password: " RDS_PASSWORD
echo ""

# Azure AD Configuration
read -p "Enter Azure Tenant ID: " AZURE_TENANT_ID
read -p "Enter Azure Client ID: " AZURE_CLIENT_ID
read -s -p "Enter Azure Client Secret: " AZURE_CLIENT_SECRET
echo ""

# Flask Configuration
echo "Generating Flask secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Get EB environment URL
EB_URL=$(eb status 2>/dev/null | grep "CNAME:" | awk '{print $2}')
if [ -z "$EB_URL" ]; then
    read -p "Enter your EB environment URL (e.g., production-env.il-central-1.elasticbeanstalk.com): " EB_URL
fi

# Build DATABASE_URL
DATABASE_URL="postgresql://${RDS_USER}:${RDS_PASSWORD}@${RDS_ENDPOINT}:5432/${RDS_DBNAME}"

# Build redirect URI
AZURE_REDIRECT_URI="https://${EB_URL}/auth/callback"

echo ""
echo "📋 Configuration Summary:"
echo "========================="
echo "DATABASE_URL: postgresql://${RDS_USER}:****@${RDS_ENDPOINT}:5432/${RDS_DBNAME}"
echo "AZURE_TENANT_ID: $AZURE_TENANT_ID"
echo "AZURE_CLIENT_ID: $AZURE_CLIENT_ID"
echo "AZURE_REDIRECT_URI: $AZURE_REDIRECT_URI"
echo ""

read -p "Proceed with setting environment variables? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "⚙️ Setting environment variables..."

eb setenv \
    DATABASE_URL="$DATABASE_URL" \
    FLASK_ENV=production \
    SECRET_KEY="$SECRET_KEY" \
    AZURE_TENANT_ID="$AZURE_TENANT_ID" \
    AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
    AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
    AZURE_REDIRECT_URI="$AZURE_REDIRECT_URI"

echo ""
echo "✅ Environment variables set successfully!"
echo ""
echo "📌 Next steps:"
echo "1. Add the redirect URI to your Azure AD App Registration:"
echo "   $AZURE_REDIRECT_URI"
echo ""
echo "2. Deploy your application:"
echo "   eb deploy"
echo ""
echo "3. Open the application:"
echo "   eb open"
