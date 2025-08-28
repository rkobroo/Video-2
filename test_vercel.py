#!/usr/bin/env python3
"""
Test script for Vercel deployment readiness
"""

import os
import json
import sys

def check_vercel_config():
    """Check if Vercel configuration is valid"""
    print("🔍 Checking Vercel configuration...")
    
    # Check vercel.json
    if not os.path.exists('vercel.json'):
        print("   ❌ Missing vercel.json")
        return False
    
    try:
        with open('vercel.json', 'r') as f:
            config = json.load(f)
        print("   ✅ vercel.json is valid JSON")
        
        # Check required fields
        required_fields = ['version', 'builds', 'routes']
        for field in required_fields:
            if field not in config:
                print(f"   ❌ Missing required field: {field}")
                return False
        
        print("   ✅ vercel.json has required fields")
    except json.JSONDecodeError:
        print("   ❌ vercel.json is not valid JSON")
        return False
    
    return True

def check_api_structure():
    """Check API structure for Vercel"""
    print("\n🔍 Checking API structure...")
    
    # Check api directory
    if not os.path.exists('api'):
        print("   ❌ Missing api/ directory")
        return False
    
    # Check api/index.py
    if not os.path.exists('api/index.py'):
        print("   ❌ Missing api/index.py")
        return False
    
    print("   ✅ API structure is correct")
    
    # Check handler export
    try:
        with open('api/index.py', 'r') as f:
            content = f.read()
        
        if 'handler = app' not in content:
            print("   ❌ Missing 'handler = app' export in api/index.py")
            return False
        
        print("   ✅ Handler export found")
    except Exception as e:
        print(f"   ❌ Error reading api/index.py: {e}")
        return False
    
    return True

def check_dependencies():
    """Check if dependencies are Vercel-compatible"""
    print("\n🔍 Checking dependencies...")
    
    # Check requirements-vercel.txt
    if not os.path.exists('requirements-vercel.txt'):
        print("   ❌ Missing requirements-vercel.txt")
        return False
    
    try:
        with open('requirements-vercel.txt', 'r') as f:
            deps = f.read().strip().split('\n')
        
        required_deps = ['fastapi', 'yt-dlp', 'pydantic', 'httpx']
        missing_deps = []
        
        for req_dep in required_deps:
            if not any(req_dep in dep for dep in deps):
                missing_deps.append(req_dep)
        
        if missing_deps:
            print(f"   ❌ Missing dependencies: {', '.join(missing_deps)}")
            return False
        
        print(f"   ✅ Found {len(deps)} dependencies")
        print(f"   ✅ All required dependencies present")
    except Exception as e:
        print(f"   ❌ Error reading requirements-vercel.txt: {e}")
        return False
    
    return True

def check_static_files():
    """Check static files"""
    print("\n🔍 Checking static files...")
    
    if not os.path.exists('static'):
        print("   ❌ Missing static/ directory")
        return False
    
    if not os.path.exists('static/index.html'):
        print("   ❌ Missing static/index.html")
        return False
    
    print("   ✅ Static files present")
    return True

def test_api_import():
    """Test if the API can be imported"""
    print("\n🔍 Testing API import...")
    
    try:
        sys.path.insert(0, 'api')
        import index
        
        if hasattr(index, 'app'):
            print("   ✅ FastAPI app found")
        else:
            print("   ❌ FastAPI app not found")
            return False
            
        if hasattr(index, 'handler'):
            print("   ✅ Handler export found")
        else:
            print("   ❌ Handler export not found")
            return False
            
        print("   ✅ API imports successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all checks"""
    print("🧪 Testing Vercel Deployment Readiness")
    print("=" * 50)
    
    checks = [
        check_vercel_config,
        check_api_structure,
        check_dependencies,
        check_static_files,
        test_api_import
    ]
    
    results = []
    for check in checks:
        results.append(check())
    
    print("\n" + "=" * 50)
    
    if all(results):
        print("✅ All checks passed! Ready for Vercel deployment")
        print("\n📝 Next steps:")
        print("   1. Push your code to GitHub")
        print("   2. Connect your repo to Vercel")
        print("   3. Deploy!")
        print("\n🔗 Deployment guide: VERCEL_DEPLOYMENT.md")
        return 0
    else:
        failed_count = len([r for r in results if not r])
        print(f"❌ {failed_count} check(s) failed")
        print("\n📝 Please fix the issues above before deploying")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)