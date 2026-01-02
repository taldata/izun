
from database import DatabaseManager
db = DatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT vaadot_id, start_time FROM vaadot WHERE start_time IS NOT NULL LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(f"ID: {row[0]}, Start: '{row[1]}'")
conn.close()
