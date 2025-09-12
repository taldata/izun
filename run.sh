#!/bin/bash

# Committee Management System Startup Script
echo "Starting Committee Management System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if database exists, if not run migration
if [ ! -f "committee_system.db" ]; then
    echo "Database not found. Running initial setup..."
    python migrate_db.py
fi

# Kill any existing Flask processes
echo "Checking for existing Flask processes..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 1

# Start the Flask application on port 5001
echo "Starting Flask application on http://localhost:5001"
echo "Press Ctrl+C to stop the server"
export FLASK_RUN_PORT=5001
python app.py
