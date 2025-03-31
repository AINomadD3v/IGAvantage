import uiautomator2 as u2
import time
from Shared.popup_handler import PopupHandler
from Shared.ui_helper import UIHelper
from Shared.logger_config import setup_logger

logger = setup_logger("PopupWatcherTest")

def test_popup_watcher():
    logger.info("🔌 Connecting to device...")
    d = u2.connect()
    logger.info(f"📱 Connected to: {d.device_info.get('serial')}")

    logger.info("🧪 Initializing PopupHandler and watchers...")
    popup_handler = PopupHandler(d, helper=UIHelper(d))
    popup_handler.register_watchers()

    logger.info("🕵️ Watchers registered. Waiting for popup to trigger callback...")

    # Keep process alive so watcher can respond
    try:
        for i in range(30):
            logger.info(f"⏳ Waiting... ({i+1}/30)")
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")

    logger.info("✅ Test script finished")

if __name__ == "__main__":
    test_popup_watcher()

