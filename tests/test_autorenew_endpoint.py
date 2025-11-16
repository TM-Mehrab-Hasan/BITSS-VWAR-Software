"""
Diagnostic test for Auto-Renew API endpoint
Tests the endpoint directly to identify the 404 issue
"""

import requests
import json
import sys
sys.path.insert(0, '.')

from config import API_AUTO_RENEW, API_AUTO_RENEW_KEY

def test_endpoint():
    print("=" * 80)
    print("AUTO-RENEW ENDPOINT DIAGNOSTIC")
    print("=" * 80)
    
    print(f"\n🔗 Endpoint URL: {API_AUTO_RENEW}")
    print(f"🔑 API Key: {API_AUTO_RENEW_KEY[:20]}...")
    
    # Test 1: Basic connectivity (GET request)
    print("\n" + "─" * 80)
    print("TEST 1: Basic Connectivity (GET)")
    print("─" * 80)
    try:
        response = requests.get(API_AUTO_RENEW, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        if response.status_code == 404:
            print("❌ 404 Not Found - The endpoint URL doesn't exist on the server")
            print("   Possible causes:")
            print("   - File 'autoReNew.php' doesn't exist in /vwar_windows/ directory")
            print("   - Server case-sensitivity issue")
            print("   - Incorrect path configuration")
        else:
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    # Test 2: POST with API Key
    print("\n" + "─" * 80)
    print("TEST 2: POST with Authentication")
    print("─" * 80)
    
    payload = {
        "id": "test_123",
        "auto_renew": "YES"
    }
    
    headers = {
        "API-Key": API_AUTO_RENEW_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.post(API_AUTO_RENEW, json=payload, headers=headers, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 404:
            print("\n❌ 404 Not Found")
            print("   The endpoint doesn't exist. Please check:")
            print(f"   1. File exists: https://bitts.fr/vwar_windows/autoReNew.php")
            print("   2. File name spelling (case-sensitive)")
            print("   3. Directory path is correct")
        elif response.status_code == 200:
            print(f"\n✅ Success! Response:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
        else:
            print(f"\n⚠️  Unexpected Status: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Request Error: {e}")
    
    # Test 3: Alternative URLs to try
    print("\n" + "─" * 80)
    print("TEST 3: Alternative URLs to Check")
    print("─" * 80)
    
    alternatives = [
        "https://bitts.fr/vwar_windows/autorenew.php",  # lowercase
        "https://bitts.fr/vwar_windows/AutoRenew.php",  # different case
        "https://bitts.fr/vwar_windows/auto-renew",     # no .php
        "https://bitts.fr/vwar_windows/auto_renew.php", # underscore
    ]
    
    print("Trying alternative URLs (GET requests):\n")
    for url in alternatives:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 404:
                print(f"✅ {url}")
                print(f"   Status: {response.status_code}")
            else:
                print(f"❌ {url} - 404")
        except Exception as e:
            print(f"❌ {url} - Error: {e}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("\n📋 Recommendations:")
    print("1. Verify the PHP file exists on your server")
    print("2. Check file name spelling and case")
    print("3. Verify server-side .htaccess or routing configuration")
    print("4. Contact server admin to confirm endpoint availability")
    print("=" * 80)


if __name__ == "__main__":
    test_endpoint()
