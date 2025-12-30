import urllib.parse
import migrate_to_postgres

# Credentials
user = "izun_admin"
password = "D9?F)D8:<32:<-E&3ibZK:Lp"
host = "izun-postgres.c144ycakgpha.il-central-1.rds.amazonaws.com"
port = "5432"
dbname = "izun"

# URL Encode password
encoded_password = urllib.parse.quote_plus(password)

database_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"

print(f"Target URL constructed (hidden password)")

json_path = "db_export_remote.json"

try:
    migrate_to_postgres.migrate_to_postgres(json_path, database_url)
    print("Migration wrapper finished.")
except Exception as e:
    print(f"Migration failed: {e}")
