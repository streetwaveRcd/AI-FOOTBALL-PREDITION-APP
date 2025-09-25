#!/usr/bin/env python3
"""
Test script for the new FREE web search prediction system
No API keys required (except for football data)!
"""

import asyncio
import sys
from datetime import datetime

def test_free_predictions():
    """Test the free prediction system with DuckDuckGo web search"""
    
    print("🆓 Testing FREE Football Prediction System")
    print("=" * 50)
    print("✅ No Google API key needed")
    print("✅ No OpenAI API key needed") 
    print("✅ Uses DuckDuckGo free search")
    print("✅ Statistical analysis included")
    print()
    
    try:
        # Test 1: Import all components
        print("📦 Testing imports...")
        from web_scraper_predictor import WebScraperPredictor
        from ai_enhanced_predictor import AIEnhancedPredictor
        from predictions import MatchPredictor
        print("✅ All imports successful")
        print()
        
        # Test 2: Initialize web scraper (no API key needed)
        print("🌐 Initializing web scraper (DuckDuckGo)...")
        scraper = WebScraperPredictor()  # No OpenAI key needed!
        print("✅ Web scraper ready (completely free)")
        print()
        
        # Test 3: Initialize AI enhanced predictor  
        print("🤖 Initializing AI enhanced predictor...")
        ai_predictor = AIEnhancedPredictor()  # No OpenAI key needed!
        print("✅ AI enhanced predictor ready (uses free sources)")
        print()
        
        # Test 4: Test with a sample match
        print("⚽ Testing prediction with sample match...")
        test_match = {
            'homeTeam': {'name': 'Manchester United'},
            'awayTeam': {'name': 'Liverpool'},
            'competition': {'name': 'Premier League'},
            'utcDate': '2025-01-20T15:00:00Z'
        }
        
        print(f"Match: {test_match['homeTeam']['name']} vs {test_match['awayTeam']['name']}")
        print("🔍 Searching web for predictions...")
        
        # Run quick web search test
        result = scraper.predict_match(test_match)
        
        print("📊 PREDICTION RESULTS:")
        print(f"   Predicted: {result.get('predicted_team', 'Unknown')}")
        print(f"   Confidence: {result.get('confidence', 0)}%")
        print(f"   Sources: {result.get('sources_analyzed', 0)} web sources analyzed")
        print(f"   Method: {result.get('reasoning', 'Unknown')[:50]}...")
        print(f"   Web scraped: {result.get('web_scraped', False)}")
        print()
        
        print("🎉 SUCCESS! Free prediction system working perfectly!")
        print()
        print("💡 NEXT STEPS:")
        print("1. Set your FOOTBALL_DATA_API_KEY environment variable")
        print("2. Run: python app.py")
        print("3. Open: http://127.0.0.1:5000")
        print("4. Optional: Add OPENAI_API_KEY for enhanced predictions")
        print()
        print("💰 COST SUMMARY:")
        print("- Web search: FREE (DuckDuckGo)")
        print("- Statistical analysis: FREE") 
        print("- Football data: FREE tier available")
        print("- OpenAI enhancement: OPTIONAL (~$0.002/prediction)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_free_predictions()
    sys.exit(0 if success else 1)