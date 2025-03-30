import time
import logging

logger = logging.getLogger(__name__)


class NewIdentityHandler:
    def __init__(self, driver):
        self.d = driver

    def open_notification_panel(self, delay: float = 2.0):
        logger.info("🔽 Opening notification panel")
        self.d.open_notification()
        time.sleep(delay)

    def click_notification_by_text(self, search_text: str) -> bool:
        """
        Finds a notification by its text and taps its clickable parent container.
        """
        logger.info(f"🔍 Searching for notification with text: '{search_text}'")

        elements = self.d.xpath('//*[@resource-id="android:id/text"]').all()

        for el in elements:
            text = el.attrib.get("text", "")
            if search_text in text:
                logger.info(f"✅ Found matching text: '{text}'")

                # Correct way to find parent with XPath match
                parent_el = el.parent('//android.widget.FrameLayout[@resource-id="com.android.systemui:id/expandableNotificationRow"]')

                if parent_el and parent_el.info.get("clickable"):
                    bounds = parent_el.info["bounds"]
                    center_x = (bounds["left"] + bounds["right"]) // 2
                    center_y = (bounds["top"] + bounds["bottom"]) // 2
                    logger.info(f"👆 Clicking at center: ({center_x}, {center_y})")
                    self.d.click(center_x, center_y)
                    return True
                else:
                    logger.warning("⚠️ Clickable parent not found or not clickable")

        logger.warning("❌ Notification interaction failed or no match found")
        return False


    def handle_notification(self, text: str, timeout: int = 10) -> bool:
        """
        Full routine: open panel, locate notification, click it.
        """
        try:
            self.open_notification_panel()
            end_time = time.time() + timeout
            while time.time() < end_time:
                if self.click_notification_by_text(text):
                    return True
                time.sleep(1)
            logger.error("❌ Timeout: Notification not found or not clickable")
            return False
        except Exception as e:
            logger.error(f"💥 Exception while handling notification: {e}")
            return False

def new_identity(driver, timeout: int = 10) -> bool:
    """
    Public function to trigger identity reset via notification panel.
    Can be imported and called from other scripts.
    """
    handler = NewIdentityHandler(driver)
    notification_text = "Tap to quit the app and generate a new identity."
    return handler.handle_notification(notification_text, timeout=timeout)



if __name__ == "__main__":
    import uiautomator2 as u2
    from logger_config import setup_logger

    setup_logger("NotificationTest")
    logger = logging.getLogger("NotificationTest")

    try:
        logger.info("📱 Connecting to device...")
        d = u2.connect()
        logger.info(f"✅ Connected to device: {d.serial}")

        handler = NewIdentityHandler(d)

        # 🔧 Set this to the exact or partial text in your target notification
        notification_text = "Tap to quit the app and generate a new identity."

        success = handler.handle_notification(notification_text, timeout=10)

        if success:
            logger.info("🎯 Notification interaction succeeded!")
        else:
            logger.warning("❌ Notification interaction failed or timed out")

    except Exception as e:
        logger.error(f"💥 Error during test: {e}")

