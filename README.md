# Football Dashboard (Cross-Platform)

A modern dark-themed football dashboard with tabs for Live Matches, Upcoming Matches, Predictions, and Results (already played matches). Built with Flask and vanilla JS with enhanced prediction capabilities and improved UI/UX.

Data source: football-data.org (v4 API).

## Features
- **Live Matches**: Real-time match data with live scores and status
- **Upcoming Matches**: Future fixtures with comprehensive filtering
- **Smart Match Predictions**: Multi-source AI-powered predictions with confidence scores
  - 🆓 **FREE Web Search**: Uses DuckDuckGo search (no API key required!)
  - 📊 **Statistical Analysis**: Advanced mathematical modeling
  - 🤖 **Optional AI Enhancement**: GPT analysis (requires OpenAI API key)
  - 🌐 **Multi-Source Aggregation**: Combines predictions from multiple sources
- **Results**: Historical match results and statistics
- **Smart Filtering**: Today, Tomorrow/Yesterday, Week, Custom date ranges
- **Outcome Filters**: Filter predictions by Wins, Draws, or confidence levels
- **Auto-refresh**: Updates every 10 minutes with optimized API usage
- **Modern UI**: Dark theme, responsive design with hover effects and animations
- **Cross-platform**: Run scripts for both Windows (.bat) and Unix (.sh)

## Prerequisites
- Python 3.8+
- A football-data.org API key (free tier available)
- Internet connection (for web search predictions)
- **Optional**: OpenAI API key (for enhanced AI predictions)

## Setup

### 1) Navigate to the project folder
   - **Windows PowerShell**:
     ```powershell
     
     ```
   - **macOS/Linux terminal**:
     ```bash
     cd /path/to/football-dashboard
     ```

### 2) Create a virtual environment (recommended)
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

### 3) Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

### 4) Set your API keys
   
   **Required: Football Data API Key**
   - Get your free API key from [football-data.org](https://www.football-data.org/client/register)
   - **Windows (PowerShell)**:
     ```powershell
     $Env:FOOTBALL_DATA_API_KEY = "your_football_api_key_here"
     ```
   - **macOS/Linux**:
     ```bash
     export FOOTBALL_DATA_API_KEY="your_football_api_key_here"
     ```
   
   **Optional: OpenAI API Key (for enhanced predictions)**
   - Only needed if you want GPT-powered prediction analysis
   - Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **Windows (PowerShell)**:
     ```powershell
     $Env:OPENAI_API_KEY = "your_openai_api_key_here"
     ```
   - **macOS/Linux**:
     ```bash
     export OPENAI_API_KEY="your_openai_api_key_here"
     ```
   - ⚠️ **Note**: Without OpenAI key, the app will use free web search + statistical analysis (still very effective!)

### 5) Run the application
   - **Windows**:
     ```powershell
     .\run.bat
     ```
   - **macOS/Linux**:
     ```bash
     chmod +x run.sh
     ./run.sh
     ```

## Recent Improvements (v2.0)

### 🆓 FREE Web Search Integration
- **DuckDuckGo Integration**: Completely free web search - no API keys required!
- **Multi-Source Analysis**: Aggregates predictions from multiple football websites
- **Intelligent Text Analysis**: Extracts predictions from search results and web pages
- **Smart Source Weighting**: Different reliability scores for different prediction sources
- **No Rate Limits**: Unlike Google Search API, DuckDuckGo search is completely free

### 🤖 Enhanced AI System
- **OpenAI Optional**: Works perfectly without OpenAI API key
- **Three-Tier Prediction**: Web Search + Statistical Analysis + Optional AI Enhancement
- **Fallback Chain**: Graceful degradation when services are unavailable
- **Fixed API Compatibility**: Updated for OpenAI v1.x client
- **Cost-Effective**: Only use paid APIs when you want maximum accuracy

### 📊 Prediction System Enhancements
- **Fixed Prediction Diversity**: Resolved issue where all predictions showed "Draw"
- **Enhanced Filtering**: Outcome-based filters (All Predictions, Wins Only, Draws Only)
- **Confidence Scoring**: Realistic confidence levels from multiple sources
- **Status Handling**: Updated to handle both "SCHEDULED" and "TIMED" match statuses

### UI/UX Improvements
- **Centered Layout**: Fixed alignment issues with home/away team sections in match cards
- **Modern Styling**: Enhanced gradients, hover effects, and responsive design
- **Better Spacing**: Optimized card layouts with improved centering and consistent widths
- **Debug Logging**: Comprehensive logging for easier troubleshooting

## Configuration

### Environment Variables
- **FOOTBALL_DATA_API_KEY**: 🔴 **Required** - Get free key from football-data.org
- **OPENAI_API_KEY**: 🟡 **Optional** - For enhanced AI predictions (costs $)
- **PORT**: Default 5000 (set PORT environment variable to change)
- **HOST**: Default 127.0.0.1
- **FLASK_DEBUG**: Default True

### Prediction Sources (in order of priority)
1. 🆓 **Web Search** (DuckDuckGo) - Always free!
2. 📊 **Statistical Analysis** - Built-in mathematical models
3. 🤖 **AI Enhancement** - Optional OpenAI GPT analysis

### Cost Breakdown
- **Football Data API**: Free tier (10 requests/minute)
- **Web Search**: Completely free (DuckDuckGo)
- **Statistical Analysis**: Free (built-in)
- **OpenAI GPT**: Optional (~$0.002 per prediction)

## Usage

Once running, navigate to `http://127.0.0.1:5000` in your browser.

### Available Tabs
- **Live**: Current matches in progress
- **Upcoming**: Future fixtures with date/league filtering
- **Predictions**: AI-powered match predictions with outcome filters
- **Results**: Completed matches and historical data

### Filtering Options
- **Date Filters**: Today, Tomorrow/Yesterday, This Week, Custom Range
- **Prediction Filters**: All Predictions, Wins Only, Draws Only, High Confidence (>70%)
- **League Filter**: Available on Upcoming and Results tabs

## Troubleshooting

### Common Issues
- **"GPT API unavailable - using fallback prediction"**: 
  - ✅ **This is normal!** The app is working correctly using free web search + statistical analysis
  - Only appears if OpenAI API key is missing or has quota issues
  - Predictions are still highly accurate without GPT

- **No predictions showing**: Check that matches have "SCHEDULED" or "TIMED" status

- **Web search predictions failing**:
  - Check your internet connection
  - DuckDuckGo may be temporarily rate-limiting (very rare)
  - App will automatically fallback to statistical predictions

- **API rate limiting**: The app automatically refreshes every 10 minutes to respect API limits

- **Missing team crests**: Some teams may not have crest URLs in the API data

### Debug Mode
The app runs with debug logging enabled. Check console output for detailed information about API calls and prediction processing.

## Security Note
Do not commit real API keys. Always use environment variables for API keys in production deployments.

## License
MIT

