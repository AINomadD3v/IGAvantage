import time
import cv2
import random
import pytesseract
from PIL import Image
from typing import Optional, Callable
from .logger_config import setup_logger

# TODO  Change over OCR to ImageX from uiautomator2 for advanced poopups

logger = setup_logger(name='UiHelper')

class UIHelper:
    def __init__(self, driver):
        self.d = driver
        self.logger = setup_logger(self.__class__.__name__)

    def wait_for_xpath(self, xpath, timeout=30, interval=1.0, on_found: Optional[Callable[[str], None]] = None):
        self.logger.info(f"Waiting for element: {xpath}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.d.xpath(xpath).exists:
                self.logger.info(f"Element found: {xpath}")
                if on_found:
                    try:
                        on_found(xpath)
                    except Exception as e:
                        self.logger.error(f"Error in on_found callback: {e}")
                return True
            time.sleep(interval)
        self.logger.error(f"Timeout waiting for element: {xpath}")
        return False

    def perform_ocr(self, lang='pol'):
        try:
            self.logger.info("Capturing screen for OCR...")
            screenshot = self.d.screenshot(format='opencv')
            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            text = pytesseract.image_to_string(img_pil, lang=lang)
            self.logger.info(f"OCR detected text: {text}")
            return text.lower()
        except Exception as e:
            self.logger.error(f"OCR failed: {e}")
            return ""

    def get_element_center(self, element):
        try:
            bounds = element.info.get('bounds', {})
            if bounds:
                center_x = (bounds['left'] + bounds['right']) // 2
                center_y = (bounds['top'] + bounds['bottom']) // 2
                return center_x, center_y
            self.logger.warning("Element bounds not found")
            return None
        except Exception as e:
            self.logger.error(f"Error getting element center: {e}")
            return None

    def find_text_center(self, text, lang='eng'):
        try:
            self.logger.info(f"Attempting to find text center for: '{text}' using OCR")
            screenshot = self.d.screenshot(format='opencv')
            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            data = pytesseract.image_to_data(img_pil, output_type=pytesseract.Output.DICT, lang=lang)

            text = text.lower().strip()
            candidates = []

            for i in range(len(data['text']) - 1):
                phrase = ""
                coords = []
                for j in range(i, min(i + 5, len(data['text']))):
                    word = data['text'][j].strip().lower()
                    if word:
                        phrase += word + " "
                        coords.append(j)
                    if text in phrase.strip():
                        x = data['left'][coords[0]]
                        y = data['top'][coords[0]]
                        right = data['left'][coords[-1]] + data['width'][coords[-1]]
                        bottom = data['top'][coords[-1]] + data['height'][coords[-1]]
                        center = ((x + right) // 2, (y + bottom) // 2)
                        self.logger.info(f"Found partial match '{phrase.strip()}' for '{text}' at {center}")
                        return center
                candidates.append(phrase.strip())

            self.logger.warning(f"No match found for '{text}' via OCR. Candidates: {candidates}")
            return None

        except Exception as e:
            self.logger.error(f"OCR failed while finding text center: {e}")
            return None

    def smart_button_clicker(self, text: str, fallback_xpath: Optional[str] = None, timeout: int = 10) -> bool:
        try:
            self.logger.info(f"Attempting smart click on button with text: '{text}'")
            button = self.d.xpath(f'//android.widget.Button[contains(@text, "{text}")]')

            start_time = time.time()
            while time.time() - start_time < timeout:
                if button.exists:
                    if button.click_exists(timeout=3):
                        self.logger.info(f"✅ Successfully clicked button using text: '{text}'")
                        return True
                time.sleep(1)

            if fallback_xpath:
                self.logger.warning(f"Primary match failed. Trying fallback XPath: {fallback_xpath}")
                fb_button = self.d.xpath(fallback_xpath)
                if fb_button.exists and fb_button.click_exists(timeout=3):
                    self.logger.info(f"✅ Successfully clicked button using fallback XPath")
                    return True

            self.logger.error(f"❌ Failed to click button with text: '{text}'")
            return False

        except Exception as e:
            self.logger.error(f"Error in smart button click: {e}")
            return False

    def click_with_fallback(self, xpath=None, fallback_coords=None, timeout=5):
        try:
            if xpath and self.d.xpath(xpath).exists:
                element = self.d.xpath(xpath)
                if element.click_exists(timeout=timeout):
                    self.logger.info(f"Clicked element: {xpath}")
                    return True

            if fallback_coords:
                self.logger.info(f"Falling back to coordinates: {fallback_coords}")
                x, y = fallback_coords
                self.d.click(x, y)
                return True

            self.logger.error("Click failed: no valid xpath or fallback coordinates")
            return False

        except Exception as e:
            self.logger.error(f"Click with fallback failed: {e}")
            return False

    def click_show_password_icon(self, password_xpath):
        try:
            password_input = self.d.xpath(password_xpath)
            if not password_input.exists:
                self.logger.error("Password field not found for show icon detection")
                return False

            pw_bounds = password_input.info.get('bounds')
            if not pw_bounds:
                self.logger.error("Could not retrieve bounds of password field")
                return False

            pw_center_y = (pw_bounds['top'] + pw_bounds['bottom']) // 2
            pw_right = pw_bounds['right']

            closest_button = None
            min_dist = float('inf')

            for button in self.d.xpath('//android.widget.Button').all():
                btn_bounds = button.info.get('bounds')
                if not btn_bounds:
                    continue

                btn_center_y = (btn_bounds['top'] + btn_bounds['bottom']) // 2
                btn_center_x = (btn_bounds['left'] + btn_bounds['right']) // 2

                if abs(btn_center_y - pw_center_y) > 100:
                    continue

                dist = abs(btn_center_x - pw_right)

                if dist < min_dist:
                    closest_button = button
                    min_dist = dist

            if closest_button:
                center = self.get_element_center(closest_button)
                if center:
                    self.logger.info(f"Clicking closest show password button at: {center}")
                    self.d.click(*center)
                    return True

            self.logger.warning("No matching show-password icon found near password field")
            return False

        except Exception as e:
            self.logger.error(f"Error clicking show password icon: {e}")
            return False

    def tap_random_within_element(self, xpath: str, label: str = "element", timeout: int = 5) -> bool:
        try:
            el = self.d.xpath(xpath)
            if not el.wait(timeout=timeout):
                self.logger.warning(f"{label} not found: {xpath}")
                return False

            bounds = el.get().info.get("bounds", {})
            return self._tap_random_in_bounds(bounds, label)

        except Exception as e:
            self.logger.error(f"Error clicking {label}: {e}")
            return False

    def _tap_random_in_bounds(self, bounds_input, label: str = "element", offset: int = 8) -> bool:
        try:
            if isinstance(bounds_input, dict):
                left = bounds_input["left"]
                top = bounds_input["top"]
                right = bounds_input["right"]
                bottom = bounds_input["bottom"]
                bounds_str = f"[{left},{top}][{right},{bottom}]"
            else:
                bounds_str = bounds_input
                left, top, right, bottom = map(int, bounds_str.strip("[]").replace("][", ",").split(","))

            x = random.randint(left + offset, right - offset)
            y = random.randint(top + offset, bottom - offset)
            self.logger.info(f"👆 Tapping {label} randomly at ({x}, {y}) within bounds {bounds_str}")
            self.d.click(x, y)
            return True
        except Exception as e:
            self.logger.error(f"Error during tap on {label}: {e}")
            return False



    def scroll_up(self, scale: float = 0.8):
        self.logger.debug(f"Scrolling up with scale={scale}")
        self.d.swipe_ext("up", scale=scale)

    def find_prompt_xpath(self, keywords: list[str], timeout=10) -> Optional[str]:
        self.logger.info(f"Searching for prompt matching: {keywords}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            elements = self.d.xpath('//*').all()
            for el in elements:
                text = (el.attrib.get('text') or '').lower()
                desc = (el.attrib.get('content-desc') or '').lower()
                for keyword in keywords:
                    if keyword.lower() in text or keyword.lower() in desc:
                        xpath = el.get_xpath()
                        self.logger.info(f"✅ Matched keyword '{keyword}' in element: {xpath}")
                        return xpath
            time.sleep(1)
        self.logger.warning("❌ No prompt found matching keywords")
        return None

class PageDetector:
    def __init__(self, driver, helper=None):
        self.d = driver
        self.helper = helper
        self.logger = setup_logger(self.__class__.__name__)

    def detect(self):
        page_checks = [
            ("explore", self._is_explore_page),
            ("reels", self._is_reels_page),
            ("home", self._is_home_page),
            ("profile", self._is_profile_page),
            ("notifications", self._is_notifications_page),
        ]

        for name, fn in page_checks:
            if fn():
                self.logger.info(f"📍 Detected page: {name}")
                return name

        self.logger.warning("❓ Unknown page")
        return "unknown"

    def _is_explore_page(self):
        return self.d.xpath('//android.widget.TextView[@text="Explore"]').exists

    def _is_reels_page(self):
        return self.d.xpath('//android.widget.TextView[@text="Reels"]').exists

    def _is_home_page(self):
        return self.d.xpath('//android.widget.TextView[@text="Home"]').exists

    def _is_profile_page(self):
        return self.d.xpath('//android.widget.TextView[@text="Edit profile"]').exists

    def _is_notifications_page(self):
        return self.d.xpath('%All caught up%').exists


class PageRouter:
    def __init__(self, driver, helper):
        self.d = driver
        self.helper = helper
        self.detector = PageDetector(driver, helper)
        self.logger = setup_logger(self.__class__.__name__)

    def dispatch(self):
        page = self.detector.detect()

        if page == "explore":
            return self.handle_explore()
        elif page == "reels":
            return self.handle_reels()
        elif page == "profile":
            return self.handle_profile()
        elif page == "notifications":
            return self.handle_notifications()
        else:
            self.logger.warning("No handler defined for unknown page")
            return False

    def handle_explore(self):
        self.logger.info("✨ Handling Explore page (stub)")
        # TODO: Add real logic
        return True

    def handle_reels(self):
        self.logger.info("🎥 Handling Reels page (stub)")
        # TODO: Add real logic
        return True

    def handle_profile(self):
        self.logger.info("👤 Handling Profile page (stub)")
        # TODO: Add real logic
        return True

    def handle_notifications(self):
        self.logger.info("🔔 Handling Notifications page (stub)")
        # TODO: Add real logic
        return True

