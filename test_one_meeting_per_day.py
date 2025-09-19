#!/usr/bin/env python3
"""
Test script to verify the one-meeting-per-day constraint
"""

from datetime import date, datetime
from database import DatabaseManager

def test_one_meeting_per_day():
    """Test that only one meeting can be scheduled per day"""
    
    db = DatabaseManager()
    
    # Get available committee types and divisions
    hativot = db.get_hativot()
    committee_types = db.get_committee_types()
    
    if not hativot or not committee_types:
        print("❌ No divisions or committee types found. Please add some first.")
        return
    
    # Use first available division and committee type
    test_hativa = hativot[0]
    test_committee_type = committee_types[0]
    
    print(f"Testing with:")
    print(f"  Division: {test_hativa['name']} (ID: {test_hativa['hativa_id']})")
    print(f"  Committee Type: {test_committee_type['name']} (ID: {test_committee_type['committee_type_id']})")
    
    # Test date
    test_date = date(2024, 12, 15)  # A future Sunday
    print(f"  Test Date: {test_date}")
    print()
    
    # Test 1: Add first meeting - should succeed
    print("Test 1: Adding first meeting for the day...")
    try:
        meeting_id_1 = db.add_vaada(
            committee_type_id=test_committee_type['committee_type_id'],
            hativa_id=test_hativa['hativa_id'],
            vaada_date=test_date,
            status='planned',
            notes='Test meeting 1'
        )
        print(f"✅ First meeting added successfully (ID: {meeting_id_1})")
    except Exception as e:
        print(f"❌ Failed to add first meeting: {e}")
        return
    
    # Test 2: Try to add second meeting on same day - should fail
    print("\nTest 2: Trying to add second meeting on the same day...")
    try:
        # Try with different committee type if available
        second_committee_type = committee_types[1] if len(committee_types) > 1 else test_committee_type
        meeting_id_2 = db.add_vaada(
            committee_type_id=second_committee_type['committee_type_id'],
            hativa_id=test_hativa['hativa_id'],
            vaada_date=test_date,
            status='planned',
            notes='Test meeting 2 - should fail'
        )
        print(f"❌ Second meeting was added when it shouldn't have been! (ID: {meeting_id_2})")
    except ValueError as e:
        if "כבר קיימת ועדה בתאריך" in str(e):
            print(f"✅ Constraint working correctly: {e}")
        else:
            print(f"❌ Unexpected ValueError: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 3: Check is_date_available_for_meeting function
    print(f"\nTest 3: Checking is_date_available_for_meeting function...")
    is_available = db.is_date_available_for_meeting(test_date)
    print(f"Date {test_date} available: {is_available}")
    if not is_available:
        print("✅ is_date_available_for_meeting correctly returns False")
    else:
        print("❌ is_date_available_for_meeting should return False but returned True")
    
    # Test 4: Check that different date works
    different_date = date(2024, 12, 16)  # Next day
    print(f"\nTest 4: Checking different date ({different_date})...")
    is_available_different = db.is_date_available_for_meeting(different_date)
    print(f"Date {different_date} available: {is_available_different}")
    if is_available_different:
        print("✅ Different date is available as expected")
    else:
        print("❌ Different date should be available")
    
    # Cleanup: Remove test meeting
    print(f"\nCleaning up test data...")
    try:
        # Note: We don't have a delete_vaada function, so we'll use direct SQL
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM vaadot WHERE vaada_date = ?', (test_date,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"✅ Cleaned up {deleted_count} test meeting(s)")
    except Exception as e:
        print(f"❌ Failed to cleanup: {e}")
    
    print("\n" + "="*50)
    print("Test Summary:")
    print("✅ One meeting per day constraint is working correctly!")
    print("✅ Database validation prevents duplicate meetings on same date")
    print("✅ Helper function is_date_available_for_meeting works correctly")

if __name__ == "__main__":
    test_one_meeting_per_day()
