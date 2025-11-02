import os
import json
import requests
import tkinter as tk
from tkinter import messagebox
from activation.hwid import get_processor_info, get_motherboard_info
from config import (
    ACTIVATION_FILE, 
    API_LICENSE_FETCH, 
    API_LICENSE_FETCH_KEY,
    API_HW_INFO_INSERT,
    API_HW_INFO_INSERT_KEY
)
from app_main import VWARScannerGUI
from datetime import datetime
from config import ICON_PATH
from cryptography.fernet import Fernet
import base64, hashlib
# from liences_utils import _store_activation  # ✅ now imported from liences_utils
from activation.license_utils import _store_activation  # ✅ now imported from license_utils


def generate_fernet_key_from_string(secret_string):
    sha256 = hashlib.sha256(secret_string.encode()).digest()
    return base64.urlsafe_b64encode(sha256)

SECRET_KEY = generate_fernet_key_from_string("VWAR@BIFIN")
fernet = Fernet(SECRET_KEY)


def show_activation_window(reason=None):
    """Launch the activation GUI window and display the reason if provided."""
    root = tk.Tk()
    root.title("Activate VWAR Scanner")
    root.geometry("400x320")  # Increased height for auto-renew checkbox
    root.configure(bg="#1e1e1e")
    # root.iconbitmap(ICON_PATH)
    root.resizable(False, False)

    # Optional reason label
    if reason:
        tk.Label(root, text=reason, fg="red", bg="#1e1e1e", font=("Arial", 11, "bold")).pack(pady=(20, 5))

    tk.Label(root, text="Enter Activation Key", bg="#1e1e1e", fg="white", font=("Arial", 12)).pack(pady=(10 if reason else 30, 5))

    key_entry = tk.Entry(root, font=("Arial", 12), width=30, justify="center")
    key_entry.pack(pady=10)
    
    # Auto-renew checkbox
    auto_renew_var = tk.BooleanVar(value=False)
    auto_renew_check = tk.Checkbutton(
        root, 
        text="Enable Auto-Renew", 
        variable=auto_renew_var,
        bg="#1e1e1e", 
        fg="white", 
        selectcolor="#2e2e2e",
        activebackground="#1e1e1e",
        activeforeground="white",
        font=("Arial", 10)
    )
    auto_renew_check.pack(pady=(5, 10))

    tk.Button(
        root, text="Activate", bg="#28a745", fg="white", font=("Arial", 12),
        command=lambda: activate(key_entry.get(), root, auto_renew_var.get())
    ).pack(pady=20)

    root.mainloop()


def activate(license_key, root, auto_renew=False):
    """Handles the activation process: check key, match hardware, and activate.
    Supports up to 2 devices per license key.
    
    Args:
        license_key (str): The license key entered by user
        root: The Tkinter root window
        auto_renew (bool): Whether to enable auto-renewal for this license
    """
    if not license_key:
        messagebox.showwarning("Empty Field", "Please enter a license key.")
        return
    
    # Get hardware info first
    current_cpu = get_processor_info()
    current_mobo = get_motherboard_info()

    if not current_cpu or not current_mobo:
        messagebox.showerror("Hardware Error", "Failed to retrieve hardware information.")
        return
    
    try:
        # Use POST with hardware info to get license for this device
        headers = {
            "X-API-Key": API_LICENSE_FETCH_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "processor_id": current_cpu,
            "motherboard_id": current_mobo
        }
        response = requests.post(API_LICENSE_FETCH, json=payload, headers=headers, timeout=10)
        
        if response.status_code != 200:
            messagebox.showerror("API Error", f"Failed to connect to activation server (Status: {response.status_code})")
            return
        
        data = response.json()
        records = data.get("data", [])
        
    except Exception as e:
        messagebox.showerror("API Error", f"Failed to connect to activation server: {e}")
        return

    # Find the license record
    found = None
    for record in records:
        if record.get("password") == license_key:
            found = record
            break

    if not found:
        messagebox.showerror("Invalid Key", "The license key entered is not valid.")
        return

    # Check expiration first (applies to all devices)
    valid_till = found.get("valid_till")
    try:
        expiry = datetime.strptime(valid_till, "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiry:
            messagebox.showerror("Expired Key", "This license key has expired. Please renew your license.\nContact us at: https://bitss.one/contact")
            return
    except Exception as e:
        messagebox.showerror("Invalid Date", f"Failed to validate license expiry:\n{e}")
        return

    # Get device slots from database
    device1_cpu = found.get("processor_id")
    device1_mobo = found.get("motherboard_id")
    device2_cpu = found.get("processor_id_2")
    device2_mobo = found.get("motherboard_id_2")

    # Check if current device matches Device 1
    if device1_cpu and device1_mobo:
        if current_cpu == device1_cpu and current_mobo == device1_mobo:
            _store_activation(found, current_cpu, current_mobo, auto_renew)
            messagebox.showinfo("Re-Activation", "VWAR Scanner is already activated on this system (Device 1).")
            _launch_app(root)
            return

    # Check if current device matches Device 2
    if device2_cpu and device2_mobo:
        if current_cpu == device2_cpu and current_mobo == device2_mobo:
            _store_activation(found, current_cpu, current_mobo, auto_renew)
            messagebox.showinfo("Re-Activation", "VWAR Scanner is already activated on this system (Device 2).")
            _launch_app(root)
            return

    # Try to bind to an empty slot
    # Priority: Device 1 first, then Device 2
    target_slot = None
    if not device1_cpu or not device1_mobo:
        # Device 1 slot is empty
        target_slot = 1
    elif not device2_cpu or not device2_mobo:
        # Device 2 slot is empty
        target_slot = 2
    else:
        # Both slots are occupied by different devices
        messagebox.showerror(
            "Device Limit Reached", 
            "This license key is already activated on 2 devices.\n\n"
            "Maximum device limit reached. To activate on this device,\n"
            "please deactivate one of the existing devices first.\n\n"
            "Contact support: https://bitss.one/contact"
        )
        return

    # Bind to the available slot
    try:
        # Use slot-specific field names so server receives exactly the column we intend to update.
        # API expects processor_id / motherboard_id for slot 1 and processor_id_2 / motherboard_id_2 for slot 2.
        if target_slot == 1:
            bind_payload = {
                "id": found["id"],
                "slot": target_slot,
                "processor_id": current_cpu,
                "motherboard_id": current_mobo
            }
        else:
            bind_payload = {
                "id": found["id"],
                "slot": target_slot,
                "processor_id_2": current_cpu,
                "motherboard_id_2": current_mobo
            }
        
        headers = {
            "X-API-Key": API_HW_INFO_INSERT_KEY,
            "Content-Type": "application/json"
        }
        bind_response = requests.post(API_HW_INFO_INSERT, json=bind_payload, headers=headers)
        result = bind_response.json()
        # Log full bind response for diagnostics (helps determine if server inserted into both slots)
        try:
            print(f"[ACTIVATION] Slot {target_slot} binding result: {result.get('status')}")
            print(f"[ACTIVATION] Bind response payload: {result}")
        except Exception:
            # Fallback to raw text if JSON is not printable
            try:
                print(f"[ACTIVATION] Bind response text: {bind_response.text}")
            except Exception:
                pass

        # Also append the raw response to a local debug file for offline inspection
        try:
            dbg_path = os.path.join(os.getcwd(), 'activation_bind_debug.log')
            with open(dbg_path, 'a', encoding='utf-8') as dbg_f:
                dbg_f.write(f"\n--- BIND ATTEMPT ({datetime.now().isoformat()}) ---\n")
                dbg_f.write(json.dumps({
                    'target_slot': target_slot,
                    'payload_sent': bind_payload,
                    'response': result
                }, default=str, ensure_ascii=False, indent=2))
                dbg_f.write('\n')
        except Exception as e:
            print(f"[ACTIVATION] Failed to write bind debug file: {e}")

        if result.get('status') == "success":
            # Prefer authoritative record returned by server (if present)
            server_record = None
            if isinstance(result.get('data'), dict):
                server_record = result.get('data')
            elif isinstance(result.get('record'), dict):
                server_record = result.get('record')

            try:
                if server_record:
                    # Safety guard: if the server returned values for BOTH device slots,
                    # treat this as suspicious and avoid blindly overwriting the local
                    # activation file with a possibly incorrect server record.
                    slot1_populated = bool(server_record.get('processor_id') or server_record.get('motherboard_id'))
                    slot2_populated = bool(server_record.get('processor_id_2') or server_record.get('motherboard_id_2'))
                    if slot1_populated and slot2_populated:
                        # Suspicious: server returned both slots. Log, write debug file, and conservatively
                        # store only the locally-known 'found' record updated with the slot we intended to bind.
                        warning_msg = (
                            f"[ACTIVATION] Suspicious server record: both device slots populated for license id={found.get('id')}."
                        )
                        print(warning_msg)
                        # Append to debug log
                        try:
                            dbg_path = os.path.join(os.getcwd(), 'activation_bind_debug.log')
                            with open(dbg_path, 'a', encoding='utf-8') as dbg_f:
                                dbg_f.write(f"\n--- SUSPICIOUS SERVER RECORD ({datetime.now().isoformat()}) ---\n")
                                dbg_f.write(json.dumps({
                                    'target_slot': target_slot,
                                    'payload_sent': bind_payload,
                                    'server_record': server_record
                                }, default=str, ensure_ascii=False, indent=2))
                                dbg_f.write('\n')
                        except Exception as e:
                            print(f"[ACTIVATION] Failed to append suspicious record to debug file: {e}")

                        # Conservative local store: only update the intended slot fields so we don't mirror both-slot writes
                        try:
                            if target_slot == 1:
                                found['processor_id'] = current_cpu
                                found['motherboard_id'] = current_mobo
                            else:
                                found['processor_id_2'] = current_cpu
                                found['motherboard_id_2'] = current_mobo
                            _store_activation(found, current_cpu, current_mobo, auto_renew)
                            # Inform user
                            try:
                                messagebox.showwarning(
                                    "Activation Notice",
                                    "Server returned unexpected device info. Activation stored locally for this device, "
                                    "but server response was unusual. Please contact support if this persists."
                                )
                            except Exception:
                                pass
                        except Exception as e:
                            print(f"[ACTIVATION] Failed to conservatively store activation: {e}")
                    else:
                        # Normal case: server record looks reasonable - store authoritative record
                        _store_activation(server_record, current_cpu, current_mobo, auto_renew)
                else:
                    # Fallback: store the original found record updated locally
                    found['processor_id'] = current_cpu if target_slot == 1 else found.get('processor_id')
                    found['motherboard_id'] = current_mobo if target_slot == 1 else found.get('motherboard_id')
                    if target_slot == 2:
                        found['processor_id_2'] = current_cpu
                        found['motherboard_id_2'] = current_mobo
                    _store_activation(found, current_cpu, current_mobo, auto_renew)
            except Exception as e:
                print(f"[ACTIVATION] Warning: failed to store server record: {e}")

            # Sync auto-renew with server if enabled
            if auto_renew:
                from activation.license_utils import update_auto_renew_status
                success, msg = update_auto_renew_status(True)
                if not success:
                    print(f"[WARNING] Failed to sync auto-renew: {msg}")

            messagebox.showinfo(
                "Activation Successful",
                f"VWAR Scanner activated successfully!\n\n"
                f"Device Slot: {target_slot} of 2\n"
                f"Valid Until: {valid_till}\n"
                f"Auto-Renew: {'Enabled' if auto_renew else 'Disabled'}"
            )
            _launch_app(root)
            return
        else:
            error_msg = result.get('message', 'Server rejected activation attempt.')
            messagebox.showerror("Activation Failed", f"Activation failed: {error_msg}")
            return

    except Exception as e:
        messagebox.showerror("POST Error", f"Failed to bind activation:\n{e}")
        return


def _launch_app(root):
    """Close activation window and launch the main VWAR app."""
    root.destroy()
    app_root = tk.Tk()
    VWARScannerGUI(app_root)
    app_root.mainloop()
