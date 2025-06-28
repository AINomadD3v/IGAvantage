# LoginBot/main_loginbot.py

import os
import sys
import time
from typing import Optional

import uiautomator2 as u2
from uiautomator2 import UiObjectNotFoundError

# This adds the project root to the Python path, allowing imports from Shared
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import json
import os
import threading
import time
from typing import Optional  # Added for type hinting

import requests  # For the API-based approach
import uiautomator2 as u2
from PIL import Image

from Shared.config_loader import get_popup_config
from Shared.Data.airtable_manager import AirtableClient

# REMOVED: from Shared.Utils.xpath_config import InstagramXPaths
from Shared.Imap.get_imap_code import get_instagram_verification_code
from Shared.instagram_actions import InstagramInteractions
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper

# --- NEW VPN IMPORT ---
from Shared.VPN.nord import main_flow as rotate_nordvpn_ip

logger = setup_logger(
    name="PopupHandler"
)  # Changed logger name slightly for consistency


module_logger = setup_logger(__name__)

# --- STANDALONE WATCHER TEST BLOCK ---
if __name__ == "__main__":
    module_logger.info("--- Running Popup Watcher Standalone Test ---")

    # --- Configuration ---
    # Duration to run the test in seconds.
    # During this time, you should manually trigger popups on the device.
    TEST_DURATION_SECONDS = 180  # 3 minutes

    # --- Initialize variables ---
    d = None
    popup_handler = None

    try:
        # --- 1. Connect to Device ---
        module_logger.info("Connecting to device...")
        d = u2.connect()
        module_logger.info(f"Connected to device: {d.serial}")
        module_logger.info(f"Device screen dimensions: {d.window_size()}")

        # --- 2. Initialize and Start Popup Watchers ---
        # Note: For this test, we are not setting a real Airtable client.
        # Callbacks that require Airtable will log an error, which is expected.
        # The main goal is to confirm that the watcher *triggers*.
        module_logger.info("Initializing and starting PopupHandler...")
        popup_handler = PopupHandler(driver=d)

        # Set dummy context to test the callback logic.
        # The 'handle_suspension' callback will attempt to use these values.
        popup_handler.set_context(
            airtable_client=None,  # No real Airtable client needed for this test
            record_id="dummy_record_123",
            package_name="com.instagram.androir",  # The package of the app you are testing
            base_id="dummy_base_abc",
            table_id="dummy_table_xyz",
        )

        popup_handler.register_and_start_watchers()

        # --- 3. Wait for Popups to be Triggered Manually ---
        module_logger.info("=" * 60)
        module_logger.info(
            f"WATCHERS ARE NOW ACTIVE FOR {TEST_DURATION_SECONDS} SECONDS."
        )
        module_logger.info(
            "Please manually navigate the app on the device and trigger popups."
        )
        module_logger.info("Examples:")
        module_logger.info("  - Trigger the 'Your account has been suspended' screen.")
        module_logger.info("  - Trigger the 'Save your login info?' dialog.")
        module_logger.info("  - Trigger the 'Turn on notifications' prompt.")
        module_logger.info(
            "Watch the console logs here to see if the watchers are triggered."
        )
        module_logger.info("=" * 60)

        # Keep the script alive to let the background watchers run.
        end_time = time.time() + TEST_DURATION_SECONDS
        while time.time() < end_time:
            # Print a heartbeat message to show the script is still running
            remaining_time = int(end_time - time.time())
            # The \r character moves the cursor to the beginning of the line
            print(f"\rTest running... Time remaining: {remaining_time:03d}s", end="")
            time.sleep(1)

        print("\n")  # Add a newline after the countdown finishes
        module_logger.info("Test duration complete.")

    except KeyboardInterrupt:
        module_logger.info("\nKeyboard interrupt received. Shutting down gracefully.")
    except Exception as e:
        module_logger.error(
            f"💥 A critical error occurred during the test: {e}", exc_info=True
        )

    finally:
        # --- 4. Cleanup ---
        module_logger.info("--- Test Process Finished ---")

        if popup_handler:
            module_logger.info("Stopping popup watchers...")
            popup_handler.stop_watchers()

        module_logger.info("--- test complete ---")
