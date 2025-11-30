#!/bin/bash

# איזון עומסים - Committee Load Balancing System
# Startup script for the Flask web application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="איזון עומסים"
PORT=${PORT:-5001}
PYTHON_CMD=${PYTHON_CMD:-python3}
VENV_DIR="venv"
DB_FILE="committee_system.db"
CURRENT_SCRIPT_PID=$$

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
check_python() {
    if ! command -v $PYTHON_CMD &> /dev/null; then
        log_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    log_success "Python found: $(python3 --version)"
}

# Setup virtual environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment..."
        $PYTHON_CMD -m venv $VENV_DIR
        log_success "Virtual environment created"
    fi
    
    log_info "Activating virtual environment..."
    source $VENV_DIR/bin/activate
    
    # Check if requirements need to be installed
    if [ ! -f "$VENV_DIR/.requirements_installed" ] || [ "requirements.txt" -nt "$VENV_DIR/.requirements_installed" ]; then
        log_info "Installing/updating dependencies..."
        pip install --upgrade pip
        pip install -r requirements.txt
        touch "$VENV_DIR/.requirements_installed"
        log_success "Dependencies installed"
    else
        log_info "Dependencies already up to date"
    fi
}

# Initialize database if needed
init_database() {
    if [ ! -f "$DB_FILE" ]; then
        log_info "Database not found. Initializing database..."
        $PYTHON_CMD -c "from database import DatabaseManager; DatabaseManager()"
        log_success "Database initialized"
    else
        log_info "Database already exists"
    fi
}

# Kill processes that match pattern (excluding this script)
kill_processes_by_pattern() {
    local pattern=$1
    local description=$2
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    local kill_list=()

    if [ -n "$pids" ]; then
        for pid in $pids; do
            if [ "$pid" = "$CURRENT_SCRIPT_PID" ]; then
                continue
            fi
            kill_list+=("$pid")
        done
    fi

    if [ ${#kill_list[@]} -eq 0 ]; then
        return 1
    fi

    local label=${description:-"processes matching '$pattern'"}
    log_warning "Stopping $label: ${kill_list[*]}"
    kill "${kill_list[@]}" 2>/dev/null || true
    sleep 1

    local still_running=()
    for pid in "${kill_list[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            still_running+=("$pid")
        fi
    done

    if [ ${#still_running[@]} -gt 0 ]; then
        log_warning "Force killing stubborn $label: ${still_running[*]}"
        kill -9 "${still_running[@]}" 2>/dev/null || true
    fi

    return 0
}

# Clean up existing processes
cleanup_processes() {
    log_info "Terminating existing application processes before start..."

    local patterns=(
        "python.*app.py::Flask app (python app.py)"
        "flask .*app.py::Flask development server"
        "gunicorn.*app::Gunicorn workers"
        "celery .*app::Celery workers"
        "apscheduler.*CalendarSyncScheduler::Scheduler jobs"
    )

    local killed_any=false
    for entry in "${patterns[@]}"; do
        local pattern="${entry%%::*}"
        local label="${entry##*::}"
        if kill_processes_by_pattern "$pattern" "$label"; then
            killed_any=true
        fi
    done

    if [ "$killed_any" = true ]; then
        log_success "Existing processes cleaned up"
    else
        log_info "No matching application processes found"
    fi
}

# Ensure the configured port is free before starting the app
free_port_if_in_use() {
    log_info "Checking if port $PORT is in use..."
    local pids=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)

    if [ -n "$pids" ]; then
        log_warning "Port $PORT is in use by PIDs: $pids"
        kill -TERM $pids 2>/dev/null || true
        sleep 1

        # If still listening, force kill
        local remaining=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)
        if [ -n "$remaining" ]; then
            log_warning "Force killing remaining PIDs on port $PORT: $remaining"
            kill -9 $remaining 2>/dev/null || true
        fi

        # Final check
        local final=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)
        if [ -z "$final" ]; then
            log_success "Port $PORT is now free"
        else
            log_error "Failed to free port $PORT (still held by: $final)"
            exit 1
        fi
    else
        log_info "Port $PORT is free"
    fi
}

# Start the application
start_app() {
    log_info "Starting $APP_NAME on http://localhost:$PORT"
    log_info "Press Ctrl+C to stop the server"
    echo
    
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export FLASK_RUN_PORT=$PORT
    
    # Start with error handling
    if ! $PYTHON_CMD app.py; then
        log_error "Failed to start the application"
        exit 1
    fi
}

# Trap to handle cleanup on exit
cleanup_on_exit() {
    echo
    log_info "Shutting down $APP_NAME..."
    pkill -f "python.*app.py" 2>/dev/null || true
    log_success "Application stopped"
}

trap cleanup_on_exit EXIT INT TERM

# Main execution
main() {
    echo "=================================================="
    echo "           $APP_NAME"
    echo "=================================================="
    echo
    
    check_python
    setup_venv
    init_database
    cleanup_processes
    free_port_if_in_use
    start_app
}

# Run main function
main "$@"
