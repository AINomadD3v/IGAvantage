# activate_imap.py

import concurrent.futures
import logging
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
    HEADLESS_MODE: bool = False
    ACCOUNTS_TO_PROCESS: int = 3
    MAX_WORKERS: int = 1


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
                        "message": str(e),
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
                browser = p.chromium.launch(headless=self.config.HEADLESS_MODE)
                page = browser.new_page()

                # Resize the browser window to ensure all UI elements are in view
                page.set_viewport_size(
                    {"width": 1920, "height": 1080}
                )  # Adjust to desired resolution

                page.goto(self.config.LOGIN_URL)

                self._handle_cookie_banner(page)
                self._perform_login(page, account_data)

                # Immediately handle all potential pop-up screens after login
                self._handle_post_login_sequence(page)

                # Now that pop-ups are handled, we can proceed to the inbox
                self._navigate_and_enable_protocols(page)

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

    def _navigate_and_enable_protocols(self, page: Page):
        """Navigates to settings from the inbox and toggles IMAP/POP3."""
        # Now we can safely expect to be on the inbox page
        expect(page).to_have_url(
            re.compile(r"https://poczta.onet.pl/.*"), timeout=25000
        )
        logging.info("Successfully landed on inbox page. Navigating to settings...")

        page.get_by_role("button", name="").click()
        page.get_by_role("link", name=re.compile(r"Ustawienia")).click()
        expect(page).to_have_url(
            re.compile(r".*ustawienia.poczta.onet.pl.*"), timeout=15000
        )

        if not page.locator("#popCheck").is_visible(timeout=5000):
            page.get_by_role("button", name="Konto główne").click()

            # 3. Check and Enable Protocols
            pop3_toggle = page.locator("#popCheck")
            imap_toggle = page.locator("#imapCheck")
            expect(pop3_toggle).to_be_visible(timeout=10000)

            if not pop3_toggle.is_checked():
                print("POP3 is OFF. Enabling it now...")
                pop3_toggle.click(force=True)
                expect(pop3_toggle).to_be_checked()
                print("POP3 has been successfully turned ON.")
            else:
                print("POP3 is already ON.")

            if not imap_toggle.is_checked():
                print("IMAP is OFF. Enabling it now...")
                imap_toggle.click(force=True)
                expect(imap_toggle).to_be_checked()
                print("IMAP has been successfully turned ON.")
            else:
                print("IMAP is already ON.")


if __name__ == "__main__":
    try:
        config = Config()
        activator = OnetImapActivator(config)
        activator.run()
    except Exception as e:
        logging.critical(
            f"A critical error occurred at the application level: {e}", exc_info=True
        )
