# LoginBot/get_ig_login_code.py

import os
import re
import time
from pathlib import Path
from typing import Optional, Tuple  # Added Tuple

import uiautomator2 as u2

# Corrected import path for new_identity
from Shared.AppCloner.new_identity import new_identity

# Core project imports
from Shared.Data.airtable_manager import AirtableClient

# Assuming InstagramInteractions is now in Shared directory after refactor
from Shared.instagram_actions import InstagramInteractions
from Shared.UI.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper
from Shared.Utils.xpath_config import FirefoxEmailXPaths  # Import the Firefox XPaths

# --- Configuration ---
# Use module-level logger for setup messages before class instantiation
module_logger = setup_logger(__name__)
POPUP_CONFIG_PATH = Path(__file__).resolve().parents[1] / "Shared" / "popup_config.json"
DEFAULT_FIREFOX_PACKAGE = "org.mozilla.firefox"  # Default package name

# --- Helper Classes Refactored ---


class FirefoxManager:
    """Manages Firefox browser interactions like launch, navigation, tabs."""

    def __init__(
        self,
        device: u2.Device,
        interactions: InstagramInteractions,
        firefox_xpaths: FirefoxEmailXPaths,
        stealth_typer: StealthTyper,
        popup_handler: PopupHandler,
    ):
        self.d = device
        self.interactions = interactions  # Use the generic interactions layer
        self.firefox_xpaths = firefox_xpaths
        self.typer = stealth_typer
        self.popup_handler = popup_handler
        self.logger = setup_logger(self.__class__.__name__)
        self.firefox_package = (
            self.interactions.app_package
        )  # Get package from interactions

    def launch_and_navigate(self, url: str) -> bool:
        """Launches Firefox (if not already running) and navigates to the URL."""
        self.logger.info(
            f"🚀 Ensuring Firefox ({self.firefox_package}) is open and navigating to {url}..."
        )

        # 1. Ensure Firefox is open and ready using interactions layer
        # Use the URL bar as a readiness signal
        if not self.interactions.open_app(
            readiness_xpath=self.firefox_xpaths.firefox_url_bar_edit_text,
            readiness_timeout=20,
            max_retries=2,
        ):
            # Try the smart search bar as an alternative readiness signal
            self.logger.warning(
                "Primary readiness XPath failed, trying smart search bar..."
            )
            if not self.interactions.open_app(
                readiness_xpath=self.firefox_xpaths.firefox_url_bar_smart_search,
                readiness_timeout=15,
                max_retries=1,  # Only one more try
            ):
                self.logger.error(
                    f"❌ Failed to open/ready Firefox ({self.firefox_package})."
                )
                return False

        self.logger.info("✅ Firefox is open. Handling initial popups...")
        time.sleep(1)  # Allow UI to settle slightly
        self.popup_handler.handle_all_popups(delay_after_click=0.5)  # Quick check
        time.sleep(1)

        # 2. Navigate to the URL
        try:
            full_url = f"https://{url}" if not url.startswith("http") else url
            self.logger.info(f"Navigating to {full_url}")

            # Find and click URL bar (try both methods)
            url_bar_found = False
            if self.interactions.click_if_exists(
                self.firefox_xpaths.firefox_url_bar_smart_search, timeout=2
            ):
                self.logger.info("Clicked smart URL bar.")
                url_bar_found = True
            elif self.interactions.click_by_xpath(
                self.firefox_xpaths.firefox_url_bar_edit_text, timeout=5
            ):
                self.logger.info("Clicked fallback URL bar (EditText).")
                url_bar_found = True

            if not url_bar_found:
                self.logger.error("❌ Failed to find or click Firefox URL bar.")
                return False

            # Get the EditText element *after* clicking (important for focus)
            url_input_xpath = self.firefox_xpaths.firefox_url_bar_edit_text
            if not self.interactions.wait_for_element_appear(
                url_input_xpath, timeout=3
            ):
                self.logger.error(
                    "❌ URL EditText field did not appear after clicking bar."
                )
                return False

            # Clear and type using StealthTyper
            self.logger.debug("Clearing URL bar...")
            # uiautomator2's clear_text might be needed if element reference changes
            # self.d.xpath(url_input_xpath).clear_text() # Or use interactions clear?
            self.d.clear_text()  # Direct clear might be okay here
            time.sleep(0.5)

            self.logger.debug(f"Typing URL: {full_url}")
            self.typer.type_text(full_url)
            time.sleep(1)  # Let text settle

            # Verification (Optional but recommended)
            entered_text = self.interactions.get_element_text(
                url_input_xpath, timeout=2
            )
            if not entered_text or full_url not in entered_text:
                self.logger.warning(
                    f"URL verification failed. Expected ~'{full_url}', got '{entered_text}'. Retrying typing..."
                )
                self.d.clear_text()
                time.sleep(0.3)
                self.typer.type_text(full_url)
                time.sleep(1)
                entered_text = self.interactions.get_element_text(
                    url_input_xpath, timeout=2
                )
                if not entered_text or full_url not in entered_text:
                    self.logger.error("❌ URL typing failed verification after retry.")
                    return False

            self.logger.debug("Pressing Enter...")
            self.typer.press_enter()
            self.logger.info(
                f"✅ Navigation to {full_url} initiated. Waiting for page load..."
            )
            time.sleep(7)  # Increased wait for page load after Enter
            return True

        except Exception as e:
            self.logger.error(f"Error navigating to URL '{url}': {e}", exc_info=True)
            return False

    def close_firefox(self) -> bool:
        """Closes the Firefox application."""
        self.logger.info(f"🛑 Closing Firefox ({self.firefox_package})...")
        return self.interactions.close_app()

    def open_new_tab(self) -> bool:
        """Opens a new tab in Firefox."""
        try:
            self.logger.info("🆕 Attempting to open a new tab in Firefox...")
            # Use random tap for more human-like interaction
            if not self.interactions.tap_random_within_element(
                self.firefox_xpaths.firefox_tabs_button, label="Tabs Button", timeout=5
            ):
                self.logger.warning("⚠️ Failed to click 'Tabs' button.")
                # Fallback: Try direct click if random tap failed
                if not self.interactions.click_by_xpath(
                    self.firefox_xpaths.firefox_tabs_button, timeout=3
                ):
                    self.logger.error(
                        "❌ Failed to click 'Tabs' button (fallback failed)."
                    )
                    return False
                self.logger.info("Clicked 'Tabs' button via fallback.")

            time.sleep(1.5)  # Wait for tabs view animation

            # Click 'New tab' button
            if not self.interactions.click_by_xpath(
                self.firefox_xpaths.firefox_new_tab_button, timeout=5
            ):
                # Sometimes it's a different element type or has slightly different text
                alt_new_tab_xpath = (
                    '//android.widget.Button[contains(@text, "New tab")]'
                )
                self.logger.warning(
                    "Primary 'New Tab' click failed, trying alternative..."
                )
                if not self.interactions.click_by_xpath(alt_new_tab_xpath, timeout=3):
                    self.logger.error("❌ Failed to click 'New tab' button.")
                    return False

            self.logger.info("✅ Opened new tab.")
            time.sleep(1.5)  # Wait for new tab to load/settle
            return True
        except Exception as e:
            self.logger.error(f"💥 Error opening new tab: {e}", exc_info=True)
            return False


class EmailLogin:
    """Handles the op.pl login process (email and password steps)."""

    def __init__(
        self,
        device: u2.Device,  # Keep device for direct stealth typer access
        interactions: InstagramInteractions,
        firefox_xpaths: FirefoxEmailXPaths,
        stealth_typer: StealthTyper,
        popup_handler: PopupHandler,
        email_address: str,
        email_password: str,
    ):
        self.d = device  # Needed for direct calls like clear_text, potentially
        self.interactions = interactions
        self.firefox_xpaths = firefox_xpaths
        self.typer = stealth_typer
        self.popup_handler = popup_handler
        self.email = email_address
        self.password = email_password
        self.logger = setup_logger(self.__class__.__name__)
        self._email_input_successful = False  # Internal state tracker

    def perform_op_login(self) -> bool:
        """Executes the full op.pl login sequence (email -> password -> verify)."""
        self.logger.info("🔐 Starting op.pl login sequence...")

        if not self._handle_email_input():
            self.logger.error("❌ Email input stage failed.")
            return False

        password_result = self._handle_password_input()
        if password_result != "submitted":  # Expect "submitted" on success
            self.logger.error("❌ Password input stage failed.")
            return False

        # Final verification after password submission
        if not self._handle_post_login_flow():
            self.logger.error("❌ Post-login verification failed (inbox not reached).")
            return False

        self.logger.info("✅ op.pl Login sequence completed successfully.")
        return True

    def _handle_email_input(self) -> bool:
        """Handles finding and filling the email field, and clicking NEXT."""
        if self._email_input_successful:
            self.logger.info("📧 Email already handled successfully, skipping.")
            return True

        email_field_xpath = self.firefox_xpaths.email_login_email_field
        password_field_xpath = self.firefox_xpaths.email_login_password_field
        next_button_text = [self.firefox_xpaths.email_login_next_button_text]
        next_button_fallback = self.firefox_xpaths.email_login_next_button_fallback

        for attempt in range(3):
            self.logger.info(f"📧 Email entry attempt {attempt + 1}/3")

            # 1. Wait for email field
            if not self.interactions.wait_for_element_appear(
                email_field_xpath, timeout=10
            ):
                self.logger.error("Email input field not found, checking for popups...")
                self.popup_handler.handle_all_popups()  # Check popups if field isn't there
                time.sleep(1)
                if not self.interactions.element_exists(email_field_xpath):
                    self.logger.error(
                        "Email input field still not found after popup check."
                    )
                    continue  # To next attempt

            self.logger.info(
                "🕒 Email field potentially found — waiting before cookie check..."
            )
            time.sleep(4)  # Slightly reduced wait

            # 2. Handle cookies specifically
            self.logger.info("🍪 Running cookie popup handler before email entry")
            self.popup_handler.handle_cookie_popup()
            time.sleep(1)  # Wait for cookie handler to finish

            # 3. Click email field
            if not self.interactions.click_by_xpath(email_field_xpath, timeout=3):
                self.logger.error(
                    "❌ Failed to click email field. Handling general popups..."
                )
                self.popup_handler.handle_all_popups()  # Maybe another popup appeared
                time.sleep(1)
                if not self.interactions.click_by_xpath(email_field_xpath, timeout=2):
                    self.logger.error(
                        "❌ Failed to click email field after popup check."
                    )
                    continue  # To next attempt

            # 4. Clear and type email
            self.logger.debug("Clearing email field...")
            self.d.clear_text()  # Direct clear often needed here
            time.sleep(0.3)
            self.logger.debug(f"Typing email: {self.email}")
            self.typer.type_text(self.email)
            time.sleep(0.5)

            # 5. Verify email input
            entered_text = self.interactions.get_element_text(
                email_field_xpath, timeout=2
            )
            if not entered_text or self.email not in entered_text:
                self.logger.warning(
                    f"Email verification failed. Expected ~'{self.email}', got '{entered_text}'. Retrying typing..."
                )
                self.d.clear_text()
                time.sleep(0.3)
                self.typer.type_text(self.email)
                time.sleep(1)
                entered_text = self.interactions.get_element_text(
                    email_field_xpath, timeout=2
                )
                if not entered_text or self.email not in entered_text:
                    self.logger.error(
                        "❌ Email typing failed verification after retry."
                    )
                    continue  # To next attempt
            self.logger.info("✅ Email typed and verified.")

            # 6. Click NEXT button
            if not self.interactions.smart_button_clicker(
                text_patterns=next_button_text,
                fallback_xpath=next_button_fallback,
                timeout=5,
            ):
                self.logger.error("❌ Failed to click NEXT button.")
                # Check for common errors here? e.g. incorrect email format error message?
                continue  # To next attempt

            # 7. Wait for password field to appear as confirmation
            if self.interactions.wait_for_element_appear(
                password_field_xpath, timeout=10
            ):
                self.logger.info(
                    "✅ Email submitted successfully (password field appeared)."
                )
                self._email_input_successful = True
                return True
            else:
                self.logger.warning(
                    "NEXT clicked, but password field did not appear. Maybe login error?"
                )
                # Add check for error messages if needed
                self.popup_handler.handle_all_popups()  # Check for other popups
                # Don't immediately return False, let retry loop handle it unless it's the last attempt.

        self.logger.error("❌ Email input failed after all retries.")
        return False

    def _handle_password_input(self) -> str | bool:
        """Handles finding and filling the password field, clicking show, verifying, and submitting."""
        password_field_xpath = self.firefox_xpaths.email_login_password_field
        login_button_text = [self.firefox_xpaths.email_login_login_button_text]
        login_button_fallback = self.firefox_xpaths.email_login_login_button_fallback

        for attempt in range(3):
            self.logger.info(f"🔑 Password entry attempt {attempt + 1}/3")

            # 1. Wait for password field
            if not self.interactions.wait_for_element_appear(
                password_field_xpath, timeout=10
            ):
                self.logger.error("Password input field not found.")
                # Check popups?
                self.popup_handler.handle_all_popups()
                time.sleep(1)
                if not self.interactions.element_exists(password_field_xpath):
                    continue  # To next attempt

            # 2. Click password field
            if not self.interactions.click_by_xpath(password_field_xpath, timeout=3):
                self.logger.error("❌ Failed to click password field.")
                self.popup_handler.handle_all_popups()
                time.sleep(1)
                if not self.interactions.click_by_xpath(
                    password_field_xpath, timeout=2
                ):
                    continue  # To next attempt

            # 3. Clear and type password
            self.logger.debug("Clearing password field...")
            self.d.clear_text()
            time.sleep(0.3)
            self.logger.debug("Typing password...")
            self.typer.type_text(self.password)
            time.sleep(0.7)  # Slightly longer pause after password

            # 4. Click show password icon IMMEDIATELY for verification
            if not self.interactions.click_show_password_icon(password_field_xpath):
                self.logger.error(
                    "❌ Could not click show-password icon — cannot verify password input."
                )
                # Decide: retry typing, or fail attempt? Failing is safer.
                continue  # To next attempt
            time.sleep(0.5)  # Wait for text to become visible

            # 5. Verify password text
            visible_pw = self.interactions.get_element_text(
                password_field_xpath, timeout=3
            )
            self.logger.info(
                f"👁️ Visible password field text: '{visible_pw}'"
            )  # Log for debug

            if visible_pw == self.password:
                self.logger.info("✅ Password match confirmed.")

                # 6. Click LOG IN button
                if self.interactions.smart_button_clicker(
                    text_patterns=login_button_text,
                    fallback_xpath=login_button_fallback,
                    timeout=5,
                ):
                    self.logger.info("✅ Password submitted (LOG IN clicked).")
                    time.sleep(3)  # Wait for potential page transition/login process
                    return "submitted"  # Signal success
                else:
                    self.logger.error("❌ Failed to click LOG IN button.")
                    # Check for error messages like "Incorrect password"?
                    self.popup_handler.handle_all_popups()
                    # Don't retry immediately, let the loop handle it unless it's the last attempt.
            else:
                self.logger.warning(
                    f"❌ Password mismatch! Expected '{self.password}', got '{visible_pw}'. Retrying..."
                )
                # Field is already cleared by the start of the loop if it repeats

        self.logger.error("❌ Password entry failed after all retries.")
        return False

    def _handle_post_login_flow(self) -> bool:
        """Verifies successful login by checking for the main email container."""
        self.logger.info("▶️ Verifying post-login state (checking for inbox UI)...")
        inbox_indicator_xpath = self.firefox_xpaths.email_main_container

        # Wait up to 30 seconds for the main container to appear
        if self.interactions.wait_for_element_appear(inbox_indicator_xpath, timeout=30):
            self.logger.info("✅ Login successful: Main email container found.")
            return True
        else:
            self.logger.error(
                "❌ Login verification failed: Main email container did not appear."
            )
            self.popup_handler.handle_all_popups()  # Check if a different unexpected screen appeared
            # Maybe take a screenshot for debugging?
            # self.d.screenshot(...)
            return False


class EmailNavigation:
    """Handles navigation within the op.pl email interface after login."""

    def __init__(
        self,
        device: u2.Device,
        interactions: InstagramInteractions,
        firefox_xpaths: FirefoxEmailXPaths,
        popup_handler: PopupHandler,
    ):
        self.d = device
        self.interactions = interactions
        self.firefox_xpaths = firefox_xpaths
        self.popup_handler = popup_handler
        self.logger = setup_logger(self.__class__.__name__)

    def verify_logged_in(self) -> bool:
        """Verifies if the main email container is present."""
        # This might be redundant if EmailLogin._handle_post_login_flow() already does it,
        # but can be used as a quick check.
        self.logger.debug("Verifying logged-in status via main container...")
        # Use element_exists for a quick check without long wait
        return self.interactions.element_exists(
            self.firefox_xpaths.email_main_container
        )

    def _extract_code_from_text(self, text: str) -> Optional[str]:
        """Helper to extract a 6-digit code from a string."""
        if not text:
            return None
        match = re.search(r"\b(\d{6})\b", text)
        if match:
            code = match.group(1)
            self.logger.info(f"Found 6-digit code: {code}")
            return code
        return None

    def find_code_in_email_preview(self) -> Optional[str]:
        """Scans the main email list view for the Instagram code in previews."""
        self.logger.info(
            "🔍 Scanning email preview list (main container) for 2FA code..."
        )
        container_xpath = self.firefox_xpaths.email_main_container
        # XPath targeting blocks likely containing IG verification emails
        block_xpath = self.firefox_xpaths.email_instagram_verification_block

        # Ensure main container exists first
        if not self.interactions.wait_for_element_appear(container_xpath, timeout=5):
            self.logger.warning("Main container not found, cannot scan previews.")
            return None

        # Find candidate email blocks
        # Using device.xpath directly as interactions doesn't have a specific 'find_all' yet
        blocks = self.d.xpath(block_xpath).all()
        self.logger.info(
            f"📦 Found {len(blocks)} candidate Instagram email blocks in preview."
        )

        if not blocks:
            # Try scrolling down once if no blocks found initially
            self.logger.info("No candidate blocks found, trying to scroll down once.")
            self.interactions.scroll_down_humanlike()
            time.sleep(2)
            blocks = self.d.xpath(block_xpath).all()
            self.logger.info(f"📦 Found {len(blocks)} blocks after scrolling.")

        for block in blocks:
            try:
                # Extract all text from children of the block
                # This is complex, get_text() on the block might be simpler if structure allows
                block_text_content = ""
                children = self.d.xpath(
                    block.get_xpath() + "//*"
                ).all()  # Get all descendants
                for child in children:
                    text = child.info.get("text") or child.info.get(
                        "contentDescription"
                    )
                    if text:
                        block_text_content += text + " "

                self.logger.debug(
                    f"Preview block text content: {block_text_content[:200]}..."
                )
                code = self._extract_code_from_text(block_text_content)
                if code:
                    self.logger.info(
                        f"✅ Found 2FA code in email preview block: {code}"
                    )
                    return code
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Error processing preview block: {e}", exc_info=True
                )
                continue  # Try next block

        self.logger.info("❌ No 2FA code found directly in email previews.")
        return None

    def open_email_and_extract_code_from_detail_view(self) -> Optional[str]:
        """Opens the first relevant Instagram email and extracts the code from its detail view."""
        self.logger.info(
            "🔓 Attempting to open top Instagram email and extract code from detail..."
        )

        # XPath to find the clickable area of the IG email block
        # This assumes the structure found in find_code_in_main_container
        ig_block_xpath = self.firefox_xpaths.email_instagram_verification_block
        # The clickable element might be the block itself or a parent
        clickable_block_xpath = f"({ig_block_xpath})[1]"  # Try the first one found

        # Try clicking the block directly first
        if self.interactions.click_by_xpath(clickable_block_xpath, timeout=5):
            self.logger.info("✅ Clicked first Instagram email block directly.")
        else:
            # Fallback: find 'Instagram' text and click its parent/grandparent
            self.logger.warning(
                "Direct block click failed, trying parent click strategy..."
            )
            ig_text_xpath = (
                f"({ig_block_xpath}//android.view.View[@text='Instagram'])[1]"
            )
            ig_text_element = self.d.xpath(ig_text_xpath)
            if ig_text_element.wait(timeout=3):
                try:
                    # Try clicking parent, then grandparent
                    if ig_text_element.parent().click_exists(timeout=1):
                        self.logger.info("Clicked parent of 'Instagram' text.")
                    elif ig_text_element.parent().parent().click_exists(timeout=1):
                        self.logger.info("Clicked grandparent of 'Instagram' text.")
                    else:
                        self.logger.error(
                            "❌ Failed to click Instagram email block via parent strategy."
                        )
                        return None
                except Exception as click_e:
                    self.logger.error(
                        f"❌ Error clicking parent/grandparent: {click_e}"
                    )
                    return None
            else:
                self.logger.error(
                    "❌ Instagram email block/text not found for opening."
                )
                return None

        self.logger.info("⏳ Waiting for email detail view to load...")
        time.sleep(5)  # Allow time for email content to render

        # Handle potential popups after opening email
        self.popup_handler.handle_all_popups()

        # Now, search for the code within the detail view
        code_xpath = self.firefox_xpaths.email_opened_verification_code
        self.logger.info("🔍 Searching for 6-digit code in detail view...")

        # Wait a bit longer for the code element itself
        if not self.interactions.wait_for_element_appear(code_xpath, timeout=15):
            self.logger.error(
                "❌ 6-digit code element not found in opened email detail view."
            )
            # Try OCR as a last resort? Requires careful implementation.
            # self.logger.info("Trying OCR fallback on email detail...")
            # screen_text = self.popup_handler.perform_ocr(lang="eng") # Or relevant lang
            # code = self._extract_code_from_text(screen_text)
            # if code: return code
            return None

        # Iterate through potential code elements found by XPath
        # Using d.xpath().all() as interactions doesn't have find_all yet
        code_elements = self.d.xpath(code_xpath).all()
        self.logger.debug(f"Found {len(code_elements)} potential code elements.")
        for el in code_elements:
            try:
                # Get text using interactions layer for consistency (even if getting from loop)
                # text = self.interactions.get_element_text(el.get_xpath(), timeout=1)
                text = el.info.get("text")  # Direct info access might be faster here
                if text and text.isdigit() and len(text) == 6:
                    self.logger.info(f"✅ Found 2FA code in email detail view: {text}")
                    return text
            except Exception as e:
                self.logger.warning(f"Error checking potential code element: {e}")
                continue

        self.logger.error(
            "❌ Found potential code elements, but none contained a valid 6-digit code."
        )
        return None

    def navigate_to_communities_and_extract_code(self) -> Optional[str]:
        """Navigates to the 'Communities' tab (if available) and tries to extract the code."""
        self.logger.info(
            "🛖 Attempting to navigate to 'Communities' tab to find code..."
        )

        # 1. Open Sidebar
        if not self.interactions.click_by_xpath(
            self.firefox_xpaths.email_sidebar_button, timeout=10
        ):
            self.logger.error("❌ Failed to find/click sidebar button.")
            return None
        self.logger.info("Opened sidebar.")
        time.sleep(1.5)

        # 2. Verify Sidebar is Open (check for known element inside)
        if not self.interactions.wait_for_element_appear(
            self.firefox_xpaths.email_sidebar_write_message_button, timeout=5
        ):
            self.logger.warning(
                "Sidebar verification element not found. Retrying sidebar open..."
            )
            if not self.interactions.click_by_xpath(
                self.firefox_xpaths.email_sidebar_button, timeout=5
            ):
                self.logger.error("❌ Failed to open sidebar on retry.")
                return None
            time.sleep(1.5)
            if not self.interactions.wait_for_element_appear(
                self.firefox_xpaths.email_sidebar_write_message_button, timeout=5
            ):
                self.logger.error("❌ Sidebar failed to open/verify after retries.")
                return None
        self.logger.info("Sidebar verified open.")

        # 3. Click Communities Button
        if not self.interactions.click_by_xpath(
            self.firefox_xpaths.email_sidebar_communities_button, timeout=10
        ):
            self.logger.error(
                "❌ Failed to find/click 'Communities' button in sidebar."
            )
            # Press back to close sidebar before returning
            self.interactions.device.press("back")
            return None
        self.logger.info("✅ Clicked 'Communities' tab. Waiting for view...")
        time.sleep(3)  # Wait for Communities view to load

        # 4. Search for 2FA Email Text within Communities View
        # This relies on finding specific text content within the view.
        # Let's try finding any view containing the characteristic IG login attempt text.
        # Using a broad search within the current view.
        self.logger.info("Searching for IG 2FA email text in Communities view...")
        # TODO: Refine this XPath if possible - searching all Views can be slow.
        # Consider adding a container specific to the Communities view if identifiable.
        # Smart search might be too slow here, using specific text content search
        keyword_xpath = "//*[contains(@text, 'tried to log in to your Instagram account') or contains(@content-desc, 'tried to log in to your Instagram account')]"

        # Wait briefly for the text to appear
        if not self.interactions.wait_for_element_appear(keyword_xpath, timeout=10):
            self.logger.warning(
                "Did not find characteristic IG email text in Communities view."
            )
            # Press back to potentially return to main inbox
            self.interactions.device.press("back")
            time.sleep(1)
            return None

        # Found the text, now try to extract code from nearby elements or the element itself
        ig_email_elements = self.d.xpath(keyword_xpath).all()
        self.logger.info(
            f"Found {len(ig_email_elements)} elements containing IG login text."
        )

        for element in ig_email_elements:
            try:
                full_text = ""
                # Try getting text directly from the element
                info = element.info
                el_text = info.get("text") or info.get("content-desc", "")
                full_text += el_text + " "

                # Also check siblings or children if necessary (more complex)
                # This part is highly dependent on the actual structure

                self.logger.debug(f"Checking text block: {full_text[:150]}...")
                code = self._extract_code_from_text(full_text)
                if code:
                    self.logger.info(
                        f"✅ Extracted 2FA code from Communities tab: {code}"
                    )
                    # Press back to exit Communities before returning code
                    self.interactions.device.press("back")
                    time.sleep(1)
                    return code
            except Exception as e:
                self.logger.warning(
                    f"Error processing element in Communities view: {e}"
                )
                continue

        self.logger.warning(
            "❌ Found IG email text in Communities, but couldn't extract 6-digit code."
        )
        # Press back to exit Communities view
        self.interactions.device.press("back")
        time.sleep(1)
        return None

    def logout(self) -> bool:
        """Logs out of the op.pl email account."""
        self.logger.info("🚪 Attempting to log out of email...")
        try:
            # 1. Open account menu
            if not self.interactions.click_by_xpath(
                self.firefox_xpaths.email_account_menu_button, timeout=10
            ):
                self.logger.warning("⚠️ Account menu button not found.")
                # Try opening sidebar first? Sometimes logout is there.
                if self.interactions.click_by_xpath(
                    self.firefox_xpaths.email_sidebar_button, timeout=5
                ):
                    self.logger.info("Opened sidebar as fallback for logout...")
                    time.sleep(1)
                else:
                    self.logger.error(
                        "❌ Could not find Account Menu or Sidebar button."
                    )
                    return False

            # 2. Find and click Logout button (could be in main menu or sidebar)
            time.sleep(1)  # Wait for menu/sidebar animation
            if self.interactions.click_by_xpath(
                self.firefox_xpaths.email_logout_button, timeout=7
            ):
                self.logger.info("✅ Clicked logout button.")
                time.sleep(3)  # Wait for logout process
                # Verify logout? Check if login fields reappear?
                if self.interactions.wait_for_element_appear(
                    self.firefox_xpaths.email_login_email_field, 5
                ):
                    self.logger.info("✅ Logout confirmed (login field appeared).")
                    return True
                else:
                    self.logger.warning(
                        "⚠️ Logout clicked, but login field did not reappear."
                    )
                    # Assume success for now, but flag potential issue.
                    return True  # Or False if strict verification needed
            else:
                self.logger.error("❌ Logout button not found in menu/sidebar.")
                # Try pressing back to close menu/sidebar if stuck
                self.d.press("back")
                return False
        except Exception as e:
            self.logger.error(f"💥 Error logging out of email: {e}", exc_info=True)
            return False


class TwoFactorTokenRetriever:
    """Orchestrates the retrieval of the 2FA code from the email."""

    def __init__(
        self,
        email_navigator: EmailNavigation,  # Pass the navigator instance
        logger_instance,  # Pass logger
    ):
        # Removed direct dependencies on d, interactions etc. - uses email_navigator
        self.email_nav = email_navigator
        self.logger = logger_instance  # Use passed logger
        # self.is_logged_in = False # State likely managed by Firefox2FAFlow

    def get_2fa_code_from_email(self, max_retries=2) -> Optional[str]:
        """
        Attempts to retrieve the 2FA code using multiple strategies:
        1. Communities Tab (if applicable for the email client)
        2. Email Preview List (Inbox view)
        3. Opening Email Detail View
        Includes retries with delays.
        """
        self.logger.info("🔑 Starting 2FA code retrieval process from email...")

        for attempt in range(1, max_retries + 1):
            self.logger.info(
                f"--- 2FA Code Retrieval Attempt {attempt}/{max_retries} ---"
            )

            # Strategy 1: Try Communities Tab first (if implemented and relevant)
            # Note: This might be specific to op.pl's mobile web interface.
            # Disable if not reliable or applicable.
            # code = self.email_nav.navigate_to_communities_and_extract_code()
            # if code:
            #     self.logger.info("✅ Code found via Communities Tab.")
            #     return code
            # self.logger.info("Code not found in Communities Tab (or skipped).")
            # time.sleep(1) # Small delay before next strategy

            # Strategy 2: Scan Email Previews in Inbox
            code = self.email_nav.find_code_in_email_preview()
            if code:
                self.logger.info("✅ Code found via Email Preview Scan.")
                return code
            self.logger.info("Code not found in email previews.")
            time.sleep(1)

            # Strategy 3: Open Top Email and Scan Detail View
            code = self.email_nav.open_email_and_extract_code_from_detail_view()
            if code:
                self.logger.info("✅ Code found via Email Detail View.")
                return code
            self.logger.info("Code not found after opening email detail view.")

            if attempt < max_retries:
                wait_time = 3 * attempt
                self.logger.warning(
                    f"⚠️ Code not found in attempt {attempt}. Waiting {wait_time}s before retrying..."
                )
                # Optional: Add a refresh action here? (e.g., pull-to-refresh)
                # self.email_nav.interactions.swipe_down_humanlike() # Example refresh gesture
                time.sleep(wait_time)
            else:
                self.logger.error(
                    "❌ Failed to retrieve 2FA code after all strategies and retries."
                )

        return None


class Firefox2FAFlow:
    """Orchestrates the entire flow: setup, login, 2FA retrieval, cleanup."""

    def __init__(
        self,
        email: str,
        password: str,
        record_id: str,
        base_id: str,
        table_id: str,
        firefox_package: str = DEFAULT_FIREFOX_PACKAGE,
    ):
        self.email = email
        self.password = password
        self.record_id = record_id
        self.base_id = base_id
        self.table_id = table_id
        self.firefox_package = firefox_package

        # Centralized instance creation
        self.logger = setup_logger(self.__class__.__name__)
        self.d: Optional[u2.Device] = None
        self.firefox_xpaths: Optional[FirefoxEmailXPaths] = None
        self.interactions: Optional[InstagramInteractions] = None
        self.popup_handler: Optional[PopupHandler] = None
        self.stealth_typer: Optional[StealthTyper] = None
        self.airtable: Optional[AirtableClient] = None
        self.firefox_manager: Optional[FirefoxManager] = None
        self._initialized = False

    def _initialize_resources(self) -> bool:
        """Connects to device and initializes helper instances."""
        if self._initialized:
            return True
        try:
            self.logger.info("🔧 Initializing resources...")
            self.d = u2.connect()
            self.logger.info(f"📱 Connected to device: {self.d.serial}")

            self.firefox_xpaths = FirefoxEmailXPaths(
                firefox_package=self.firefox_package
            )
            # Provide package name for interactions instance specific to Firefox
            self.interactions = InstagramInteractions(
                device=self.d, app_package=self.firefox_package
            )
            self.popup_handler = PopupHandler(
                driver=self.d, config_path=str(POPUP_CONFIG_PATH)
            )
            self.stealth_typer = StealthTyper(device_id=self.d.serial)
            self.airtable = AirtableClient(base_id=self.base_id, table_id=self.table_id)

            # Pass shared instances to FirefoxManager
            self.firefox_manager = FirefoxManager(
                device=self.d,
                interactions=self.interactions,
                firefox_xpaths=self.firefox_xpaths,
                stealth_typer=self.stealth_typer,
                popup_handler=self.popup_handler,
            )

            # Register watchers AFTER initializing popup_handler
            self.popup_handler.register_watchers()
            # Set context for suspension handler (example)
            # self.popup_handler.set_context(airtable_client=self.airtable, record_id=self.record_id, ...)

            self.logger.info("✅ Resources initialized successfully.")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"💥 Failed to initialize resources: {e}", exc_info=True)
            self._initialized = False
            return False

    def _cleanup_resources(self):
        """Stops watchers and closes Firefox."""
        self.logger.info("🧹 Cleaning up resources...")
        if self.popup_handler:
            self.popup_handler.stop_watcher_loop()  # Stop background loop if started
            # Ensure watchers registered by this instance are stopped/removed
            try:
                self.d.watcher.stop()
                self.d.watcher.remove()  # Remove all watchers associated with this connection
                self.logger.info("UIA2 Watchers stopped and removed.")
            except Exception as e:
                self.logger.error(f"Error stopping/removing uia2 watchers: {e}")

        if self.firefox_manager:
            self.firefox_manager.close_firefox()
        else:
            # Attempt direct close if manager wasn't created
            if self.interactions:
                self.logger.warning(
                    "FirefoxManager not available, attempting direct close."
                )
                self.interactions.close_app()

        self.logger.info("✅ Cleanup complete.")

    def run(self) -> Optional[str]:
        """Executes the entire Firefox 2FA code retrieval process."""
        if not self._initialize_resources():
            return None

        code = None  # Initialize code to None

        try:
            self.logger.info(f"🚀 Starting Firefox 2FA extraction for {self.email}...")

            # 1. Launch Firefox and navigate to op.pl
            # TODO: Determine the correct starting URL for op.pl login
            login_url = "poczta.op.pl/login/form.html"  # Example - needs verification
            if not self.firefox_manager.launch_and_navigate(login_url):
                self.logger.error(
                    "❌ Failed to launch Firefox and navigate to login page."
                )
                return None  # Critical failure

            # 2. Perform email login
            email_login_handler = EmailLogin(
                device=self.d,
                interactions=self.interactions,
                firefox_xpaths=self.firefox_xpaths,
                stealth_typer=self.stealth_typer,
                popup_handler=self.popup_handler,
                email_address=self.email,
                email_password=self.password,
            )
            if not email_login_handler.perform_op_login():
                self.logger.error("❌ op.pl login failed.")
                return None  # Login failure

            self.logger.info(
                "✅ op.pl login successful. Proceeding to 2FA code retrieval."
            )
            time.sleep(2)  # Pause before starting code search

            # 3. Retrieve 2FA code
            email_navigator = EmailNavigation(
                device=self.d,
                interactions=self.interactions,
                firefox_xpaths=self.firefox_xpaths,
                popup_handler=self.popup_handler,
            )
            token_retriever = TwoFactorTokenRetriever(
                email_navigator=email_navigator,
                logger_instance=self.logger,  # Pass logger
            )

            code = token_retriever.get_2fa_code_from_email(max_retries=2)

            if code:
                self.logger.info(f"✅✅ Successfully retrieved 2FA code: {code}")
                # Optionally logout after getting the code?
                # email_navigator.logout()
            else:
                self.logger.error("❌❌ Failed to retrieve 2FA code from email.")
                # Take screenshot on failure?
                # self.d.screenshot("failure_screenshot_2fa_retrieval.png")

            # 4. Trigger New Identity (Only if code retrieval was successful?)
            # Decide if this runs even on failure or only success. Currently runs only on success.
            if code:
                self.logger.info("🔁 Triggering new identity reset...")
                if new_identity(self.d):  # Pass the device object
                    self.logger.info("✅ New identity successfully triggered.")
                else:
                    self.logger.warning("⚠️ Failed to trigger new identity.")
            else:
                self.logger.warning(
                    "Skipping new identity trigger due to 2FA code retrieval failure."
                )

            return code  # Return the code (or None if failed)

        except Exception as e:
            self.logger.error(
                f"💥 Unhandled exception during Firefox2FAFlow run: {e}", exc_info=True
            )
            # Take screenshot on major error?
            # if self.d: self.d.screenshot("error_screenshot_firefox2fa.png")
            return None  # Ensure None is returned on error
        finally:
            # Cleanup resources regardless of success or failure
            self._cleanup_resources()


# --- Main Execution Block ---
if __name__ == "__main__":
    try:
        module_logger.info("--- Starting Email 2FA Code Retrieval Process ---")

        # Pull env vars for Airtable config
        base_id = os.getenv("AIRTABLE_BASE_ID")
        table_id = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")
        view_id = os.getenv(
            "IG_ARMY_UNUSED_VIEW_ID"
        )  # Make sure this view provides email+password

        if not all([base_id, table_id, view_id]):
            raise ValueError(
                "❌ Missing required Airtable environment variables (BASE_ID, TABLE_ID, VIEW_ID)."
            )

        module_logger.info("🔍 Fetching email credentials from Airtable...")
        client = AirtableClient()  # No need to set base/table ID here if passed to Flow
        account_data = client.get_single_active_account(
            base_id=base_id, table_id=table_id, view_id=view_id
        )

        if not account_data:
            raise Exception("❌ No active account found in Airtable view specified.")

        fields = account_data.get("fields", {})
        record_id = account_data.get("id")
        email = fields.get("Email")
        password = fields.get(
            "Email Password"
        )  # Ensure this field name matches Airtable

        if not email or not password or not record_id:
            raise Exception(
                f"❌ Missing critical data (Email, Email Password, or record ID) in Airtable record: {record_id}"
            )

        module_logger.info(f"✅ Using email: {email} (Record ID: {record_id})")

        # Initialize and run the flow
        flow = Firefox2FAFlow(
            email=email,
            password=password,
            record_id=record_id,
            base_id=base_id,
            table_id=table_id,
            # firefox_package="org.mozilla.firefox" # Optional: Override default if needed
        )

        retrieved_code = flow.run()

        if retrieved_code:
            module_logger.info(
                f"🏁 Process finished successfully. Retrieved Code: {retrieved_code}"
            )
            # TODO: What should happen with the code? Print it? Update Airtable? Return it?
            # Example: Update Airtable
            # update_success = client.update_record_fields(record_id, {"2FA Code": retrieved_code}, base_id=base_id, table_id=table_id)
            # module_logger.info(f"Airtable update result: {update_success}")
        else:
            module_logger.error("❌ Process finished: Failed to retrieve 2FA code.")

    except Exception as e:
        module_logger.error(f"💥 Main execution failed: {e}", exc_info=True)

    finally:
        module_logger.info("--- Email 2FA Code Retrieval Process Ended ---")
