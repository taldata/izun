#!/usr/bin/env python3
"""
Script to fetch database from Render and import to AWS
Run this on AWS EB instance via SSH
"""

import os
import sys
import requests
import subprocess

RENDER_URL = "https://committee-management-izun.onrender.com"

def main():
    print("=" * 50)
    print("📥 Fetching database from Render...")
    print("=" * 50)
    
    # Try to download db_export.json
    export_url = f"{RENDER_URL}/static/db_export.json"
    print(f"\n1. Attempting to download from: {export_url}")
    
    try:
        response = requests.get(export_url, timeout=30)
        if response.status_code == 200 and len(response.content) > 100:
            # Save to temp file
            export_file = "/tmp/db_export.json"
            with open(export_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ Downloaded {len(response.content)} bytes to {export_file}")
            
            # Import to AWS database
            print(f"\n2. Importing to AWS database...")
            db_path = os.environ.get('DATABASE_PATH', '/var/app/data/committee_system.db')
            print(f"   Database path: {db_path}")
            
            # Run import
            result = subprocess.run(
                ['python', 'upload_db.py', 'import', export_file],
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            if result.returncode == 0:
                print("\n✅ Successfully imported database!")
            else:
                print(f"\n❌ Import failed with code {result.returncode}")
                return 1
        else:
            print(f"❌ Failed to download (status: {response.status_code})")
            print("\n💡 Please run this in Render Shell first:")
            print("   cd /opt/render/project/src")
            print("   python upload_db.py export")
            print("   cp db_export.json static/db_export.json")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Please run this in Render Shell first:")
        print("   cd /opt/render/project/src")
        print("   python upload_db.py export")
        print("   cp db_export.json static/db_export.json")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
