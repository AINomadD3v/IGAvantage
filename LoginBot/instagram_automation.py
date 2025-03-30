#instagram_automation.py

import time
import uiautomator2 as u2
from Shared.logger_config import setup_logger
from Shared.stealth_typing import StealthTyper
from get_code import UIHelper

logger = setup_logger(__name__)


class InstagramAutomation:
    def __init__(self, device, package_name):
        self.d = device
        self.package_name = package_name
        self.typer = StealthTyper(device_id=self.d.serial)
        self.logger = setup_logger(self.__class__.__name__)
        self.helper = UIHelper(self.d)

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

    #TODO Update name to reflect now using xpath
    def login_with_ocr(self, username, password):
        try:
            self.logger.info("Starting Instagram login process via XPath (smart search)")

            current_app = self.d.app_current()
            if "instagram" not in current_app['package']:
                raise Exception("Instagram app not currently running")

            time.sleep(3)  # Allow UI to stabilize

            # --- Step 1: Sanity check field labels via smart XPath ---
            username_label_xpath = '^Username, email or mobile number'
            password_label_xpath = '^Password'

            if not self.d.xpath(username_label_xpath).exists:
                self.logger.warning("⚠️ Username label not found with smart XPath")

            if not self.d.xpath(password_label_xpath).exists:
                self.logger.warning("⚠️ Password label not found with smart XPath")

            # --- Step 2: Find EditText fields ---
            edit_fields = self.d.xpath('//android.widget.EditText').all()

            if len(edit_fields) < 2:
                self.logger.error("❌ Not enough EditText fields found for login form")
                return False

            username_field = edit_fields[0]
            password_field = edit_fields[1]

            # --- Step 3: Enter username ---
            self.logger.info("Clicking and typing into username field")
            username_field.click()
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.5)
            self.typer.type_text(username)
            time.sleep(1)

            # --- Step 4: Enter password ---
            self.logger.info("Clicking and typing into password field")
            password_field.click()
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.5)
            self.typer.type_text(password)
            time.sleep(1)

            # --- Step 5: Click show-password icon (optional) ---
            show_pw_xpath = '//android.widget.Button[@content-desc="Show password"]'
            if self.d.xpath(show_pw_xpath).exists:
                self.logger.info("Clicking show password button via known XPath")
                self.d.xpath(show_pw_xpath).click()
                time.sleep(0.5)
            else:
                self.logger.warning("Show password button not found via XPath")


            # --- Step 6: Confirm password was entered by checking it exists in the UI ---
            password_match_xpath = f'//android.widget.EditText[@text="{password}"]'

            if self.d.xpath(password_match_xpath).exists:
                self.logger.info(f"✅ Password match confirmed via text XPath: {password}")
            else:
                self.logger.warning("⚠️ Password text not found in any EditText — proceed with caution")


            # --- Step 7: Click login button ---
            login_xpath = '//android.widget.Button[@content-desc="Log in"]'
            login_btn = self.d.xpath(login_xpath)
            if not login_btn.exists or not login_btn.click_exists(timeout=3):
                self.logger.error("Login button not found or not clickable")
                return False

            # --- Step 8: Post-login error or success detection ---
            self.logger.info("Login submitted, entering post-login check loop...")
            incorrect_password_xpath = '//android.widget.TextView[@text="Incorrect Password"]'
            check_email_xpath = '//android.view.View[@content-desc="Check your email"]'
            ok_button_xpath = '//android.widget.Button[@text="OK"]'

            start = time.time()
            while time.time() - start < 30:
                if self.d.xpath(incorrect_password_xpath).exists:
                    self.logger.warning("❌ Incorrect Password detected")
                    ok_button = self.d.xpath(ok_button_xpath)
                    if ok_button.exists and ok_button.click_exists(timeout=3):
                        self.logger.info("Clicked 'OK' to acknowledge incorrect password")
                    else:
                        self.logger.warning("'OK' button not found or not clickable")
                    return False

                if self.d.xpath(check_email_xpath).exists:
                    self.logger.info("✅ 2FA screen detected: 'Check your email'")
                    return True

                time.sleep(3)

            self.logger.error("⏰ Timeout: No 2FA screen or incorrect password message detected")
            return False

        except Exception as e:
            self.logger.error(f"Error during XPath login: {e}")
            return False



def handle_identity_reset_via_notification(d, timeout=10):
    try:
        logger.info("🔄 opening notification shade for identity reset...")
        d.open_notification()
        time.sleep(2)

        # wait for the unique notification text to appear
        identity_text_xpath = '//android.widget.textview[@resource-id="android:id/text" and @text="tap to quit the app and generate a new identity."]'
        container_xpath = '(//android.widget.framelayout[@resource-id="com.android.systemui:id/expandablenotificationrow"])[6]'

        start_time = time.time()
        while time.time() - start_time < timeout:
            if d.xpath(identity_text_xpath).exists:
                logger.info("✅ found 'new identity' notification text")
                container = d.xpath(container_xpath)
                if container.exists and container.click_exists(timeout=3):
                    logger.info("✅ clicked 'new identity' notification container")
                    return true
                else:
                    logger.warning("⚠️ container found but click failed")
            else:
                logger.debug("waiting for 'new identity' notification to appear...")
                time.sleep(1)

        logger.error("❌ timeout: 'new identity' notification not found or not clickable")
        return false

    except exception as e:
        logger.error(f"exception while handling identity reset: {e}")
        return false

