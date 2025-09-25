@echo off
:: Football Dashboard - Windows Startup Script
:: This script starts the football dashboard application on Windows

title Football Dashboard - Starting...

echo ========================================
echo    FOOTBALL DASHBOARD - WINDOWS
echo ========================================
echo.

:: Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    echo.
    pause
    exit /b 1
)

:: Display Python version
for /f "tokens=*" %%i in ('python --version') do echo Found: %%i

:: Check if we're in the correct directory
echo.
echo [2/5] Checking application directory...
if not exist "app.py" (
    echo ERROR: app.py not found in current directory
    echo Please run this script from the football-dashboard directory
    echo Current directory: %cd%
    echo.
    pause
    exit /b 1
)
echo Application files found in: %cd%

:: Install/upgrade dependencies
echo.
echo [3/5] Installing dependencies...
echo Installing required Python packages from requirements.txt...
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo WARNING: Some packages might have failed to install
        echo Trying individual fallback installation...
        pip install flask flask-cors requests python-dateutil --quiet
    )
) else (
    echo WARNING: requirements.txt not found, installing basic packages...
    pip install flask flask-cors requests python-dateutil --quiet
)

:: Check for database and run migration if needed
echo.
echo [4/6] Checking database...
if exist "football_predictions.db" (
    echo Database found, running migration to ensure schema is up to date...
    python migrate_db.py
) else (
    echo Database not found, will be created automatically on first run
)

:: Display startup info
echo.
echo [5/6] Preparing to start Football Dashboard...
echo.
echo ========================================
echo   Dashboard will be available at:
echo   http://localhost:5000
echo   http://127.0.0.1:5000
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

:: Quick API key info (no validation for fast startup)
echo.
echo [6/6] API Key Status:
if defined FOOTBALL_API_KEY (
    echo ✅ FOOTBALL_API_KEY: Custom key set
) else (
    echo ⚡ FOOTBALL_API_KEY: Using development fallback
)

if defined OPENAI_API_KEY (
    echo ✅ OPENAI_API_KEY: Custom key set
) else (
    echo ⚡ OPENAI_API_KEY: Using development fallback
)

echo ⚡ Fast startup mode - set PRODUCTION=true for secure mode

:: Set environment variables for better performance
set FLASK_ENV=production
set FLASK_DEBUG=False

:: Start the Flask application
echo.
echo Starting application...
python app.py

:: If we get here, the app has stopped
echo.
echo ========================================
echo Football Dashboard has stopped
echo ========================================
pause