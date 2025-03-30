# get_code.py

import os
from airtable_management import AirtableClient
import re
import uiautomator2 as u2
import time
import logging
import cv2
import numpy as np
from PIL import Image
from Shared.logger_config import setup_logger
from Shared.stealth_typing import StealthTyper
from popup_handler import PopupHandler
from new_identity import new_identity
from Shared.ui_helper import UIHelper

logger = setup_logger(__name__)

class FirefoxAutomation:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.d = u2.connect()  # Connect to device
        self.helper = UIHelper(self.d)  # ✅ Initialize helper before using it

        self.popup_handler = PopupHandler(self.d, helper=self.helper, config_path="popup_config.json")  # ✅ Now safe to use helper
        self.popup_handler.register_watchers()

        self.firefox_package = "org.mozilla.firefoy"
        self.logger = setup_logger(self.__class__.__name__)
        self.token_retriever = TwoFactorTokenRetriever(
            driver=self.d,
            helper=self.helper,
            logger=self.logger,
            firefox_package=self.firefox_package,
            popup_handler=self.popup_handler
        )
        self.is_logged_in = False

    def launch_firefox(self):
        try:
            self.logger.info("Launching Firefox...")
            self.d.app_start(self.firefox_package)
            time.sleep(1)

            self.logger.info("⏳ Waiting for first-time popups...")
            time.sleep(3)  # Give time for popup watchers to auto-dismiss

            # Manually handle any missed popups once
            self.popup_handler.handle_all_popups()

            # Now try to find the URL bar
            smart_xpath = '^Search or enter address'
            url_bar_xpath = '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'

            for _ in range(10):
                self.popup_handler.handle_all_popups()

                if self.d.xpath(smart_xpath).exists:
                    self.logger.info("✅ Smart match: found 'Search or enter address'")
                    self.d.xpath(smart_xpath).click()
                    return True, True

                if self.d.xpath(url_bar_xpath).exists:
                    self.logger.info("✅ Fallback: found URL bar via resource-id")
                    self.d.xpath(url_bar_xpath).click()
                    return True, False

                time.sleep(1)

            self.logger.error("❌ URL bar not found after popups cleared")
            return False, False

        except Exception as e:
            self.logger.error(f"Error launching Firefox: {e}")
            return False, False

    def navigate_to_url(self, url, skip_click=False):
        try:
            if not url.startswith(('http://', 'https://')):
                url = f'https://www.{url}'

            self.logger.info("Navigating to %s", url)
            typer = StealthTyper(device_id=self.d.serial)

            url_bar_xpath = '//android.widget.EditText[contains(@resource-id, "edit_url_view")]'

            if skip_click:
                self.logger.info("🔁 Smart match already clicked — skipping manual URL bar click")
                time.sleep(0.5)
            else:
                self.logger.info("👆 Manually clicking URL bar (no smart match used)")
                if not self.helper.wait_for_xpath(url_bar_xpath, timeout=5):
                    self.logger.error("❌ URL bar not found")
                    return False

                if not self.d.xpath(url_bar_xpath).click_exists(timeout=3):
                    self.logger.error("❌ Failed to click URL bar")
                    return False

            # Always re-fetch the url_bar element after interaction
            url_bar = self.d.xpath(url_bar_xpath)

            # Enter and confirm the URL
            for attempt in range(2):
                self.d.clear_text()
                time.sleep(0.3)
                typer.type_text(url)
                time.sleep(0.8)

                typed_text = url_bar.get_text() or ""
                self.logger.info("Typed URL: '%s'", typed_text)

                if url in typed_text:
                    break
                self.logger.warning("URL entry mismatch. Retrying...")

            if url not in (url_bar.get_text() or ""):
                self.logger.error("❌ Failed to correctly enter URL after retries")
                return False

            typer.press_enter()

            # Wait for WebView and progress bar to disappear
            self.logger.info("⏳ Waiting for page to load...")
            start_time = time.time()
            while time.time() - start_time < 20:
                if self.d(className="android.webkit.WebView").exists:
                    progress = self.d(resourceIdMatches=".*progress.*")
                    if not progress.exists:
                        self.logger.info("✅ Page loaded — WebView visible, no progress bar")
                        time.sleep(5)  # buffer for cookie popup

                        try:
                            self.logger.info("🔍 Checking for cookie popup...")
                            self.popup_handler.handle_cookie_popup()
                        except Exception as e:
                            self.logger.warning(f"⚠️ Cookie popup handling failed: {e}")

                        return True
                time.sleep(1)

            self.logger.warning("⚠️ Page did not fully load within timeout")
            return False

        except Exception as e:
            self.logger.error(f"💥 Error in navigate_to_url: {e}")
            return False

 

    def handle_email_input(self):
        d = self.d
        helper = self.helper
        email = self.email
        logger = logging.getLogger("handle_email_input")
        typer = StealthTyper(device_id=d.serial)
        email_xpath = '//android.widget.EditText[@resource-id="email"]'
        password_xpath = '//android.widget.EditText[@resource-id="password"]'

        for attempt in range(3):
            logger.info(f"📧 Email entry attempt {attempt + 1}/3")
            if not helper.wait_for_xpath(email_xpath, timeout=10):
                logger.error("Email input field not found")
                return False

            field = d.xpath(email_xpath)
            if not field.click_exists(timeout=2):
                logger.error("Failed to click email field")
                return False

            d.clear_text()
            typer.type_text(email)

            for _ in range(3):
                entered = field.get_text() or ""
                if email in entered:
                    logger.info(f"✅ Email entered: {entered}")
                    break
                time.sleep(0.5)
            else:
                logger.warning(f"❌ Email mismatch: {entered}")
                continue

            # Confirm one last time
            if email not in (field.get_text() or ""):
                logger.error("❌ Final email entry failed")
                return False

            if not helper.smart_button_clicker("NEXT", fallback_xpath='//android.widget.Button[@text="NEXT"]'):
                logger.error("❌ Failed to click NEXT")
                return False

            if not helper.wait_for_xpath(password_xpath, timeout=8):
                logger.warning("NEXT clicked, but password field didn't appear")
                return False

            logger.info("✅ Email flow complete")
            return True

        logger.error("❌ Email input failed after retries")
        return False

    def handle_password_input(self):
        d = self.d
        helper = self.helper
        password = self.password
        logger = logging.getLogger("handle_password_input")
        typer = StealthTyper(device_id=d.serial)
        password_xpath = '//android.widget.EditText[@resource-id="password"]'
        trusted_prompt_xpath = '//android.view.View[@text="Do you want to add this device to trusted ones?"]'

        for attempt in range(3):
            logger.info(f"🔑 Password entry attempt {attempt + 1}/3")

            if not helper.wait_for_xpath(password_xpath, timeout=10):
                logger.error("Password input field not found")
                return False

            field = d.xpath(password_xpath)
            if not field.click_exists(timeout=2):
                logger.error("Failed to click password field")
                return False

            d.clear_text()

            for fill_attempt in range(2):
                typer.type_text(password)
                time.sleep(0.5)
                if not helper.click_show_password_icon(password_xpath):
                    logger.warning("Show password icon not found")
                visible_pw = field.get_text() or ""
                if visible_pw == password:
                    logger.info("✅ Password match confirmed")
                    break
                else:
                    logger.warning("❌ Password mismatch — retrying")
                    d.clear_text()
            else:
                continue

            if not helper.smart_button_clicker("LOG IN", fallback_xpath='//android.widget.Button[@text="LOG IN"]'):
                logger.error("❌ Failed to click LOG IN")
                return False

            logger.info("✅ Password submitted — waiting for next page")
            time.sleep(2)

            logger.info("Password Submitted - continuing to post-login flow")
            return "submitted"

            # # Short wait for trusted device prompt
            # if helper.wait_for_xpath(trusted_prompt_xpath, timeout=2):
            #     logger.info("➡️ Trusted device prompt detected")
            #     return "trusted_device_prompt"
            #
            # return "submitted"

        logger.error("❌ Password entry failed after retries")
        return False

    def handle_trusted_device_prompt(self):
        helper = self.helper

        logger = logging.getLogger("handle_trusted_device_prompt")
        prompt_xpath = '//android.view.View[@text="Do you want to add this device to trusted ones?"]'

        if not helper.wait_for_xpath(prompt_xpath, timeout=10):
            logger.info("Trusted device prompt not present")
            return False

        logger.info("Trusted device prompt detected")

        if not helper.smart_button_clicker("Skip", fallback_xpath='//android.widget.Button[@text="Skip"]'):
            logger.warning("❌ Failed to click Skip on trusted device prompt")
            return False

        time.sleep(1.5)
        logger.info("✅ Trusted device prompt skipped")
        return True

    def handle_post_login_flow(self):
        d = self.d
        helper = self.helper
        popup_handler = self.popup_handler
        logger = logging.getLogger("handle_post_login_flow")

        logger.info("▶️ Starting post-login handling")

        # Step 1: Dismiss save password popup (if shown)
        for _ in range(5):
            container = d(resourceId="org.mozilla.firefoy:id/design_bottom_sheet")
            cancel_btn = d(resourceId="org.mozilla.firefoy:id/save_cancel")
            if container.exists and cancel_btn.exists and cancel_btn.click_exists(timeout=3):
                logger.info("✅ Dismissed save password popup")
                time.sleep(1)
                break
            time.sleep(1.5)

        # Step 2: Handle translation popup if it appears late
        popup_handler.handle_translation_popup()

        # Step 3: Handle any lingering popups
        popup_handler.handle_all_popups()

        # Step 4: Wait for final inbox UI (React_MainContainer)
        logger.info("⏳ Verifying inbox UI up to 30s post-popup")
        email_nav = EmailNavigation(driver=d, helper=helper, popup_handler=popup_handler)

        start = time.time()
        while time.time() - start < 30:
            popup_handler.handle_all_popups()
            if email_nav.verify_logged_in():
                logger.info("✅ Final login verification passed")
                return True
            time.sleep(2)

        logger.error("❌ Login failed: final inbox not reached")
        return False



    def perform_login_sequence(self):
        try:
            self.logger.info("🔐 Starting login sequence...")


            # Step 1: Email input
            if not self.handle_email_input():
                self.logger.error("❌ Email input failed")
                return False

            # Step 2: Password input
            password_result = self.handle_password_input()
            if password_result is False:
                self.logger.error("❌ Password input failed")
                return False

            # Step 3: Trusted device prompt if immediately triggered
            if password_result == "trusted_device_prompt":
                self.logger.info("➡️ Trusted device prompt appeared immediately")
                self.handle_trusted_device_prompt()

            # Step 4: Final post-login handling and inbox verification
            if not self.handle_post_login_flow():
                self.logger.error("❌ Post-login flow failed to verify login")
                return False

            self.logger.info("✅ Login sequence completed successfully")
            self.is_logged_in = True
            return True

        except Exception as e:
            self.logger.error(f"💥 Fatal error in login sequence: {e}")
            return False

class EmailNavigation:
    def __init__(self, driver, helper, popup_handler):
        self.d = driver
        self.helper = helper
        self.popup_handler = popup_handler
        self.logger = setup_logger(self.__class__.__name__)


    def verify_logged_in(self):
        try:
            self.logger.info("Verifying login status...")
            main_container_xpath = '^React_MainContainer'  # Smart search by resource-id

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
            self.logger.info("🔍 Scanning React_MainContainer for Instagram 2FA email blocks...")

            container_xpath = '//android.view.View[@resource-id="React_MainContainer"]'
            block_xpath = container_xpath + '//android.view.View[.//android.view.View[@text="Instagram"] and .//android.view.View[@text="Verify your account"]]'

            blocks = self.d.xpath(block_xpath).all()
            self.logger.info(f"📦 Found {len(blocks)} candidate blocks inside main container")

            for block in blocks:
                try:
                    children = self.d.xpath(block.get_xpath() + '/android.view.View').all()
                    for child in children:
                        text = child.attrib.get("text", "") or ""
                        match = re.search(r'\b(\d{6})\b', text)
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
            clickable_wrapper_xpath = email_block.get_xpath() + '/../..'  # go up to Button container

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
                self.logger.error("Write message button not found - sidebar might not be open")
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
            self.logger.info("Searching for Communities button using xpath: %s", communities_xpath)
            
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
            # Step 1: Verify login state
            logged_in = self.verify_logged_in()

            if logged_in:
                self.logger.info("✅ React_MainContainer present — waiting for possible popups...")

                # Step 2: Handle translation popup if it appears within 5 seconds
                translation_xpath = '^Try private translations'
                for _ in range(5):
                    if self.d.xpath(translation_xpath).exists:
                        self.logger.info("📌 Translation popup appeared — dismissing")
                        self.popup_handler.handle_all_popups()
                        time.sleep(1.5)
                        break
                    time.sleep(1)

                # Step 3: Attempt to extract 2FA code from main container
                code = self.find_code_in_main_container()
                if code:
                    self.logger.info(f"✅ 2FA code found in main container: {code}")
                    return code
                else:
                    self.logger.info("⚠️ No 2FA code found in main container — falling back to sidebar")

            else:
                self.logger.info("⚠️ React_MainContainer not found — proceeding with sidebar fallback...")

            # Step 4: Open sidebar
            if not self.open_sidebar():
                self.logger.info("🕵️ Sidebar open failed — checking for cashback popup...")
                try:
                    dismissed = self.popup_handler.handle_cashback_popup()
                    if dismissed:
                        self.logger.info("✅ Cashback popup dismissed — retrying sidebar")
                        if not self.open_sidebar():
                            self.logger.error("❌ Sidebar open still failed after cashback dismiss")
                            return None
                    else:
                        self.logger.info("ℹ️ No cashback popup to dismiss")
                        return None
                except Exception as e:
                    self.logger.warning(f"⚠️ Cashback popup handler failed: {e}")
                    return None

            time.sleep(1.5)  # Let animation settle

            # Step 5: Confirm sidebar opened (retry up to 2 times)
            for attempt in range(2):
                if self.verify_sidebar_open():
                    break
                self.logger.warning(f"Sidebar not open, retrying ({attempt+1}/2)...")
                self.open_sidebar()
                time.sleep(1.5)
            else:
                self.logger.error("❌ Sidebar failed to open after retries")
                return None

            # Step 6: Navigate to Communities tab
            if not self.navigate_to_communities():
                return None

            self.logger.info("✅ Clicked Communities tab — waiting for view to load...")
            time.sleep(2)

            # Step 7: Search for 2FA email in community tab
            smart_xpath = '^Hi '
            matches = self.d.xpath(smart_xpath).all()
            self.logger.info(f"📥 Found {len(matches)} candidate email blocks")

            for email_element in matches:
                full_text = email_element.attrib.get("text", "")
                if "tried to log in to your Instagram account" in full_text:
                    self.logger.info(f"📩 Matched 2FA email: {full_text[:100]}...")
                    match = re.search(r"\b(\d{6})\b", full_text)
                    if match:
                        code = match.group(1)
                        self.logger.info(f"✅ Extracted 2FA code: {code}")
                        return code
                    else:
                        self.logger.warning("No 6-digit code found in matched email")
                        return None

            self.logger.error("❌ No matching Instagram 2FA email found after sidebar navigation")
            return None

        except Exception as e:
            self.logger.error(f"Error in email navigation sequence: {e}")
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
                    new_tab_xpath = '//android.widget.TextView[contains(@text, "New tab")]'
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
            instagram_text_xpath = f'{top_email_xpath}//android.view.View[@text="Instagram"]'
            verify_text_xpath = f'{top_email_xpath}//android.view.View[@text="Verify your account"]'

            if self.d.xpath(instagram_text_xpath).exists and self.d.xpath(verify_text_xpath).exists:
                self.logger.info("Top email matches Instagram verification criteria")

                if top_email_element.click_exists(timeout=3):
                    self.logger.info("Clicked top Instagram verification email")
                    return True
                else:
                    self.logger.error("Failed to click top Instagram email")
                    return False
            else:
                self.logger.warning("Top email does not match Instagram verification content")
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
                '/android.widget.GridView/android.view.View[4]/android.view.View'
                '/android.widget.GridView/android.view.View/android.view.View'
                '/android.widget.GridView/android.view.View[2]/android.view.View'
                '/android.widget.GridView/android.view.View/android.view.View'
                '/android.widget.GridView/android.view.View'
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
                    text = element.attrib.get('text', '')
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
            self.logger.info("Attempt %d/%d to find Instagram email", attempt, max_retries)
            
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

            # Try early code extraction from main container
            email_nav = EmailNavigation(driver=self.d, helper=self.helper, popup_handler=self.popup_handler)
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


# if __name__ == "__main__":
#     try:
#         logger.info("🔍 Fetching email credentials from Airtable...")
#
#         base_id = os.getenv("AIRTABLE_BASE_ID")
#         table_name = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")
#         unused_view_id = os.getenv("IG_ARMY_UNUSED_VIEW_ID")
#
#         client = AirtableClient()
#         account_data = client.get_single_active_account(
#             base_id=base_id,
#             table_name=table_name,
#             unused_view_id=unused_view_id
#         )
#
#         if not account_data:
#             raise Exception("❌ No active account found in Airtable")
#
#         account = account_data["fields"]
#         email = account.get("Email")
#         password = account.get("Email Password")
#
#         if not email or not password:
#             raise Exception("❌ Missing email or password in Airtable record")
#
#         logger.info(f"✅ Using email: {email}")
#
#         firefox = FirefoxAutomation(email=email, password=password)
#
#         if not firefox.launch_firefox():
#             raise Exception("❌ Failed to launch Firefox")
#
#         if not firefox.navigate_to_url("op.pl"):
#             raise Exception("❌ Failed to navigate to op.pl")
#
#         if not firefox.perform_login_sequence():
#             raise Exception("❌ Login sequence failed")
#
#         email_nav = EmailNavigation(driver=firefox.d, helper=firefox.helper, popup_handler=popup_handler)
#         code = email_nav.perform_email_navigation()
#
#         if not code:
#             logger.info("🔁 Trying fallback extraction from opened email")
#             code = firefox.token_retriever.get_2fa_code(max_retries=3)
#
#         if not code:
#             raise Exception("❌ Failed to retrieve 2FA code")
#         else:
#             logger.info(f"✅ Successfully retrieved 2FA code: {code}")
#
#         # Always try indentiy reset, regardless of sources
#         try:
#             logger.info("🔄 Triggering identity reset...")
#             if new_identity(firefox.d, timeout=10):
#                 logger.info("✅ Identity reset triggered successfully")
#             else:
#                 logger.warning("⚠️ Identity reset failed or notification not found")
#         except Exception as e:
#             logger.error(f"💥 Error during identity reset: {e}")
#
#     except Exception as e:
#         logger.error(f"❌ Process failed: {e}")
#
#     finally:
#         pass
def main():
    try:
        logger.info("🧪 Running email logout + new tab test")

        d = u2.connect()
        helper = UIHelper(d)

        # Ensure Firefox is open and user is logged into email before running this
        popup_handler = PopupHandler(d, helper=helper, config_path="popup_config.json")
        popup_handler.register_watchers()

        email_nav = EmailNavigation(driver=d, helper=helper, popup_handler=popup_handler)

        if email_nav.logout_of_email():
            logger.info("✅ Successfully logged out of email")

        if email_nav.open_new_tab():
            logger.info("✅ Successfully opened new tab in Firefox")

        logger.info("🎉 Test completed")

    except Exception as e:
        logger.error(f"💥 Test failed: {e}")

if __name__ == "__main__":
    main()

