import json
import threading
import os
import time
from .logger_config import setup_logger
import uiautomator2 as u2
from .ui_helper import UIHelper

logger = setup_logger(name='PopupHander')

class PopupHandler:
    def __init__(self, driver, helper=None, config_path=None):
        self.d = driver
        self.helper = helper or UIHelper(driver)
        self.logger = setup_logger("PopupHandler")
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "popup_config.json")
        self.config = self._load_config(config_path)

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Popup config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def register_watchers(self):
        """Register background popup watchers."""
        w = self.d.watcher



        # Photo Removed Popup
        w("photo_removed_popup") \
        .when("^We removed your photo") \
        .call(lambda d, sel: photo_removed_callback(d, sel))

        # 🔁 Translation popup
        w("translation_popup") \
            .when("//*[contains(@text, 'Try private translations')]") \
            .when("//*[contains(@text, 'Not now')]") \
            .click()

        # 💾 Save login info prompt (Instagram)
        w("save_login_info") \
            .when("save your login info") \
            .when() \
            .click()

        # 📍 Setup prompts and location access (Instagram)
        w("setup_prompt") \
            .when("use location services") \
            .when("access your location") \
            .when("set up on new device") \
            .when("continue setup") \
            .when("Not now") \
            .when("Skip") \
            .click()

        # 💾 Save password (Firefox)
        w("save_password") \
            .when('//*[@resource-id="org.mozilla.firefoy:id/save_cancel"]') \
            .click()

        # 🔐 Trusted device prompt
        w("trusted_prompt") \
            .when("^Do you want to add this device to trusted ones?") \
            .when("Skip") \
            .click()

        # 🛡️ Trackers dismiss (Firefox)
        w("trackers") \
            .when("^cfr.dismiss") \
            .click()

        # Location access popup
        w("location_services") \
            .when('//*[@content-desc="Continue"]') \
            .click()

        # 📍 Open location settings prompt
        w("open_location_settings") \
            .when("^Open your location settings to allow") \
            .when("Cancel") \
            .click()

        # 🎬 Reels creation prompt
        w("reels_create_prompt") \
            .when("Create longer Reels") \
            .when("OK") \
            .click()

        # Create a sticker popup
        w("create_sticker_popup") \
            .when("Create a sticker") \
            .when("Not now") \
            .click()

        # Edit your reels draft popup
        w("edit_reel_draft") \
            .when("//*[contains(@text, 'Keep editing your draft?') or contains(@text, 'Continue editing your draft?')]") \
            .when("//*[contains(@text, 'Start new video')]") \
            .click()

        w("reels_about_popup") \
            .when("//*[contains(@resource-id, 'clips_nux_sheet_title') and @text='About Reels']") \
            .when("//*[contains(@resource-id, 'clips_nux_sheet_share_button') and @content-desc='Share']") \
            .click()


        # 🎵 Trending audio tab (click parent of "Trending" when detected)
        w("reels_trending_tab") \
            .when("Trending") \
            .call(lambda el: el.parent().click())

        # Others can download your reels Popup
        w("others_can_download") \
            .when("Others can now download") \
            .when("Continue") \
            .click()

        # Allow Media Access
        w("allow_media_access") \
            .when("//*[contains(@text, 'access photos')]") \
            .when("//*[contains(@resource-id, 'permission_allow_button')]") \
            .click()

        # Allow camera access
        w("allow_camera_access") \
            .when("//*[contains(@text, 'take photos')]") \
            .when("//*[contains(@resource-id, 'permission_allow_button')]") \
            .click()

        # Allow microphone access
        w("allow_microphone_access") \
            .when("//*[contains(@text, 'record audio')]") \
            .when("//*[contains(@resource-id, 'permission_allow_button')]") \
            .click()

        # ❌ Generic error toast: "Something went wrong"
        w("reel_share_failure_toast") \
            .when("//*[contains(@text, 'Something went wrong')]") \
            .call(lambda el: logger.warning("⚠️ Toast detected: Something went wrong"))

        # New ways to reuse popup
        w("new_ways_to_reuse") \
            .when("//*[contains(@text, 'New ways to reuse')]") \
            .when("//*[contains(@content-desc, 'OK')]") \
            .click()

        # .call(lambda d, el: self.logger.warning("✅ WATCHER triggered: New ways to reuse") or el.click())
        w("account_restriction") \
            .when("//*[contains(@content-desc, 'We added a restriction to your account')]") \
            .when("//*[contains(@content-desc, 'Cancel')]") \
            .click()

        w("account_suspended") \
            .when("^We suspended your account") \
            .call(self.handle_suspension)

        w("firefox_color_popup") \
            .when("//*[contains(@text, 'Try a splash')]") \
            .when("//*[contains(@content-desc, 'Close tab')]") \
            .click()

        w.start()
        self.logger.info("✅ Popup watchers registered and started.")

    def start_watcher_loop(self, interval=0.5):
        """Continuously run watcher to handle popups in background."""
        def loop():
            self.logger.info("📡 Watcher loop started")
            while True:
                try:
                    self.d.watcher.run()
                except Exception as e:
                    self.logger.error(f"💥 Watcher run error: {e}")
                time.sleep(interval)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()

    def handle_cookie_popup(self) -> bool:
        try:
            self.logger.info("📋 Running OCR-based cookie popup handler")

            keywords = [
                "przejdź do serwisu", "zaakceptuj wszystko", "wyrażam zgodę", "akceptuję",
                "akceptuję i przechodzę do serwisu", "zgadzam się", "cookie", "ciasteczka",
                "polityka prywatności"
            ]
            click_texts = ["PRZEJDŹ DO SERWISU", "Przejdź do serwisu"]

            webview = self.d(className="android.webkit.WebView")
            bounds = webview.info.get('bounds', {}) if webview.exists else {}

            fallback_coords = []
            if bounds:
                fallback_coords = [
                    (bounds['left'] + 150, bounds['bottom'] - 100),
                    ((bounds['left'] + bounds['right']) // 2, bounds['bottom'] - 100),
                    (bounds['right'] - 150, bounds['bottom'] - 100),
                    ((bounds['left'] + bounds['right']) // 2, bounds['bottom'] - 150),
                    ((bounds['left'] + bounds['right']) // 2, bounds['bottom'] - 50),
                ]

            screen_text = self.helper.perform_ocr()
            if not any(keyword in screen_text for keyword in keywords):
                self.logger.info("✅ No cookie popup detected via OCR")
                return False

            self.logger.info("⚠️ Cookie popup detected via OCR")

            for text in click_texts:
                btn = self.d(text=text)
                if btn.exists and btn.click_exists(timeout=3):
                    self.logger.info(f"✅ Clicked cookie dismiss button: '{text}'")
                    time.sleep(2)
                    return True

            for x, y in fallback_coords:
                self.logger.info(f"⚙️ Clicking fallback coordinate ({x}, {y})")
                self.d.click(x, y)
                time.sleep(2)
                return True

            self.logger.warning("❌ Failed to dismiss cookie popup")
            return False

        except Exception as e:
            self.logger.error(f"💥 Error in handle_cookie_popup: {e}")
            return False

    def handle_all_popups(self, delay_after_click=1.0) -> int:
        handled_count = 1
        for entry in self.config:
            name = entry.get("name", "Unnamed Popup")
            text_xpath = entry.get("text_xpath")
            button_xpath = entry.get("button_xpath")
            container_xpath = entry.get("container_xpath")  # optional: add to config for stricter visibility checks

            if not text_xpath or not button_xpath:
                self.logger.warning(f"⚠️ Skipping popup '{name}' due to missing XPaths")
                continue

            try:
                if self.d.xpath(text_xpath).exists:
                    self.logger.info(f"📌 Detected popup: {name}")

                    dismiss_btn = self.d.xpath(button_xpath)
                    clicked = False

                    if dismiss_btn.exists:
                        clicked = dismiss_btn.click_exists(timeout=3)

                        # Retry once if click failed
                        if not clicked:
                            self.logger.warning(f"⚠️ First click attempt failed for popup: {name}, retrying...")
                            time.sleep(1)
                            clicked = dismiss_btn.click_exists(timeout=3)

                        if clicked:
                            time.sleep(delay_after_click)

                            # Check if popup still exists
                            visible = (
                                self.d.xpath(text_xpath).exists or
                                (container_xpath and self.d.xpath(container_xpath).exists)
                            )
                            if visible:
                                self.logger.warning(f"⚠️ Popup '{name}' still visible after click — may not be dismissed")
                            else:
                                self.logger.info(f"✅ Dismissed popup: {name}")
                                handled_count += 1
                        else:
                            try:
                                center = dismiss_btn.get().center()
                                self.logger.warning(f"⚠️ Click failed for popup '{name}' at {center}")
                            except Exception:
                                self.logger.warning(f"⚠️ Click failed for popup '{name}', and couldn't get center")
                    else:
                        self.logger.debug(f"❎ Dismiss button not found for popup: {name}")
                else:
                    self.logger.debug(f"❎ Popup not present: {name}")
            except Exception as e:
                self.logger.error(f"💥 Error handling popup '{name}': {e}")
        return handled_count

    def try_dismiss_trackers_popup(self) -> bool:
        try:
            xpath = "^cfr.dismiss"
            btn = self.d.xpath(xpath)
            if btn.exists:
                try:
                    center = btn.get().center()
                    self.logger.info(f"🟣 Manually clicking trackers popup at {center}")
                    self.d.click(*center)
                    time.sleep(1)
                    return True
                except Exception as e:
                    self.logger.error(f"❌ Failed to get bounds or click trackers dismiss: {e}")
            else:
                self.logger.debug("Trackers dismiss button not found (manual)")
        except Exception as e:
            self.logger.error(f"Error in try_dismiss_trackers_popup: {e}")
        return False

    def handle_suspension(self, selector=None, d=None, source=None):
        try:
            self.logger.warning("🚫 WATCHER: Account appears suspended")

            if hasattr(self, "_suspension_handled") and self._suspension_handled:
                self.logger.info("⏭️ Suspension already handled this session")
                return

            if not hasattr(self.helper, "record_id") or not hasattr(self.helper, "airtable_client"):
                self.logger.error("❌ Missing record_id or Airtable client in PopupHandler context")
                return

            # 🚫 Airtable update
            airtable = self.helper.airtable_client
            airtable.base_id = self.helper.base_id
            airtable.table_id = self.helper.table_id
            airtable.update_record_fields(self.helper.record_id, {"Status": "Banned"})
            self.logger.info("✅ Updated Airtable: Status = 'Banned'")

            # 💀 Kill the suspended Instagram clone
            package = getattr(self.helper, "package_name", None)
            if package:
                self.logger.info(f"🛑 Stopping suspended app: {package}")
                d.app_stop(package)
            else:
                self.logger.warning("⚠️ No package name set — cannot stop app")

            self._suspension_handled = True

        except Exception as e:
            self.logger.error(f"💥 Error handling suspension watcher: {e}")

def photo_removed_callback(d, sel):
    logger.info("photo_removed_popup watcher triggered!")
    try:
        element_text = sel.text
        element_bounds = sel.bounds
        logger.info("Matched element - text: '%s', bounds: %s", element_text, element_bounds)
    except Exception as e:
        logger.error("Error retrieving element info: %s", e)
    
    # Try primary method: using advanced search shorthand to locate the Cancel button.
    cancel_selector = d.xpath('^@Cancel')
    if cancel_selector.exists:
        logger.info("Found Cancel button using '^@Cancel'. Attempting click...")
        if cancel_selector.click_exists(timeout=3):
            logger.info("Successfully clicked Cancel button via '^@Cancel'.")
            return
        else:
            logger.warning("Click using '^@Cancel' failed. Trying fallback...")
    else:
        logger.info("Cancel button not found with '^@Cancel', trying fallback XPath...")

    # Fallback: search by explicit content-desc.
    fallback_selector = d.xpath('//android.widget.Button[@content-desc="Cancel"]')
    if fallback_selector.exists:
        logger.info("Found Cancel button using fallback XPath. Attempting click...")
        if fallback_selector.click_exists(timeout=3):
            logger.info("Successfully clicked Cancel button using fallback XPath.")
        else:
            logger.error("Fallback click attempt failed.")
    else:
        logger.error("No Cancel button found with fallback XPath.")


if __name__ == "__main__":
    import uiautomator2 as u2
    from Shared.ui_helper import UIHelper
    from Shared.airtable_manager import AirtableClient
    import logging
    import time

    logger = logging.getLogger("TestAccountSuspendedWatcher")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        logger.info("🔗 Connecting to device...")
        d = u2.connect()

        # 🔧 Hardcoded Airtable record info
        record_id = "reczBLvQ76R2H6BRl"
        base_id = "appubnJsm4tcUpVhg"
        table_id = "tblpCwgzs4lauL2ZZ"

        # Setup Airtable client and inject into helper
        airtable_client = AirtableClient()
        airtable_client.base_id = base_id
        airtable_client.table_id = table_id

        helper = UIHelper(d)
        helper.record_id = record_id
        helper.base_id = base_id
        helper.table_id = table_id
        helper.airtable_client = airtable_client

        # Initialize and register watchers
        popup_handler = PopupHandler(d, helper)
        popup_handler.register_watchers()

        logger.info("🧪 Waiting for 'We suspended your account' watcher to trigger...")
        for _ in range(60):  # ~30 seconds
            d.watcher.run()
            time.sleep(0.5)

        logger.info("🛑 Done watching — check logs for result.")

    except Exception as e:
        logger.error(f"💥 Test failed: {e}")

