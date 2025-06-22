# LoginBot/instagram_login.py
# Renamed file and class to better reflect purpose

import os
import time
from typing import Optional

import uiautomator2 as u2
from Shared.Data.airtable_manager import AirtableClient

# Assuming InstagramInteractions is now in Shared directory
from Shared.instagram_actions import InstagramInteractions

# Core project imports
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper
from Shared.Utils.xpath_config import InstagramXPaths  # Import the Instagram XPaths

# Assuming PopupHandler might be needed later, though not used in the original snippet directly for login logic itself
# from Shared.UI.popup_handler import PopupHandler

# Use module-level logger for setup messages before class instantiation
module_logger = setup_logger(__name__)


class InstagramLoginHandler:
    """Handles the Instagram login process and detects post-login states."""

    def __init__(
        self,
        device: u2.Device,
        interactions: InstagramInteractions,
        xpaths: InstagramXPaths,
        stealth_typer: StealthTyper,
        airtable_client: Optional[AirtableClient] = None,
        record_id: Optional[str] = None,
        # Base ID and Table ID might be needed if AirtableClient is shared/reused
        base_id: Optional[str] = None,
        table_id: Optional[str] = None,
    ):
        """
        Initializes the InstagramLoginHandler.

        Args:
            device (u2.Device): The uiautomator2 device instance.
            interactions (InstagramInteractions): Instance for UI interactions.
            xpaths (InstagramXPaths): Instance containing Instagram XPath selectors.
            stealth_typer (StealthTyper): Instance for stealth typing.
            airtable_client (Optional[AirtableClient]): Airtable client for status updates.
            record_id (Optional[str]): Airtable record ID to update.
            base_id (Optional[str]): Airtable base ID (if client context needs setting).
            table_id (Optional[str]): Airtable table ID (if client context needs setting).
        """
        self.d = device  # Keep device for direct access if needed (e.g., .all())
        self.interactions = interactions
        self.xpaths = xpaths
        self.typer = stealth_typer
        self.logger = setup_logger(self.__class__.__name__)
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.base_id = base_id
        self.table_id = table_id
        # Ensure package name is consistent
        self.package_name = self.interactions.app_package
        self.logger.debug(f"Initialized Login Handler for package: {self.package_name}")

    def wait_for_2fa_screen(self, timeout: int = 30) -> bool:
        """Wait for the 2FA screen ('Check your email' text) to appear."""
        self.logger.info("Waiting for 2FA screen ('Check your email' text)...")
        # Use the specific TextView XPath from config
        xpath = self.xpaths.two_fa_check_email_text_view
        return self.interactions.wait_for_element_appear(xpath, timeout=timeout)

    def detect_post_login_state(self, username: str, timeout: int = 30) -> str:
        """
        Determines the screen state after submitting login credentials by polling elements.

        Args:
            username (str): The username used for login (for dynamic story XPaths).
            timeout (int): Maximum time in seconds to wait for a state indicator.

        Returns:
            str: "login_success", "2fa_required", "account_suspended", or "unknown".
        """
        self.logger.info("🔍 Detecting post-login state...")

        # Define checks using methods/properties from self.xpaths
        # Order matters for prioritization (success > 2fa > suspended)
        checks = {
            # Login Success indicators (prioritized)
            "save_login_view": self.xpaths.save_login_info_prompt_view,
            "save_login_smart": self.xpaths.save_login_info_prompt_smart,
            "notifications_smart": self.xpaths.turn_on_notifications_prompt_smart,
            "story_text": self.xpaths.home_your_story_text,
            "story_button": self.xpaths.home_user_story_button(username),
            "story_image": self.xpaths.home_user_story_image(username),
            # 2FA indicators
            "2fa_prompt": self.xpaths.two_fa_prompt_view_desc,
            "2fa_input": self.xpaths.two_fa_code_input_field,  # Generic EditText check
            "2fa_text": self.xpaths.two_fa_check_email_text_view,  # Check email text
            # Suspension indicator
            "suspended_smart": self.xpaths.account_suspended_text_smart,
        }

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for login success indicators first
            for name in [
                "save_login_view",
                "save_login_smart",
                "notifications_smart",
                "story_text",
                "story_button",
                "story_image",
            ]:
                xpath = checks.get(name)
                if xpath and self.interactions.element_exists(xpath):
                    self.logger.info(f"✅ Detected UI indicating Login Success: {name}")
                    return "login_success"

            # Check for 2FA indicators next
            for name in ["2fa_prompt", "2fa_input", "2fa_text"]:
                xpath = checks.get(name)
                if xpath and self.interactions.element_exists(xpath):
                    self.logger.info(f"✅ Detected UI indicating 2FA Required: {name}")
                    return "2fa_required"

            # Check for suspension indicator last
            xpath_suspended = checks.get("suspended_smart")
            if xpath_suspended and self.interactions.element_exists(xpath_suspended):
                self.logger.warning(
                    f"🚫 Detected UI indicating Account Suspended: suspended_smart"
                )
                return "account_suspended"

            # Wait before next poll cycle
            time.sleep(1.0)

        self.logger.error(
            f"⏰ Timeout ({timeout}s): No known post-login state detected."
        )
        # Consider taking a screenshot here for debugging unknown states
        # self.d.screenshot("unknown_post_login_state.png")
        return "unknown"

    def _update_airtable_status(self, status_map: dict):
        """Helper to update Airtable if client and record_id are available."""
        if self.airtable_client and self.record_id:
            self.logger.info(
                f"📡 Updating Airtable record {self.record_id}: {status_map}"
            )
            # Ensure Airtable client context is correct if needed
            if self.base_id:
                self.airtable_client.base_id = self.base_id
            if self.table_id:
                self.airtable_client.table_id = self.table_id

            success = self.airtable_client.update_record_fields(
                self.record_id, status_map
            )
            if success:
                self.logger.info(f"✅ Airtable update successful: {status_map}")
            else:
                self.logger.error(
                    f"❌ Airtable update failed for record {self.record_id}."
                )
        else:
            self.logger.debug(
                "Airtable client or record_id not provided, skipping status update."
            )

    def execute_login(self, username, password) -> str:
        """
        Performs the Instagram login sequence using username and password.

        Args:
            username (str): Instagram username.
            password (str): Instagram password.

        Returns:
            str: Status of the login attempt:
                 - "login_success"
                 - "2fa_required"
                 - "login_failed" (e.g., incorrect password)
                 - "account_banned"
                 - "timeout_or_unknown"
                 - "error" (for unexpected exceptions during the process)
        """
        try:
            self.logger.info(f"--- Starting Instagram Login for: {username} ---")

            # Basic check: Ensure Instagram app is in foreground
            current_app = self.d.app_current()
            if self.package_name not in current_app.get("package", ""):
                self.logger.error(
                    f"Instagram app ({self.package_name}) not in foreground. Current app: {current_app.get('package')}"
                )
                # Try to open the app? Or just fail? Failing is safer here.
                # self.interactions.open_app() # Requires readiness XPath for login screen
                raise Exception(
                    f"Instagram app ({self.package_name}) not currently running or in foreground."
                )

            self.logger.info("Waiting for login screen UI to stabilize...")
            time.sleep(3)  # Keep the stabilization wait

            # --- Step 1: Check field labels (Optional, for logging/debugging) ---
            if not self.interactions.element_exists(
                self.xpaths.login_username_label_smart
            ):
                self.logger.warning("⚠️ Username label (smart search) not found.")
            if not self.interactions.element_exists(
                self.xpaths.login_password_label_smart
            ):
                self.logger.warning("⚠️ Password label (smart search) not found.")

            # --- Step 2: Locate input fields (Using generic XPath + indexing) ---
            self.logger.debug(
                "Locating username and password fields using generic XPath..."
            )
            # Need direct d.xpath().all() as interactions layer doesn't have find_all
            edit_fields = self.d.xpath(self.xpaths.login_edittext_field_generic).all()

            if len(edit_fields) < 2:
                self.logger.error(
                    "❌ Not enough EditText fields found on screen. Cannot proceed."
                )
                # Take screenshot?
                # self.d.screenshot("login_fields_not_found.png")
                return "error"  # Or a more specific state like "ui_error"

            # Assuming first is username, second is password based on original logic
            username_field_element = edit_fields[0]
            password_field_element = edit_fields[1]
            self.logger.info("✅ Located generic username and password fields.")

            # --- Step 3: Type username ---
            self.logger.info("Entering username...")
            try:
                username_field_element.click()  # Direct click on the found element
                time.sleep(0.5)
                self.d.clear_text()  # Clear field before typing
                time.sleep(0.3)
                self.typer.type_text(username)
                time.sleep(1)
                # Optional verification: Check if text matches
                entered_user = username_field_element.get_text()
                if entered_user != username:
                    self.logger.warning(
                        f"Username verification mismatch. Expected '{username}', got '{entered_user}'. Continuing..."
                    )

            except Exception as e:
                self.logger.error(
                    f"❌ Error interacting with username field: {e}", exc_info=True
                )
                return "error"

            # --- Step 4: Type password ---
            self.logger.info("Entering password...")
            try:
                password_field_element.click()  # Direct click
                time.sleep(0.5)
                self.d.clear_text()  # Clear field
                time.sleep(0.3)
                self.typer.type_text(password)
                time.sleep(1)  # Wait after typing password
            except Exception as e:
                self.logger.error(
                    f"❌ Error interacting with password field: {e}", exc_info=True
                )
                return "error"

            # --- Step 5: Show password (Optional, helps with debugging) ---
            # Use click_if_exists for safety
            if self.interactions.click_if_exists(
                self.xpaths.login_show_password_button, timeout=2
            ):
                self.logger.info("Clicked 'Show password' button.")
                time.sleep(0.5)
                # Optional: Log the visible password for debugging (use cautiously)
                # visible_pw = password_field_element.get_text()
                # self.logger.debug(f"Visible password text: {visible_pw}")
            else:
                self.logger.warning("'Show password' button not found or click failed.")

            # --- Step 6: Click Login button ---
            self.logger.info("Clicking 'Log in' button...")
            if not self.interactions.click_by_xpath(
                self.xpaths.login_button, timeout=5
            ):
                self.logger.error("❌ 'Log in' button not found or click failed.")
                # Take screenshot?
                # self.d.screenshot("login_button_fail.png")
                return "error"  # Or "ui_error"

            # --- Step 7: Post-login checks ---
            self.logger.info("Login submitted, entering post-login checks...")

            # 7.1: Check for "Incorrect Password" immediately (Fast fail)
            incorrect_pw_xpath = self.xpaths.login_incorrect_password_text_view
            ok_button_xpath = self.xpaths.login_incorrect_password_ok_button
            # Brief check for the error message
            if self.interactions.wait_for_element_appear(incorrect_pw_xpath, timeout=5):
                self.logger.warning("❌ Incorrect Password error detected!")
                # Try to click OK to dismiss
                if self.interactions.click_if_exists(ok_button_xpath, timeout=3):
                    self.logger.info("Clicked 'OK' on incorrect password dialog.")
                else:
                    self.logger.warning(
                        "Could not click 'OK' on incorrect password dialog."
                    )
                self._update_airtable_status({"Status": "Login Failed - Incorrect PW"})
                return "login_failed"

            # 7.2: Handle "Save your login info?" prompt explicitly (High priority success indicator)
            save_prompt_xpath = (
                self.xpaths.save_login_info_prompt_view
            )  # Using view desc
            save_button_xpath = self.xpaths.save_login_info_save_button
            self.logger.info(
                "Checking explicitly for 'Save your login info?' screen..."
            )
            # Wait longer for this specific prompt as it confirms successful login credentials
            if self.interactions.wait_for_element_appear(save_prompt_xpath, timeout=15):
                self.logger.info("✅ 'Save your login info?' prompt detected.")
                if self.interactions.click_if_exists(save_button_xpath, timeout=3):
                    self.logger.info("✅ Clicked 'Save' button.")
                else:
                    self.logger.warning(
                        "⚠️ Found 'Save prompt' but 'Save' button click failed."
                    )
                    # Still counts as login success, just didn't save prompt

                self._update_airtable_status(
                    {"Logged In?": True, "Status": "Logged In - Active"}
                )
                return "login_success"
            else:
                self.logger.info(
                    "'Save your login info?' screen not detected explicitly, proceeding to general detection."
                )

            # 7.3: Fallback to general post-login state detection
            # Use a reasonable timeout for the general detection phase
            final_state = self.detect_post_login_state(username=username, timeout=25)

            # --- Step 8: Handle final state and update Airtable ---
            if final_state == "login_success":
                self.logger.info(
                    "✅ Login successful (detected via general UI indicators)."
                )
                self._update_airtable_status(
                    {"Logged In?": True, "Status": "Logged In - Active"}
                )
                return "login_success"
            elif final_state == "2fa_required":
                self.logger.info("🔑 2FA Required.")
                # Don't update "Logged In?" yet, but maybe update status
                self._update_airtable_status({"Status": "Login OK - 2FA Required"})
                return "2fa_required"
            elif final_state == "account_suspended":
                self.logger.warning("🚫 Account Suspended.")
                self._update_airtable_status({"Status": "Banned"})
                # Close the app maybe? handled by watcher usually
                # self.interactions.close_app()
                return "account_banned"
            else:  # Handles "unknown"
                self.logger.error(
                    "❌ Login failed: Timeout or Unknown post-login state."
                )
                self._update_airtable_status({"Status": "Login Failed - Unknown State"})
                # Take screenshot on unknown state
                self.d.screenshot("unknown_final_login_state.png")
                return "timeout_or_unknown"

        except Exception as e:
            self.logger.error(
                f"💥 Unexpected Error during Instagram login process: {e}",
                exc_info=True,
            )
            # Maybe update Airtable with error status?
            self._update_airtable_status({"Status": f"Login Error: {type(e).__name__}"})
            return "error"


# --- Example Usage (if needed for standalone testing) ---
if __name__ == "__main__":
    module_logger.info("--- Running Instagram Login Handler Standalone Test ---")

    # --- Configuration ---
    # !! Replace with your actual test details !!
    TEST_USERNAME = "your_test_username"
    TEST_PASSWORD = "your_test_password"
    INSTAGRAM_PACKAGE_NAME = "com.instagram.android"  # Or your clone package name

    # Optional: Airtable details for testing status updates
    TEST_AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")  # Replace or getenv
    TEST_AIRTABLE_TABLE_ID = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")  # Replace or getenv
    TEST_AIRTABLE_RECORD_ID = "recXXXXXXXXXXXXXX"  # Find a test record ID

    airtable_client = None
    if TEST_AIRTABLE_BASE_ID and TEST_AIRTABLE_TABLE_ID and TEST_AIRTABLE_RECORD_ID:
        module_logger.info(
            "Airtable details provided, setting up client for status updates."
        )
        airtable_client = AirtableClient()  # Assumes API key is in env
    else:
        module_logger.warning(
            "Airtable details not fully provided, status updates will be skipped."
        )

    # --- Initialization ---
    try:
        module_logger.info("Connecting to device...")
        d = u2.connect()
        module_logger.info(f"Connected: {d.serial}")

        module_logger.info(
            f"Ensuring Instagram app ({INSTAGRAM_PACKAGE_NAME}) is running..."
        )
        d.app_start(INSTAGRAM_PACKAGE_NAME, stop=True)  # Start fresh
        time.sleep(5)  # Wait for app to load

        # Initialize components
        interactions = InstagramInteractions(
            device=d, app_package=INSTAGRAM_PACKAGE_NAME
        )
        xpaths = InstagramXPaths(package_name=INSTAGRAM_PACKAGE_NAME)
        typer = StealthTyper(device_id=d.serial)

        # Initialize the handler
        login_handler = InstagramLoginHandler(
            device=d,
            interactions=interactions,
            xpaths=xpaths,
            stealth_typer=typer,
            airtable_client=airtable_client,
            record_id=TEST_AIRTABLE_RECORD_ID,
            base_id=TEST_AIRTABLE_BASE_ID,
            table_id=TEST_AIRTABLE_TABLE_ID,
        )

        # --- Execute Login ---
        login_result = login_handler.execute_login(TEST_USERNAME, TEST_PASSWORD)

        module_logger.info(f"--- Login Process Finished ---")
        module_logger.info(f"Final Login Status: {login_result}")
        module_logger.info("Check the device screen for the final state.")

    except Exception as e:
        module_logger.error(f"💥 Standalone test failed: {e}", exc_info=True)

    finally:
        module_logger.info("--- Test Complete ---")
