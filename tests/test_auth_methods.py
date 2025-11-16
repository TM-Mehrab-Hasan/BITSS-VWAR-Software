"""
Test different authentication methods for auto-renew endpoint
"""
import requests
import json

url = 'https://bitts.fr/vwar_windows/autoReNew'
key = '47831D7C324F4C929B99AB7D58769'
payload = {'id': '118', 'auto_renew': 'YES'}

print("=" * 80)
print("TESTING DIFFERENT AUTHENTICATION METHODS")
print("=" * 80)

tests = [
    {
        'name': 'API-Key header',
        'headers': {'API-Key': key, 'Content-Type': 'application/json'}
    },
    {
        'name': 'X-API-Key header',
        'headers': {'X-API-Key': key, 'Content-Type': 'application/json'}
    },
    {
        'name': 'Authorization Bearer',
        'headers': {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    },
    {
        'name': 'apikey header (lowercase)',
        'headers': {'apikey': key, 'Content-Type': 'application/json'}
    }
]

for i, test in enumerate(tests, 1):
    print(f"\n{i}. Testing: {test['name']}")
    try:
        response = requests.post(url, json=payload, headers=test['headers'], timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code != 401:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 80)
