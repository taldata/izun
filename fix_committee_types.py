#!/usr/bin/env python3
"""
Script to fix committee types and assign them to correct divisions
"""

from database import DatabaseManager

def fix_committee_types():
    """Fix committee types by recreating them with correct division assignments"""
    
    db = DatabaseManager()
    
    print("Fixing committee types...")
    
    # The _insert_default_committee_types will be called automatically
    # when we create a new DatabaseManager instance, but since we already
    # have the database, we need to call it manually
    db._insert_default_committee_types()
    
    print("Committee types fixed!")
    
    # Verify the results
    print("\nCurrent committee types:")
    committee_types = db.get_committee_types()
    
    for ct in committee_types:
        print(f"  {ct['name']} - {ct['hativa_name']} - {ct['frequency']} - יום {ct['scheduled_day_name']}")

if __name__ == "__main__":
    fix_committee_types()
