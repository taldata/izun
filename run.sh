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

# Clean up existing processes
cleanup_processes() {
    log_info "Checking for existing Flask processes..."
    local pids=$(pgrep -f "python.*app.py" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        log_warning "Found existing Flask processes: $pids"
        pkill -f "python.*app.py" 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        local remaining=$(pgrep -f "python.*app.py" 2>/dev/null || true)
        if [ -n "$remaining" ]; then
            log_warning "Force killing remaining processes: $remaining"
            pkill -9 -f "python.*app.py" 2>/dev/null || true
        fi
        log_success "Existing processes cleaned up"
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
    start_app
}

# Run main function
main "$@"
