#!/usr/bin/env python3
"""
Migrate data from SQLite (local/Render) to PostgreSQL (AWS RDS)
Usage: python migrate_to_postgres.py [sqlite_path] [postgres_url]

If no arguments provided, uses:
- SQLite: db_export.json (exported data)
- PostgreSQL: DATABASE_URL environment variable
"""

import json
import os
import sys
from datetime import datetime

def get_postgres_connection(database_url: str):
    """Get PostgreSQL connection"""
    try:
        import psycopg2
        return psycopg2.connect(database_url)
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

def load_json_data(json_path: str) -> dict:
    """Load exported data from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate_to_postgres(json_path: str, postgres_url: str):
    """Migrate data from JSON export to PostgreSQL"""
    
    print(f"📥 Loading data from: {json_path}")
    data = load_json_data(json_path)
    
    print(f"🔗 Connecting to PostgreSQL...")
    conn = get_postgres_connection(postgres_url)
    cursor = conn.cursor()
    
    # Import order to respect foreign key relationships
    import_order = [
        'users',           # No dependencies
        'hativot',         # No dependencies
        'system_settings', # Depends on users (optional FK)
        'maslulim',        # Depends on hativot
        'committee_types', # Depends on hativot
        'exception_dates', # No dependencies
        'user_hativot',    # Depends on users, hativot
        'hativa_day_constraints',  # Depends on hativot
        'vaadot',          # Depends on committee_types, hativot, exception_dates
        'events',          # Depends on vaadot, maslulim
        'audit_logs',      # Depends on users (optional FK)
        'calendar_sync_events',  # No strict dependencies
    ]
    
    # Add any tables not in the import order at the end
    for table in data.keys():
        if table not in import_order:
            import_order.append(table)
    
    total_imported = 0
    
    for table in import_order:
        if table not in data:
            continue
        
        records = data[table]
        if not records:
            print(f"   ⏭️  {table}: No records to import")
            continue
        
        # Get column names from first record
        columns = list(records[0].keys())
        
        # Build parameterized insert query
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        # Use ON CONFLICT DO NOTHING for duplicate handling
        insert_query = f"""
            INSERT INTO {table} ({column_names}) 
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """
        
        success_count = 0
        error_count = 0
        
        for record in records:
            try:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_query, values)
                success_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"   ⚠️  Error in {table}: {e}")
        
        total_imported += success_count
        if error_count > 0:
            print(f"   ✓ {table}: {success_count}/{len(records)} records ({error_count} errors)")
        else:
            print(f"   ✓ {table}: {len(records)} records imported")
        
        conn.commit()
    
    # Reset sequences for PostgreSQL
    print("\n🔄 Resetting PostgreSQL sequences...")
    sequence_tables = [
        ('hativot', 'hativa_id'),
        ('maslulim', 'maslul_id'),
        ('committee_types', 'committee_type_id'),
        ('vaadot', 'vaadot_id'),
        ('events', 'event_id'),
        ('users', 'user_id'),
        ('exception_dates', 'date_id'),
        ('system_settings', 'setting_id'),
        ('audit_logs', 'log_id'),
        ('user_hativot', 'user_hativa_id'),
        ('hativa_day_constraints', 'constraint_id'),
        ('calendar_sync_events', 'sync_id'),
    ]
    
    for table, pk_column in sequence_tables:
        try:
            cursor.execute(f"""
                SELECT setval(pg_get_serial_sequence('{table}', '{pk_column}'), 
                              COALESCE((SELECT MAX({pk_column}) FROM {table}), 1))
            """)
        except Exception as e:
            print(f"   Note: Could not reset sequence for {table}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Migration complete!")
    print(f"📊 Total records imported: {total_imported}")

def main():
    # Get paths from arguments or defaults
    json_path = sys.argv[1] if len(sys.argv) > 1 else 'db_export.json'
    postgres_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('DATABASE_URL')
    
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        print("   First export data from your source database:")
        print("   python upload_db.py")
        sys.exit(1)
    
    if not postgres_url:
        print("❌ PostgreSQL URL not provided.")
        print("   Set DATABASE_URL environment variable or provide as argument:")
        print("   python migrate_to_postgres.py db_export.json postgresql://user:pass@host:5432/db")
        sys.exit(1)
    
    migrate_to_postgres(json_path, postgres_url)

if __name__ == '__main__':
    main()
