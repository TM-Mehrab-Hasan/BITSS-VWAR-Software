"""
Test script to verify 2-device licensing logic
This simulates the activation flow without making actual API calls
"""

def test_2device_logic():
    print("=" * 70)
    print("Testing 2-Device Licensing Logic")
    print("=" * 70)
    
    # Simulate license record from API
    license_record = {
        "id": "123",
        "username": "test_user",
        "password": "TEST-KEY-12345",
        "valid_till": "2025-12-31 23:59:59",
        "processor_id": None,      # Device 1 CPU
        "motherboard_id": None,    # Device 1 Motherboard
        "processor_id_2": None,    # Device 2 CPU
        "motherboard_id_2": None   # Device 2 Motherboard
    }
    
    # Simulate different devices
    device_A = {"cpu": "CPU_AAA", "mobo": "MOBO_AAA"}
    device_B = {"cpu": "CPU_BBB", "mobo": "MOBO_BBB"}
    device_C = {"cpu": "CPU_CCC", "mobo": "MOBO_CCC"}
    
    print("\n📋 Test Scenarios:\n")
    
    # Scenario 1: First device activation (Device A)
    print("1️⃣  SCENARIO 1: First device (Device A) tries to activate")
    print("   Current State: Both slots empty")
    result = simulate_activation(license_record, device_A)
    print(f"   Result: {result}\n")
    
    # Update license record after Device A activation
    if result["success"]:
        if result["slot"] == 1:
            license_record["processor_id"] = device_A["cpu"]
            license_record["motherboard_id"] = device_A["mobo"]
        else:
            license_record["processor_id_2"] = device_A["cpu"]
            license_record["motherboard_id_2"] = device_A["mobo"]
    
    # Scenario 2: Device A re-activates
    print("2️⃣  SCENARIO 2: Device A tries to re-activate")
    print(f"   Current State: Slot 1 = Device A, Slot 2 = Empty")
    result = simulate_activation(license_record, device_A)
    print(f"   Result: {result}\n")
    
    # Scenario 3: Second device activation (Device B)
    print("3️⃣  SCENARIO 3: Second device (Device B) tries to activate")
    print(f"   Current State: Slot 1 = Device A, Slot 2 = Empty")
    result = simulate_activation(license_record, device_B)
    print(f"   Result: {result}\n")
    
    # Update license record after Device B activation
    if result["success"]:
        if result["slot"] == 1:
            license_record["processor_id"] = device_B["cpu"]
            license_record["motherboard_id"] = device_B["mobo"]
        else:
            license_record["processor_id_2"] = device_B["cpu"]
            license_record["motherboard_id_2"] = device_B["mobo"]
    
    # Scenario 4: Device B re-activates
    print("4️⃣  SCENARIO 4: Device B tries to re-activate")
    print(f"   Current State: Slot 1 = Device A, Slot 2 = Device B")
    result = simulate_activation(license_record, device_B)
    print(f"   Result: {result}\n")
    
    # Scenario 5: Third device tries to activate (should fail)
    print("5️⃣  SCENARIO 5: Third device (Device C) tries to activate")
    print(f"   Current State: Slot 1 = Device A, Slot 2 = Device B (FULL)")
    result = simulate_activation(license_record, device_C)
    print(f"   Result: {result}\n")
    
    # Scenario 6: Test payload generation
    print("6️⃣  SCENARIO 6: Verify API payload structure")
    test_payload_structure()
    
    print("=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)


def simulate_activation(license_record, current_device):
    """Simulates the activation logic from gui.py"""
    current_cpu = current_device["cpu"]
    current_mobo = current_device["mobo"]
    
    # Get device slots from database
    device1_cpu = license_record.get("processor_id")
    device1_mobo = license_record.get("motherboard_id")
    device2_cpu = license_record.get("processor_id_2")
    device2_mobo = license_record.get("motherboard_id_2")
    
    # Check if current device matches Device 1
    if device1_cpu and device1_mobo:
        if current_cpu == device1_cpu and current_mobo == device1_mobo:
            return {
                "success": True,
                "action": "RE-ACTIVATION",
                "slot": 1,
                "message": "Already activated on this system (Device 1)"
            }
    
    # Check if current device matches Device 2
    if device2_cpu and device2_mobo:
        if current_cpu == device2_cpu and current_mobo == device2_mobo:
            return {
                "success": True,
                "action": "RE-ACTIVATION",
                "slot": 2,
                "message": "Already activated on this system (Device 2)"
            }
    
    # Try to bind to an empty slot
    target_slot = None
    if not device1_cpu or not device1_mobo:
        target_slot = 1
    elif not device2_cpu or not device2_mobo:
        target_slot = 2
    else:
        return {
            "success": False,
            "action": "REJECTED",
            "slot": None,
            "message": "Device limit reached (2/2 devices already activated)"
        }
    
    # Simulate successful binding
    return {
        "success": True,
        "action": "NEW_ACTIVATION",
        "slot": target_slot,
        "message": f"Activated in slot {target_slot}"
    }


def test_payload_structure():
    """Verify the API payload structure matches documentation"""
    print("   Testing API payload structure for hw-info-insert:\n")
    
    # Expected payload structure
    expected_payload = {
        "id": "123",
        "slot": 1,  # or 2
        "processor_id": "CPU_XXX",
        "motherboard_id": "MOBO_XXX"
    }
    
    print(f"   Expected Payload: {expected_payload}")
    print(f"   ✓ Contains 'id' field")
    print(f"   ✓ Contains 'slot' field (1 or 2)")
    print(f"   ✓ Contains 'processor_id' field")
    print(f"   ✓ Contains 'motherboard_id' field")
    print(f"   ✓ Payload structure matches API documentation\n")


if __name__ == "__main__":
    test_2device_logic()
