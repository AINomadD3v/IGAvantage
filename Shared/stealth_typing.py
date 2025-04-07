import subprocess
import random
import time
import logging
import uiautomator2 as u2

# === CONFIG ===
TARGET_WPM = 75
TYPING_DELAY_RANGE = (0.05, 0.1)

logger = logging.getLogger("StealthTyper")

class StealthTyper:
    def __init__(self, device_id: str = None):
        self.device_id = device_id
        self.base_delay = 60 / (TARGET_WPM * 5)
        self.d = u2.connect(device_id)
        self.set_adb_keyboard()

    def _adb_shell(self, command: str):
        cmd = ["adb"]
        if self.device_id:
            cmd += ["-s", self.device_id]
        cmd += ["shell", command]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()


    def set_adb_keyboard(self):
        logger.info("Activating ADBKeyBoard")
        self._adb_shell("ime enable com.android.adbkeyboard/.AdbIME")
        self._adb_shell("ime set com.android.adbkeyboard/.AdbIME")

    def _send_adb_input(self, text: str):
        safe_text = text.replace('"', '\\"')
        self._adb_shell(f'am broadcast -a ADB_INPUT_TEXT --es msg "{safe_text}"')

    def clear_field_before_typing(self, xpath: str):
        logger.info("🧹 Checking field for existing text")
        try:
            el = self.d.xpath(xpath).get(timeout=3.0)
            logger.info(f"🧼 Field found: {el}")
            current = el.text or ""
            if current.strip():
                logger.info(f"Clearing {len(current)} chars: '{current}'")
                el.click()
                time.sleep(0.3)
                self.d.long_click(*el.center())
                time.sleep(0.3)
                self._adb_shell("input keyevent 123")
                time.sleep(0.2)
                for _ in range(len(current)):
                    self.d.press("DEL")
                    time.sleep(0.05)
            else:
                logger.info("✅ Field already empty")
        except Exception as e:
            logger.warning(f"⚠️ Could not clear field: {e}")



    def type_text(self, text: str):
        text = text.strip()
        logger.info(f"Typing text using adb shell input: {text}")

        try:
            self.d.clear_text()
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"⚠️ clear_text() failed: {e}")

        # ADB shell input requires escaping spaces
        safe_text = text.replace(" ", "%s")
        command = f'input text "{safe_text}"'

        try:
            self._adb_shell(command)
            time.sleep(1)
            logger.info("✅ Text input sent via adb shell input")
        except Exception as e:
            logger.error(f"❌ Failed to type via adb shell input: {e}")

    def type_caption_with_emojis(self, caption: str):
        """
        Types a full caption (including emojis) using custom ADB keyboard via broadcast.
        Assumes the input field is already focused and visible.
        """
        caption = caption.strip()
        logger.info(f"📝 Typing caption with emojis: {caption}")

        # 1. Set ADBKeyboard as IME
        self.set_adb_keyboard()
        time.sleep(0.5)  # Give time for IME to activate

        # 2. Clear existing text if any (assumes field is already focused)
        try:
            self.d.clear_text()
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"⚠️ clear_text() failed: {e}")

        # 3. Send full caption (including emojis) via broadcast
        try:
            self._send_adb_input(caption)
            time.sleep(1.5)
            logger.info("✅ Caption broadcast sent via ADB keyboard")
        except Exception as e:
            logger.error(f"❌ Failed to type caption via broadcast: {e}")

        # 4. Optional: log what’s now in the field
        focused = self.d(focused=True)
        if focused.exists:
            field_text = focused.info.get("text", "")
            logger.info(f"🕵️ Text field now contains: {field_text}")
        else:
            logger.warning("⚠️ No focused field found for verification")






    def press_enter(self):
        self._adb_shell("input keyevent ENTER")

    def press_tab(self):
        self._adb_shell("input keyevent 61")


# === TEST HARNESS ===

TEST_XPATH = '//android.widget.EditText'  # Simplified for now, use your full one if needed
FULL_XPATH = '//android.widget.FrameLayout[@resource-id="com.instagram.androkp:id/layout_container_main"]/android.widget.FrameLayout/android.widget.FrameLayout[2]/android.widget.FrameLayout[1]/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup[1]/android.view.ViewGroup/android.view.ViewGroup/android.widget.EditText'


def test_stealth_typing(device_id, xpath=FULL_XPATH):
    logger.info(f"🔌 Connecting to device {device_id}")
    d = u2.connect(device_id)
    typer = StealthTyper(device_id)

    logger.info(f"🔍 Waiting for field at XPath: {xpath}")
    el = d.xpath(xpath)
    if not el.wait(timeout=10):
        logger.error("❌ Field not found")
        return

    logger.info("✅ Field found. Clicking to focus...")
    el.click()
    time.sleep(1)

    logger.info("🔤 Clearing text with clear_text()")
    try:
        d.clear_text()
        time.sleep(0.3)
    except Exception as e:
        logger.warning(f"⚠️ clear_text() failed: {e}")

    logger.info("⌨️ Typing test string: 'test_username_123'")
    typer.type_text("test_username_123")

    logger.info("🧪 Done. Verify field contains text manually.")


if __name__ == "__main__":
    test_stealth_typing(device_id="R5CR7027Y7W")
#
#
# def main():
#     logging.basicConfig(level=logging.INFO)
#     test_text = "Hello 👋 this is a caption with emojis 🔥🚀💬"
#     caption_xpath = '//android.widget.AutoCompleteTextView[@resource-id="com.instagram.androie:id/caption_input_text_view"]'
#
#     typer = StealthTyper()
#     typer.type_text(test_text, clear_xpath=caption_xpath)
#     typer.press_enter()
#
# if __name__ == "__main__":
#     main()
#
