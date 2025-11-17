"""
Test automatic installation detection functionality
"""

import os
import sys
import time
import subprocess
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.installation_detector import get_installation_detector, get_installation_logger


def test_automatic_detection():
    """Test that the detector automatically finds installer processes."""
    
    print("=" * 80)
    print("AUTOMATIC INSTALLATION DETECTION TEST")
    print("=" * 80)
    
    # Get detector instance
    detector = get_installation_detector()
    logger = get_installation_logger()
    
    # Start monitoring
    print("\n1. Starting installation detector...")
    detector.start_monitoring()
    time.sleep(2)
    
    # Check initial state
    print("\n2. Checking initial state...")
    if detector.is_installation_active():
        print(f"   ✓ Found {len(detector.get_active_installers())} active installers")
        for installer in detector.get_active_installers():
            print(f"     - {installer['name']} (PID: {installer['pid']})")
    else:
        print("   ✓ No installers currently running")
    
    # Simulate running an installer (create a temporary setup.exe process)
    print("\n3. Simulating installer process...")
    print("   Creating a temporary 'setup.exe' process...")
    
    # Create a simple batch file that acts like an installer
    temp_dir = tempfile.gettempdir()
    test_installer_bat = os.path.join(temp_dir, "test_setup_installer.bat")
    
    with open(test_installer_bat, 'w') as f:
        f.write('@echo off\n')
        f.write('echo Installing test software...\n')
        f.write('timeout /t 15 /nobreak > nul\n')  # Run for 15 seconds
        f.write('echo Installation complete!\n')
    
    # Start the "installer" process
    print(f"   Launching: {test_installer_bat}")
    installer_process = subprocess.Popen(
        [test_installer_bat],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    # Wait for detector to find it
    print("\n4. Waiting for detector to find installer process...")
    time.sleep(7)
    
    # Check if detected
    if detector.is_installation_active():
        print("   ✅ SUCCESS: Installer detected!")
        for installer in detector.get_active_installers():
            print(f"     - {installer['name']} (PID: {installer['pid']}, running {installer['duration']:.0f}s)")
    else:
        print("   ❌ FAILED: Installer not detected")
    
    # Test file path checking
    print("\n5. Testing file path detection...")
    test_file = os.path.join(temp_dir, "test_file.dll")
    
    if detector.is_file_being_installed(test_file):
        print(f"   ✅ File correctly identified as being installed: {test_file}")
    else:
        print(f"   ℹ️ File not in monitored installation folder")
    
    # Wait for installer to finish
    print("\n6. Waiting for installer to complete...")
    installer_process.wait()
    time.sleep(3)
    
    # Check if detector noticed completion
    if detector.is_installation_active():
        print("   ⚠️ Installer still marked as active")
    else:
        print("   ✅ Detector correctly noticed installer completed")
    
    # Cleanup
    try:
        os.remove(test_installer_bat)
    except:
        pass
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE - Check data/installation.log for detailed logs")
    print("=" * 80)


def test_log_format():
    """Test the installation.log format."""
    
    print("\n" + "=" * 80)
    print("INSTALLATION LOG FORMAT TEST")
    print("=" * 80)
    
    detector = get_installation_detector()
    logger = get_installation_logger()
    
    # Simulate various log entries
    print("\n1. Logging test scan events...")
    
    detector.log_installation_scan("C:\\Program Files\\TestApp\\app.exe", "CLEAN", scan_time_ms=45)
    detector.log_installation_scan("C:\\Program Files\\TestApp\\malware.dll", "THREAT", "TrojanDropper", 120)
    detector.log_installation_quarantine(
        "C:\\Program Files\\TestApp\\malware.dll",
        "quarantine/malware.dll.quarantined",
        "TrojanDropper"
    )
    
    print("   ✅ Logged 3 test events")
    print(f"   📄 Check: data/installation.log")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🔧 Automatic Installation Detection Test Suite\n")
    
    try:
        test_automatic_detection()
        print("\n")
        test_log_format()
        
        print("\n✅ ALL TESTS COMPLETED")
        print("\nTo see automatic installation mode in action:")
        print("1. Run the VWAR application")
        print("2. Start Auto Scanning")
        print("3. Download an installer (.exe, .msi) or run an existing one")
        print("4. Watch the Installation Mode button update automatically")
        print("5. Download files during installation - they'll be scanned in-place")
        print("6. Only malware will be quarantined, clean files stay where installed")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
