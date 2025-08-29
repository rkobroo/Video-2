#!/usr/bin/env python3
"""
Quick deployment test for Vercel
"""

import json
import os
import sys

def check_vercel_setup():
    """Check if the Vercel setup is correct"""
    print("🔍 Checking Vercel deployment setup...")
    
    errors = []
    warnings = []
    
    # Check vercel.json
    if not os.path.exists('vercel.json'):
        errors.append("Missing vercel.json file")
    else:
        try:
            with open('vercel.json', 'r') as f:
                config = json.load(f)
            
            # Check for required fields
            if 'builds' not in config:
                errors.append("Missing 'builds' in vercel.json")
            
            if 'routes' not in config:
                errors.append("Missing 'routes' in vercel.json")
            
            # Check for conflicting fields
            if 'functions' in config and 'builds' in config:
                warnings.append("Both 'functions' and 'builds' present - should use only one")
                
        except json.JSONDecodeError:
            errors.append("Invalid JSON in vercel.json")
    
    # Check API structure
    if not os.path.exists('api/index.py'):
        errors.append("Missing api/index.py file")
    
    # Check requirements
    if not os.path.exists('api/requirements.txt'):
        warnings.append("Missing api/requirements.txt - may cause dependency issues")
    
    # Check runtime
    if not os.path.exists('runtime.txt'):
        warnings.append("Missing runtime.txt - Python version may not be specified")
    
    # Print results
    if errors:
        print("❌ Errors found:")
        for error in errors:
            print(f"   - {error}")
    
    if warnings:
        print("⚠️  Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
    
    if not errors and not warnings:
        print("✅ Setup looks good!")
    elif not errors:
        print("✅ Setup is functional with minor warnings")
    else:
        print("❌ Setup has critical errors")
        return False
    
    return True

def main():
    print("🚀 Vercel Deployment Checker")
    print("=" * 40)
    
    if check_vercel_setup():
        print("\n📝 Deployment ready!")
        print("   1. Make sure all files are committed to git")
        print("   2. Push to GitHub")
        print("   3. Deploy on Vercel")
    else:
        print("\n❌ Fix errors before deploying")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())