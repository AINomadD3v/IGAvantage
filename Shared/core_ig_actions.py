# Shared.core_ig_actions.py

import random
import time
import math

from .logger_config import setup_logger
import subprocess
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

import random
import time
import math
import logging

logger = logging.getLogger("Scroller")

class SwipeHelper:
    def __init__(self, device):
        self.device = device

    def _curved_path(self, start, end, steps=20, max_arc_x=30, jitter_y=3, intensity="medium"):
        x1, y1 = start
        x2, y2 = end
        path = []

        # Apply intensity presets
        if intensity == "gentle":
            max_arc_x = 10
            jitter_y = 1
        elif intensity == "chaotic":
            max_arc_x = 50
            jitter_y = 6
        # "medium" is default

        for i in range(steps + 1):
            t = i / steps
            arc_offset = math.sin(t * math.pi) * random.uniform(-max_arc_x, max_arc_x)
            jitter = random.uniform(-jitter_y, jitter_y)
            x = x1 + (x2 - x1) * t + arc_offset
            y = y1 + (y2 - y1) * t + jitter
            path.append((int(x), int(y)))

        return path

    def _perform_path_swipe(self, path, total_duration_ms):
        interval = total_duration_ms / len(path)
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            dur = int(interval)
            self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {dur}")
            time.sleep(interval / 1000.0)

    def curved_swipe(self, start, end, duration=400, intensity="medium"):
        logger.info(f"🌀 Executing curved swipe: {start} → {end} over {duration}ms (style: {intensity})")
        path = self._curved_path(start, end, steps=20, intensity=intensity)
        self._perform_path_swipe(path, total_duration_ms=duration)

    def curved_tap(self, target_x, target_y, arc_radius=80, steps=10):
        """Simulate a curved tap motion ending at (target_x, target_y)."""
        start_x = target_x - random.randint(arc_radius // 2, arc_radius)
        start_y = target_y + random.randint(arc_radius // 2, arc_radius)

        logger.info(f"👆 Curved tap from ({start_x}, {start_y}) to ({target_x}, {target_y})")

        path = self._curved_path(
            start=(start_x, start_y),
            end=(target_x, target_y),
            steps=steps,
            max_arc_x=15,
            jitter_y=2,
            intensity="gentle"
        )
        self._perform_path_swipe(path, total_duration_ms=100 + random.randint(50, 120))

    def human_scroll_up(self):
        """Scroll up in a controlled human-like way (downward swipe)."""
        x = random.randint(500, 580)
        y_start = random.randint(1200, 1400)
        y_end = random.randint(600, 800)  # Must be LESS than y_start to swipe downward
        dur = random.randint(300, 600)
        intensity = random.choice(["gentle", "medium"])

        # Ensure swipe goes downward on screen
        if y_start <= y_end:
            y_start, y_end = y_end + 200, y_end  # force downward movement

        self.curved_swipe(start=(x, y_start), end=(x, y_end), duration=dur, intensity=intensity)


    def human_scroll_down(self):
        """Scroll down (reverse) in a human-like way."""
        x = random.randint(500, 580)
        y_start = random.randint(600, 800)
        y_end = random.randint(1200, 1400)
        dur = random.randint(300, 600)
        intensity = random.choice(["gentle", "medium", "chaotic"])

        self.curved_swipe(start=(x, y_start), end=(x, y_end), duration=dur, intensity=intensity)

    def human_like_scroll(self):
        """Human-like scrolls, constrained to proper downward direction."""
        mode = random.choice(["standard", "jitter"])
        logger.info(f"↕️ Human scroll mode: {mode}")

        if mode == "standard":
            self.human_scroll_up()

        elif mode == "jitter":
            self.human_scroll_up()
            time.sleep(random.uniform(0.1, 0.3))
            self.human_scroll_up()


    def simulate_peek(self, reel_post):
        """Taps a reel briefly and presses back to mimic curiosity."""
        if random.random() < 0.2:  # 20% chance to peek
            logger.info(f"👀 Simulating peek on reel @{reel_post['username']}")
            try:
                reel_xpath = f'//android.widget.ImageView[@content-desc="{reel_post["desc"]}"]'
                el = self.device.xpath(reel_xpath).get(timeout=2.0)
                el.click()
                time.sleep(random.uniform(1.0, 2.0))
                self.device.press("back")
                time.sleep(1.0)
                return True
            except Exception as e:
                logger.warning(f"⚠️ Failed peek: {e}")
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

