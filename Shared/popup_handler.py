import json
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
            .when("^Try private translations") \
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

        # 🎬 Reels NUX popup (Advanced XPath)
        w("reels_about_popup") \
            .when("About Reels") \
            .when("Share") \
            .click()

        w.start()
        self.logger.info("✅ Popup watchers registered and started.")


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

    def handle_cashback_popup(self) -> bool:
        try:
            self.logger.info("🟡 Running OCR-based cashback popup handler")

            keywords = [
                "cashback", "usługa zwrotu", "800 sklepach", "sprawdzam",
                "gdzie możesz", "onet poczta", "allegro", "media markt",
                "sinsay", "carrefour", "lot", "esky"
            ]

            screen_text = self.helper.perform_ocr().lower()
            if not any(keyword in screen_text for keyword in keywords):
                self.logger.info("✅ Cashback popup not detected via OCR")
                return False

            self.logger.info("⚠️ Cashback popup detected — attempting to dismiss...")

            # OCR-based attempt to click '×' or 'x'
            for symbol in ["×", "x"]:
                center = self.helper.find_text_center(symbol, lang='eng')
                if center:
                    self.logger.info(f"✅ [OCR Click] Close symbol '{symbol}' found at {center}")
                    self.d.click(*center)
                    time.sleep(2)
                    if not any(k in self.helper.perform_ocr().lower() for k in keywords):
                        self.logger.info("✅ Popup dismissed via OCR-based click")
                        return True

            # Final absolute pixel fallback
            self.logger.warning("🛑 Trying hardcoded absolute fallback near (1025, 715)")
            fallback_coords = [
                (1025, 715),
                (1015, 715),
                (1035, 715),
                (1025, 705),
                (1025, 725),
            ]

            for x, y in fallback_coords:
                self.logger.info(f"🎯 [Absolute Click] Trying at ({x}, {y})")
                self.d.click(x, y)
                time.sleep(1.5)
                if not any(k in self.helper.perform_ocr().lower() for k in keywords):
                    self.logger.info(f"✅ Popup dismissed via hardcoded click at ({x}, {y})")
                    return True

            self.logger.error("❌ All dismissal attempts failed — cashback popup still visible")
            return False

        except Exception as e:
            self.logger.error(f"💥 Error in handle_cashback_popup: {e}")
            return False

    def handle_translation_popup(self, timeout=6):
        try:
            self.logger.info("🔍 Waiting for translation popup...")
            xpath = '^Try private translations'
            for _ in range(timeout):
                if self.d.xpath(xpath).exists:
                    self.logger.info("📌 Translation popup detected — handling")
                    self.handle_all_popups()
                    time.sleep(1.5)
                    return True
                time.sleep(1)
            self.logger.info("✅ Translation popup did not appear")
            return False
        except Exception as e:
            self.logger.error(f"💥 Error in handle_translation_popup: {e}")
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
    from ui_helper import UIHelper
    import logging

    logger = logging.getLogger("TestCashbackPopup")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        logger.info("🔗 Connecting to device...")
        d = u2.connect()
        helper = UIHelper(d)
        popup_handler = PopupHandler(d, helper)

        logger.info("🧪 Running cashback popup test...")
        success = popup_handler.handle_cashback_popup()

        if success:
            logger.info("✅ Cashback popup dismissed successfully")
        else:
            logger.warning("❌ Cashback popup not dismissed")

    except Exception as e:
        logger.error(f"💥 Error during cashback popup test: {e}")

