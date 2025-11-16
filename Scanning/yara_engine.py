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
    """Fetch categorized YARA rules from remote and merge with local rules.
    
    Smart merge strategy:
    - Only adds NEW rules from server
    - Preserves existing local rules
    - Updates rules if server version is different
    
    Returns a tuple: (fetch_status, rule_count)
    fetch_status: 'remote' (new rules added), 'local' (offline/no updates), or 'none' (no rules)
    rule_count: number of rules processed
    """
    # Count existing local rules first
    existing_rules = {}
    for root, _, files in os.walk(YARA_FOLDER):
        for file in files:
            if file.endswith(".yar"):
                full_path = os.path.join(root, file)
                # Store relative path as key for comparison
                rel_path = os.path.relpath(full_path, YARA_FOLDER)
                existing_rules[rel_path] = full_path
    
    initial_rule_count = len(existing_rules)
    # User-friendly message (no technical details)
    if initial_rule_count > 0:
        log_message(f"[INFO] {initial_rule_count} threat signatures loaded from local storage")
    
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
                log_message(f"[DEBUG] Checking for signature updates...")
                resp = requests.get(API_YARA_FETCH, headers=hdr, timeout=10)
                log_message(f"[DEBUG] Server response: {resp.status_code}")
                if resp.status_code == 200:
                    response = resp
                    break
                else:
                    last_exc = Exception(f"Server returned status {resp.status_code}")
            except Exception as inner_e:
                last_exc = inner_e
                log_message(f"[DEBUG] Connection attempt failed: {inner_e}")
        
        if response is None:
            raise last_exc or Exception("Connection failed")
        
        response.raise_for_status()
        json_data = response.json()
        
        if not json_data:
            if initial_rule_count > 0:
                return ("local", initial_rule_count)
            else:
                return ("none", 0)
        
        # Process and merge rules
        new_rules_added = 0
        updated_rules = 0
        
        for rule in json_data:
            category = rule.get("categoryname", "uncategorized")
            rule_name = rule.get("rulename", "unknown_rule")
            rule_content = rule.get("conditions", [{}])[0].get("string", "")
            
            category_dir = os.path.join(YARA_FOLDER, category)
            os.makedirs(category_dir, exist_ok=True)
            
            file_path = os.path.join(category_dir, f"{rule_name}.yar")
            rel_path = os.path.relpath(file_path, YARA_FOLDER)
            
            # Check if rule already exists
            if rel_path in existing_rules:
                # Rule exists - check if content is different (update scenario)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    
                    if existing_content != rule_content:
                        # Content is different - update it
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(rule_content)
                        updated_rules += 1
                        log_message(f"[DEBUG] Updated signature: {category}/{rule_name}")
                except Exception as e:
                    log_message(f"[DEBUG] Failed to update signature {rule_name}: {e}")
            else:
                # New rule - add it
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(rule_content)
                    new_rules_added += 1
                    log_message(f"[DEBUG] Added new signature: {category}/{rule_name}")
                except Exception as e:
                    log_message(f"[DEBUG] Failed to save signature {rule_name}: {e}")
        
        # Count final rules
        final_count = 0
        for root, _, files in os.walk(YARA_FOLDER):
            for file in files:
                if file.endswith(".yar"):
                    final_count += 1
        
        # User-friendly status messages
        if new_rules_added > 0 or updated_rules > 0:
            log_message(f"[INFO] Signature database updated: {new_rules_added} new, {updated_rules} improved")
            return ("remote", final_count)
        else:
            log_message(f"[INFO] Signature database is current")
            return ("local", final_count)
            
    except Exception as e:
        log_message(f"[DEBUG] Online update check failed: {e}")
        
        # Fallback to local rules (user-friendly message)
        local_count = len(existing_rules)
        if local_count > 0:
            # Don't show error - just use local rules silently
            return ("local", local_count)
        else:
            log_func("Unable to initialize scanner. Please check your internet connection.")
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
                        log_message(f"[DEBUG] Invalid signature file: {file}")
        
        if not valid_rule_files:
            log_message("[DEBUG] No valid signature files found")
            return None, 0
        
        rules = yara.compile(filepaths=valid_rule_files)
        log_message(f"[INFO] Loaded {len(valid_rule_files)} threat signatures")
        return rules, len(valid_rule_files)
    except Exception as e:
        log_message(f"[ERROR] Failed to compile signatures: {e}")
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
