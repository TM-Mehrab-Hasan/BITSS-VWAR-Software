import os
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from utils.path_utils import resource_path

class HelpPage(tk.Frame):
    """Modern tabbed Help page with comprehensive documentation.
    
    Features:
    - Tabbed interface (Getting Started, Features, FAQ, Troubleshooting, Contact)
    - Color scheme matches app theme (#009AA5, #004d4d)
    - PDF guide access button
    - Searchable content
    """
    COMMON_FILENAMES = [
        "Vwar User Manual.pdf", "Guide.pdf", "UserGuide.pdf", "VWAR_Guide.pdf", "VWAR_User_Guide.pdf",
    ]

    def __init__(self, parent, app):
        super().__init__(parent, bg="#009AA5")
        self.app = app

        super().__init__(parent, bg="#009AA5")
        self.app = app

        # Header
        header_frame = tk.Frame(self, bg="#004d4d")
        header_frame.pack(fill="x", pady=0)
        
        header = tk.Label(
            header_frame, 
            text="❓ Help & Documentation", 
            font=("Arial", 20, "bold"), 
            bg="#004d4d", 
            fg="white"
        )
        header.pack(pady=15)
        
        sub = tk.Label(
            header_frame,
            text="Learn how to use VWAR Scanner effectively",
            font=("Arial", 11),
            bg="#004d4d",
            fg="#cccccc"
        )
        sub.pack(pady=(0, 15))

        # Create notebook (tabbed interface)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Custom.TNotebook', background='#009AA5', borderwidth=0)
        style.configure('Custom.TNotebook.Tab', 
                       background='#007777', 
                       foreground='white',
                       padding=[20, 10],
                       font=('Arial', 11, 'bold'))
        style.map('Custom.TNotebook.Tab',
                 background=[('selected', '#009AA5')],
                 foreground=[('selected', 'white')])

        self.notebook = ttk.Notebook(self, style='Custom.TNotebook')
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        self._create_getting_started_tab()
        self._create_features_tab()
        self._create_faq_tab()
        self._create_troubleshooting_tab()
        self._create_contact_tab()

        # Bottom bar with PDF button
        bottom_frame = tk.Frame(self, bg="#004d4d")
        bottom_frame.pack(fill="x", side="bottom")
        
        pdf_frame = tk.Frame(bottom_frame, bg="#004d4d")
        pdf_frame.pack(pady=10)
        
        files = self._find_guides()
        pdf_path = files.get("pdf")
        pdf_name = files.get("pdf_name") or "User Manual"
        
        if pdf_path:
            tk.Button(
                pdf_frame,
                text=f"📄 Open PDF Guide ({pdf_name})",
                command=lambda: self._open_file(pdf_path),
                bg="#007777",
                fg="white",
                font=("Arial", 11, "bold"),
                padx=20,
                pady=8,
                relief="flat",
                cursor="hand2"
            ).pack(side="left", padx=5)
            
            tk.Button(
                pdf_frame,
                text="📁 Show in Folder",
                command=lambda: self._open_folder(os.path.dirname(pdf_path)),
                bg="#555555",
                fg="white",
                font=("Arial", 10),
                padx=15,
                pady=8,
                relief="flat",
                cursor="hand2"
            ).pack(side="left", padx=5)
        else:
            tk.Label(
                pdf_frame,
                text="⚠️ PDF User Manual not found",
                bg="#004d4d",
                fg="#ffcc00",
                font=("Arial", 10)
            ).pack()

    def _create_getting_started_tab(self):
        """Getting Started tab with quick start guide."""
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="🚀 Getting Started")
        
        # Scrollable text area
        container = tk.Frame(tab, bg="white")
        container.pack(fill="both", expand=True, padx=20, pady=15)
        
        text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="white",
            fg="#222",
            relief="flat",
            padx=15,
            pady=15
        )
        text.pack(fill="both", expand=True)
        
        content = """
🚀 QUICK START GUIDE

Welcome to VWAR Scanner! Follow these steps to get started:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1: ACTIVATION
• VWAR requires activation with a valid license key
• Enter your license key when prompted on first launch
• License is bound to your hardware for security
• Contact support@bobosohomail.com if you need a license

STEP 2: UNDERSTAND THE INTERFACE
• Home: View license status and monitoring status
• Scan: Manually scan files or folders
• Backup: Create and restore file backups
• Scan Vault: Review files being scanned
• Help: Access this documentation
• Schedule Scan: Configure automatic scanning

STEP 3: REAL-TIME PROTECTION
• VWAR automatically monitors your Downloads, Desktop, and Documents
• New files are captured and scanned before you use them
• Detected threats are automatically quarantined
• A system tray icon shows VWAR is running

STEP 4: MANUAL SCANNING
• Go to the "Scan" page
• Click "Browse" to select files or folders
• Click "Start Scan" to begin scanning
• View results and take action on detected threats

STEP 5: SCHEDULE AUTOMATIC SCANS
• Go to "Schedule Scan" page
• Choose frequency (Hourly, Daily, Custom)
• Set time and paths to scan
• Click "Save" to activate scheduled scanning

STEP 6: SYSTEM TRAY
• VWAR runs in the system tray for continuous protection
• Click X to minimize to tray (doesn't close the app)
• Right-click tray icon for quick actions
• Use "Quit VWAR" button in sidebar to exit completely

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 IMPORTANT TIPS:
✓ Keep VWAR running for continuous protection
✓ Don't disable real-time monitoring during downloads
✓ Review quarantined files regularly
✓ Update VWAR when prompted for latest protection
✓ Run VWAR as Administrator for full functionality

"""
        text.insert("1.0", content)
        text.config(state="disabled")

    def _create_features_tab(self):
        """Features tab with detailed feature explanations."""
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="📚 Features")
        
        container = tk.Frame(tab, bg="white")
        container.pack(fill="both", expand=True, padx=20, pady=15)
        
        text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="white",
            fg="#222",
            relief="flat",
            padx=15,
            pady=15
        )
        text.pack(fill="both", expand=True)
        
        content = """
📚 VWAR SCANNER FEATURES

Complete overview of all VWAR Scanner capabilities:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛡️ REAL-TIME PROTECTION

Monitors your system 24/7 for new and modified files:
• Watches Downloads, Desktop, Documents folders
• Monitors all non-system drives (D:, E:, etc.)
• Scans files immediately upon creation/modification
• Uses C++ monitor for high-performance detection
• Minimal CPU and memory usage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 YARA-BASED DETECTION

Advanced threat detection using YARA rules:
• Detects ransomware, spyware, trojans, worms
• Identifies APT (Advanced Persistent Threats)
• Pattern matching for known malware signatures
• Regular rule updates for new threats
• Low false-positive rate

Supported threat types:
✓ Ransomware (file encryption malware)
✓ Spyware (data theft malware)
✓ Trojans (backdoor access)
✓ Worms (self-replicating malware)
✓ APT malware (targeted attacks)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 SCANVAULT SYSTEM

Innovative file isolation and scanning:
• Captures files before they execute
• Scans in isolated environment
• Restores clean files automatically
• Quarantines detected threats
• Prevents malware execution
• 🔧 Installation Mode for legitimate installers

How it works:
1. File created/downloaded → Moved to ScanVault
2. Scanned with YARA rules
3. If clean → Restored to original location
4. If threat → Moved to Quarantine

Installation Mode (NEW):
• Temporarily skips installer files
• Active for 10 minutes with countdown timer
• Reduces false positives during software installation
• Auto-deactivates after timer expires
• Toggle from "Scan Vault" page (orange button)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 QUARANTINE MANAGEMENT

Safe isolation of detected threats:
• Threats stored in secure quarantine folder
• Original location and metadata preserved
• Review quarantined items anytime
• Restore false positives if needed
• Permanent deletion option
• Re-scan on restore for verification

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ SCHEDULED SCANNING

Flexible automatic scanning options:
• Realtime: Continuous monitoring
• Hourly: Scan every hour at specified time
• Twice Daily: Scan at two set times
• Daily: Scan once per day
• Custom: Set custom interval in minutes

Features:
✓ Multiple path scanning
✓ Include/exclude subdirectories
✓ Background scanning (doesn't interfere with work)
✓ Last run timestamp tracking
✓ "Run Now" button for manual trigger

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💾 BACKUP & RESTORE

Protect your important files:
• Manual backup: Choose files/folders to backup
• Auto backup: Schedule automatic backups
• Restore: Recover files from backup
• Version history preserved
• Backup location configurable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 HARDWARE-LOCKED ACTIVATION

Secure license system:
• License bound to your PC hardware
• Prevents unauthorized sharing
• Online validation via secure API
• Automatic renewal checking
• Grace period for expiration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 SYSTEM TRAY INTEGRATION

Runs unobtrusively in background:
• Minimize to tray (click X)
• Quick access menu
• Status indicators
• Scan on demand
• Easy exit option

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 AUTOMATIC UPDATES

Stay protected with latest version:
• Update checker on startup
• Download link provided
• Version comparison
• Change log available
• Optional manual check

"""
        text.insert("1.0", content)
        text.config(state="disabled")

    def _create_faq_tab(self):
        """FAQ tab with common questions."""
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="❓ FAQ")
        
        container = tk.Frame(tab, bg="white")
        container.pack(fill="both", expand=True, padx=20, pady=15)
        
        text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="white",
            fg="#222",
            relief="flat",
            padx=15,
            pady=15
        )
        text.pack(fill="both", expand=True)
        
        content = """
❓ FREQUENTLY ASKED QUESTIONS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: How do I close VWAR Scanner?
A: Click the "Quit VWAR" button in the sidebar (bottom red button). 
   Clicking the X button minimizes to system tray instead of closing.
   This keeps your protection running in the background.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: Why does VWAR need administrator rights?
A: Administrator rights are required to:
   • Monitor system-wide file changes
   • Move files to/from quarantine
   • Access all drives and folders
   • Start system-level monitoring service

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: What if VWAR detects a false positive?
A: If a legitimate file is quarantined:
   1. Go to "Scan Vault" page
   2. Find the file in quarantine list
   3. Select it and click "Restore"
   4. VWAR will re-scan on restore
   5. If still detected, contact support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: How do I schedule automatic scans?
A: Go to "Schedule Scan" page:
   1. Choose frequency (Hourly, Daily, or Custom)
   2. Set time using hour/minute spinboxes
   3. Add paths to scan (click +Dir button)
   4. Enable "Include Subdirectories" if needed
   5. Click "Save"
   6. Use "Run Now" to test immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: Does VWAR slow down my computer?
A: VWAR is designed for minimal impact:
   • Uses efficient C++ monitor
   • Scans run in background thread
   • Only active during file operations
   • Typical CPU usage: <2%
   • Memory usage: ~50-100MB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: How often should I scan my computer?
A: Real-time protection is always active, but we recommend:
   • Daily scan: For average users
   • Twice daily: For heavy downloaders
   • Weekly full scan: For complete peace of mind
   • After visiting suspicious websites
   • Before opening email attachments

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: What happens when my license expires?
A: When license expires:
   • You'll see warnings 7 days before expiration
   • Scanning will be disabled after expiration
   • You can still view quarantine
   • Contact support to renew: support@bobosohomail.com
   • License validation happens every 6 hours

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: How many devices can I use with one license?
A: 🔹 Each license key supports up to 2 devices:
   • Device Slot 1: First device activation
   • Device Slot 2: Second device activation
   • Auto-allocation: System automatically assigns slots
   • Device limit: Maximum 2 devices per license
   • To use on a 3rd device: Deactivate one existing device first
   • Contact support to manage devices: support@bobosohomail.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: Can I use VWAR with other antivirus software?
A: Yes! VWAR is designed to complement existing security:
   • Works alongside Windows Defender
   • Compatible with most antivirus software
   • Provides additional YARA-based detection
   • ScanVault adds extra protection layer
   • No conflicts with other security tools

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: Where are quarantined files stored?
A: Quarantined files are in:
   • Folder: VWAR_exe_2/quarantine/
   • Files are renamed with timestamp
   • Metadata stored in .meta files
   • Safe to delete entire folder contents
   • Automatic cleanup not implemented (manual only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: How do I update VWAR Scanner?
A: VWAR checks for updates on startup:
   1. If update available, you'll see notification
   2. Click "Update Available" button
   3. Download latest version from GitHub
   4. Close VWAR
   5. Replace VWAR.exe with new version
   6. Restart VWAR

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: Can I exclude certain files/folders from scanning?
A: Yes! VWAR automatically excludes:
   • System folders (Windows, Program Files)
   • Recycle Bin
   • Temporary files
   • VWAR's own folders
   Future update will add custom exclusions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: What is Installation Mode?
A: 🔧 Installation Mode temporarily disables ScanVault for installer files:
   
   When to use:
   • Installing new software
   • Installing Windows updates
   • Running legitimate installers
   
   How it works:
   • Activate from "Scan Vault" page (orange button)
   • Active for 10 minutes (auto-deactivates)
   • Skips installer files (.msi, .exe, .dll, .sys, etc.)
   • Skips files in trusted installer folders
   • Regular files still scanned normally
   
   What gets skipped:
   ✓ Windows Installer folder files
   ✓ Windows Update files
   ✓ System installer directories
   ✓ User-defined trusted folders (future update)
   
   Timer display:
   • Shows countdown: "Installation Mode: ON (09:45)"
   • Auto-deactivates when timer reaches 00:00
   • Click button again to deactivate early
   
   Note: Installation Mode reduces false positives during software installation
         without compromising your overall protection.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: What file types does VWAR scan?
A: VWAR scans all files except:
   • System files (*.sys, *.dll in system folders)
   • Temporary files (*.tmp, *.log)
   • Partial downloads (*.crdownload, *.part)
   • VWAR's own files
   • Installer files (when Installation Mode active)
   All other files are checked for threats.

"""
        text.insert("1.0", content)
        text.config(state="disabled")

    def _create_troubleshooting_tab(self):
        """Troubleshooting tab with problem solutions."""
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="🔧 Troubleshooting")
        
        container = tk.Frame(tab, bg="white")
        container.pack(fill="both", expand=True, padx=20, pady=15)
        
        text = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="white",
            fg="#222",
            relief="flat",
            padx=15,
            pady=15
        )
        text.pack(fill="both", expand=True)
        
        content = """
🔧 TROUBLESHOOTING GUIDE

Common issues and solutions:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: VWAR won't start or crashes on startup

Solutions:
□ Run as Administrator (Right-click → Run as administrator)
□ Check if VWAR.exe is the correct filename
□ Verify Python 3.11.5+ is installed
□ Reinstall dependencies: pip install -r requirements.txt
□ Check antivirus isn't blocking VWAR
□ Look for error messages in console window

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: "Activation file not found" error

Solutions:
□ You need a valid license key
□ Contact support@bobosohomail.com for activation
□ Ensure data/ folder exists in VWAR directory
□ Don't delete activation.enc file
□ Check if activation was successful

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Real-time monitoring not working

Solutions:
□ Ensure VWAR has administrator rights
□ Check if monitoring toggle is ON (green)
□ Verify vwar_monitor.exe exists
□ Look for C++ monitor in Task Manager
□ Restart VWAR as administrator
□ Check if Windows Defender is blocking

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: System tray icon not appearing

Solutions:
□ Check Windows tray settings (Show hidden icons)
□ Verify pywin32 is installed: pip install pywin32
□ Restart VWAR
□ Check if tray icon is in overflow area
□ Look for error messages about tray

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Scans are very slow

Solutions:
□ Reduce scan paths (don't scan entire drives)
□ Exclude large folders (videos, games)
□ Check if other antivirus is scanning simultaneously
□ Ensure SSD/HDD is healthy (check SMART status)
□ Close other resource-intensive programs
□ Wait for initial scan to complete (first scan is slowest)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: License expired message

Solutions:
□ Check "Valid Till" date on Home page
□ Contact support for renewal
□ Ensure internet connection is active
□ Don't modify system date/time
□ License validation happens every 6 hours

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: False positive detections

Solutions:
□ Restore file from Scan Vault page
□ File will be re-scanned on restore
□ Report false positive to support
□ Check if file is from trusted source
□ Verify file with VirusTotal.com
□ Future update will add exclusion list

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Can't restore quarantined file

Solutions:
□ Ensure file still exists in quarantine folder
□ Check if .meta file is present
□ Run VWAR as administrator
□ Manually copy from quarantine/ folder
□ Contact support if issue persists

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: High CPU or memory usage

Solutions:
□ Normal during active scanning
□ Check if stuck on a large file
□ Restart VWAR
□ Reduce scheduled scan frequency
□ Close other programs
□ Check Windows Task Manager for conflicts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Schedule scan not running

Solutions:
□ Verify schedule is saved (check Last Run time)
□ Ensure VWAR is running (not closed)
□ Check if paths exist
□ Set realistic time (not in the past)
□ Use "Run Now" to test manually
□ Check console for error messages

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Updates not detecting

Solutions:
□ Check internet connection
□ Verify GitHub is accessible
□ Look for update notification on Home page
□ Manually check: https://github.com/AnindhaxNill/VWAR-release
□ Contact support if stuck on old version

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STILL HAVING ISSUES?

If none of these solutions work:

1. Check console output for error messages
2. Collect logs from data/ folder
3. Note exact error message
4. Contact support with details
5. Email: support@bobosohomail.com
6. Website: http://www.bitss.one
7. Include VWAR version and Windows version

"""
        text.insert("1.0", content)
        text.config(state="disabled")

    def _create_contact_tab(self):
        """Contact tab with support information."""
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="📧 Contact")
        
        container = tk.Frame(tab, bg="white")
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Title
        title = tk.Label(
            container,
            text="📧 Contact & Support",
            font=("Arial", 18, "bold"),
            bg="white",
            fg="#009AA5"
        )
        title.pack(pady=(0, 20))
        
        # Company info box
        info_frame = tk.Frame(container, bg="#f0f8ff", relief="solid", borderwidth=1)
        info_frame.pack(fill="x", pady=10)
        
        tk.Label(
            info_frame,
            text="🏢 Developer: Bitss.one",
            font=("Arial", 14, "bold"),
            bg="#f0f8ff",
            fg="#004d4d"
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        tk.Label(
            info_frame,
            text="🌐 Website: http://www.bitss.one",
            font=("Arial", 12),
            bg="#f0f8ff",
            fg="#007777",
            cursor="hand2"
        ).pack(anchor="w", padx=20, pady=5)
        
        tk.Label(
            info_frame,
            text="📧 Email: support@bobosohomail.com",
            font=("Arial", 12),
            bg="#f0f8ff",
            fg="#007777",
            cursor="hand2"
        ).pack(anchor="w", padx=20, pady=5)
        
        tk.Label(
            info_frame,
            text=f"📦 Version: {self._get_version()}",
            font=("Arial", 12),
            bg="#f0f8ff",
            fg="#004d4d"
        ).pack(anchor="w", padx=20, pady=(5, 15))
        
        # Support info
        support_text = tk.Text(
            container,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="white",
            fg="#333",
            relief="flat",
            height=15
        )
        support_text.pack(fill="both", expand=True, pady=20)
        
        support_content = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 SUPPORT HOURS

Monday - Friday: 9:00 AM - 6:00 PM (GMT)
Saturday: 10:00 AM - 4:00 PM (GMT)
Sunday: Closed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 EMAIL SUPPORT

For technical support, license inquiries, or bug reports:
support@bobosohomail.com

Please include:
• VWAR version number
• Windows version
• Detailed description of issue
• Screenshots if applicable
• Steps to reproduce the problem

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔑 LICENSE INQUIRIES

For new licenses or renewals:
• Visit: http://www.bitss.one
• Email: support@bobosohomail.com
• Include your hardware ID (shown on activation screen)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐛 BUG REPORTS

Found a bug? Help us improve:
1. Note the exact error message
2. Describe what you were doing
3. Check if it's repeatable
4. Email details to support
5. Include log files if available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 FEATURE REQUESTS

Have an idea for improvement?
We'd love to hear it! Email your suggestions to:
support@bobosohomail.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌟 Thank you for using VWAR Scanner!
Your security is our priority.

"""
        support_text.insert("1.0", support_content)
        support_text.config(state="disabled")

    def _get_version(self):
        """Get current VWAR version."""
        try:
            from utils.update_checker import CURRENT_VERSION
            return CURRENT_VERSION
        except:
            return "3.0.0"

    def _open_file(self, path):
        """Open file with default application."""
        try:
            os.startfile(path)  # Windows: opens with default app
        except Exception:
            pass

    def _open_folder(self, folder):
        """Open folder in Windows Explorer."""
        try:
            os.startfile(folder)
        except Exception:
            pass

    def _find_guides(self):
        """Find guide files robustly.

        Priority:
        1) Known common filenames in assets/ then root
        2) Otherwise, newest *.pdf found in assets/ then root
        """
        def exists(p: str) -> bool:
            try:
                return os.path.exists(p)
            except Exception:
                return False

        def fmt_mtime(p: str) -> str:
            try:
                return datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                return "unknown"

        # 1) Try known filenames
        known_candidates = []
        for name in self.COMMON_FILENAMES:
            known_candidates.append(resource_path(os.path.join("assets", name)))
            known_candidates.append(resource_path(name))

        pdf_path = next((p for p in known_candidates if p.lower().endswith('.pdf') and exists(p)), None)
        docx_path = None

        # 2) Fallback to newest match by extension
        def newest_with_ext(exts):
            found = []
            for base in (resource_path("assets"), resource_path(".")):
                try:
                    for fname in os.listdir(base):
                        if any(fname.lower().endswith(e) for e in exts):
                            full = os.path.join(base, fname)
                            if exists(full):
                                try:
                                    found.append((os.path.getmtime(full), full))
                                except Exception:
                                    found.append((0, full))
                except Exception:
                    continue
            if not found:
                return None
            found.sort(reverse=True)
            return found[0][1]

        if not pdf_path:
            pdf_path = newest_with_ext(['.pdf'])

        return {
            "pdf": pdf_path,
            "pdf_name": (os.path.basename(pdf_path) if pdf_path else None),
            "pdf_mtime": (fmt_mtime(pdf_path) if pdf_path else None),
        }
