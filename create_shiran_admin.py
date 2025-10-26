#!/usr/bin/env python3
"""
Create or update Shiran as admin user in production
"""

import sqlite3
import os

def create_shiran_admin():
    """Create or update shiran.bs as admin user"""
    
    # Use correct database path for Render
    db_path = '/var/data/committee_system.db' if os.path.exists('/var/data') else 'committee_system.db'
    
    print("=" * 70)
    print("👤 Creating/Updating Shiran as Admin")
    print("=" * 70)
    print(f"📁 Database: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if Shiran exists
        cursor.execute("""
            SELECT user_id, username, email, role, is_active
            FROM users
            WHERE username = 'shiran.bs' OR email = 'shiran.bs@innovationisrael.org.il'
        """)
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"✅ Found existing user:")
            print(f"   User ID: {existing_user[0]}")
            print(f"   Username: {existing_user[1]}")
            print(f"   Email: {existing_user[2]}")
            print(f"   Current Role: {existing_user[3]}")
            print(f"   Active: {existing_user[4]}")
            print()
            
            # Update to admin
            cursor.execute("""
                UPDATE users 
                SET role = 'admin', 
                    is_active = 1,
                    auth_source = 'ad'
                WHERE username = 'shiran.bs' OR email = 'shiran.bs@innovationisrael.org.il'
            """)
            
            print(f"🔧 Updated user to admin role")
            
        else:
            print("❌ User not found - creating new user...")
            
            # Create new user
            cursor.execute("""
                INSERT INTO users (
                    username, 
                    email, 
                    password_hash, 
                    full_name, 
                    role, 
                    auth_source, 
                    is_active
                )
                VALUES (
                    'shiran.bs',
                    'shiran.bs@innovationisrael.org.il',
                    'AZURE_AD_NO_PASSWORD_AUTH',
                    'Shiran Ben Simhon',
                    'admin',
                    'ad',
                    1
                )
            """)
            
            print("✅ Created new user: shiran.bs")
        
        # Commit changes
        conn.commit()
        
        # Verify final state
        print("\n" + "=" * 70)
        print("📊 Final Verification:")
        print("=" * 70)
        
        cursor.execute("""
            SELECT user_id, username, email, full_name, role, auth_source, is_active
            FROM users
            WHERE username = 'shiran.bs' OR email = 'shiran.bs@innovationisrael.org.il'
        """)
        
        final_user = cursor.fetchone()
        
        if final_user:
            print(f"\n✅ Success! User details:")
            print(f"   User ID:     {final_user[0]}")
            print(f"   Username:    {final_user[1]}")
            print(f"   Email:       {final_user[2]}")
            print(f"   Full Name:   {final_user[3]}")
            print(f"   Role:        {final_user[4]} 👑")
            print(f"   Auth Source: {final_user[5]}")
            print(f"   Active:      {'✅ Yes' if final_user[6] else '❌ No'}")
            print()
        else:
            print("\n❌ Error: User not found after operation")
            conn.close()
            return False
        
        conn.close()
        
        print("=" * 70)
        print("✅ SUCCESS: Shiran is now an admin!")
        print("=" * 70)
        print()
        print("📝 Next steps:")
        print("1. Shiran should visit: https://izun.onrender.com")
        print("2. Login via Microsoft SSO")
        print("3. Will have full admin access")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    create_shiran_admin()
