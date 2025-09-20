#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to check SLA data for all routes
"""

from database import DatabaseManager

def check_sla_data():
    """Check SLA data for all routes"""
    db = DatabaseManager()
    
    try:
        # Get all routes with their SLA data
        maslulim = db.get_maslulim()
        
        print("נתוני SLA עבור כל המסלולים:")
        print("=" * 80)
        
        # Group by hativa
        by_hativa = {}
        for maslul in maslulim:
            hativa_name = maslul['hativa_name']
            if hativa_name not in by_hativa:
                by_hativa[hativa_name] = []
            by_hativa[hativa_name].append(maslul)
        
        for hativa_name, hativa_maslulim in by_hativa.items():
            print(f"\n🏢 {hativa_name}:")
            print("-" * 60)
            
            for maslul in sorted(hativa_maslulim, key=lambda x: x['name']):
                sla_days = maslul.get('sla_days', 45)
                print(f"  📋 {maslul['name']:<50} SLA: {sla_days:>3} ימים")
        
        print(f"\n📊 סה\"כ: {len(maslulim)} מסלולים")
        
        # Statistics
        sla_counts = {}
        for maslul in maslulim:
            sla_days = maslul.get('sla_days', 45)
            sla_counts[sla_days] = sla_counts.get(sla_days, 0) + 1
        
        print("\n📈 התפלגות SLA:")
        for sla_days in sorted(sla_counts.keys()):
            count = sla_counts[sla_days]
            print(f"  {sla_days} ימים: {count} מסלולים")
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת נתוני SLA: {str(e)}")

if __name__ == '__main__':
    check_sla_data()
