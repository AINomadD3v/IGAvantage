from .logger_config import setup_logger
import subprocess
import time
import uiautomator2 as u2

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

def bring_app_to_foreground(d, package_name: str, check_xpath: str = None, timeout: int = 10, max_retries: int = 3) -> bool:
    import subprocess
    import time
    from Shared.ui_helper import UIHelper
    logger = setup_logger(__name__)
    helper = UIHelper(d)

    logger.info(f"📱 Forcing home, then launching {package_name} using ADB monkey...")

    for attempt in range(1, max_retries + 1):
        logger.info(f"🔁 Foreground attempt {attempt}/{max_retries}")

        try:
            subprocess.run(["adb", "-s", d.serial, "shell", "input", "keyevent", "KEYCODE_HOME"], check=True)
            time.sleep(1.5)

            subprocess.run([
                "adb", "-s", d.serial, "shell",
                "monkey", "-p", package_name,
                "-c", "android.intent.category.LAUNCHER", "1"
            ], check=True)
            time.sleep(3)

        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Launch attempt failed: {e}")

        current = d.app_current().get("package", "")
        logger.info(f"📦 Current foreground package: {current}")
        if current == package_name:
            logger.info("✅ App is now in foreground")

            if check_xpath:
                logger.info(f"🔍 Waiting for UI element: {check_xpath}")
                if helper.wait_for_xpath(check_xpath, timeout=timeout):
                    logger.info("✅ Confirmed screen is ready")
                    return True
                else:
                    logger.warning("⚠️ App launched but expected screen not found")
                    return False

            return True

        # Only log warning if not foreground
        logger.warning(f"⚠️ Still not in foreground: currently at {current}")
        time.sleep(1)

    logger.error("❌ Failed to bring app to foreground after retries")
    return False

if __name__ == "__main__":
    package_name = "com.instagram.androky"

    logger.info("🔌 Connecting to device...")
    d = u2.connect()
    logger.info(f"📱 Connected to device: {d.serial}")

    current = d.app_current().get("package", "")
    logger.info(f"🔍 Current foreground app before: {current}")

    success = bring_app_to_foreground(d, package_name)

    logger.info(f"✅ bring_app_to_foreground result: {success}")
