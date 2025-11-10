

# # ##############################################################################################


# import os, threading, base64, time, shutil, traceback
# from tkinter import Frame, Button, Label, Text, Canvas, filedialog
# from tkinter.ttk import Progressbar

# from Scanning.yara_engine import fetch_and_generate_yara_rules, compile_yara_rules
# from Scanning.quarantine import quarantine_file
# from utils.tooltip import Tooltip
# from utils.logger import log_message
# import yara
# import os
# from datetime import datetime
# import shutil
# import json

# from Scanning.scanner_core import scan_file_for_realtime 


# class ScanPage(Frame):
#     def __init__(self, root, switch_page_callback):
#         super().__init__(root, bg="#009AA5")
#         self.root = root
#         self.switch_page_callback = switch_page_callback

#         self.target_path = None
#         self.rules = None
#         self.stop_scan = False

#         self.build_ui()
#         fetch_and_generate_yara_rules(self.log)
#         self.root.after(100, self.load_rules)

#     def build_ui(self):
#         # Back Button
#         back_btn = Button(self, text="← Back", command=lambda: self.switch_page_callback("home"),
#                           bg="gold", fg="white", font=("Inter", 12))
#         back_btn.place(x=10, y=10, width=80, height=30)

#         # LOAD TEXT log box
#         self.LOAD_TEXT = Text(self,bd=0, bg="#D9D9D9", fg="black", wrap="word",highlightthickness=0)
#         self.LOAD_TEXT.place(x=302, y=10, width=600, height=100)

#         # Select File Button
#         Button(self, text="Select Target File", command=self.select_file).place(x=302, y=139, width=125, height=40)
#         label_file = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         label_file.place(x=432, y=139)
#         Tooltip(label_file, "Choose a file to scan with YARA rules.")

#         # Select Folder Button
#         Button(self, text="Select Target Folder", command=self.select_folder).place(x=302, y=195, width=125, height=40)
#         label_folder = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         label_folder.place(x=432, y=195)
#         Tooltip(label_folder, "Choose a folder to scan recursively")

#         # Start Scan Button
#         Button(self, text="Scan", command=self.start_scan_thread, bg="green", fg="white").place(x=485, y=150, width=73, height=25)
#         label_start = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         label_start.place(x=570, y=150)
#         Tooltip(label_start, "Start the scanning immediately.")

#         # Stop Button
#         Button(self, text="Stop", command=self.stop_scan_thread, bg="red", fg="white").place(x=485, y=195, width=73, height=25)
#         label_stop = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         label_stop.place(x=570, y=195)
#         Tooltip(label_stop, "Stop the scanning immediately.")

#         # Quarantine Navigation Button
#         Button(self, text="Show Quarantined Files", command=lambda: self.switch_page_callback("monitor"),
#                bg="purple", fg="white", font=("Inter", 12)).place(x=700, y=195, width=200, height=40)
#         label_quarantine = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         label_quarantine.place(x=910, y=195)
#         Tooltip(label_quarantine, "View files moved to quarantine after detection")

#         # Progress bar
#         self.progress_label = Label(self, text="PROGRESS : 0%", bg="#12e012", fg="#000000", font=("Inter", 12))
#         self.progress_label.place(x=476, y=311)

#         self.progress = Progressbar(self, orient="horizontal", length=350, mode="determinate")
#         self.progress.place(x=354, y=350)

#         # Matched Files section
#         matched_canvas = Canvas(self, bg="#AE0505", height=54, width=485, bd=0, highlightthickness=0, relief="ridge")
#         matched_canvas.place(x=0, y=432)
#         matched_canvas.create_text(164, 15, anchor="nw", text="MATCHED FILES", fill="#FFFFFF", font=("Inter", 20 * -1))

#         self.matched_text = Text(self, bg="#F0CDCD", fg="#000000", wrap="word")
#         self.matched_text.place(x=0, y=488, width=485, height=232)

#         # Tested Files section
#         tested_canvas = Canvas(self, bg="#0A8D05", height=54, width=485, bd=0, highlightthickness=0, relief="ridge")
#         tested_canvas.place(x=557, y=432)
#         tested_canvas.create_text(164, 15, anchor="nw", text="TESTED FILES", fill="#FFFFFF", font=("Inter", 20 * -1))

#         self.tested_text = Text(self, bg="#B6F7AD", fg="#000000", wrap="word")
#         self.tested_text.place(x=557, y=488, width=485, height=232)

#     def log(self, msg, target="load"):
#         log_message(msg)
#         if target == "load":
#             self.LOAD_TEXT.insert("end", msg + "\n")
#         elif target == "matched":
#             self.matched_text.insert("end", msg + "\n")
#             self.matched_text.see("end")
            
#         elif target == "tested":
#             self.tested_text.insert("end", msg + "\n")
#             self.tested_text.see("end")  

#     def select_file(self):
#         path = filedialog.askopenfilename()
#         if path:
#             self.target_path = path
#             self.LOAD_TEXT.delete("1.0", "end")
#             self.log(f"[INFO] Selected file: {path}", "load")

#     def select_folder(self):
#         path = filedialog.askdirectory()
#         if path:
#             self.target_path = path
#             self.LOAD_TEXT.delete("1.0", "end")
#             self.log(f"[INFO] Selected folder: {path}", "load")

#     def start_scan_thread(self):
#         self.stop_scan = False
#         thread = threading.Thread(target=self.scan, daemon=True)
#         thread.start()

#     def stop_scan_thread(self):
#         self.stop_scan = True
#         self.log("[INFO] Scan stop requested.", "load")

#     def load_rules(self):
#         self.rules = compile_yara_rules(log_func=self.log)

#     def scan(self):
#         if not self.rules:
#             self.log("[ERROR] No YARA rules loaded.", "load")
#             return
#         if not self.target_path:
#             self.log("[ERROR] No target path selected.", "load")
#             return

#         self.matched_text.delete("1.0", "end")
#         self.tested_text.delete("1.0", "end")

#         if os.path.isfile(self.target_path):
#             self.scan_file(self.target_path)
#         elif os.path.isdir(self.target_path):
#             self.scan_directory(self.target_path)

#         self.progress.stop()
#         self.progress_label.config(text="Scan Complete!")

#     def scan_directory(self, directory):
#         files = []
#         for root, _, filenames in os.walk(directory):
#             for f in filenames:
#                 files.append(os.path.join(root, f))

#         total = len(files)
#         self.progress["maximum"] = total
#         self.progress["value"] = 0

#         for i, file_path in enumerate(files, 1):
#             if self.stop_scan:
#                 break
#             self.scan_file(file_path)
#             self.progress["value"] = i
#             percent = int((i / total) * 100)
#             self.progress_label.config(text=f"PROGRESS : {percent}%")
#             self.root.update_idletasks()

#     # def scan_file(self, path):
#     #     try:
#     #         matches = self.rules.match(path, timeout=60)
#     #         self.log(path, "tested")
#     #         if matches:
#     #             rule = matches[0].rule
#     #             self.log(f"[MATCH] {path} => Rule: {rule}", "matched")
#     #             quarantine_file(path, matched_rules=[rule])
#     #     except Exception as e:
#     #         self.log(f"[ERROR] Failed to scan {path}:\n{traceback.format_exc()}", "tested")

#     def scan_file(self, path):
#         self.log(path, "tested")
#         matched, rule, qpath, meta_path = scan_file_for_realtime(path)
#         if matched:
#             self.log(f"[MATCH] {path} => Rule: {rule}", "matched")



#     # def scan_file(self, file_path):
#     #     """Scan a single file using YARA rules and quarantine if matched."""
#     #     print(f"[DEBUG] Scanning file: {file_path}")
#     #     try:
#     #         with open(file_path, "rb"):
#     #             pass
#     #     except Exception:
#     #         print(f"[WARNING] Cannot open file: {file_path}")
#     #         return

#     #     # Compile rules
#     #     rule_paths = {}
#     #     yara_dir = os.path.join("assets", "yara")
#     #     for category in os.listdir(yara_dir):
#     #         cat_path = os.path.join(yara_dir, category)
#     #         for rule in os.listdir(cat_path):
#     #             if rule.endswith(".yar") or rule.endswith(".yara"):
#     #                 key = f"{category}_{rule}"
#     #                 rule_paths[key] = os.path.join(cat_path, rule)

#     #     try:
#     #         rules = yara.compile(filepaths=rule_paths)
#     #         matches = rules.match(filepath=file_path)
#     #     except Exception as e:
#     #         print(f"[ERROR] YARA scan failed: {e}")
#     #         return

#     #     if matches:
#     #         log_message(f"[MATCH] {file_path} matched {matches}")
#     #         self.quarantine_file(file_path, [str(m) for m in matches])
#     #         self.update_quarantine_listbox()
#     #         self.notify_threat_detected(file_path, matches)







# ##############################################################################################


import os, threading, base64, time, shutil, traceback
from tkinter import Frame, Button, Label, Text, Canvas, filedialog
from tkinter.ttk import Progressbar

from Scanning.yara_engine import fetch_and_generate_yara_rules, compile_yara_rules
from Scanning.quarantine import quarantine_file
from utils.tooltip import Tooltip
from utils.logger import log_message
from utils.notify import notify, show_app_notification
from utils.settings import SETTINGS
import yara
import os
from datetime import datetime
import shutil
import json

from Scanning.scanner_core import scan_file_for_realtime 


class ScanPage(Frame):
    def __init__(self, root, switch_page_callback, app_ref=None):
        super().__init__(root, bg="#009AA5")
        self.root = root
        self.switch_page_callback = switch_page_callback
        self.app_ref = app_ref  # Reference to main app for tray access

        self.target_path = None
        self.rules = None
        self.stop_scan = False

        self.build_ui()
        
        # ✨ Show loading spinner during YARA rule fetch
        self._show_loading_spinner("Loading YARA rules...")
        
        # Fetch and compile rules, showing only one relevant message for each step
        fetch_status, fetch_count = fetch_and_generate_yara_rules(lambda msg: None)  # suppress direct log
        rules, compile_count = compile_yara_rules(log_func=lambda msg: None)  # suppress direct log
        
        # ✨ Hide spinner after loading complete
        self._hide_loading_spinner()
        
        # Simplified UI message: hide internal method details from end user
        if compile_count > 0 and fetch_status in ("remote", "local"):
            # Rules were fetched/loaded and compiled successfully
            self.log("Scanning system is up to date.")
        elif compile_count > 0:
            # Compiled rules present but fetch source uncertain
            self.log("Scanning system is ready.")
        else:
            # No rules available
            self.log("Scanning system: no YARA rules available. Please check configuration.")
        self.rules = rules

    # def build_ui(self):
    #     # Back Button
    #     back_btn = Button(self, text="← Back", command=lambda: self.switch_page_callback("home"),
    #                       bg="gold", fg="white", font=("Inter", 12))
    #     back_btn.place(x=10, y=10, width=80, height=30)

    #     # LOAD TEXT log box
    #     self.LOAD_TEXT = Text(self,bd=0, bg="#D9D9D9", fg="black", wrap="word",highlightthickness=0)
    #     self.LOAD_TEXT.place(x=302, y=10, width=600, height=100)

    #     # Select File Button
    #     Button(self, text="Select Target File", command=self.select_file).place(x=302, y=139, width=125, height=40)
    #     label_file = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
    #     label_file.place(x=432, y=139)
    #     Tooltip(label_file, "Choose a file to scan with YARA rules.")

    #     # Select Folder Button
    #     Button(self, text="Select Target Folder", command=self.select_folder).place(x=302, y=195, width=125, height=40)
    #     label_folder = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
    #     label_folder.place(x=432, y=195)
    #     Tooltip(label_folder, "Choose a folder to scan recursively")

    #     # Start Scan Button
    #     Button(self, text="Scan", command=self.start_scan_thread, bg="green", fg="white").place(x=485, y=150, width=73, height=25)
    #     label_start = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
    #     label_start.place(x=570, y=150)
    #     Tooltip(label_start, "Start the scanning immediately.")

    #     # Stop Button
    #     Button(self, text="Stop", command=self.stop_scan_thread, bg="red", fg="white").place(x=485, y=195, width=73, height=25)
    #     label_stop = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
    #     label_stop.place(x=570, y=195)
    #     Tooltip(label_stop, "Stop the scanning immediately.")

    #     # Quarantine Navigation Button
    #     Button(self, text="Show Quarantined Files", command=lambda: self.switch_page_callback("monitor"),
    #            bg="purple", fg="white", font=("Inter", 12)).place(x=700, y=195, width=200, height=40)
    #     label_quarantine = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
    #     label_quarantine.place(x=910, y=195)
    #     Tooltip(label_quarantine, "View files moved to quarantine after detection")

    #     # Progress bar
    #     self.progress_label = Label(self, text="PROGRESS : 0%", bg="#12e012", fg="#000000", font=("Inter", 12))
    #     self.progress_label.place(x=476, y=311)

    #     self.progress = Progressbar(self, orient="horizontal", length=350, mode="determinate")
    #     self.progress.place(x=354, y=350)

    #     # Matched Files section
    #     matched_canvas = Canvas(self, bg="#AE0505", height=54, width=485, bd=0, highlightthickness=0, relief="ridge")
    #     matched_canvas.place(x=0, y=432)
    #     matched_canvas.create_text(164, 15, anchor="nw", text="MATCHED FILES", fill="#FFFFFF", font=("Inter", 20 * -1))

    #     self.matched_text = Text(self, bg="#F0CDCD", fg="#000000", wrap="word")
    #     self.matched_text.place(x=0, y=488, width=485, height=232)

    #     # Tested Files section
    #     tested_canvas = Canvas(self, bg="#0A8D05", height=54, width=485, bd=0, highlightthickness=0, relief="ridge")
    #     tested_canvas.place(x=557, y=432)
    #     tested_canvas.create_text(164, 15, anchor="nw", text="TESTED FILES", fill="#FFFFFF", font=("Inter", 20 * -1))

    #     self.tested_text = Text(self, bg="#B6F7AD", fg="#000000", wrap="word")
    #     self.tested_text.place(x=557, y=488, width=485, height=232)



    def build_ui(self):
        # === Top Navigation ===
        nav_frame = Frame(self, bg="#009AA5")
        nav_frame.pack(fill="x", pady=5, padx=5)

        # Button(nav_frame, text="← Back", command=lambda: self.switch_page_callback("home"),
        #     bg="gold", fg="white", font=("Inter", 12)).pack(side="left")
        # 🔹 Title
        Label(nav_frame, text="Scanning page ", font=("Arial", 24),
            bg="#009AA5", fg="white").pack(side="top",expand=True,fill='both')
        
        Button(nav_frame, text="Show Quarantined Files", command=lambda: self.switch_page_callback("monitor"),
            bg="purple", fg="white", font=("Inter", 12)).pack(side="right", padx=(0, 10))

        # === Load Log Box ===
        log_frame = Frame(self, bg="#009AA5")
        log_frame.pack(fill="x", padx=10)

        self.LOAD_TEXT = Text(log_frame, height=6, bg="#D9D9D9", fg="black", wrap="word", highlightthickness=0)
        self.LOAD_TEXT.pack(fill="x", expand=True)

        # === File/Folder Controls ===
        control_frame = Frame(self, bg="#009AA5")
        control_frame.pack(fill="x", padx=10, pady=10)

        self._add_button_with_tooltip(control_frame, "Select Target File", self.select_file,
                                    "Choose a file to scan with YARA rules.")
        self._add_button_with_tooltip(control_frame, "Select Target Folder", self.select_folder,
                                    "Choose a folder to scan recursively")
        self._add_button_with_tooltip(control_frame, "Scan", self.start_scan_thread,
                                    "Start the scanning immediately.", bg="green", fg="white")
        self._add_button_with_tooltip(control_frame, "Stop", self.stop_scan_thread,
                                    "Stop the scanning immediately.", bg="red", fg="white")

        # === Progress Bar ===
        progress_frame = Frame(self, bg="#009AA5")
        progress_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.progress_label = Label(progress_frame, text="PROGRESS : 0%", bg="#12e012", fg="#000000", font=("Inter", 12))
        self.progress_label.pack(anchor="w")

        # ✨ Custom progress bar with animation support
        self.progress = Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")
        
        # Configure custom style for animated stripes (creates professional look)
        try:
            from tkinter import ttk
            style = ttk.Style()
            style.theme_use('clam')  # Use clam theme for better customization
            style.configure("Animated.Horizontal.TProgressbar",
                          troughcolor='#E0E0E0',
                          background='#00AA00',  # Green progress
                          bordercolor='#009AA5',
                          lightcolor='#00DD00',
                          darkcolor='#008800')
            self.progress.config(style="Animated.Horizontal.TProgressbar")
        except Exception:
            pass  # Fallback to default style if configuration fails
        
        # Animation state
        self._progress_animating = False

        # === Results Area (Matched / Tested) ===
        results_frame = Frame(self, bg="#009AA5")
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_result = Frame(results_frame, bg="#AE0505")
        left_result.pack(side="left", expand=True, fill="both", padx=5)

        Label(left_result, text="MATCHED FILES", bg="#AE0505", fg="white", font=("Inter", 16, "bold")).pack(fill="x")
        self.matched_text = Text(left_result, bg="#F0CDCD", fg="#000000", wrap="word")
        self.matched_text.pack(fill="both", expand=True)

        right_result = Frame(results_frame, bg="#0A8D05")
        right_result.pack(side="right", expand=True, fill="both", padx=5)

        # Header with Clear button
        tested_header = Frame(right_result, bg="#0A8D05")
        tested_header.pack(fill="x")
        
        Label(tested_header, text="TESTED FILES", bg="#0A8D05", fg="white", font=("Inter", 16, "bold")).pack(side="left", padx=5)
        
        # Clear History button
        clear_btn = Button(tested_header, text="🗑️ Clear", command=self.clear_tested_history,
                          bg="#FF6600", fg="white", font=("Inter", 10, "bold"),
                          relief="raised", cursor="hand2")
        clear_btn.pack(side="right", padx=5, pady=2)
        Tooltip(clear_btn, "Clear the tested files history")
        
        self.tested_text = Text(right_result, bg="#B6F7AD", fg="#000000", wrap="word")
        self.tested_text.pack(fill="both", expand=True)



    def _add_button_with_tooltip(self, parent, text, command, tooltip, bg=None, fg=None):
        btn = Button(parent, text=text, command=command, bg=bg, fg=fg, relief="raised", bd=2)
        btn.pack(side="left", padx=5)
        
        # ✨ Add click animation (press-down effect)
        self._add_button_click_effect(btn)
        
        tip_label = Label(parent, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        tip_label.pack(side="left", padx=(0, 10))
        Tooltip(tip_label, tooltip)
    
    def _add_button_click_effect(self, button):
        """Add subtle press-down effect on button click (no flickering)."""
        def on_press(e):
            button.config(relief="sunken")
        
        def on_release(e):
            button.config(relief="raised")
        
        button.bind("<ButtonPress-1>", on_press)
        button.bind("<ButtonRelease-1>", on_release)








    def log(self, msg, target="load"):
        log_message(msg)
        if target == "load":
            self.LOAD_TEXT.insert("end", msg + "\n")
        elif target == "matched":
            self.matched_text.insert("end", msg + "\n")
            self.matched_text.see("end")
            
        elif target == "tested":
            self.tested_text.insert("end", msg + "\n")
            self.tested_text.see("end")  

    def select_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.target_path = path
            self.LOAD_TEXT.delete("1.0", "end")
            self.log(f"[INFO] Selected file: {path}", "load")

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.target_path = path
            self.LOAD_TEXT.delete("1.0", "end")
            self.log(f"[INFO] Selected folder: {path}", "load")

    def start_scan_thread(self):
        # ⚠️ Check if app is in view-only mode (license invalid/expired)
        if hasattr(self.app_ref, 'view_only_mode') and self.app_ref.view_only_mode:
            self.log("[ERROR] Scanning disabled: License invalid or expired", "load")
            try:
                from tkinter import messagebox
                messagebox.showerror(
                    "Scanning Disabled",
                    "Your license is invalid or expired.\n\n"
                    "Scanning features are disabled until you renew your license.\n\n"
                    "Contact support: https://bitss.one/contact"
                )
            except Exception:
                pass
            return
        
        self.stop_scan = False
        
        # ✨ Start progress bar pulse animation
        self._progress_animating = True
        self._animate_progress_pulse()
        
        thread = threading.Thread(target=self.scan, daemon=True)
        thread.start()

    def stop_scan_thread(self):
        self.stop_scan = True
        self._progress_animating = False  # ✨ Stop animation
        self.log("[INFO] Scan stop requested.", "load")
    
    def _animate_progress_pulse(self):
        """Create subtle pulsing animation on progress label during scan."""
        if not self._progress_animating:
            return
        
        try:
            # Alternate between two shades of green for subtle pulse (no flickering)
            current_bg = self.progress_label.cget("bg")
            new_bg = "#10d010" if current_bg == "#12e012" else "#12e012"
            self.progress_label.config(bg=new_bg)
            
            # Continue animation every 800ms (slow, smooth pulse)
            self.root.after(800, self._animate_progress_pulse)
        except Exception:
            pass  # Silent fail to prevent animation errors

    def clear_tested_history(self):
        """Clear the tested files history."""
        try:
            self.tested_text.delete("1.0", "end")
            self.log("[INFO] Tested files history cleared.", "load")
            log_message("[SCAN] Tested files history cleared by user.")
        except Exception as e:
            log_message(f"[ERROR] Failed to clear tested history: {e}")

    def load_rules(self):
        self.rules = compile_yara_rules(log_func=self.log)

    def scan(self):
        if not self.rules:
            self.log("[ERROR] No YARA rules loaded.", "load")
            return
        if not self.target_path:
            self.log("[ERROR] No target path selected.", "load")
            return

        self.matched_text.delete("1.0", "end")
        self.tested_text.delete("1.0", "end")

        # Update tray tooltip
        if self.app_ref and hasattr(self.app_ref, 'tray_icon') and self.app_ref.tray_icon:
            try:
                self.app_ref.tray_icon.update_tooltip(f"VWAR - Scanning: {os.path.basename(self.target_path)}")
            except Exception:
                pass
        
        # Notify scan started (notify is now fully non-blocking)
        if SETTINGS.tray_notifications:
            try:
                notify("🔍 VWAR Scan Started", f"Scanning: {os.path.basename(self.target_path)}")
            except Exception:
                pass

        matches_found = 0
        total_scanned = 0
        
        if os.path.isfile(self.target_path):
            total_scanned = 1
            if self.scan_file(self.target_path):
                matches_found += 1
        elif os.path.isdir(self.target_path):
            matches_found, total_scanned = self.scan_directory(self.target_path)

        self.progress.stop()
        self.progress_label.config(text="Scan Complete!")
        
        # Reset tray tooltip
        if self.app_ref and hasattr(self.app_ref, 'tray_icon') and self.app_ref.tray_icon:
            try:
                self.app_ref.tray_icon.update_tooltip("VWAR")
            except Exception:
                pass
        
        # Notify scan complete with total files scanned (notify is now fully non-blocking)
        if SETTINGS.tray_notifications:
            try:
                if matches_found > 0:
                    notify("🛡️ VWAR Scan Complete", 
                           f"Scanned {total_scanned} file(s)\nFound {matches_found} threat(s)!")
                else:
                    notify("✅ VWAR Scan Complete", 
                           f"Scanned {total_scanned} file(s)\nNo threats detected. System is clean.")
            except Exception:
                pass

    def scan_directory(self, directory):
        files = []
        for root, _, filenames in os.walk(directory):
            for f in filenames:
                files.append(os.path.join(root, f))

        total = len(files)
        self.progress["maximum"] = total
        self.progress["value"] = 0
        
        matches_count = 0
        for i, file_path in enumerate(files, 1):
            if self.stop_scan:
                break
            if self.scan_file(file_path):
                matches_count += 1
            self.progress["value"] = i
            percent = int((i / total) * 100)
            self.progress_label.config(text=f"PROGRESS : {percent}% ({i}/{total})")
            self.root.update_idletasks()
        
        # Return both matches count and total scanned
        files_scanned = i if self.stop_scan else total
        return matches_count, files_scanned

    def scan_file(self, path):
        self.log(path, "tested")
        result = scan_file_for_realtime(path)
        # Backwards compatibility still allows tuple, but we prefer named fields
        matched, rule, qpath, meta_path = result[:4]
        status = getattr(result, 'status', 'UNKNOWN')

        if matched:
            self.log(f"[MATCH] {path} => Rule: {rule}", "matched")
            # Notify threat detected (notify is now fully non-blocking)
            if SETTINGS.tray_notifications:
                try:
                    notify("⚠️ Threat Detected!", f"Rule: {rule}\nFile: {os.path.basename(path)}")
                except Exception:
                    pass
            
            # ✨ Show animated in-app notification for threats
            try:
                show_app_notification(
                    self.root, 
                    "⚠️ Threat Detected!",
                    f"Rule: {rule}\nFile: {os.path.basename(path)}",
                    duration=6000,
                    bg_color="#CC0000",  # Red for danger
                    title_color="white"
                )
            except Exception:
                pass  # Silent fail if notification error
            
            return True  # Return True if threat found
        else:
            if status == "NO_RULES":
                self.log(f"[WARN] Rules not loaded when scanning: {path}", "tested")
            elif status == "SKIPPED_INTERNAL":
                self.log(f"[SKIP] Internal rule file skipped: {path}", "tested")
            elif status == "QUARANTINE_FAILED":
                self.log(f"[WARNING] Match but quarantine failed: {path} (rule={rule})", "tested")
            elif status == "YARA_ERROR":
                self.log(f"[WARNING] YARA engine error on: {path}", "tested")
            elif status == "ERROR":
                self.log(f"[ERROR] Unexpected failure scanning: {path}", "tested")
            # CLEAN is silent except already logged as tested
            return False  # Return False if no threat

    def _show_loading_spinner(self, message="Loading..."):
        """Display animated loading spinner overlay."""
        try:
            from tkinter import Toplevel
            
            self._spinner_window = Toplevel(self.root)
            self._spinner_window.title("")
            self._spinner_window.overrideredirect(True)  # Remove window decorations
            self._spinner_window.config(bg="#009AA5")
            
            # Center on screen
            width, height = 300, 100
            x = (self._spinner_window.winfo_screenwidth() // 2) - (width // 2)
            y = (self._spinner_window.winfo_screenheight() // 2) - (height // 2)
            self._spinner_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Message label
            Label(self._spinner_window, text=message, font=("Arial", 12, "bold"),
                  bg="#009AA5", fg="white").pack(pady=15)
            
            # Animated dots
            self._spinner_label = Label(self._spinner_window, text="●", font=("Arial", 24),
                                       bg="#009AA5", fg="white")
            self._spinner_label.pack()
            
            self._spinner_active = True
            self._animate_spinner_dots()
            
            self.root.update()
        except Exception:
            pass  # Silent fail if spinner creation fails
    
    def _animate_spinner_dots(self):
        """Animate spinner dots (● ● ●)."""
        if not hasattr(self, '_spinner_active') or not self._spinner_active:
            return
        
        try:
            dots = ["●", "● ●", "● ● ●", "● ●"]
            current_text = self._spinner_label.cget("text")
            current_index = dots.index(current_text) if current_text in dots else 0
            next_index = (current_index + 1) % len(dots)
            self._spinner_label.config(text=dots[next_index])
            
            self.root.after(300, self._animate_spinner_dots)  # Update every 300ms
        except Exception:
            pass
    
    def _hide_loading_spinner(self):
        """Hide and destroy loading spinner."""
        try:
            self._spinner_active = False
            if hasattr(self, '_spinner_window'):
                self._spinner_window.destroy()
        except Exception:
            pass












