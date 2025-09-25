# Football Dashboard - Setup Guide

A comprehensive football prediction dashboard with live matches, predictions, and accuracy tracking.

## 🚀 Quick Start

### Windows
1. **Double-click** `start_dashboard.bat` 
2. The script will automatically:
   - Check Python installation
   - Install dependencies
   - Setup the database
   - Start the dashboard
3. Open your browser to `http://localhost:5000`

### macOS / Linux / Unix
1. **Open terminal** in the project directory
2. **Run**: `./start_dashboard.sh`
   - If permission denied: `chmod +x start_dashboard.sh` then try again
3. The script will automatically:
   - Check Python installation
   - Create virtual environment
   - Install dependencies
   - Setup the database
   - Start the dashboard
4. Open your browser to `http://localhost:5000`

---

## 📋 System Requirements

### Required
- **Python 3.7+** (3.8+ recommended)
- **Internet connection** (for fetching match data)
- **4GB RAM minimum** (8GB recommended)

### Python Packages (Auto-installed)
- Flask 2.0+
- Flask-CORS
- Requests
- SQLite3 (built-in)

---

## 🛠️ Manual Installation

If the automatic scripts don't work, follow these steps:

### 1. Install Python
- **Windows**: Download from [python.org](https://python.org)
- **macOS**: `brew install python3` or from [python.org](https://python.org)
- **Ubuntu/Debian**: `sudo apt update && sudo apt install python3 python3-pip`
- **CentOS/RHEL**: `sudo yum install python3 python3-pip`

### 2. Install Dependencies
```bash
# Windows
pip install flask flask-cors requests python-dotenv

# macOS/Linux (preferred with virtual environment)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install flask flask-cors requests python-dotenv
```

### 3. Setup Database
```bash
python migrate_db.py  # If database exists
# Otherwise, it will be created automatically
```

### 4. Start Application
```bash
python app.py
```

---

## 🌐 Dashboard Features

### 📊 Main Tabs
1. **Live Matches** - Currently ongoing matches with live updates
2. **Upcoming Matches** - Future matches with AI predictions
3. **Predictions** - Detailed match predictions with:
   - Win/Draw/Loss probabilities
   - Half-time scenarios
   - Team statistics
   - Confidence ratings
4. **Results** - Past match results
5. **Accuracy** - Prediction accuracy analysis and statistics

### 🤖 Prediction Features
- **Main Predictions**: Home Win / Draw / Away Win with confidence levels
- **Half-Time Scenarios**: Probability of teams leading at half-time but losing at full-time
- **Team Statistics**: Strength ratings and goals per game
- **Confidence Levels**:
  - 🟡 **Elite (80%+)**: High-confidence predictions
  - 🟢 **High (70-79%)**: Strong predictions
  - 🟠 **Medium (50-69%)**: Moderate confidence
  - 🔴 **Low (<50%)**: Lower confidence

### 📈 Accuracy Tracking
- **Overall accuracy** percentage across all predictions
- **Confidence-based accuracy**: Performance by confidence level
- **Outcome-based accuracy**: Performance by prediction type
- **Historical comparison**: Predictions vs actual results

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project directory:

```env
# Football Data API (optional - has default)
FOOTBALL_API_KEY=your_api_key_here

# OpenAI API (optional - for GPT predictions)
OPENAI_API_KEY=your_openai_key_here

# Server Configuration
HOST=127.0.0.1
PORT=5000
FLASK_DEBUG=False
```

### API Keys (Optional)
- **Football Data API**: Get free key at [football-data.org](https://football-data.org)
- **OpenAI API**: Get key at [openai.com](https://openai.com) for GPT predictions

---

## 🖥️ Browser Compatibility

### Recommended Browsers
- **Chrome 90+** ✅
- **Firefox 88+** ✅ 
- **Safari 14+** ✅
- **Edge 90+** ✅

### Mobile Support
- Fully responsive design
- Touch-friendly interface
- Optimized for mobile viewing

---

## 🐛 Troubleshooting

### Common Issues

#### "Python not found"
- **Windows**: Make sure Python is in PATH during installation
- **macOS**: Install via Homebrew: `brew install python3`
- **Linux**: Install via package manager: `sudo apt install python3`

#### "Permission denied" (macOS/Linux)
```bash
chmod +x start_dashboard.sh
./start_dashboard.sh
```

#### Port 5000 already in use
- Change port in `app.py`: `port = int(os.environ.get('PORT', 8000))`
- Or set environment variable: `PORT=8000`

#### Database issues
```bash
# Reset database
rm football_predictions.db
python migrate_db.py
```

#### Dependencies fail to install
```bash
# Upgrade pip first
pip install --upgrade pip
# Then try installing dependencies again
```

---

## 📱 Mobile Usage

### Features on Mobile
- **Responsive design** - Auto-adapts to screen size
- **Touch navigation** - Swipe-friendly interface
- **Optimized cards** - Compact layout for mobile viewing
- **Quick loading** - Optimized for mobile networks

---

## 🔄 Updates

### Updating the Application
1. **Pull latest changes** (if using Git)
2. **Run migration**: `python migrate_db.py`
3. **Restart the application**

### Database Migration
The migration script (`migrate_db.py`) automatically:
- Adds new database columns
- Preserves existing data
- Updates schema for new features

---

## 📊 Database

### Data Storage
- **SQLite database**: `football_predictions.db`
- **Automatic backups**: Created during migrations
- **Data includes**:
  - Match predictions with timestamps
  - Actual match results
  - Prediction accuracy tracking

### Privacy
- **No personal data** collected
- **Local storage only** - data stays on your device
- **API calls** only for match data (football-data.org)

---

## 🎯 Performance Tips

### For Better Performance
1. **Close unused tabs** in your browser
2. **Use modern browser** (Chrome, Firefox, Edge)
3. **Stable internet** for live data updates
4. **4GB+ RAM** recommended for smooth operation

### Resource Usage
- **RAM**: ~100-200MB typical usage
- **CPU**: Low usage, spikes during predictions
- **Network**: ~1-5MB per hour for live updates
- **Storage**: ~10-50MB for database

---

## 📞 Support

### If You Need Help
1. **Check this README** for common solutions
2. **Restart the application** - fixes many issues
3. **Check browser console** for error messages
4. **Try different browser** if issues persist

### System Information
The dashboard includes system information at:
`http://localhost:5000/api/system-info`

---

## 🎉 Enjoy Your Dashboard!

The Football Dashboard provides comprehensive match predictions with detailed analytics. The accuracy tracking helps you understand prediction performance over time, while the clean interface makes it easy to follow your favorite matches.

**Happy predicting! ⚽📊**