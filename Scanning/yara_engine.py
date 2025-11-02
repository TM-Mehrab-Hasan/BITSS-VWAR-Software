import os
import yara
import requests

from config import (
    YARA_FOLDER, 
    API_YARA_FETCH, 
    API_YARA_FETCH_KEY,
    API_YARA_INSERT,
    API_YARA_INSERT_KEY
)
from utils.logger import log_message


def fetch_and_generate_yara_rules(log_func=print):
    """Fetch categorized YARA rules from remote and store locally using authenticated API.
    Returns a tuple: (fetch_status, rule_count)
    fetch_status: 'remote', 'local', or 'none'
    rule_count: number of rules loaded from remote or local
    """
    try:
        header_variants = [
            {"X-API-Key": API_YARA_FETCH_KEY},
            {"x-api-key": API_YARA_FETCH_KEY},
            {"API-Key": API_YARA_FETCH_KEY},
            {"Authorization": f"Bearer {API_YARA_FETCH_KEY}"}
        ]
        response = None
        last_exc = None
        for hdr in header_variants:
            try:
                log_message(f"[DEBUG] Attempting YARA fetch with headers: {list(hdr.keys())}")
                resp = requests.get(API_YARA_FETCH, headers=hdr, timeout=10)
                log_message(f"[DEBUG] YARA fetch attempt status: {resp.status_code} for headers={list(hdr.keys())}")
                if resp.status_code == 200:
                    response = resp
                    break
                else:
                    last_exc = Exception(f"Unexpected status {resp.status_code}")
            except Exception as inner_e:
                last_exc = inner_e
                try:
                    log_message(f"[DEBUG] YARA fetch attempt failed for headers={list(hdr.keys())}: {inner_e}")
                except Exception:
                    pass
        if response is None:
            raise last_exc or Exception("YARA fetch failed (no response)")
        response.raise_for_status()
        json_data = response.json()
        if not json_data:
            log_func("[WARNING] No YARA rules found from server.")
            return ("none", 0)
        for rule in json_data:
            category = rule.get("categoryname", "uncategorized")
            rule_name = rule.get("rulename", "unknown_rule")
            rule_content = rule.get("conditions", [{}])[0].get("string", "")
            category_dir = os.path.join(YARA_FOLDER, category)
            os.makedirs(category_dir, exist_ok=True)
            file_path = os.path.join(category_dir, f"{rule_name}.yar")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(rule_content)
        try:
            log_message(f"[INFO] YARA rules fetched and saved ({len(json_data)} entries)")
        except Exception:
            pass
        log_func(f"[INFO] YARA rules updated from server. ({len(json_data)} rules loaded)")
        return ("remote", len(json_data))
    except Exception as e:
        try:
            log_message(f"[ERROR] Failed to fetch YARA rules: {e}")
        except Exception:
            pass
        # Fallback to local rules
        local_count = 0
        for root, _, files in os.walk(YARA_FOLDER):
            for file in files:
                if file.endswith(".yar"):
                    local_count += 1
        if local_count > 0:
            log_func(f"[INFO] Using local YARA rules. ({local_count} rules loaded)")
            return ("local", local_count)
        else:
            log_func("[ERROR] No YARA rules available (fetch failed, no local rules found).")
            return ("none", 0)


def compile_yara_rules(rule_folder=YARA_FOLDER, log_func=print):
    """Compile all valid .yar rule files and return a compiled ruleset. Returns (rules, rule_count)"""
    valid_rule_files = {}
    failed_files = []
    try:
        for root, _, files in os.walk(rule_folder):
            for file in files:
                if file.endswith(".yar"):
                    full_path = os.path.join(root, file)
                    try:
                        yara.compile(filepath=full_path)
                        valid_rule_files[file] = full_path
                    except Exception as e:
                        failed_files.append(f"{file}: {e}")
        if not valid_rule_files:
            log_func("[ERROR] No valid YARA rules found.")
            return None, 0
        rules = yara.compile(filepaths=valid_rule_files)
        try:
            log_message(f"[INFO] Compiled {len(valid_rule_files)} YARA rule files.")
        except Exception:
            pass
        log_func(f"[INFO] {len(valid_rule_files)} YARA rules compiled and ready.")
        return rules, len(valid_rule_files)
    except Exception as e:
        try:
            log_message(f"[ERROR] Failed to compile YARA rules: {e}")
        except Exception:
            pass
        log_func("[ERROR] Failed to compile YARA rules. See application log for details.")
        return None, 0


def insert_yara_rule(category, rule_name, rule_content, strings, log_func=print):
    try:
        log_func(f"[INFO] Uploading YARA rule '{rule_name}' to library...")
        
        # Prepare payload according to API documentation
        payload = {
            "category": category,
            "rule": rule_content,
            "strings": strings
        }
        
        # Set authentication headers
        headers = {
            "API-Key": API_YARA_INSERT_KEY,
            "Content-Type": "application/json"
        }
        
        # Send POST request to insert endpoint
        response = requests.post(API_YARA_INSERT, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            log_func(f"[INFO] Successfully uploaded YARA rule '{rule_name}' to library")
            return True
        else:
            log_func(f"[WARNING] Failed to upload YARA rule. Status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        log_func(f"[ERROR] Network error uploading YARA rule: {e}")
        return False
    except Exception as e:
        log_func(f"[ERROR] Failed to upload YARA rule to library: {e}")
        return False
