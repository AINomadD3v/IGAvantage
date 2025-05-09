# get_code.py

import os
import re
import time
from pathlib import Path

import uiautomator2 as u2

from Shared.airtable_manager import AirtableClient
from Shared.logger_config import setup_logger
from Shared.popup_handler import PopupHandler
from Shared.stealth_typing import StealthTyper
from Shared.ui_helper import UIHelper

logger = setup_logger(__name__)

POPUP_CONFIG_PATH = Path(__file__).resolve().parents[1] / "Shared" / "popup_config.json"


class FirefoxSession:
    def __init__(
        self, email: str, password: str, firefox_package: str = "org.mozilla.firefoy"
    ):
        self.email = email
        self.password = password
        self.firefox_package = firefox_package
        self.d = u2.connect()
        self.logger = setup_logger(self.__class__.__name__)
        self.helper = UIHelper(self.d)
        self.popup_handler = PopupHandler(
            self.d, helper=self.helper, config_path=str(POPUP_CONFIG_PATH)
        )
        self.popup_handler.register_watchers()

    def start(self, url: str = "op.pl") -> bool:
        return all(
            [
                self._launch_firefox(),
                self._navigate_to_url(url),
                self._perform_login_sequence(),
            ]
        )

    def _launch_firefox(self) -> bool:
        try:
            self.logger.info("Launching Firefox...")
            self.d.app_start(self.firefox_package)
            time.sleep(3)
            self.popup_handler.handle_all_popups()

            smart_xpath = "^Search or enter address"
            fallback_xpath = (
                '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'
            )

            for _ in range(10):
                if self.d.xpath(smart_xpath).exists:
                    self.logger.info("✅ Found smart URL bar")
                    self.d.xpath(smart_xpath).click()
                    return True
                if self.d.xpath(fallback_xpath).exists:
                    self.logger.info("✅ Found fallback URL bar")
                    self.d.xpath(fallback_xpath).click()
                    return True
                time.sleep(1)

            self.logger.error("❌ Could not find Firefox URL bar")
            return False
        except Exception as e:
            self.logger.error(f"Error launching Firefox: {e}")
            return False

    def _navigate_to_url(self, url: str) -> bool:
        try:
            full_url = f"https://www.{url}" if not url.startswith("http") else url
            self.logger.info(f"Navigating to {full_url}")
            typer = StealthTyper(device_id=self.d.serial)
            xpath = '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'

            if not self.helper.wait_for_xpath(xpath, timeout=5):
                return False
            if not self.d.xpath(xpath).click_exists(timeout=3):
                return False

            input_box = self.d.xpath(xpath)

            for _ in range(2):
                self.d.clear_text()
                time.sleep(0.3)
                typer.type_text(full_url)
                time.sleep(1)
                if full_url in (input_box.get_text() or ""):
                    break
            else:
                return False

            typer.press_enter()
            time.sleep(5)
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to URL: {e}")
            return False


class EmailLogin:
    def __init__(self, email, password, firefox_package="org.mozilla.firefoy"):
        self.email = email
        self.password = password
        self.d = u2.connect()
        self.helper = UIHelper(self.d)
        self.popup_handler = PopupHandler(
            self.d, helper=self.helper, config_path=str(POPUP_CONFIG_PATH)
        )
        self.popup_handler.register_watchers()
        self.firefox_package = firefox_package
        self.logger = setup_logger(self.__class__.__name__)
        self.email_entered = False

    def handle_email_input(self):
        logger = self.logger
        email_xpath = '//android.widget.EditText[@resource-id="email"]'
        password_xpath = '//android.widget.EditText[@resource-id="password"]'
        typer = StealthTyper(device_id=self.d.serial)

        if self.email_entered:
            logger.info("📧 Email already entered, skipping")
            return True

        for attempt in range(3):
            logger.info(f"📧 Email entry attempt {attempt + 1}/3")

            # Step 1: Wait for email field to appear
            if not self.helper.wait_for_xpath(email_xpath, timeout=10):
                logger.error("Email input field not found")
                return False

            logger.info("🕒 Email field found — waiting before popup check...")
            time.sleep(5)

            # Step 2: Run cookie popup handler BEFORE interacting with email field
            self.logger.info("📋 Running cookie popup handler before email entry")
            self.popup_handler.handle_cookie_popup()

            # Step 3: Wait again to let any popup interaction settle
            time.sleep(1)

            # Step 4: Locate and click email field
            field = self.d.xpath(email_xpath)
            if not field.click_exists(timeout=2):
                logger.error("❌ Failed to click email field")
                return False

            self.d.clear_text()
            typer.type_text(self.email)

            # Step 5: Verify email was typed correctly
            for _ in range(3):
                entered = field.get_text() or ""
                if self.email in entered:
                    logger.info(f"✅ Email entered: {entered}")
                    break
                time.sleep(0.5)
            else:
                logger.warning(f"❌ Email mismatch: {entered}")
                continue

            # Step 6: Click "NEXT" button
            if not self.helper.smart_button_clicker(
                "NEXT", fallback_xpath='//android.widget.Button[@text="NEXT"]'
            ):
                logger.error("❌ Failed to click NEXT")
                return False

            # Step 7: Wait for password field to appear
            if not self.helper.wait_for_xpath(password_xpath, timeout=8):
                logger.warning("NEXT clicked, but password field didn't appear")
                return False

            logger.info("✅ Email flow complete")
            self.email_entered = True
            return True

        logger.error("❌ Email input failed after retries")
        return False

    def handle_password_input(self):
        logger = self.logger
        password_xpath = '//android.widget.EditText[@resource-id="password"]'
        typer = StealthTyper(device_id=self.d.serial)

        for attempt in range(3):
            logger.info(f"🔑 Password entry attempt {attempt + 1}/3")

            if not self.helper.wait_for_xpath(password_xpath, timeout=10):
                logger.error("Password input field not found")
                return False

            field = self.d.xpath(password_xpath)
            if not field.click_exists(timeout=2):
                logger.error("Failed to click password field")
                return False

            self.d.clear_text()
            typer.type_text(self.password)
            time.sleep(0.5)

            # 🔁 IMMEDIATE show-password button click, BEFORE checking text
            if not self.helper.click_show_password_icon(password_xpath):
                logger.error(
                    "❌ Could not click show-password icon — can't verify password"
                )
                return False

            visible_pw = field.get_text() or ""
            logger.info(f"👁️ Visible field text: '{visible_pw}'")

            if visible_pw == self.password:
                logger.info("✅ Password match confirmed")
                if not self.helper.smart_button_clicker(
                    "LOG IN", fallback_xpath='//android.widget.Button[@text="LOG IN"]'
                ):
                    logger.error("❌ Failed to click LOG IN")
                    return False
                logger.info("✅ Password submitted")
                time.sleep(2)
                return "submitted"
            else:
                logger.warning("❌ Password mismatch — retrying")
                self.d.clear_text()
                time.sleep(1)

        logger.error("❌ Password entry failed after retries")
        return False

    def handle_post_login_flow(self):
        logger = self.logger
        d = self.d

        logger.info("▶️ Starting post-login handling")

        logger.info("⏳ Verifying inbox UI up to 30s post-login")
        email_nav = EmailNavigation(
            driver=d, helper=self.helper, popup_handler=self.popup_handler
        )

        start = time.time()
        while time.time() - start < 30:
            if email_nav.verify_logged_in():
                logger.info("✅ Final login verification passed")
                return True
            time.sleep(2)

        logger.error("❌ Login failed: final inbox not reached")
        return False

    def perform_full_login(self):
        self.logger.info("🔐 Starting full email login flow...")

        # ✅ Step 0: Start Firefox and navigate to op.pl
        self.logger.info("🌐 Launching Firefox and navigating to op.pl")

        try:
            self.d.app_start(self.firefox_package)
            time.sleep(3)
            self.popup_handler.handle_all_popups()

            smart_xpath = "^Search or enter address"
            fallback_xpath = (
                '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'
            )

            for _ in range(10):
                if self.d.xpath(smart_xpath).exists:
                    self.logger.info("✅ Found smart URL bar")
                    self.d.xpath(smart_xpath).click()
                    break
                elif self.d.xpath(fallback_xpath).exists:
                    self.logger.info("✅ Found fallback URL bar")
                    self.d.xpath(fallback_xpath).click()
                    break
                time.sleep(1)
            else:
                self.logger.error("❌ Could not find Firefox URL bar")
                return False

            typer = StealthTyper(device_id=self.d.serial)
            url_xpath = (
                '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'
            )

            if not self.d.xpath(url_xpath).click_exists(timeout=3):
                self.logger.error("❌ Could not click on URL input box")
                return False

            self.d.clear_text()
            time.sleep(0.3)
            typer.type_text("https://www.op.pl")
            typer.press_enter()
            time.sleep(5)

        except Exception as e:
            self.logger.error(f"❌ Failed to launch and navigate Firefox: {e}")
            return False

        # ✅ Proceed with login
        if not self.handle_email_input():
            return False
        self.handle_password_input()
        return self.handle_post_login_flow()


class EmailNavigation:
    def __init__(self, driver, helper, popup_handler):
        self.d = driver
        self.helper = helper
        self.popup_handler = popup_handler
        self.logger = setup_logger(self.__class__.__name__)

    def verify_logged_in(self):
        try:
            self.logger.info("Verifying login status...")
            main_container_xpath = "^React_MainContainer"  # Smart search by resource-id

            if self.d.xpath(main_container_xpath).exists:
                self.logger.info("✅ Main container found - successfully logged in")
                return True

            self.logger.warning("Main container not found - login might have failed")
            return False

        except Exception as e:
            self.logger.error(f"Error verifying login status: {e}")
            return False

    def find_code_in_main_container(self):
        """
        Attempt to extract Instagram 2FA code:
        - First try preview list (React_MainContainer)
        - If not found, open the Instagram email and extract from full email body
        """
        try:
            self.logger.info(
                "🔍 Scanning React_MainContainer for Instagram 2FA email blocks..."
            )

            container_xpath = '//android.view.View[@resource-id="React_MainContainer"]'
            block_xpath = (
                container_xpath
                + '//android.view.View[.//android.view.View[@text="Instagram"] and .//android.view.View[@text="Verify your account"]]'
            )

            blocks = self.d.xpath(block_xpath).all()
            self.logger.info(
                f"📦 Found {len(blocks)} candidate blocks inside main container"
            )

            for block in blocks:
                try:
                    children = self.d.xpath(
                        block.get_xpath() + "/android.view.View"
                    ).all()
                    for child in children:
                        text = child.attrib.get("text", "") or ""
                        match = re.search(r"\b(\d{6})\b", text)
                        if match:
                            code = match.group(1)
                            self.logger.info(f"✅ Found 2FA code in preview: {code}")
                            return code
                except Exception as e:
                    self.logger.warning(f"⚠️ Error reading preview block: {e}")
                    continue

            self.logger.info("❌ No 2FA code found in preview — opening full email")
            return self._open_email_and_extract_code()

        except Exception as e:
            self.logger.error(f"💥 Error in find_code_in_main_container: {e}")
            return None

    def _open_email_and_extract_code(self):
        try:
            self.logger.info("🔓 Attempting to open Instagram email for full view")

            # Smart match for the Instagram email in the inbox list
            email_xpath = '//android.view.View[@text="Instagram"]'

            if not self.d.xpath(email_xpath).wait(timeout=5):
                self.logger.error("❌ Instagram email entry not found")
                return None

            email_block = self.d.xpath(email_xpath).get()
            clickable_wrapper_xpath = (
                email_block.get_xpath() + "/../.."
            )  # go up to Button container

            if not self.d.xpath(clickable_wrapper_xpath).click_exists(timeout=3):
                self.logger.error("❌ Failed to click Instagram email block")
                return None

            self.logger.info("✅ Clicked Instagram email — waiting for content")
            time.sleep(2)

            # Smart match: find a 6-digit number
            code_xpath = '//android.view.View[string-length(@text)=6 and translate(@text, "0123456789", "") = ""]'

            if not self.d.xpath(code_xpath).wait(timeout=10):
                self.logger.error("❌ Code element not found in opened email")
                return None

            for el in self.d.xpath(code_xpath).all():
                text = el.attrib.get("text", "")
                if text.isdigit() and len(text) == 6:
                    self.logger.info(f"✅ Found 2FA code in full email: {text}")
                    return text

            self.logger.warning("❌ No matching code found in opened email")
            return None

        except Exception as e:
            self.logger.error(f"💥 Error while extracting code from opened email: {e}")
            return None

    def open_sidebar(self):
        try:
            self.logger.info("Attempting to open sidebar...")
            sidebar_btn_xpath = '//android.widget.Button[@resource-id="sidebar-btn"]'

            if not self.d.xpath(sidebar_btn_xpath).wait(timeout=10):
                self.logger.warning("Sidebar button not found")
                return False

            # Click the sidebar button
            if not self.d.xpath(sidebar_btn_xpath).click_exists(timeout=3):
                self.logger.error("Failed to click sidebar button")
                return False

            self.logger.info("Successfully clicked sidebar button")
            return True

        except Exception as e:
            self.logger.error("Error opening sidebar: %s", e)
            return False

    def verify_sidebar_open(self):
        try:
            self.logger.info("Verifying sidebar is open...")
            write_msg_xpath = '//android.widget.Button[@text="Napisz wiadomość"]'

            if not self.d.xpath(write_msg_xpath).wait(timeout=10):
                self.logger.error(
                    "Write message button not found - sidebar might not be open"
                )
                return False

            self.logger.info("Write message button found - sidebar is open")
            return True

        except Exception as e:
            self.logger.error("Error verifying sidebar: %s", e)
            return False

    def navigate_to_communities(self):
        try:
            self.logger.info("Navigating to Communities section...")

            # Using a more flexible XPath that looks for View elements containing the text
            communities_xpath = '//android.view.View[contains(@text, "Społeczności")]'
            self.logger.info(
                "Searching for Communities button using xpath: %s", communities_xpath
            )

            # Wait for the element to be present
            if not self.d.xpath(communities_xpath).wait(timeout=10):
                self.logger.error("Communities button not found")
                return False

            # Click the element
            if self.d.xpath(communities_xpath).click_exists(timeout=3):
                self.logger.info("Successfully clicked Communities button")
                return True

            self.logger.error("Failed to click Communities button")
            return False

        except Exception as e:
            self.logger.error("Error navigating to Communities: %s", e)
            return False

    def perform_email_navigation(self):
        try:
            self.logger.info("🔁 Trying Communities tab first for 2FA code...")

            # Step 1: Open sidebar
            time.sleep(3)
            if not self.open_sidebar():
                self.logger.error("❌ Failed to open sidebar")
                return None

            time.sleep(1.5)

            # Step 2: Confirm sidebar opened
            for attempt in range(2):
                if self.verify_sidebar_open():
                    break
                self.logger.warning(f"Sidebar not open, retrying ({attempt+1}/2)...")
                self.open_sidebar()
                time.sleep(1.5)
            else:
                self.logger.error("❌ Sidebar failed to open after retries")
                return None

            # Step 3: Navigate to Communities tab
            if not self.navigate_to_communities():
                self.logger.error("❌ Failed to navigate to Communities tab")
                return None

            self.logger.info("✅ Clicked Communities tab — waiting for view to load...")
            time.sleep(2)

            # Step 4: Search for 2FA email in community tab
            smart_xpath = "^Hi "
            matches = self.d.xpath(smart_xpath).all()
            self.logger.info(f"📥 Found {len(matches)} candidate email blocks")

            for email_element in matches:
                full_text = email_element.attrib.get("text", "")
                if "tried to log in to your Instagram account" in full_text:
                    self.logger.info(f"📩 Matched 2FA email: {full_text[:100]}...")

                    # Try to extract 6-digit code from the preview
                    match = re.search(r"\b(\d{6})\b", full_text)
                    if match:
                        code = match.group(1)
                        self.logger.info(
                            f"✅ Extracted 2FA code from Communities tab: {code}"
                        )
                        return code
                    else:
                        self.logger.warning(
                            "No 6-digit code found in matched email — opening email to extract"
                        )

                        try:
                            # Go up to clickable wrapper for this email
                            email_xpath = email_element.get_xpath()
                            wrapper_xpath = email_xpath + "/../.."

                            if not self.d.xpath(wrapper_xpath).click_exists(timeout=3):
                                self.logger.error(
                                    "❌ Failed to click matched email block"
                                )
                                return None

                            self.logger.info(
                                "✅ Clicked email block — waiting for full view to load"
                            )
                            time.sleep(2)

                            # Attempt to extract 6-digit code from opened email
                            code_xpath = '//android.view.View[string-length(@text)=6 and translate(@text, "0123456789", "") = ""]'

                            if not self.d.xpath(code_xpath).wait(timeout=10):
                                self.logger.error(
                                    "❌ Code element not found in opened email"
                                )
                                return None

                            for el in self.d.xpath(code_xpath).all():
                                text = el.attrib.get("text", "")
                                if text.isdigit() and len(text) == 6:
                                    self.logger.info(
                                        f"✅ Found 2FA code in full email: {text}"
                                    )
                                    return text

                            self.logger.warning(
                                "❌ No matching 2FA code found in opened email"
                            )
                            return None

                        except Exception as e:
                            self.logger.error(
                                f"💥 Exception during fallback email open: {e}"
                            )
                            return None

            # If no matches found at all
            self.logger.warning(
                "❌ No 2FA code found in Communities tab — pressing back and falling back to main container"
            )
            self.d.press("back")
            time.sleep(2)
            self.logger.info(
                "✅ Logged in — trying to extract code from main container"
            )

            # Step 6: Try main container extraction
            code = self.find_code_in_main_container()
            if code:
                self.logger.info(f"✅ 2FA code retrieved from main container: {code}")
                return code
            else:
                self.logger.error("❌ No 2FA code found in main container fallback")
                return None

        except Exception as e:
            self.logger.error(f"💥 Error in email navigation sequence: {e}")
            return None

    def logout_of_email(self):
        try:
            self.logger.info("🚪 Attempting to log out of email...")

            # Click on profile/avatar or menu (adjust XPath based on actual site)
            menu_xpath = '//android.widget.Button[@text="Menu użytkownika"]'
            if self.helper.wait_for_xpath(menu_xpath, timeout=10):
                if self.d.xpath(menu_xpath).click_exists(timeout=3):
                    self.logger.info("✅ Opened account menu")

                    logout_xpath = '//android.view.View[contains(@text, "Wyloguj") or contains(@content-desc, "Sign out")]'
                    if self.helper.wait_for_xpath(logout_xpath, timeout=5):
                        if self.d.xpath(logout_xpath).click_exists(timeout=3):
                            self.logger.info("✅ Clicked logout")
                            time.sleep(2)
                            return True
                    else:
                        self.logger.warning("⚠️ Logout button not found in menu")
                else:
                    self.logger.warning("⚠️ Failed to open account menu")
            else:
                self.logger.warning("⚠️ Account menu not found")
            return False

        except Exception as e:
            self.logger.error(f"💥 Error logging out of email: {e}")
            return False

    def open_new_tab(self):
        try:
            self.logger.info("🆕 Attempting to open a new tab in Firefox...")

            # XPath for "Tabs" button
            tab_btn_xpath = '//android.widget.ImageView[@content-desc="Tabs"]'
            if self.helper.wait_for_xpath(tab_btn_xpath, timeout=5):
                if self.d.xpath(tab_btn_xpath).click_exists(timeout=3):
                    self.logger.info("✅ Clicked Tabs button")
                    time.sleep(1)

                    # XPath for "New tab"
                    new_tab_xpath = (
                        '//android.widget.TextView[contains(@text, "New tab")]'
                    )
                    if self.d.xpath(new_tab_xpath).click_exists(timeout=3):
                        self.logger.info("✅ Opened new tab")
                        time.sleep(1)
                        return True
            self.logger.warning("⚠️ Failed to open new tab")
            return False
        except Exception as e:
            self.logger.error(f"💥 Error opening new tab: {e}")
            return False


class TwoFactorTokenRetriever:
    def __init__(self, driver, helper, logger, firefox_package, popup_handler):
        self.d = driver
        self.helper = helper
        self.logger = logger
        self.firefox_package = firefox_package
        self.popup_handler = popup_handler
        self.is_logged_in = False

    def find_and_verify_instagram_email(self):
        try:
            self.logger.info("Searching for top Instagram verification email...")

            # Target the top email item specifically
            top_email_xpath = '//android.view.View[@resource-id="React_MainContainer"]/android.view.View[2]/android.view.View[2]/android.view.View[1]/android.view.View'

            if not self.d.xpath(top_email_xpath).exists:
                self.logger.error("Top email item not found")
                return False

            # Check if it contains both "Instagram" and "Verify your account"
            top_email_element = self.d.xpath(top_email_xpath)

            # Search inside that block for both expected text elements
            instagram_text_xpath = (
                f'{top_email_xpath}//android.view.View[@text="Instagram"]'
            )
            verify_text_xpath = (
                f'{top_email_xpath}//android.view.View[@text="Verify your account"]'
            )

            if (
                self.d.xpath(instagram_text_xpath).exists
                and self.d.xpath(verify_text_xpath).exists
            ):
                self.logger.info("Top email matches Instagram verification criteria")

                if top_email_element.click_exists(timeout=3):
                    self.logger.info("Clicked top Instagram verification email")
                    return True
                else:
                    self.logger.error("Failed to click top Instagram email")
                    return False
            else:
                self.logger.warning(
                    "Top email does not match Instagram verification content"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error finding top Instagram verification email: {e}")
            return False

    def wait_for_email_content(self, timeout=10):
        try:
            self.logger.info("Waiting for email content to load...")
            email_content_xpath = '//android.view.View[@resource-id="email_content"]/android.widget.GridView/android.view.View[4]/android.view.View/android.widget.GridView/android.view.View/android.view.View/android.widget.GridView/android.view.View[2]/android.view.View/android.widget.GridView/android.view.View/android.view.View/android.widget.GridView/android.view.View/android.view.View[2]/android.widget.GridView/android.view.View/android.view.View'

            if not self.d.xpath(email_content_xpath).wait(timeout=timeout):
                self.logger.error("Email content container not found")
                return False

            self.logger.info("Email content container found")
            return True

        except Exception as e:
            self.logger.error("Error waiting for email content: %s", e)
            return False

    def extract_verification_code(self, timeout=10):
        try:
            self.logger.info("Waiting for email content to load...")

            # Define the XPath for the email content container
            content_xpath = (
                '//android.view.View[@resource-id="email_content"]'
                "/android.widget.GridView/android.view.View[4]/android.view.View"
                "/android.widget.GridView/android.view.View/android.view.View"
                "/android.widget.GridView/android.view.View[2]/android.view.View"
                "/android.widget.GridView/android.view.View/android.view.View"
                "/android.widget.GridView/android.view.View"
            )

            # Wait for the content container to appear
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.d.xpath(content_xpath).exists:
                    self.logger.info("✅ Email content container is now visible")
                    break
                self.logger.debug("Waiting for content container to appear...")
                time.sleep(1)
            else:
                self.logger.error("❌ Timeout waiting for email content to load")
                return None

            # Attempt to extract the 2FA code via XPath
            self.logger.info("Attempting to extract 2FA code via XPath...")

            # XPath to find any 6-digit number in visible views
            code_xpath = '//android.view.View[string-length(@text)=6 and translate(@text, "0123456789", "") = ""]'
            elements = self.d.xpath(code_xpath).all()

            for element in elements:
                try:
                    text = element.attrib.get("text", "")
                    if text.isdigit() and len(text) == 6:
                        self.logger.info(f"✅ Found 2FA code via XPath: {text}")
                        return text
                except Exception as e:
                    self.logger.warning(f"Skipping element due to error: {e}")
                    continue

            self.logger.error("❌ No 6-digit code found using XPath")
            return None

        except Exception as e:
            self.logger.error(f"Error extracting verification code via XPath: {e}")
            return None

    def _retrieve_verification_code(self, max_retries):
        """Attempt to find and extract the verification code"""
        token_retriever = TwoFactorTokenRetriever(self.d)
        attempt = 1

        while attempt <= max_retries:
            self.logger.info(
                "Attempt %d/%d to find Instagram email", attempt, max_retries
            )

            if token_retriever.find_and_verify_instagram_email():
                verification_code = token_retriever.extract_verification_code()

                if verification_code:
                    return verification_code

            attempt += 1
            time.sleep(3)

        return None

    def get_2fa_code(self, max_retries=3):
        try:
            self.logger.info("Starting 2FA code retrieval process")

            email_nav = EmailNavigation(
                driver=self.d, helper=self.helper, popup_handler=self.popup_handler
            )
            early_code = email_nav.perform_email_navigation()
            if early_code:
                self.logger.info(f"✅ Using early extracted 2FA code: {early_code}")
                self.is_logged_in = True
                return early_code  # EARLY RETURN – don't continue to fallback

            self.logger.error("Failed to retrieve 2FA code via any method")
            return None

        except Exception as e:
            self.logger.error("Error in get_2fa_code: %s", e)
            return None


class Firefox2FAFlow:
    def __init__(
        self,
        email,
        password,
        record_id,
        base_id,
        table_id,
        firefox_package="org.mozilla.firefoy",
    ):
        self.email = email
        self.password = password
        self.record_id = record_id
        self.base_id = base_id
        self.table_id = table_id
        self.firefox_package = firefox_package
        self.logger = setup_logger(self.__class__.__name__)
        self.d = u2.connect()
        self.airtable = AirtableClient()
        self.airtable.base_id = self.base_id
        self.airtable.table_id = self.table_id

    def run(self) -> str | None:
        try:
            self.logger.info("🚀 Starting Firefox 2FA extraction flow")

            login = EmailLogin(
                email=self.email,
                password=self.password,
                firefox_package=self.firefox_package,
            )

            if not login.perform_full_login():
                self.logger.error("❌ Login failed")
                return None

            helper = UIHelper(self.d)
            popup_handler = PopupHandler(
                self.d, helper=helper, config_path=str(POPUP_CONFIG_PATH)
            )
            token_retriever = TwoFactorTokenRetriever(
                driver=self.d,
                helper=helper,
                logger=self.logger,
                firefox_package=self.firefox_package,
                popup_handler=popup_handler,
            )

            code = token_retriever.get_2fa_code()
            if code:
                self.logger.info(f"✅ 2FA code retrieved: {code}")

                return code
            else:
                self.logger.error("❌ Failed to retrieve 2FA code")
                return None

        except Exception as e:
            self.logger.error(f"💥 Exception during Firefox2FAFlow: {e}")
            return None


if __name__ == "__main__":
    try:
        logger.info("🔍 Fetching email credentials from Airtable...")

        # Pull env vars for Airtable config
        base_id = os.getenv("AIRTABLE_BASE_ID")
        table_id = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")
        view_id = os.getenv("IG_ARMY_UNUSED_VIEW_ID")

        # Fetch account record
        client = AirtableClient()
        account_data = client.get_single_active_account(
            base_id=base_id, table_id=table_id, view_id=view_id
        )

        if not account_data:
            raise Exception("❌ No active account found in Airtable")

        fields = account_data["fields"]
        email = fields.get("Email")
        password = fields.get("Email Password")

        if not email or not password:
            raise Exception("❌ Missing email or password in Airtable record")

        logger.info(f"✅ Using email: {email}")

        # Run Firefox 2FA flow
        flow = Firefox2FAFlow(
            email=email,
            password=password,
            record_id=account_data["id"],
            base_id=account_data["base_id"],
            table_id=account_data["table_id"],
        )

        code = flow.run()

        if not code:
            raise Exception("❌ Failed to retrieve 2FA code")
        else:
            logger.info(f"✅ Successfully retrieved 2FA code: {code}")

            # 🆕 Trigger new identity after 2FA is logged
            from Shared.new_identity import new_identity  # Adjust import path as needed

            logger.info("🔁 Triggering new identity reset")
            if new_identity(flow.d):
                logger.info("🆕 New identity successfully triggered")
            else:
                logger.warning("⚠️ Failed to trigger new identity")

    except Exception as e:
        logger.error(f"❌ Process failed: {e}")

    finally:
        pass
