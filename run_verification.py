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
    
    tables = ['users', 'hativot', 'maslulim', 'vaadot', 'events']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: {count}")
    
    conn.close()
    
except Exception as e:
    print(f"Verification failed: {e}")
