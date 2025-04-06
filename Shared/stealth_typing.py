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
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def set_adb_keyboard(self):
        logger.info("Activating ADBKeyBoard")
        self._adb_shell("ime enable com.android.adbkeyboard/.AdbIME")
        self._adb_shell("ime set com.android.adbkeyboard/.AdbIME")

    def _send_adb_input(self, text: str):
        safe_text = text.replace('"', '\\"')
        self._adb_shell(f'am broadcast -a ADB_INPUT_TEXT --es msg "{safe_text}"')

    def clear_field_before_typing(self, xpath: str):
        logger.info("Checking field for existing text")
        try:
            el = self.d.xpath(xpath).get(timeout=5.0)
            current = el.text or ""
            if current.strip():
                logger.info(f"Clearing {len(current)} chars: {current}")
                el.click()
                time.sleep(0.3)
                self.d.long_click(*el.center())  # Long click to trigger cursor/focus
                time.sleep(0.3)
                self._adb_shell("input keyevent 123")  # KEYCODE_MOVE_END
                time.sleep(0.2)
                for _ in range(len(current)):
                    self.d.press("DEL")
                    time.sleep(0.05)
            else:
                logger.info("Field is already empty")
        except Exception as e:
            logger.warning(f"Could not clear field: {e}")


    def type_text(self, text: str, clear_xpath: str = None):
        text = text.strip()
        if clear_xpath:
            self.clear_field_before_typing(clear_xpath)

        logger.info(f"Typing text via ADBKeyBoard: {text}")
        start_time = time.time()
        total_chars = len(text)

        words = text.split()
        for i, word in enumerate(words):
            self._send_adb_input(word)
            time.sleep(self.base_delay * len(word) + random.uniform(*TYPING_DELAY_RANGE))
            if i < len(words) - 1:
                self._send_adb_input(" ")

        elapsed = time.time() - start_time
        actual_wpm = (total_chars / 5) / (elapsed / 60)
        logger.info(f"Typed {total_chars} chars (~{actual_wpm:.1f} WPM) in {elapsed:.2f}s")


    def press_enter(self):
        self._adb_shell("input keyevent ENTER")

    def press_tab(self):
        self._adb_shell("input keyevent 61")


# === TEST HARNESS ===

def main():
    logging.basicConfig(level=logging.INFO)
    test_text = "Hello 👋 this is a caption with emojis 🔥🚀💬"
    caption_xpath = '//android.widget.AutoCompleteTextView[@resource-id="com.instagram.androie:id/caption_input_text_view"]'

    typer = StealthTyper()
    typer.type_text(test_text, clear_xpath=caption_xpath)
    typer.press_enter()

if __name__ == "__main__":
    main()

