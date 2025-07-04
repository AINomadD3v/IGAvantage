# activate_imap.py

import concurrent.futures
import logging
import random
import re
from dataclasses import dataclass

# Assumes your AirtableClient class is in a file named imap_airtable.py
from imap_airtable import AirtableClient
from playwright.sync_api import Page, TimeoutError, expect, sync_playwright

# --- 1. Professional Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# --- 2. Centralized Configuration ---
@dataclass(frozen=True)
class Config:
    """Holds all script settings in one place."""

    LOGIN_URL: str = (
        "https://konto.onet.pl/en/signin?state=https%3A%2F%2Fpoczta.onet.pl%2F&client_id=poczta.onet.pl.front.onetapi.pl"
    )
    HEADLESS_MODE: bool = True
    ACCOUNTS_TO_PROCESS: int = 10
    MAX_WORKERS: int = 4


class OnetImapActivator:
    """
    Manages the end-to-end process of activating IMAP for Onet email accounts.
    """

    def __init__(self, config: Config):
        self.config = config
        self.airtable_client = AirtableClient()
        logging.info("Onet IMAP Activator initialized.")

    def run(self):
        logging.info(f"Starting activation run. Config: {self.config}")
        accounts = self._fetch_accounts()
        if not accounts:
            logging.warning("No accounts found to process. Run finished.")
            return
        self._process_accounts_concurrently(accounts)
        logging.info("Activation run finished.")

    def _fetch_accounts(self) -> list[dict]:
        logging.info(f"Fetching up to {self.config.ACCOUNTS_TO_PROCESS} accounts...")
        try:
            accounts = self.airtable_client.get_imap_accounts(
                max_records=self.config.ACCOUNTS_TO_PROCESS
            )
            logging.info(f"Found {len(accounts)} accounts to process.")
            return accounts
        except Exception as e:
            logging.error(f"Failed to fetch accounts from Airtable: {e}", exc_info=True)
            return []

    def _process_accounts_concurrently(self, accounts: list[dict]):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.MAX_WORKERS, thread_name_prefix="Activator"
        ) as executor:
            future_to_account = {
                executor.submit(self._activate_single_account, account): account
                for account in accounts
            }
            for future in concurrent.futures.as_completed(future_to_account):
                account = future_to_account[future]
                try:
                    result = future.result()
                    self._update_airtable_record(result)
                except Exception as e:
                    logging.error(
                        f"A fatal error occurred processing {account.get('email', 'N/A')}: {e}",
                        exc_info=True,
                    )
                    error_result = {
                        "status": "error",
                        "account": account,
                    }
                    self._update_airtable_record(error_result)

    def _update_airtable_record(self, result: dict):
        account = result["account"]
        record_id = account["record_id"]
        email = account["email"]
        logging.info(f"Updating Airtable for {email} with status: {result['status']}")

        if result["status"] == "success":
            update_data = {"IMAP Status": "On"}
        else:
            # FIX: Only update fields that exist in your Airtable.
            update_data = {"IMAP Status": "Error"}

        self.airtable_client.update_record_fields(record_id, update_data)

    def _activate_single_account(self, account_data: dict) -> dict:
        """Core logic to process one email account."""
        email = account_data["email"]
        try:
            with sync_playwright() as p:
                # -- STEP 1: Random User-Agent to avoid detection
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                ]
                user_agent = random.choice(user_agents)

                # -- STEP 2: Realistic browser fingerprint
                browser = p.chromium.launch(headless=self.config.HEADLESS_MODE)
                context = browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                    timezone_id="Europe/Warsaw",
                    geolocation={"longitude": 19.9449799, "latitude": 50.0646501},
                    permissions=["geolocation"],
                )
                page = context.new_page()

                # -- STEP 3: Stealth patch common bot fingerprints
                page.add_init_script(
                    """    // Stealth patch: WebGL
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'NVIDIA Corporation';
        if (parameter === 37446) return 'NVIDIA GeForce GTX 1050/PCIe/SSE2';
        return getParameter(parameter);
    };

    // Stealth patch: navigator.mediaDevices
    navigator.mediaDevices.enumerateDevices = async () => [{
        kind: 'videoinput',
        label: 'Built-in Camera',
        deviceId: 'abcd',
        groupId: '1234'
    }];

    // Stealth patch: screen resolution lying
    Object.defineProperty(window.screen, 'width', { get: () => 1280 });
    Object.defineProperty(window.screen, 'height', { get: () => 800 });

    // Stealth patch: HardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });

    // Stealth patch: Permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );"""
                )

                # Resize (just to be sure; matches viewport above)
                page.set_viewport_size({"width": 1280, "height": 800})

                # Fresh load
                page.goto(self.config.LOGIN_URL)

                self._handle_cookie_banner(page)
                self._perform_login(page, account_data)
                self._handle_post_login_sequence(page)
                self._navigate_and_enable_protocols(page, email)

                context.close()
                browser.close()

                success_message = f"IMAP and POP3 configuration complete for {email}"
                logging.info(success_message)
                return {
                    "status": "success",
                    "message": success_message,
                    "account": account_data,
                }

        except Exception as e:
            error_message = (
                f"Failed during activation for {email}: {type(e).__name__} - {e}"
            )
            logging.error(error_message, exc_info=False)
            return {
                "status": "error",
                "message": error_message,
                "account": account_data,
            }

    def _handle_cookie_banner(self, page: Page):
        cookie_button_pl = page.get_by_role("button", name="Przejdź do serwisu")
        cookie_button_en = page.get_by_role("button", name="accept and close")
        try:
            expect(cookie_button_pl.or_(cookie_button_en)).to_be_visible(timeout=10000)
            if cookie_button_pl.is_visible():
                cookie_button_pl.click()
            else:
                cookie_button_en.click()
        except TimeoutError:
            logging.warning("No cookie banner found, proceeding.")

    def _perform_login(self, page: Page, account_data: dict):
        email_input = page.get_by_role("textbox", name="E-mail address")
        expect(email_input).to_be_visible(timeout=15000)
        email_input.fill(account_data["email"])
        page.get_by_role("button", name="Next").click()
        page.get_by_role("textbox", name="Password").fill(account_data["password"])
        page.get_by_role("button", name="Log in", exact=True).click()

    def _handle_post_login_sequence(self, page: Page):
        """
        Handles the full sequence of potential pop-ups after login.
        This respects the logic of your original script.
        """
        logging.info("Checking for post-login pop-up sequence...")

        # Screen 1: The MFA / "Trusted Device" page
        if "konto.onet.pl/mfa" in page.url:
            logging.warning(
                "MFA screen detected. Attempting to click 'Remind me later'."
            )
            try:
                page.get_by_role("button", name="Remind me later").click(timeout=5000)
            except TimeoutError:
                raise Exception("MFA screen encountered but could not be bypassed.")

        # Screen 2: The "Skip" button page (from your original script)
        try:
            skip_button = page.get_by_role("button", name="Skip", exact=True)
            skip_button.click(timeout=10000)
            logging.info("Clicked 'Skip' button on post-login screen.")
        except TimeoutError:
            pass  # This screen is optional

        # Screen 3: The "Next" button page (from your original script)
        try:
            next_button = page.get_by_role("button", name="Next", exact=True)
            next_button.click(timeout=5000)
            logging.info("Clicked 'Next' button on post-login screen.")
        except TimeoutError:
            pass  # This screen is also optional

    def _navigate_and_enable_protocols(self, page: Page, email: str):
        """Navigates to settings from the inbox and toggles IMAP/POP3."""
        logging.info("Navigating to settings...")
        try:
            page.get_by_role("button", name="").click()
            page.get_by_role(
                "link", name=re.compile(r"Ustawienia", re.IGNORECASE)
            ).click()
            expect(page).to_have_url(
                re.compile(r".*ustawienia.poczta.onet.pl.*"), timeout=15000
            )
            logging.info("Navigated to settings page.")

            # This check remains valid.
            if not page.locator('label[for="popCheck"]').is_visible(timeout=5000):
                logging.info(
                    "Settings not immediately visible, clicking 'Konto główne'..."
                )
                page.get_by_role("button", name="Konto główne").click()

            # --- START OF MODIFIED SECTION ---

            # 1. CORRECTED LOCATORS: Target the <label> as the container.
            pop3_container = page.locator('label[for="popCheck"]')
            imap_container = page.locator('label[for="imapCheck"]')

            # 2. Check and Enable POP3 with Text Verification
            logging.info("Checking POP3 status...")
            expect(pop3_container).to_be_visible(timeout=10000)

            # Get text content and check for None to prevent type errors.
            pop3_status = pop3_container.text_content()
            if pop3_status and "Wyłączony" in pop3_status:
                logging.info("POP3 is OFF. Enabling it now...")
                pop3_container.dispatch_event("click")
                # Verify the text changes to "On" inside the container.
                expect(
                    pop3_container.locator('span:text-is("Włączony")')
                ).to_be_visible(timeout=10000)
                logging.info("POP3 has been successfully turned ON and verified.")
                page.wait_for_timeout(5000)  # Wait 2 seconds for the setting to save
            else:
                logging.info("POP3 is already ON.")

            # 3. Check and Enable IMAP with Text Verification
            logging.info("Checking IMAP status...")
            expect(imap_container).to_be_visible(timeout=10000)

            # Get text content and check for None to prevent type errors.
            imap_status = imap_container.text_content()
            if imap_status and "Wyłączony" in imap_status:
                logging.info("IMAP is OFF. Enabling it now...")
                imap_container.dispatch_event("click")
                # Verify the text changes to "On" inside the container.
                expect(
                    imap_container.locator('span:text-is("Włączony")')
                ).to_be_visible(timeout=10000)
                logging.info("IMAP has been successfully turned ON and verified.")
                page.wait_for_timeout(5000)  # Wait 2 seconds for the setting to save
            else:
                logging.info("IMAP is already ON.")
            # --- END OF MODIFIED SECTION ---
        except Exception as e:
            # The main exception handler in _activate_single_account will catch this
            # and trigger the DOM dump.
            logging.error(f"An error occurred on the settings page for {email}.")
            raise e


if __name__ == "__main__":
    try:
        config = Config()
        activator = OnetImapActivator(config)
        activator.run()
    except Exception as e:
        logging.critical(
            f"A critical error occurred at the application level: {e}", exc_info=True
        )
