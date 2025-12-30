import urllib.parse
import psycopg2

# Credentials
user = "izun_admin"
password = "D9?F)D8:<32:<-E&3ibZK:Lp"
host = "izun-postgres.c144ycakgpha.il-central-1.rds.amazonaws.com"
port = "5432"
dbname = "izun"

# URL Encode password
encoded_password = urllib.parse.quote_plus(password)
database_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"

print(f"Connecting to: {host}")
try:
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("\n--- Committee Dates (Vaadot) ---")
    cursor.execute("SELECT MIN(vaada_date), MAX(vaada_date), COUNT(*) FROM vaadot")
    min_date, max_date, count = cursor.fetchone()
    print(f"Range: {min_date} to {max_date} (Total: {count})")
    
    print("\n--- Event Dates ---")
    cursor.execute("SELECT MIN(scheduled_date), MAX(scheduled_date), COUNT(*) FROM events")
    min_date, max_date, count = cursor.fetchone()
    print(f"Range: {min_date} to {max_date} (Total: {count})")
    
    print("\n--- Vaadot in December 2025 ---")
    cursor.execute("SELECT * FROM vaadot WHERE vaada_date BETWEEN '2025-12-01' AND '2025-12-31'")
    rows = cursor.fetchall()
    print(f"Count: {len(rows)}")
    for row in rows:
        print(row)

    conn.close()
    
except Exception as e:
    print(f"Verification failed: {e}")
