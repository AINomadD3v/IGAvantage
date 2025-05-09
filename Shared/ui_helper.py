# Shared/ui_helper.py

import cv2
import pytesseract
from PIL import Image

from .logger_config import setup_logger

# TODO  Change over OCR to ImageX from uiautomator2 for advanced poopups
logger = setup_logger(name="UiHelper")


class UIHelper:
    def __init__(self, driver):
        self.d = driver
        self.logger = setup_logger(self.__class__.__name__)

    def perform_ocr(self, lang="pol"):
        try:
            self.logger.info("Capturing screen for OCR...")
            screenshot = self.d.screenshot(format="opencv")
            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            text = pytesseract.image_to_string(img_pil, lang=lang)
            self.logger.info(f"OCR detected text: {text}")
            return text.lower()
        except Exception as e:
            self.logger.error(f"OCR failed: {e}")
            return ""

    def find_text_center(self, text, lang="eng"):
        try:
            self.logger.info(f"Attempting to find text center for: '{text}' using OCR")
            screenshot = self.d.screenshot(format="opencv")
            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            data = pytesseract.image_to_data(
                img_pil, output_type=pytesseract.Output.DICT, lang=lang
            )

            text = text.lower().strip()
            candidates = []

            for i in range(len(data["text"]) - 1):
                phrase = ""
                coords = []
                for j in range(i, min(i + 5, len(data["text"]))):
                    word = data["text"][j].strip().lower()
                    if word:
                        phrase += word + " "
                        coords.append(j)
                    if text in phrase.strip():
                        x = data["left"][coords[0]]
                        y = data["top"][coords[0]]
                        right = data["left"][coords[-1]] + data["width"][coords[-1]]
                        bottom = data["top"][coords[-1]] + data["height"][coords[-1]]
                        center = ((x + right) // 2, (y + bottom) // 2)
                        self.logger.info(
                            f"Found partial match '{phrase.strip()}' for '{text}' at {center}"
                        )
                        return center
                candidates.append(phrase.strip())

            self.logger.warning(
                f"No match found for '{text}' via OCR. Candidates: {candidates}"
            )
            return None

        except Exception as e:
            self.logger.error(f"OCR failed while finding text center: {e}")
            return None


# TODO: Implement this class

# class PageRouter:
#     def __init__(self, driver, helper):
#         self.d = driver
#         self.helper = helper
#         self.detector = PageDetector(driver, helper)
#         self.logger = setup_logger(self.__class__.__name__)
#
#     def dispatch(self):
#         page = self.detector.detect()
#
#         if page == "explore":
#             return self.handle_explore()
#         elif page == "reels":
#             return self.handle_reels()
#         elif page == "profile":
#             return self.handle_profile()
#         elif page == "notifications":
#             return self.handle_notifications()
#         else:
#             self.logger.warning("No handler defined for unknown page")
#             return False
#
#     def handle_explore(self):
#         self.logger.info("✨ Handling Explore page (stub)")
#         # TODO: Add real logic
#         return True
#
#     def handle_reels(self):
#         self.logger.info("🎥 Handling Reels page (stub)")
#         # TODO: Add real logic
#         return True
#
#     def handle_profile(self):
#         self.logger.info("👤 Handling Profile page (stub)")
#         # TODO: Add real logic
#         return True
#
#     def handle_notifications(self):
#         self.logger.info("🔔 Handling Notifications page (stub)")
#         # TODO: Add real logic
#         return True
