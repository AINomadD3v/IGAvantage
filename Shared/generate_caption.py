import re
import os
import sys
import time
from difflib import SequenceMatcher
from typing import Optional
import uiautomator2 as u2

from logger_config import setup_logger
from stealth_typing import StealthTyper
from ai_api import generate_caption
from xpath_config import InstagramXPaths

logger = setup_logger(__name__)

# Ensure src is on path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)


class GenerateCaption:
    def __init__(self, device, app_package: str, post_type: str, logger, device_id: str = None):
        self.device = device
        self.app_package = app_package
        self.logger = logger
        self.post_type = post_type
        self.xpath_config = InstagramXPaths(app_package)
        self.xpath = '//android.widget.AutoCompleteTextView[@resource-id="com.instagram.androie:id/caption_input_text_view"]'
        self.stealth_typer = StealthTyper(device_id=device_id)

    def wait_for_caption_field(self, timeout=10):
        self.logger.info("🕵️ Waiting for caption input field...")
        field = self.device.xpath(self.xpath)
        if not field.wait(timeout=timeout):
            self.logger.error("❌ Caption input field not found.")
            return None
        self.logger.info("✅ Caption input field found.")
        return field

    def type_caption(self, caption: str):
        self.logger.info(f"✍️ Typing caption with StealthTyper: {caption}")
        self.stealth_typer.type_text(caption)
        time.sleep(2)

    def get_caption_text(self) -> str:
        field = self.device.xpath(self.xpath)
        try:
            raw = field.get(timeout=5).attrib.get('text', '')
            self.logger.debug(f"📥 Fetched caption box text: {raw}")
            return raw
        except Exception as e:
            self.logger.error(f"❌ Failed to get caption box text: {e}")
            return ""

    def captions_are_similar(self, typed: str, fetched: str) -> bool:
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)

        typed_clean = emoji_pattern.sub('', typed).lower().strip()
        fetched_clean = emoji_pattern.sub('', fetched).lower().strip()
        ratio = SequenceMatcher(None, typed_clean, fetched_clean).ratio()
        self.logger.info(f"🔍 Caption similarity: {ratio:.2f}")
        return ratio > 0.9

    def write_caption(self) -> Optional[str]:
        self.logger.info("🧠 Generating AI caption...")
        caption = generate_caption()
        self.logger.info(f"💬 AI Caption: {caption}")

        field = self.wait_for_caption_field()
        if not field:
            return None

        field.click()
        time.sleep(1)

        self.type_caption(caption)

        # Hide keyboard to reveal next button
        self.device.press("back")
        time.sleep(2)

        verified_text = self.get_caption_text()
        if not self.captions_are_similar(caption, verified_text):
            self.logger.warning("⚠️ Caption text mismatch after typing")
            return None
        else:
            self.logger.info("✅ Caption text verified successfully")

        return caption


def generate_and_enter_caption(device, app_package: str, post_type: str = "reel", device_id: Optional[str] = None) -> Optional[str]:
    try:
        caption_writer = GenerateCaption(
            device=device,
            app_package=app_package,
            post_type=post_type,
            logger=logger,
            device_id=device_id
        )
        return caption_writer.write_caption()

    except Exception as e:
        logger.error(f"💥 Error in caption entry: {str(e)}", exc_info=True)
        return None


def main():
    device = u2.connect()
    app_package = "com.instagram.androie"

    logger.info("🚀 Testing caption generation + input flow")

    try:
        caption_text = generate_and_enter_caption(device, app_package)
        if caption_text:
            logger.info(f"✅ Caption entered and advanced. Caption: {caption_text}")
        else:
            logger.error("❌ Caption entry or verification failed.")
    except Exception as e:
        logger.error(f"💥 Unhandled exception in main(): {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()


