#!/usr/bin/env python3
"""
Test script to verify all Ray Serve deployments are working correctly.
Run this from inside the Ray cluster container.
"""

import requests
import json
import sys

def test_endpoint(url, description):
    """Test an endpoint and return results."""
    try:
        response = requests.get(url, timeout=5)
        print(f"✅ {description}: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def main():
    """Test all endpoints."""
    print("🧪 Testing Ray Serve Deployments")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    tests = [
        (f"{base_url}/", "Root endpoint"),
        (f"{base_url}/health", "Health check"),
        (f"{base_url}/api/algorunner/status", "Algorunner status"),
        (f"{base_url}/api/screener/filters", "Screener filters"),
        (f"{base_url}/api/tickscrawler/sources", "Tickscrawler sources"),
    ]
    
    passed = 0
    total = len(tests)
    
    for url, description in tests:
        if test_endpoint(url, description):
            passed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All services are working correctly!")
        sys.exit(0)
    else:
        print("⚠️  Some services have issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
