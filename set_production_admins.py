#!/usr/bin/env python3
"""
Set tal.s and shiran.bs as admin users in production
Run this script on Render to update production database
"""

import sqlite3
import sys

def set_admins():
    """Set tal.s and shiran.bs as admin users"""
    
    # Connect to production database
    try:
        conn = sqlite3.connect('committee_system.db')
        cursor = conn.cursor()
        
        print("🔍 Checking current users...")
        
        # Check tal.s
        cursor.execute("""
            SELECT username, email, role, auth_source, is_active
            FROM users
            WHERE username = 'tal.s' OR email = 'tal.s@innovationisrael.org.il'
        """)
        tal_user = cursor.fetchone()
        
        if tal_user:
            print(f"✅ Found tal.s: {tal_user[0]} ({tal_user[1]}) - Role: {tal_user[2]}")
        else:
            print("❌ tal.s not found - creating...")
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, role, auth_source, is_active)
                VALUES ('tal.s', 'tal.s@innovationisrael.org.il', 'AZURE_AD_NO_PASSWORD_AUTH', 
                        'Tal Sabag', 'admin', 'ad', 1)
            """)
            print("✅ Created tal.s as admin")
        
        # Check shiran.bs
        cursor.execute("""
            SELECT username, email, role, auth_source, is_active
            FROM users
            WHERE username = 'shiran.bs' OR email = 'shiran.bs@innovationisrael.org.il'
        """)
        shiran_user = cursor.fetchone()
        
        if shiran_user:
            print(f"✅ Found shiran.bs: {shiran_user[0]} ({shiran_user[1]}) - Role: {shiran_user[2]}")
        else:
            print("❌ shiran.bs not found - creating...")
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, role, auth_source, is_active)
                VALUES ('shiran.bs', 'shiran.bs@innovationisrael.org.il', 'AZURE_AD_NO_PASSWORD_AUTH', 
                        'Shiran Ben Simhon', 'admin', 'ad', 1)
            """)
            print("✅ Created shiran.bs as admin")
        
        # Update both users to admin role
        print("\n🔧 Updating users to admin role...")
        
        cursor.execute("""
            UPDATE users 
            SET role = 'admin', auth_source = 'ad', is_active = 1
            WHERE username IN ('tal.s', 'shiran.bs') 
               OR email IN ('tal.s@innovationisrael.org.il', 'shiran.bs@innovationisrael.org.il')
        """)
        
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} user(s) to admin role")
        
        # Verify the changes
        print("\n📊 Final verification:")
        cursor.execute("""
            SELECT username, email, role, full_name, auth_source, is_active
            FROM users
            WHERE username IN ('tal.s', 'shiran.bs') 
               OR email IN ('tal.s@innovationisrael.org.il', 'shiran.bs@innovationisrael.org.il')
            ORDER BY username
        """)
        
        admin_users = cursor.fetchall()
        for user in admin_users:
            print(f"  ✅ {user[0]:15} | {user[1]:40} | {user[2]:10} | {user[3]:20} | {user[4]:5} | Active: {user[5]}")
        
        # Commit changes
        conn.commit()
        print("\n✅ Changes committed to production database!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("🔐 Setting Production Admin Users")
    print("=" * 70)
    print()
    
    success = set_admins()
    
    print()
    print("=" * 70)
    if success:
        print("✅ SUCCESS: Admin users configured")
        print()
        print("Next steps:")
        print("1. Users should logout if currently logged in")
        print("2. Login again via SSO")
        print("3. They will have admin privileges")
        sys.exit(0)
    else:
        print("❌ FAILED: Could not configure admin users")
        sys.exit(1)
    print("=" * 70)
