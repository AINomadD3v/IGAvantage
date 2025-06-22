import logging
import time

import uiautomator2 as u2


def test_dismiss_about_reels_popup():
    logging.info("🔗 Connecting to device...")
    d = u2.connect()

    logging.info("🔍 Looking for 'About Reels' popup...")
    if d.xpath("About Reels").exists:
        logging.info("✅ 'About Reels' text found")
        time.sleep(0.5)

        share_btn = d.xpath("Share")
        if share_btn.exists:
            logging.info("📤 'Share' button found — clicking...")
            if share_btn.click_exists(timeout=3):
                logging.info("✅ Clicked 'Share' button successfully")
            else:
                logging.error("❌ Failed to click 'Share' button")
        else:
            logging.warning("❌ 'Share' button not found")
    else:
        logging.info("ℹ️ 'About Reels' popup not present")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_dismiss_about_reels_popup()

if __name__ == "__main__":
    test_dismiss_about_reels_popup()
