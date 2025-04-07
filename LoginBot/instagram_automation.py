#instagram_automation.py

import time
import uiautomator2 as u2
from Shared.logger_config import setup_logger
from Shared.stealth_typing import StealthTyper
from Shared.airtable_manager import AirtableClient
from .get_code import UIHelper

logger = setup_logger(__name__)


class InstagramAutomation:
    def __init__(self, device, package_name, airtable_client=None, record_id=None):
        self.d = device
        self.package_name = package_name
        self.typer = StealthTyper(device_id=self.d.serial)
        self.logger = setup_logger(self.__class__.__name__)
        self.helper = UIHelper(self.d)
        self.airtable_client = airtable_client
        self.record_id = record_id


    def wait_for_2fa_screen(self, timeout=30):
        """Wait for the 2FA screen to appear after login is submitted."""
        self.logger.info("Waiting for 2FA screen (e.g., 'Check your email')...")
        xpath = '//android.widget.TextView[contains(@text, "check your email")]'  # adjust if needed

        start = time.time()
        while time.time() - start < timeout:
            if self.d.xpath(xpath).exists:
                self.logger.info("Detected 2FA screen")
                return True
            time.sleep(1)

        self.logger.error("2FA screen not detected within timeout")
        return False

    def detect_post_login_state(self, username: str, timeout: int = 30) -> str:
        """
        Determines what screen we landed on after submitting login credentials.
        Returns one of:
            - "2fa_required"
            - "login_success"
            - "account_suspended"
            - "unknown"

        Waits up to `timeout` seconds.
        """
        d = self.d
        helper = self.helper
        logger = self.logger

        logger.info("🔍 Detecting post-login state...")

        # Common post-login XPath indicators
        checks = {
            "2fa_prompt": '//android.view.View[@content-desc="Check your email"]',
            "2fa_input": '//android.widget.EditText',

            "save_login": '^Save your login info%',
            "notifications": '%Turn on notifications%',
            "story_1": '//android.widget.TextView[@text="Your story"]',
            "story_2": f'//android.widget.Button[contains(@content-desc, "{username}\'s story")]',
            "story_3": f'//android.widget.ImageView[contains(@content-desc, "{username}\'s story")]',

            "suspended": '%We suspended your account%',
        }

        start = time.time()
        while time.time() - start < timeout:
            for name, xpath in checks.items():
                if d.xpath(xpath).exists:
                    logger.info(f"✅ Detected UI: {name}")

                    # 👇 PRIORITIZE login_success BEFORE 2fa
                    if name.startswith("story") or name in ("save_login", "notifications"):
                        return "login_success"
                    if name.startswith("2fa"):
                        return "2fa_required"
                    if name == "suspended":
                        return "account_suspended"

            time.sleep(1)

        logger.error("⏰ Timeout: No known post-login state detected")
        return "unknown"

    def ig_login(self, username, password):
        try:
            self.logger.info("Starting Instagram login process via XPath (smart search)")

            current_app = self.d.app_current()
            if "instagram" not in current_app['package']:
                raise Exception("Instagram app not currently running")

            time.sleep(3)  # Allow UI to stabilize

            # --- Step 1: Check field labels ---
            if not self.d.xpath('^Username, email or mobile number').exists:
                self.logger.warning("⚠️ Username label not found")
            if not self.d.xpath('^Password').exists:
                self.logger.warning("⚠️ Password label not found")

            # --- Step 2: Locate input fields ---
            edit_fields = self.d.xpath('//android.widget.EditText').all()
            if len(edit_fields) < 2:
                self.logger.error("❌ Not enough EditText fields found")
                return False

            username_field = edit_fields[0]
            password_field = edit_fields[1]

            # --- Step 3: Type username ---
            self.logger.info("Clicking and typing into username field")
            username_field.click()
            time.sleep(0.5)
            self.typer.type_text(username)
            time.sleep(1)

            # --- Step 4: Type password ---
            self.logger.info("Clicking and typing into password field")
            password_field.click()
            time.sleep(0.5)
            self.typer.type_text(password)

            time.sleep(0.5)
            time.sleep(1)

            # --- Step 5: Show password (optional) ---
            show_pw_xpath = '//android.widget.Button[@content-desc="Show password"]'
            if self.d.xpath(show_pw_xpath).exists:
                self.logger.info("Clicking show password button")
                self.d.xpath(show_pw_xpath).click()
                time.sleep(0.5)
            else:
                self.logger.warning("Show password button not found")

            # --- Step 6: Confirm password match (optional sanity check) ---
            match_xpath = f'//android.widget.EditText[@text="{password}"]'
            if self.d.xpath(match_xpath).exists:
                self.logger.info(f"✅ Password match confirmed: {password}")
            else:
                self.logger.warning("⚠️ Password match not found")

            # --- Step 7: Click Login button ---
            login_xpath = '//android.widget.Button[@content-desc="Log in"]'
            if not self.d.xpath(login_xpath).click_exists(timeout=3):
                self.logger.error("❌ Login button not found or click failed")
                return False

            # --- Step 8: Post-login checks ---
            self.logger.info("Login submitted, entering post-login check loop...")

            # 8.1: Fast-fail incorrect password
            incorrect_pw_xpath = '//android.widget.TextView[@text="Incorrect Password"]'
            for _ in range(5):
                if self.d.xpath(incorrect_pw_xpath).exists:
                    self.logger.warning("❌ Incorrect Password detected")
                    ok_btn = self.d.xpath('//android.widget.Button[@text="OK"]')
                    if ok_btn.exists and ok_btn.click_exists(timeout=3):
                        self.logger.info("Clicked 'OK'")
                    return "login_failed"
                time.sleep(1)

            # 8.2: Handle "Save your login info?" prompt explicitly
            save_prompt_xpath = '//android.view.View[@content-desc="Save your login info?"]'
            save_button_xpath = '//android.widget.Button[@content-desc="Save"]'

            self.logger.info("Checking if 'Save your login info?' screen is present...")
            if self.d.xpath(save_prompt_xpath).wait(timeout=10):
                self.logger.info("✅ 'Save your login info?' prompt detected")
                if self.d.xpath(save_button_xpath).click_exists(timeout=3):
                    self.airtable_client.update_record_fields(self.record_id, {"Logged In?": True})

                    self.logger.info("✅ Clicked 'Save' button")
                else:
                    self.logger.warning("⚠️ 'Save' button click failed")

                # Update Airtable if context is available
                if hasattr(self, "airtable_client") and hasattr(self, "record_id"):
                    self.logger.info("📡 Updating Airtable: Logged In = True")
                    self.airtable_client.update_record_fields(self.record_id, {"Logged In?": True})

                return "login_success"

            # 8.3: Fallback to full post-login state detection
            state = self.detect_post_login_state(username)

            if state == "login_success":
                if hasattr(self, "airtable_client") and hasattr(self, "record_id"):
                    self.logger.info("📡 Updating Airtable: Logged In = True")
                    self.airtable_client.update_record_fields(self.record_id, {"Logged In?": True})
                return "login_success"
            elif state == "2fa_required":
                return "2fa_required"
            elif state == "account_suspended":
                return "account_banned"
            else:
                return "timeout_or_unknown"

        except Exception as e:
            self.logger.error(f"Error during XPath login: {e}")
            return False
