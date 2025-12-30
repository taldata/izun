import urllib.parse
import os
from database import DatabaseManager
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
os.environ['DATABASE_URL'] = database_url

try:
    print("Initializing DatabaseManager (creates schema)...")
    db = DatabaseManager()
    print("Schema initialization complete.")
    
    # Verification
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    print("Tables found:", [t[0] for t in tables])
    conn.close()
    
except Exception as e:
    print(f"Schema init failed: {e}")
    import traceback
    traceback.print_exc()
