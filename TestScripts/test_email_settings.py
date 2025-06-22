import re

import pytest
from playwright.sync_api import Page, TimeoutError, expect

clients = [{"email": "langstonfitzpatrick@op.pl", "password": "khan567996"}]


@pytest.mark.parametrize("client_data", clients)
def test_activate_imap_and_pop3(client_data: dict, page: Page):
    """
    This test logs into a client's email account, checks the status of
    IMAP and POP3, enables them if they are off, and reports the final state.
    """
    # 1. Navigate and Log In
    page.goto(
        "https://konto.onet.pl/en/signin?state=https%3A%2F%2Fpoczta.onet.pl%2F&client_id=poczta.onet.pl.front.onetapi.pl"
    )
    page.get_by_role("button", name="accept and close").click()
    page.get_by_role("textbox", name="E-mail address").fill(client_data["email"])
    page.get_by_role("button", name="Next").click()
    page.get_by_role("textbox", name="Password").fill(client_data["password"])
    page.get_by_role("button", name="Log in", exact=True).click()

    # 2. Handle potential MFA/post-login screen
    try:
        skip_button = page.get_by_role("button", name="Skip", exact=True)
        skip_button.wait_for(timeout=10000)
        print("MFA/Setup screen detected. Clicking 'Skip'.")
        skip_button.click()
    except TimeoutError:
        print("MFA/Setup screen not found, proceeding directly.")

    # 3. Navigate from the main portal to the settings page
    expect(page).to_have_url(re.compile(r"https://poczta.onet.pl/.*"), timeout=20000)
    print("Successfully logged in. Clicking settings icon...")
    page.get_by_role("button", name="").click()

    print("Waiting for the 'Ustawienia' (Settings) link to appear...")
    settings_link = page.get_by_role("link", name=re.compile("Ustawienia"))
    expect(settings_link).to_be_visible(timeout=10000)
    print("Settings link is visible. Clicking it now.")
    settings_link.click()

    # 4. Verify navigation to the new settings subdomain
    print("Verifying navigation to the new settings subdomain...")
    expect(page).to_have_url(
        re.compile(r".*ustawienia.poczta.onet.pl.*"), timeout=15000
    )
    print("Successfully navigated to the main settings area.")

    # 5. Click the "Konto główne" BUTTON, but only if necessary.
    if not page.locator("#popCheck").is_visible(timeout=5000):
        print(
            "'Konto główne' options are not visible. Clicking the button to reveal them..."
        )
        page.get_by_role("button", name="Konto główne").click()
    else:
        print("POP3/IMAP options are already visible.")

    # 6. FINAL LOGIC: Check status and enable toggles if they are off
    print("\n--- Verifying POP3 and IMAP Settings ---")

    # Define locators for the checkboxes using their unique IDs
    pop3_toggle = page.locator("#popCheck")
    imap_toggle = page.locator("#imapCheck")

    # Wait for the elements to be visible before interacting
    expect(pop3_toggle).to_be_visible(timeout=10000)
    expect(imap_toggle).to_be_visible(timeout=10000)

    # Check and handle POP3 status
    if pop3_toggle.is_checked():
        print("✅ POP3 is already ON.")
    else:
        print("❌ POP3 is OFF. Enabling it now...")
        # Force the click because a styled <span> intercepts pointer events
        pop3_toggle.click(force=True)
        expect(pop3_toggle).to_be_checked()  # Wait and verify it was turned on
        print("✅ POP3 has been successfully turned ON.")

    # Check and handle IMAP status
    if imap_toggle.is_checked():
        print("✅ IMAP is already ON.")
    else:
        print("❌ IMAP is OFF. Enabling it now...")
        # Force the click because a styled <span> intercepts pointer events
        imap_toggle.click(force=True)
        expect(imap_toggle).to_be_checked()  # Wait and verify it was turned on
        print("✅ IMAP has been successfully turned ON.")

    print(
        f"\nSUCCESS: IMAP and POP3 configuration completed for {client_data['email']}"
    )
