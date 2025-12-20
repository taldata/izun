#!/bin/bash
# Startup script - compatible with both Render and AWS Elastic Beanstalk
# Note: On AWS EB, migrations run via .ebextensions/03_commands.config
# This script is kept for backward compatibility with Render

set -e  # Exit on any error

echo "==========================================="
echo "🚀 Starting Izun Committee Management System"
echo "==========================================="

# Detect if running on AWS EB (PORT env var may not be set, use default 8000)
if [ -z "$PORT" ]; then
    PORT=8000
    echo "⚠️  PORT not set, using default: $PORT"
fi

# Step 1: Ensure data directory exists (for AWS EB)
if [ ! -d "/var/app/data" ]; then
    echo "📁 Creating data directory..."
    mkdir -p /var/app/data || true
fi

# Step 2: Run database migrations (if not already run by EB commands)
echo ""
echo "📦 Step 2: Running database migrations..."
if python migrate_db.py; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed!"
    echo "❌ Cannot start server without database"
    exit 1
fi

# Step 3: Import data if database is empty and export file exists
echo ""
echo "📥 Step 3: Checking for data import..."
if [ -f "db_export.json" ]; then
    echo "   Found db_export.json - checking if import needed..."
    python upload_db.py import || echo "   ⚠️  Import skipped or failed (may not be needed)"
else
    echo "   No export file found - skipping import"
fi

# Step 4: Verify persistence
echo ""
echo "🔍 Step 4: Verifying data persistence..."
python verify_persistence.py
if [ $? -ne 0 ]; then
    echo "⚠️  Persistence verification failed (non-critical)"
fi

# Step 5: Start the application
echo ""
echo "🌟 Step 5: Starting application server..."
echo "==========================================="
exec gunicorn --bind 0.0.0.0:$PORT --timeout 300 application:application

