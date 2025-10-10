#!/bin/bash
# Render startup script - runs migrations and starts the server

set -e  # Exit on any error

echo "==========================================="
echo "🚀 Starting Izun Committee Management System"
echo "==========================================="

# Step 1: Run database migrations
echo ""
echo "📦 Step 1: Running database migrations..."
if python migrate_db.py; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed!"
    echo "❌ Cannot start server without database"
    exit 1
fi

# Step 2: Verify persistence
echo ""
echo "🔍 Step 2: Verifying data persistence..."
python verify_persistence.py
if [ $? -ne 0 ]; then
    echo "⚠️  Persistence verification failed (non-critical)"
fi

# Step 3: Start the application
echo ""
echo "🌟 Step 3: Starting application server..."
echo "==========================================="
exec gunicorn --bind 0.0.0.0:$PORT app:app

