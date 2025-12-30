
import os
import psycopg2
from datetime import datetime

# Database connection URL
DB_URL = "postgresql://izun_admin:IzunAdmin123!@izun-postgres.c144ycakgpha.il-central-1.rds.amazonaws.com:5432/izun_db"

def check_jan_2026():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        start_date = '2026-01-01'
        end_date = '2026-01-31'
        
        query = """
            SELECT vaadot_id, committee_name, vaada_date 
            FROM vaadot 
            WHERE vaada_date >= %s AND vaada_date <= %s
            ORDER BY vaada_date
        """
        
        print(f"Checking committees between {start_date} and {end_date}...")
        cursor.execute(query, (start_date, end_date))
        
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} committees in January 2026:")
        for row in rows:
            print(f"ID: {row[0]}, Name: {row[1]}, Date: {row[2]}")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_jan_2026()
