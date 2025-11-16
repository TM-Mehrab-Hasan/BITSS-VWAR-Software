import os
import json
from tkinter import Frame, Label, Button, Entry, Listbox, Scrollbar, filedialog, messagebox
from config import AUTO_BACKUP_CONFIG_PATH
from utils.tooltip import Tooltip
from utils.logger import log_message
from Backup.auto_backup import perform_rotating_backup
import threading

class AutoBackupPage(Frame):
    def __init__(self, root, switch_page_callback):
        super().__init__(root, bg="#009AA5")
        self.root = root
        self.switch_page_callback = switch_page_callback

        self.folders = []
        self.destination = ""
        self.time = ""

        # Back button
        back_btn = Button(self, text="Back", command=lambda: switch_page_callback("backup"),
                          bg="red", fg="white", font=("Inter", 12))
        back_btn.place(x=10, y=10, width=80, height=30)
        # Tooltip(back_btn, "Return to Backup Menu")

        Label(self, text="Auto Backup Settings", font=("Inter", 16, "bold"),
              bg="#009AA5", fg="black").place(x=400, y=10)

        # Time Input
        Label(self, text="Backup Time (24-hour, e.g. 14:00):", font=("Inter", 12, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=60)
        self.time_entry = Entry(self, font=("Inter", 12))
        self.time_entry.place(x=320, y=60, width=200, height=30)

        # Folder list
        Label(self, text="Selected Folders", font=("Inter", 12, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=110)
        self.folder_listbox = Listbox(self, font=("Inter", 11))
        self.folder_listbox.place(x=20, y=140, width=500, height=150)

        scroll = Scrollbar(self, orient="vertical", command=self.folder_listbox.yview)
        scroll.place(x=520, y=140, height=150)
        self.folder_listbox.config(yscrollcommand=scroll.set)

        # Destination
        Label(self, text="Backup Destination Folder", font=("Inter", 12, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=310)
        self.dest_label = Label(self, text="No destination selected", bg="white", font=("Inter", 11),
                                anchor="w", relief="sunken")
        self.dest_label.place(x=20, y=340, width=500, height=30)

        # Buttons
        Button(self, text="Add Folder", command=self.add_folder,
               bg="#004953", fg="white", font=("Inter", 12, "bold")).place(x=600, y=140, width=180, height=40)
        Button(self, text="Clear All", command=self.clear_folders,
               bg="#a94442", fg="white", font=("Inter", 12, "bold")).place(x=600, y=200, width=180, height=40)
        Button(self, text="Set Destination", command=self.set_destination,
               bg="#004953", fg="white", font=("Inter", 12, "bold")).place(x=600, y=260, width=180, height=40)

        # Save config
        Button(self, text="Save Settings", command=self.save_settings,
               bg="#006666", fg="white", font=("Inter", 12, "bold")).place(x=600, y=340, width=180, height=40)

    #     Button(self, text="Run Auto Backup Now", command=self.run_now,
    #    bg="#006666", fg="white", font=("Inter", 12)).place(x=600, y=400, width=180, height=40)

        
        
        # Load existing config if any
        self.load_config()

    def add_folder(self):
        folders = filedialog.askdirectory(title="Select Folder to Backup")
        if folders and folders not in self.folders:
            self.folders.append(folders)
            self.folder_listbox.insert("end", folders)

    def clear_folders(self):
        self.folders.clear()
        self.folder_listbox.delete(0, "end")

    def set_destination(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            if not folder.endswith("VWARbackup"):
                    folder = os.path.join(folder, "VWARbackup")
            self.destination = folder
            self.dest_label.config(text=folder)


    # def set_destination(self):
    #         folder = filedialog.askdirectory(title="Select Backup Destination")
    #         if folder:
    #             if not folder.endswith("VWARbackup"):
    #                 folder = os.path.join(folder, "VWARbackup")
    #             os.makedirs(folder, exist_ok=True)
    #             self.selected_backup_folder = folder
    #             # self.dest_label = folder
    #             self.dest_label.config(text=folder)
                


    def save_settings(self):
        time_str = self.time_entry.get().strip()
        if not self.folders or not self.destination or not time_str:
            messagebox.showerror("Missing", "Please fill all fields before saving.")
            return

        config = {
            "folders": self.folders,
            "destination": self.destination,
            "time": time_str,
            "current_day": 1
        }
        os.makedirs(os.path.dirname(AUTO_BACKUP_CONFIG_PATH), exist_ok=True)
        with open(AUTO_BACKUP_CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        messagebox.showinfo("Saved", "Auto-backup settings saved successfully.")
        log_message("[AUTO] Auto-backup settings saved.")
        self.switch_page_callback("backup")

    def load_config(self):
        if not os.path.exists(AUTO_BACKUP_CONFIG_PATH):
            return
        with open(AUTO_BACKUP_CONFIG_PATH, "r") as f:
            config = json.load(f)
            self.folders = config.get("folders", [])
            self.destination = config.get("destination", "")
            self.time = config.get("time", "")
            self.time_entry.insert(0, self.time)

            self.dest_label.config(text=self.destination)
            for f in self.folders:
                self.folder_listbox.insert("end", f)


    # def run_now(self):
    #     perform_rotating_backup()
        
    # def run_now(self):
    #     threading.Thread(target=perform_rotating_backup(), daemon=True).start()