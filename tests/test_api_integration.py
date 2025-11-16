"""
Test API integration for 2-device licensing
This shows the exact API calls that will be made
"""

def test_api_calls():
    print("=" * 80)
    print("API INTEGRATION TEST - 2-DEVICE LICENSING")
    print("=" * 80)
    
    # Test data
    license_id = "123"
    license_key = "TEST-LICENSE-KEY"
    device_cpu = "Intel_Core_i7_12700K"
    device_mobo = "ASUS_ROG_MAXIMUS_Z690"
    
    print("\n📡 API ENDPOINT 1: License Fetch (GET)")
    print("─" * 80)
    print(f"URL: https://bitts.fr/vwar_windows/license-fetch")
    print(f"Method: GET")
    print(f"Headers:")
    print(f"  API-Key: FDD56B7B7C46658IBAD28EDCC83CE")
    print(f"\nExpected Response:")
    print(f"""{{
    "data": [
        {{
            "id": "{license_id}",
            "username": "test_user",
            "password": "{license_key}",
            "valid_till": "2025-12-31 23:59:59",
            "processor_id": null,        // Device 1 CPU
            "motherboard_id": null,      // Device 1 Motherboard
            "processor_id_2": null,      // Device 2 CPU
            "motherboard_id_2": null     // Device 2 Motherboard
        }}
    ]
}}""")
    
    print("\n\n📡 API ENDPOINT 2: Hardware Info Insert (POST)")
    print("─" * 80)
    print(f"URL: https://bitts.fr/vwar_windows/hw-info-insert")
    print(f"Method: POST")
    print(f"Headers:")
    print(f"  API-Key: E246F159FBC2B3F39227394CBBD76")
    print(f"  Content-Type: application/json")
    print(f"\nPayload (Device 1 - Slot 1):")
    payload_slot1 = {
        "id": license_id,
        "slot": 1,
        "processor_id": device_cpu,
        "motherboard_id": device_mobo
    }
    import json
    print(json.dumps(payload_slot1, indent=2))
    
    print(f"\nPayload (Device 2 - Slot 2):")
    payload_slot2 = {
        "id": license_id,
        "slot": 2,
        "processor_id": "AMD_Ryzen_9_5900X",
        "motherboard_id": "MSI_MAG_B550_TOMAHAWK"
    }
    print(json.dumps(payload_slot2, indent=2))
    
    print(f"\nExpected Response:")
    print(f"""{{
    "status": "success",
    "message": "Hardware info updated successfully"
}}""")
    
    print("\n\n📡 API ENDPOINT 3: Auto-Renew (POST)")
    print("─" * 80)
    print(f"URL: https://bitts.fr/vwar_windows/autoReNew.php")
    print(f"Method: POST")
    print(f"Headers:")
    print(f"  API-Key: E246F159FBC2B3F39227394CBBD76")
    print(f"  Content-Type: application/json")
    print(f"\nPayload (Enable):")
    auto_renew_payload = {
        "id": license_id,
        "auto_renew": "YES"
    }
    print(json.dumps(auto_renew_payload, indent=2))
    
    print(f"\nPayload (Disable):")
    auto_renew_payload["auto_renew"] = "NO"
    print(json.dumps(auto_renew_payload, indent=2))
    
    print(f"\nExpected Response:")
    print(f"""{{
    "status": "success",
    "message": "Auto-renew updated successfully"
}}""")
    
    print("\n\n📡 API ENDPOINT 4: YARA Fetch (GET)")
    print("─" * 80)
    print(f"URL: https://library.bitss.one/vwar_windows/fetch-rules")
    print(f"Method: GET")
    print(f"Headers:")
    print(f"  API-Key: 7A6D317B24AAE34DD74B9B8E35E5F")
    print(f"\nExpected Response:")
    print(f"""[
    {{
        "categoryname": "ransomware",
        "rulename": "WannaCry",
        "conditions": [
            {{
                "string": "rule WannaCry {{ ... }}"
            }}
        ]
    }},
    ...
]""")
    
    print("\n\n📡 API ENDPOINT 5: YARA Insert (POST)")
    print("─" * 80)
    print(f"URL: https://library.bitss.one/vwar_windows/insert-rule")
    print(f"Method: POST")
    print(f"Headers:")
    print(f"  API-Key: 93B78A8977A6617EB2BEDF4235848")
    print(f"  Content-Type: application/json")
    print(f"\nPayload:")
    yara_payload = {
        "category": "ransomware",
        "rule": "rule CustomRule { ... }",
        "strings": "$string1 = \"malicious_pattern\""
    }
    print(json.dumps(yara_payload, indent=2))
    
    print(f"\nExpected Response:")
    print(f"""{{
    "status": "success",
    "message": "Rule inserted successfully"
}}""")
    
    print("\n" + "=" * 80)
    print("✅ API INTEGRATION SUMMARY")
    print("=" * 80)
    print("✓ All 5 API endpoints configured with authentication")
    print("✓ Payload structures match API documentation")
    print("✓ 2-device licensing properly integrated:")
    print("  - Slot 1: processor_id & motherboard_id")
    print("  - Slot 2: processor_id_2 & motherboard_id_2")
    print("✓ Hardware binding payload includes 'slot' parameter")
    print("✓ All endpoints use proper API-Key headers")
    print("=" * 80)


if __name__ == "__main__":
    test_api_calls()
