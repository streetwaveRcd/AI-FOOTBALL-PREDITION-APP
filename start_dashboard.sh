#!/bin/bash
# Football Dashboard - Unix/Linux/macOS Startup Script
# This script starts the football dashboard application on Unix-like systems

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    FOOTBALL DASHBOARD - UNIX/LINUX${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

# Set script to exit on any error
set -e

print_header

# Check if Python is installed
print_step "[1/5] Checking Python installation..."

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    print_error "ERROR: Python is not installed or not in PATH"
    print_error "Please install Python 3.7+ from your package manager or https://python.org"
    echo
    echo "On Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "On CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "On macOS: brew install python3 (requires Homebrew)"
    echo
    exit 1
fi

# Display Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "Found: $PYTHON_VERSION"

# Check Python version (must be 3.7+)
PYTHON_VERSION_NUM=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if (( $(echo "$PYTHON_VERSION_NUM < 3.7" | bc -l) )); then
    print_error "ERROR: Python 3.7+ is required, but found Python $PYTHON_VERSION_NUM"
    exit 1
fi

# Check if we're in the correct directory
echo
print_step "[2/5] Checking application directory..."

if [[ ! -f "app.py" ]]; then
    print_error "ERROR: app.py not found in current directory"
    print_error "Please run this script from the football-dashboard directory"
    print_error "Current directory: $(pwd)"
    echo
    exit 1
fi

print_success "Application files found in: $(pwd)"

# Check for virtual environment and create if needed
echo
print_step "[3/5] Setting up Python environment..."

if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows Git Bash
    source venv/Scripts/activate
else
    # Unix-like systems
    source venv/bin/activate
fi

print_success "Virtual environment activated"

# Install/upgrade dependencies
echo
print_step "[4/6] Installing dependencies..."
echo "Installing required Python packages from requirements.txt..."

$PIP_CMD install --upgrade pip --quiet

if [[ -f "requirements.txt" ]]; then
    echo "Installing from requirements.txt..."
    $PIP_CMD install -r requirements.txt --quiet || {
        print_error "WARNING: Some packages from requirements.txt failed to install"
        echo "Trying fallback installation..."
        $PIP_CMD install flask flask-cors requests python-dateutil ddgs aiohttp beautifulsoup4 --quiet
    }
else
    print_error "WARNING: requirements.txt not found, installing basic packages..."
    $PIP_CMD install flask flask-cors requests python-dateutil --quiet
fi

# sqlite3 is built into Python, no need to install
if ! $PYTHON_CMD -c "import sqlite3" 2>/dev/null; then
    print_error "WARNING: SQLite3 module not available"
    print_error "This is unusual and may cause issues"
fi

print_success "Dependencies installed successfully"

# Check for database and run migration if needed
echo
print_step "[5/6] Checking database..."

if [[ -f "football_predictions.db" ]]; then
    echo "Database found, running migration to ensure schema is up to date..."
    $PYTHON_CMD migrate_db.py
    print_success "Database migration completed"
else
    echo "Database not found, will be created automatically on first run"
fi

# Quick API key info (no validation for fast startup)
echo
print_step "[6/6] API Key Status:"

if [[ -n "$FOOTBALL_API_KEY" ]]; then
    print_success "FOOTBALL_API_KEY: Custom key set"
else
    echo -e "${YELLOW}FOOTBALL_API_KEY: Using development fallback${NC}"
fi

if [[ -n "$OPENAI_API_KEY" ]]; then
    print_success "OPENAI_API_KEY: Custom key set"
else
    echo -e "${YELLOW}OPENAI_API_KEY: Using development fallback${NC}"
fi

echo -e "${YELLOW}⚡ Fast startup mode - set PRODUCTION=true for secure mode${NC}"

# Start the application
echo
print_step "Starting Football Dashboard..."
echo

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Dashboard will be available at:${NC}"
echo -e "${GREEN}   http://localhost:5000${NC}"
echo -e "${GREEN}   http://127.0.0.1:5000${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo

# Set environment variables for better performance
export FLASK_ENV=production
export FLASK_DEBUG=False

# Function to cleanup on exit
cleanup() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Football Dashboard has stopped${NC}"
    echo -e "${BLUE}========================================${NC}"
    deactivate 2>/dev/null || true
}

# Set trap to run cleanup on script exit
trap cleanup EXIT

# Start the Flask application
$PYTHON_CMD app.py