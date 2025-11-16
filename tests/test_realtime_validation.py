"""
Real-Time License Validation Test

This script tests the 30-second real-time validation feature.
It will monitor the license status and detect when changes are made in the database.

Test Scenarios:
1. Monitor current license status
2. Wait for you to change valid_till in database (make it expired)
3. Detect expiry within 30 seconds
4. Wait for you to renew license in database
5. Detect renewal within 30 seconds

Instructions:
1. Run this script
2. When prompted, go to your database and change the valid_till date
3. Watch as the script detects the change within 30 seconds
"""

import time
import requests
from datetime import datetime
from config import API_LICENSE_FETCH, API_LICENSE_FETCH_KEY
from activation.hwid import get_processor_info, get_motherboard_info

def fetch_license_status():
    """Fetch current license status from server."""
    try:
        # Get hardware info
        processor_info = get_processor_info()
        motherboard_info = get_motherboard_info()
        
        headers = {
            "X-API-Key": API_LICENSE_FETCH_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "processor_id": processor_info,
            "motherboard_id": motherboard_info
        }
        
        response = requests.post(API_LICENSE_FETCH, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle both response formats:
            # 1. {"status": "success", "license": {...}} - single license
            # 2. {"status": "success", "data": [...]} - multiple licenses
            
            if data.get("status") == "success":
                # Check for single license format first
                if "license" in data:
                    license_data = data["license"]
                    return {
                        "success": True,
                        "license_id": license_data.get("id"),
                        "license_key": license_data.get("license_key"),
                        "valid_till": license_data.get("valid_till"),
                        "auto_renew": license_data.get("auto_renew"),
                        "status": license_data.get("status"),
                        "days_left": license_data.get("days_left")
                    }
                
                # Check for multiple licenses format
                elif "data" in data and len(data["data"]) > 0:
                    # Get the first license that matches this device
                    for license_data in data["data"]:
                        # Check if this license is for the current device
                        device1_match = (license_data.get("processor_id") == processor_info and 
                                       license_data.get("motherboard_id") == motherboard_info)
                        device2_match = (license_data.get("processor_id_2") == processor_info and 
                                       license_data.get("motherboard_id_2") == motherboard_info)
                        
                        if device1_match or device2_match:
                            return {
                                "success": True,
                                "license_id": license_data.get("id"),
                                "license_key": license_data.get("password"),  # API uses 'password' field
                                "valid_till": license_data.get("valid_till"),
                                "auto_renew": license_data.get("auto_renew"),
                                "status": "active" if datetime.strptime(license_data.get("valid_till"), "%Y-%m-%d %H:%M:%S") > datetime.now() else "expired",
                                "days_left": (datetime.strptime(license_data.get("valid_till"), "%Y-%m-%d %H:%M:%S") - datetime.now()).days
                            }
                    
                    return {"success": False, "error": "No license found for this device"}
                else:
                    return {"success": False, "error": "No licenses found in response"}
            else:
                # Response is 200 but doesn't have success status
                return {"success": False, "error": f"Unexpected response: {data}"}
        
        return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def print_license_info(license_data, check_number):
    """Print formatted license information."""
    print(f"\n{'='*70}")
    print(f"CHECK #{check_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    if license_data.get("success"):
        print(f"✅ License ID: {license_data.get('license_id')}")
        print(f"✅ License Key: {license_data.get('license_key')}")
        print(f"✅ Valid Until: {license_data.get('valid_till')}")
        print(f"✅ Status: {license_data.get('status')}")
        print(f"✅ Days Left: {license_data.get('days_left')}")
        print(f"✅ Auto-Renew: {license_data.get('auto_renew')}")
    else:
        print(f"❌ Error: {license_data.get('error')}")
    
    print(f"{'='*70}\n")

def main():
    print("\n" + "="*70)
    print(" REAL-TIME LICENSE VALIDATION TEST - 30 SECOND INTERVAL")
    print("="*70)
    print("\nThis test will check your license status every 30 seconds.")
    print("You can modify the license in the database and see it update here.\n")
    
    # Initial check
    print("Performing initial license check...")
    initial_status = fetch_license_status()
    print_license_info(initial_status, 1)
    
    if not initial_status.get("success"):
        print("❌ Could not fetch license. Please check your connection and try again.")
        return
    
    print("\n📋 TEST INSTRUCTIONS:")
    print("-" * 70)
    print("1. Note the current 'Valid Until' date above")
    print("2. Go to your database and change the 'valid_till' to a past date")
    print("3. Watch this script detect the expiry within 30 seconds")
    print("4. Then change 'valid_till' back to a future date")
    print("5. Watch the script detect the renewal within 30 seconds")
    print("-" * 70)
    print("\n⏱️  Monitoring started... (Press Ctrl+C to stop)\n")
    
    check_count = 1
    previous_valid_till = initial_status.get("valid_till")
    previous_status = initial_status.get("status")
    previous_auto_renew = initial_status.get("auto_renew")
    
    try:
        while True:
            # Wait for 30 seconds
            for i in range(30, 0, -1):
                print(f"⏳ Next check in {i:2d} seconds...", end="\r")
                time.sleep(1)
            
            # Fetch current status
            check_count += 1
            current_status = fetch_license_status()
            
            if current_status.get("success"):
                current_valid_till = current_status.get("valid_till")
                current_status_value = current_status.get("status")
                current_auto_renew = current_status.get("auto_renew")
                
                # Detect changes
                changes_detected = []
                
                if current_valid_till != previous_valid_till:
                    changes_detected.append(f"Valid Till: {previous_valid_till} → {current_valid_till}")
                
                if current_status_value != previous_status:
                    changes_detected.append(f"Status: {previous_status} → {current_status_value}")
                
                if current_auto_renew != previous_auto_renew:
                    changes_detected.append(f"Auto-Renew: {previous_auto_renew} → {current_auto_renew}")
                
                if changes_detected:
                    print("\n" + "🚨 " * 35)
                    print("🎯 CHANGE DETECTED!")
                    print("🚨 " * 35)
                    for change in changes_detected:
                        print(f"   📍 {change}")
                    print("🚨 " * 35)
                
                print_license_info(current_status, check_count)
                
                # Update previous values
                previous_valid_till = current_valid_till
                previous_status = current_status_value
                previous_auto_renew = current_auto_renew
            else:
                print(f"\n❌ Check #{check_count} failed: {current_status.get('error')}\n")
    
    except KeyboardInterrupt:
        print("\n\n✅ Test stopped by user.")
        print(f"Total checks performed: {check_count}")
        print("="*70 + "\n")

if __name__ == "__main__":
    main()
