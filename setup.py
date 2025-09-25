#!/usr/bin/env python3
"""
Quick Setup Script for Football Dashboard
Helps users configure the application securely
"""

import os
import sys
import shutil

def setup_dashboard():
    """Interactive setup for Football Dashboard"""
    
    print("🏈 FOOTBALL DASHBOARD - QUICK SETUP")
    print("=" * 40)
    print()
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled. Edit your existing .env file manually.")
            return
    
    # Copy .env.example to .env if it exists
    if os.path.exists('.env.example'):
        print("📋 Creating .env file from template...")
        shutil.copy('.env.example', '.env')
        print("✅ .env file created")
    else:
        print("❌ .env.example not found")
        return False
    
    print()
    print("🔑 API KEY SETUP:")
    print("Now you need to add your API keys to the .env file")
    print()
    
    # Get Football Data API key
    print("1. FOOTBALL DATA API KEY (Required):")
    print("   - Visit: https://www.football-data.org/client/register")
    print("   - Sign up for a FREE account")
    print("   - Get your API key")
    
    football_key = input("   Enter your Football Data API key: ").strip()
    
    if football_key:
        # Update .env file
        with open('.env', 'r') as f:
            content = f.read()
        
        content = content.replace('your_football_data_api_key_here', football_key)
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print("   ✅ Football Data API key saved")
    else:
        print("   ⚠️  No API key entered - you'll need to add it manually to .env")
    
    print()
    
    # Optional OpenAI API key
    print("2. OPENAI API KEY (Optional):")
    print("   - Only needed for enhanced GPT predictions")
    print("   - Visit: https://platform.openai.com/api-keys")
    print("   - Cost: ~$0.002 per prediction")
    print("   - Leave blank to use FREE web search predictions only")
    
    openai_key = input("   Enter your OpenAI API key (or press Enter to skip): ").strip()
    
    if openai_key:
        with open('.env', 'r') as f:
            content = f.read()
        
        content = content.replace('your_openai_api_key_here', openai_key)
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print("   ✅ OpenAI API key saved")
    else:
        print("   ✅ Skipped - using FREE web search predictions")
    
    print()
    print("🎉 SETUP COMPLETE!")
    print()
    print("📋 NEXT STEPS:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Start the dashboard:")
    if os.name == 'nt':  # Windows
        print("   - Windows: start_dashboard.bat")
    else:  # Unix-like
        print("   - Unix/Linux: ./start_dashboard.sh")
    print("   - Or directly: python app.py")
    print()
    print("3. Open in browser: http://127.0.0.1:5000")
    print()
    print("💰 COST SUMMARY:")
    print("- Football Data API: FREE (10 requests/minute)")
    print("- Web search: FREE (DuckDuckGo)")
    print("- Statistical analysis: FREE")
    if openai_key:
        print("- OpenAI predictions: ~$0.002 per prediction")
    else:
        print("- OpenAI predictions: Not configured (using free alternatives)")
    
    print()
    print("🔒 SECURITY:")
    print("- Your API keys are stored in .env (not committed to git)")
    print("- Never share your .env file")
    print("- The .env.example file shows the required format")
    
    return True

if __name__ == "__main__":
    try:
        success = setup_dashboard()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\\nSetup failed: {e}")
        sys.exit(1)