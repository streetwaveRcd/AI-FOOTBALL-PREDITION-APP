import json
import time
from typing import Dict, List, Optional
from datetime import datetime

try:
    import openai
    # Try to detect OpenAI version and setup compatibility
    if hasattr(openai, 'OpenAI'):
        # New OpenAI client (v1.x)
        OPENAI_NEW_CLIENT = True
    else:
        # Legacy OpenAI client (v0.x)
        OPENAI_NEW_CLIENT = False
except ImportError as e:
    raise ImportError(f"OpenAI package not available: {e}")

class GPTFootballPredictor:
    """
    Enhanced football prediction service using OpenAI GPT API for intelligent match analysis.
    """
    
    def __init__(self, api_key: str, football_api=None):
        self.api_key = api_key
        self.football_api = football_api
        
        # Initialize OpenAI client based on version
        if OPENAI_NEW_CLIENT:
            try:
                # Initialize with minimal parameters for new client
                import os
                os.environ['OPENAI_API_KEY'] = api_key
                
                # Try creating client with just the API key - avoid any potential parameter issues
                self.client = openai.OpenAI(api_key=api_key)
                self.use_new_client = True
                print("OpenAI new client initialized successfully")
            except Exception as e:
                print(f"OpenAI new client init error: {e}")
                # Set up for direct client creation in API calls
                self.client = None
                self.use_new_client = False
                print("Will create OpenAI client per API call")
        else:
            # This branch should not be reached with OpenAI v1.x
            self.client = None
            self.use_new_client = False
            print("Legacy OpenAI client mode (should not be used with v1.x)")
        
        # Cache for GPT predictions to avoid repeated API calls
        self.prediction_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
    def predict_match(self, match: Dict) -> Dict:
        """
        Use GPT to predict match outcome with intelligent analysis.
        """
        home_team = match.get("homeTeam", {}).get("name", "Unknown")
        away_team = match.get("awayTeam", {}).get("name", "Unknown")
        competition = match.get("competition", {}).get("name", "")
        match_date = match.get("utcDate", "")
        
        # Create cache key
        cache_key = f"{home_team}_vs_{away_team}_{match_date}"
        
        # Check cache first
        if cache_key in self.prediction_cache:
            cached_result = self.prediction_cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.cache_duration:
                return cached_result['prediction']
        
        try:
            # Get team statistics if available
            team_stats = self._get_team_context(match)
            
            # Create GPT prompt
            prompt = self._create_prediction_prompt(home_team, away_team, competition, team_stats)
            
            # Call GPT API
            gpt_response = self._call_gpt_api(prompt)
            
            # Parse GPT response into structured prediction
            prediction = self._parse_gpt_response(gpt_response, home_team, away_team)
            
            # Cache the result
            self.prediction_cache[cache_key] = {
                'prediction': prediction,
                'timestamp': time.time()
            }
            
            return prediction
            
        except Exception as e:
            print(f"GPT prediction error: {e}")
            # Fallback to basic prediction
            return self._create_fallback_prediction(home_team, away_team)
    
    def _get_team_context(self, match: Dict) -> Dict:
        """
        Get additional context about the teams if available.
        """
        context = {
            'home_team': match.get("homeTeam", {}).get("name", "Unknown"),
            'away_team': match.get("awayTeam", {}).get("name", "Unknown"),
            'venue': match.get("venue", "Unknown venue"),
            'competition': match.get("competition", {}).get("name", ""),
            'season': match.get("season", {})
        }
        
        # Try to get recent form if available
        if self.football_api:
            try:
                home_team_id = match.get("homeTeam", {}).get("id")
                away_team_id = match.get("awayTeam", {}).get("id")
                
                if home_team_id and away_team_id:
                    home_matches = self.football_api.get_team_recent_matches(home_team_id)
                    away_matches = self.football_api.get_team_recent_matches(away_team_id)
                    
                    if home_matches:
                        home_form = self.football_api.calculate_team_form(home_matches, home_team_id)
                        context['home_form'] = home_form
                    
                    if away_matches:
                        away_form = self.football_api.calculate_team_form(away_matches, away_team_id)
                        context['away_form'] = away_form
                        
            except Exception as e:
                print(f"Error getting team context: {e}")
        
        return context
    
    def _create_prediction_prompt(self, home_team: str, away_team: str, competition: str, team_stats: Dict) -> str:
        """
        Create a detailed prompt for GPT to analyze the match.
        """
        
        # Base prompt
        prompt = f"""You are a professional football analyst. Analyze the upcoming match between {home_team} (home) vs {away_team} (away) in {competition}.

Match Details:
- Home Team: {home_team}
- Away Team: {away_team}
- Competition: {competition}
- Venue: {team_stats.get('venue', 'Unknown')}

"""
        
        # Add team form if available
        if 'home_form' in team_stats:
            home_form = team_stats['home_form']
            prompt += f"""
Home Team Recent Form:
- Wins: {home_form.get('wins', 0)}
- Draws: {home_form.get('draws', 0)}
- Losses: {home_form.get('losses', 0)}
- Goals Scored: {home_form.get('goals_scored', 0)}
- Goals Conceded: {home_form.get('goals_conceded', 0)}
- Points per Game: {home_form.get('points_per_game', 0)}
- Recent Form: {home_form.get('recent_form', 'N/A')}
"""
        
        if 'away_form' in team_stats:
            away_form = team_stats['away_form']
            prompt += f"""
Away Team Recent Form:
- Wins: {away_form.get('wins', 0)}
- Draws: {away_form.get('draws', 0)}
- Losses: {away_form.get('losses', 0)}
- Goals Scored: {away_form.get('goals_scored', 0)}
- Goals Conceded: {away_form.get('goals_conceded', 0)}
- Points per Game: {away_form.get('points_per_game', 0)}
- Recent Form: {away_form.get('recent_form', 'N/A')}
"""
        
        prompt += f"""
Please provide a detailed match prediction in the following JSON format:
{{
    "predicted_winner": "home_team_name" or "away_team_name" or "Draw",
    "confidence": percentage (0-100),
    "home_win_probability": percentage (0-100),
    "draw_probability": percentage (0-100),
    "away_win_probability": percentage (0-100),
    "reasoning": "detailed explanation of your prediction",
    "key_factors": ["factor1", "factor2", "factor3"],
    "predicted_score": "X-Y",
    "match_analysis": "comprehensive analysis of the matchup"
}}

Consider factors like:
- Recent form and momentum
- Head-to-head history
- Home advantage
- Team strengths and weaknesses
- Player injuries/suspensions (if known)
- Competition importance
- Current league position and form

Provide realistic probabilities that add up to 100% and give detailed reasoning for your prediction."""
        
        return prompt
    
    def _call_gpt_api(self, prompt: str) -> str:
        """
        Make API call to OpenAI GPT with version compatibility.
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert football analyst with deep knowledge of teams, players, and match predictions. Provide accurate, data-driven analysis."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            if self.use_new_client and self.client:
                # Use existing client
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            else:
                # Create a fresh client using a clean approach to avoid any proxy issues
                try:
                    # Import httpx to create a clean HTTP client
                    import httpx
                    import os
                    
                    # Set the API key in environment
                    os.environ['OPENAI_API_KEY'] = self.api_key
                    
                    # Create a clean HTTP client without any proxy configuration
                    http_client = httpx.Client()
                    
                    # Create OpenAI client with clean HTTP client
                    temp_client = openai.OpenAI(
                        api_key=self.api_key,
                        http_client=http_client
                    )
                    
                    response = temp_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    # Clean up
                    http_client.close()
                    
                    return response.choices[0].message.content.strip()
                    
                except ImportError:
                    # If httpx is not available, try without it
                    try:
                        temp_client = openai.OpenAI(api_key=self.api_key)
                        response = temp_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=1000
                        )
                        return response.choices[0].message.content.strip()
                    except Exception as final_error:
                        print(f"Final fallback failed: {final_error}")
                        raise final_error
                        
                except Exception as fallback_error:
                    print(f"Clean client creation failed: {fallback_error}")
                    raise fallback_error
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise e
    
    def _parse_gpt_response(self, gpt_response: str, home_team: str, away_team: str) -> Dict:
        """
        Parse GPT response into structured prediction format.
        """
        try:
            # Try to extract JSON from the response
            start_idx = gpt_response.find('{')
            end_idx = gpt_response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = gpt_response[start_idx:end_idx]
                gpt_data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            # Map to our expected format
            predicted_winner = gpt_data.get("predicted_winner", "Draw")
            
            # Determine predicted team name
            if predicted_winner.lower() == "draw":
                predicted_team = "Draw"
            elif home_team.lower() in predicted_winner.lower():
                predicted_team = home_team
            elif away_team.lower() in predicted_winner.lower():
                predicted_team = away_team
            else:
                predicted_team = predicted_winner
            
            return {
                "prediction": "DRAW" if predicted_team == "Draw" else ("HOME_WIN" if predicted_team == home_team else "AWAY_WIN"),
                "predicted_team": predicted_team,
                "confidence": float(gpt_data.get("confidence", 50.0)),
                "reasoning": gpt_data.get("reasoning", "GPT analysis completed"),
                "probabilities": {
                    "home_win": float(gpt_data.get("home_win_probability", 33.3)),
                    "draw": float(gpt_data.get("draw_probability", 33.3)),
                    "away_win": float(gpt_data.get("away_win_probability", 33.3))
                },
                "gpt_analysis": {
                    "key_factors": gpt_data.get("key_factors", []),
                    "predicted_score": gpt_data.get("predicted_score", "1-1"),
                    "match_analysis": gpt_data.get("match_analysis", "Analysis completed"),
                    "source": "OpenAI GPT-3.5-Turbo"
                }
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Error parsing GPT response: {e}")
            # Try to extract basic prediction from text
            return self._parse_text_response(gpt_response, home_team, away_team)
    
    def _parse_text_response(self, text: str, home_team: str, away_team: str) -> Dict:
        """
        Fallback parser for non-JSON GPT responses.
        """
        text_lower = text.lower()
        
        # Simple keyword analysis
        home_mentions = text_lower.count(home_team.lower())
        away_mentions = text_lower.count(away_team.lower())
        draw_mentions = text_lower.count("draw") + text_lower.count("tie")
        
        # Determine prediction based on mentions and keywords
        if "win" in text_lower and home_mentions > away_mentions:
            predicted_team = home_team
            prediction = "HOME_WIN"
            confidence = 65.0
        elif "win" in text_lower and away_mentions > home_mentions:
            predicted_team = away_team
            prediction = "AWAY_WIN"
            confidence = 65.0
        else:
            predicted_team = "Draw"
            prediction = "DRAW"
            confidence = 55.0
        
        return {
            "prediction": prediction,
            "predicted_team": predicted_team,
            "confidence": confidence,
            "reasoning": "GPT analysis (text-based parsing)",
            "probabilities": {
                "home_win": 35.0 if prediction != "HOME_WIN" else 55.0,
                "draw": 30.0,
                "away_win": 35.0 if prediction != "AWAY_WIN" else 55.0
            },
            "gpt_analysis": {
                "key_factors": ["GPT text analysis"],
                "predicted_score": "1-1",
                "match_analysis": text[:200] + "..." if len(text) > 200 else text,
                "source": "OpenAI GPT-3.5-Turbo (text parsing)"
            }
        }
    
    def _create_fallback_prediction(self, home_team: str, away_team: str) -> Dict:
        """
        Create a fallback prediction when GPT API fails.
        """
        return {
            "prediction": "DRAW",
            "predicted_team": "Draw",
            "confidence": 45.0,
            "reasoning": "GPT API unavailable - using fallback prediction",
            "probabilities": {
                "home_win": 35.0,
                "draw": 30.0,
                "away_win": 35.0
            },
            "gpt_analysis": {
                "key_factors": ["API unavailable"],
                "predicted_score": "1-1", 
                "match_analysis": "Unable to perform detailed analysis due to API issues",
                "source": "Fallback prediction"
            }
        }