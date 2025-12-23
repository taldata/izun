#!/bin/bash
# Script to fetch SQLite database from Render and copy to AWS

echo "==========================================="
echo "📥 Fetching database from Render..."
echo "==========================================="

RENDER_URL="https://committee-management-izun.onrender.com"
DB_FILE="/tmp/render_committee_system.db"
AWS_DB_PATH="/var/app/data/committee_system.db"

# Method 1: Try to download from static folder (if user copied it there)
echo "Attempting Method 1: Download from static folder..."
curl -s "${RENDER_URL}/static/committee_system.db" -o "${DB_FILE}"

if [ -f "${DB_FILE}" ] && [ -s "${DB_FILE}" ] && [ $(stat -f%z "${DB_FILE}" 2>/dev/null || stat -c%s "${DB_FILE}" 2>/dev/null) -gt 10000 ]; then
    echo "✅ Downloaded database file from static folder"
    ls -lh "${DB_FILE}"
else
    echo "❌ Method 1 failed"
    rm -f "${DB_FILE}"
    
    # Method 2: Try to download db_export.json
    echo ""
    echo "Attempting Method 2: Download db_export.json..."
    curl -s "${RENDER_URL}/static/db_export.json" -o /tmp/db_export.json
    
    if [ -f /tmp/db_export.json ] && [ -s /tmp/db_export.json ] && [ $(stat -f%z /tmp/db_export.json 2>/dev/null || stat -c%s /tmp/db_export.json 2>/dev/null) -gt 100 ]; then
        echo "✅ Downloaded db_export.json"
        echo "📥 Importing JSON to database..."
        python3 upload_db.py import /tmp/db_export.json
        exit $?
    else
        echo "❌ Method 2 failed"
        echo ""
        echo "💡 Please run this in Render Shell first:"
        echo "   cd /opt/render/project/src"
        echo "   cp /var/data/committee_system.db static/committee_system.db"
        echo "   # OR export to JSON:"
        echo "   python upload_db.py export"
        echo "   cp db_export.json static/db_export.json"
        exit 1
    fi
fi

# If we got here, we have the SQLite file - copy it to AWS location
echo ""
echo "📥 Copying database to AWS location..."
sudo mkdir -p /var/app/data
sudo cp "${DB_FILE}" "${AWS_DB_PATH}"
sudo chown webapp:webapp "${AWS_DB_PATH}"
sudo chmod 664 "${AWS_DB_PATH}"

echo "✅ Database copied successfully!"
echo "   Location: ${AWS_DB_PATH}"
ls -lh "${AWS_DB_PATH}"
