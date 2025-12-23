#!/bin/bash
# Import database from Render via JSON export

RENDER_URL="https://committee-management-izun.onrender.com"
JSON_FILE="/tmp/db_export.json"
AWS_DB_PATH="/var/app/data/committee_system.db"

echo "==========================================="
echo "📥 Fetching database from Render (JSON)..."
echo "==========================================="

# Download JSON export
echo "Downloading db_export.json..."
curl -s "${RENDER_URL}/static/db_export.json" -o "${JSON_FILE}"

if [ ! -f "${JSON_FILE}" ] || [ ! -s "${JSON_FILE}" ]; then
    echo "❌ Failed to download db_export.json"
    echo "   File size: $(stat -c%s ${JSON_FILE} 2>/dev/null || echo 0) bytes"
    exit 1
fi

FILE_SIZE=$(stat -c%s "${JSON_FILE}" 2>/dev/null || stat -f%z "${JSON_FILE}" 2>/dev/null)
echo "✅ Downloaded ${FILE_SIZE} bytes"

if [ "${FILE_SIZE}" -lt 100 ]; then
    echo "❌ File too small - likely error page"
    cat "${JSON_FILE}"
    exit 1
fi

# Ensure data directory exists
sudo mkdir -p /var/app/data
sudo chown webapp:webapp /var/app/data
sudo chmod 755 /var/app/data

# Import using upload_db.py
echo ""
echo "📥 Importing to database..."
cd /var/app/current
python3 upload_db.py import "${JSON_FILE}"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully imported database!"
    ls -lh "${AWS_DB_PATH}"
else
    echo "❌ Import failed"
    exit 1
fi
