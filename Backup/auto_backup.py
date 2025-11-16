


import os
import shutil
import json
import threading
from datetime import datetime
import time
from config import AUTO_BACKUP_CONFIG_PATH
from utils.logger import log_message
import re


def load_config():
    """Load auto-backup configuration from JSON file."""
    if not os.path.exists(AUTO_BACKUP_CONFIG_PATH):
        return None
    with open(AUTO_BACKUP_CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    """Save auto-backup configuration to JSON file."""
    os.makedirs(os.path.dirname(AUTO_BACKUP_CONFIG_PATH), exist_ok=True)
    with open(AUTO_BACKUP_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)





def perform_rotating_backup():
    today = datetime.now().strftime("%d-%m-%Y")
    today_obj = datetime.strptime(today, "%d-%m-%Y")
    config = load_config()
    if not config:
        log_message("[AUTO] No auto-backup config found.")
        return
    folders = config.get("folders", [])
    destination = config.get("destination")
    backup_root = os.path.join(destination, "AutoBackup")
    os.makedirs(backup_root, exist_ok=True)

    pattern = re.compile(r"day(\d)_(\d{2}-\d{2}-\d{4})")
    existing_folders = []

    for folder in os.listdir(backup_root):
        match = pattern.match(folder)
        if match:
            day_num = int(match.group(1))
            folder_date = match.group(2)
            try:
                folder_date_obj = datetime.strptime(folder_date, "%d-%m-%Y")
                existing_folders.append((day_num, folder_date_obj, folder))
            except:
                continue

    # Check if today's backup already exists
    for _, date_obj, folder in existing_folders:
        if date_obj.date() == today_obj.date():
            # self.log(f"[AUTO BACKUP] Skipped - Already backed up today in {folder}", "load")
            return

    # Sort to find the oldest
    existing_folders.sort(key=lambda x: x[1])
    if len(existing_folders) < 7:
        next_day = len(existing_folders) + 1
    else:
        next_day = existing_folders[0][0]
        shutil.rmtree(os.path.join(backup_root, existing_folders[0][2]), ignore_errors=True)

    folder_name = f"day{next_day}_{today}"
    target_folder = os.path.join(backup_root, folder_name)
    os.makedirs(target_folder, exist_ok=True)

    try:
        for folder in folders:
            if not os.path.exists(folder):
                print(f"[AUTO BACKUP] Skipped non-existent folder: {folder}", "load")
                continue

            for root_dir, _, files in os.walk(folder):
                for file in files:
                    src_file = os.path.join(root_dir, file)
                    rel_path = os.path.relpath(src_file, folder)
                    rel_dir = os.path.dirname(rel_path)
                    filename = os.path.basename(file) + ".backup"
                    dest_dir = os.path.join(target_folder, os.path.basename(folder), rel_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(src_file, os.path.join(dest_dir, filename))

        print(f"[AUTO BACKUP] Backup completed in {folder_name}", "load")
    except Exception as e:
        print(f"[ERROR] Auto Backup failed: {e}", "load")


class AutoBackupScheduler:
    """Background thread to schedule auto-backup daily."""

    def __init__(self):
        self.running = False
        self.thread = None
        self.last_run_date = ""

    def start(self):
        """Start the scheduler thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the scheduler thread."""
        self.running = False

    def _run(self):
        while self.running:
            try:
                config = load_config()
                if not config:
                    time.sleep(60)
                    continue

                scheduled_time = config.get("time")
                if not scheduled_time:
                    time.sleep(60)
                    continue

                now = datetime.now()
                current_time = now.strftime("%H:%M")
                today = now.strftime("%d-%m-%Y")

                if current_time == scheduled_time and self.last_run_date != today:
                    log_message("[AUTO] Starting scheduled backup...")
                    # self.perform_rotating_backup()
                    # threading.Thread(target=self.perform_rotating_backup(), daemon=True).start()
                    threading.Thread(target=perform_rotating_backup, daemon=True).start()

                    self.last_run_date = today

                time.sleep(30)

            except Exception as e:
                log_message(f"[AUTO] Scheduler error: {e}")
                time.sleep(60)
