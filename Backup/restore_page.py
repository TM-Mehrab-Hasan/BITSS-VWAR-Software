

import os
import shutil
from tkinter import Frame, Button, Label, filedialog, Listbox, messagebox, Scrollbar
from utils.tooltip import Tooltip
from utils.logger import log_message
import threading

class RestoreBackupPage(Frame):
    def __init__(self, root, switch_page_callback):
        super().__init__(root, bg="#009AA5")
        self.root = root
        self.switch_page_callback = switch_page_callback

        self.selected_vwar_folder = ""
        self.selected_restore_files = []
        self.selected_restore_folder = ""
        self.restore_base_folder = ""  # Used to compute correct relative path

        # === Back Button ===
        back_btn = Button(self, text="Back", command=lambda: switch_page_callback("backup"),
                          bg="red", fg="white", font=("Inter", 12))
        back_btn.place(x=10, y=10, width=80, height=30)
        back_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        back_tip.place(x=95, y=10)
        Tooltip(back_tip, "Return to Backup Main Menu")

        Label(self, text="Restore Backup", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="black").place(x=400, y=10)

        # === Step 1: VWARbackup Folder ===
        Label(self, text="Step 1: Select VWARbackup Folder", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=50)

        self.vwar_folder_label = Label(self, text="No folder selected", font=("Inter", 11),
                                       bg="white", fg="black", anchor="w", relief="sunken")
        self.vwar_folder_label.place(x=20, y=85, width=500, height=30)

        vwar_btn = Button(self, text="Browse", command=self.select_vwarbackup_folder,
                          bg="#004953", fg="white", font=("Inter", 12, "bold"))
        vwar_btn.place(x=600, y=80, width=180, height=40)

        vwar_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        vwar_tip.place(x=790, y=80)
        Tooltip(vwar_tip, "Select the VWARbackup folder that stores all backups.")

        # === Step 2: Select Files or Folder ===
        Label(self, text="Step 2: Select Backup Files or Folder", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=130)

        self.restore_file_listbox = Listbox(self, font=("Inter", 11))
        self.restore_file_listbox.place(x=20, y=170, width=500, height=130)

        file_scroll = Scrollbar(self, orient="vertical", command=self.restore_file_listbox.yview)
        file_scroll.place(x=520, y=170, height=130)
        self.restore_file_listbox.config(yscrollcommand=file_scroll.set)

        self.select_file_btn = Button(self, text="Select Files", command=self.select_restore_files,
                                      state="disabled", bg="#004953", fg="white", font=("Inter", 12, "bold"))
        self.select_file_btn.place(x=600, y=160, width=180, height=40)

        self.select_folder_btn = Button(self, text="Select Folder", command=self.select_restore_folder,
                                        state="disabled", bg="#004953", fg="white", font=("Inter", 12, "bold"))
        self.select_folder_btn.place(x=600, y=210, width=180, height=40)

        folder_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        folder_tip.place(x=790, y=210)
        Tooltip(folder_tip, "Select a full dated backup folder to restore all contents.")

        # === Remove All ===
        remove_all_btn = Button(self, text="Remove All", command=self.clear_restore_list,
                                bg="#a94442", fg="white", font=("Inter", 12, "bold"))
        remove_all_btn.place(x=600, y=305, width=180, height=40)

        remove_all_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        remove_all_tip.place(x=790, y=305)
        Tooltip(remove_all_tip, "Clear all selected restore files or folders.")

        # === Step 3: Restore Destination ===
        Label(self, text="Step 3: Select Restore Location", font=("Inter", 14, "bold"),
              bg="#009AA5", fg="white").place(x=20, y=360)

        self.restore_location_label = Label(self, text="No restore location selected", font=("Inter", 11),
                                            bg="white", fg="black", anchor="w", relief="sunken")
        self.restore_location_label.place(x=20, y=400, width=500, height=30)

        dest_btn = Button(self, text="Select Location", command=self.select_restore_location,
                          bg="#004953", fg="white", font=("Inter", 12, "bold"))
        dest_btn.place(x=600, y=395, width=180, height=40)

        dest_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        dest_tip.place(x=790, y=395)
        Tooltip(dest_tip, "Choose where the restored files will be copied to.")

        # === Start Restore ===
        self.restore_btn = Button(self, text="Start Restore", command=self.start_restore_thread,
                                  state="disabled", bg="#006666", fg="white", font=("Inter", 12, "bold"))
        self.restore_btn.place(x=600, y=460, width=180, height=40)

        restore_tip = Label(self, text="?", bg="#009AA5", fg="white", font=("Arial", 12, "bold"))
        restore_tip.place(x=790, y=460)
        Tooltip(restore_tip, "Restore all selected backup files or folders.")

    def select_vwarbackup_folder(self):
        folder = filedialog.askdirectory(title="Select VWARbackup Folder")
        if not folder:
            return
        if not folder.endswith("VWARbackup"):
            messagebox.showerror("Invalid", "Folder must end with 'VWARbackup'.")
            return

        self.selected_vwar_folder = folder
        self.vwar_folder_label.config(text=folder)

        # Enable file/folder select buttons
        self.select_file_btn.config(state="normal")
        self.select_folder_btn.config(state="normal")

    def select_restore_files(self):
        if not self.selected_vwar_folder:
            messagebox.showwarning("Select VWARbackup Folder", "Please select the VWARbackup folder first.")
            return

        files = filedialog.askopenfilenames(
            title="Select One or More Backup Files",
            filetypes=[("Backup Files", "*.backup")],
            initialdir=self.selected_vwar_folder
        )
        if files:
            self.selected_restore_files = list(files)
            self.restore_file_listbox.delete(0, "end")
            self.restore_base_folder = os.path.commonpath(self.selected_restore_files)

            for f in self.selected_restore_files:
                self.restore_file_listbox.insert("end", f)
            self.check_ready()

    def select_restore_folder(self):
        if not self.selected_vwar_folder:
            messagebox.showwarning("Select VWARbackup Folder", "Please select the VWARbackup folder first.")
            return

        folder = filedialog.askdirectory(title="Select Backup Folder", initialdir=self.selected_vwar_folder)
        if folder:
            self.restore_base_folder = folder
            self.selected_restore_files = []
            self.restore_file_listbox.delete(0, "end")
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.endswith(".backup"):
                        full_path = os.path.join(root, f)
                        self.selected_restore_files.append(full_path)
                        self.restore_file_listbox.insert("end", full_path)
            self.check_ready()

    def select_restore_location(self):
        folder = filedialog.askdirectory(title="Select Restore Location")
        if folder:
            self.selected_restore_folder = folder
            self.restore_location_label.config(text=folder)
            self.check_ready()

    def clear_restore_list(self):
        self.restore_file_listbox.delete(0, "end")
        self.selected_restore_files = []
        self.check_ready()

    def check_ready(self):
        if self.selected_restore_files and self.selected_restore_folder:
            self.restore_btn.config(state="normal")
        else:
            self.restore_btn.config(state="disabled")

    def perform_restore(self):
        errors = []
        restored = 0

        for backup_path in self.selected_restore_files:
            # rel_path = os.path.relpath(backup_path, self.restore_base_folder)
            # rel_path = rel_path.replace(".backup", "")
            # target_path = os.path.join(self.selected_restore_folder, rel_path)
            rel_path = os.path.relpath(backup_path, self.selected_vwar_folder)
            # rel_path = os.path.relpath(backup_path, self.restore_base_folder)
            # Split the path into directory and filename
            rel_dir = os.path.dirname(rel_path)
            # filename = os.path.basename(rel_path).replace(".backup", "")
            # print(rel_dir)
            name, ext = os.path.splitext(os.path.basename(rel_path))
            # print(name,ext)
            if ext == ".backup":
                filename = name  # Correct original file name
            else:
                filename = name + ext  # Leave it unchanged (if somehow no .backup)

            # Final restored path
            # target_path = os.path.join(self.selected_restore_folder, rel_dir, filename) wrong code
            target_path = os.path.join(self.selected_restore_folder, filename)



            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(backup_path, target_path)
                log_message(f"[RESTORE] {backup_path} -> {target_path}")
                restored += 1
            except Exception as e:
                errors.append((backup_path, str(e)))
                log_message(f"[ERROR] Restore failed: {backup_path} -> {e}")

        msg = f"✅ Restored {restored} file(s)."
        if errors:
            msg += f"\n⚠️ {len(errors)} file(s) failed."

        messagebox.showinfo("Restore Complete", msg)

    def start_restore_thread(self):
        threading.Thread(target=self.perform_restore, daemon=True).start()