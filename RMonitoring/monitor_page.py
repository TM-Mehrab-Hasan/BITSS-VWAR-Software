import os
import re
import json
import time
import threading
from tkinter import Frame, Label, Button, Listbox, Scrollbar, Text, StringVar, filedialog, Toplevel, messagebox, LabelFrame
from RMonitoring.real_time_monitor import RealTimeMonitor
from utils.notify import notify as notify_user
from utils.tooltip import Tooltip
from utils.logger import log_message
from config import QUARANTINE_FOLDER, SCANVAULT_FOLDER
from Scanning.vault_processor import start_vault_processor, stop_vault_processor, get_vault_processor
from utils.installation_mode import get_installation_mode

class MonitorPage(Frame):
    def __init__(self, root, app_main, switch_page_callback):
        super().__init__(root, bg="#009AA5")
        self.root = root
        self.app_main = app_main  # VWARScannerGUI instance
        self.switch_page_callback = switch_page_callback

        self.display_index_to_meta = {}
        self.vault_index_to_meta = {}
        self.monitoring_active = False
        self.real_time_monitor = None
        self.auto_scan_button_text = StringVar(value="Start Auto Scanning")

        self.quarantine_folder = QUARANTINE_FOLDER
        self.scanvault_folder = SCANVAULT_FOLDER

        # ✅ FIX: Don't auto-start ScanVault here - it will be controlled by auto scan toggle
        # ScanVault processor will start/stop with auto scanning
        # start_vault_processor(monitor_page_ref=self)

        self.setup_gui()

    def setup_gui(self):
        # Top bar
        Button(self, text="Back", command=lambda: self.switch_page_callback("home"),
               bg="red", fg="white", font=("Inter", 12)).place(x=10, y=10, width=80, height=30)
        Label(self, text="Auto Scanning", font=("Inter", 16, "bold"),
              bg="#009AA5", fg="white").place(x=400, y=10)

        # ---- ScanVault (top-left) ----
        vault_header_frame = Frame(self, bg="#009AA5")
        vault_header_frame.place(x=20, y=60, width=950, height=25)
        
        Label(vault_header_frame, text="Scan History (Recent Scans)", font=("Inter", 12, "bold"),
              bg="#009AA5", fg="white").pack(side="left")
        
        # 🔍 Scanning animation indicator (shows when queue is active)
        self.scanning_indicator = Label(vault_header_frame, text="", font=("Inter", 10, "bold"),
                                       bg="#009AA5", fg="#FFD700")  # Gold color
        self.scanning_indicator.pack(side="left", padx=10)
        
        self.scanvault_listbox = Listbox(self, font=("Inter", 10))
        self.scanvault_listbox.place(x=20, y=90, width=950, height=150)
        yscroll_v = Scrollbar(self, orient="vertical", command=self.scanvault_listbox.yview)
        yscroll_v.place(x=970, y=90, height=150)
        self.scanvault_listbox.config(yscrollcommand=yscroll_v.set)
        self.scanvault_listbox.bind("<<ListboxSelect>>", self.on_select_vault)
        Button(self, text="Refresh Vault", command=self.update_scanvault_listbox,
               bg="#006666", fg="white", font=("Inter", 10)).place(x=20, y=255, width=120, height=25)
        Button(self, text="Delete Selected", command=self.delete_selected_vault,
               bg="#B22222", fg="white", font=("Inter", 10)).place(x=150, y=255, width=120, height=25)
        Button(self, text="Clear History", command=self.clear_vault_history,
               bg="#555577", fg="white", font=("Inter", 10)).place(x=280, y=255, width=120, height=25)
        
        # Installation Mode Toggle
        self.install_mode_button_text = StringVar(value="🔧 Installation Mode: OFF")
        Button(self, textvariable=self.install_mode_button_text, command=self.toggle_installation_mode,
               bg="#FF8800", fg="white", font=("Inter", 10, "bold")).place(x=420, y=255, width=220, height=25)

        # ---- Divider ----
        Label(self, text="", bg="#009AA5").place(x=20, y=285, width=950, height=2)

        # ---- Quarantine (bottom-left) ----
        # ✨ Quarantine header with animated file counter
        quarantine_header_frame = Frame(self, bg="#009AA5")
        quarantine_header_frame.place(x=20, y=310, width=500, height=25)
        
        Label(quarantine_header_frame, text="Quarantined Files", font=("Inter", 12, "bold"),
              bg="#009AA5", fg="white").pack(side="left")
        
        self.quarantine_count_label = Label(quarantine_header_frame, text="(0)", font=("Inter", 11, "bold"),
                                           bg="#009AA5", fg="#FFD700")  # Gold color
        self.quarantine_count_label.pack(side="left", padx=5)
        self.quarantine_listbox = Listbox(self, font=("Inter", 10))
        self.quarantine_listbox.place(x=20, y=340, width=500, height=130)
        yscroll = Scrollbar(self, orient="vertical", command=self.quarantine_listbox.yview)
        yscroll.place(x=520, y=340, height=130)
        self.quarantine_listbox.config(yscrollcommand=yscroll.set)
        self.quarantine_listbox.bind("<<ListboxSelect>>", self.on_select)

        # ---- Metadata (right side) ----
        Label(self, text="Quarantine Metadata", font=("Inter", 12, "bold"),
              bg="#009AA5", fg="white").place(x=550, y=310)
        self.quarantine_detail_text = Text(self, font=("Inter", 11), wrap="word", state="disabled",
                                           bg="white", fg="black")
        self.quarantine_detail_text.place(x=550, y=340, width=420, height=130)

     # ---- Quarantine actions ----
        Button(self, text="Refresh Quarantine", command=self.update_quarantine_listbox,
            bg="#006666", fg="white", font=("Inter", 10)).place(x=20, y=480, width=180, height=25)
        Button(self, text="Delete Selected", command=self.delete_selected,
            bg="#B22222", fg="white", font=("Inter", 10)).place(x=210, y=480, width=120, height=25)
        Button(self, text="Restore from Backup", command=self.restore_quarantined_file,
            bg="blue", fg="white", font=("Inter", 10)).place(x=340, y=480, width=160, height=25)

        # ---- Auto scan controls ----
        Button(self, textvariable=self.auto_scan_button_text, command=self.toggle_monitoring,
               bg="#004953", fg="white", font=("Inter", 12, "bold")).place(x=20, y=520, width=220, height=32)
        self.auto_scan_status_label = Label(self, text="Status: Stopped",
                                            font=("Inter", 12, "bold"), bg="#FFFFFF", fg="red")
        self.auto_scan_status_label.place(x=260, y=524)

        # Initial population
        self.update_quarantine_listbox()
        self.update_scanvault_listbox()
        
        # Start installation mode timer updater
        self.update_installation_mode_display()
        
        # 🔍 Start scanning animation updater
        self._scanning_animation_frame = 0
        self.update_scanning_animation()

    # ---------------- Installation Mode Controls ----------------
    def toggle_installation_mode(self):
        """Toggle installation mode on/off."""
        install_mode = get_installation_mode()
        
        if install_mode.is_active():
            # Deactivate
            install_mode.deactivate()
            self.install_mode_button_text.set("🔧 Installation Mode: OFF")
            messagebox.showinfo(
                "Installation Mode",
                "Installation Mode Deactivated\n\n"
                "ScanVault will now capture and scan all files normally."
            )
        else:
            # Activate for 10 minutes
            install_mode.activate(duration_minutes=10)
            self.install_mode_button_text.set("🔧 Installation Mode: ON (10:00)")
            messagebox.showinfo(
                "Installation Mode Activated",
                "Installation Mode is now active for 10 minutes.\n\n"
                "During this time:\n"
                "• Installer files (.msi, .exe, .dll, etc.) will be scanned in their original location\n"
                "• Clean files will remain in place (not moved to ScanVault)\n"
                "• Malware will be quarantined immediately\n"
                "• Files in trusted installer folders will be scanned in-place\n"
                "• Regular files will still use ScanVault protection\n\n"
                "Mode will auto-deactivate after 10 minutes."
            )
    
    def update_installation_mode_display(self):
        """Update the installation mode button text with remaining time."""
        try:
            install_mode = get_installation_mode()
            
            if install_mode.is_active():
                remaining = install_mode.get_remaining_time()
                minutes = remaining // 60
                seconds = remaining % 60
                self.install_mode_button_text.set(f"🔧 Installation Mode: ON ({minutes:02d}:{seconds:02d})")
            else:
                self.install_mode_button_text.set("🔧 Installation Mode: OFF")
        except Exception:
            pass
        
        # Schedule next update in 1 second
        self.root.after(1000, self.update_installation_mode_display)

    # ---------------- Monitoring Controls ----------------
    def toggle_monitoring(self):
        if self.monitoring_active:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        if self.monitoring_active:
            return
        try:
            # Start the C++ realtime monitor and pipe
            if self.real_time_monitor is None:
                self.real_time_monitor = RealTimeMonitor(self)
            
            # Pass exclusion paths to C++ monitor (includes Installation Mode trusted paths)
            from utils.exclusions import get_internal_exclude_roots, get_temp_roots
            from utils.installation_mode import TRUSTED_INSTALLER_PATHS
            import os
            
            exclude_paths = list(get_internal_exclude_roots() | get_temp_roots())
            
            # Add Installation Mode trusted system paths (always excluded)
            # These are Windows system installer locations that should never trigger ScanVault
            for trusted_path in TRUSTED_INSTALLER_PATHS:
                # Convert relative pattern to absolute path for C++ monitor
                if '\\' in trusted_path:
                    # Try to resolve to absolute path
                    parts = trusted_path.split('\\')
                    if parts[0].lower() == 'windows':
                        abs_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), *parts[1:])
                        if os.path.exists(abs_path):
                            exclude_paths.append(abs_path)
                    elif parts[0].lower() == 'programdata':
                        abs_path = os.path.join(os.environ.get('ProgramData', 'C:\\ProgramData'), *parts[1:])
                        if os.path.exists(abs_path):
                            exclude_paths.append(abs_path)
                    elif parts[0].lower() == 'appdata':
                        # AppData\Local paths are user-specific
                        user_profile = os.path.expanduser('~')
                        abs_path = os.path.join(user_profile, *parts)
                        if os.path.exists(abs_path):
                            exclude_paths.append(abs_path)
            
            self.real_time_monitor.start_cpp_monitor_engine(excludes=exclude_paths)

            # ✅ FIX: Start ScanVault processor when auto scan starts
            from Scanning.vault_processor import get_vault_processor
            vault_processor = get_vault_processor()
            if not vault_processor._running:
                vault_processor.monitor_page = self  # Update reference
                vault_processor.start()
                log_message("[MONITOR] ScanVault processor started with auto scanning")

            self.monitoring_active = True
            self.auto_scan_button_text.set("Stop Auto Scanning")
            try:
                self.auto_scan_status_label.config(text="Status: Running", fg="green")
            except Exception:
                pass
            log_message("[MONITOR] Real-time monitoring started")
            try:
                notify_user("VWAR", "Auto scanning is running")
            except Exception:
                pass
        except Exception as e:
            log_message(f"[ERROR] Failed to start monitoring: {e}")

    def stop_monitoring(self):
        if not self.monitoring_active:
            return
        try:
            if self.real_time_monitor:
                try:
                    self.real_time_monitor.stop_cpp_monitor_engine()
                except Exception:
                    pass
            
            # ✅ FIX: Stop ScanVault processor when auto scan stops
            from Scanning.vault_processor import get_vault_processor
            try:
                vault_processor = get_vault_processor()
                vault_processor.stop()
                log_message("[MONITOR] ScanVault processor stopped with auto scanning")
            except Exception as e:
                log_message(f"[WARNING] Failed to stop ScanVault processor: {e}")
            
            self.monitoring_active = False
            self.auto_scan_button_text.set("Start Auto Scanning")
            try:
                self.auto_scan_status_label.config(text="Status: Stopped", fg="red")
            except Exception:
                pass
            log_message("[MONITOR] Real-time monitoring stopped")
            try:
                notify_user("VWAR", "Auto scanning stopped")
            except Exception:
                pass
        except Exception as e:
            log_message(f"[ERROR] Failed to stop monitoring: {e}")

    def on_select(self, event):
        index = self.quarantine_listbox.curselection()
        if not index:
            # Clear panel when nothing selected, keep blank (user deselected)
            self.quarantine_detail_text.config(state="normal")
            self.quarantine_detail_text.delete("1.0", "end")
            self.quarantine_detail_text.config(state="disabled")
            return
        meta_path = self.display_index_to_meta.get(index[0])
        if not meta_path or not os.path.exists(meta_path):
            return
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            detail_text = (
                f"Original Path:\n{metadata.get('original_path', 'Unknown')}\n\n"
                f"Quarantined At:\n{metadata.get('timestamp', 'Unknown')}\n\n"
                f"Matched Rules:\n{', '.join(metadata.get('matched_rules', []))}"
            )
        except Exception as e:
            detail_text = f"Failed to load metadata:\n{e}"
        self.quarantine_detail_text.config(state="normal")
        self.quarantine_detail_text.delete("1.0", "end")
        self.quarantine_detail_text.insert("end", detail_text)
        self.quarantine_detail_text.config(state="disabled")

    def on_select_vault(self, event):
        # No metadata panel in this reverted UI version; ignore selection
        return

    def delete_selected(self):
        """Show user-friendly dialog with options to permanently delete or restore the quarantined file."""
        index = self.quarantine_listbox.curselection()
        if not index:
            messagebox.showwarning("No Selection", "Please select a quarantined file first.")
            return
        index = index[0]

        # Use stored meta path instead of parsing text
        meta_path = self.display_index_to_meta.get(index)
        if not meta_path:
            messagebox.showerror("Error", "Metadata not found for selected file.")
            return

        # ✅ FIX: Quarantine files have .quarantined extension
        qpath = meta_path.replace(".quarantined.meta", ".quarantined")
        
        # Load metadata to get original file info
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            original_path = metadata.get('original_path', 'Unknown')
            file_name = os.path.basename(qpath).replace('.quarantined', '')
            matched_rules = metadata.get('matched_rules', [])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file metadata:\n{e}")
            return

        # Create custom dialog window
        dialog = Toplevel(self.root)
        dialog.title("⚠️ Quarantined File Action")
        dialog.configure(bg="#f0f0f0")
        dialog.resizable(False, False)
        
        # Set size and center on screen (not just parent window)
        dialog_width = 650
        dialog_height = 450
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        center_x = int(screen_width/2 - dialog_width/2)
        center_y = int(screen_height/2 - dialog_height/2)
        dialog.geometry(f'{dialog_width}x{dialog_height}+{center_x}+{center_y}')
        
        # Ensure dialog is always on top and modal
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()
        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.after(100, lambda: dialog.attributes('-topmost', False))  # Remove topmost after showing
        
        # Header
        header_frame = Frame(dialog, bg="#d9534f", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        Label(header_frame, text="⚠️ What would you like to do with this file?", 
              font=("Arial", 14, "bold"), bg="#d9534f", fg="white").pack(pady=15)
        
        # Content area
        content_frame = Frame(dialog, bg="#f0f0f0")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # File information
        info_frame = LabelFrame(content_frame, text="📄 File Information", 
                               font=("Arial", 11, "bold"), bg="white", fg="#333", padx=15, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        Label(info_frame, text=f"File Name:", font=("Arial", 10, "bold"), 
              bg="white", fg="#555", anchor="w").grid(row=0, column=0, sticky="w", pady=3)
        Label(info_frame, text=file_name, font=("Arial", 10), 
              bg="white", fg="#000", anchor="w", wraplength=450).grid(row=0, column=1, sticky="w", pady=3, padx=(10, 0))
        
        Label(info_frame, text=f"Original Location:", font=("Arial", 10, "bold"), 
              bg="white", fg="#555", anchor="w").grid(row=1, column=0, sticky="w", pady=3)
        Label(info_frame, text=original_path, font=("Arial", 10), 
              bg="white", fg="#000", anchor="w", wraplength=450).grid(row=1, column=1, sticky="w", pady=3, padx=(10, 0))
        
        Label(info_frame, text=f"Threat Detected:", font=("Arial", 10, "bold"), 
              bg="white", fg="#555", anchor="w").grid(row=2, column=0, sticky="w", pady=3)
        rules_text = ', '.join(matched_rules) if matched_rules else 'Unknown'
        Label(info_frame, text=rules_text, font=("Arial", 10), 
              bg="white", fg="#d9534f", anchor="w", wraplength=450).grid(row=2, column=1, sticky="w", pady=3, padx=(10, 0))
        
        # Warning message
        warning_frame = Frame(content_frame, bg="#fff3cd", relief="solid", borderwidth=1)
        warning_frame.pack(fill="x", pady=(0, 15))
        
        Label(warning_frame, text="⚠️ Warning: This file was quarantined because it matched malware signatures.", 
              font=("Arial", 9, "bold"), bg="#fff3cd", fg="#856404", wraplength=550, justify="left").pack(padx=10, pady=8)
        
        # Action description
        Label(content_frame, text="Please choose an action:", 
              font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#333").pack(anchor="w", pady=(0, 10))
        
        # Result variable
        user_choice = {"action": None}
        
        def on_restore():
            """Restore file to original location."""
            user_choice["action"] = "restore"
            dialog.destroy()
        
        def on_delete():
            """Permanently delete the file."""
            user_choice["action"] = "delete"
            dialog.destroy()
        
        def on_cancel():
            """Cancel and keep in quarantine."""
            user_choice["action"] = "cancel"
            dialog.destroy()
        
        # Buttons frame
        buttons_frame = Frame(content_frame, bg="#f0f0f0")
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Restore button (green)
        restore_btn = Button(buttons_frame, text="✅ Keep File (Restore)", 
                            command=on_restore, bg="#5cb85c", fg="white", 
                            font=("Arial", 11, "bold"), cursor="hand2", relief="raised", 
                            borderwidth=2, padx=15, pady=10)
        restore_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        Tooltip(restore_btn, "Restore this file to its original location.\nUse this if you believe the file is safe.")
        
        # Delete button (red)
        delete_btn = Button(buttons_frame, text="🗑️ Delete Permanently", 
                           command=on_delete, bg="#d9534f", fg="white", 
                           font=("Arial", 11, "bold"), cursor="hand2", relief="raised", 
                           borderwidth=2, padx=15, pady=10)
        delete_btn.pack(side="left", expand=True, fill="x", padx=5)
        Tooltip(delete_btn, "Permanently delete this file from quarantine.\nThis action cannot be undone.")
        
        # Cancel button (gray)
        cancel_btn = Button(buttons_frame, text="❌ Cancel", 
                           command=on_cancel, bg="#6c757d", fg="white", 
                           font=("Arial", 11, "bold"), cursor="hand2", relief="raised", 
                           borderwidth=2, padx=15, pady=10)
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))
        Tooltip(cancel_btn, "Keep the file in quarantine and take no action.")
        
        # Wait for user decision
        self.root.wait_window(dialog)
        
        # Process user choice
        if user_choice["action"] == "restore":
            # Restore file to original location
            try:
                import shutil
                
                # Create directory if it doesn't exist
                original_dir = os.path.dirname(original_path)
                os.makedirs(original_dir, exist_ok=True)
                
                # Copy file back to original location
                shutil.copy2(qpath, original_path)
                
                # Remove from quarantine
                if os.path.exists(qpath):
                    os.remove(qpath)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                
                # Update UI
                self.quarantine_listbox.delete(index)
                self.quarantine_detail_text.config(state="normal")
                self.quarantine_detail_text.delete("1.0", "end")
                self.quarantine_detail_text.config(state="disabled")
                self.update_quarantine_listbox()
                
                log_message(f"[RESTORED] {file_name} → {original_path}")
                messagebox.showinfo("✅ File Restored", 
                                  f"The file has been successfully restored to:\n\n{original_path}\n\n"
                                  f"⚠️ Please ensure this file is safe before opening it.")
                
            except Exception as e:
                log_message(f"[ERROR] Restore failed for {file_name}: {e}")
                messagebox.showerror("Restore Failed", 
                                   f"Failed to restore the file:\n\n{str(e)}\n\n"
                                   f"The file remains in quarantine.")
        
        elif user_choice["action"] == "delete":
            # Permanently delete the file
            try:
                # Remove quarantined file and metadata
                if os.path.exists(qpath):
                    os.remove(qpath)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                
                # Update UI
                self.quarantine_listbox.delete(index)
                self.quarantine_detail_text.config(state="normal")
                self.quarantine_detail_text.delete("1.0", "end")
                self.quarantine_detail_text.config(state="disabled")
                self.update_quarantine_listbox()
                
                log_message(f"[DELETED] Permanently removed {file_name} from quarantine")
                messagebox.showinfo("🗑️ File Deleted", 
                                  f"The file has been permanently deleted from quarantine.\n\n"
                                  f"File: {file_name}")
                
            except Exception as e:
                log_message(f"[ERROR] Delete failed for {file_name}: {e}")
                messagebox.showerror("Delete Failed", 
                                   f"Failed to delete the file:\n\n{str(e)}")
        
        else:
            # User cancelled - do nothing
            log_message(f"[INFO] User cancelled action for {file_name}")
            pass

    def restore_quarantined_file(self):
        index = self.quarantine_listbox.curselection()
        if not index:
            messagebox.showwarning("No Selection", "Please select a file.")
            return
        text = self.quarantine_listbox.get(index)
        match = re.search(r"→ From:\s*(.+)", text)
        if not match:
            messagebox.showerror("Error", "Could not parse original path.")
            return
        original_path = match.group(1)
        fname = os.path.basename(original_path)

        backup_root = filedialog.askdirectory(title="Select VWARbackup Folder")
        if not backup_root or not backup_root.endswith("VWARbackup"):
            messagebox.showerror("Error", "Invalid backup folder.")
            return

        found = []
        for root, _, files in os.walk(backup_root):
            for file in files:
                if file == fname + ".backup":
                    found.append(os.path.join(root, file))
        if not found:
            messagebox.showinfo("Not Found", "No backup file found.")
            return

        selected = found[0]
        if len(found) > 1:
            top = Toplevel(self.root)
            top.title("Choose Backup")
            listbox = Listbox(top, width=80)
            listbox.pack()
            for f in found:
                listbox.insert("end", f)
            def confirm():
                nonlocal selected
                if listbox.curselection():
                    selected = listbox.get(listbox.curselection()[0])
                    top.destroy()
            Button(top, text="Restore", command=confirm).pack()
            top.transient(self.root)
            top.grab_set()
            self.root.wait_window(top)

        try:
            os.makedirs(os.path.dirname(original_path), exist_ok=True)
            import shutil
            shutil.copy2(selected, original_path)
            messagebox.showinfo("Restored", f"Restored to:\n{original_path}")
        except Exception as e:
            messagebox.showerror("Restore Failed", str(e))

    def add_to_quarantine_listbox(self, file_path, meta_path, matched_rules):
        # Always marshal UI mutations to main thread
        def _do_insert():
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            file_name = os.path.basename(file_path)
            display_text = (
                f"File: {file_name}\n→ From: {file_path}\n→ Matched: {', '.join(matched_rules)}\n→ Time: {timestamp}"
            )
            try:
                self.quarantine_listbox.insert("end", display_text)
                self.display_index_to_meta[self.quarantine_listbox.size() - 1] = meta_path
            except Exception:
                pass
            try:
                self.update_quarantine_listbox()
            except Exception:
                pass
        try:
            self.root.after(0, _do_insert)
        except Exception:
            _do_insert()

    def add_to_scanvault_listbox(self, vaulted_path: str, meta_path: str):
        """Insert or update a single vaulted entry (pending). Fallback to full refresh for simplicity."""
        # Route through main loop for thread safety
        try:
            self.root.after(0, self.update_scanvault_listbox)
        except Exception:
            self.update_scanvault_listbox()

    def update_quarantine_listbox(self):
        """Refresh the quarantine list with current files."""
        # Ensure executed in Tk main thread
        if threading.current_thread().name != 'MainThread':
            try:
                return self.root.after(0, self.update_quarantine_listbox)
            except Exception:
                pass
        
        old_count = self.quarantine_listbox.size()  # ✨ Get count before update
        
        self.quarantine_listbox.delete(0, "end")
        self.display_index_to_meta = {}

        if not os.path.exists(self.quarantine_folder):
            self._animate_quarantine_count(0)  # ✨ Animate to 0
            # Show "No Quarantined Files" message in metadata panel
            self.quarantine_detail_text.config(state="normal")
            self.quarantine_detail_text.delete("1.0", "end")
            self.quarantine_detail_text.insert("1.0", "📁 No Quarantined Files\n\nYour system is currently clean.\nQuarantined files will appear here when threats are detected.")
            self.quarantine_detail_text.config(state="disabled")
            return

        # Get and sort quarantined files by creation time
        files = [f for f in os.listdir(self.quarantine_folder) if f.endswith(".quarantined")]
        files.sort(key=lambda f: os.path.getctime(os.path.join(self.quarantine_folder, f)))

        for index, file in enumerate(files, start=1):
            base_name = file[:-12]  # Remove '.quarantined'
            meta_file = os.path.join(self.quarantine_folder, file + ".meta")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    original_path = meta.get("original_path", "Unknown")
                    display = f"{index}. File: {base_name}\n→ From: {original_path}"
                    self.quarantine_listbox.insert("end", display)
                    self.display_index_to_meta[self.quarantine_listbox.size() - 1] = meta_file
                except Exception as e:
                    print(f"[WARNING] Failed to load metadata for {file}: {e}")
        
        # ✨ Animate counter update (smooth counting effect)
        new_count = len(files)
        self._animate_quarantine_count(new_count)
        
        # Show "No Quarantined Files" message if empty
        if new_count == 0:
            self.quarantine_detail_text.config(state="normal")
            self.quarantine_detail_text.delete("1.0", "end")
            self.quarantine_detail_text.insert("1.0", "📁 No Quarantined Files\n\nYour system is currently clean.\nQuarantined files will appear here when threats are detected.")
            self.quarantine_detail_text.config(state="disabled")

    def update_scanvault_listbox(self):
        """Rebuild ScanVault list (pending + history) newest first, with status suffix for completed."""
        if not hasattr(self, 'scanvault_listbox'):
            return
        # Marshal to main thread if called from worker
        if threading.current_thread().name != 'MainThread':
            try:
                return self.root.after(0, self.update_scanvault_listbox)
            except Exception:
                pass
        self.scanvault_listbox.delete(0, 'end')
        self.vault_index_to_meta = {}
        if not os.path.isdir(self.scanvault_folder):
            return
        entries = []  # (dt, display_text, meta_path)
        # Pending (.vaulted)
        for f in os.listdir(self.scanvault_folder):
            if not f.endswith('.vaulted'):
                continue
            meta = os.path.join(self.scanvault_folder, f + '.meta')
            if not os.path.exists(meta):
                continue
            try:
                with open(meta, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                ts = data.get('timestamp', '')
                try:
                    dt_key = time.mktime(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))
                except Exception:
                    dt_key = os.path.getctime(meta)
                fname = os.path.basename(data.get('vaulted_path', f))
                display = f"{fname} | {ts}"
                entries.append((dt_key, display, meta))
            except Exception:
                continue
        # History (.meta in history)
        history_dir = os.path.join(self.scanvault_folder, 'history')
        if os.path.isdir(history_dir):
            for f in os.listdir(history_dir):
                if not f.endswith('.meta'):
                    continue
                meta = os.path.join(history_dir, f)
                try:
                    with open(meta, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                    ts = data.get('timestamp', '')
                    try:
                        dt_key = time.mktime(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))
                    except Exception:
                        dt_key = os.path.getctime(meta)
                    fname = os.path.basename(data.get('vaulted_path', data.get('file_name', f)))
                    status = data.get('final_status')
                    suffix = ''
                    if status:
                        s = str(status).lower()
                        if s == 'quarantined':
                            suffix = ' — quarantined'
                        elif s == 'restored':
                            suffix = ' — restored'
                        elif s == 'duplicate_suppressed':
                            suffix = ' — duplicate suppressed'
                        elif s == 'clean':
                            suffix = ' — ✅ clean (scanned)'
                    display = f"{fname} | {ts}{suffix}"
                    entries.append((dt_key, display, meta))
                except Exception:
                    continue
        entries.sort(key=lambda x: x[0], reverse=True)
        for _, display, meta in entries:
            self.scanvault_listbox.insert('end', display)
            self.vault_index_to_meta[self.scanvault_listbox.size() - 1] = meta

    def delete_selected_vault(self):
        sel = self.scanvault_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        meta_path = self.vault_index_to_meta.get(idx)
        if not meta_path:
            return
        try:
            history_dir = os.path.join(self.scanvault_folder, 'history')
            if os.path.commonpath([os.path.abspath(meta_path), os.path.abspath(history_dir)]) == os.path.abspath(history_dir):
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            else:
                vaulted_path = meta_path[:-5] if meta_path.endswith('.meta') else meta_path
                if os.path.exists(vaulted_path):
                    try:
                        os.remove(vaulted_path)
                    except Exception:
                        pass
                if os.path.exists(meta_path):
                    os.remove(meta_path)
        except Exception as e:
            print(f"[WARNING] Failed to delete vault item: {e}")
        finally:
            self.update_scanvault_listbox()

    def clear_vault_history(self):
        try:
            history_dir = os.path.join(self.scanvault_folder, 'history')
            if os.path.isdir(history_dir):
                for f in os.listdir(history_dir):
                    if f.endswith('.meta'):
                        try:
                            os.remove(os.path.join(history_dir, f))
                        except Exception:
                            pass
            self.update_scanvault_listbox()
        except Exception as e:
            print(f"[WARNING] Failed to clear vault history: {e}")
    
    def _animate_quarantine_count(self, target_count):
        """✨ Animate quarantine file counter with smooth counting effect (no flickering)."""
        try:
            current_text = self.quarantine_count_label.cget("text")
            current_count = int(current_text.strip("()")) if current_text.strip("()").isdigit() else 0
            
            # If count unchanged, no animation needed
            if current_count == target_count:
                return
            
            # Animate counting (increment or decrement)
            step = 1 if target_count > current_count else -1
            
            def _update_count():
                nonlocal current_count
                if current_count != target_count:
                    current_count += step
                    self.quarantine_count_label.config(text=f"({current_count})")
                    self.root.after(30, _update_count)  # 30ms per step for smooth effect
            
            _update_count()
        except Exception:
            # Fallback to instant update on error
            self.quarantine_count_label.config(text=f"({target_count})")
    
    def update_scanning_animation(self):
        """🔍 Update scanning animation indicator based on ScanVault queue status."""
        try:
            from utils.scanvault_queue import get_queue_count
            
            # Get queue size from queue file
            queue_size = get_queue_count()
            
            if queue_size > 0:
                # Show animated scanning indicator
                dots = ["●", "● ●", "● ● ●", "● ●"]
                dot_index = self._scanning_animation_frame % len(dots)
                self.scanning_indicator.config(text=f"🔍 Scanning: {queue_size} file(s) {dots[dot_index]}")
                self._scanning_animation_frame += 1
            else:
                # Hide indicator when queue is empty
                self.scanning_indicator.config(text="")
                self._scanning_animation_frame = 0
        except Exception:
            # Silent fail - don't break UI if animation fails
            self.scanning_indicator.config(text="")
        
        # Update every 400ms for smooth animation
        self.root.after(400, self.update_scanning_animation)
