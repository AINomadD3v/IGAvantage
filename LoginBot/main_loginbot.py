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


# --- NEW: Hardcoded XPaths for easier testing ---
class HardcodedXPaths:
    """
    A simple class to hold hardcoded XPath selectors for testing purposes.
    This replaces the dependency on the external xpath_config.py file.
    """

    def __init__(self, package_name):
        self.package_name = package_name

        # --- Login Screen ---
        self.login_edittext_field_generic = f"//*[@resource-id='{package_name}:id/login_text_input_layout']//android.widget.EditText"
        self.login_button = f"//android.widget.Button[@content-desc='Log in']"
        # This selector targets the login button when its text changes to "Loading..."
        self.login_loading_indicator = (
            f"//android.widget.Button[@content-desc='Loading...']"
        )
        self.login_incorrect_password_text_view = "//*[@text='Incorrect password']"

        # --- 2FA Screen ---
        self.two_fa_code_input_field = (
            f"//*[@resource-id='{package_name}:id/verification_code_field']"
        )
        self.two_fa_confirm_button = (
            f"//android.widget.Button[@content-desc='Continue']"
        )
        self.two_fa_check_email_text_view = (
            "//*[@text='Check your email']"  # A general check
        )
        self.two_fa_prompt_view_desc = (
            "//*[@content-desc='two_factor_required_challenge']"
        )

        # --- Post-Login & Home Screen ---
        self.save_login_info_prompt_view = (
            "//*[@content-desc='save_login_info_dialog_title']"
        )
        self.turn_on_notifications_prompt_smart = "//*[@text='Turn on notifications']"
        self.home_your_story_text = "//*[@text='Your story']"

        # --- Account Status ---
        self.account_suspended_text_smart = (
            "//*[@text='Your account has been suspended']"
        )

    def home_user_story_button(self, username):
        # This method creates a dynamic XPath
        return f"//android.widget.Button[@content-desc='Add to story. Your story, double tap to add.']"

    def home_user_story_image(self, username):
        # This method creates a dynamic XPath
        return f"//android.widget.ImageView[@content-desc='{username}']"

    @property
    def save_login_info_prompt_smart(self):
        return self.save_login_info_prompt_view


class InstagramLoginHandler:
    """Handles the Instagram login process, including 2FA, and detects post-login states."""

    def __init__(
        self,
        device: u2.Device,
        interactions: InstagramInteractions,
        # REMOVED: xpaths parameter
        stealth_typer: StealthTyper,
        airtable_client: Optional[AirtableClient] = None,
        record_id: Optional[str] = None,
        base_id: Optional[str] = None,
        table_id: Optional[str] = None,
    ):
        self.d = device
        self.interactions = interactions
        # --- MODIFIED: Use the hardcoded xpaths ---
        self.xpaths = HardcodedXPaths(interactions.app_package)
        self.typer = stealth_typer
        self.logger = setup_logger(self.__class__.__name__)
        self.airtable_client = airtable_client
        self.record_id = record_id
        if airtable_client and base_id and table_id:
            airtable_client.base_id = base_id
            airtable_client.table_id = table_id
        self.package_name = self.interactions.app_package
        self.current_username: Optional[str] = None
        self.logger.debug(f"Initialized Login Handler for package: {self.package_name}")

    def detect_post_login_state(self, username: str, timeout: int = 30) -> str:
        self.logger.info("🔍 Detecting post-login state...")

        checks = {
            "save_login_view": self.xpaths.save_login_info_prompt_view,
            "save_login_smart": self.xpaths.save_login_info_prompt_smart,
            "notifications_smart": self.xpaths.turn_on_notifications_prompt_smart,
            "story_text": self.xpaths.home_your_story_text,
            "story_button": self.xpaths.home_user_story_button(username),
            "story_image": self.xpaths.home_user_story_image(username),
            "2fa_prompt": self.xpaths.two_fa_prompt_view_desc,
            "2fa_input": self.xpaths.two_fa_code_input_field,
            "2fa_text": self.xpaths.two_fa_check_email_text_view,
            "suspended_smart": self.xpaths.account_suspended_text_smart,
        }

        start_time = time.time()
        while time.time() - start_time < timeout:
            for name in [
                "save_login_view",
                "save_login_smart",
                "notifications_smart",
                "story_text",
                "story_button",
                "story_image",
            ]:
                if self.interactions.element_exists(checks[name]):
                    self.logger.info(f"✅ Detected UI indicating Login Success: {name}")
                    return "login_success"

            for name in ["2fa_prompt", "2fa_input", "2fa_text"]:
                if self.interactions.element_exists(checks[name]):
                    self.logger.info(f"✅ Detected UI indicating 2FA Required: {name}")
                    return "2fa_required"

            if self.interactions.element_exists(checks["suspended_smart"]):
                self.logger.warning(
                    f"🚫 Detected UI indicating Account Suspended: suspended_smart"
                )
                return "account_suspended"

            time.sleep(1.0)

        self.logger.error(
            f"⏰ Timeout ({timeout}s): No known post-login state detected."
        )
        return "unknown"

    def handle_2fa(self, email_address: str, email_password: str) -> str:
        self.logger.info("--- Starting 2FA Handling Process ---")

        self.logger.info(f"Attempting to fetch 2FA code for '{email_address}'...")
        verification_code = get_instagram_verification_code(
            email_address, email_password, debug=True
        )

        if not verification_code:
            self.logger.warning("IMAP code retrieval failed. Calling activation API...")
            API_URL = os.getenv(
                "EMAIL_ACTIVATION_API_URL", "http://127.0.0.1:8000/activate-protocols"
            )
            try:
                response = requests.post(
                    API_URL,
                    json={"email": email_address, "password": email_password},
                    timeout=120,
                )
                response.raise_for_status()
                activation_result = response.json()
                if activation_result.get("status") == "success":
                    self.logger.info(
                        "Email protocols activation successful. Retrying code retrieval..."
                    )
                    time.sleep(5)
                    verification_code = get_instagram_verification_code(
                        email_address, email_password, debug=True
                    )
                else:
                    self.logger.error(
                        f"API reported failure: {activation_result.get('message')}"
                    )
                    self._update_airtable_status(
                        {"Status": "Login Failed - 2FA Email Activation Error"}
                    )
                    return "2fa_failed"
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to call activation API at {API_URL}: {e}")
                self._update_airtable_status({"Status": "Login Failed - 2FA API Error"})
                return "2fa_failed"

        if verification_code:
            self.logger.info(f"✅ Successfully retrieved 2FA code: {verification_code}")

            code_input_xpath = self.xpaths.two_fa_code_input_field
            if not self.interactions.wait_for_element_appear(
                code_input_xpath, timeout=10
            ):
                self.logger.error("Could not find the 2FA code input field on screen.")
                return "2fa_failed"

            self.logger.info("Entering the 6-digit code...")
            self.interactions.click_by_xpath(code_input_xpath)
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.3)
            self.typer.type_text(verification_code)
            time.sleep(1)

            confirm_button_xpath = self.xpaths.two_fa_confirm_button
            if self.interactions.click_if_exists(confirm_button_xpath, timeout=5):
                self.logger.info("Clicked the 2FA confirmation button.")
            else:
                self.logger.error(
                    "Could not find or click the 2FA confirmation button."
                )
                return "2fa_failed"

            self.logger.info("Verifying login status after submitting 2FA code...")
            final_state = self.detect_post_login_state(
                username=self.current_username, timeout=30
            )

            if final_state == "login_success":
                return "login_success"
            else:
                self.logger.error(
                    f"Login failed after submitting 2FA code. Final state: {final_state}"
                )
                self._update_airtable_status(
                    {"Status": "Login Failed - 2FA Code Rejected"}
                )
                return "2fa_failed"
        else:
            self.logger.error("❌ Failed to retrieve 2FA code after all attempts.")
            self._update_airtable_status(
                {"Status": "Login Failed - 2FA Code Not Found"}
            )
            return "2fa_failed"

    def _update_airtable_status(self, status_map: dict):
        if self.airtable_client and self.record_id:
            self.logger.info(
                f"📡 Updating Airtable record {self.record_id}: {status_map}"
            )
            try:
                self.airtable_client.update_record_fields(self.record_id, status_map)
                self.logger.info(f"✅ Airtable update successful.")
            except Exception as e:
                self.logger.error(
                    f"❌ Airtable update failed for record {self.record_id}: {e}"
                )
        else:
            self.logger.debug(
                "Airtable client or record_id not provided, skipping status update."
            )

    def _wait_for_2fa_prompt_text(self, timeout=15, interval=0.5) -> bool:
        self.logger.info(
            "Performing robust check for 2FA screen using advanced XPath..."
        )
        xpath_expr = "//*[starts-with(@text, 'Enter the code')]"
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                elem = self.d.xpath(xpath_expr)
                if elem.exists:
                    self.logger.info(f"✅ Found 2FA prompt text: '{elem.get_text()}'")
                    return True
            except UiObjectNotFoundError:
                pass
            time.sleep(interval)
        self.logger.warning("Failed to find the 2FA code prompt text within timeout.")
        return False

    def execute_login(
        self, username: str, password: str, email_address: str, email_password: str
    ) -> str:
        try:
            self.logger.info(f"--- Starting Instagram Login for: {username} ---")
            self.current_username = username

            self.logger.info("Entering username and password...")
            edit_fields = self.d.xpath(self.xpaths.login_edittext_field_generic).all()
            if len(edit_fields) < 2:
                return "error"
            username_field, password_field = edit_fields[0], edit_fields[1]
            username_field.click()
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.3)
            self.typer.type_text(username)
            password_field.click()
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.3)
            self.typer.type_text(password)

            if not self.interactions.click_if_exists(
                self.xpaths.login_button, timeout=5
            ):
                self.logger.error("Could not find or click the main login button.")
                return "error"

            self.logger.info(
                "Login clicked. Now waiting for the loading process to complete."
            )
            loading_indicator = self.d.xpath(self.xpaths.login_loading_indicator)

            if loading_indicator.wait(timeout=5):
                self.logger.info(
                    "✅ 'Loading...' indicator appeared. Waiting for it to disappear..."
                )
                if not loading_indicator.wait_gone(
                    timeout=45
                ):  # Increased timeout for slow networks
                    self.logger.error(
                        "❌ Loading indicator did not disappear within 45 seconds. Login may be stuck."
                    )
                    self.d.screenshot("login_stuck_on_loading.png")
                    return "error"
                self.logger.info("✅ Loading process finished.")
            else:
                self.logger.warning(
                    "⚠️ Loading indicator did not appear. The page may have changed instantly or failed to start loading."
                )

            self.logger.info("Login loading complete, entering post-login checks...")

            if self.interactions.wait_for_element_appear(
                self.xpaths.login_incorrect_password_text_view, timeout=2
            ):
                self.logger.warning("❌ Incorrect Password error detected!")
                self._update_airtable_status({"Status": "Login Failed - Incorrect PW"})
                return "login_failed"

            if self._wait_for_2fa_prompt_text(timeout=5):
                self.logger.info("✅ 2FA screen detected. Starting 2FA handler...")
                tfa_result = self.handle_2fa(email_address, email_password)
                if tfa_result == "login_success":
                    self.logger.info("✅ Login successful after completing 2FA.")
                    self._update_airtable_status(
                        {"Logged In?": True, "Status": "Logged In - Active"}
                    )
                    return "login_success"
                else:
                    return "login_failed"

            self.logger.info(
                "No immediate state found, starting general post-login state detection..."
            )
            final_state = self.detect_post_login_state(username=username, timeout=20)

            if final_state == "login_success":
                self.logger.info("✅ Login successful.")
                self._update_airtable_status(
                    {"Logged In?": True, "Status": "Logged In - Active"}
                )
                return "login_success"
            elif final_state == "2fa_required":
                self.logger.info(
                    "🔑 2FA Required (detected by general poll). Initiating handler."
                )
                tfa_result = self.handle_2fa(email_address, email_password)
                if tfa_result == "login_success":
                    self.logger.info("✅ Login successful after completing 2FA.")
                    self._update_airtable_status(
                        {"Logged In?": True, "Status": "Logged In - Active"}
                    )
                    return "login_success"
                else:
                    return "login_failed"
            elif final_state == "account_suspended":
                self.logger.warning("🚫 Account Suspended.")
                self._update_airtable_status({"Status": "Banned"})
                return "account_banned"
            else:
                self.logger.error(
                    "❌ Login failed: Timeout or Unknown post-login state."
                )
                self._update_airtable_status({"Status": "Login Failed - Unknown State"})
                return "timeout_or_unknown"

        except Exception as e:
            self.logger.error(
                f"💥 Unexpected Error during login process: {e}", exc_info=True
            )
            self._update_airtable_status({"Status": f"Login Error: {type(e).__name__}"})
            return "error"


class PopupHandler:
    """
    Manages background UI watchers based on a JSON/YAML configuration.
    This class initializes, registers, and runs watchers in a background thread
    to handle dynamic popups during automation tasks.
    """

    def __init__(self, driver: u2.Device):
        """
        Initializes the PopupHandler.

        Args:
            driver (u2.Device): The uiautomator2 device instance.
        """
        self.d = driver
        self.logger = setup_logger(self.__class__.__name__)
        self._watcher_thread = None
        self._watcher_stop_event = threading.Event()

        # --- Context attributes for specific watcher callbacks ---
        self.airtable_client = None
        self.record_id = None
        self.package_name = None
        self.base_id = None
        self.table_id = None
        self._suspension_handled = False  # Prevents multiple callback triggers

        # --- Load Configuration using the loader function ---
        self.config = get_popup_config()
        if self.config:
            self.logger.info("Successfully loaded popup config via get_popup_config()")
        else:
            self.logger.error("Failed to load popup config or config is empty.")

    def set_context(self, airtable_client, record_id, package_name, base_id, table_id):
        """Sets the necessary context for watcher callbacks (e.g., for Airtable updates)."""
        self.logger.debug(
            f"Setting context: record_id={record_id}, package={package_name}"
        )
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.package_name = package_name
        self.base_id = base_id
        self.table_id = table_id
        self._suspension_handled = False  # Reset flag each time context is set

    def register_and_start_watchers(self):
        """
        Registers all watchers from the config and starts the background monitoring loop.
        """
        self.logger.info("Registering and starting popup watchers...")
        w = self.d.watcher
        w.reset()  # Clear any existing watchers first

        if not isinstance(self.config, list) or not self.config:
            self.logger.warning(
                "Popup config is empty or invalid. No watchers will be started."
            )
            return

        for entry in self.config:
            name = entry.get("name")
            text_xpath = entry.get("text_xpath")
            button_xpath = entry.get("button_xpath")
            callback_name = entry.get("callback")

            if not name or not text_xpath:
                self.logger.warning(
                    f"Skipping invalid entry (missing name or text_xpath): {entry}"
                )
                continue

            watcher = w(name).when(text_xpath)

            # Prioritize a specific callback over a generic button click if both are defined
            if callback_name:
                callback_method = getattr(self, callback_name, None)
                if callable(callback_method):
                    self.logger.info(
                        f"Registering watcher '{name}': WHEN '{text_xpath}' THEN CALL '{callback_name}'"
                    )
                    watcher.call(callback_method)
                else:
                    self.logger.error(
                        f"Callback '{callback_name}' not found for watcher '{name}'."
                    )
            elif button_xpath:
                # CORRECTED: Use watcher.call() with a lambda to click the target XPath.
                # The watcher passes the triggering UI element ('selector') to the lambda.
                # We capture button_xpath in the lambda to ensure the correct button is clicked.
                self.logger.info(
                    f"Registering watcher '{name}': WHEN '{text_xpath}' THEN CLICK '{button_xpath}'"
                )
                watcher.call(
                    lambda selector, xpath=button_xpath: self.d.xpath(xpath).click()
                )
            else:
                self.logger.warning(
                    f"Watcher '{name}' has no valid action (button_xpath or callback)."
                )

        # CORRECTED: Check the internal _watchers dictionary to see if any watchers were registered.
        # This avoids the AttributeError from .count or .list.
        if not w._watchers:
            self.logger.info(
                "No watchers were successfully registered. Loop will not start."
            )
            return

        # Start the monitoring loop in a background thread
        self._watcher_stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()
        self.logger.info(
            f"✅ {len(w._watchers)} watchers registered. Watcher loop started in background."
        )

    def _watcher_loop(self, interval: float = 1.0):
        """The actual loop that runs in a background thread."""
        self.logger.debug("📡 Watcher thread running.")
        while not self._watcher_stop_event.is_set():
            try:
                self.d.watcher.run()
            except Exception as e:
                self.logger.error(f"💥 Watcher run error: {e}", exc_info=False)
            self._watcher_stop_event.wait(timeout=interval)
        self.logger.info("📡 Watcher thread stopped.")

    def stop_watchers(self):
        """Stops the background watcher loop and removes all registered watchers."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            self.logger.info("🛑 Signaling watcher loop to stop...")
            self._watcher_stop_event.set()
            self._watcher_thread.join(timeout=2.0)
            if self._watcher_thread.is_alive():
                self.logger.warning("Watcher thread did not stop cleanly.")
            self._watcher_thread = None

        try:
            self.d.watcher.stop()
            self.d.watcher.remove()
            self.logger.info("Underlying uiautomator2 watchers stopped and removed.")
        except Exception as e:
            # Hide "watch already stopped" message for cleaner logs
            if "watch already stopped" not in str(e):
                self.logger.error(f"Error stopping uiautomator2 watcher: {e}")

    # --- Specific Handler Callbacks (used by watchers) ---

    def handle_suspension(self, selector):
        """Callback triggered by a 'account_suspended' watcher."""
        self.logger.warning("🚫 WATCHER: Account suspended popup detected!")
        if self._suspension_handled:
            self.logger.info("⏭️ Suspension already handled for this account.")
            return

        if not self.record_id or not self.airtable_client:
            self.logger.error(
                "❌ Cannot handle suspension: Missing record_id or Airtable client."
            )
            return

        try:
            self.logger.info(f"Updating Airtable record {self.record_id} to 'Banned'.")
            if self.base_id:
                self.airtable_client.base_id = self.base_id
            if self.table_id:
                self.airtable_client.table_id = self.table_id

            self.airtable_client.update_record_fields(
                self.record_id, {"Status": "Banned"}
            )
            self.logger.info("✅ Updated Airtable status to 'Banned'.")

            if self.package_name:
                self.logger.info(f"🛑 Stopping suspended app: {self.package_name}")
                self.d.app_stop(self.package_name)

            self._suspension_handled = True
        except Exception as e:
            self.logger.error(
                f"💥 Error in handle_suspension callback: {e}", exc_info=True
            )


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


# # --- STANDALONE TEST BLOCK ---
# if __name__ == "__main__":
#     module_logger.info("--- Running Instagram Login Handler Standalone E2E Test ---")
#
#     # --- Configuration ---
#     INSTAGRAM_PACKAGE_NAME = (
#         "com.instagram.androir"  # Using the specified clone package name
#     )
#     BASE_ID = os.getenv("IG_ARMY_BASE_ID")
#     TABLE_ID = os.getenv("IG_ARMY_ACCS_TABLE_ID")
#
#     # --- Initialize clients and variables ---
#     d = None
#     popup_handler = None
#     login_result = "not_run"
#
#     try:
#         # --- 1. Fetch Account from Airtable ---
#         module_logger.info("Fetching one unused account from Airtable...")
#         airtable_client = AirtableClient()
#         accounts_to_test = airtable_client.fetch_unused_accounts(max_records=1)
#
#         if not accounts_to_test:
#             module_logger.error(
#                 "❌ No unused accounts found in Airtable. Cannot proceed."
#             )
#             sys.exit(1)
#
#         account_data = accounts_to_test[0]
#         TEST_USERNAME = account_data["instagram_username"]
#         TEST_PASSWORD = account_data["instagram_password"]
#         TEST_EMAIL = account_data["email_address"]
#         TEST_EMAIL_PASSWORD = account_data["email_password"]
#         TEST_RECORD_ID = account_data["record_id"]
#
#         module_logger.info(
#             f"✅ Found account to test: {TEST_USERNAME} (Record: {TEST_RECORD_ID})"
#         )
#
#         # --- 2. Connect to Device and Rotate IP ---
#         module_logger.info("Connecting to device...")
#         d = u2.connect()
#         module_logger.info(f"Connected to device: {d.serial}")
#
#         module_logger.info("--- Starting NordVPN IP Rotation ---")
#         try:
#             rotate_nordvpn_ip(d)
#             module_logger.info("✅ NordVPN IP rotation successful.")
#         except Exception as vpn_error:
#             module_logger.error(f"❌ VPN IP rotation failed: {vpn_error}. Aborting.")
#             sys.exit(1)
#
#         # --- 3. Initialize and Start Popup Watchers ---
#         module_logger.info("Initializing and starting PopupHandler...")
#         popup_handler = PopupHandler(driver=d)
#         popup_handler.set_context(
#             airtable_client=airtable_client,
#             record_id=TEST_RECORD_ID,
#             package_name=INSTAGRAM_PACKAGE_NAME,
#             base_id=BASE_ID,
#             table_id=TABLE_ID,
#         )
#         popup_handler.register_and_start_watchers()
#
#         # --- 4. Prepare for Login ---
#         module_logger.info(f"Starting Instagram app ('{INSTAGRAM_PACKAGE_NAME}')...")
#         d.app_start(INSTAGRAM_PACKAGE_NAME, stop=True)
#         time.sleep(5)  # Wait for app to settle
#
#         # Initialize automation helpers
#         interactions = InstagramInteractions(
#             device=d, app_package=INSTAGRAM_PACKAGE_NAME
#         )
#         typer = StealthTyper(device_id=d.serial)
#         login_handler = InstagramLoginHandler(
#             device=d,
#             interactions=interactions,
#             stealth_typer=typer,
#             airtable_client=airtable_client,
#             record_id=TEST_RECORD_ID,
#             base_id=BASE_ID,
#             table_id=TABLE_ID,
#         )
#
#         # --- 5. Execute Login ---
#         login_result = login_handler.execute_login(
#             TEST_USERNAME, TEST_PASSWORD, TEST_EMAIL, TEST_EMAIL_PASSWORD
#         )
#
#     except Exception as e:
#         module_logger.error(
#             f"💥 A critical error occurred during the test: {e}", exc_info=True
#         )
#         login_result = "critical_error"
#
#     finally:
#         # --- 6. Cleanup and Final Report ---
#         module_logger.info("--- Test Process Finished ---")
#         module_logger.info(f"Final Login Status: {login_result.upper()}")
#
#         if popup_handler:
#             module_logger.info("Stopping popup watchers...")
#             popup_handler.stop_watchers()
#
#         module_logger.info("--- Test Complete ---")
