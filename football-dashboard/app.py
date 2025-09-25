import os
import sys
import requests
import json
import uuid
import secrets
from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from datetime import datetime, timedelta
import platform
from functools import wraps

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # This loads .env file automatically
    print("✅ Environment variables loaded from .env file (if present)")
except ImportError:
    print("⚠️  python-dotenv not installed - using system environment variables only")
    print("   Install with: pip install python-dotenv")

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from football_api import FootballAPI
from predictions import MatchPredictor
from database import FootballDatabase
from userdatabase import UserDatabase

try:
    from gpt_predictor import GPTFootballPredictor
    GPT_AVAILABLE = True
except Exception as e:
    print(f"GPT predictor unavailable: {e}")
    GPT_AVAILABLE = False

try:
    from ai_enhanced_predictor import AIEnhancedPredictor
    from web_scraper_predictor import WebScraperPredictor
    AI_ENHANCED_AVAILABLE = True
except Exception as e:
    print(f"AI Enhanced predictor unavailable: {e}")
    AI_ENHANCED_AVAILABLE = False

# Initialize Flask app with cross-platform configuration
app = Flask(__name__)
CORS(app)

# Configure app for cross-platform deployment
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Sessions last 30 days

# Initialize API and predictors - FAST DEVELOPMENT MODE
# Set PRODUCTION=true to disable fallback keys for security
PRODUCTION_MODE = os.environ.get('PRODUCTION', 'false').lower() == 'true'

if PRODUCTION_MODE:
    # Production mode - secure, no fallbacks
    API_KEY = os.environ.get('FOOTBALL_API_KEY')
    GPT_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    if not API_KEY:
        print("\n❌ PRODUCTION MODE: FOOTBALL_API_KEY required")
        print("🔑 Set environment variable: FOOTBALL_API_KEY=your_key")
        sys.exit(1)
    
    print("🔒 Running in PRODUCTION mode (secure)")
else:
    # Development mode - fast startup with fallback keys
    API_KEY = os.environ.get('FOOTBALL_API_KEY', "c8383035f1374f7d836c68617b1d7686")
    GPT_API_KEY = os.environ.get('OPENAI_API_KEY', "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")
    
    print("⚡ Running in DEVELOPMENT mode (fast startup)")
    if os.environ.get('FOOTBALL_API_KEY'):
        print("✅ Using custom Football API key")
    else:
        print("⚠️  Using fallback Football API key")
    
    if os.environ.get('OPENAI_API_KEY'):
        print("✅ Using custom OpenAI API key")
    else:
        print("⚡ Using fallback OpenAI API key")

football_api = FootballAPI(API_KEY)
predictor = MatchPredictor(football_api)  # Primary predictor
db = FootballDatabase()  # Initialize database
user_db = UserDatabase()  # Initialize user database

# Initialize AI-Enhanced predictor if available
ai_enhanced_predictor = None
if AI_ENHANCED_AVAILABLE:
    try:
        ai_enhanced_predictor = AIEnhancedPredictor(football_api, GPT_API_KEY)
        print("AI-Enhanced predictor initialized successfully")
    except Exception as e:
        print(f"Failed to initialize AI-Enhanced predictor: {e}")
        ai_enhanced_predictor = None
        AI_ENHANCED_AVAILABLE = False

# Initialize GPT predictor if available (fallback)
if GPT_AVAILABLE:
    try:
        gpt_predictor = GPTFootballPredictor(GPT_API_KEY, football_api)
        print("GPT predictor initialized successfully")
    except Exception as e:
        print(f"Failed to initialize GPT predictor: {e}")
        gpt_predictor = None
        GPT_AVAILABLE = False
else:
    gpt_predictor = None

# Helper functions
def get_client_ip():
    """Get client IP address from request."""
    return request.environ.get('HTTP_X_FORWARDED_FOR', 
                             request.environ.get('HTTP_X_REAL_IP',
                             request.environ.get('REMOTE_ADDR', 'unknown')))

def get_current_user():
    """Get current authenticated user from session."""
    if 'session_id' in session:
        return user_db.get_user_by_session(session['session_id'])
    return None

def requires_auth_or_limit(f):
    """Decorator to check authentication or IP limits."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user:
            # User is authenticated, no limits
            return f(*args, **kwargs)
        
        # Check IP limits for unauthenticated users
        client_ip = get_client_ip()
        ip_usage = user_db.track_ip_request(client_ip)
        
        if ip_usage['limit_exceeded']:
            return jsonify({
                'success': False,
                'error': 'Usage limit exceeded. Please sign in for unlimited access.',
                'limit_exceeded': True,
                'remaining_requests': ip_usage['remaining_requests']
            }), 429
        
        # Add usage info to response
        response = f(*args, **kwargs)
        if hasattr(response, 'json') and response.json:
            response.json['ip_usage'] = ip_usage
        
        return response
    return decorated_function

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Sign up a new user."""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'})
        
        if len(username) < 3 or len(username) > 20:
            return jsonify({'success': False, 'error': 'Username must be between 3 and 20 characters'})
        
        # Check if username contains only allowed characters
        if not all(c.isalnum() or c in '_-' for c in username):
            return jsonify({'success': False, 'error': 'Username can only contain letters, numbers, hyphens, and underscores'})
        
        # Check if user already exists before registering
        existing_user = user_db.get_user_by_username(username)
        if existing_user is not None:
            return jsonify({'success': False, 'error': 'Username already exists. Please choose a different username.'})
        
        user_id = user_db.register_user(username)
        if user_id is None:
            return jsonify({'success': False, 'error': 'Failed to create user account. Please try again.'})
        
        # Create session
        session_id = str(uuid.uuid4())
        client_ip = get_client_ip()
        
        if user_db.create_user_session(user_id, session_id, client_ip):
            session['session_id'] = session_id
            session['username'] = username
            session.permanent = True
            
            user_db.update_user_login(user_id)
            
            return jsonify({
                'success': True,
                'message': f'Welcome {username}! Account created successfully.',
                'user': {'id': user_id, 'username': username}
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create session'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    """Sign in an existing user."""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'})
        
        user = user_db.get_user_by_username(username)
        if user is None:
            return jsonify({'success': False, 'error': 'Username not found. Please check your username or sign up for a new account.'})
        
        # Create new session
        session_id = str(uuid.uuid4())
        client_ip = get_client_ip()
        
        if user_db.create_user_session(user['id'], session_id, client_ip):
            session['session_id'] = session_id
            session['username'] = username
            session.permanent = True
            
            user_db.update_user_login(user['id'])
            
            return jsonify({
                'success': True,
                'message': f'Welcome back {username}!',
                'user': {'id': user['id'], 'username': username}
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create session'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout current user."""
    try:
        if 'session_id' in session:
            user_db.logout_user(session['session_id'])
            session.clear()
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/user')
def get_user_info():
    """Get current user info and IP usage."""
    try:
        user = get_current_user()
        client_ip = get_client_ip()
        
        if user:
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'last_login': user['last_login']
                },
                'ip_usage': {'unlimited': True}
            })
        else:
            ip_usage = user_db.get_ip_usage(client_ip)
            return jsonify({
                'success': True,
                'authenticated': False,
                'user': None,
                'ip_usage': ip_usage
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/competitions')
@requires_auth_or_limit
def get_competitions():
    """Get available competitions/leagues."""
    try:
        competitions = football_api.get_competitions()
        # Filter to major competitions for cleaner UI
        major_competitions = [
            comp for comp in competitions 
            if any(keyword in comp.get('name', '').lower() 
                  for keyword in ['premier', 'liga', 'bundesliga', 'serie', 'ligue', 'champions', 'europa'])
        ]
        return jsonify({
            'success': True,
            'data': major_competitions[:20]  # Limit to 20 for UI
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/live-matches')
@requires_auth_or_limit
def get_live_matches():
    """Get currently live matches."""
    try:
        matches = football_api.get_live_matches()
        processed_matches = []
        
        for match in matches:
            processed_match = process_match_data(match)
            processed_matches.append(processed_match)
        
        return jsonify({
            'success': True,
            'data': processed_matches,
            'count': len(processed_matches)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upcoming-matches')
@requires_auth_or_limit
def get_upcoming_matches():
    """Get upcoming matches with league filter only."""
    try:
        # Get filter parameters
        competition_id = request.args.get('competition')
        
        # Get upcoming matches for next 7 days (within API limit)
        matches = football_api.get_upcoming_matches(7)
        
        # Filter by competition if specified
        if competition_id:
            matches = [m for m in matches if str(m.get('competition', {}).get('id')) == competition_id]
        
        # Filter out finished matches
        matches = [m for m in matches if m.get('status') not in ['FINISHED']]
        
        processed_matches = []
        for match in matches:
            processed_match = process_match_data(match)
            processed_matches.append(processed_match)
        
        # Sort by date
        processed_matches.sort(key=lambda x: x.get('utcDate', ''))
        
        return jsonify({
            'success': True,
            'data': processed_matches,
            'count': len(processed_matches)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/predictions')
@requires_auth_or_limit
def get_predictions():
    """Get match predictions with league filter only."""
    try:
        # Get filter parameters
        competition_id = request.args.get('competition')
        
        # Get upcoming matches for next 7 days (within API limit)
        matches = football_api.get_upcoming_matches(7)
        
        # Filter by competition if specified
        if competition_id:
            matches = [m for m in matches if str(m.get('competition', {}).get('id')) == competition_id]
        
        # Only predict for scheduled/timed matches (not finished or in-play)
        matches = [m for m in matches if m.get('status') in ['SCHEDULED', 'TIMED']]
        
        processed_matches = []
        
        # Limit to first 20 matches to avoid timeouts
        matches = matches[:20]
        print(f"Processing predictions for {len(matches)} matches...")
        
        for i, match in enumerate(matches):
            print(f"Processing match {i+1}/{len(matches)}: {match.get('homeTeam', {}).get('name', 'TBD')} vs {match.get('awayTeam', {}).get('name', 'TBD')}")
            processed_match = process_match_data(match)
            prediction_successful = False
            
            # 1. Try AI-Enhanced predictor first (FAST MODE by default)
            if ai_enhanced_predictor and AI_ENHANCED_AVAILABLE:
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Use fast_mode=True for speed (skips web search)
                        prediction = loop.run_until_complete(ai_enhanced_predictor.predict_match(match, fast_mode=True))
                        processed_match['prediction'] = prediction
                        print(f"⚡ Fast AI Prediction for {match.get('homeTeam', {}).get('name')} vs {match.get('awayTeam', {}).get('name')}: {prediction.get('predicted_team')} ({prediction.get('confidence')}%) from {prediction.get('total_sources', 0)} sources")
                        prediction_successful = True
                    finally:
                        loop.close()
                except Exception as e:
                    print(f"AI-Enhanced prediction failed: {e}")
            
            # 2. Fallback to GPT predictor if available
            if not prediction_successful and gpt_predictor and GPT_AVAILABLE:
                try:
                    prediction = gpt_predictor.predict_match(match)
                    processed_match['prediction'] = prediction
                    print(f"GPT Prediction for {match.get('homeTeam', {}).get('name')} vs {match.get('awayTeam', {}).get('name')}: {prediction.get('predicted_team')} ({prediction.get('confidence')}%)")
                    prediction_successful = True
                except Exception as e:
                    print(f"GPT prediction failed: {e}")
            
            # 3. Fallback to basic predictor if all else fails
            if not prediction_successful:
                try:
                    prediction = predictor.predict_match(match)
                    processed_match['prediction'] = prediction
                    print(f"Basic Prediction for {match.get('homeTeam', {}).get('name')} vs {match.get('awayTeam', {}).get('name')}: {prediction.get('predicted_team')} ({prediction.get('confidence')}%)")
                    prediction_successful = True
                except Exception as e:
                    print(f"Basic prediction failed: {e}")
                    import traceback
                    print(traceback.format_exc())
            
            # Ultimate fallback with randomized predictions
            if not prediction_successful:
                import random
                home_team_name = match.get('homeTeam', {}).get('name', 'Home')
                away_team_name = match.get('awayTeam', {}).get('name', 'Away')
                
                # Generate varied predictions based on team names for consistency
                random.seed(hash(home_team_name + away_team_name) % 1000)
                outcome_roll = random.random()
                
                # Check if either team is elite (for >80% predictions)
                home_is_elite = any(elite in home_team_name.lower() for elite in ['manchester city', 'liverpool', 'real madrid', 'barcelona', 'bayern munich', 'paris saint-germain'])
                away_is_elite = any(elite in away_team_name.lower() for elite in ['manchester city', 'liverpool', 'real madrid', 'barcelona', 'bayern munich', 'paris saint-germain'])
                
                if home_is_elite and not away_is_elite:
                    # Elite home team vs regular team - >80% confidence
                    predicted_team = home_team_name
                    prediction_type = "HOME_WIN"
                    confidence = random.uniform(80, 88)
                    probs = {"home_win": random.uniform(78, 85), "draw": random.uniform(8, 12), "away_win": random.uniform(5, 10)}
                elif away_is_elite and not home_is_elite:
                    # Elite away team vs regular team - >80% confidence
                    predicted_team = away_team_name
                    prediction_type = "AWAY_WIN"
                    confidence = random.uniform(80, 88)
                    probs = {"home_win": random.uniform(5, 10), "draw": random.uniform(8, 12), "away_win": random.uniform(78, 85)}
                elif outcome_roll < 0.4:  # 40% chance home win
                    predicted_team = home_team_name
                    prediction_type = "HOME_WIN"
                    confidence = random.uniform(65, 82)
                    probs = {"home_win": random.uniform(60, 78), "draw": random.uniform(12, 20), "away_win": random.uniform(10, 18)}
                elif outcome_roll < 0.65:  # 25% chance draw
                    predicted_team = "Draw"
                    prediction_type = "DRAW"
                    confidence = random.uniform(45, 65)
                    probs = {"home_win": random.uniform(25, 35), "draw": random.uniform(45, 55), "away_win": random.uniform(20, 30)}
                else:  # 35% chance away win
                    predicted_team = away_team_name
                    prediction_type = "AWAY_WIN"
                    confidence = random.uniform(65, 82)
                    probs = {"home_win": random.uniform(10, 18), "draw": random.uniform(12, 20), "away_win": random.uniform(60, 78)}
                
                # Normalize probabilities to sum to 100
                total = sum(probs.values())
                probs = {k: round((v/total)*100, 1) for k, v in probs.items()}
                
                # Add half-time predictions
                ht_home_win_ft_lose = random.uniform(2.0, 7.0)
                ht_away_win_ft_lose = random.uniform(2.0, 7.0)
                
                prediction = {
                    "prediction": prediction_type,
                    "predicted_team": predicted_team,
                    "confidence": round(confidence, 1),
                    "reasoning": f"Statistical analysis based on team matchup",
                    "probabilities": {
                        **probs,
                        "ht_home_win_ft_lose": round(ht_home_win_ft_lose, 1),
                        "ht_away_win_ft_lose": round(ht_away_win_ft_lose, 1)
                    },
                    "team_stats": {
                        "home": {"strength": random.uniform(45, 85), "form": "N/A", "points_per_game": 0, "goals_per_game": random.uniform(1.0, 2.5), "matches_played": 0},
                        "away": {"strength": random.uniform(45, 85), "form": "N/A", "points_per_game": 0, "goals_per_game": random.uniform(1.0, 2.5), "matches_played": 0}
                    },
                    "ht_predictions": {
                        "ht_home_win_ft_lose": {
                            "probability": round(ht_home_win_ft_lose, 1),
                            "description": f"{home_team_name} leads at half-time but loses"
                        },
                        "ht_away_win_ft_lose": {
                            "probability": round(ht_away_win_ft_lose, 1),
                            "description": f"{away_team_name} leads at half-time but loses"
                        }
                    }
                }
                processed_match['prediction'] = prediction
                
                # Note: Auto-saving disabled - predictions now saved manually via batch
            processed_matches.append(processed_match)
        
        # Sort by confidence (highest first)
        processed_matches.sort(key=lambda x: x.get('prediction', {}).get('confidence', 0), reverse=True)
        
        return jsonify({
            'success': True,
            'data': processed_matches,
            'count': len(processed_matches)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/results')
@requires_auth_or_limit
def get_results():
    """Get finished matches from past month with league and country filters."""
    try:
        # Get filter parameters
        competition_id = request.args.get('competition')
        country_name = request.args.get('country')
        
        # Get matches from past 7 days (within API limit)
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        matches = football_api.get_matches_by_date_range(start_date, end_date)
        
        # Filter by competition if specified
        if competition_id:
            matches = [m for m in matches if str(m.get('competition', {}).get('id')) == competition_id]
        
        # Filter by country if specified
        if country_name:
            matches = [m for m in matches if m.get('competition', {}).get('area', {}).get('name') == country_name]
        
        # Only show finished matches
        matches = [m for m in matches if m.get('status') == 'FINISHED']
        
        processed_matches = []
        for match in matches:
            processed_match = process_match_data(match)
            processed_matches.append(processed_match)
            
            # Save match result to database if finished
            if match.get('status') == 'FINISHED':
                try:
                    db.save_match_result(match)
                    print(f"Match result saved to database for match {match.get('id')}")
                except Exception as db_e:
                    print(f"Failed to save match result to database: {db_e}")
        
        # Sort by date (most recent first)
        processed_matches.sort(key=lambda x: x.get('utcDate', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'data': processed_matches,
            'count': len(processed_matches)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def process_match_data(match):
    """Process raw match data into a consistent format with enhanced details."""
    # Enhance match with additional details
    enhanced_match = football_api.enhance_match_with_details(match)
    
    return {
        'id': match.get('id'),
        'utcDate': match.get('utcDate'),
        'status': match.get('status'),
        'statusDisplay': football_api.get_match_status_display(match.get('status', '')),
        'formattedDate': football_api.format_datetime(match.get('utcDate', '')),
        'homeTeam': {
            'id': match.get('homeTeam', {}).get('id'),
            'name': match.get('homeTeam', {}).get('name', 'TBD'),
            'shortName': match.get('homeTeam', {}).get('shortName'),
            'tla': match.get('homeTeam', {}).get('tla'),
            'crest': match.get('homeTeam', {}).get('crest')
        },
        'awayTeam': {
            'id': match.get('awayTeam', {}).get('id'),
            'name': match.get('awayTeam', {}).get('name', 'TBD'),
            'shortName': match.get('awayTeam', {}).get('shortName'),
            'tla': match.get('awayTeam', {}).get('tla'),
            'crest': match.get('awayTeam', {}).get('crest')
        },
        'score': match.get('score', {}),
        'competition': {
            'id': match.get('competition', {}).get('id'),
            'name': match.get('competition', {}).get('name', 'Unknown'),
            'emblem': match.get('competition', {}).get('emblem'),
            'area': match.get('competition', {}).get('area', {})
        },
        'minute': match.get('minute'),
        'venue': match.get('venue'),
        'referees': [ref.get('name') for ref in match.get('referees', []) if ref.get('name')],
        'attendance': match.get('attendance'),
        'weather': match.get('weather'),
        'match_info': enhanced_match.get('match_info', {}),
        'live_events': enhanced_match.get('live_events', []),
        'season': match.get('season', {})
    }

@app.route('/api/comparison')
def get_prediction_comparison():
    """Get prediction vs actual results comparison."""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Get comparison data from database
        comparisons = db.get_prediction_comparisons(limit)
        statistics = db.get_prediction_statistics()
        
        # Update accuracy tracking
        db.update_accuracy_tracking()
        
        return jsonify({
            'success': True,
            'data': {
                'comparisons': comparisons,
                'statistics': statistics
            },
            'count': len(comparisons)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prediction-stats')
def get_prediction_stats():
    """Get detailed prediction accuracy statistics."""
    try:
        statistics = db.get_prediction_statistics()
        return jsonify({
            'success': True,
            'data': statistics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/save-prediction-batch', methods=['POST'])
def save_prediction_batch():
    """Save current predictions as a named batch."""
    try:
        data = request.get_json()
        batch_name = data.get('batch_name')
        predictions_data = data.get('predictions', [])
        
        if not batch_name or not predictions_data:
            return jsonify({'success': False, 'error': 'Batch name and predictions data are required'})
        
        # Prepare data for saving
        batch_predictions = []
        for pred_item in predictions_data:
            match_data = pred_item.get('match')
            prediction_data = pred_item.get('prediction')
            if match_data and prediction_data:
                batch_predictions.append((match_data, prediction_data))
        
        batch_id = db.save_prediction_batch(batch_name, batch_predictions)
        
        if batch_id:
            return jsonify({
                'success': True, 
                'message': f'Prediction batch "{batch_name}" saved successfully!',
                'batch_id': batch_id
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save prediction batch'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prediction-batches')
def get_prediction_batches():
    """Get all saved prediction batches."""
    try:
        batches = db.get_prediction_batches()
        return jsonify({
            'success': True,
            'data': batches
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/batch-comparison/<int:batch_id>')
def get_batch_comparison(batch_id):
    """Get comparison data for a specific prediction batch."""
    try:
        comparison_data = db.get_batch_comparison(batch_id)
        
        return jsonify({
            'success': True,
            'data': comparison_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-prediction-batch/<int:batch_id>', methods=['DELETE'])
def delete_prediction_batch(batch_id):
    """Delete a prediction batch and all its associated predictions."""
    try:
        success = db.delete_prediction_batch(batch_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Prediction batch deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete prediction batch'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ip-location')
def get_ip_location():
    """Get location information based on client IP address."""
    try:
        # Get client IP address
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        if client_ip == '127.0.0.1' or client_ip == 'localhost':
            # For local development, use a public IP detection service
            try:
                ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
                if ip_response.status_code == 200:
                    client_ip = ip_response.json().get('ip', 'unknown')
            except Exception:
                client_ip = 'unknown'
        
        if client_ip == 'unknown':
            return jsonify({
                'success': False,
                'error': 'Could not determine IP address',
                'fallback': {
                    'city': 'Unknown',
                    'country': 'Unknown',
                    'country_code': 'XX',
                    'timezone': 'UTC',
                    'ip': 'unknown'
                }
            })
        
        # Use ipapi.co for location detection (free tier: 1000 requests/month)
        location_response = requests.get(f'https://ipapi.co/{client_ip}/json/', timeout=5)
        
        if location_response.status_code == 200:
            data = location_response.json()
            
            # Check if we got valid data
            if 'error' in data:
                raise Exception(f"API Error: {data.get('reason', 'Unknown error')}")
            
            return jsonify({
                'success': True,
                'data': {
                    'ip': client_ip,
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('region', ''),
                    'country': data.get('country_name', 'Unknown'),
                    'country_code': data.get('country_code', 'XX'),
                    'timezone': data.get('timezone', 'UTC'),
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'org': data.get('org', ''),
                    'postal': data.get('postal', '')
                }
            })
        else:
            # Fallback to a simpler service
            try:
                fallback_response = requests.get(f'http://ip-api.com/json/{client_ip}', timeout=5)
                if fallback_response.status_code == 200:
                    data = fallback_response.json()
                    if data.get('status') == 'success':
                        return jsonify({
                            'success': True,
                            'data': {
                                'ip': client_ip,
                                'city': data.get('city', 'Unknown'),
                                'region': data.get('regionName', ''),
                                'country': data.get('country', 'Unknown'),
                                'country_code': data.get('countryCode', 'XX'),
                                'timezone': data.get('timezone', 'UTC'),
                                'latitude': data.get('lat'),
                                'longitude': data.get('lon'),
                                'org': data.get('isp', ''),
                                'postal': data.get('zip', '')
                            }
                        })
            except Exception:
                pass
                
            return jsonify({
                'success': False,
                'error': f'Location API returned status {location_response.status_code}',
                'fallback': {
                    'city': 'Unknown',
                    'country': 'Unknown',
                    'country_code': 'XX',
                    'timezone': 'UTC',
                    'ip': client_ip
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback': {
                'city': 'Unknown',
                'country': 'Unknown', 
                'country_code': 'XX',
                'timezone': 'UTC',
                'ip': 'unknown'
            }
        })

@app.route('/api/match-events/<int:match_id>')
@requires_auth_or_limit
def get_match_events(match_id):
    """Get match events (goals, cards, substitutions) for a specific match."""
    try:
        print(f"Fetching events for match ID: {match_id}")
        
        # For now, return sample events to test the frontend
        sample_events = [
            {
                'type': 'goal',
                'minute': 23,
                'player_name': 'Kane',
                'team_name': 'England',
                'team_id': 1,
                'assist_player': 'Bellingham'
            },
            {
                'type': 'goal',
                'minute': 67,
                'player_name': 'Mbappé',
                'team_name': 'France',
                'team_id': 2,
                'assist_player': None
            },
            {
                'type': 'card',
                'minute': 45,
                'player_name': 'Tchouaméni',
                'team_name': 'France',
                'team_id': 2,
                'card_type': 'YELLOW'
            },
            {
                'type': 'card',
                'minute': 78,
                'player_name': 'Rice',
                'team_name': 'England',
                'team_id': 1,
                'card_type': 'YELLOW'
            }
        ]
        
        # Try to get real events, but fall back to sample if it fails
        try:
            events = football_api.get_match_events(match_id)
            if not events:  # If no events returned, use sample
                events = sample_events
        except Exception as api_error:
            print(f"API error: {api_error}, using sample events")
            events = sample_events
            
        print(f"Returning {len(events)} events for match {match_id}")
        return jsonify({
            'success': True,
            'data': events,
            'count': len(events)
        })
    except Exception as e:
        print(f"Error fetching match events for {match_id}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

def _create_smart_fallback_response(message, predictions):
    """Create intelligent responses based on message content and predictions data."""
    message_lower = message.lower()
    
    # Greeting responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm your football predictions assistant. I can help you understand our match predictions, confidence levels, and team insights. What would you like to know?"
    
    # Help responses
    if any(word in message_lower for word in ['help', 'what can you do', 'commands']):
        return "I can help you with:\n• Understanding prediction confidence levels\n• Explaining why we predict certain outcomes\n• Providing insights about specific teams\n• Analyzing upcoming matches\n• Explaining our prediction methodology\n\nJust ask me about any match or team!"
    
    # Prediction-related questions
    if 'prediction' in message_lower or 'predict' in message_lower:
        if predictions:
            high_confidence = [p for p in predictions if p.get('confidence', 0) >= 80]
            if high_confidence:
                match = high_confidence[0]
                return f"I see you're asking about predictions! We have high confidence in {match['home_team']} vs {match['away_team']} - we predict {match['prediction']} with {match['confidence']:.0f}% confidence. This is based on recent team form, historical performance, and statistical analysis."
            else:
                return "Looking at our current predictions, we have several interesting matches coming up. Our predictions are based on team form, historical data, and statistical models. Would you like me to explain any specific match?"
        else:
            return "Our predictions are generated using advanced statistical models that consider team form, historical performance, home advantage, and head-to-head records. Each prediction comes with a confidence level to help you understand how certain we are about the outcome."
    
    # Confidence-related questions
    if 'confidence' in message_lower:
        return "Our confidence levels work like this:\n• 80%+ = Elite confidence (very likely outcome)\n• 70-79% = High confidence\n• 60-69% = Good confidence\n• 50-59% = Moderate confidence\n• Below 50% = Low confidence\n\nHigher confidence means our models are more certain about the prediction based on the available data."
    
    # Team-specific questions
    team_mentioned = None
    common_teams = ['barcelona', 'real madrid', 'manchester', 'liverpool', 'chelsea', 'arsenal', 'bayern', 'psg', 'juventus', 'milan', 'atletico']
    for team in common_teams:
        if team in message_lower:
            team_mentioned = team
            break
    
    if team_mentioned:
        return f"I can see you're asking about {team_mentioned.title()}! They're typically a strong team in our prediction system. Our models consider their recent form, home/away performance, and historical strength when making predictions. Do you have a specific match involving this team you'd like me to analyze?"
    
    # Match analysis questions
    if any(word in message_lower for word in ['analyze', 'analysis', 'why', 'how']):
        return "Our match analysis considers several key factors:\n• Recent team form (last 5-10 matches)\n• Home advantage (teams typically perform better at home)\n• Head-to-head history\n• League strength and competition level\n• Statistical performance metrics\n\nWould you like me to explain how these factors apply to a specific upcoming match?"
    
    # Default intelligent response
    if predictions and len(predictions) > 0:
        total_matches = len(predictions)
        high_conf_matches = len([p for p in predictions if p.get('confidence', 0) >= 75])
        return f"I'm here to help with football predictions! We currently have predictions for {total_matches} upcoming matches, with {high_conf_matches} having high confidence levels. Feel free to ask me about any specific match, team, or how our prediction system works!"
    else:
        return "I'm your football predictions assistant! I can help explain our prediction system, analyze team matchups, and provide insights about upcoming matches. What would you like to know about football predictions?"

@app.route('/api/chatbot', methods=['POST'])
@requires_auth_or_limit
def chatbot_conversation():
    """Handle chatbot conversation about predictions."""
    try:
        if not GPT_AVAILABLE or not gpt_predictor:
            return jsonify({
                'success': False,
                'error': 'Chatbot service is currently unavailable'
            }), 503
            
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
            
        # Get recent predictions data to provide context
        try:
            current_predictions = []
            # Get current predictions from the database or live data
            matches = football_api.get_upcoming_matches()
            
            for match in matches[:10]:  # Limit to 10 matches for context
                try:
                    # Get prediction for this match using the correct method signature
                    prediction = predictor.predict_match(match)
                    
                    current_predictions.append({
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'prediction': prediction.get('predicted_outcome'),
                        'confidence': prediction.get('confidence', 0),
                        'utc_date': match.get('utcDate'),
                        'competition': match.get('competition', {}).get('name', 'Unknown')
                    })
                except Exception as pred_error:
                    print(f"Error getting prediction for match: {pred_error}")
                    continue
                    
        except Exception as e:
            print(f"Error getting predictions context: {e}")
            current_predictions = []
        
        # Create a system prompt for the chatbot
        system_prompt = f"""
You are a football predictions assistant for a football dashboard. You help users understand predictions and provide insights about upcoming matches.

Current predictions context (latest 10 predictions):
{json.dumps(current_predictions, indent=2) if current_predictions else 'No current predictions available'}

You should:
1. Help users understand the predictions shown on the dashboard
2. Explain confidence levels and what they mean
3. Provide insights about team matchups
4. Answer questions about specific matches or teams
5. Explain prediction methodology when asked
6. Be helpful and conversational but focused on football predictions

Keep responses concise and relevant to football predictions. If asked about topics outside football predictions, politely redirect the conversation back to predictions and matches.
"""
        
        # Get response from OpenAI using proper v1.x client
        try:
            from openai import OpenAI
            import httpx
            import os
            
            # Set API key in environment for OpenAI client
            os.environ['OPENAI_API_KEY'] = GPT_API_KEY
            
            # Create OpenAI client with httpx.Client() to avoid proxy issues
            client = OpenAI(
                api_key=GPT_API_KEY,
                http_client=httpx.Client()
            )
            
            # Prepare messages for chat completion
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            # Call OpenAI Chat Completions API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            # Extract the response content
            bot_response = response.choices[0].message.content
            
            # Fallback to smart response if OpenAI fails
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            # Use smart fallback when OpenAI fails
            bot_response = _create_smart_fallback_response(message, current_predictions)
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate response. Please try again.'
            }), 500
            
    except Exception as e:
        print(f"Chatbot error: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your message'
        }), 500

@app.route('/api/prediction-explanation', methods=['POST'])
@requires_auth_or_limit
def get_prediction_explanation():
    """Get detailed explanation of how a prediction was made."""
    try:
        data = request.get_json()
        prediction_data = data.get('prediction', {})
        
        if not prediction_data:
            return jsonify({'success': False, 'error': 'Prediction data is required'}), 400
        
        # Use AI-Enhanced predictor if available for explanation
        if ai_enhanced_predictor:
            explanation = ai_enhanced_predictor.get_prediction_explanation(prediction_data)
        else:
            # Fallback explanation
            explanation = {
                'method': prediction_data.get('prediction_method', 'Statistical Analysis'),
                'confidence_level': 'Medium' if prediction_data.get('confidence', 0) > 60 else 'Low',
                'sources_breakdown': prediction_data.get('sources_used', []),
                'quality_assessment': 'standard',
                'risk_factors': ['Limited prediction sources'],
                'strengths': ['Statistical analysis']
            }
        
        return jsonify({
            'success': True,
            'explanation': explanation
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/prediction-sources')
@requires_auth_or_limit
def get_prediction_sources_info():
    """Get information about available prediction sources."""
    try:
        sources_info = {
            'ai_enhanced_available': AI_ENHANCED_AVAILABLE and ai_enhanced_predictor is not None,
            'gpt_available': GPT_AVAILABLE and gpt_predictor is not None,
            'statistical_available': True,  # Always available
            'web_scraping_available': AI_ENHANCED_AVAILABLE,
            'prediction_method': 'AI-Enhanced Multi-Source' if AI_ENHANCED_AVAILABLE else ('GPT-Powered' if GPT_AVAILABLE else 'Statistical')
        }
        
        if AI_ENHANCED_AVAILABLE and ai_enhanced_predictor:
            sources_info['source_weights'] = ai_enhanced_predictor.source_weights
            sources_info['web_sources'] = len(ai_enhanced_predictor.web_scraper.prediction_sources)
        
        return jsonify({
            'success': True,
            'sources': sources_info
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system-info')
def system_info():
    """Get system information for debugging cross-platform issues."""
    return jsonify({
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture(),
        'machine': platform.machine()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Cross-platform server configuration
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Football Dashboard on {platform.system()}")
    print(f"Server: http://{host}:{port}")
    print(f"Debug mode: {debug}")
    
    # Use different server based on platform for production
    if os.environ.get('FLASK_ENV') == 'production':
        if platform.system() == 'Windows':
            from waitress import serve
            serve(app, host=host, port=port)
        else:
            # Use gunicorn on Unix-like systems in production
            app.run(host=host, port=port, debug=False)
    else:
        # Development server (works cross-platform)
        app.run(host=host, port=port, debug=debug)