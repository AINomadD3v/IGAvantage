# activate_imap.py

import re

from playwright.sync_api import TimeoutError, expect, sync_playwright


def activate_email_protocols(client_data: dict, headless: bool = False) -> dict:
    """
    Logs into an Onet email account, enables IMAP and POP3 if they are
    disabled, and returns a status dictionary.

    Args:
        client_data: A dictionary with "email" and "password" keys.
        headless: If True, runs the browser in the background. Defaults to False.

    Returns:
        A dictionary with "status" and "message" keys.
    """
    print(f"--- Starting activation process for {client_data['email']} ---")

    try:
        with sync_playwright() as p:
            # 1. Launch browser and create a new page
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            # 2. Navigate and Log In (All the logic from your test)
            page.goto(
                "https://konto.onet.pl/en/signin?state=https%3A%2F%2Fpoczta.onet.pl%2F&client_id=poczta.onet.pl.front.onetapi.pl"
            )
            page.get_by_role("button", name="accept and close").click()
            page.get_by_role("textbox", name="E-mail address").fill(
                client_data["email"]
            )
            page.get_by_role("button", name="Next").click()
            page.get_by_role("textbox", name="Password").fill(client_data["password"])
            page.get_by_role("button", name="Log in", exact=True).click()

            # Handle potential MFA/post-login screen
            try:
                skip_button = page.get_by_role("button", name="Skip", exact=True)
                skip_button.wait_for(timeout=10000)
                print("MFA/Setup screen detected. Clicking 'Skip'.")
                skip_button.click()
            except TimeoutError:
                print("MFA/Setup screen not found, proceeding directly.")

            # Navigate to settings
            expect(page).to_have_url(
                re.compile(r"https://poczta.onet.pl/.*"), timeout=20000
            )
            page.get_by_role("button", name="").click()
            settings_link = page.get_by_role("link", name=re.compile("Ustawienia"))
            expect(settings_link).to_be_visible(timeout=10000)
            settings_link.click()
            expect(page).to_have_url(
                re.compile(r".*ustawienia.poczta.onet.pl.*"), timeout=15000
            )

            # Reveal main account settings if necessary
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

            # 4. Success: close browser and return success status
            browser.close()
            success_message = f"SUCCESS: IMAP and POP3 configuration complete for {client_data['email']}"
            print(success_message)
            return {"status": "success", "message": success_message}

    except Exception as e:
        # 5. Failure: Catch any error and return a failure status
        error_message = f"ERROR: An error occurred for {client_data['email']}: {e}"
        print(error_message)
        return {"status": "error", "message": error_message}


# This block allows you to run this file directly for testing
if __name__ == "__main__":
    # Example client data
    single_client = {"email": "langstonfitzpatrick@op.pl", "password": "khan567996"}

    # Set headless=False to watch it run, or True to run in the background
    result = activate_email_protocols(single_client, headless=False)

    print("\n--- SCRIPT FINISHED ---")
    print(f"Final Status: {result['status']}")
    print(f"Final Message: {result['message']}")
