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
import threading

import requests  # For the API-based approach

# --- Your existing imports ---
from get_imap_code import get_instagram_verification_code
from nord import main_flow as rotate_nordvpn_ip
from PIL import Image

from Shared.config_loader import get_popup_config
from Shared.Data.airtable_manager import AirtableClient
from Shared.instagram_actions import InstagramInteractions
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper

# --- Logger Setup ---
module_logger = setup_logger(__name__)


# --- MODIFIED: Using the exact XPaths as requested ---
class HardcodedXPaths:
    """
    A simple class to hold hardcoded XPath selectors for testing purposes.
    It uses the advanced uiautomator2 selector syntax.
    """

    def __init__(self, package_name):
        self.package_name = package_name

        # --- Login Screen (as per user specification) ---
        self.login_page = f"//*[@content-desc='Forgot password?']"
        self.login_username_smart = f"^Username, email or mobile number"
        self.login_password_smart = f"^Password"
        self.login_button = f"//android.widget.Button[@content-desc='Log in']"
        self.login_loading_indicator = (
            f"//android.widget.Button[@content-desc='Loading...']"
        )
        self.login_incorrect_password_text_view = "//*[@text='Incorrect password']"

        # --- 2FA Screen ---
        self.two_fa_code_input_field = f"^Enter code"
        self.two_fa_confirm_button = f"^Continue"
        self.two_fa_check_email_text_view = "//*[@text='Check your email']"
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
        return f"//android.widget.Button[@content-desc='Add to story. Your story, double tap to add.']"

    def home_user_story_image(self, username):
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
        stealth_typer: StealthTyper,
        airtable_client: Optional[AirtableClient] = None,
        record_id: Optional[str] = None,
        base_id: Optional[str] = None,
        table_id: Optional[str] = None,
    ):
        self.d = device
        self.interactions = interactions
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

        verification_code = None
        max_retries = 5  # Try up to 5 times
        retry_delay = 15  # Wait 15 seconds between tries

        for attempt in range(max_retries):
            self.logger.info(
                f"Attempting to fetch 2FA code for '{email_address}'... (Attempt {attempt + 1}/{max_retries})"
            )
            code = get_instagram_verification_code(
                email_address, email_password, debug=True
            )
            if code:
                self.logger.info("✅ Code found!")
                verification_code = code
                break

            self.logger.warning(
                f"Code not found. Waiting {retry_delay} seconds before retrying..."
            )
            time.sleep(retry_delay)

        if not verification_code:
            self.logger.warning(
                "IMAP code retrieval failed. Calling activation API as a fallback..."
            )
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
                    return "2fa_failed"
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to call activation API at {API_URL}: {e}")
                return "2fa_failed"

        if verification_code:
            self.logger.info(f"✅ Successfully retrieved 2FA code: {verification_code}")
            code_input_xpath = self.xpaths.two_fa_code_input_field
            if not self.interactions.wait_for_element_appear(
                code_input_xpath, timeout=10
            ):
                self.logger.error("Could not find the 2FA code input field.")
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
                    f"Login failed after submitting 2FA. Final state: {final_state}"
                )
                return "2fa_failed"
        else:
            self.logger.error("❌ Failed to retrieve 2FA code after all attempts.")
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
        self.logger.info("Performing robust check for 2FA screen...")
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

            # Step 1: Wait for the login page
            self.logger.info("Waiting for the main login page to be visible...")
            if not self.interactions.wait_for_element_appear(
                self.xpaths.login_page, timeout=20
            ):
                self.logger.error("❌ Timed out waiting for the login page.")
                self.d.screenshot("login_page_not_found_error.png")
                return "error"
            self.logger.info("✅ Login page identified.")

            # Step 2: Enter username
            self.logger.info("Entering username...")
            try:
                username_field = self.d.xpath(self.xpaths.login_username_smart)
                if not username_field.wait(timeout=5):
                    self.logger.error("❌ Username field not found.")
                    self.d.screenshot("username_field_not_found_error.png")
                    return "error"
                username_field.click()
                time.sleep(0.5)
                self.d.clear_text()
                time.sleep(0.3)
                self.typer.type_text(username)
            except Exception as e:
                self.logger.error(f"❌ Failed to type username: {e}", exc_info=True)
                self.d.screenshot("username_typing_error.png")
                return "error"

            # Step 3: Enter password
            self.logger.info("Entering password...")
            try:
                password_field = self.d.xpath(self.xpaths.login_password_smart)
                if not password_field.wait(timeout=5):
                    self.logger.error("❌ Password field not found.")
                    self.d.screenshot("password_field_not_found_error.png")
                    return "error"
                password_field.click()
                time.sleep(0.5)
                self.d.clear_text()
                time.sleep(0.3)
                self.typer.type_text(password)
            except Exception as e:
                self.logger.error(f"❌ Failed to type password: {e}", exc_info=True)
                self.d.screenshot("password_typing_error.png")
                return "error"

            # Step 4: Click Login
            if not self.interactions.click_if_exists(
                self.xpaths.login_button, timeout=5
            ):
                self.logger.error("Could not find or click the main login button.")
                return "error"

            self.logger.info("Login clicked. Waiting for loading to complete.")
            loading_indicator = self.d.xpath(self.xpaths.login_loading_indicator)
            if loading_indicator.wait(timeout=5):
                self.logger.info("✅ 'Loading...' indicator appeared.")
                if not loading_indicator.wait_gone(timeout=45):
                    self.logger.error("❌ Loading indicator did not disappear.")
                    self.d.screenshot("login_stuck_on_loading.png")
                    return "error"
                self.logger.info("✅ Loading process finished.")
            else:
                self.logger.warning("⚠️ Loading indicator did not appear.")

            # Step 5: Post-login checks
            self.logger.info("Entering post-login checks...")
            if self.interactions.wait_for_element_appear(
                self.xpaths.login_incorrect_password_text_view, timeout=2
            ):
                self.logger.warning("❌ Incorrect Password error detected!")
                self._update_airtable_status({"Status": "Login Failed - Incorrect PW"})
                return "login_failed"

            if self._wait_for_2fa_prompt_text(timeout=5):
                self.logger.info("✅ 2FA screen detected. Starting 2FA handler...")
                return self.handle_2fa(email_address, email_password)

            final_state = self.detect_post_login_state(username=username, timeout=20)
            if final_state == "login_success":
                self.logger.info("✅ Login successful.")
                self._update_airtable_status(
                    {"Logged In?": True, "Status": "Logged In - Active"}
                )
                return "login_success"
            elif final_state == "2fa_required":
                self.logger.info("🔑 2FA Required. Initiating handler.")
                return self.handle_2fa(email_address, email_password)
            elif final_state == "account_suspended":
                self.logger.warning("🚫 Account Suspended.")
                self._update_airtable_status({"Status": "Banned"})
                return "account_banned"
            else:
                self.logger.error("❌ Login failed: Timeout or Unknown state.")
                self._update_airtable_status({"Status": "Login Failed - Unknown State"})
                return "timeout_or_unknown"

        except Exception as e:
            self.logger.error(f"💥 Unexpected Error during login: {e}", exc_info=True)
            self._update_airtable_status({"Status": f"Login Error: {type(e).__name__}"})
            return "error"


class PopupHandler:
    """Manages background UI watchers to handle dynamic popups."""

    def __init__(self, driver: u2.Device):
        self.d = driver
        self.logger = setup_logger(self.__class__.__name__)
        self._watcher_thread = None
        self._watcher_stop_event = threading.Event()
        self.airtable_client = None
        self.record_id = None
        self.package_name = None
        self.base_id = None
        self.table_id = None
        self._suspension_handled = False
        self.config = get_popup_config()
        if self.config:
            self.logger.info("Successfully loaded popup config.")
        else:
            self.logger.error("Failed to load popup config.")

    def set_context(self, airtable_client, record_id, package_name, base_id, table_id):
        self.logger.debug(
            f"Setting context: record_id={record_id}, package={package_name}"
        )
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.package_name = package_name
        self.base_id = base_id
        self.table_id = table_id
        self._suspension_handled = False

    def register_and_start_watchers(self):
        self.logger.info("Registering and starting popup watchers...")
        w = self.d.watcher
        w.reset()

        if not isinstance(self.config, list) or not self.config:
            self.logger.warning("Popup config invalid. No watchers will start.")
            return

        for entry in self.config:
            name = entry.get("name")
            text_xpath = entry.get("text_xpath")
            button_xpath = entry.get("button_xpath")
            callback_name = entry.get("callback")

            if not name or not text_xpath:
                self.logger.warning(f"Skipping invalid entry: {entry}")
                continue

            watcher = w(name).when(text_xpath)

            # --- FIX APPLIED HERE ---
            if callback_name:
                # Only call getattr if callback_name is not None
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
                self.logger.info(
                    f"Registering watcher '{name}': WHEN '{text_xpath}' THEN CLICK '{button_xpath}'"
                )
                watcher.call(
                    lambda selector, xpath=button_xpath: self.d.xpath(xpath).click()
                )
            else:
                self.logger.warning(f"Watcher '{name}' has no valid action.")

        if not w._watchers:
            self.logger.info("No watchers registered. Loop will not start.")
            return

        self._watcher_stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()
        self.logger.info(f"✅ {len(w._watchers)} watchers started in background.")

    def _watcher_loop(self, interval: float = 1.0):
        self.logger.debug("📡 Watcher thread running.")
        while not self._watcher_stop_event.is_set():
            try:
                self.d.watcher.run()
            except Exception as e:
                self.logger.error(f"💥 Watcher run error: {e}", exc_info=False)
            self._watcher_stop_event.wait(timeout=interval)
        self.logger.info("📡 Watcher thread stopped.")

    def stop_watchers(self):
        if self._watcher_thread and self._watcher_thread.is_alive():
            self.logger.info("🛑 Signaling watcher loop to stop...")
            self._watcher_stop_event.set()
            self._watcher_thread.join(timeout=2.0)
            self._watcher_thread = None

        try:
            self.d.watcher.stop()
            self.d.watcher.remove()
            self.logger.info("Underlying uiautomator2 watchers stopped.")
        except Exception as e:
            if "watch already stopped" not in str(e):
                self.logger.error(f"Error stopping uiautomator2 watcher: {e}")

    # --- Watcher Callbacks ---
    def handle_suspension(self, selector):
        self.logger.warning("🚫 WATCHER: Account suspended popup detected!")
        if self._suspension_handled:
            self.logger.info("⏭️ Suspension already handled for this account.")
            return
        if not self.record_id or not self.airtable_client:
            self.logger.error("❌ Cannot handle suspension: Missing context.")
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
            self.logger.error(f"💥 Error in handle_suspension: {e}", exc_info=True)

    def handle_vpn_slow_connection(self, selector):
        self.logger.warning("WATCHER: 'handle_vpn_slow_connection' triggered.")

    def photo_removed_callback(self, selector):
        self.logger.warning("WATCHER: 'photo_removed_callback' triggered.")

    def handle_generic_error_toast(self, selector):
        self.logger.warning("WATCHER: 'handle_generic_error_toast' triggered.")


# --- Main Execution Block ---
if __name__ == "__main__":
    module_logger.info("--- Main LoginBot Script Started ---")

    BASE_ID = os.getenv("IG_ARMY_BASE_ID")
    TABLE_ID = os.getenv("IG_ARMY_ACCS_TABLE_ID")

    d = None
    popup_handler = None
    login_result = "not_run"

    try:
        # 1. Fetch Account Details from Airtable
        module_logger.info("Fetching one unused account from Airtable...")
        airtable_client = AirtableClient()
        accounts_to_process = airtable_client.fetch_unused_accounts(max_records=1)

        if not accounts_to_process:
            module_logger.error("❌ No unused accounts found. Cannot proceed.")
            sys.exit(1)

        account_data = accounts_to_process[0]

        # Extract and clean the device_id and package_name
        device_id_val = account_data.get("device_id")
        package_name_val = account_data.get("package_name")

        if isinstance(device_id_val, list) and device_id_val:
            DEVICE_ID = device_id_val[0].strip()
        elif isinstance(device_id_val, str):
            DEVICE_ID = device_id_val.strip()
        else:
            DEVICE_ID = None

        if isinstance(package_name_val, list) and package_name_val:
            PACKAGE_NAME = package_name_val[0].strip()
        elif isinstance(package_name_val, str):
            PACKAGE_NAME = package_name_val.strip()
        else:
            PACKAGE_NAME = None

        if not DEVICE_ID or not PACKAGE_NAME:
            module_logger.error(
                f"❌ Account {account_data.get('instagram_username')} is missing "
                f"a valid 'device_id' or 'package_name' after processing. Skipping."
            )
            sys.exit(1)

        module_logger.info(
            f"✅ Processing account: {account_data['instagram_username']} "
            f"on device: '{DEVICE_ID}' for package: '{PACKAGE_NAME}'"
        )

        # 2. Connect to the Specific Device
        module_logger.info(f"Connecting to device: {DEVICE_ID}...")
        d = u2.connect(DEVICE_ID)
        module_logger.info(f"✅ Connected to device: {d.serial}")

        # 3. Rotate IP Address
        module_logger.info("--- Starting NordVPN IP Rotation ---")
        try:
            rotate_nordvpn_ip(d)
            module_logger.info("✅ NordVPN IP rotation successful.")
        except Exception as vpn_error:
            module_logger.error(f"❌ VPN IP rotation failed: {vpn_error}. Aborting.")
            sys.exit(1)

        # 4. Initialize and Start Popup Watchers
        module_logger.info("Initializing and starting PopupHandler...")
        popup_handler = PopupHandler(driver=d)
        popup_handler.set_context(
            airtable_client=airtable_client,
            record_id=account_data["record_id"],
            package_name=PACKAGE_NAME,
            base_id=BASE_ID,
            table_id=TABLE_ID,
        )
        popup_handler.register_and_start_watchers()

        # 5. Start Instagram Application
        module_logger.info(f"Starting Instagram app ('{PACKAGE_NAME}')...")
        d.app_start(PACKAGE_NAME, stop=True)
        time.sleep(5)

        # 6. Initialize Handlers for Login Execution
        interactions = InstagramInteractions(device=d, app_package=PACKAGE_NAME)
        typer = StealthTyper(device_id=d.serial)
        login_handler = InstagramLoginHandler(
            device=d,
            interactions=interactions,
            stealth_typer=typer,
            airtable_client=airtable_client,
            record_id=account_data["record_id"],
            base_id=BASE_ID,
            table_id=TABLE_ID,
        )

        # 7. Execute the Login Process
        login_result = login_handler.execute_login(
            username=account_data["instagram_username"],
            password=account_data["instagram_password"],
            email_address=account_data["email_address"],
            email_password=account_data["email_password"],
        )

    except Exception as e:
        module_logger.error(
            f"💥 A critical error occurred during execution: {e}", exc_info=True
        )
        login_result = "critical_error"

    finally:
        # 8. Cleanup and Final Status
        module_logger.info("--- Execution Finished ---")
        module_logger.info(f"Final Login Status: {login_result.upper()}")

        if popup_handler:
            module_logger.info("Stopping popup watchers...")
            popup_handler.stop_watchers()

        module_logger.info("--- Script Complete ---")
