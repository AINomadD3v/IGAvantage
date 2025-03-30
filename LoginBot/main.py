import uiautomator2 as u2
import os
import subprocess
import time
from get_code import FirefoxAutomation, EmailNavigation, TwoFactorTokenRetriever, UIHelper
from instagram_automation import InstagramAutomation
from Shared.stealth_typing import StealthTyper
from Shared.logger_config import setup_logger
from Shared.airtable_manager import AirtableClient
from new_identity import new_identity


logger = setup_logger(__name__)

def handle_save_login_prompt(d, helper, username=None, timeout=8):
    try:
        keywords = ["save your login info", "save login", "zapisz dane logowania"]
        logger.info("Checking for post-login save prompt...")

        prompt_xpath = helper.find_prompt_xpath(keywords, timeout=timeout)
        if not prompt_xpath:
            logger.info("No save prompt appeared")
            return

        # Now search for the "Save" or "Not Now" buttons nearby
        for button_text in ["Save", "Zapisz", "Not now", "Nie teraz"]:
            btn_xpath = f'//android.widget.Button[contains(@text, "{button_text}")] | //android.widget.Button[contains(@content-desc, "{button_text}")]'
            if helper.wait_for_xpath(btn_xpath, timeout=5):
                if d.xpath(btn_xpath).click_exists(timeout=3):
                    logger.info(f"✅ Clicked button: {button_text}")
                    time.sleep(2)
                    return
                else:
                    logger.warning(f"⚠️ Button found but click failed: {button_text}")

        logger.warning("⚠️ Prompt appeared but no matching button was clicked")

    except Exception as e:
        logger.error(f"Error handling save login prompt: {e}")

        # TODO Clean up function, move to using the watchers for popups and pull out logic for 2fa

def handle_login_and_2fa(d, username, password, package_name, email, email_password, airtable_client, record_id, base_id, table_name):
    try:
        instagram = InstagramAutomation(d, package_name)
        login_result = instagram.login_with_ocr(username, password)

        if d.xpath('//android.widget.TextView[@resource-id="android:id/message"]').exists:
            msg = d.xpath('//android.widget.TextView[@resource-id="android:id/message"]').get().attrib.get('text', '')
            logger.error("Detected error message: %s", msg)
            return "login_failed"

        if d.xpath('//android.view.View[contains(@text, "incorrect")]').exists:
            logger.error("Detected incorrect password error")
            return "login_failed"

        if not login_result:
            logger.error("OCR-based login process failed")
            return "login_failed"

        airtable_client.update_record(base_id, table_name, record_id, {"Automation Used?": True})
        logger.info("2FA screen detected. Proceeding to retrieve 2FA code via Firefox")

        firefox = FirefoxAutomation(email=email, password=email_password)
        if not firefox.launch_firefox():
            logger.error("❌ Failed to launch Firefox")
            return "firefox_launch_failed"

        if not firefox.navigate_to_url("op.pl"):
            logger.error("❌ Failed to navigate to op.pl")
            return "oppl_navigation_failed"

        if not firefox.perform_login_sequence():
            logger.error("❌ Firefox login sequence failed")
            return "firefox_login_failed"

        verification_code = firefox.token_retriever.get_2fa_code()
        if not verification_code:
            logger.error("❌ Failed to retrieve 2FA code")
            return "2fa_failed"

        d.app_start(package_name)
        logger.info("Switched back to Instagram app")
        time.sleep(5)

        helper = UIHelper(d)
        typer = StealthTyper(device_id=d.serial)

        if not helper.wait_for_xpath('//android.view.View[@content-desc="Check your email"]', timeout=15):
            logger.error("❌ 2FA screen not ready — Check your email prompt missing")
            return "2fa_screen_not_ready"

        input_xpath = '//android.widget.EditText'
        if not helper.wait_for_xpath(input_xpath, timeout=10):
            logger.error("❌ 2FA input field not found")
            return "2fa_input_not_found"

        input_field = d.xpath(input_xpath)

        # Reliable EditText focus and click
        for attempt in range(3):
            logger.info(f"👆 Tapping EditText field (attempt {attempt+1})")
            if input_field.click_exists(timeout=2):
                time.sleep(0.5)
                break
            time.sleep(1)
        else:
            logger.error("❌ Failed to focus 2FA input field after retries")
            return "2fa_input_click_failed"

        d.clear_text()
        time.sleep(0.5)
        typer.type_text(verification_code)
        time.sleep(1.5)

        entered = input_field.get_text() or ""
        logger.info(f"🔍 Text in input field: '{entered}'")

        if verification_code not in entered:
            logger.warning("❌ Code not correctly entered — retrying once more")
            input_field.click()
            time.sleep(0.5)
            d.clear_text()
            time.sleep(0.5)
            typer.type_text(verification_code)
            time.sleep(1.5)
            entered = input_field.get_text() or ""
            logger.info(f"🔁 Retried input — field now contains: '{entered}'")
            if verification_code not in entered:
                logger.error("❌ Code still not correctly entered")
                return "2fa_code_mismatch"

        logger.info("✅ Successfully entered 2FA code")

        # Continue button click
        continue_xpath_variants = [
            '//android.widget.Button[contains(@content-desc, "Continue")]',
            '//android.widget.Button[contains(@text, "Continue")]',
            '//android.view.View[contains(@content-desc, "Continue")]',
            '^Continue',
            '%continue%',
        ]
        for xpath in continue_xpath_variants:
            if helper.wait_for_xpath(xpath, timeout=5):
                if d.xpath(xpath).click_exists(timeout=3):
                    logger.info(f"✅ Clicked Continue button using XPath: {xpath}")
                    break
        else:
            logger.warning("⚠️ Continue button not found — checking if we already advanced")

            # Check if we already passed the Continue screen (e.g. Save Login Info is up)
            save_prompt_xpath = '//android.view.View[@content-desc="Save your login info?"]'
            if helper.wait_for_xpath(save_prompt_xpath, timeout=5):
                logger.info("✅ Detected Save Login screen — assuming Continue was already clicked")
            else:
                logger.error("❌ Continue button not found and Save screen not present")
                return "confirm_button_not_found"

        save_prompt_xpath = '//android.view.View[@content-desc="Save your login info?"]'
        logger.info("Waiting for save login info prompt to appear...")
        helper.wait_for_xpath(save_prompt_xpath, timeout=15)
        handle_save_login_prompt(d, helper, username)

        setup_xpath = '%Set up on new device%'
        skip_xpath = '^Skip'
        logger.info("Checking for optional 'Set up on new device' screen...")
        if d.xpath(setup_xpath).wait(timeout=30):
            logger.info("🆕 'Set up on new device' screen detected")
            if d.xpath(skip_xpath).click_exists(timeout=5):
                logger.info("✅ Clicked 'Skip' button")
                time.sleep(1.5)
            else:
                logger.warning("⚠️ 'Skip' button appeared but click failed")
        else:
            logger.info("No 'Set up on new device' prompt appeared")

        logger.info("Waiting for post-2FA login confirmation...")
        story_xpath_variants = [
            f'//android.widget.TextView[@text="Your story"]',
            f'//android.widget.Button[contains(@content-desc, "{username}\'s story")]',
            f'//android.widget.ImageView[contains(@content-desc, "{username}\'s story")]',
        ]
        ban_xpath = '%We suspended your account%'

        start_time = time.time()
        timeout = 30
        while time.time() - start_time < timeout:
            if d.xpath(ban_xpath).exists:
                logger.error("🚫 Account suspended detected after 2FA")
                return "account_banned"

            for xpath in story_xpath_variants:
                if d.xpath(xpath).exists:
                    logger.info(f"✅ Story element matched: {xpath} — login + 2FA successful")
                    airtable_client.update_record(base_id, table_name, record_id, {"Logged In?": True})
                    return True

            time.sleep(2)

        logger.warning("❓ No story or ban element detected after timeout")
        return "unknown"

    except Exception as e:
        logger.error("Error during login and 2FA process: %s", e)
        return "exception"


if __name__ == "__main__":
    d = u2.connect()  # or pass in serial if needed
    result = None  # Track login outcome

    try:
        logger.info("🔍 Fetching email credentials from Airtable...")

        base_id = os.getenv("AIRTABLE_BASE_ID")
        table_name = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")
        unused_view_id = os.getenv("IG_ARMY_UNUSED_VIEW_ID")

        airtable_client = AirtableClient()
        account_data = airtable_client.get_single_active_account(
            base_id=base_id,
            table_name=table_name,
            unused_view_id=unused_view_id
        )

        if not account_data:
            raise Exception("❌ No active account found in Airtable")

        fields = account_data["fields"]
        record_id = account_data["id"]
        username = fields.get("Account")
        password = fields.get("Password")
        email = fields.get("Email")
        email_password = fields.get("Email Password")
        package_name = fields.get("Package Name")

        if not all([username, password, email, email_password]):
            raise Exception("❌ Missing required fields in Airtable record")

        logger.info(f"✅ Starting automation for {username}")

        # Try to get package name from Airtable, otherwise ask user to pick one
        if not package_name:
            logger.info("📦 No package name found in Airtable. Prompting user to select one...")
            package_name = select_instagram_package()
            if not package_name:
                raise Exception("❌ No Instagram package selected. Aborting.")

        logger.info(f"Launching Clone {package_name}")
        d.app_start(package_name)
        time.sleep(5)

        # Run login + 2FA
        result = handle_login_and_2fa(
            d=d,
            username=username,
            password=password,
            package_name=package_name,
            email=email,
            email_password=email_password,
            airtable_client=airtable_client,
            record_id=record_id,
            base_id=base_id,
            table_name=table_name
        )

        logger.info(f"🏁 Login flow result: {result}")

    except KeyboardInterrupt:
        logger.warning("⚠️ Script interrupted by user (Ctrl+C)")

    except Exception as e:
        logger.error(f"❌ Process failed with error: {e}")

    # ✅ Only reset identity if account was banned
    if result == "account_banned":
        logger.info("🚫 Account banned, triggering identity reset...")
        if new_identity(d, timeout=10):
            logger.info("✅ Identity reset triggered successfully")
            confirm_xpath = '//android.widget.TextView[@resource-id="android:id/alertTitle"]'
            if d.xpath(confirm_xpath).wait(timeout=10):
                logger.info("🎉 New identity confirmed via alertTitle prompt")
            else:
                logger.warning("⚠️ Identity reset triggered, but confirmation prompt not detected")
        else:
            logger.warning("⚠️ Identity reset failed or notification not found")
    else:
        logger.info("✅ No identity reset needed (account not banned)")
# def test_2fa_code_entry_only(d, code="434558"):
#     from stealth_typing import StealthTyper
#     from ui_helper import UIHelper
#     import time
#     import logging
#
#     logger = setup_logger("2FA_Code_Entry_Test")
#     helper = UIHelper(d)
#     typer = StealthTyper(device_id=d.serial)
#
#     check_email_xpath = '//android.view.View[@content-desc="Check your email"]'
#     input_xpath = '//android.widget.EditText'
#
#     logger.info(f"📲 Starting 2FA code entry test with code: {code}")
#
#     # Wait for the 'Check your email' prompt
#     if not helper.wait_for_xpath(check_email_xpath, timeout=15):
#         logger.error("❌ 'Check your email' prompt not found")
#         return False
#
#     # Wait for input field
#     if not helper.wait_for_xpath(input_xpath, timeout=10):
#         logger.error("❌ Input field not found")
#         return False
#
#     input_field = d.xpath(input_xpath)
#
#     # Try clicking the field
#     for attempt in range(3):
#         logger.info(f"👆 Tapping EditText field (attempt {attempt+1})")
#         if input_field.click_exists(timeout=2):
#             time.sleep(0.5)
#             break
#         time.sleep(1)
#     else:
#         logger.error("❌ Failed to focus input field after retries")
#         return False
#
#     d.clear_text()
#     time.sleep(0.5)
#
#     typer.type_text(code)
#     time.sleep(1.5)
#
#     entered_text = input_field.get_text() or ""
#     logger.info(f"🔍 Text in input field: '{entered_text}'")
#
#     if code in entered_text:
#         logger.info("✅ Code entered correctly")
#         return True
#     else:
#         logger.error("❌ Code not correctly entered")
#         return False
# if __name__ == "__main__":
#     import uiautomator2 as u2
#     d = u2.connect()
#
#     success = test_2fa_code_entry_only(d, code="434558")
#     print("✅ Test passed" if success else "❌ Test failed")
#
