"""
ScanVault Queue Manager - Maintains sequential processing queue for files.

This module provides a persistent queue system that ensures files are processed
one at a time in the order they were detected, preventing race conditions and
duplicate processing.
"""

import json
import os
import threading
import time
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

QUEUE_FILE = os.path.join("data", "scanvault_queue.json")
_queue_lock = threading.Lock()


def _load_queue() -> List[Dict]:
    """Load the queue from disk."""
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_queue(queue: List[Dict]):
    """Save the queue to disk."""
    try:
        os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(queue, f, indent=2)
    except Exception:
        pass


def add_to_queue(file_path: str, event_type: str = "created") -> bool:
    """
    Add a file to the processing queue.
    
    Args:
        file_path: Absolute path to the file
        event_type: Type of event (created, modified, etc.)
    
    Returns:
        True if added, False if already in queue
    """
    with _queue_lock:
        queue = _load_queue()
        
        # Normalize path for comparison
        normalized = os.path.abspath(file_path).replace("\\", "/").lower()
        
        # Check if already in queue
        for item in queue:
            if item.get("path_normalized") == normalized:
                return False  # Already queued
        
        # Add to queue
        queue_item = {
            "original_path": file_path,
            "path_normalized": normalized,
            "event_type": event_type,
            "queued_at": datetime.now().isoformat(),
            "status": "pending"
        }
        queue.append(queue_item)
        _save_queue(queue)
        
        return True


def is_in_queue(file_path: str) -> bool:
    """
    Check if a file is already in the queue (any status).
    
    Args:
        file_path: Absolute path to the file
    
    Returns:
        True if file is in queue, False otherwise
    """
    with _queue_lock:
        queue = _load_queue()
        normalized = os.path.abspath(file_path).replace("\\", "/").lower()
        
        for item in queue:
            if item.get("path_normalized") == normalized:
                return True
        
        return False


def get_queue_count() -> int:
    """
    Get the current number of pending items in the queue.
    
    Returns:
        Number of pending items
    """
    with _queue_lock:
        queue = _load_queue()
        pending_count = sum(1 for item in queue if item.get("status") == "pending")
        return pending_count


def get_next_pending() -> Optional[Dict]:
    """
    Get the next pending file from the queue without removing it.
    
    Returns:
        Queue item dict or None if queue is empty
    """
    with _queue_lock:
        queue = _load_queue()
        
        # Find first pending item
        for item in queue:
            if item.get("status") == "pending":
                return item
        
        return None


def mark_processing(file_path: str):
    """Mark a file as currently being processed."""
    with _queue_lock:
        queue = _load_queue()
        normalized = os.path.abspath(file_path).replace("\\", "/").lower()
        
        for item in queue:
            if item.get("path_normalized") == normalized:
                item["status"] = "processing"
                item["processing_started"] = datetime.now().isoformat()
                _save_queue(queue)
                break


def mark_completed(file_path: str, success: bool, result: str = None):
    """
    Mark a file as completed and remove from queue.
    
    Args:
        file_path: Path to the file
        success: Whether processing succeeded
        result: Result description (e.g., "restored", "quarantined")
    """
    with _queue_lock:
        queue = _load_queue()
        normalized = os.path.abspath(file_path).replace("\\", "/").lower()
        
        # Remove completed item
        queue = [item for item in queue if item.get("path_normalized") != normalized]
        _save_queue(queue)


def get_queue_size() -> int:
    """Get the number of pending items in the queue."""
    with _queue_lock:
        queue = _load_queue()
        return sum(1 for item in queue if item.get("status") == "pending")


def clear_queue():
    """Clear all items from the queue."""
    with _queue_lock:
        _save_queue([])


def is_in_queue(file_path: str) -> bool:
    """Check if a file is already in the queue."""
    with _queue_lock:
        queue = _load_queue()
        normalized = os.path.abspath(file_path).replace("\\", "/").lower()
        
        return any(item.get("path_normalized") == normalized for item in queue)
