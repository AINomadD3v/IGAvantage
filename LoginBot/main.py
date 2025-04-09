# main.py

import uiautomator2 as u2
import os
import time
from Shared import core_ig_actions
from Shared.ui_helper import UIHelper
from .get_code import  Firefox2FAFlow
from .instagram_automation import InstagramAutomation
from Shared.stealth_typing import StealthTyper
from Shared.logger_config import setup_logger
from Shared.airtable_manager import AirtableClient
from Shared.core_ig_actions import bring_app_to_foreground, launch_app_via_adb
from Shared.new_identity import new_identity
from Shared.popup_handler import PopupHandler
from InterActions import scroller

from dotenv import load_dotenv
from pathlib import Path

# Ensure project root .env is loaded
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)


logger = setup_logger(__name__)

def handle_2fa(
    d,
    username,
    password,
    package_name,
    email,
    email_password,
    airtable_client,
    record_id,
    base_id,
    table_name,
    allow_manual_fallback=True
):
    try:
        logger.info("🔐 2FA screen detected. Starting Firefox automation for code retrieval")

        firefox = Firefox2FAFlow(
            email=email,
            password=email_password,
            record_id=record_id,
            base_id=base_id,
            table_id=table_name
        )

        verification_code = firefox.run()

        if not verification_code and allow_manual_fallback:
            logger.warning("⚠️ Auto 2FA failed — prompting user manually")
            verification_code = input("📩 Enter the 2FA code from email: ").strip()
            if not verification_code or not verification_code.isdigit():
                logger.error("❌ Invalid or empty 2FA code entered")
                return "2fa_failed"
        elif not verification_code:
            logger.error("❌ No 2FA code retrieved and fallback is disabled")
            return "2fa_failed"

        logger.info(f"✅ 2FA code retrieved: {verification_code}")

        # Step 1: Wait briefly
        logger.info("🕒 Waiting before triggering new identity reset...")
        time.sleep(2)

        # Step 2: Trigger identity reset via notification
        logger.info("🔁 Attempting identity reset from Firefox notification...")
        identity_success = new_identity(d)

        if identity_success:
            logger.info("✅ Identity reset succeeded via notification")
        else:
            logger.warning("⚠️ Identity notification interaction failed")

        # Step 3: Kill Firefox to release control
        logger.info("🛑 Stopping Firefox to release focus")
        d.app_stop("org.mozilla.firefoy")
        time.sleep(1.5)

        # Step 4: Bring Instagram clone to foreground
        logger.info(f"📲 Switching back to Instagram clone: {package_name}")
        if not bring_app_to_foreground(
            d,
            package_name,
            check_xpath='//android.view.View[@content-desc="Check your email"]',
            timeout=10
        ):
            logger.error("❌ Failed to foreground Instagram clone")
            return "foreground_switch_failed"

        # Step 5: Input 2FA code
        helper = UIHelper(d)
        typer = StealthTyper(device_id=d.serial)

        if not helper.wait_for_xpath('//android.view.View[@content-desc="Check your email"]', timeout=10):
            logger.error("❌ 2FA screen not ready — 'Check your email' prompt missing")
            return "2fa_screen_not_ready"

        input_xpath = '//android.widget.EditText'
        if not helper.wait_for_xpath(input_xpath, timeout=10):
            logger.error("❌ 2FA input field not found")
            return "2fa_input_not_found"

        input_field = d.xpath(input_xpath)
        for attempt in range(3):
            logger.info(f"👆 Attempt {attempt+1}/3: Tapping input field and entering 2FA code")

            if input_field.click_exists(timeout=2):
                time.sleep(0.5)

                logger.info("🧼 Clearing text manually via StealthTyper")
                typer.clear_field_before_typing(xpath=input_xpath)

                logger.info("⌨️ Typing verification code via ADB keyboard")
                typer.type_text(verification_code)
                time.sleep(2)

                entered = input_field.get_text() or ""
                logger.info(f"🔍 Field now contains: '{entered}'")

                if verification_code in entered:
                    logger.info("✅ Code successfully entered")
                    break
                else:
                    logger.warning("❌ Code mismatch — retrying")
            else:
                logger.warning("⚠️ Could not click input field")

            time.sleep(1)

        else:
            logger.error("❌ Code entry failed after all attempts")
            return "2fa_code_mismatch"



        # Step 6: Wait for Save Login screen
        save_prompt_xpath = '//android.view.View[@content-desc="Save your login info?"]'
        logger.info(f"🕒 Waiting for Save Login screen: {save_prompt_xpath}")
        if not helper.wait_for_xpath(save_prompt_xpath, timeout=10):
            logger.error("❌ Save login prompt not found")
            return "save_prompt_not_found"

        logger.info("✅ Save Login screen appeared — proceeding to post-login handler")
        return Post2FAHandler(
            d=d,
            username=username,
            airtable_client=airtable_client,
            record_id=record_id,
            base_id=base_id,
            table_name=table_name
        ).handle()

    except Exception as e:
        logger.error("💥 Exception during 2FA flow: %s", e)
        return "exception"

class Post2FAHandler:
    def __init__(self, d, username, airtable_client, record_id, base_id, table_name):
        self.d = d
        self.username = username
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.base_id = base_id
        self.table_name = table_name
        self.helper = UIHelper(d)
        self.logger = setup_logger()


    def handle(self):
        self._handle_save_login_prompt()
        self._handle_setup_prompt()
        return self._finalize_login_check()

    def _handle_save_login_prompt(self):
        try:
            save_prompt_xpath = '//android.view.View[@content-desc="Save your login info?"]'
            self.logger.info("Waiting for save login info prompt to appear...")
            self.helper.wait_for_xpath(save_prompt_xpath, timeout=15)

            self.logger.info("Checking for post-login save prompt...")

            keywords = ["save your login info", "save login", "zapisz dane logowania"]
            prompt_xpath = self.helper.find_prompt_xpath(keywords, timeout=8)

            if not prompt_xpath:
                self.logger.info("No save prompt appeared")
                return

            for button_text in ["Save", "Zapisz", "Not now", "Nie teraz"]:
                btn_xpath = f'//android.widget.Button[contains(@text, "{button_text}")] | //android.widget.Button[contains(@content-desc, "{button_text}")]'
                if self.helper.wait_for_xpath(btn_xpath, timeout=5):
                    if self.d.xpath(btn_xpath).click_exists(timeout=3):
                        self.logger.info(f"✅ Clicked button: {button_text}")
                        time.sleep(2)
                        return
                    else:
                        self.logger.warning(f"⚠️ Button found but click failed: {button_text}")
            self.logger.warning("⚠️ Prompt appeared but no matching button was clicked")

        except Exception as e:
            self.logger.error(f"Error handling save login prompt: {e}")

    def _handle_setup_prompt(self):
        setup_xpath = '%Set up on new device%'
        skip_xpath = '^Skip'
        self.logger.info("Checking for optional 'Set up on new device' screen...")

        if self.d.xpath(setup_xpath).wait(timeout=30):
            self.logger.info("🆕 'Set up on new device' screen detected")
            if self.d.xpath(skip_xpath).click_exists(timeout=5):
                self.logger.info("✅ Clicked 'Skip' button")
                time.sleep(1.5)
            else:
                self.logger.warning("⚠️ 'Skip' button appeared but click failed")
        else:
            self.logger.info("No 'Set up on new device' prompt appeared")

    def _finalize_login_check(self):
        self.logger.info("Waiting for post-2FA login confirmation...")

        story_xpath_variants = [
            f'//android.widget.TextView[@text="Your story"]',
            f'//android.widget.Button[contains(@content-desc, "{self.username}\'s story")]',
            f'//android.widget.ImageView[contains(@content-desc, "{self.username}\'s story")]',
        ]
        ban_xpath = '%We suspended your account%'

        start_time = time.time()
        timeout = 30

        while time.time() - start_time < timeout:
            if self.d.xpath(ban_xpath).exists:
                self.logger.error("🚫 Account suspended detected after 2FA")
                return "account_banned"

            for xpath in story_xpath_variants:
                if self.d.xpath(xpath).exists:
                    self.logger.info(f"✅ Story element matched: {xpath} — login + 2FA successful")

                    self.airtable_client.base_id = self.base_id
                    self.airtable_client.table_id = self.table_name
                    self.airtable_client.update_record_fields(self.record_id, {"Logged In?": True})

                    return True

            time.sleep(2)

        self.logger.warning("❓ No story or ban element detected after timeout")
        return "unknown"



if __name__ == "__main__":
    result = None  # Track login outcome

    try:
        logger.info("🔍 Fetching email credentials from Airtable...")
        # ✅ Always use these three keys
        base_id = os.getenv("IG_ARMY_BASE_ID")
        table_id = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")
        view_id = os.getenv("IG_ARMY_UNUSED_VIEW_ID")
        logger.info(f"🔑 IG_ARMY_BASE_ID = {base_id}")

        if not all([base_id, table_id, view_id]):
            raise Exception("❌ Missing required IG Army env variables")

        logger.info(f"📄 Using IG Army base_id={base_id}, table_id={table_id}, view_id={view_id}")

        airtable_client = AirtableClient()
        airtable_client.base_id = base_id
        airtable_client.table_id = table_id

        account_data = airtable_client.get_single_active_account(
            base_id=base_id,
            table_id=table_id,
            view_id=view_id
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
        device_id = fields.get("Device ID")

        if not all([username, password, email, email_password, device_id]):
            raise Exception("❌ Missing required fields in Airtable record")

        logger.info(f"📱 Connecting to device {device_id}")
        d = u2.connect(device_id)
        logger.info(f"✅ Starting automation for {username} on device {device_id}")

        logger.info(f"🚀 Attempting to launch Instagram clone: {package_name}")
        core_ig_actions.launch_app_via_adb(device_id, package_name)
        time.sleep(4)

        # 🔧 Inject helper + popup watcher
        helper = UIHelper(d)
        helper.record_id = record_id
        helper.base_id = base_id
        helper.table_id = table_id
        helper.airtable_client = airtable_client
        helper.package_name = package_name

        popup_handler = PopupHandler(d, helper)
        popup_handler.register_watchers()

        automation = InstagramAutomation(
            d,
            package_name=package_name,
            airtable_client=airtable_client,
            record_id=record_id
        )
        login_result = automation.ig_login(username, password)

        if login_result == "login_success":
            logger.info("✅ Logged in successfully without 2FA")
            result = "login_success"
            logger.info("🚀 Starting warmup session after login")
            scroller.run_warmup_session(device_id=device_id, package_name=package_name, session_duration_secs=120)

        elif login_result == "2fa_required":
            logger.info("🔐 2FA required — proceeding with verification")
            result = handle_2fa(
                d=d,
                username=username,
                password=password,
                email=email,
                email_password=email_password,
                package_name=package_name,
                airtable_client=airtable_client,
                record_id=record_id,
                base_id=base_id,
                table_name=table_id,
                allow_manual_fallback=True
            )

            if result is True:
                logger.info("✅ 2FA + post-login flow succeeded — starting warmup")
                scroller.run_warmup_session(device_id=device_id, package_name=package_name, max_runtime_seconds=120)

        elif login_result == "login_failed":
            logger.error("❌ Login failed due to incorrect credentials")
            result = "login_failed"

        else:
            logger.error("❌ Login timeout or unknown post-login state")
            result = "timeout_or_unknown"

        logger.info(f"🏁 Login flow result: {result}")

    except KeyboardInterrupt:
        logger.warning("⚠️ Script interrupted by user (Ctrl+C)")

    except Exception as e:
        logger.error(f"❌ Process failed with error: {e}")

