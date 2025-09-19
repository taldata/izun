#!/usr/bin/env python3
"""
Script to add routes (maslulim) to the committee management system
"""

import sqlite3
from database import DatabaseManager

def add_routes():
    """Add all the specified routes to their respective divisions"""
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Define routes by division
    routes_by_division = {
        # זירה routes - I'll assume these belong to הזנק division since they seem related
        'הזנק': [
            'זירה',
            'זירה + מסלול',
            'הזנק',
            'הזנק קרן פרה-סיד (מסלול 7)',
            'הזנק קרן הון אנושי להייטק',
            'הזנק הליך תחרותי',
            'הזנק סיד היברידי',
            'הזנק מעבדות חדשנות',
            'הזנק חממות',
            'הזנק תנופה'
        ],
        'צמיחה': [
            'צמיחה',
            'צמיחה קרן הסיד (מסלול 7)',
            'צמיחה קרן A (מסלול 7)',
            'צמיחה קרן המו"פ',
            'צמיחה פיילוטים',
            'צמיחה פיילוט רחפנים',
            'צמיחה פליטת גזי חממה',
            'צמיחה חדשנות משבשת',
            'צמיחה ערוץ מהיר'
        ],
        'תשתיות': [
            'תשתיות',
            'תשתיות מאגדי מגנט (5א\')',
            'תשתיות מאגד בהתקשרויות יחידניות תעשיה',
            'תשתיות מאגד בהתקשרות יחידניות אקדמיה',
            'תשתיות המסלול המשותף עם משרד הביטחון (מימ"ד)',
            'תשתיות מסחור ידע (5ד\')',
            'תשתיות מחקר יישומי באקדמיה (5ג\')',
            'תשתיות תשתיות מו"פ לתעשייה (5ב\')',
            'תשתיות מחקר יישומי בתעשיה (5ה\')'
        ]
    }
    
    # Get division IDs
    hativot = db.get_hativot()
    hativa_map = {h['name']: h['hativa_id'] for h in hativot}
    
    print("Available divisions:")
    for name, id in hativa_map.items():
        print(f"  {name}: {id}")
    print()
    
    # Add routes to each division
    total_added = 0
    for division_name, routes in routes_by_division.items():
        if division_name not in hativa_map:
            print(f"Warning: Division '{division_name}' not found in database!")
            continue
            
        hativa_id = hativa_map[division_name]
        print(f"Adding routes to {division_name} (ID: {hativa_id}):")
        
        for route_name in routes:
            try:
                route_id = db.add_maslul(hativa_id, route_name, f"מסלול {route_name}")
                print(f"  ✓ Added: {route_name} (ID: {route_id})")
                total_added += 1
            except Exception as e:
                print(f"  ✗ Failed to add {route_name}: {e}")
        print()
    
    print(f"Total routes added: {total_added}")
    
    # Verify the additions
    print("\nVerification - Routes by division:")
    for division_name in routes_by_division.keys():
        if division_name in hativa_map:
            hativa_id = hativa_map[division_name]
            routes = db.get_maslulim(hativa_id)
            print(f"\n{division_name} ({len(routes)} routes):")
            for route in routes:
                print(f"  - {route['name']}")

if __name__ == "__main__":
    add_routes()
