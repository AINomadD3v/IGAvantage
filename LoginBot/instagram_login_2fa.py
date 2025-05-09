# LoginBot/instagram_login_2fa.py

import os
import time
from pathlib import Path
from typing import Optional

import uiautomator2 as u2
from dotenv import load_dotenv

from Shared.AppCloner.new_identity import new_identity  # Corrected path
from Shared.config_loader import ConfigLoader  # For Scroller configuration

# --- Refactored / Shared component imports ---
from Shared.Data.airtable_manager import AirtableClient
from Shared.instagram_actions import InstagramInteractions
from Shared.UI.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper
from Shared.Utils.xpath_config import InstagramXPaths

# --- Import for WarmupBot (assuming refactored Scroller class) ---
from WarmupBot.scroller import Scroller as WarmupScroller  # Alias to avoid confusion

# --- Imports from within LoginBot (assuming these are the refactored versions) ---
from .get_ig_login_code import Firefox2FAFlow
from .instagram_login import InstagramLoginHandler

# Ensure project root .env is loaded
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print(f"[WARN] instagram_login_2fa.py: .env file not found at {env_path}")

module_logger = setup_logger(__name__)  # Module-level for initial messages


class Post2FAHandler:
    """Handles UI interactions after a 2FA code has been submitted successfully."""

    def __init__(
        self,
        device: u2.Device,
        interactions: InstagramInteractions,
        xpaths: InstagramXPaths,
        username: str,
        airtable_client: Optional[AirtableClient] = None,
        record_id: Optional[str] = None,
        base_id: Optional[str] = None,
        table_id: Optional[str] = None,
    ):
        self.d = device
        self.interactions = interactions
        self.xpaths = xpaths
        self.username = username
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.base_id = base_id
        self.table_id = table_id
        self.logger = setup_logger(self.__class__.__name__)

    def _update_airtable_status_final_login(
        self, status_message: str = "Logged In - Active"
    ):
        """Updates Airtable to indicate successful login after all prompts."""
        if self.airtable_client and self.record_id and self.base_id and self.table_id:
            self.logger.info(
                f"📡 Finalizing Airtable status for {self.record_id}: Logged In = True, Status = {status_message}"
            )
            # AirtableClient might need re-scoping if it's a shared instance
            original_base_id, original_table_id = (
                self.airtable_client.base_id,
                self.airtable_client.table_id,
            )
            self.airtable_client.base_id = self.base_id
            self.airtable_client.table_id = self.table_id

            success = self.airtable_client.update_record_fields(
                self.record_id, {"Logged In?": True, "Status": status_message}
            )
            if success:
                self.logger.info("✅ Airtable final login status updated.")
            else:
                self.logger.error("❌ Failed to update Airtable final login status.")
            # Restore original scope if necessary
            self.airtable_client.base_id, self.airtable_client.table_id = (
                original_base_id,
                original_table_id,
            )
        else:
            self.logger.debug("Airtable details incomplete for final status update.")

    def handle_post_2fa_prompts(self) -> str:
        """
        Orchestrates handling of various prompts after 2FA.
        Returns: "login_success", "account_banned", or "unknown_post_2fa_state".
        """
        self.logger.info("--- Handling Post-2FA Prompts ---")
        self._handle_save_login_prompt()
        self._handle_setup_prompt()
        return self._finalize_login_check()

    def _handle_save_login_prompt(self):
        self.logger.info("Checking for 'Save your login info?' prompt (post-2FA)...")
        save_prompt_xpath = self.xpaths.save_login_info_prompt_view  # More specific

        if self.interactions.wait_for_element_appear(save_prompt_xpath, timeout=10):
            self.logger.info("✅ 'Save your login info?' prompt detected.")

            # Prioritize "Save" button
            if self.interactions.click_if_exists(
                self.xpaths.save_login_info_save_button, timeout=2
            ):
                self.logger.info("Clicked 'Save' on save login prompt.")
                time.sleep(2)
                return

            # Fallback to language-specific buttons or "Not now"
            # This creates a list of XPath properties to try
            buttons_to_try = [
                self.xpaths.post_login_save_button_text_en,  # "Save"
                self.xpaths.post_login_save_button_text_pl,  # "Zapisz"
                self.xpaths.post_login_not_now_button_text_en,  # "Not now"
                self.xpaths.post_login_not_now_button_text_pl,  # "Nie teraz"
            ]
            for btn_xpath_prop_name in [
                "post_login_save_button_text_en",
                "post_login_save_button_text_pl",
                "post_login_not_now_button_text_en",
                "post_login_not_now_button_text_pl",
            ]:
                btn_xpath = getattr(self.xpaths, btn_xpath_prop_name)
                if self.interactions.click_if_exists(btn_xpath, timeout=1):
                    self.logger.info(
                        f"Clicked '{btn_xpath_prop_name}' on save login prompt."
                    )
                    time.sleep(2)
                    return
            self.logger.warning(
                "Save prompt present, but no action button clicked ('Save' or 'Not now' variants)."
            )
        else:
            self.logger.info(
                "No 'Save your login info?' prompt detected explicitly (post-2FA)."
            )

    def _handle_setup_prompt(self):
        self.logger.info("Checking for optional 'Set up on new device' screen...")
        if self.interactions.wait_for_element_appear(
            self.xpaths.setup_on_new_device_prompt_smart, timeout=15
        ):
            self.logger.info("🆕 'Set up on new device' screen detected.")
            if self.interactions.click_if_exists(
                self.xpaths.skip_button_smart, timeout=5
            ):
                self.logger.info("✅ Clicked 'Skip' button.")
                time.sleep(2.5)
            else:
                self.logger.warning(
                    "⚠️ 'Skip' button found but click failed, or button not found on setup screen."
                )
        else:
            self.logger.info("No 'Set up on new device' prompt appeared.")

    def _finalize_login_check(self) -> str:
        self.logger.info(
            "Finalizing login check (post-2FA): looking for home screen or ban indicators..."
        )
        story_xpaths = [
            self.xpaths.home_your_story_text,
            self.xpaths.home_user_story_button(self.username),
            self.xpaths.home_user_story_image(self.username),
        ]
        ban_xpath = self.xpaths.account_suspended_text_smart
        timeout = 30
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.interactions.element_exists(ban_xpath):
                self.logger.error("🚫 Account suspended detected after 2FA submission.")
                # Status updated by watcher or main flow
                return "account_banned"
            for xpath in story_xpaths:
                if self.interactions.element_exists(xpath):
                    self.logger.info(
                        f"✅ Login confirmed: Home screen element '{xpath}' matched."
                    )
                    self._update_airtable_status_final_login()
                    return "login_success"
            self.logger.debug(
                "Finalizing login: Still searching for home/ban indicators..."
            )
            time.sleep(2)
        self.logger.warning(
            "❓ Final login check timed out: No definitive home screen or ban element detected post-2FA."
        )
        return "unknown_post_2fa_state"


def handle_2fa_flow(
    device: u2.Device,
    interactions_instagram: InstagramInteractions,
    xpaths_instagram: InstagramXPaths,
    stealth_typer_instagram: StealthTyper,
    username_ig: str,  # Renamed for clarity
    email_for_2fa: str,
    email_password_for_2fa: str,
    airtable_client: AirtableClient,  # Made non-optional as it's used
    record_id: str,
    base_id: str,
    table_id: str,
    allow_manual_fallback: bool = True,
) -> str:
    """Manages the 2FA code retrieval and submission process."""
    logger = setup_logger(f"handle_2fa_flow_for_{username_ig}")

    try:
        logger.info("🔐 2FA required. Starting 2FA code retrieval via Firefox...")

        firefox_flow = Firefox2FAFlow(
            email=email_for_2fa,
            password=email_password_for_2fa,
            record_id=record_id,
            base_id=base_id,
            table_id=table_id,
            # firefox_package will use its default: DEFAULT_FIREFOX_PACKAGE
        )
        verification_code = (
            firefox_flow.run()
        )  # This handles its own Firefox launch & cleanup

        if not verification_code and allow_manual_fallback:
            logger.warning(
                "⚠️ Automated 2FA code retrieval failed. Prompting user for manual input..."
            )
            try:
                verification_code = input(
                    f"📩 [{username_ig}] Enter the 6-digit 2FA code from email '{email_for_2fa}': "
                ).strip()
                if (
                    not verification_code
                    or not verification_code.isdigit()
                    or len(verification_code) != 6
                ):
                    logger.error("❌ Invalid or empty 2FA code entered manually.")
                    return "2fa_failed_manual_invalid"
            except EOFError:
                logger.error(
                    "❌ Manual 2FA input prompt failed (EOFError - non-interactive environment?)."
                )
                return "2fa_failed_manual_prompt_error"
            except Exception as e_input:
                logger.error(f"❌ Error during manual 2FA input: {e_input}")
                return "2fa_failed_manual_prompt_error"

        elif not verification_code:
            logger.error(
                "❌ No 2FA code retrieved (automated) and manual fallback is disabled."
            )
            return "2fa_failed_auto_no_fallback"

        logger.info(f"✅ Using 2FA code: {verification_code}")

        logger.info(
            "🔁 Attempting identity reset (e.g., via notification interaction)..."
        )
        if new_identity(device):
            logger.info("✅ Identity reset reported success.")
        else:
            logger.warning("⚠️ Identity reset reported failure or no action taken.")
        time.sleep(1)

        # Firefox is closed by Firefox2FAFlow's run() method's finally block.

        logger.info(
            f"📲 Switching back to Instagram app: {interactions_instagram.app_package}"
        )
        if not interactions_instagram.open_app(
            readiness_xpath=xpaths_instagram.two_fa_prompt_view_desc,  # Check for "Check your email"
            readiness_timeout=20,
            max_retries=2,
        ):
            # Fallback: Check for the input field directly if prompt view isn't there
            logger.warning(
                "Primary 2FA screen readiness check failed (prompt view), trying 2FA input field..."
            )
            if not interactions_instagram.open_app(
                readiness_xpath=xpaths_instagram.two_fa_code_input_field,
                readiness_timeout=15,
                max_retries=1,
            ):
                logger.error(
                    "❌ Failed to bring Instagram app to foreground or 2FA screen not ready (input field also not found)."
                )
                return "2fa_failed_foreground_switch"
        logger.info("✅ Instagram is foregrounded, on 2FA screen.")
        time.sleep(1)

        logger.info("✍️ Entering 2FA code into Instagram...")
        input_field_xpath = xpaths_instagram.two_fa_code_input_field
        if not interactions_instagram.wait_for_element_appear(
            input_field_xpath, timeout=10
        ):
            logger.error("❌ 2FA input field not found on Instagram screen.")
            return "2fa_failed_input_not_found"

        code_entered_successfully = False
        for attempt in range(3):
            logger.info(f"Attempt {attempt + 1}/3 to input 2FA code...")
            if interactions_instagram.click_by_xpath(input_field_xpath, timeout=2):
                time.sleep(0.5)
                logger.info("Clearing 2FA input field...")
                device.clear_text()
                time.sleep(0.3)
                logger.info(f"Typing 2FA code: {verification_code}...")
                stealth_typer_instagram.type_text(verification_code)
                time.sleep(1.5)

                entered_text = interactions_instagram.get_element_text(
                    input_field_xpath, timeout=2
                )
                if entered_text and verification_code in entered_text:
                    logger.info("✅ 2FA code appears correctly in field.")
                    code_entered_successfully = True
                    break
                elif not interactions_instagram.element_exists(input_field_xpath):
                    logger.info(
                        "2FA input field disappeared, assuming auto-submit or transition."
                    )
                    code_entered_successfully = True
                    break
                else:
                    logger.warning(
                        f"Code mismatch or still present. Entered: '{entered_text}'. Retrying..."
                    )
            else:
                logger.warning("Could not click 2FA input field.")
            time.sleep(1)

        if not code_entered_successfully:
            logger.error("❌ Failed to input 2FA code correctly after retries.")
            return "2fa_failed_code_entry"

        time.sleep(3)  # Wait for transition after code submission

        logger.info("Transitioning to Post-2FA prompt handling...")
        post_2fa_handler = Post2FAHandler(
            device=device,
            interactions=interactions_instagram,
            xpaths=xpaths_instagram,
            username=username_ig,
            airtable_client=airtable_client,
            record_id=record_id,
            base_id=base_id,
            table_id=table_id,
        )
        post_2fa_result = post_2fa_handler.handle_post_2fa_prompts()

        if post_2fa_result == "login_success":
            return "2fa_success_login_confirmed"
        else:
            return post_2fa_result

    except Exception as e:
        logger.error(f"💥 Exception during 2FA flow: {e}", exc_info=True)
        if airtable_client and record_id and base_id and table_id:
            # Ensure client is scoped correctly if it's a shared instance
            original_base_id, original_table_id = (
                airtable_client.base_id,
                airtable_client.table_id,
            )
            airtable_client.base_id = base_id
            airtable_client.table_id = table_id
            airtable_client.update_record_fields(
                record_id, {"Status": f"2FA Exception: {type(e).__name__}"}
            )
            airtable_client.base_id, airtable_client.table_id = (
                original_base_id,
                original_table_id,
            )
        return "2fa_exception"


if __name__ == "__main__":
    final_outcome = "process_not_run"
    d_instance: Optional[u2.Device] = None
    popup_handler_instance: Optional[PopupHandler] = None

    try:
        module_logger.info("--- Instagram Login with 2FA Process START ---")

        base_id_env = os.getenv("IG_ARMY_BASE_ID")
        table_id_env = os.getenv("IG_ARMY_ACCOUNTS_TABLE_ID")
        view_id_env = os.getenv("IG_ARMY_UNUSED_VIEW_ID")

        if not all([base_id_env, table_id_env, view_id_env]):
            raise ValueError(
                "❌ Missing required IG Army Airtable environment variables (BASE_ID, TABLE_ID, VIEW_ID)."
            )

        module_logger.info("Fetching account details from Airtable...")
        airtable_client_main = AirtableClient(
            base_id=base_id_env, table_id=table_id_env
        )
        account_data = airtable_client_main.get_single_active_account(
            view_id=view_id_env
        )

        if not account_data:
            raise Exception("❌ No active account found in Airtable for login.")

        fields = account_data.get("fields", {})
        record_id_main = account_data.get("id")
        username_ig_main = fields.get("Account")
        password_ig_main = fields.get("Password")
        email_2fa_main = fields.get("Email")
        email_password_2fa_main = fields.get("Email Password")
        package_name_ig_main = fields.get("Package Name", "com.instagram.android")
        device_id_main = fields.get("Device ID")

        if not all(
            [
                username_ig_main,
                password_ig_main,
                email_2fa_main,
                email_password_2fa_main,
                device_id_main,
                record_id_main,
            ]
        ):
            raise ValueError(
                "❌ Missing critical account details from Airtable record."
            )

        module_logger.info(
            f"Attempting login for IG User: {username_ig_main} on Device: {device_id_main} (App: {package_name_ig_main})"
        )

        module_logger.info(f"Connecting to device: {device_id_main}")
        d_instance = u2.connect(device_id_main)
        module_logger.info(
            f"✅ Connected to {d_instance.serial if d_instance else 'N/A'}. Preparing Instagram interactions..."
        )

        interactions_ig = InstagramInteractions(
            device=d_instance,
            app_package=package_name_ig_main,
            airtable_manager=airtable_client_main,
        )  # Pass airtable_client to interactions
        xpaths_ig = InstagramXPaths(package_name=package_name_ig_main)
        typer_ig = StealthTyper(device_id=d_instance.serial)

        # Use a consistent POPUP_CONFIG_PATH, defined globally or imported
        # Assuming POPUP_CONFIG_PATH is correctly defined in get_ig_login_code.py and imported here
        # If not, define it: POPUP_CONFIG_PATH_MAIN = Path(Shared.UI.popup_handler.__file__).resolve().parent / "popup_config.json"
        # For now, using the one from get_ig_login_code (assuming it's globally accessible or re-declared)

        # We should define POPUP_CONFIG_PATH in this file or import it from a central place.
        # For this example, let's assume it's like in get_ig_login_code.py:
        CURRENT_POPUP_CONFIG_PATH = (
            Path(__file__).resolve().parents[1] / "Shared" / "popup_config.json"
        )
        if not CURRENT_POPUP_CONFIG_PATH.exists():
            module_logger.warning(
                f"Popup config not found at {CURRENT_POPUP_CONFIG_PATH}, trying Shared/UI path..."
            )
            CURRENT_POPUP_CONFIG_PATH = (
                Path(PopupHandler.__module__.__file__).resolve().parent
                / "popup_config.json"
            )
            if not CURRENT_POPUP_CONFIG_PATH.exists():
                module_logger.error(
                    "Critical: popup_config.json not found in expected locations."
                )
                raise FileNotFoundError("popup_config.json not found.")

        popup_handler_instance = PopupHandler(
            driver=d_instance, config_path=str(CURRENT_POPUP_CONFIG_PATH)
        )
        popup_handler_instance.set_context(
            airtable_client=airtable_client_main,
            record_id=record_id_main,
            package_name=package_name_ig_main,
            base_id=base_id_env,
            table_id=table_id_env,
        )
        popup_handler_instance.register_watchers()
        # popup_handler_instance.start_watcher_loop() # Start if persistent watching is desired

        module_logger.info(f"🚀 Launching Instagram app: {package_name_ig_main}")
        if not interactions_ig.open_app(
            readiness_xpath=xpaths_ig.login_button, readiness_timeout=25, max_retries=2
        ):
            raise Exception(
                f"❌ Failed to launch or ready Instagram app ({package_name_ig_main})."
            )
        module_logger.info("✅ Instagram app launched/foregrounded.")
        time.sleep(2)

        login_handler_main = InstagramLoginHandler(
            device=d_instance,
            interactions=interactions_ig,
            xpaths=xpaths_ig,
            stealth_typer=typer_ig,
            airtable_client=airtable_client_main,
            record_id=record_id_main,
            base_id=base_id_env,
            table_id=table_id_env,
        )
        initial_login_status = login_handler_main.execute_login(
            username_ig_main, password_ig_main
        )
        module_logger.info(f"Initial login attempt result: {initial_login_status}")

        if initial_login_status == "login_success":
            final_outcome = "login_success_no_2fa"
            module_logger.info("✅ Login successful without 2FA.")
        elif initial_login_status == "2fa_required":
            module_logger.info("🔐 2FA is required. Initiating 2FA handling...")
            final_outcome = handle_2fa_flow(
                device=d_instance,
                interactions_instagram=interactions_ig,
                xpaths_instagram=xpaths_ig,
                stealth_typer_instagram=typer_ig,
                username_ig=username_ig_main,
                email_for_2fa=email_2fa_main,
                email_password_for_2fa=email_password_2fa_main,
                airtable_client=airtable_client_main,
                record_id=record_id_main,
                base_id=base_id_env,
                table_id=table_id_env,
                allow_manual_fallback=True,
            )
            if final_outcome == "2fa_success_login_confirmed":
                module_logger.info("✅✅ 2FA successful and login confirmed!")
            else:
                module_logger.error(
                    f"❌ 2FA handling finished with status: {final_outcome}"
                )
                airtable_client_main.update_record_fields(
                    record_id_main, {"Status": f"Login Failed - {final_outcome}"}
                )
        elif initial_login_status in [
            "login_failed",
            "account_banned",
            "timeout_or_unknown",
            "error",
        ]:
            final_outcome = initial_login_status
            module_logger.error(f"Login failed before 2FA stage: {final_outcome}")
        else:
            final_outcome = f"unknown_initial_status_{initial_login_status}"
            module_logger.error(
                f"Received unexpected status from initial login: {initial_login_status}"
            )
            airtable_client_main.update_record_fields(
                record_id_main, {"Status": f"Login Error - {final_outcome}"}
            )

        if final_outcome in ["login_success_no_2fa", "2fa_success_login_confirmed"]:
            module_logger.info(
                f"🚀 Login successful ({final_outcome}). Starting warmup session..."
            )
            try:
                # Assuming WarmupScroller needs these instances for its own interactions
                config_loader_main = (
                    ConfigLoader()
                )  # Assuming it can be instantiated like this

                warmup_scroller_instance = WarmupScroller(
                    device=d_instance,
                    interactions=interactions_ig,  # Pass IG interactions
                    xpaths=xpaths_ig,  # Pass IG XPaths
                    config_loader=config_loader_main,
                )
                # Check the actual method name and parameters for Scroller
                # Assuming run_scroll_session is the method and it takes duration
                warmup_scroller_instance.run_scroll_session(duration_seconds=120)

                module_logger.info("✅ Warmup session completed.")
                airtable_client_main.update_record_fields(
                    record_id_main, {"Status": "Warmup Done"}
                )
            except Exception as e_warmup:
                module_logger.error(
                    f"💥 Warmup session failed: {e_warmup}", exc_info=True
                )
                airtable_client_main.update_record_fields(
                    record_id_main, {"Status": "Warmup Failed"}
                )
        else:
            module_logger.info(
                f"Skipping warmup due to login/2FA outcome: {final_outcome}"
            )

    except ValueError as ve:
        module_logger.error(f"❌ Configuration Error: {ve}", exc_info=True)
        final_outcome = "config_error"
    except u2.GatewayError as ge:  # Corrected exception
        module_logger.error(
            f"❌ uiautomator2 Gateway Error (is ATX agent running on device?): {ge}",
            exc_info=True,
        )
        final_outcome = "atx_agent_error"
    except Exception as e_main:
        module_logger.error(f"💥 Main process failed: {e_main}", exc_info=True)
        final_outcome = f"main_exception: {type(e_main).__name__}"
    finally:
        module_logger.info(
            f"--- Instagram Login with 2FA Process END --- Final Outcome: {final_outcome} ---"
        )
        if popup_handler_instance:
            popup_handler_instance.stop_watcher_loop()
        if d_instance:
            try:
                d_instance.watcher.stop()
                d_instance.watcher.remove()
                module_logger.info(
                    "UIA2 Watchers stopped and removed if any were active."
                )
            except Exception as e_cleanup_watch:
                module_logger.error(
                    f"Error stopping/removing uia2 watchers: {e_cleanup_watch}"
                )
        module_logger.info("Cleanup attempted.")
