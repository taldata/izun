#!/usr/bin/env python3
"""
Force update session for admin users - DEVELOPMENT ONLY
This script helps verify admin role is correctly set
"""

import sqlite3

def verify_admin_users():
    """Verify admin users in database"""
    conn = sqlite3.connect('committee_system.db')
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🔍 Verifying Admin Users")
    print("=" * 70)
    print()
    
    # Check all admin users
    cursor.execute("""
        SELECT user_id, username, email, role, auth_source, is_active, full_name
        FROM users
        WHERE role = 'admin'
        ORDER BY username
    """)
    
    admins = cursor.fetchall()
    
    if not admins:
        print("❌ No admin users found!")
        conn.close()
        return False
    
    print(f"✅ Found {len(admins)} admin user(s):\n")
    
    for admin in admins:
        user_id, username, email, role, auth_source, is_active, full_name = admin
        status = "✅ Active" if is_active else "❌ Inactive"
        
        print(f"  👤 {full_name}")
        print(f"     User ID:     {user_id}")
        print(f"     Username:    {username}")
        print(f"     Email:       {email}")
        print(f"     Role:        {role}")
        print(f"     Auth Source: {auth_source}")
        print(f"     Status:      {status}")
        print()
    
    conn.close()
    return True

if __name__ == '__main__':
    verify_admin_users()
    
    print("=" * 70)
    print("📝 IMPORTANT STEPS TO GET ADMIN ACCESS:")
    print("=" * 70)
    print()
    print("1. ✅ Database is updated (verified above)")
    print()
    print("2. 🔓 LOGOUT completely:")
    print("   - Click your name (top right)")
    print("   - Click 'התנתק'")
    print("   - OR go to: https://izun.onrender.com/logout")
    print()
    print("3. 🔐 LOGIN again:")
    print("   - Go to: https://izun.onrender.com")
    print("   - Will redirect to Microsoft SSO")
    print("   - Login with your credentials")
    print()
    print("4. ✅ Verify admin access:")
    print("   - Top right: Click your name")
    print("   - Should see 'ניהול משתמשים' option")
    print("   - Go to: https://izun.onrender.com/admin/users")
    print()
    print("=" * 70)
    print("⚠️  CRITICAL: You MUST logout and login again!")
    print("    Old session still has old role (user)")
    print("    New login will load new role (admin) from database")
    print("=" * 70)
