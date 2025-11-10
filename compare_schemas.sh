#!/bin/bash
# Script to compare dev and prod schemas

echo "=== Getting DEV schema ==="
sqlite3 /Users/talsabag/izun/committee_system.db << 'EOF' > /tmp/dev_schema.txt
.schema
EOF

echo ""
echo "=== Getting PROD schema via SSH ==="
echo "You need to manually run this on prod:"
echo "ssh srv-d33b3e8dl3ps738nmmeg@ssh.oregon.render.com"
echo "Then run: sqlite3 /var/data/committee_system.db '.schema' > /tmp/prod_schema.txt"
echo ""
echo "DEV schema saved to: /tmp/dev_schema.txt"

