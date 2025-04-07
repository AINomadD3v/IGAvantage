from .logger_config import setup_logger
import subprocess
import time
import uiautomator2 as u2
from Shared.ui_helper import UIHelper

logger = setup_logger(__name__)

def launch_app_via_adb(device_id, package_name):
    logger.info(f"🔧 Launching {package_name} via ADB (monkey shell)")
    try:
        subprocess.run([
            "adb", "-s", device_id, "shell",
            "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1"
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ ADB launch failed: {e}")


def bring_app_to_foreground(
    d: u2.Device,
    package_name: str,
    check_xpath: str = None,
    timeout: int = 10,
    max_retries: int = 3
) -> bool:
    """
    Brings the specified app to the foreground and optionally waits for a screen element.

    Args:
        d: uiautomator2.Device instance.
        package_name (str): Package name to bring to the foreground.
        check_xpath (str, optional): XPath to confirm the app screen is ready.
        timeout (int): Timeout for XPath presence.
        max_retries (int): Retry attempts.

    Returns:
        bool: True if the app screen is visible, False otherwise.
    """
    package_name = package_name.strip()
    logger.info(f"📱 Attempting to bring '{package_name}' to the foreground without restarting...")

    helper = UIHelper(d)

    for attempt in range(1, max_retries + 1):
        logger.info(f"🔁 Attempt {attempt}/{max_retries}")

        try:
            d.app_start(package_name, stop=False)
            time.sleep(3)

            if check_xpath:
                logger.info(f"🔍 Waiting for expected screen element: {check_xpath}")
                if helper.wait_for_xpath(check_xpath, timeout=timeout):
                    logger.info("✅ App screen is visible (XPath matched)")
                    return True
                else:
                    logger.warning("⚠️ App started, but expected screen not visible")
            else:
                logger.info("✅ App started (no XPath check requested)")
                return True

        except Exception as e:
            logger.error(f"❌ Exception while foregrounding app: {e}")

        time.sleep(1)

    logger.error(f"❌ Failed to bring '{package_name}' to foreground with visible screen after {max_retries} attempts.")
    return False

if __name__ == "__main__":
    package_name = "com.instagram.androky"  # Correct package name for Instagram

    logger.info("🔌 Connecting to device...")
    d = u2.connect()
    logger.info(f"📱 Connected to device: {d.serial}")

    current = d.app_current().get("package", "")
    logger.info(f"🔍 Current foreground app before: {current}")

    success = bring_app_to_foreground(d, package_name)

    logger.info(f"✅ bring_app_to_foreground result: {success}")

