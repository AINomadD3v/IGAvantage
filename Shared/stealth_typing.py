import subprocess
import random
import time
import logging

logger = logging.getLogger("StealthTyper")

class StealthTyper:
    def __init__(self, device_id: str = None, min_delay=0.05, max_delay=0.15, backspace_chance=0.1):
        self.device_id = device_id
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backspace_chance = backspace_chance

    def _adb_shell(self, command: str):
        base_cmd = ["adb"]
        if self.device_id:
            base_cmd += ["-s", self.device_id]
        base_cmd += ["shell", command]
        logger.debug(f"Running ADB command: {' '.join(base_cmd)}")
        subprocess.run(base_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _type_char(self, char: str):
        # Only escape characters that truly break ADB, not @
        safe_char = char.replace(" ", "%s").replace("&", "\\&").replace("'", "\\'")
        self._adb_shell(f"input text '{safe_char}'")


    def _press_backspace(self):
        self._adb_shell("input keyevent DEL")

    def type_text(self, text: str):
        logger.info(f"Typing text stealthily: {text}")
        for i, char in enumerate(text):
            self._type_char(char)
            delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(delay)

            # Random chance to simulate human backspace error
            if random.random() < self.backspace_chance and i > 0:
                logger.debug("Simulating backspace")
                self._press_backspace()
                time.sleep(random.uniform(0.05, 0.1))
                self._type_char(char)  # Re-type the character
                time.sleep(random.uniform(self.min_delay, self.max_delay))

    def press_enter(self):
        self._adb_shell("input keyevent ENTER")

    def press_tab(self):
        self._adb_shell("input keyevent 61")  # KEYCODE_TAB




