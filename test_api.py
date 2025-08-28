#!/usr/bin/env python3
"""
Test script for the Social Media Video Downloader API
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_api():
    """Test the main API endpoints"""
    print("🧪 Testing Social Media Video Downloader API...")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("1. Testing server health...")
    try:
        response = requests.get(f"{API_BASE}/")
        if response.status_code == 200:
            print("   ✅ Server is running!")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server. Make sure it's running on port 8000")
        return
    
    # Test 2: Get supported platforms
    print("\n2. Testing supported platforms endpoint...")
    try:
        response = requests.get(f"{API_BASE}/api/platforms")
        if response.status_code == 200:
            platforms = response.json()
            print(f"   ✅ Found {len(platforms['platforms'])} supported platforms:")
            for platform in platforms['platforms'][:3]:  # Show first 3
                print(f"      - {platform['name']} ({platform['domain']})")
            if len(platforms['platforms']) > 3:
                print(f"      ... and {len(platforms['platforms']) - 3} more")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Test video info endpoint (using a sample YouTube video)
    print("\n3. Testing video info endpoint...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing
    
    try:
        response = requests.post(
            f"{API_BASE}/api/video/info",
            json={
                "url": test_url,
                "quality": "best",
                "audio_only": False
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            video_info = response.json()
            print("   ✅ Video info retrieved successfully!")
            print(f"      Title: {video_info.get('title', 'N/A')}")
            print(f"      Uploader: {video_info.get('uploader', 'N/A')}")
            print(f"      Duration: {video_info.get('duration', 'N/A')} seconds")
            print(f"      Formats available: {len(video_info.get('formats', []))}")
        else:
            print(f"   ⚠️  Video info request failed with status {response.status_code}")
            try:
                error_detail = response.json().get('detail', 'No error details')
                print(f"      Error: {error_detail}")
            except:
                print(f"      Raw response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ API testing completed!")
    print("\n📝 Next steps:")
    print("   - Open http://localhost:8000 in your browser")
    print("   - Try downloading a video using the web interface")
    print("   - Check API documentation at http://localhost:8000/docs")

if __name__ == "__main__":
    test_api()