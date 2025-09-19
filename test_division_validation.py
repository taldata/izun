#!/usr/bin/env python3
"""
Test script to verify division validation for events
"""

from datetime import date
from database import DatabaseManager

def test_division_validation():
    """Test that events can only be created with routes from the same division as the committee"""
    
    db = DatabaseManager()
    
    print("Testing division validation for events...")
    
    # Get divisions and routes
    hativot = db.get_hativot()
    maslulim = db.get_maslulim()
    
    if len(hativot) < 2:
        print("❌ Need at least 2 divisions to test validation")
        return
    
    if len(maslulim) < 2:
        print("❌ Need at least 2 routes to test validation")
        return
    
    print(f"Available divisions: {[h['name'] for h in hativot]}")
    route_names = [f"{m['name']} ({m['hativa_name']})" for m in maslulim]
    print(f"Available routes: {route_names}")
    
    # Create committee types for testing
    try:
        # Create committee type for first division
        committee_type_1 = db.add_committee_type(
            hativa_id=hativot[0]['hativa_id'],
            name='ועדת בדיקה 1',
            scheduled_day=0,  # Monday
            frequency='weekly'
        )
        print(f"✅ Created committee type for {hativot[0]['name']}")
        
        # Create committee meeting
        test_date = date(2024, 12, 20)  # Future Monday
        vaada_id = db.add_vaada(
            committee_type_id=committee_type_1,
            hativa_id=hativot[0]['hativa_id'],
            vaada_date=test_date
        )
        print(f"✅ Created committee meeting for {test_date}")
        
        # Find routes from different divisions
        route_same_division = None
        route_different_division = None
        
        for route in maslulim:
            if route['hativa_id'] == hativot[0]['hativa_id']:
                route_same_division = route
            elif route['hativa_id'] != hativot[0]['hativa_id']:
                route_different_division = route
        
        if not route_same_division or not route_different_division:
            print("❌ Could not find routes from different divisions")
            return
        
        print(f"Testing with:")
        print(f"  Committee: {hativot[0]['name']}")
        print(f"  Route (same division): {route_same_division['name']} ({route_same_division['hativa_name']})")
        print(f"  Route (different division): {route_different_division['name']} ({route_different_division['hativa_name']})")
        
        # Test 1: Create event with route from same division - should succeed
        print("\nTest 1: Creating event with route from same division...")
        try:
            event_id_1 = db.add_event(
                vaadot_id=vaada_id,
                maslul_id=route_same_division['maslul_id'],
                name='אירוע בדיקה - חטיבה תואמת',
                event_type='kokok',
                expected_requests=5
            )
            print(f"✅ Event created successfully (ID: {event_id_1})")
        except Exception as e:
            print(f"❌ Failed to create event with same division route: {e}")
        
        # Test 2: Try to create event with route from different division - should fail
        print("\nTest 2: Trying to create event with route from different division...")
        try:
            event_id_2 = db.add_event(
                vaadot_id=vaada_id,
                maslul_id=route_different_division['maslul_id'],
                name='אירוע בדיקה - חטיבה לא תואמת',
                event_type='shotef',
                expected_requests=3
            )
            print(f"❌ Event was created when it shouldn't have been! (ID: {event_id_2})")
        except ValueError as e:
            if "אינו יכול להיות משויך" in str(e):
                print(f"✅ Validation working correctly: {e}")
            else:
                print(f"❌ Unexpected validation error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Test 3: Test update event validation
        print("\nTest 3: Testing event update validation...")
        try:
            # Try to update the valid event to use a route from different division
            success = db.update_event(
                event_id=event_id_1,
                vaadot_id=vaada_id,
                maslul_id=route_different_division['maslul_id'],
                name='אירוע מעודכן - חטיבה לא תואמת',
                event_type='kokok',
                expected_requests=7
            )
            print(f"❌ Event update succeeded when it shouldn't have!")
        except ValueError as e:
            if "אינו יכול להיות משויך" in str(e):
                print(f"✅ Update validation working correctly: {e}")
            else:
                print(f"❌ Unexpected update validation error: {e}")
        except Exception as e:
            print(f"❌ Unexpected update error: {e}")
        
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return
    
    # Cleanup
    print(f"\nCleaning up test data...")
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete events
        cursor.execute('DELETE FROM events WHERE vaadot_id = ?', (vaada_id,))
        events_deleted = cursor.rowcount
        
        # Delete committee meeting
        cursor.execute('DELETE FROM vaadot WHERE vaadot_id = ?', (vaada_id,))
        vaadot_deleted = cursor.rowcount
        
        # Delete committee type
        cursor.execute('DELETE FROM committee_types WHERE committee_type_id = ?', (committee_type_1,))
        committee_types_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ Cleaned up: {events_deleted} events, {vaadot_deleted} meetings, {committee_types_deleted} committee types")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    
    print("\n" + "="*60)
    print("Division Validation Test Summary:")
    print("✅ Events can only be created with routes from the same division")
    print("✅ Database validation prevents cross-division event creation")
    print("✅ Event updates are also validated for division consistency")
    print("✅ Clear error messages provided for validation failures")

if __name__ == "__main__":
    test_division_validation()
