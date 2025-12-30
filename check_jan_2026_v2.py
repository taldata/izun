
import psycopg2
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Database connection URL from environment or hardcoded as per user context
DB_URL = "postgresql://izun_admin:IzunAdmin123!@izun-postgres.c144ycakgpha.il-central-1.rds.amazonaws.com:5432/izun_db"

def check_jan_2026():
    print("Starting check...", flush=True)
    try:
        conn = psycopg2.connect(DB_URL)
        print("Connected to DB.", flush=True)
        cursor = conn.cursor()
        
        start_date = '2026-01-01'
        end_date = '2026-01-31'
        
        query = """
            SELECT vaadot_id, committee_name, vaada_date 
            FROM vaadot 
            WHERE vaada_date >= %s AND vaada_date <= %s
            ORDER BY vaada_date
        """
        
        print(f"Executing query for range {start_date} to {end_date}...", flush=True)
        cursor.execute(query, (start_date, end_date))
        
        rows = cursor.fetchall()
        
        print(f"Query executed. Found {len(rows)} rows.", flush=True)
        
        if not rows:
            print("No committees found in January 2026.", flush=True)
        else:
            print(f"Found {len(rows)} committees in January 2026:", flush=True)
            for row in rows:
                print(f"ID: {row[0]}, Name: {row[1]}, Date: {row[2]}", flush=True)
            
        cursor.close()
        conn.close()
        print("Done.", flush=True)
        
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    check_jan_2026()
