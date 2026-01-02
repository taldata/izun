
import sys
import os
# Add the project root to sys.path
sys.path.append(os.path.abspath('.'))

from app import calendar_service, db
from database import DatabaseManager

try:
    print("Starting calendar reset test...")
    # We might need to mock ADService if authentication fails, 
    # but let's see if it even gets to that point.
    result = calendar_service.delete_all_calendar_events_and_reset()
    print(f"Result: {result}")
except Exception as e:
    import traceback
    print("CAUGHT EXCEPTION:")
    traceback.print_exc()
