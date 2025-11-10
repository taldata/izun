#!/usr/bin/env python3
"""Compare database schemas between dev and prod"""
import sqlite3
import sys
import os

def get_schema_info(db_path):
    """Get detailed schema information from a database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema = {}
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        schema[table] = {
            'columns': [],
            'indexes': []
        }
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns:
            cid, name, col_type, notnull, default, pk = col
            schema[table]['columns'].append({
                'name': name,
                'type': col_type,
                'notnull': bool(notnull),
                'default': default,
                'pk': bool(pk)
            })
        
        # Get indexes for this table
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        for idx in indexes:
            idx_name = idx[1]
            cursor.execute(f"PRAGMA index_info({idx_name})")
            idx_cols = [row[2] for row in cursor.fetchall()]
            schema[table]['indexes'].append({
                'name': idx_name,
                'columns': idx_cols
            })
    
    conn.close()
    return schema

def compare_schemas(dev_schema, prod_schema):
    """Compare two schemas and report differences"""
    differences = []
    
    # Check tables
    dev_tables = set(dev_schema.keys())
    prod_tables = set(prod_schema.keys())
    
    missing_in_prod = dev_tables - prod_tables
    missing_in_dev = prod_tables - dev_tables
    
    if missing_in_prod:
        differences.append(f"❌ Tables missing in PROD: {', '.join(missing_in_prod)}")
    if missing_in_dev:
        differences.append(f"⚠️  Tables missing in DEV: {', '.join(missing_in_dev)}")
    
    # Check common tables
    common_tables = dev_tables & prod_tables
    for table in sorted(common_tables):
        dev_cols = {col['name']: col for col in dev_schema[table]['columns']}
        prod_cols = {col['name']: col for col in prod_schema[table]['columns']}
        
        dev_col_names = set(dev_cols.keys())
        prod_col_names = set(prod_cols.keys())
        
        missing_in_prod_cols = dev_col_names - prod_col_names
        missing_in_dev_cols = prod_col_names - dev_col_names
        
        if missing_in_prod_cols:
            differences.append(f"❌ Table '{table}': Columns missing in PROD: {', '.join(missing_in_prod_cols)}")
        if missing_in_dev_cols:
            differences.append(f"⚠️  Table '{table}': Columns missing in DEV: {', '.join(missing_in_dev_cols)}")
        
        # Check column types for common columns
        common_cols = dev_col_names & prod_col_names
        for col_name in sorted(common_cols):
            dev_col = dev_cols[col_name]
            prod_col = prod_cols[col_name]
            
            if dev_col['type'] != prod_col['type']:
                differences.append(f"⚠️  Table '{table}', Column '{col_name}': Type mismatch - DEV: {dev_col['type']}, PROD: {prod_col['type']}")
            if dev_col['notnull'] != prod_col['notnull']:
                differences.append(f"⚠️  Table '{table}', Column '{col_name}': NOT NULL mismatch - DEV: {dev_col['notnull']}, PROD: {prod_col['notnull']}")
            if dev_col['pk'] != prod_col['pk']:
                differences.append(f"⚠️  Table '{table}', Column '{col_name}': PRIMARY KEY mismatch - DEV: {dev_col['pk']}, PROD: {prod_col['pk']}")
    
    return differences

if __name__ == '__main__':
    dev_db = '/Users/talsabag/izun/committee_system.db'
    
    if len(sys.argv) > 1:
        prod_db = sys.argv[1]
    else:
        print("Usage: python check_schema.py <prod_db_path>")
        print("\nFor now, checking DEV schema only:")
        dev_schema = get_schema_info(dev_db)
        print(f"\n✅ DEV has {len(dev_schema)} tables:")
        for table in sorted(dev_schema.keys()):
            print(f"  - {table}: {len(dev_schema[table]['columns'])} columns")
        sys.exit(0)
    
    print("Comparing schemas...")
    dev_schema = get_schema_info(dev_db)
    prod_schema = get_schema_info(prod_db)
    
    differences = compare_schemas(dev_schema, prod_schema)
    
    if not differences:
        print("✅ Schemas are identical!")
    else:
        print(f"❌ Found {len(differences)} difference(s):\n")
        for diff in differences:
            print(diff)
        sys.exit(1)

