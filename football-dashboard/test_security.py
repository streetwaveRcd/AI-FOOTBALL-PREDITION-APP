#!/usr/bin/env python3
"""
Security Test Script for Football Dashboard
Tests that API keys are properly handled and not hardcoded
"""

import os
import sys
import re

def test_security():
    """Test that no hardcoded API keys or secrets exist"""
    
    print("🔐 SECURITY TEST: Football Dashboard")
    print("=" * 50)
    print()
    
    # Files to check for hardcoded secrets
    files_to_check = [
        'app.py',
        'gpt_predictor.py', 
        'ai_enhanced_predictor.py',
        'web_scraper_predictor.py',
        'football_api.py',
        'start_dashboard.bat',
        'start_dashboard.sh',
        'test_free_predictions.py'
    ]
    
    # Patterns that indicate hardcoded secrets
    dangerous_patterns = [
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI API keys
        r'[a-f0-9]{32}',         # 32-character hex strings (API keys)
        r'Bearer [a-zA-Z0-9]+',   # Bearer tokens
        r'password\s*=\s*["\'][^"\']+["\']',  # Hardcoded passwords
        r'secret\s*=\s*["\'][^"\']+["\']',    # Hardcoded secrets
        r'api_key\s*=\s*["\'][^"\']+["\']',   # Hardcoded API keys (except templates)
    ]
    
    issues_found = []
    files_checked = 0
    
    print("🔍 Scanning files for hardcoded secrets...")
    print()
    
    for filename in files_to_check:
        if not os.path.exists(filename):
            print(f"⚠️  {filename}: File not found (skipping)")
            continue
            
        files_checked += 1
        print(f"🔎 Checking {filename}...")
        
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for i, line in enumerate(content.split('\\n'), 1):
                for pattern in dangerous_patterns:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Skip template values and environment variable examples
                        if any(template in match.lower() for template in [
                            'your_key_here', 'your_api_key', 'example', 'template', 
                            'dummy', 'test', 'placeholder', 'xxx', 'yyy'
                        ]):
                            continue
                        
                        # Skip environment variable usage (this is good!)
                        if 'environ.get' in line or 'os.getenv' in line:
                            continue
                            
                        # Skip comments and documentation
                        if line.strip().startswith('#') or line.strip().startswith('//'):
                            continue
                            
                        issues_found.append({
                            'file': filename,
                            'line': i,
                            'pattern': pattern,
                            'match': match,
                            'full_line': line.strip()
                        })
        
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            continue
    
    print()
    print("📊 RESULTS:")
    print("-" * 30)
    
    if not issues_found:
        print("✅ PASSED: No hardcoded secrets found!")
        print(f"✅ Checked {files_checked} files successfully")
        print()
        print("🔒 SECURITY STATUS: GOOD")
        print("- No hardcoded API keys detected")
        print("- Secrets should be loaded from environment variables")
        print("- .env.example file provides secure template")
        
    else:
        print("❌ FAILED: Hardcoded secrets detected!")
        print()
        for issue in issues_found:
            print(f"🚨 {issue['file']}:{issue['line']}")
            print(f"   Pattern: {issue['pattern']}")
            print(f"   Match: {issue['match']}")
            print(f"   Line: {issue['full_line']}")
            print()
        
        print("🔧 RECOMMENDED ACTIONS:")
        print("1. Replace hardcoded values with os.environ.get('VAR_NAME')")
        print("2. Add sensitive values to .env file (not committed)")
        print("3. Use .env.example as template for required variables")
    
    print()
    print("🛡️  SECURITY CHECKLIST:")
    checklist_items = [
        (".env.example exists", os.path.exists('.env.example')),
        (".gitignore protects .env", '.env' in open('.gitignore', encoding='utf-8', errors='ignore').read() if os.path.exists('.gitignore') else False),
        ("No hardcoded secrets", len(issues_found) == 0),
        ("Environment variable loading", 'load_dotenv' in open('app.py', encoding='utf-8', errors='ignore').read() if os.path.exists('app.py') else False),
    ]
    
    for item, status in checklist_items:
        icon = "✅" if status else "❌"
        print(f"{icon} {item}")
    
    return len(issues_found) == 0

if __name__ == "__main__":
    success = test_security()
    sys.exit(0 if success else 1)