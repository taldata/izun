#!/bin/bash
# Script to download database from Render to AWS EB

echo "==========================================="
echo "📥 Downloading database from Render..."
echo "==========================================="

# Try to download db_export.json from Render static folder
RENDER_URL="https://committee-management-izun.onrender.com"

echo "Attempting to download from Render..."
curl -s "${RENDER_URL}/static/db_export.json" -o /tmp/db_export.json

if [ -f /tmp/db_export.json ] && [ -s /tmp/db_export.json ]; then
    echo "✅ Downloaded db_export.json from Render"
    ls -lh /tmp/db_export.json
else
    echo "❌ Could not download from Render static folder"
    echo ""
    echo "Please run this in Render Shell first:"
    echo "  cd /opt/render/project/src"
    echo "  python upload_db.py export"
    echo "  cp db_export.json static/db_export.json"
    echo ""
    echo "Then run this script again, or manually upload db_export.json to AWS"
    exit 1
fi

# Import to AWS database
echo ""
echo "📥 Importing to AWS database..."
python upload_db.py import /tmp/db_export.json

echo ""
echo "✅ Done!"
