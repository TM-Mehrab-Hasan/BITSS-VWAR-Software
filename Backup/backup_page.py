



# import os
# import shutil
# from datetime import datetime
# from tkinter import Frame, Button, Label, Listbox, Scrollbar, filedialog, messagebox
# from utils.tooltip import Tooltip
# from utils.logger import log_message
# from config import BACKUP_FOLDER


# class ManualBackupPage(Frame):
#     def __init__(self, root, switch_page_callback):
#         super().__init__(root, bg="#009AA5")
#         self.root = root
#         self.switch_page_callback = switch_page_callback
#         self.selected_files = []
#         self.selected_backup_folder = ""

#         # === Back Button ===
#         back_btn = Button(self, text="Back", command=lambda: switch_page_callback("backup"),
#                           bg="red", fg="white", font=("Inter", 12))
#         back_btn.place(x=10, y=10, width=80, height=30)
#         # Tooltip(back_btn, "Return to Backup Main Menu")
        
#         label_back = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         label_back.place(x=95, y=10)
#         Tooltip(label_back, "Return to Backup Main Menu")

#         Label(self, text="Manual Backup", font=("Inter", 14, "bold"),
#               bg="#009AA5", fg="black").place(x=400, y=10)

#         # === File List ===
#         Label(self, text="Selected Files to Backup", font=("Inter", 14, "bold"),
#               bg="#009AA5", fg="white").place(x=20, y=70)

#         self.backup_file_listbox = Listbox(self, font=("Inter", 11), selectmode="multiple")
#         self.backup_file_listbox.place(x=20, y=110, width=500, height=200)

#         scrollbar = Scrollbar(self, orient="vertical", command=self.backup_file_listbox.yview)
#         scrollbar.place(x=520, y=110, height=200)
#         self.backup_file_listbox.config(yscrollcommand=scrollbar.set)

#         # === Destination ===
#         Label(self, text="Backup Destination:", font=("Inter", 14, "bold"),
#               bg="#009AA5", fg="white").place(x=20, y=320)

#         self.backup_destination_label = Label(
#             self,
#             text="No folder selected",
#             font=("Inter", 11),
#             bg="white",
#             fg="black",
#             anchor="w",
#             relief="sunken"
#         )
#         self.backup_destination_label.place(x=20, y=360, width=500, height=30)

#         # === Select Files Button ===
#         select_files_btn = Button(self, text="Select Files", command=self.select_backup_files,
#                                   bg="#004953", fg="white", font=("Inter", 12, "bold"))
#         select_files_btn.place(x=600, y=110, width=180, height=40)
#         # Tooltip(select_files_btn, "Choose one or more files to back up manually.")

#         # Tooltip icon
#         file_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         file_tip.place(x=790, y=110)
#         Tooltip(file_tip, "Files will be copied to a dated backup folder.")

#         # === Select Destination Button ===
#         select_dest_btn = Button(self, text="Select Destination", command=self.select_backup_destination,
#                                  bg="#004953", fg="white", font=("Inter", 12, "bold"))
#         select_dest_btn.place(x=600, y=170, width=180, height=40)
#         # Tooltip(select_dest_btn, "Choose or create the VWARbackup folder.")

#         dest_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         dest_tip.place(x=790, y=170)
#         Tooltip(dest_tip, "Backup files will be saved under VWARbackup/YYYY-MM-DD/")

#         # === Start Backup Button ===
#         self.start_backup_button = Button(self, text="Start Backup", command=self.perform_backup,
#                                           state="disabled", bg="#006666", fg="white", font=("Inter", 12, "bold"))
#         self.start_backup_button.place(x=600, y=230, width=180, height=40)
#         # Tooltip(self.start_backup_button, "Back up selected files into today's dated folder.")

#         start_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
#         start_tip.place(x=790, y=230)
#         Tooltip(start_tip, "Click to initiate manual backup now.")

#     # === File and Folder Selection ===
#     def select_backup_files(self):
#         files = filedialog.askopenfilenames(title="Select Files to Backup")
#         if files:
#             self.selected_files = list(files)
#             self.backup_file_listbox.delete(0, "end")
#             for file in self.selected_files:
#                 self.backup_file_listbox.insert("end", file)
#             self.check_ready_to_backup()





#     def select_backup_destination(self):
#         folder = filedialog.askdirectory(title="Select Destination Folder")
#         if folder:
#             if not folder.endswith("VWARbackup"):
#                 folder = os.path.join(folder, "VWARbackup")
#             os.makedirs(folder, exist_ok=True)
#             self.selected_backup_folder = folder
#             self.backup_destination_label.config(text=folder)
#             self.check_ready_to_backup()

#     def check_ready_to_backup(self):
#         if self.selected_files and self.selected_backup_folder:
#             self.start_backup_button.config(state="normal")
#         else:
#             self.start_backup_button.config(state="disabled")

#     # === Perform Backup ===
#     def perform_backup(self):
#         today = datetime.now().strftime("%Y-%m-%d")
#         date_folder_path = os.path.join(self.selected_backup_folder, today)
#         os.makedirs(date_folder_path, exist_ok=True)

#         try:
#             for source_path in self.selected_files:
#                 filename = os.path.basename(source_path)
#                 backup_file_path = os.path.join(date_folder_path, filename + ".backup")
#                 shutil.copy2(source_path, backup_file_path)
#                 log_message(f"[BACKUP] {source_path} -> {backup_file_path}")
#             messagebox.showinfo("Backup Completed", f"Successfully backed up {len(self.selected_files)} files.")
#         except Exception as e:
#             log_message(f"[ERROR] Failed to backup files: {e}")
#             messagebox.showerror("Backup Error", f"Failed to backup files:\n{e}")



import os
import shutil
from datetime import datetime
from tkinter import Frame, Button, Label, Listbox, Scrollbar, filedialog, messagebox
from utils.tooltip import Tooltip
from utils.logger import log_message
from config import BACKUP_FOLDER
import threading


class ManualBackupPage(Frame):
    def __init__(self, root, switch_page_callback):
        super().__init__(root, bg="#009AA5")
        self.root = root
        self.switch_page_callback = switch_page_callback
        self.selected_files = []
        self.selected_folders = []
        self.selected_backup_folder = ""

        # === UI HEADER ===
        Button(self, text="Back", command=lambda: switch_page_callback("backup"),
               bg="red", fg="white", font=("Inter", 12)).place(x=10, y=10, width=80, height=30)
        label_back = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        label_back.place(x=95, y=10)
        Tooltip(label_back, "Return to Backup Main Menu")
        
        
        Label(self, text="Manual Backup", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="black").place(x=400, y=10)

        # === File Selection ===
        Label(self, text="Selected Files", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=60)
        self.file_listbox = Listbox(self, font=("Inter", 11))
        self.file_listbox.place(x=20, y=100, width=500, height=100)
        scrollbar1 = Scrollbar(self, orient="vertical", command=self.file_listbox.yview)
        scrollbar1.place(x=520, y=100, height=100)
        self.file_listbox.config(yscrollcommand=scrollbar1.set)

        Label(self, text="Selected Folders", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=220)
        self.folder_listbox = Listbox(self, font=("Inter", 11))
        self.folder_listbox.place(x=20, y=260, width=500, height=100)
        scrollbar2 = Scrollbar(self, orient="vertical", command=self.folder_listbox.yview)
        scrollbar2.place(x=520, y=260, height=100)
        self.folder_listbox.config(yscrollcommand=scrollbar2.set)

        # === Destination Folder ===
        Label(self, text="Backup Destination:", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=380)
        self.destination_label = Label(self, text="No folder selected",
                                       bg="white", font=("Inter", 11),
                                       anchor="w", relief="sunken")
        self.destination_label.place(x=20, y=420, width=500, height=30)

        # === Buttons ===
        Button(self, text="Select Files", command=self.select_files,
               bg="#004953", fg="white", font=("Inter", 12, "bold")).place(x=550, y=100, width=180, height=40)
        file_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        file_tip.place(x=740, y=110)
        Tooltip(file_tip, "Files will be copied to a dated backup folder.")

        
        
        Button(self, text="Select Folders", command=self.select_folders,
               bg="#004953", fg="white", font=("Inter", 12, "bold")).place(x=550, y=260, width=180, height=40)
        folder_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        folder_tip.place(x=740, y=270)
        Tooltip(folder_tip, "folders will be copied to a dated backup folder.")

        
        Button(self, text="Select Destination", command=self.select_destination,
               bg="#004953", fg="white", font=("Inter", 12, "bold")).place(x=550, y=420, width=180, height=40)
        des_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        des_tip.place(x=740, y=430)
        Tooltip(des_tip, "Backup files will be saved under VWARbackup/YYYY-MM-DD/")

        

        self.backup_button = Button(self, text="Start Backup", command=self.start_backup_thread,
                                    state="disabled", bg="#006666", fg="white", font=("Inter", 12, "bold"))
        self.backup_button.place(x=400, y=560, width=180, height=40)

        # Remove Selected Files Button
        remove_file_btn = Button(self, text="Remove File", command=self.remove_selected_files,
                                bg="#a94442", fg="white", font=("Inter", 12, "bold"))
        remove_file_btn.place(x=800, y=100, width=180, height=40)

        # Remove Selected Folders Button
        remove_folder_btn = Button(self, text="Remove Folder", command=self.remove_selected_folders,
                                bg="#a94442", fg="white", font=("Inter", 12, "bold"))
        remove_folder_btn.place(x=800, y=260, width=180, height=40)




    def select_files(self):
        files = filedialog.askopenfilenames(title="Select Files to Backup")
        if files:
            self.selected_files = list(files)
            self.file_listbox.delete(0, "end")
            for f in self.selected_files:
                self.file_listbox.insert("end", f)
            self.check_ready()

    def select_folders(self):
        folders = filedialog.askdirectory(title="Select Folder to Backup")
        if folders:
            self.selected_folders = [folders]
            self.folder_listbox.delete(0, "end")
            for f in self.selected_folders:
                self.folder_listbox.insert("end", f)
            self.check_ready()

    def select_destination(self):
        folder = filedialog.askdirectory(title="Select Backup Destination")
        if folder:
            if not folder.endswith("VWARbackup"):
                folder = os.path.join(folder, "VWARbackup")
            os.makedirs(folder, exist_ok=True)
            self.selected_backup_folder = folder
            self.destination_label.config(text=folder)
            self.check_ready()

    def remove_selected_files(self):
        selection = list(self.file_listbox.curselection())
        if not selection:
            return
        for i in reversed(selection):
            self.file_listbox.delete(i)
            del self.selected_files[i]
        self.check_ready()

    def remove_selected_folders(self):
        selection = list(self.folder_listbox.curselection())
        if not selection:
            return
        for i in reversed(selection):
            self.folder_listbox.delete(i)
            del self.selected_folders[i]
        self.check_ready()



    def check_ready(self):
        if (self.selected_files or self.selected_folders) and self.selected_backup_folder:
            self.backup_button.config(state="normal")
        else:
            self.backup_button.config(state="disabled")

    def perform_backup(self):
        today = datetime.now().strftime("%Y-%m-%d")
        date_path = os.path.join(self.selected_backup_folder, today)
        os.makedirs(date_path, exist_ok=True)

        try:
            # --- Backup Files ---
            for src in self.selected_files:
                filename = os.path.basename(src)
                dst = os.path.join(date_path, filename + ".backup")
                shutil.copy2(src, dst)
                log_message(f"[BACKUP] File: {src} -> {dst}")

            # --- Backup Folders (inside subfolders) ---
            for folder in self.selected_folders:
                folder_name = os.path.basename(folder)
                target_root = os.path.join(date_path, folder_name)
                for root, _, files in os.walk(folder):
                    for file in files:
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, folder)
                        dst_file = os.path.join(target_root, rel_path + ".backup")
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        log_message(f"[BACKUP] Folder: {src_file} -> {dst_file}")

            messagebox.showinfo("Success", "Backup completed successfully.")
        except Exception as e:
            log_message(f"[ERROR] Backup failed: {e}")
            messagebox.showerror("Backup Error", str(e))


    def start_backup_thread(self):
        threading.Thread(target=self.perform_backup, daemon=True).start()