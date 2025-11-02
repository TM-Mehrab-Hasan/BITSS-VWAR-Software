# 📁 File: utils/update_checker.py

import requests
import json
import os
from tkinter import messagebox
from config import CURRENT_VERSION
import webbrowser
import urllib.request


# update_status = {
#     "latest_version": "3.0.0",
#     "changelog": "",
#     "download_url": ""
# }


def compare_versions(version1, version2):
    """Compare semantic versions. Returns -1 if v1<v2, 0 if equal, 1 if v1>v2"""
    try:
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        while len(v1_parts) < 3:
            v1_parts.append(0)
        while len(v2_parts) < 3:
            v2_parts.append(0)
        
        for i in range(3):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        return 0
    except:
        return 0 if version1 == version2 else -1


def up_to():
    try:
        url = "https://raw.githubusercontent.com/TM-Mehrab-Hasan/VWAR-Releases/main/update_info.json"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            # print(data)
        
        latest = data["latest_version"]
        
        # update_status["changelog"]
        # update_status["download_url"]
        
        
        
        if compare_versions(CURRENT_VERSION, latest) < 0:
            return 1
    except Exception as e:
            print(f"[ERROR] Failed to check for updates: {e}")

def check_for_updates():
    try:
        url = "https://raw.githubusercontent.com/TM-Mehrab-Hasan/VWAR-Releases/main/update_info.json"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        # print(data)
        latest = data["latest_version"]
        download_url = data["download_url"]
        notes = data.get("changelog", "")
        
        # update_status["changelog"]
        # update_status["download_url"]

        
        
        if compare_versions(CURRENT_VERSION, latest) < 0:
            if messagebox.askyesno("Update Available",
                f"A new version {latest} is available.\n\nChangelog:\n{notes}\n\nDo you want to update now?"):
                webbrowser.open(download_url)
                
                
        print("[Active status updeate _cheacker]active checked up to date")
            
    except Exception as e:
        print(f"[ERROR] Failed to check for updates: {e}")