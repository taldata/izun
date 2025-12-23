#!/bin/bash
# Alternative method: Download directly via Render and import

echo "==========================================="
echo "📥 Alternative: Direct database import"
echo "==========================================="

# Try to download JSON first
RENDER_URL="https://committee-management-izun.onrender.com"
JSON_FILE="/tmp/db_export_render.json"

echo "Attempting to download db_export.json..."
curl -v "${RENDER_URL}/static/db_export.json" -o "${JSON_FILE}" 2>&1 | tail -20

if [ -f "${JSON_FILE}" ]; then
    SIZE=$(stat -c%s "${JSON_FILE}" 2>/dev/null || stat -f%z "${JSON_FILE}" 2>/dev/null)
    echo "File size: ${SIZE} bytes"
    
    if [ "${SIZE}" -gt 100 ]; then
        echo "✅ Downloaded successfully"
        cat "${JSON_FILE}" | head -20
    else
        echo "❌ File too small"
        cat "${JSON_FILE}"
    fi
fi
