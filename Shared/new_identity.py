import time
import logging
import uiautomator2 as u2

logger = logging.getLogger(__name__)


import time
import logging
import uiautomator2 as u2

logger = logging.getLogger(__name__)


class NewIdentityHandler:
    def __init__(self, driver: u2.Device):
        self.d = driver

    def handle_notification(self, text: str, timeout: int = 10) -> bool:
        logger.info("🔽 Performing manual swipe to open notification panel")
        width, height = self.d.window_size()
        x = width // 2
        self.d.swipe(x, int(height * 0.01), x, int(height * 0.5), 0.2)
        time.sleep(2)

        end_time = time.time() + timeout

        while time.time() < end_time:
            logger.info(f"🔍 Searching for notifications with text: '{text}'")
            matches = self.d.xpath(f'//android.widget.TextView[contains(@text, "{text}")]').all()

            if not matches:
                logger.info("🔁 No matching notifications found yet, retrying...")
                time.sleep(1)
                continue

            logger.info(f"📦 Found {len(matches)} matching notification(s)")

            for i, el in enumerate(matches):
                try:
                    notif_xpath = el.get_xpath()

                    containers = self.d.xpath('//android.widget.FrameLayout[contains(@resource-id, "expandableNotificationRow")]').all()
                    selected_container = None
                    for container in containers:
                        if notif_xpath.startswith(container.get_xpath()):
                            selected_container = container
                            break

                    if not selected_container:
                        logger.warning("⚠️ No container found for this notification — skipping")
                        continue

                    container_xpath = selected_container.get_xpath()
                    logger.info(f"🔗 Notification {i+1}: container_xpath = {container_xpath}")

                    # Expand if collapsed
                    expand_xpath = container_xpath + '//android.widget.ImageView[contains(@resource-id, "expand_button")]'
                    if self.d.xpath(expand_xpath).exists:
                        logger.info("⤵️ Expanding notification")
                        self.d.xpath(expand_xpath).click()
                        time.sleep(0.5)

                    # Confirm Firefox source
                    firefox_xpath = container_xpath + '//android.widget.TextView[@resource-id="android:id/app_name_text" and contains(@text, "Firefox")]'
                    if not self.d.xpath(firefox_xpath).exists:
                        logger.info("⛔ Not a Firefox notification — skipping")
                        continue

                    logger.info("✅ Firefox source confirmed — clicking notification")
                    self.d.xpath(container_xpath).click()
                    time.sleep(1)

                    # Wait a moment for popups to appear
                    logger.info("⏳ Waiting for post-click popups...")
                    time.sleep(5)

                    # Unified popup wait logic
                    old_version_title = "//android.widget.TextView[@resource-id='android:id/alertTitle']"
                    ok_button = "//android.widget.Button[@resource-id='android:id/button1']"
                    notif_text_xpath = "//android.widget.TextView[@resource-id='com.android.permissioncontroller:id/permission_message']"
                    notif_btn_xpath = "//android.widget.Button[@resource-id='com.android.permissioncontroller:id/permission_allow_button']"

                    logger.info("🔐 Waiting for either old version warning or permission prompt...")

                    popup_timeout = 10
                    start = time.time()
                    while time.time() - start < popup_timeout:
                        if self.d.xpath(old_version_title).exists:
                            logger.info("⚠️ Old version warning detected — clicking OK")
                            self.d.xpath(ok_button).click_exists(timeout=3)
                            time.sleep(1)
                            continue

                        if self.d.xpath(notif_text_xpath).exists:
                            logger.info("✅ Permission prompt detected — clicking Allow")
                            self.d.xpath(notif_btn_xpath).click_exists(timeout=3)
                            break

                        time.sleep(0.5)
                    else:
                        logger.info("ℹ️ No relevant popups appeared after waiting")

                    logger.info("🎯 New identity flow fully completed")
                    return True

                except Exception as e:
                    logger.warning(f"⚠️ Error processing notification: {e}")

            time.sleep(1)

        logger.error("❌ Timeout: No valid Firefox notification clicked")
        return False

def new_identity(driver: u2.Device, timeout: int = 10) -> bool:
    handler = NewIdentityHandler(driver)
    return handler.handle_notification(
        "Tap to quit the app and generate a new identity.", timeout=timeout
    )


if __name__ == "__main__":
    from .logger_config import setup_logger

    setup_logger("NotificationTest")
    logger = logging.getLogger("NotificationTest")

    d = u2.connect()
    handler = NewIdentityHandler(d)

    success = handler.handle_notification("Tap to quit the app and generate a new identity.")

    if success:
        logger.info("🎯 Notification interaction succeeded!")
    else:
        logger.warning("❌ Notification interaction failed or timed out")

