# Shared/popup_handler.py

import json
import os
import threading
import time
from typing import Optional  # Added for type hinting

# Imports needed for the merged OCR methods
import cv2
import pytesseract
import uiautomator2 as u2
from PIL import Image

from .config_loader import get_popup_config
from .logger_config import setup_logger

# Removed: from .ui_helper import UIHelper

logger = setup_logger(
    name="PopupHandler"
)  # Changed logger name slightly for consistency


class PopupHandler:
    """
    Handles detection and dismissal of various popups using uiautomator2 watchers.
    Also includes OCR capabilities for specific popup types (e.g., cookies).
    """

    def __init__(self, driver: u2.Device, config_path: Optional[str] = None):
        """
        Initializes the PopupHandler.

        Args:
            driver (u2.Device): The uiautomator2 device instance.
            config_path (Optional[str]): Path to the popup configuration JSON file.
                                         Defaults to 'popup_config.json' in the same directory.
        """
        self.d = driver
        # Removed: self.helper = helper or UIHelper(driver)
        self.logger = setup_logger(self.__class__.__name__)  # Use class name for logger

        # --- Context attributes for specific watcher callbacks (like handle_suspension) ---
        # These need to be set externally before the watcher might trigger the callback
        self.airtable_client = None
        self.record_id = None
        self.package_name = None
        self.base_id = None
        self.table_id = None
        self._suspension_handled = False  # Flag to prevent multiple handling runs

        # Load the config for popups/watchers from the config file.
        self.config = get_popup_config()
        # --- End context attributes ---

        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "popup_config.json")
        self.config = self._load_config(config_path)

    def set_context(
        self,
        airtable_client=None,
        record_id=None,
        package_name=None,
        base_id=None,
        table_id=None,
    ):
        """Sets context needed for certain watcher callbacks (e.g., Airtable updates)."""
        self.logger.debug(
            f"Setting PopupHandler context: record_id={record_id}, package={package_name}"
        )
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.package_name = package_name
        self.base_id = base_id  # Needed if airtable_client needs re-scoping
        self.table_id = table_id  # Needed if airtable_client needs re-scoping
        self._suspension_handled = False  # Reset flag when context is set

    def _load_config(self, path):
        """Loads popup configuration from a JSON file."""
        if not os.path.exists(path):
            self.logger.error(f"Popup config file not found: {path}")
            # Return empty list or dict instead of raising error? Allows partial functionality.
            return []
            # raise FileNotFoundError(f"Popup config file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {path}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading config file {path}: {e}")
            return []

    # --- OCR Methods (Merged from UIHelper) ---

    def perform_ocr(self, lang: str = "pol") -> str:
        """
        Captures the current screen and performs OCR using pytesseract.

        Args:
            lang (str): The language code for Tesseract OCR (e.g., 'eng', 'pol').

        Returns:
            str: The detected text in lowercase, or an empty string on failure.
        """
        try:
            self.logger.info(f"Capturing screen for OCR (lang={lang})...")
            # Ensure screenshot format is compatible with cv2
            screenshot = self.d.screenshot(format="opencv")
            if screenshot is None:
                self.logger.error("Failed to get screenshot from device.")
                return ""
            # Convert color format for PIL
            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            # Perform OCR
            text = pytesseract.image_to_string(img_pil, lang=lang)
            self.logger.debug(f"OCR detected text: {text}")
            return text.lower()  # Return lowercase for easier matching
        except pytesseract.TesseractNotFoundError:
            self.logger.error("Tesseract OCR engine not found or not in PATH.")
            return ""
        except Exception as e:
            self.logger.error(f"OCR failed: {e}", exc_info=True)
            return ""

    def find_text_center(
        self, text_to_find: str, lang: str = "eng"
    ) -> Optional[Tuple[int, int]]:
        """
        Finds the approximate center coordinates of a given text string on the screen using OCR.

        Args:
            text_to_find (str): The text string to locate.
            lang (str): The language code for Tesseract OCR.

        Returns:
            Optional[Tuple[int, int]]: (x, y) coordinates of the text center, or None if not found.
        """
        try:
            self.logger.info(
                f"Attempting to find text center for: '{text_to_find}' using OCR (lang={lang})"
            )
            screenshot = self.d.screenshot(format="opencv")
            if screenshot is None:
                self.logger.error("Failed to get screenshot for find_text_center.")
                return None
            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            # Get detailed OCR data including bounding boxes
            data = pytesseract.image_to_data(
                img_pil, output_type=pytesseract.Output.DICT, lang=lang
            )

            text_to_find_lower = text_to_find.lower().strip()
            if not text_to_find_lower:
                return None

            n_boxes = len(data["level"])
            found_coords = []

            # Iterate through detected words to find matches
            for i in range(n_boxes):
                word_text = data["text"][i].strip().lower()
                # Simple check first
                if text_to_find_lower == word_text:
                    # Found exact word match
                    x = data["left"][i]
                    y = data["top"][i]
                    w = data["width"][i]
                    h = data["height"][i]
                    center = (x + w // 2, y + h // 2)
                    self.logger.info(
                        f"Found exact OCR match for '{text_to_find}' at {center}"
                    )
                    return center
                # TODO: Add multi-word phrase matching if needed (more complex)

            # If exact match not found (or multi-word needed), implement phrase search
            # (Keeping original phrase logic commented out for now, needs refinement)
            # candidates = []
            # for i in range(len(data['text']) - 1):
            #     phrase = ""
            #     coords_indices = []
            #     # ... (original phrase building logic) ...
            #     if text_to_find_lower in phrase.strip():
            #         # ... (calculate center from phrase bounds) ...
            #         return center

            self.logger.warning(f"No exact OCR match found for '{text_to_find_lower}'.")
            return None

        except pytesseract.TesseractNotFoundError:
            self.logger.error("Tesseract OCR engine not found or not in PATH.")
            return None
        except Exception as e:
            self.logger.error(
                f"OCR failed while finding text center: {e}", exc_info=True
            )
            return None

    # --- Watcher Registration and Management ---
    # Inside the PopupHandler class in Shared/popup_handler.py

    def register_watchers(self):
        """
        Register background popup watchers based SOLELY on the loaded configuration.
        The configuration should be a list of dictionaries, each defining a watcher.
        """
        self.logger.info("Registering popup watchers from configuration...")
        w = self.d.watcher
        w.reset()  # Clear any existing watchers first

        if not isinstance(self.config, list):
            self.logger.error("Popup config is not a list. Cannot register watchers.")
            return

        registered_count = 0
        for entry in self.config:
            name = entry.get("name")
            text_xpath = entry.get("text_xpath")  # Condition to trigger the watcher
            button_xpath = entry.get("button_xpath")  # Optional: Button to click
            callback_name = entry.get(
                "callback"
            )  # Optional: Method/function name to call

            # Basic validation
            if not name or not text_xpath:
                self.logger.warning(
                    f"Skipping invalid config entry (missing name or text_xpath): {entry}"
                )
                continue

            # Action validation: Must have either a button or a callback
            if not button_xpath and not callback_name:
                self.logger.warning(
                    f"Watcher '{name}' has neither 'button_xpath' nor 'callback' defined. Skipping action."
                )
                continue
            if button_xpath and callback_name:
                self.logger.warning(
                    f"Watcher '{name}' has both 'button_xpath' and 'callback' defined. Prioritizing callback."
                )
                button_xpath = None  # Prioritize callback if both are present

            try:
                # Start defining the watcher with its trigger condition
                watcher_instance = w(name).when(text_xpath)

                # Add the action (callback or click)
                if callback_name:
                    # Try to find the callback method on this instance first
                    callback_method = getattr(self, callback_name, None)
                    if callable(callback_method):
                        self.logger.debug(
                            f"Registering watcher '{name}': WHEN '{text_xpath}' CALL self.'{callback_name}'"
                        )
                        watcher_instance.call(callback_method)
                        registered_count += 1
                    else:
                        # If not on instance, check if it's a globally defined function
                        # Note: This requires the callback function (like photo_removed_callback)
                        # to be imported or defined in the scope where PopupHandler is used.
                        # It's generally safer to make callbacks instance methods if they need 'self'.
                        global_callback = globals().get(callback_name)
                        if callable(global_callback):
                            self.logger.debug(
                                f"Registering watcher '{name}': WHEN '{text_xpath}' CALL global '{callback_name}'"
                            )
                            # Need to handle potential arguments d, sel passed by watcher
                            watcher_instance.call(
                                lambda d, sel: global_callback(d, sel)
                            )
                            registered_count += 1
                        else:
                            self.logger.error(
                                f"Callback '{callback_name}' not found for watcher '{name}'. Watcher action skipped."
                            )

                elif button_xpath:
                    self.logger.debug(
                        f"Registering watcher '{name}': WHEN '{text_xpath}' CLICK '{button_xpath}'"
                    )
                    watcher_instance.click(button_xpath)
                    registered_count += 1

            except Exception as e:
                self.logger.error(
                    f"Error registering watcher '{name}': {e}", exc_info=True
                )

        self.logger.info(
            f"✅ {registered_count} popup watchers registered from configuration."
        )
        # Note: Watchers are registered but not started here. Use start_watcher_loop() or d.watcher.start() externally.

    def start_watcher_loop(self, interval: float = 0.5):
        """
        Continuously run watcher checks in a background thread.
        NOTE: Ensure device.watcher.stop() is called to terminate this thread.
        """
        # Check if loop is already running
        if (
            hasattr(self, "_watcher_thread")
            and self._watcher_thread is not None
            and self._watcher_thread.is_alive()
        ):
            self.logger.info("Watcher loop already running.")
            return

        self._watcher_stop_event = threading.Event()  # Event to signal loop termination

        def loop():
            self.logger.info("📡 Watcher loop thread started.")
            while not self._watcher_stop_event.is_set():
                try:
                    # Run registered watchers
                    self.d.watcher.run()
                except Exception as e:
                    # Catch errors during watcher run (e.g., device disconnected)
                    self.logger.error(f"💥 Watcher run error: {e}", exc_info=False)
                    # Optional: Stop the loop on certain errors?
                    # self._watcher_stop_event.set()
                # Wait before next check, respecting the stop event
                self._watcher_stop_event.wait(timeout=interval)
            self.logger.info("📡 Watcher loop thread stopped.")

        # Start the loop in a daemon thread
        self._watcher_thread = threading.Thread(target=loop, daemon=True)
        self._watcher_thread.start()

    def stop_watcher_loop(self):
        """Signals the background watcher loop thread to stop."""
        if hasattr(self, "_watcher_stop_event"):
            self.logger.info("🛑 Signaling watcher loop to stop...")
            self._watcher_stop_event.set()
            # Optional: Wait for thread to finish
            if hasattr(self, "_watcher_thread") and self._watcher_thread is not None:
                self._watcher_thread.join(timeout=2.0)  # Wait briefly
                if self._watcher_thread.is_alive():
                    self.logger.warning("Watcher loop thread did not stop cleanly.")
                self._watcher_thread = None  # Clear reference
        else:
            self.logger.info("Watcher loop was not running or already stopped.")
        # Also stop the underlying uiautomator2 watcher service
        try:
            self.d.watcher.stop()
            self.d.watcher.remove()  # Remove registered watchers
            self.logger.info("🛑 Underlying uiautomator2 watcher stopped and removed.")
        except Exception as e:
            self.logger.error(f"Error stopping/removing uiautomator2 watcher: {e}")

    # --- Manual Popup Handling ---

    def handle_cookie_popup(self) -> bool:
        """Attempts to detect and dismiss cookie popups using OCR and fallback clicks."""
        try:
            self.logger.info("📋 Running OCR-based cookie popup handler")

            # Keywords to detect cookie popups
            keywords = [
                "przejdź do serwisu",
                "zaakceptuj wszystko",
                "wyrażam zgodę",
                "akceptuję",
                "akceptuję i przechodzę do serwisu",
                "zgadzam się",
                "cookie",
                "ciasteczka",
                "polityka prywatności",
                "accept all",
                "agree",
            ]
            # Text on buttons to click (case-insensitive check later)
            click_texts = [
                "PRZEJDŹ DO SERWISU",
                "Przejdź do serwisu",
                "Accept All",
                "Agree",
                "Zaakceptuj wszystko",
            ]

            # Perform OCR on the current screen
            screen_text = self.perform_ocr(
                lang="pol+eng"
            )  # Use combined languages if needed
            if not screen_text:
                self.logger.warning(
                    "OCR returned no text, cannot check for cookie popup."
                )
                return False  # Cannot determine if popup exists

            # Check if any keywords are present
            if not any(keyword in screen_text for keyword in keywords):
                self.logger.info("✅ No cookie popup keywords detected via OCR.")
                return False  # Indicate no popup was handled

            self.logger.info("⚠️ Cookie popup detected via OCR keywords.")

            # Attempt to click known dismiss buttons by text
            for text in click_texts:
                # Use case-insensitive text search if possible with uiautomator2 selectors
                # Example using XPath translate() for case-insensitivity:
                btn_xpath = f"//android.widget.Button[contains(translate(@text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                # Or simpler contains: btn_xpath = f"//android.widget.Button[contains(@text, '{text}')]"
                btn = self.d.xpath(btn_xpath)
                if btn.exists:
                    self.logger.info(
                        f"Found potential dismiss button with text similar to '{text}'. Clicking..."
                    )
                    if btn.click_exists(timeout=2):
                        self.logger.info(f"✅ Clicked cookie dismiss button: '{text}'")
                        time.sleep(2)  # Wait for popup to disappear
                        return True  # Handled

            # If text buttons fail, try fallback coordinates (less reliable)
            self.logger.warning(
                "Failed to click known text buttons, trying fallback coordinates."
            )
            webview = self.d(
                className="android.webkit.WebView"
            )  # Check if it's a webview popup
            bounds = (
                webview.info.get("bounds") if webview.exists else self.d.info
            )  # Use screen bounds if no webview
            if bounds:
                # Calculate potential button locations (heuristic)
                width = bounds.get("right", self.d.info["displayWidth"]) - bounds.get(
                    "left", 0
                )
                height = bounds.get(
                    "bottom", self.d.info["displayHeight"]
                ) - bounds.get("top", 0)
                left = bounds.get("left", 0)
                bottom = bounds.get("bottom", self.d.info["displayHeight"])

                fallback_coords = [
                    (
                        left + int(width * 0.8),
                        bottom - int(height * 0.1),
                    ),  # Bottom right-ish
                    (
                        left + int(width * 0.5),
                        bottom - int(height * 0.1),
                    ),  # Bottom center
                    (
                        left + int(width * 0.2),
                        bottom - int(height * 0.1),
                    ),  # Bottom left-ish
                ]
                for x, y in fallback_coords:
                    self.logger.info(f"⚙️ Clicking fallback coordinate ({x}, {y})")
                    self.d.click(x, y)
                    time.sleep(2)  # Wait to see if it worked
                    # Re-check OCR to see if popup disappeared
                    screen_text_after = self.perform_ocr(lang="pol+eng")
                    if not any(keyword in screen_text_after for keyword in keywords):
                        self.logger.info(
                            "✅ Cookie popup likely dismissed via fallback coordinate."
                        )
                        return True  # Handled

            self.logger.error(
                "❌ Failed to dismiss cookie popup using text or fallbacks."
            )
            return False  # Not handled

        except Exception as e:
            self.logger.error(f"💥 Error in handle_cookie_popup: {e}", exc_info=True)
            return False

    def handle_all_popups(self, delay_after_click: float = 1.0) -> int:
        """
        Manually checks for and handles popups defined in the config file.
        This is useful for explicitly clearing the screen before a critical step.

        Args:
            delay_after_click (float): Time to wait after successfully clicking a dismiss button.

        Returns:
            int: The number of popups handled in this pass.
        """
        handled_count = 0
        self.logger.debug("Manually handling all configured popups...")
        if not isinstance(self.config, list):
            self.logger.warning(
                "Popup config is not a list, cannot run handle_all_popups."
            )
            return 0

        for entry in self.config:
            name = entry.get("name", "Unnamed Popup")
            text_xpath = entry.get("text_xpath")
            button_xpath = entry.get("button_xpath")
            # container_xpath = entry.get("container_xpath") # Optional for stricter check

            if not text_xpath or not button_xpath:
                self.logger.warning(
                    f"⚠️ Skipping configured popup '{name}' due to missing XPaths"
                )
                continue

            try:
                # Check if the popup text/identifier exists
                popup_present = self.d.xpath(text_xpath).exists
                if popup_present:
                    self.logger.info(f"📌 Detected popup manually: {name}")
                    dismiss_btn = self.d.xpath(button_xpath)
                    clicked = False

                    if dismiss_btn.wait(timeout=1):  # Wait briefly for button
                        # Try clicking multiple times if needed
                        for attempt in range(2):
                            if dismiss_btn.click_exists(timeout=1):
                                clicked = True
                                self.logger.info(
                                    f"Clicked dismiss button for '{name}' (attempt {attempt+1})"
                                )
                                break  # Exit retry loop on success
                            else:
                                self.logger.warning(
                                    f"Click attempt {attempt+1} failed for '{name}' button."
                                )
                                time.sleep(0.5)  # Wait before retry

                        if clicked:
                            time.sleep(delay_after_click)  # Wait after successful click
                            # Verify dismissal (optional but good)
                            if not self.d.xpath(text_xpath).exists:
                                self.logger.info(f"✅ Dismissed popup: {name}")
                                handled_count += 1
                            else:
                                self.logger.warning(
                                    f"⚠️ Popup '{name}' still visible after clicking dismiss button."
                                )
                        else:
                            self.logger.error(
                                f"❌ Failed to click dismiss button for popup: {name} ({button_xpath})"
                            )
                    else:
                        self.logger.warning(
                            f"Popup '{name}' detected, but dismiss button not found: {button_xpath}"
                        )
                # else:
                #    self.logger.debug(f"Configured popup not present: {name}")
            except Exception as e:
                self.logger.error(
                    f"💥 Error handling configured popup '{name}': {e}", exc_info=True
                )

        self.logger.debug(f"Manual popup handling finished. Handled: {handled_count}")
        return handled_count

    # --- Specific Handler Callbacks (used by watchers) ---

    def handle_suspension(self, selector=None):  # Match watcher call signature
        """Callback function triggered by the 'account_suspended' watcher."""
        # Use instance logger
        self.logger.warning("🚫 WATCHER: Account suspended popup detected!")
        try:
            # Prevent multiple executions if watcher triggers rapidly
            if self._suspension_handled:
                self.logger.info("⏭️ Suspension already handled in this context.")
                return

            # Check if necessary context (Airtable client, record ID) was set
            if not self.record_id or not self.airtable_client:
                self.logger.error(
                    "❌ Cannot handle suspension: Missing record_id or Airtable client context in PopupHandler."
                )
                return

            # Update Airtable record
            self.logger.info(
                f"Updating Airtable record {self.record_id} status to 'Banned'."
            )
            # Re-assign base/table IDs if client is shared and might change context
            if self.base_id:
                self.airtable_client.base_id = self.base_id
            if self.table_id:
                self.airtable_client.table_id = self.table_id
            success = self.airtable_client.update_record_fields(
                self.record_id, {"Status": "Banned"}
            )
            if success:
                self.logger.info("✅ Updated Airtable: Status = 'Banned'")
            else:
                self.logger.error("❌ Failed to update Airtable status to 'Banned'.")

            # Stop the suspended app instance
            if self.package_name:
                self.logger.info(f"🛑 Stopping suspended app: {self.package_name}")
                try:
                    self.d.app_stop(self.package_name)
                    # Optional: Add ADB force-stop as fallback if needed
                    # subprocess.run(...)
                except Exception as stop_e:
                    self.logger.error(
                        f"Error stopping suspended app {self.package_name}: {stop_e}"
                    )
            else:
                self.logger.warning(
                    "⚠️ Cannot stop suspended app: package_name context not set."
                )

            # Set flag to prevent re-handling
            self._suspension_handled = True
            # Optionally, trigger the global failure event
            # global failure_triggered
            # failure_triggered.set()

        except Exception as e:
            self.logger.error(
                f"💥 Error in handle_suspension callback: {e}", exc_info=True
            )


# --- External Callback Example (Needs to be defined globally or imported) ---
def photo_removed_callback(d, sel):
    """Example callback for the 'photo_removed_popup' watcher."""
    # Use the module-level logger or pass one in if needed
    logger.info("🚫 WATCHER: 'Photo removed' popup detected!")
    try:
        logger.info(f"Matched element info: {sel.info}")
    except Exception as e:
        logger.error(f"Error retrieving element info in callback: {e}")

    # Try to click "Cancel" using different strategies
    # TODO: Refactor XPaths
    cancel_xpath_1 = "^@Cancel"  # uiautomator2 shorthand for content-desc
    cancel_xpath_2 = '//android.widget.Button[@content-desc="Cancel"]'
    cancel_xpath_3 = '//android.widget.Button[@text="Cancel"]'  # Added text check

    for i, xpath in enumerate([cancel_xpath_1, cancel_xpath_2, cancel_xpath_3]):
        logger.debug(f"Trying Cancel strategy {i+1}: {xpath}")
        cancel_button = d.xpath(xpath)
        if cancel_button.exists:
            if cancel_button.click_exists(timeout=2):
                logger.info(f"✅ Clicked Cancel button using strategy {i+1}.")
                return  # Success
            else:
                logger.warning(
                    f"Found Cancel button with strategy {i+1}, but click failed."
                )
        else:
            logger.debug(f"Cancel button not found with strategy {i+1}.")

    logger.error("❌ Failed to find or click Cancel button on 'Photo removed' popup.")


# --- Test Harness (Example Usage) ---
if __name__ == "__main__":
    import logging

    # Assuming AirtableClient is importable
    from Shared.airtable_manager import AirtableClient

    # Setup logger for testing
    test_logger = logging.getLogger("TestPopupHandler")
    test_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    if not test_logger.hasHandlers():  # Prevent adding multiple handlers
        test_logger.addHandler(handler)

    try:
        test_logger.info("🔗 Connecting to device...")
        # Connect to device (replace with your device ID if needed)
        d = u2.connect()
        test_logger.info(f"✅ Connected to device: {d.serial}")

        # --- Test Context Setup ---
        # Hardcoded example context (replace with actual values for real testing)
        test_record_id = "recTESTINGID123"
        test_base_id = "appTESTINGBASEID"  # Get from env or config
        test_table_id = "tblTESTINGTABLEID"  # Get from env or config
        test_package_name = "com.instagram.android"  # Example package

        # Setup Airtable client for context
        # Ensure API key is available in environment
        airtable_client = AirtableClient()
        # Manually set base/table for testing if needed by handler context
        # airtable_client.base_id = test_base_id
        # airtable_client.table_id = test_table_id

        # Initialize PopupHandler
        popup_handler = PopupHandler(d)
        # Set the context needed for handle_suspension
        popup_handler.set_context(
            airtable_client=airtable_client,
            record_id=test_record_id,
            package_name=test_package_name,
            base_id=test_base_id,  # Pass if needed by handler
            table_id=test_table_id,  # Pass if needed by handler
        )
        # Register watchers
        popup_handler.register_watchers()

        test_logger.info(
            "🧪 Watchers registered. Manually trigger a popup on the device."
        )
        test_logger.info(
            "🧪 (e.g., try to share something that might fail, or navigate to trigger a known popup)"
        )
        test_logger.info("🧪 Monitoring for 60 seconds...")

        # Monitor watcher activity (doesn't use the background loop for this test)
        start_watch_time = time.time()
        while time.time() - start_watch_time < 60:
            d.watcher.run()
            time.sleep(0.5)

        test_logger.info("🛑 Done watching — check logs for any triggered watchers.")

        # Test manual handling (optional)
        # test_logger.info("🧪 Testing manual popup handling...")
        # handled = popup_handler.handle_all_popups()
        # test_logger.info(f"Manual handling finished, handled {handled} popups.")

        # Test OCR cookie handler (optional)
        # test_logger.info("🧪 Testing cookie popup handler...")
        # was_handled = popup_handler.handle_cookie_popup()
        # test_logger.info(f"Cookie handler result: {was_handled}")

        # Stop watchers explicitly
        d.watcher.stop()
        d.watcher.remove()
        test_logger.info("Watchers stopped and removed.")

    except ConnectionError as e:
        test_logger.error(f"💥 Test failed - Connection Error: {e}")
    except FileNotFoundError as e:
        test_logger.error(f"💥 Test failed - File Not Found (check config path?): {e}")
    except Exception as e:
        test_logger.error(f"💥 Test failed - Unhandled Exception: {e}", exc_info=True)
