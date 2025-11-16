"""
Test auto-renew API with actual license ID from activation file
"""

import os
import sys
sys.path.insert(0, '.')

import json
import requests
from cryptography.fernet import Fernet
import base64, hashlib

from config import ACTIVATION_FILE, API_AUTO_RENEW, API_AUTO_RENEW_KEY

def generate_fernet_key_from_string(secret_string):
    sha256 = hashlib.sha256(secret_string.encode()).digest()
    return base64.urlsafe_b64encode(sha256)

SECRET_KEY = generate_fernet_key_from_string("VWAR@BIFIN")
fernet = Fernet(SECRET_KEY)

print("=" * 80)
print("AUTO-RENEW API TEST WITH REAL LICENSE DATA")
print("=" * 80)

# Read actual license ID from activation file
if not os.path.exists(ACTIVATION_FILE):
    print("\n❌ Activation file not found. Please activate first.")
    sys.exit(1)

try:
    with open(ACTIVATION_FILE, "rb") as f:
        encrypted = f.read()
        decrypted = fernet.decrypt(encrypted)
        data = json.loads(decrypted.decode("utf-8"))
    
    license_id = data.get("id")
    username = data.get("username")
    current_auto_renew = data.get("auto_renew", False)
    
    print(f"\n📄 Current Activation Data:")
    print(f"   License ID: {license_id}")
    print(f"   Username: {username}")
    print(f"   Current Auto-Renew: {current_auto_renew}")
    
except Exception as e:
    print(f"\n❌ Error reading activation file: {e}")
    sys.exit(1)

# Test enabling auto-renew
print(f"\n{'─' * 80}")
print("TEST: Enable Auto-Renew (YES)")
print('─' * 80)

payload = {
    "id": license_id,
    "auto_renew": "YES"
}

headers = {
    "API-Key": API_AUTO_RENEW_KEY,
    "Content-Type": "application/json"
}

print(f"\nEndpoint: {API_AUTO_RENEW}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print(f"Headers: {json.dumps(headers, indent=2)}")

try:
    response = requests.post(API_AUTO_RENEW, json=payload, headers=headers, timeout=10)
    print(f"\n📡 Server Response:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('Content-Type')}")
    print(f"\n   Raw Response:")
    print(f"   {response.text}")
    
    # Try to parse JSON
    try:
        result = response.json()
        print(f"\n   Parsed JSON:")
        print(f"   {json.dumps(result, indent=2)}")
        
        if result.get("status") == "success":
            print(f"\n✅ Success! Auto-renew updated to YES")
        else:
            print(f"\n❌ Server rejected update")
            print(f"   Reason: {result.get('message', 'Unknown')}")
            
    except json.JSONDecodeError:
        print(f"\n⚠️  Response is not valid JSON")
        print(f"   This might indicate a server-side error")
        
except Exception as e:
    print(f"\n❌ Request failed: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
