"""
Refactored `post_reel.py` for agent-based, modular, tool-oriented design.
All shared utilities, interactions, and dependencies are reused or abstracted for reuse.
This version is designed for higher resilience, future automation, and integration with agent workflows.
"""

import os
import threading
import time
from typing import Optional, Tuple

import uiautomator2 as u2

from PostingBot.tools.device_tool import DeviceTool
from PostingBot.tools.failure_handler_tool import failure_triggered, handle_post_failure
from PostingBot.tools.logging_tool import logger

# --- Modular Tools (Shared System Interfaces) ---
from PostingBot.tools.media_tool import MediaTool
from PostingBot.tools.reel_creation_tool import ReelCreationTool

# --- Core Workflow: Post Reel ---


def post_reel(
    record: dict, project_root: str, airtable_client
) -> Tuple[bool, Optional[str]]:
    """
    Orchestrates the posting of an Instagram Reel from a record.

    Args:
        record (dict): Airtable record with fields like username, media_url, device_id, etc.
        project_root (str): Root path of the project (used for temp storage).
        airtable_client: Airtable interface (must implement update/rotate methods).

    Returns:
        Tuple[bool, Optional[str]]: (Success flag, Error message or None)
    """

    record_id = record.get("id", "N/A")
    fields = record.get("fields", {})
    account_name = fields.get("username")
    media_url = fields.get("media_url")
    package_name = fields.get("package_name")
    device_id = fields.get("device_id")

    logger.info(f"\n\n📲 Starting post_reel flow for record ID: {record_id}\n")

    # Fail early if required data is missing
    missing_fields = [
        k
        for k in ["username", "media_url", "package_name", "device_id"]
        if not fields.get(k)
    ]
    if missing_fields:
        return False, f"Missing required fields for posting: {missing_fields}"

    failure_triggered.clear()  # Reset global abort flag

    # Initialize Device
    device_tool = DeviceTool(device_id=device_id)
    try:
        device = device_tool.connect()
    except ConnectionError as e:
        return False, str(e)

    # Register UI watchers to detect popups and toasts
    device_tool.start_watchers()

    # --- Download & Push Media ---
    media_tool = MediaTool(project_root)
    success, local_path, remote_path, err_msg = media_tool.prepare_media(
        media_url, account_name, device
    )
    if not success:
        return False, err_msg

    # --- Instagram UI Interactions ---
    reel_tool = ReelCreationTool(device, package_name, airtable_client)

    # Step 1: Launch App and Wait for Home
    if not reel_tool.launch_app():
        return False, f"Failed to launch {package_name}"
    if failure_triggered.is_set():
        handle_post_failure(record_id, airtable_client)
        return False, "Aborted: Popup/Toast during app launch"

    # Step 2: Open New Post -> REEL Tab -> New Reel Screen
    if not reel_tool.prepare_reel_creation():
        return False, "Failed to enter reel creation flow."

    if failure_triggered.is_set():
        handle_post_failure(record_id, airtable_client)
        return False, "Aborted: Popup/Toast during reel setup"

        # Step 3: Select Video & Load Editor
        return False, "Video selection or editor loading failed."

    if failure_triggered.is_set():
        handle_post_failure(record_id, airtable_client)
        return False, "Aborted: Failure after editor load."

    # Step 4: Optional Audio Adding (optional tool)
    if not reel_tool.add_music():
        logger.warning("🎵 Music adding skipped or failed.")

    # Step 5: Next -> Add Caption -> Share
    if not reel_tool.finalize_and_share(record):
        return False, "Reel finalization or sharing failed."

    # Done: Cleanup and Return
    media_tool.cleanup(local_path, device)
    logger.info(f"✅ Finished posting reel for record {record_id}\n")
    return True, None
