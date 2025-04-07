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
            table_id=table_name  # ✅ Note: it's `table_name` here, not `table_id`
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

        # ✅ Switch to Instagram app and bring to foreground
        logger.info("📱 Switching back to Instagram app...")
        bring_app_to_foreground(
            d,
            package_name,
            check_xpath='//android.view.View[@content-desc="Check your email"]',
            timeout=10
        )


        helper = UIHelper(d)
        typer = StealthTyper(device_id=d.serial)

        # 🔐 Wait for 2FA input screen
        if not helper.wait_for_xpath('//android.view.View[@content-desc="Check your email"]', timeout=10):
            logger.error("❌ 2FA screen not ready — Check your email prompt missing")
            return "2fa_screen_not_ready"

        input_xpath = '//android.widget.EditText'
        if not helper.wait_for_xpath(input_xpath, timeout=10):
            logger.error("❌ 2FA input field not found")
            return "2fa_input_not_found"

        input_field = d.xpath(input_xpath)
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
        time.sleep(2)

        entered = input_field.get_text() or ""
        logger.info(f"🔍 Text in input field: '{entered}'")

        if verification_code not in entered:
            logger.warning("❌ Code not correctly entered — retrying once more")
            input_field.click()
            time.sleep(0.5)
            d.clear_text()
            time.sleep(0.5)
            typer.type_text(verification_code)
            time.sleep(2)
            entered = input_field.get_text() or ""
            logger.info(f"🔁 Retried input — field now contains: '{entered}'")
            if verification_code not in entered:
                logger.error("❌ Code still not correctly entered")
                return "2fa_code_mismatch"

        logger.info("✅ Successfully entered 2FA code")

        # ✅ Wait for Save Login screen (no continue logic)
        save_prompt_xpath = '//android.view.View[@content-desc="Save your login info?"]'
        logger.info(f"Waiting for element: {save_prompt_xpath}")
        if not helper.wait_for_xpath(save_prompt_xpath, timeout=10):
            logger.error(f"❌ Timeout waiting for element: {save_prompt_xpath}")
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
        # 💡 Set base_id + table_id explicitly for update_record_fields()
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
        device_id = fields.get("Device ID")  # 🔐 New field

        if not all([username, password, email, email_password, device_id]):
            raise Exception("❌ Missing required fields in Airtable record")

        logger.info(f"📱 Connecting to device {device_id}")
        d = u2.connect(device_id)
        logger.info(f"✅ Starting automation for {username} on device {device_id}")

        logger.info(f"🚀 Attempting to launch Instagram clone: {package_name}")
        core_ig_actions.launch_app_via_adb(device_id, package_name)
        time.sleep(4)

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
