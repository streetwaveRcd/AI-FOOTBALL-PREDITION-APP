# Football Dashboard 🏆⚽

A modern, cross-platform football dashboard with live match tracking, predictions, and result analysis. Built with Flask and vanilla JavaScript, featuring a sleek dark theme interface and AI-powered match predictions.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3.3-black?style=flat&logo=flask)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

Data source: football-data.org (v4 API).

## Features
- Live Matches: Real-time match data with live scores and status
- Upcoming Matches: Future fixtures with comprehensive filtering
- Smart Match Predictions: Multi-source AI-powered predictions with confidence scores
  - Free Web Search: Uses DuckDuckGo search (no API key required!)
  - Statistical Analysis: Advanced mathematical modeling
  - Optional AI Enhancement: GPT analysis (requires OpenAI API key)
  - Multi-Source Aggregation: Combines predictions from multiple sources
- Results: Historical match results and statistics
- Smart Filtering: Today, Tomorrow/Yesterday, Week, Custom date ranges
- Outcome Filters: Filter predictions by Wins, Draws, or confidence levels
- Auto-refresh: Updates every 10 minutes with optimized API usage
- Modern UI: Dark theme, responsive design with hover effects and animations
- Cross-platform: Startup scripts for Windows (.bat) and Unix (.sh)

## Quick Start

### Windows (PowerShell)
```powershell
# From the project root
.\start_dashboard.bat
```

### macOS/Linux
```bash
chmod +x start_dashboard.sh
./start_dashboard.sh
```

Then open http://127.0.0.1:5000 in your browser.

## Manual Setup

### 1) Navigate to the project folder
- Windows PowerShell:
  ```powershell
  cd "C:\\Users\\s.dabydin\\Documents\\warp_project\\banana-editor\\football-dashboard"
  ```
- macOS/Linux terminal:
  ```bash
  cd /path/to/football-dashboard
  ```

### 2) Create and activate a virtual environment (recommended)
- Windows (PowerShell):
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- macOS/Linux:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Required: Football Data API Key
- Get a free API key from https://www.football-data.org/client/register
- Windows (PowerShell):
  ```powershell
  $Env:FOOTBALL_API_KEY = "your_football_api_key_here"
  ```
- macOS/Linux:
  ```bash
  export FOOTBALL_API_KEY="your_football_api_key_here"
  ```

Optional: OpenAI API Key (for enhanced predictions)
- Get a key at https://platform.openai.com/api-keys
- Windows (PowerShell):
  ```powershell
  $Env:OPENAI_API_KEY = "your_openai_api_key_here"
  ```
- macOS/Linux:
  ```bash
  export OPENAI_API_KEY="your_openai_api_key_here"
  ```
- Note: Without OpenAI, the app uses free web search + statistical analysis.

Other optional settings (via .env or environment):
- HOST (default 127.0.0.1)
- PORT (default 5000)
- FLASK_DEBUG (default True)
- PRODUCTION (set to true to disable any development fallbacks)

### 5) Run the application
- Windows:
  ```powershell
  .\start_dashboard.bat
  ```
- macOS/Linux:
  ```bash
  ./start_dashboard.sh
  ```
- Or directly:
  ```bash
  python app.py
  ```

## Dashboard Tabs
- Live: Current matches in progress
- Upcoming: Future fixtures with date/league filtering
- Predictions: AI-powered match predictions with outcome filters
- Results: Completed matches and historical data
- Accuracy: Source comparison and confidence-based performance

## Prediction Sources (priority order)
1) Free Web Search (DuckDuckGo)
2) Statistical Analysis (built-in models)
3) AI Enhancement (OpenAI GPT, optional)

## Cost Breakdown
- Football Data API: Free tier (10 requests/minute)
- Web Search: Free (DuckDuckGo)
- Statistical Analysis: Free (built-in)
- OpenAI GPT: Optional (~$0.002 per prediction)

## Troubleshooting
- "GPT API unavailable - using fallback prediction":
  - Normal without an OpenAI key; free paths remain active.
- No predictions showing:
  - Ensure matches are SCHEDULED or TIMED.
- Web search predictions failing:
  - Check your internet; the app falls back to statistical predictions.
- API rate limiting:
  - Auto-refresh every 10 minutes to respect limits.
- Port in use:
  - Set PORT environment variable or update app.py.

## Security Notes
- Do not commit real API keys; use environment variables or .env (see .env.example).
- Set PRODUCTION=true to enforce secure mode and disable development fallbacks.

## Scripts
- start_dashboard.bat (Windows)
- start_dashboard.sh (macOS/Linux)
- setup.py (assisted .env setup)
- migrate_db.py (database migration/initialization)

## License
MIT
