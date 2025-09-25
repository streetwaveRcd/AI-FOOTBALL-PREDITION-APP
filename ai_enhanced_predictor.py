"""
AI-Enhanced Football Predictor
Combines multiple prediction sources including web scraping, statistical analysis, and AI reasoning
"""

import json
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics
import numpy as np
from dataclasses import dataclass

# Import our modules
from web_scraper_predictor import WebScraperPredictor
from predictions import MatchPredictor

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

@dataclass
class PredictionSource:
    """Data class for prediction sources"""
    name: str
    prediction: str
    confidence: float
    reliability: float
    reasoning: str
    source_type: str  # 'web', 'statistical', 'ai', 'expert'

class AIEnhancedPredictor:
    """
    Advanced prediction system that combines:
    1. Web scraped predictions from multiple sources
    2. Statistical analysis from historical data
    3. AI-powered analysis and reasoning
    4. Expert system rules
    """
    
    def __init__(self, football_api=None, openai_api_key: str = None):
        self.football_api = football_api
        self.openai_api_key = openai_api_key
        
        # Initialize sub-predictors
        self.web_scraper = WebScraperPredictor(openai_api_key)
        self.statistical_predictor = MatchPredictor(football_api)
        
        # Initialize OpenAI client
        self.openai_client = None
        if openai_api_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
        
        # Prediction weights for different sources
        self.source_weights = {
            'web_aggregated': 0.35,     # Web scraped predictions
            'statistical': 0.25,       # Statistical analysis
            'ai_analysis': 0.30,       # AI reasoning
            'expert_rules': 0.10       # Expert system rules
        }
        
        # Cache for expensive operations
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
        
    async def predict_match(self, match: Dict, fast_mode: bool = True) -> Dict:
        """
        Main prediction method that combines all sources
        fast_mode: If True, skips web scraping for speed (default True)
        """
        home_team = match.get('homeTeam', {}).get('name', 'Unknown')
        away_team = match.get('awayTeam', {}).get('name', 'Unknown')
        match_date = match.get('utcDate', '')
        competition = match.get('competition', {}).get('name', '')
        
        if fast_mode:
            print(f"⚡ Fast AI prediction for {home_team} vs {away_team}")
        else:
            print(f"🔍 Full AI-Enhanced prediction for {home_team} vs {away_team}")
        
        # Cache key
        cache_key = f"ai_enhanced_{home_team}_{away_team}_{match_date}_{fast_mode}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.cache_duration:
                print("📋 Returning cached prediction")
                return cached_result['data']
        
        # Collect predictions from all sources
        all_sources = []
        
        # 1. Web scraped predictions (skip in fast mode)
        if not fast_mode:
            print("🌐 Gathering web predictions...")
            try:
                web_prediction = await self._get_web_prediction(match)
                if web_prediction:
                    all_sources.append(PredictionSource(
                        name="Web Aggregation",
                        prediction=web_prediction['prediction'],
                        confidence=web_prediction['confidence'],
                        reliability=0.8 if web_prediction.get('sources_analyzed', 0) > 2 else 0.6,
                        reasoning=web_prediction.get('reasoning', ''),
                        source_type='web'
                    ))
            except Exception as e:
                print(f"Web prediction error: {e}")
        else:
            print("⚡ Skipping web search for speed")
        
        # 2. Statistical analysis
        print("📊 Running statistical analysis...")
        try:
            statistical_prediction = self.statistical_predictor.predict_match(match)
            all_sources.append(PredictionSource(
                name="Statistical Analysis",
                prediction=statistical_prediction['prediction'],
                confidence=statistical_prediction['confidence'],
                reliability=0.7,
                reasoning=statistical_prediction.get('reasoning', ''),
                source_type='statistical'
            ))
        except Exception as e:
            print(f"Statistical prediction error: {e}")
        
        # 3. AI-powered analysis
        print("🤖 Running AI analysis...")
        try:
            ai_prediction = await self._get_ai_analysis(match, all_sources)
            if ai_prediction:
                all_sources.append(PredictionSource(
                    name="AI Analysis",
                    prediction=ai_prediction['prediction'],
                    confidence=ai_prediction['confidence'],
                    reliability=0.85,
                    reasoning=ai_prediction.get('reasoning', ''),
                    source_type='ai'
                ))
        except Exception as e:
            print(f"AI analysis error: {e}")
        
        # 4. Expert system rules
        print("🧠 Applying expert rules...")
        try:
            expert_prediction = self._apply_expert_rules(match, all_sources)
            if expert_prediction:
                all_sources.append(expert_prediction)
        except Exception as e:
            print(f"Expert rules error: {e}")
        
        # 5. Combine all predictions using weighted ensemble
        print("⚖️ Combining all predictions...")
        final_prediction = self._combine_predictions(all_sources, match)
        
        # Add metadata about sources
        final_prediction['sources_used'] = [
            {
                'name': source.name,
                'type': source.source_type,
                'prediction': source.prediction,
                'confidence': source.confidence,
                'reliability': source.reliability
            } for source in all_sources
        ]
        
        final_prediction['prediction_method'] = 'AI-Enhanced Multi-Source'
        final_prediction['total_sources'] = len(all_sources)
        
        # Cache the result
        self.cache[cache_key] = {
            'data': final_prediction,
            'timestamp': time.time()
        }
        
        print(f"✅ Final prediction: {final_prediction['predicted_team']} ({final_prediction['confidence']}%)")
        return final_prediction
    
    async def _get_web_prediction(self, match: Dict) -> Optional[Dict]:
        """Get prediction from web scraping"""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.web_scraper.predict_match, match),
                timeout=30  # 30 second timeout
            )
        except Exception as e:
            print(f"Web scraping timeout/error: {e}")
            return None
    
    async def _get_ai_analysis(self, match: Dict, existing_sources: List[PredictionSource]) -> Optional[Dict]:
        """Get AI-powered prediction analysis"""
        if not self.openai_client:
            return None
        
        home_team = match.get('homeTeam', {}).get('name', 'Unknown')
        away_team = match.get('awayTeam', {}).get('name', 'Unknown')
        competition = match.get('competition', {}).get('name', '')
        match_date = match.get('utcDate', '')
        
        # Prepare context from existing sources
        sources_context = []
        for source in existing_sources:
            sources_context.append(
                f"- {source.name}: {source.prediction} ({source.confidence}%) - {source.reasoning[:100]}"
            )
        
        sources_summary = "\n".join(sources_context) if sources_context else "No previous sources available"
        
        # Create comprehensive AI prompt
        prompt = f"""
        As an expert football analyst, analyze this match and provide a detailed prediction:
        
        MATCH: {home_team} vs {away_team}
        COMPETITION: {competition}
        DATE: {match_date}
        
        EXISTING PREDICTIONS:
        {sources_summary}
        
        Please analyze considering:
        1. Recent team form and performance trends
        2. Head-to-head history and playing styles
        3. Home advantage and venue factors
        4. Player injuries/suspensions (if relevant to team names)
        5. Competition importance and context
        6. Seasonal timing (start, mid, end of season)
        7. Analysis of existing predictions for consistency
        
        Provide your prediction in this JSON format:
        {{
            "prediction": "HOME_WIN" | "AWAY_WIN" | "DRAW",
            "predicted_team": "team name or Draw",
            "confidence": numeric_value_0_to_100,
            "probabilities": {{
                "home_win": percentage,
                "draw": percentage,
                "away_win": percentage
            }},
            "reasoning": "detailed explanation of your analysis",
            "key_factors": ["factor1", "factor2", "factor3"],
            "risk_assessment": "low/medium/high risk prediction",
            "alternative_scenarios": ["scenario1", "scenario2"]
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a world-class football analyst with deep knowledge of teams, tactics, and match prediction. Provide detailed, data-driven analysis."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse the AI response
            ai_content = response.choices[0].message.content
            
            # Extract JSON from response
            start_idx = ai_content.find('{')
            end_idx = ai_content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = ai_content[start_idx:end_idx]
                ai_analysis = json.loads(json_str)
                
                # Validate and return
                if all(key in ai_analysis for key in ['prediction', 'predicted_team', 'confidence']):
                    return ai_analysis
            
        except Exception as e:
            print(f"AI analysis error: {e}")
        
        return None
    
    def _apply_expert_rules(self, match: Dict, existing_sources: List[PredictionSource]) -> Optional[PredictionSource]:
        """Apply expert system rules based on match context"""
        home_team = match.get('homeTeam', {}).get('name', '').lower()
        away_team = match.get('awayTeam', {}).get('name', '').lower()
        competition = match.get('competition', {}).get('name', '').lower()
        
        # Elite team advantage rules
        elite_teams = [
            'manchester city', 'liverpool', 'real madrid', 'barcelona', 
            'bayern munich', 'paris saint-germain', 'arsenal', 'chelsea'
        ]
        
        home_is_elite = any(elite in home_team for elite in elite_teams)
        away_is_elite = any(elite in away_team for elite in elite_teams)
        
        # Competition importance rules
        high_importance = any(comp in competition for comp in [
            'champions league', 'europa league', 'premier league', 'la liga', 'serie a'
        ])
        
        # Apply rules
        if home_is_elite and not away_is_elite:
            return PredictionSource(
                name="Expert Rules",
                prediction="HOME_WIN",
                confidence=82.0,
                reliability=0.75,
                reasoning=f"{home_team.title()} is an elite team with significant advantage at home",
                source_type='expert'
            )
        elif away_is_elite and not home_is_elite:
            return PredictionSource(
                name="Expert Rules",
                prediction="AWAY_WIN",
                confidence=75.0,
                reliability=0.75,
                reasoning=f"{away_team.title()} is an elite team, but away form can be challenging",
                source_type='expert'
            )
        elif high_importance and len(existing_sources) > 2:
            # In high-importance matches, favor the consensus
            predictions = [s.prediction for s in existing_sources]
            if predictions.count('HOME_WIN') > len(predictions) // 2:
                return PredictionSource(
                    name="Expert Rules",
                    prediction="HOME_WIN",
                    confidence=70.0,
                    reliability=0.65,
                    reasoning="High-importance match with home consensus",
                    source_type='expert'
                )
        
        return None
    
    def _combine_predictions(self, sources: List[PredictionSource], match: Dict) -> Dict:
        """Combine all prediction sources using weighted ensemble"""
        if not sources:
            return self._create_fallback_prediction(match)
        
        # Weight votes by source reliability and confidence
        weighted_votes = {
            'HOME_WIN': 0.0,
            'AWAY_WIN': 0.0,
            'DRAW': 0.0
        }
        
        total_weight = 0.0
        all_confidences = []
        all_reasonings = []
        
        for source in sources:
            # Calculate source weight
            base_weight = self.source_weights.get(source.source_type, 0.25)
            confidence_modifier = source.confidence / 100.0
            reliability_modifier = source.reliability
            
            final_weight = base_weight * confidence_modifier * reliability_modifier
            
            # Add weighted vote
            if source.prediction in weighted_votes:
                weighted_votes[source.prediction] += final_weight
                total_weight += final_weight
                
                all_confidences.append(source.confidence * reliability_modifier)
                if source.reasoning:
                    all_reasonings.append(f"{source.name}: {source.reasoning}")
        
        # Determine final prediction
        if total_weight == 0:
            return self._create_fallback_prediction(match)
        
        # Normalize votes to probabilities
        home_prob = (weighted_votes['HOME_WIN'] / total_weight) * 100
        away_prob = (weighted_votes['AWAY_WIN'] / total_weight) * 100
        draw_prob = (weighted_votes['DRAW'] / total_weight) * 100
        
        # Final prediction
        if home_prob >= away_prob and home_prob >= draw_prob:
            prediction = 'HOME_WIN'
            predicted_team = match.get('homeTeam', {}).get('name', 'Home')
            confidence = home_prob
        elif away_prob >= home_prob and away_prob >= draw_prob:
            prediction = 'AWAY_WIN'
            predicted_team = match.get('awayTeam', {}).get('name', 'Away')
            confidence = away_prob
        else:
            prediction = 'DRAW'
            predicted_team = 'Draw'
            confidence = draw_prob
        
        # Calculate ensemble confidence (weighted average of source confidences)
        ensemble_confidence = statistics.mean(all_confidences) if all_confidences else confidence
        
        # Boost confidence if multiple sources agree
        agreement_boost = 0
        if len(sources) > 1:
            same_prediction_count = sum(1 for s in sources if s.prediction == prediction)
            agreement_ratio = same_prediction_count / len(sources)
            if agreement_ratio > 0.7:
                agreement_boost = 10 * agreement_ratio
        
        final_confidence = min(95, ensemble_confidence + agreement_boost)
        
        # Combine reasoning from all sources
        combined_reasoning = f"AI-Enhanced analysis from {len(sources)} sources: " + \
                           "; ".join(all_reasonings[:3])  # Top 3 reasonings
        
        return {
            'prediction': prediction,
            'predicted_team': predicted_team,
            'confidence': round(final_confidence, 1),
            'probabilities': {
                'home_win': round(home_prob, 1),
                'draw': round(draw_prob, 1),
                'away_win': round(away_prob, 1)
            },
            'reasoning': combined_reasoning,
            'ensemble_method': 'weighted_voting',
            'agreement_boost': round(agreement_boost, 1),
            'prediction_quality': 'high' if len(sources) >= 3 and agreement_boost > 5 else 'medium'
        }
    
    def _create_fallback_prediction(self, match: Dict) -> Dict:
        """Create fallback prediction when no sources are available"""
        home_team = match.get('homeTeam', {}).get('name', 'Home')
        away_team = match.get('awayTeam', {}).get('name', 'Away')
        
        return {
            'prediction': 'DRAW',
            'predicted_team': 'Draw',
            'confidence': 45.0,
            'probabilities': {
                'home_win': 37.5,
                'draw': 25.0,
                'away_win': 37.5
            },
            'reasoning': 'No reliable prediction sources available - using balanced default',
            'ensemble_method': 'fallback',
            'prediction_quality': 'low',
            'sources_used': [],
            'total_sources': 0
        }

    def get_prediction_explanation(self, prediction: Dict) -> Dict:
        """Generate detailed explanation of how the prediction was made"""
        explanation = {
            'method': prediction.get('prediction_method', 'Unknown'),
            'confidence_level': self._get_confidence_level(prediction.get('confidence', 0)),
            'sources_breakdown': prediction.get('sources_used', []),
            'quality_assessment': prediction.get('prediction_quality', 'unknown'),
            'risk_factors': [],
            'strengths': []
        }
        
        # Assess prediction strengths
        if prediction.get('total_sources', 0) >= 3:
            explanation['strengths'].append('Multiple prediction sources analyzed')
        
        if prediction.get('agreement_boost', 0) > 5:
            explanation['strengths'].append('High agreement between sources')
        
        if any(source.get('type') == 'ai' for source in prediction.get('sources_used', [])):
            explanation['strengths'].append('AI-powered analysis included')
        
        # Assess risk factors
        if prediction.get('confidence', 0) < 60:
            explanation['risk_factors'].append('Low confidence prediction')
        
        if prediction.get('total_sources', 0) < 2:
            explanation['risk_factors'].append('Limited prediction sources')
        
        return explanation
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert numeric confidence to descriptive level"""
        if confidence >= 80:
            return 'Very High'
        elif confidence >= 70:
            return 'High'
        elif confidence >= 60:
            return 'Medium'
        elif confidence >= 50:
            return 'Low'
        else:
            return 'Very Low'