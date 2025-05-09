# Shared/generate_caption.py

import random
import re

# import sys # Not used directly, can be removed if src_path logic isn't strictly needed for imports now
import time
from difflib import SequenceMatcher
from typing import Optional

# Uiautomator2 might still be needed for type hints if used
import uiautomator2 as u2

# --- Import the main Instagram UI driver ---
# Adjust path if InstagramInteractions moves to Shared later
from UploadBot.instagram_actions import InstagramInteractions

# --- Local Imports ---
from .ai_api import generate_caption  # Assuming this handles AI call
from .logger_config import setup_logger
from .stealth_typing import StealthTyper

# from .xpath_config import InstagramXPaths # Keep if GenerateCaption needs direct access, otherwise use insta_actions.xpath_config


logger = setup_logger("GenerateCaption")  # Setup module-level logger

# # Ensure src is on path - This might be handled better by your project structure/PYTHONPATH
# src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# sys.path.insert(0, src_path)


class GenerateCaption:
    """
    Handles the process of generating an AI caption, typing it into the
    Instagram caption field, and verifying the input.
    Uses an InstagramInteractions instance for UI operations.
    """

    def __init__(
        self,
        insta_actions: InstagramInteractions,  # Takes the main interactions object
        post_type: str,
        # logger, # Can use the module logger or pass if needed
        # device_id: str = None # Get device_id from insta_actions if needed
    ):
        """
        Initializes the GenerateCaption class.

        Args:
            insta_actions (InstagramInteractions): The initialized UI interaction driver.
            post_type (str): The type of post (e.g., "reel").
        """
        self.insta_actions = insta_actions
        self.logger = logger  # Use module logger or self.insta_actions.logger
        self.post_type = post_type
        # Access xpath_config via insta_actions
        self.xpath_config = self.insta_actions.xpath_config
        # Initialize StealthTyper using the device from insta_actions
        self.stealth_typer = StealthTyper(device_id=self.insta_actions.device.serial)

        # Define the specific XPath for the caption field here (or preferably get from xpath_config)
        # TODO: Refactor XPath - Move to xpath_config.py (e.g., self.xpath_config.reel_caption_text_view)
        self.caption_field_xpath = '//android.widget.AutoCompleteTextView[@resource-id="com.instagram.androie:id/caption_input_text_view"]'
        # Fallback XPath just in case resource-id changes slightly
        # TODO: Refactor XPath - Move to xpath_config.py
        self.caption_field_xpath_fallback = (
            "//*[contains(@resource-id, 'caption_input_text_view')]"
        )

    def _wait_for_caption_field(self, timeout=10) -> bool:
        """Waits for the caption input field to appear."""
        self.logger.debug("🕵️ Waiting for caption input field...")
        # Use the primary XPath first
        if self.insta_actions.wait_for_element_appear(
            self.caption_field_xpath, timeout=timeout
        ):
            self.logger.debug("✅ Caption input field found (primary XPath).")
            return True
        # Try fallback XPath if primary fails
        self.logger.debug("Primary caption field XPath not found, trying fallback...")
        if self.insta_actions.wait_for_element_appear(
            self.caption_field_xpath_fallback, timeout=2
        ):  # Shorter timeout for fallback
            self.logger.debug("✅ Caption input field found (fallback XPath).")
            return True

        self.logger.error("❌ Caption input field not found using known XPaths.")
        return False

    def _type_caption_stealthily(self, caption: str):
        """Types the caption using StealthTyper."""
        self.logger.info(f"✍️ Typing caption with StealthTyper: '{caption[:50]}...'")
        # Use the type_caption_with_emojis method for better handling if available
        if hasattr(self.stealth_typer, "type_caption_with_emojis"):
            self.stealth_typer.type_caption_with_emojis(caption)
        else:
            # Fallback to basic type_text if the specific method isn't there
            self.stealth_typer.type_text(caption)
        # Remove sleep, rely on verification or waits in subsequent steps
        # time.sleep(2)

    def _get_current_caption_text(self) -> str:
        """Gets the current text from the caption field."""
        # Try primary XPath first
        text = self.insta_actions.get_element_text(self.caption_field_xpath, timeout=5)
        if text is not None:
            self.logger.debug(
                f"📥 Fetched caption box text (primary): '{text[:50]}...'"
            )
            return text
        # Try fallback XPath
        self.logger.debug("Failed to get text with primary XPath, trying fallback...")
        text = self.insta_actions.get_element_text(
            self.caption_field_xpath_fallback, timeout=2
        )
        if text is not None:
            self.logger.debug(
                f"📥 Fetched caption box text (fallback): '{text[:50]}...'"
            )
            return text

        self.logger.error("❌ Failed to get caption box text using known XPaths.")
        return ""

    def _captions_are_similar(
        self, typed: str, fetched: str, threshold: float = 0.9
    ) -> bool:
        """Compares typed vs fetched caption, ignoring emojis and case, using SequenceMatcher."""
        # Keep the existing emoji removal and comparison logic
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )
        typed_clean = emoji_pattern.sub("", typed).lower().strip()
        fetched_clean = emoji_pattern.sub("", fetched).lower().strip()
        if not typed_clean and not fetched_clean:  # Both empty after cleaning
            return True
        if not typed_clean or not fetched_clean:  # One is empty, the other isn't
            ratio = 0.0
        else:
            ratio = SequenceMatcher(None, typed_clean, fetched_clean).ratio()

        self.logger.info(
            f"🔍 Caption similarity ratio: {ratio:.2f} (Threshold: {threshold})"
        )
        self.logger.debug(f"   Typed Clean: '{typed_clean[:100]}...'")
        self.logger.debug(f"   Fetched Clean: '{fetched_clean[:100]}...'")
        return ratio >= threshold

    def write_caption(self) -> Optional[str]:
        """
        Orchestrates waiting for the field, generating, typing, and verifying the caption.

        Returns:
            Optional[str]: The generated and verified caption, or None on failure.
        """
        # Step 1: Wait for caption field
        # Removed initial sleep, rely on wait method
        if not self._wait_for_caption_field(timeout=15):  # Increased timeout
            return None

        # Step 1b: Click the caption field to ensure focus
        # Use click_by_xpath, trying primary then fallback XPath
        if not self.insta_actions.click_by_xpath(self.caption_field_xpath, timeout=2):
            if not self.insta_actions.click_by_xpath(
                self.caption_field_xpath_fallback, timeout=2
            ):
                self.logger.error("❌ Failed to click caption input field.")
                return None
        self.logger.debug("✅ Caption input field clicked.")
        # Allow time for keyboard to potentially appear
        time.sleep(random.uniform(0.8, 1.5))

        # Step 2: Generate caption (External call)
        self.logger.debug("🧠 Generating AI caption...")
        try:
            # Assuming generate_caption() is defined in ai_api.py and works
            caption = generate_caption()
            if not caption:
                self.logger.error("❌ AI failed to generate a caption.")
                return None
            self.logger.info(f"💬 AI Caption Generated: '{caption[:70]}...'")
        except Exception as e:
            self.logger.error(
                f"💥 Error during AI caption generation: {e}", exc_info=True
            )
            return None

        # Step 3: Type caption using StealthTyper via helper method
        self._type_caption_stealthily(caption)

        # Step 4: Hide keyboard to reveal UI elements below (like Share button)
        self.logger.debug("Hiding keyboard...")
        # Use press_back method from InstagramInteractions
        self.insta_actions.press_back()  # Ensure this method exists in InstagramInteractions
        # Wait for keyboard to disappear and UI to settle
        # TODO: Replace sleep with wait_for_element_appear for the Share/Next button
        time.sleep(random.uniform(1.5, 2.5))

        # Step 5: Verify caption text in the field
        self.logger.debug("Verifying caption text in field...")
        verified_text = self._get_current_caption_text()
        if not self._captions_are_similar(caption, verified_text):
            self.logger.warning(
                f"⚠️ Caption text mismatch after typing! Expected similar to '{caption[:50]}...', Got: '{verified_text[:50]}...'"
            )
            # Optional: Add retry logic here? Clear and re-type?
            return None  # Fail for now if verification fails
        else:
            self.logger.info("✅ Caption text verified successfully in field.")

        return caption


# --- Main Function (Entry Point) ---


def generate_and_enter_caption(
    # Takes insta_actions object instead of device/app_package directly
    insta_actions: InstagramInteractions,
    post_type: str = "reel",
    # device_id: Optional[str] = None # Not needed if insta_actions is passed
) -> Optional[str]:
    """
    High-level function to generate and input a caption.

    Args:
        insta_actions (InstagramInteractions): Initialized UI interaction driver.
        post_type (str): Type of post ('reel', 'post', etc.).

    Returns:
        Optional[str]: The verified caption string, or None on failure.
    """
    try:
        # Instantiate GenerateCaption helper class, passing insta_actions
        caption_writer = GenerateCaption(
            insta_actions=insta_actions,
            post_type=post_type,
            # logger=logger, # Can use module logger
        )
        # Call the method to perform the workflow
        return caption_writer.write_caption()

    except Exception as e:
        logger.error(
            f"💥 Error during caption generation/entry process: {str(e)}", exc_info=True
        )
        return None


# --- Test Harness (Example Usage) ---


def main():
    """Example of how to use the generate_and_enter_caption function."""
    logger.info("🚀 Testing caption generation + input flow")
    device = None
    insta_actions = None
    try:
        # Connect to device
        device = u2.connect()  # Add device_id if needed: u2.connect("YOUR_DEVICE_ID")
        if not device.info:  # Basic check
            raise ConnectionError("Failed to connect to device")
        logger.info(f"✅ Connected to device: {device.serial}")

        # Define app package (should match the one used for posting)
        app_package = "com.instagram.androie"  # TODO: Get from config or record

        # Instantiate InstagramInteractions
        # Pass None for airtable_manager if not needed by insta_actions itself for this task
        insta_actions = InstagramInteractions(
            device, app_package, airtable_manager=None
        )

        # --- Assume App is already on the Caption Screen ---
        logger.info("🧪 NOTE: This test assumes the Instagram app is already open")
        logger.info(
            "🧪       and displaying the caption input screen for a new post/reel."
        )
        logger.info("🧪       Please navigate manually before running the test.")
        input(
            "Press Enter when ready on the caption screen..."
        )  # Pause for manual setup

        # Call the main function, passing the insta_actions instance
        caption_text = generate_and_enter_caption(insta_actions=insta_actions)

        if caption_text:
            logger.info(f"✅✅✅ SUCCESS: Caption entered and verified.")
            logger.info(f"Final Caption: {caption_text}")
        else:
            logger.error("❌❌❌ FAILURE: Caption entry or verification failed.")

    except ConnectionError as e:
        logger.error(f"💥 Connection Error: {e}")
    except Exception as e:
        logger.error(f"💥 Unhandled exception in main(): {str(e)}", exc_info=True)
    finally:
        logger.info("--- Test finished ---")


if __name__ == "__main__":
    main()
