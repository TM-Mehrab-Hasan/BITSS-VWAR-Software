from tkinter import Frame, Button, Label
from utils.tooltip import Tooltip


class BackupMainPage(Frame):
    def __init__(self, root, switch_page_callback):
        super().__init__(root, bg="#009AA5")
        self.root = root
        self.switch_page_callback = switch_page_callback
        self.build_ui()

    def build_ui(self):
        Label(self, text="Backup & Restore Menu", font=("Inter", 20, "bold"), bg="#009AA5", fg="white").place(x=360, y=30)

        # Back Button
        # back_btn = Button(self, text="← Back", command=lambda: self.switch_page_callback("home"),
        #                   bg="red", fg="white", font=("Inter", 12))
        # back_btn.place(x=20, y=20, width=80, height=30)
        # Tooltip(back_btn, "Return to home page")

        # Manual Backup Button
        mb_btn = Button(self, text="📁 Manual Backup", command=lambda: self.switch_page_callback("manual_backup"),
                        bg="#006666", fg="white", font=("Inter", 14))
        mb_btn.place(x=350, y=120, width=300, height=60)
        # Tooltip(mb_btn, "Back up selected files manually into a dated backup folder")

        # Restore Backup Button
        rb_btn = Button(self, text="♻ Restore Backup", command=lambda: self.switch_page_callback("restore_backup"),
                        bg="#3a6ea5", fg="white", font=("Inter", 14))
        rb_btn.place(x=350, y=210, width=300, height=60)
        # Tooltip(rb_btn, "Restore a previously backed up file")

        # Auto Backup Button
        ab_btn = Button(self, text="⚙ Enable Auto Backup", command=lambda: self.switch_page_callback("auto_backup"),
                        bg="#d95f02", fg="white", font=("Inter", 14))
        ab_btn.place(x=350, y=300, width=300, height=60)
        # Tooltip(ab_btn, "Continuously monitor and back up selected folders automatically")
