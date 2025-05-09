# UploadBot/instagram_actions.py

import os  # Added for capture_frames_from_current_reel
import random
import re
import subprocess
import time
from typing import Dict, Optional, Tuple

import uiautomator2 as u2

# Assuming SwipeHelper class is moved to its own file
from Shared.UI.swipe_helper import SwipeHelper
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.xpath_config import InstagramXPaths

# Module-level logger (can be used by helper functions if any)
# logger = setup_logger(__name__) # You can keep this if needed elsewhere


class InstagramInteractions:
    """
    Handles direct UI interactions with the Instagram application using uiautomator2.
    Provides methods for navigation, element interaction, app management, and
    human-like gestures via SwipeHelper.
    """

    def __init__(self, device: u2.Device, app_package: str, airtable_manager=None):
        """
        Initializes the InstagramInteractions class.

        Args:
            device (u2.Device): The uiautomator2 device instance.
            app_package (str): The package name of the Instagram app/clone.
            airtable_manager: An optional Airtable client instance.
        """
        self.device = device
        self.app_package = app_package.strip()  # Ensure it's stripped
        self.xpath_config = InstagramXPaths(self.app_package)
        self.airtable_manager = airtable_manager
        # Use class name for logger for better context in logs
        self.logger = setup_logger(self.__class__.__name__)
        # Instantiate SwipeHelper for human-like gestures
        self.swipe_helper = SwipeHelper(self.device)

    # --- App Management ---

    def _launch_app_via_adb_monkey(self) -> bool:
        """
        Internal helper to launch the app using ADB monkey command.
        This is a more forceful way to ensure the app's main activity is started.
        """
        self.logger.info(
            f"🔧 Attempting to launch {self.app_package} via ADB (monkey shell)"
        )
        try:
            # Construct the command. Using self.device.serial if available,
            # otherwise assumes only one device or ADB configured for a specific one.
            cmd = ["adb"]
            if hasattr(self.device, "serial") and self.device.serial:
                cmd.extend(["-s", self.device.serial])
            cmd.extend(
                [
                    "shell",
                    "monkey",
                    "-p",
                    self.app_package,
                    "-c",
                    "android.intent.category.LAUNCHER",
                    "1",
                ]
            )
            subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=15
            )  # Added timeout
            self.logger.info(
                f"✅ ADB monkey launch command executed for {self.app_package}"
            )
            return True
        except subprocess.TimeoutExpired:
            self.logger.error(
                f"❌ ADB monkey launch command timed out for {self.app_package}."
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"❌ ADB monkey launch failed for {self.app_package}: {e.stderr}"
            )
        except FileNotFoundError:
            self.logger.error(
                "❌ ADB command not found. Ensure ADB is installed and in your PATH."
            )
        except Exception as e:
            self.logger.error(f"❌ Unexpected error during ADB monkey launch: {e}")
        return False

    def open_app(
        self,
        readiness_xpath: Optional[str] = None,
        readiness_timeout: int = 20,
        max_retries: int = 3,
    ) -> bool:
        """
        Ensures the app is open, in the foreground, and optionally waits for a readiness element.

        Tries to bring the app to the foreground first. If that fails or the app isn't running,
        it attempts a full launch. Includes ADB monkey launch as a robust fallback.

        Args:
            readiness_xpath (Optional[str]): An XPath to an element that indicates the app is ready.
                                            If None, only checks if the app is in the foreground.
            readiness_timeout (int): Timeout in seconds for the readiness_xpath to appear.
            max_retries (int): Number of times to retry the launch/foregrounding process.

        Returns:
            bool: True if the app is successfully opened and ready, False otherwise.
        """
        self.logger.info(f"🚀 Ensuring app '{self.app_package}' is open and ready...")

        for attempt in range(1, max_retries + 1):
            self.logger.info(
                f"Attempt {attempt}/{max_retries} to open/foreground '{self.app_package}'"
            )
            app_is_foreground = False
            app_launched_this_attempt = False

            try:
                # 1. Check current app and try to bring to foreground if already running
                current_app_info = self.device.app_current()
                if current_app_info.get("package") == self.app_package:
                    self.logger.info(
                        f"✅ App '{self.app_package}' is already in foreground."
                    )
                    app_is_foreground = True
                else:
                    self.logger.info(
                        f"App '{self.app_package}' not in foreground. Current: {current_app_info.get('package')}. Attempting to start/focus..."
                    )
                    self.device.app_start(
                        self.app_package, stop=False
                    )  # stop=False tries to bring to front without full restart
                    time.sleep(2)  # Give time for app to switch

                    # Verify it's in foreground
                    current_app_info = self.device.app_current()
                    if current_app_info.get("package") == self.app_package:
                        self.logger.info(
                            f"✅ App '{self.app_package}' brought to foreground."
                        )
                        app_is_foreground = True
                        app_launched_this_attempt = True  # Or focused
                    else:
                        self.logger.warning(
                            f"⚠️ Failed to bring '{self.app_package}' to foreground. Will try full launch."
                        )

                # 2. If not in foreground, try more robust launch methods
                if not app_is_foreground:
                    self.logger.info(
                        f"Attempting uiautomator2 app_start for '{self.app_package}'"
                    )
                    try:
                        # Try u2's app_start with a clean start
                        self.device.app_start(self.app_package, stop=True)
                        time.sleep(3)  # Wait for app to initialize
                        app_launched_this_attempt = True
                    except Exception as e_u2_start:
                        self.logger.warning(
                            f"uiautomator2 app_start failed: {e_u2_start}. Trying ADB AM start."
                        )
                        # Using a common main activity name, adjust if your app uses a different one
                        # Or rely on package launch which is usually enough
                        component = f"{self.app_package}/.activity.MainTabActivity"  # Example, might need adjustment
                        try:
                            subprocess.run(
                                ["adb", "shell", "am", "start", "-n", component],
                                check=True,
                                timeout=10,
                            )
                            time.sleep(3)  # Wait for app to initialize
                            app_launched_this_attempt = True
                        except Exception as e_am_start:
                            self.logger.warning(
                                f"ADB AM start failed: {e_am_start}. Trying ADB monkey."
                            )
                            # Fallback to ADB monkey launch if others fail
                            if self._launch_app_via_adb_monkey():
                                time.sleep(
                                    5
                                )  # Monkey launch might need more time to settle
                                app_launched_this_attempt = True
                            else:
                                self.logger.error(
                                    f"❌ All launch methods failed for '{self.app_package}' on attempt {attempt}."
                                )
                                continue  # To next retry

                    # Verify foreground status again after launch attempt
                    current_app_info = self.device.app_current()
                    if current_app_info.get("package") == self.app_package:
                        self.logger.info(
                            f"✅ App '{self.app_package}' launched and in foreground."
                        )
                        app_is_foreground = True
                    else:
                        self.logger.error(
                            f"❌ App still not in foreground after launch attempts on attempt {attempt}."
                        )
                        continue  # To next retry

                # 3. If app is in foreground, check for readiness_xpath
                if app_is_foreground:
                    if readiness_xpath:
                        self.logger.info(
                            f"🔍 App in foreground. Waiting for readiness element: {readiness_xpath} (timeout: {readiness_timeout}s)"
                        )
                        if self.wait_for_element_appear(
                            readiness_xpath, timeout=readiness_timeout
                        ):
                            self.logger.info(
                                f"✅ App '{self.app_package}' is open and ready (readiness XPath matched)."
                            )
                            return True
                        else:
                            self.logger.warning(
                                f"⚠️ App is in foreground, but readiness XPath '{readiness_xpath}' not found on attempt {attempt}."
                            )
                            # If launch happened this attempt but readiness failed, it's a clearer failure for this attempt
                            if app_launched_this_attempt:
                                continue
                    else:
                        self.logger.info(
                            f"✅ App '{self.app_package}' is open and in foreground (no readiness XPath specified)."
                        )
                        return True

            except subprocess.TimeoutExpired:
                self.logger.error(
                    f"❌ ADB command timed out during app launch on attempt {attempt}."
                )
            except subprocess.CalledProcessError as e:
                self.logger.error(
                    f"❌ ADB command failed during app launch on attempt {attempt}: {e.stderr}"
                )
            except Exception as e:
                self.logger.error(
                    f"❌ Unexpected error during app open/foreground attempt {attempt}: {e}",
                    exc_info=True,
                )

            if attempt < max_retries:
                wait_time = 2 * attempt
                self.logger.info(f"Waiting {wait_time}s before next retry...")
                time.sleep(wait_time)

        self.logger.error(
            f"❌ Failed to open and ready app '{self.app_package}' after {max_retries} attempts."
        )
        return False

    def press_back(self):
        self.xpath_config.back_button

    def close_app(self) -> bool:
        """
        Attempts to stop the Instagram app cleanly using u2 and falls back to ADB if needed.
        """
        pkg = self.app_package  # Already stripped in __init__
        self.logger.debug(f"🛑 Attempting to stop app: {pkg}")

        try:
            self.device.app_stop(pkg)
            time.sleep(1)  # Allow time for process to terminate

            # Verify if stopped
            current_pkg = self.device.app_current().get("package")
            if current_pkg == pkg:
                self.logger.warning(
                    f"⚠️ uiautomator2 app_stop failed for {pkg}, falling back to ADB force-stop"
                )
                try:
                    cmd = ["adb"]
                    if hasattr(self.device, "serial") and self.device.serial:
                        cmd.extend(["-s", self.device.serial])
                    cmd.extend(["shell", "am", "force-stop", pkg])
                    subprocess.run(
                        cmd, check=True, capture_output=True, text=True, timeout=10
                    )
                    self.logger.debug(
                        f"✅ App {pkg} stopped via ADB force-stop fallback"
                    )
                    # Double-check after force-stop
                    time.sleep(1)
                    current_pkg_after_adb = self.device.app_current().get("package")
                    if current_pkg_after_adb == pkg:
                        self.logger.error(
                            f"❌ ADB force-stop also failed to stop {pkg}"
                        )
                        return False
                except subprocess.TimeoutExpired:
                    self.logger.error(f"❌ ADB force-stop command timed out for {pkg}.")
                    return False
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"❌ ADB force-stop command failed for {pkg}: {e.stderr}"
                    )
                    return False
                except FileNotFoundError:
                    self.logger.error(
                        "❌ ADB command not found for force-stop fallback."
                    )
                    return False
            else:
                self.logger.debug(f"✅ App {pkg} stopped successfully via uiautomator2")

            return True  # Return True if app is confirmed not running or successfully stopped
        except Exception as e:
            self.logger.error(f"❌ Failed to stop app {pkg}: {e}", exc_info=True)
            return False

    # --- Element Interaction Primitives ---

    def wait_for_element_appear(
        self, xpath: str, timeout: int = 10, poll_interval: float = 0.5
    ) -> bool:
        """
        Waits for a UI element specified by XPath to appear on the screen.

        Args:
            xpath (str): The XPath of the element to wait for.
            timeout (int): Maximum time in seconds to wait for the element.
            poll_interval (float): Time in seconds between checks.

        Returns:
            bool: True if the element appears within the timeout, False otherwise.
        """
        self.logger.debug(f"Waiting up to {timeout}s for element to appear: {xpath}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.device.xpath(xpath).exists:
                self.logger.debug(f"Element found: {xpath}")
                return True
            time.sleep(poll_interval)
        self.logger.debug(f"Timeout waiting for element: {xpath}")
        return False

    def wait_for_element_vanish(
        self, xpath: str, timeout: int = 10, poll_interval: float = 0.5
    ) -> bool:
        """
        Waits for a UI element specified by XPath to disappear from the screen.

        Args:
            xpath (str): The XPath of the element to wait for its disappearance.
            timeout (int): Maximum time in seconds to wait.
            poll_interval (float): Time in seconds between checks.

        Returns:
            bool: True if the element disappears within the timeout, False otherwise.
        """
        self.logger.debug(f"Waiting up to {timeout}s for element to vanish: {xpath}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.device.xpath(xpath).exists:
                self.logger.debug(f"Element vanished: {xpath}")
                return True
            time.sleep(poll_interval)
        self.logger.debug(f"Timeout waiting for element to vanish: {xpath}")
        return False

    def element_exists(self, xpath: str) -> bool:
        """Checks if an element exists without waiting."""
        exists = self.device.xpath(xpath).exists
        self.logger.debug(f"Checking existence of '{xpath}': {exists}")
        return exists

    def click_by_xpath(self, xpath: str, timeout: int = 10) -> bool:
        """
        Waits for an element by XPath and clicks its center if found.

        Args:
            xpath (str): The XPath of the element to click.
            timeout (int): Maximum time to wait for the element.

        Returns:
            bool: True if the element was found and clicked, False otherwise.
        """
        self.logger.debug(f"Attempting to click element: {xpath}")
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                # Using uiautomator2's built-in click which handles more cases
                element.click()
                # Optional: ADB click as fallback or if u2 click fails for specific elements
                # center = element.center()
                # self.device.click(*center)
                self.logger.debug(f"Clicked element via XPath: {xpath}")
                return True
            else:
                self.logger.info(
                    f"Element not found for clicking after {timeout}s: {xpath}"
                )
                return False
        except Exception as e:
            # Catching potential u2 specific errors if needed, e.g., UiObjectNotFoundError
            self.logger.error(
                f"Error while waiting for or clicking element with XPath '{xpath}': {e}",
                exc_info=True,  # Include traceback for debugging
            )
            return False

    def click_if_exists(self, xpath: str, timeout: int = 1) -> bool:
        """
        Clicks an element only if it exists within a short timeout. Useful for optional elements/popups.

        Args:
            xpath (str): The XPath of the element to potentially click.
            timeout (int): Short timeout to check for existence.

        Returns:
            bool: True if the element was found and clicked, False otherwise.
        """
        self.logger.debug(f"Checking and clicking if exists: {xpath}")
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                element.click()
                self.logger.debug(f"Clicked optional element: {xpath}")
                return True
            else:
                self.logger.debug(f"Optional element not found: {xpath}")
                return False
        except Exception as e:
            self.logger.error(
                f"Error during click_if_exists for '{xpath}': {e}", exc_info=True
            )
            return False

    def input_text(
        self, xpath: str, text: str, clear_first: bool = True, timeout: int = 10
    ) -> bool:
        """
        Waits for an input field, clears it (optional), and types text into it.

        Args:
            xpath (str): XPath of the input field.
            text (str): Text to input.
            clear_first (bool): Whether to clear the field before typing.
            timeout (int): Timeout to wait for the input field.

        Returns:
            bool: True if successful, False otherwise.
        """
        self.logger.debug(f"Attempting to input text into: {xpath}")
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                if clear_first:
                    element.clear_text()
                    time.sleep(0.2)  # Short pause after clearing
                element.set_text(text)
                # Verification (optional but recommended)
                # entered_text = element.get_text()
                # if entered_text == text:
                #    self.logger.debug(f"Successfully input text into: {xpath}")
                #    return True
                # else:
                #    self.logger.warning(f"Verification failed. Expected '{text}', got '{entered_text}' in {xpath}")
                #    return False
                self.logger.debug(
                    f"Input text into: {xpath}"
                )  # Assuming success if no error
                return True
            else:
                self.logger.error(f"Input field not found: {xpath}")
                return False
        except Exception as e:
            self.logger.error(
                f"Error inputting text into '{xpath}': {e}", exc_info=True
            )
            return False

    # TODO: Add input_text_stealthily method using StealthTyper if needed

    def get_element_text(self, xpath: str, timeout: int = 5) -> Optional[str]:
        """Gets the text content of an element."""
        self.logger.debug(f"Getting text from: {xpath}")
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                return element.get_text()
            else:
                self.logger.debug(f"Element not found for get_text: {xpath}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting text from '{xpath}': {e}", exc_info=True)
            return None

    def get_element_attribute(
        self, xpath: str, attribute: str, timeout: int = 5
    ) -> Optional[str]:
        """Gets a specific attribute value of an element."""
        self.logger.debug(f"Getting attribute '{attribute}' from: {xpath}")
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                # uiautomator2 uses .info dictionary for attributes
                return element.info.get(attribute)
            else:
                self.logger.debug(f"Element not found for get_attribute: {xpath}")
                return None
        except Exception as e:
            self.logger.error(
                f"Error getting attribute '{attribute}' from '{xpath}': {e}",
                exc_info=True,
            )
            return None

    # --- Human-like Gestures (using SwipeHelper) ---

    def scroll_up_humanlike(self, intensity="medium"):
        """Performs a human-like upward scroll (downward swipe on screen)."""
        self.logger.debug("Performing human-like scroll up...")
        self.swipe_helper.human_scroll_up()  # Assuming method exists in SwipeHelper

    def scroll_down_humanlike(self, intensity="medium"):
        """Performs a human-like downward scroll (upward swipe on screen)."""
        self.logger.debug("Performing human-like scroll down...")
        self.swipe_helper.human_scroll_down()  # Assuming method exists in SwipeHelper

    def tap_coords_humanlike(self, x: int, y: int, arc_radius: int = 80):
        """Performs a human-like curved tap near coordinates."""
        self.logger.debug(f"Performing human-like tap near ({x}, {y})")
        self.swipe_helper.curved_tap(x, y, arc_radius=arc_radius)

    def swipe_humanlike(
        self,
        start_coords: tuple,
        end_coords: tuple,
        duration: int = 400,
        intensity: str = "medium",
    ):
        """Performs a human-like swipe between coordinates."""
        self.logger.debug(
            f"Performing human-like swipe from {start_coords} to {end_coords}"
        )
        self.swipe_helper.curved_swipe(
            start_coords, end_coords, duration=duration, intensity=intensity
        )

    def peek_element(
        self,
        element_xpath: str,
        min_view_duration: float = 1.0,
        max_view_duration: float = 2.0,
        tap_timeout: int = 5,
    ) -> bool:
        """
        Taps an element (e.g., a Reel), waits for a short random duration,
        then presses the back button to simulate a user "peeking".

        Args:
            element_xpath (str): The XPath of the element to tap.
            min_view_duration (float): Minimum seconds to "view" the content after tapping.
            max_view_duration (float): Maximum seconds to "view" the content after tapping.
            tap_timeout (int): Timeout in seconds to wait for the element to be clickable.

        Returns:
            bool: True if the peek action was successfully performed, False otherwise.
        """
        self.logger.info(f"👀 Simulating peek on element: {element_xpath}")
        try:
            element_to_peek = self.device.xpath(element_xpath)
            if not element_to_peek.wait(timeout=tap_timeout):
                self.logger.warning(
                    f"⚠️ Element not found for peeking within {tap_timeout}s: {element_xpath}"
                )
                return False

            # Use direct click after wait confirms presence
            element_to_peek.click()
            self.logger.debug(f"Element clicked: {element_xpath}")

            view_duration = random.uniform(min_view_duration, max_view_duration)
            self.logger.debug(f"Peeking for {view_duration:.2f} seconds...")
            time.sleep(view_duration)

            self.logger.debug("Pressing back button...")
            self.device.press("back")
            time.sleep(0.5)  # Short delay for UI to settle after back press
            self.logger.info(f"✅ Peek successful for: {element_xpath}")
            return True

        except Exception as e:
            self.logger.error(
                f"❌ Exception during peek_element for '{element_xpath}': {e}",
                exc_info=True,
            )
            # Attempt to press back anyway if the error occurred after clicking, to try and recover state
            try:
                self.logger.info("Attempting to press back after peek exception...")
                self.device.press("back")
                time.sleep(0.5)
            except Exception as back_e:
                self.logger.error(
                    f"❌ Failed to press back after peek exception: {back_e}"
                )
            return False

    # --- Content Creation Specific Methods ---

    def new_post(self):
        """Navigates to the new post creation flow."""
        # Ensure create_post_general_button is defined in xpath_config
        if self.click_by_xpath(self.xpath_config.create_post_general_button):
            self.logger.debug("Navigated to the new post creation tab.")
            # Add a wait here for the next expected screen element (e.g., gallery or camera)
            # self.wait_for_element_appear(self.xpath_config.gallery_grid_container, timeout=10)
            return True
        else:
            self.logger.error("Failed to navigate to the new post creation tab.")
            return False

    def find_and_click_album(self, album_name):
        """Finds and clicks a specific album in the gallery view."""
        self.logger.debug(f"Attempting to click album: {album_name}")
        # Ensure album_selector method exists and works in xpath_config
        xpath = self.xpath_config.album_selector(album_name)
        success = self.click_by_xpath(xpath)
        if success:
            self.logger.debug(f"Successfully clicked on album: {album_name}")
            return True
        else:
            self.logger.error(f"Failed to click album: {album_name}")
            return False

    def select_first_video(self, timeout=10):
        """
        Waits for and clicks the first fully loaded video thumbnail in the gallery.
        A thumbnail is considered 'loaded' if its child View has a content-desc
        starting with 'Video thumbnail'.
        """
        # Ensure gallery_grid_container and gallery_loaded_video_thumbnail_sub_xpath
        # are defined in xpath_config
        grid_xpath = self.xpath_config.gallery_grid_container
        loaded_thumb_sub_xpath = (
            self.xpath_config.gallery_loaded_video_thumbnail_sub_xpath
        )

        self.logger.debug("Attempting to select the first loaded video thumbnail...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Get all potential containers in the grid
                elements = self.device.xpath(grid_xpath).all()

                if not elements:
                    self.logger.debug(f"Gallery grid appears empty, waiting...")
                    time.sleep(1)
                    continue  # Retry finding elements

                for idx, container in enumerate(elements):
                    try:
                        # Check within this container for the loaded thumbnail indicator
                        # Using .xpath() on the element object searches within its subtree
                        thumbnail_indicator = container.xpath(loaded_thumb_sub_xpath)
                        if (
                            thumbnail_indicator.exists
                        ):  # Check existence within the container
                            self.logger.info(
                                f"🎯 Found loaded video thumbnail at index {idx}. Clicking container."
                            )
                            container.click()  # Click the parent container
                            # Add a wait here for the *next* screen (e.g., editor screen 'Add audio' button)
                            # if self.wait_for_element_appear(self.xpath_config.add_audio_text_or_desc_general, timeout=15):
                            #     return True
                            # else:
                            #     self.logger.warning("Clicked video, but editor screen did not appear.")
                            #     return False # Or raise an error
                            return True  # Return immediately after successful click
                    except Exception as e_inner:
                        # Handle stale element reference or other issues with a specific container
                        self.logger.debug(
                            f"⚠️ Error checking container index {idx}: {e_inner}"
                        )
                        continue  # Try next container

                self.logger.debug(
                    f"No loaded video thumbnails found in visible grid, polling again..."
                )
                time.sleep(1)  # Wait before rescanning the grid

            except Exception as e_outer:
                # Handle errors finding the grid itself
                self.logger.error(
                    f"💥 Exception during thumbnail check loop: {e_outer}",
                    exc_info=True,
                )
                time.sleep(1)  # Wait before retrying the outer loop

        self.logger.error(
            f"❌ No fully loaded video thumbnails found after {timeout} seconds."
        )
        return False

    def wait_for_posted_caption(
        self, caption: str, username: str, timeout: int = 120, poll_interval: float = 2
    ) -> bool:
        """
        Waits for confirmation that the reel was posted by checking for caption, insights pill, or profile pic.
        """
        if not caption:
            self.logger.error("❌ No caption provided for reel post verification")
            return False
        if not username:
            self.logger.error("❌ No username provided for fallback reel detection")
            return False

        # Prepare XPaths (ensure reel_viewer_insights_pill is in config)
        trimmed_caption = caption.strip()[:40].replace('"', "").replace("'", "")
        # Dynamic XPaths are okay here as they depend on runtime data
        caption_xpath = f"//android.view.ViewGroup[starts-with(@content-desc, '{trimmed_caption}') or contains(@text, '{trimmed_caption}')]"  # Added text check
        profile_xpath = f"//android.widget.ImageView[contains(@content-desc, 'Profile picture of {username}') or contains(@content-desc, '{username}')]"
        insights_xpath = self.xpath_config.reel_viewer_insights_pill

        self.logger.info(f"🔍 Waiting up to {timeout}s to verify Reel post appears...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check conditions in order of likelihood or preference
            if self.element_exists(caption_xpath):
                self.logger.info("✅ Caption detected in reel view.")
                return True
            if self.element_exists(insights_xpath):
                self.logger.info("✅ Reel insights pill detected.")
                return True
            if self.element_exists(profile_xpath):
                self.logger.info(
                    "✅ Username profile picture detected in posted reel view."
                )
                return True

            self.logger.debug(
                "⏳ Post confirmation elements not found yet, polling again..."
            )
            time.sleep(poll_interval)

        self.logger.error(
            f"❌ Reel post verification failed: Confirmation elements not found after {timeout} seconds."
        )
        return False

    # --- Data Extraction ---

    def get_account_name(self) -> Optional[str]:
        """
        Attempts to extract the logged-in account's username.
        Tries the story avatar first, then falls back to the profile page title.
        """
        self.logger.debug("Attempting to get account name...")
        try:
            # Method 1: Story Avatar (usually reliable on home screen)
            story_avatar_xpath = self.xpath_config.story_avatar
            elements = self.device.xpath(story_avatar_xpath).all()
            self.logger.debug(
                f"Found {len(elements)} elements matching story avatar XPath."
            )

            for element in elements:
                content_desc = element.info.get(
                    "contentDescription", ""
                )  # Use .info dict
                self.logger.debug(f"Element content description: {content_desc}")
                if content_desc:
                    # Regex to find "USERNAME's story at column"
                    username_match = re.search(
                        r"([^']+)'s story at column", content_desc
                    )
                    if username_match:
                        username = username_match.group(1)
                        self.logger.info(
                            f"✅ Account name extracted from story avatar: {username}"
                        )
                        return username

            self.logger.warning(
                "No valid username found in story avatar content descriptions."
            )

            # Method 2: Profile Page Title (fallback)
            profile_title_xpath = self.xpath_config.action_bar_large_title_auto_size
            # We might need to navigate to the profile tab first if not already there
            # self.navigate_to_profile_tab() # Assuming such a method exists
            profile_element = self.device.xpath(profile_title_xpath)
            if profile_element.wait(timeout=5):  # Wait briefly for profile title
                profile_username = profile_element.get_text()
                if profile_username:
                    self.logger.info(
                        f"✅ Fallback: Found username from profile page title: {profile_username}"
                    )
                    return profile_username
                else:
                    self.logger.warning("Profile title element found but has no text.")
            else:
                self.logger.warning("Profile title element not found.")

            self.logger.error("❌ Failed to extract account name using known methods.")
            return None  # Return None instead of raising ValueError immediately

        except Exception as e:
            self.logger.error(f"💥 Error during get_account_name: {e}", exc_info=True)
            return None  # Return None on error

    # --- Frame Capture for VLM ---

    def capture_frames_from_current_reel(
        self,
        num_frames: int = 3,
        interval_sec: float = 1.5,
        local_temp_dir: str = "temp_frames",
    ) -> list[str]:
        """
        Captures a sequence of frames from the currently visible and playing Reel.
        Assumes the Reel is already on screen and likely auto-playing.
        Saves frames locally to local_temp_dir and returns the list of paths.

        Args:
            num_frames (int): Number of frames to capture.
            interval_sec (float): Time interval in seconds between frame captures.
            local_temp_dir (str): Directory on the client machine to save frames.

        Returns:
            list[str]: A list of local file paths to the captured frames.
        """
        frame_paths = []
        if not os.path.exists(local_temp_dir):
            try:
                os.makedirs(local_temp_dir)
                self.logger.info(f"Created temporary frame directory: {local_temp_dir}")
            except OSError as e:
                self.logger.error(f"Failed to create directory {local_temp_dir}: {e}")
                return []  # Cannot proceed without directory

        self.logger.info(
            f"Attempting to capture {num_frames} frames at {interval_sec}s intervals."
        )

        # Allow initial UI elements to settle or video to start
        time.sleep(0.75)  # Small initial delay

        for i in range(num_frames):
            timestamp = int(time.time() * 1000)  # Milliseconds for unique filenames
            filename = f"frame_{i+1}_{timestamp}.png"
            local_frame_path = os.path.join(local_temp_dir, filename)

            try:
                # Optional: Tap center of screen to hide some UI overlays
                # display_info = self.device.info
                # center_x, center_y = display_info['displayWidth'] // 2, display_info['displayHeight'] // 2
                # self.device.click(center_x, center_y)
                # time.sleep(0.2) # Wait for UI to react

                self.device.screenshot(local_frame_path)
                # Verify screenshot was actually created on the client side
                if (
                    os.path.exists(local_frame_path)
                    and os.path.getsize(local_frame_path) > 0
                ):
                    frame_paths.append(local_frame_path)
                    self.logger.debug(f"Captured frame {i+1} to {local_frame_path}")
                else:
                    self.logger.warning(
                        f"Failed to capture or find valid frame {i+1} at {local_frame_path}"
                    )
                    # Optionally try again once?
                    # if attempt_retry: ...

                if i < num_frames - 1:  # Don't wait after the last frame
                    time.sleep(interval_sec)

            except Exception as e:
                self.logger.error(f"Error capturing frame {i+1}: {e}", exc_info=True)
                # Decide if you want to continue or break if one frame fails
                # break # Or continue to try getting subsequent frames

        self.logger.info(f"Finished capture attempt, got {len(frame_paths)} frames.")
        return frame_paths

    # --- Legacy Methods (Marked for review/deprecation) ---

    def wait_for_app_ready_legacy(
        self,
        # device, # Should use self.device
        expected_xpath: str,
        retries: int = 3,
        delay: float = 2.0,
        timeout: int = 10,
    ):
        """
        [Legacy - Review/Deprecated] Waits for the app UI to become inspectable.
        Prefer using open_app with readiness_xpath or wait_for_element_appear.
        """
        self.logger.debug(
            f"🕵️ [Legacy] Waiting for UI to become inspectable via: {expected_xpath}"
        )
        for attempt in range(1, retries + 1):
            try:
                el = self.device.xpath(expected_xpath)  # Use self.device
                if el.wait(timeout=timeout):
                    self.logger.debug(
                        "✅ [Legacy] UI element detected: app appears ready"
                    )
                    return True
            except Exception as e:
                self.logger.warning(
                    f"⚠️ [Legacy] UI not ready yet (attempt {attempt}/{retries}): {e}"
                )
            wait_time = delay * attempt
            self.logger.info(f"⏳ [Legacy] Waiting {wait_time}s before retrying...")
            time.sleep(wait_time)
        self.logger.error("❌ [Legacy] App UI did not become inspectable in time.")
        return False

    # --- Enhanced Element Interaction Methods (from UIHelper logic) ---

    def smart_button_clicker(
        self,
        text_patterns: list[str],
        fallback_xpath: Optional[str] = None,
        timeout: int = 10,
    ) -> bool:
        """
        Clicks a button based on text content, with optional fallback XPath.
        Searches for buttons containing any of the text patterns.

        Args:
            text_patterns (list[str]): A list of text strings to look for (case-insensitive contains).
            fallback_xpath (Optional[str]): An XPath to try if text matching fails.
            timeout (int): Total time to wait for the button (text or fallback).

        Returns:
            bool: True if a button was clicked, False otherwise.
        """
        self.logger.info(
            f"Attempting smart click on button matching text: {text_patterns}"
        )
        start_time = time.time()

        # Construct a combined XPath for text matching (more efficient)
        text_conditions = " or ".join(
            [
                f"contains(translate(@text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{p.lower()}')"
                for p in text_patterns
            ]
        )
        text_xpath = f"//android.widget.Button[{text_conditions}]"
        self.logger.debug(f"Constructed text XPath: {text_xpath}")

        while time.time() - start_time < timeout:
            # Try text match first
            try:
                button = self.device.xpath(text_xpath)
                if button.exists:
                    self.logger.info(f"Found button via text match: {text_patterns}")
                    # Use click_exists for safety after finding
                    if button.click_exists(timeout=1):
                        self.logger.info(
                            f"✅ Successfully clicked button using text: {text_patterns}"
                        )
                        return True
                    else:
                        self.logger.warning(f"Found button via text, but click failed.")
                        # Continue loop in case it becomes clickable later or fallback works

            except Exception as e_text:
                self.logger.warning(
                    f"Error checking text XPath '{text_xpath}': {e_text}"
                )  # Log error but continue

            # Try fallback if specified and text hasn't worked yet
            if fallback_xpath:
                try:
                    fb_button = self.device.xpath(fallback_xpath)
                    if fb_button.exists:
                        self.logger.info(f"Trying fallback XPath: {fallback_xpath}")
                        if fb_button.click_exists(timeout=1):
                            self.logger.info(
                                f"✅ Successfully clicked button using fallback XPath"
                            )
                            return True
                        else:
                            self.logger.warning(
                                f"Found button via fallback, but click failed."
                            )
                except Exception as e_fallback:
                    self.logger.warning(
                        f"Error checking fallback XPath '{fallback_xpath}': {e_fallback}"
                    )

            # Wait before next iteration
            if (
                time.time() - start_time < timeout - 0.5
            ):  # Avoid sleep if timeout is very close
                time.sleep(0.5)

        self.logger.error(
            f"❌ Failed to click button matching '{text_patterns}' or fallback '{fallback_xpath}' within {timeout}s."
        )
        return False

    def click_with_fallback(
        self,
        primary_xpath: str,
        fallback_coords: Optional[Tuple[int, int]] = None,
        timeout: int = 5,
    ) -> bool:
        """
        Attempts to click an element by XPath, falling back to coordinates if the element is not found/clicked.

        Args:
            primary_xpath (str): The preferred XPath to click.
            fallback_coords (Optional[Tuple[int, int]]): (x, y) coordinates to click if XPath fails.
            timeout (int): Timeout for waiting and clicking the XPath element.

        Returns:
            bool: True if either the element or coordinates were clicked, False otherwise.
        """
        self.logger.debug(
            f"Attempting click with fallback. Primary XPath: {primary_xpath}, Fallback Coords: {fallback_coords}"
        )
        try:
            # Try clicking the primary XPath
            if self.click_by_xpath(primary_xpath, timeout=timeout):
                self.logger.info(f"Clicked element via primary XPath: {primary_xpath}")
                return True
            else:
                self.logger.warning(
                    f"Primary XPath click failed or element not found: {primary_xpath}"
                )

            # If primary failed and fallback exists, try coordinates
            if fallback_coords:
                self.logger.info(f"Falling back to coordinates: {fallback_coords}")
                try:
                    x, y = fallback_coords
                    self.device.click(x, y)
                    self.logger.info(f"Clicked fallback coordinates: ({x}, {y})")
                    return True
                except Exception as coord_e:
                    self.logger.error(
                        f"Failed to click fallback coordinates {fallback_coords}: {coord_e}"
                    )
                    return False  # Coordinate click failed
            else:
                self.logger.error(
                    "Click failed: primary XPath failed and no fallback coordinates provided."
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Unexpected error during click_with_fallback: {e}", exc_info=True
            )
            return False

    def click_show_password_icon(self, password_field_xpath: str) -> bool:
        """
        Attempts to find and click a 'show password' button located near a password field.
        Assumes the button is a sibling or near sibling in the layout hierarchy.

        Args:
            password_field_xpath (str): The XPath of the password input field.

        Returns:
            bool: True if a likely show password button was found and clicked, False otherwise.
        """
        self.logger.info(
            f"🔍 Trying to find and click show-password button near: {password_field_xpath}"
        )
        try:
            # Strategy 1: Look for a Button sibling
            icon_xpath_sibling = f"{password_field_xpath}/../android.widget.Button"
            # Strategy 2: Look for an ImageView sibling (sometimes used)
            icon_xpath_sibling_img = (
                f"{password_field_xpath}/../android.widget.ImageView"
            )
            # Strategy 3: Look for specific content descriptions (add to xpath_config if stable)
            # show_pwd_desc_xpath = self.xpath_config.login_show_password_button_desc # Example

            possible_xpaths = [icon_xpath_sibling, icon_xpath_sibling_img]
            # if hasattr(self.xpath_config, 'login_show_password_button_desc'):
            #    possible_xpaths.append(self.xpath_config.login_show_password_button_desc)

            for i, icon_xpath in enumerate(possible_xpaths):
                self.logger.debug(f"Trying strategy {i+1}: {icon_xpath}")
                selector = self.device.xpath(icon_xpath)
                if selector.exists:
                    # Prioritize elements with relevant content descriptions if possible
                    info = selector.info
                    desc = info.get("contentDescription", "").lower()
                    text = info.get("text", "").lower()
                    if "show" in desc or "show" in text or "password" in desc:
                        self.logger.info(
                            f"Found likely show password button via strategy {i+1} (desc='{desc}', text='{text}')"
                        )
                        if selector.click_exists(timeout=1):
                            self.logger.info("✅ Clicked show password button.")
                            time.sleep(0.5)  # Allow UI to update
                            return True
                        else:
                            self.logger.warning("Found button but click failed.")
                            return False  # Don't try other strategies if found but failed click

                    # If no description match, but it's the only sibling button/image, click it
                    elif (
                        len(possible_xpaths) == i + 1
                        or not self.device.xpath(possible_xpaths[i + 1]).exists
                    ):
                        self.logger.info(
                            f"Found button/image via strategy {i+1}, clicking as likely candidate."
                        )
                        if selector.click_exists(timeout=1):
                            self.logger.info("✅ Clicked likely show password button.")
                            time.sleep(0.5)
                            return True
                        else:
                            self.logger.warning("Found likely button but click failed.")
                            return False

            self.logger.warning(
                "❌ No likely show password button found near password field."
            )
            return False

        except Exception as e:
            self.logger.error(
                f"💥 Error clicking show password button near '{password_field_xpath}': {e}",
                exc_info=True,
            )
            return False

    def _tap_random_in_bounds(
        self, bounds: dict, label: str = "element", offset: int = 8
    ) -> bool:
        """Internal helper to tap randomly within given bounds dictionary."""
        try:
            left = bounds["left"]
            top = bounds["top"]
            right = bounds["right"]
            bottom = bounds["bottom"]

            # Ensure bounds are valid and offset doesn't exceed dimensions
            if right <= left + (2 * offset) or bottom <= top + (2 * offset):
                self.logger.warning(
                    f"Bounds too small for offset {offset} on {label}. Clicking center."
                )
                x = (left + right) // 2
                y = (top + bottom) // 2
            else:
                x = random.randint(left + offset, right - offset)
                y = random.randint(top + offset, bottom - offset)

            self.logger.info(
                f"👆 Tapping {label} randomly at ({x}, {y}) within bounds [{left},{top}][{right},{bottom}]"
            )
            self.device.click(x, y)
            return True
        except KeyError:
            self.logger.error(f"Invalid bounds dictionary for {label}: {bounds}")
            return False
        except Exception as e:
            self.logger.error(
                f"Error during random tap calculation/click on {label}: {e}",
                exc_info=True,
            )
            return False

    def tap_random_within_element(
        self, xpath: str, label: str = "element", timeout: int = 5, offset: int = 8
    ) -> bool:
        """
        Finds an element by XPath and taps a random point within its bounds.

        Args:
            xpath (str): XPath of the element.
            label (str): Descriptive label for logging.
            timeout (int): Timeout to wait for the element.
            offset (int): Minimum pixel distance from the element's edges for the tap.

        Returns:
            bool: True if the tap was successful, False otherwise.
        """
        self.logger.debug(f"Attempting random tap within {label}: {xpath}")
        try:
            el = self.device.xpath(xpath)
            if not el.wait(timeout=timeout):
                self.logger.warning(f"{label} not found for random tap: {xpath}")
                return False

            # Retrieve bounds from element info
            bounds = el.info.get("bounds")
            if not bounds:
                self.logger.warning(f"Could not get bounds for {label}: {xpath}")
                # Fallback: click center if bounds are missing
                center = el.center()
                if center:
                    self.logger.info(f"Tapping center of {label} as fallback.")
                    self.device.click(*center)
                    return True
                else:
                    self.logger.error(f"Cannot get bounds or center for {label}")
                    return False

            return self._tap_random_in_bounds(bounds, label, offset)

        except Exception as e:
            self.logger.error(
                f"Error during tap_random_within_element for {label} ('{xpath}'): {e}",
                exc_info=True,
            )
            return False

    def find_element_by_keyword(
        self, keywords: list[str], element_type: str = "*", timeout: int = 5
    ) -> Optional[u2.xpath.XPathSelector]:
        """
        Searches for an element containing any of the keywords in its text or content-desc.
        More efficient than iterating through all elements.

        Args:
            keywords (list[str]): Keywords to search for (case-insensitive).
            element_type (str): The type of element (e.g., 'android.widget.Button', '*' for any).
            timeout (int): Time to wait for a matching element to appear.

        Returns:
            Optional[u2.xpath.XPathSelector]: The selector if found, None otherwise.
        """
        self.logger.info(
            f"Searching for {element_type} containing keywords: {keywords}"
        )
        if not keywords:
            return None

        # Create case-insensitive 'contains' conditions for text and content-desc
        conditions = []
        for kw in keywords:
            kw_lower = kw.lower().replace("'", "\\'")  # Escape single quotes for XPath
            conditions.append(
                f"contains(translate(@text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw_lower}')"
            )
            conditions.append(
                f"contains(translate(@contentDescription, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw_lower}')"
            )

        # Combine conditions with 'or'
        full_condition = " or ".join(conditions)
        xpath = f"//{element_type}[{full_condition}]"
        self.logger.debug(f"Constructed keyword search XPath: {xpath}")

        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                self.logger.info(
                    f"✅ Found element matching keywords via XPath: {xpath}"
                )
                return element
            else:
                self.logger.info(
                    f"No element found matching keywords within {timeout}s."
                )
                return None
        except Exception as e:
            self.logger.error(
                f"Error during find_element_by_keyword: {e}", exc_info=True
            )
            return None

    # --- Page Detection Methods (from PageDetector logic) ---
    # NOTE: Add corresponding XPaths to Shared/xpath_config.py

    def is_on_home_page(self, timeout: int = 1) -> bool:
        """Checks if the current screen looks like the main Home feed."""
        # Example: Check for the Home tab selector or the main feed container
        xpath = self.xpath_config.home_page_indicator  # Define this in xpath_config
        exists = self.device.xpath(xpath).wait(timeout=timeout)
        self.logger.debug(f"Checking for Home Page ({xpath}): {exists}")
        return exists

    def is_on_explore_page(self, timeout: int = 1) -> bool:
        """Checks if the current screen looks like the Explore page."""
        xpath = self.xpath_config.explore_page_indicator  # Define this in xpath_config
        exists = self.device.xpath(xpath).wait(timeout=timeout)
        self.logger.debug(f"Checking for Explore Page ({xpath}): {exists}")
        return exists

    def is_on_reels_page(self, timeout: int = 1) -> bool:
        """Checks if the current screen looks like the Reels feed."""
        xpath = self.xpath_config.reels_page_indicator  # Define this in xpath_config
        exists = self.device.xpath(xpath).wait(timeout=timeout)
        self.logger.debug(f"Checking for Reels Page ({xpath}): {exists}")
        return exists

    def is_on_profile_page(self, timeout: int = 1) -> bool:
        """Checks if the current screen looks like the user's own Profile page."""
        # Could check for "Edit profile" button or specific profile header elements
        xpath = self.xpath_config.profile_page_indicator  # Define this in xpath_config
        exists = self.device.xpath(xpath).wait(timeout=timeout)
        self.logger.debug(f"Checking for Profile Page ({xpath}): {exists}")
        return exists

    def is_on_notifications_page(self, timeout: int = 1) -> bool:
        """Checks if the current screen looks like the Notifications page."""
        xpath = (
            self.xpath_config.notifications_page_indicator
        )  # Define this in xpath_config
        exists = self.device.xpath(xpath).wait(timeout=timeout)
        self.logger.debug(f"Checking for Notifications Page ({xpath}): {exists}")
        return exists

    def detect_current_page(self, timeout_per_check: int = 1) -> str:
        """
        Attempts to detect the current major page/tab the user is on.

        Args:
            timeout_per_check (int): Short timeout for each individual page check.

        Returns:
            str: Name of the detected page ('home', 'explore', 'reels', 'profile', 'notifications', 'unknown').
        """
        self.logger.info("Detecting current page...")
        # Check in a likely order
        if self.is_on_home_page(timeout=timeout_per_check):
            return "home"
        if self.is_on_reels_page(timeout=timeout_per_check):
            return "reels"
        if self.is_on_explore_page(timeout=timeout_per_check):
            return "explore"
        if self.is_on_profile_page(timeout=timeout_per_check):
            return "profile"
        if self.is_on_notifications_page(timeout=timeout_per_check):
            return "notifications"
        # Add checks for other important pages like DMs, New Post screen, etc. if needed

        self.logger.warning(
            "❓ Could not determine current page based on known indicators."
        )
        return "unknown"

    # --- Scrolling Feed Interaction Methods (from scroller.py logic) ---

    def perform_light_interaction(self):
        """Performs a random, minor interaction to simulate user engagement."""
        action = random.choice(
            ["tap_to_pause_resume", "mini_horizontal_scrub", "minor_volume_change"]
        )
        self.logger.info(f"Performing light interaction: {action}")

        try:
            if action == "tap_to_pause_resume":
                # Tap near the center of the screen
                display_info = self.device.info
                width, height = (
                    display_info["displayWidth"],
                    display_info["displayHeight"],
                )
                x = random.randint(int(width * 0.4), int(width * 0.6))
                y = random.randint(int(height * 0.4), int(height * 0.6))
                self.device.click(x, y)
                self.logger.debug(f"Light interaction: Tapped near center ({x},{y})")

            elif action == "mini_horizontal_scrub":
                # Perform a small horizontal swipe using SwipeHelper
                display_info = self.device.info
                width, height = (
                    display_info["displayWidth"],
                    display_info["displayHeight"],
                )
                x_start = random.randint(int(width * 0.3), int(width * 0.5))
                y = random.randint(
                    int(height * 0.6), int(height * 0.8)
                )  # Lower part of screen
                offset = random.randint(30, 80) * random.choice(
                    [-1, 1]
                )  # Small left/right swipe
                x_end = x_start + offset
                # Use swipe_humanlike for consistency if SwipeHelper is integrated
                # self.swipe_humanlike((x_start, y), (x_end, y), duration=random.randint(50, 150), intensity="gentle")
                # Or direct swipe if SwipeHelper isn't used for this:
                self.device.swipe(x_start, y, x_end, y, duration=0.05)  # Short duration
                self.logger.debug(
                    f"Light interaction: Mini horizontal scrub from {x_start} to {x_end} at y={y}"
                )

            elif action == "minor_volume_change":
                # Use ADB shell command to press volume key
                key = random.choice(["KEYCODE_VOLUME_UP", "KEYCODE_VOLUME_DOWN"])
                cmd = ["adb"]
                if hasattr(self.device, "serial") and self.device.serial:
                    cmd.extend(["-s", self.device.serial])
                cmd.extend(["shell", "input", "keyevent", key])
                subprocess.run(
                    cmd, check=True, capture_output=True, text=True, timeout=5
                )
                self.logger.debug(f"Light interaction: Sent {key}")

        except Exception as e:
            self.logger.error(
                f"Error during light interaction '{action}': {e}", exc_info=True
            )

    def like_current_post_or_reel(self, timeout: int = 3) -> bool:
        """
        Attempts to find and tap the 'Like' button, then verifies if it's selected.
        Uses random tap within bounds for humanization.

        Args:
            timeout (int): Timeout to find the like button.

        Returns:
            bool: True if the like was successful and verified, False otherwise.
        """
        self.logger.info("Attempting to like current post/reel...")
        like_xpath = self.xpath_config.like_button_desc  # Define in xpath_config
        try:
            like_button = self.device.xpath(like_xpath)
            if not like_button.wait(timeout=timeout):
                self.logger.warning(
                    f"Like button not found within {timeout}s: {like_xpath}"
                )
                return False

            # Get bounds for random tap
            bounds = like_button.info.get("bounds")
            if not bounds:
                self.logger.warning(
                    "Could not get bounds for like button, attempting center click."
                )
                if not self.click_by_xpath(like_xpath, timeout=1):
                    return False  # Failed even center click
            else:
                # Tap randomly within the button bounds
                if not self._tap_random_in_bounds(bounds, label="Like Button"):
                    self.logger.warning("Random tap within Like button bounds failed.")
                    # Fallback to center click if random tap failed
                    if not self.click_by_xpath(like_xpath, timeout=1):
                        return False

            # Wait briefly for UI to update after like
            time.sleep(random.uniform(0.8, 1.3))

            # Verify if the button state changed to 'selected'
            # Re-find the element to get updated info
            like_button_after = self.device.xpath(like_xpath)
            if like_button_after.exists:
                # Check the 'selected' attribute in the element's info
                is_selected = like_button_after.info.get("selected", False)
                if is_selected:
                    self.logger.info("❤️ Like successful and verified.")
                    return True
                else:
                    # Check if the contentDescription changed to "Unlike"
                    desc = like_button_after.info.get("contentDescription", "")
                    if "unlike" in desc.lower():
                        self.logger.info(
                            "❤️ Like successful (verified by 'Unlike' description)."
                        )
                        return True
                    else:
                        self.logger.warning(
                            "⚠️ Like button clicked, but state did not change to selected/unlike."
                        )
                        return False
            else:
                self.logger.warning(
                    "⚠️ Like button disappeared after clicking, cannot verify."
                )
                return False  # Cannot verify

        except Exception as e:
            self.logger.error(f"❌ Error during like attempt: {e}", exc_info=True)
            return False

    def simulate_open_close_comments(self, timeout: int = 5) -> bool:
        """
        Simulates opening the comment section, scrolling slightly, and closing it.

        Args:
            timeout (int): Timeout to find the comment button.

        Returns:
            bool: True if the interaction sequence completed, False otherwise.
        """
        self.logger.info("💬 Simulating opening/closing comments...")
        comment_xpath = (
            self.xpath_config.comment_button_desc_contains
        )  # Define in xpath_config

        try:
            # Tap randomly within the comment button
            if not self.tap_random_within_element(
                comment_xpath, label="Comment Button", timeout=timeout
            ):
                self.logger.warning("Failed to tap comment button.")
                return False

            # Wait for comment section to potentially load/animate
            time.sleep(random.uniform(1.5, 2.5))

            # Perform a small swipe up (scroll down comments slightly)
            # Using swipe_humanlike if available, otherwise basic swipe
            display_info = self.device.info
            width, height = display_info["displayWidth"], display_info["displayHeight"]
            x = int(width * 0.5) + random.randint(-30, 30)
            y_start = int(height * 0.8) + random.randint(-50, 50)
            y_end = int(height * 0.5) + random.randint(-50, 50)
            self.swipe_humanlike(
                (x, y_start),
                (x, y_end),
                duration=random.randint(200, 400),
                intensity="gentle",
            )
            # Or: self.device.swipe(x, y_start, x, y_end, duration=0.2)
            self.logger.debug("Swiped up slightly within comments.")

            time.sleep(random.uniform(1.0, 2.0))

            # Press back to close comments
            self.logger.debug("Pressing back to close comments.")
            self.device.press("back")
            time.sleep(random.uniform(0.5, 1.0))  # Wait for UI to settle

            # Optional: Verify comments are closed by checking if comment button is visible again
            if self.element_exists(comment_xpath):
                self.logger.info(
                    "✅ Comment simulation complete (comment button reappeared)."
                )
                return True
            else:
                self.logger.warning("⚠️ Comment button not visible after pressing back.")
                # Maybe press back again?
                # self.device.press("back")
                # time.sleep(0.5)
                return False  # Indicate potential issue

        except Exception as e:
            self.logger.error(f"❌ Error during comment simulation: {e}", exc_info=True)
            # Try pressing back to recover state
            try:
                self.logger.info(
                    "Attempting back press after comment simulation exception..."
                )
                self.device.press("back")
            except Exception as back_e:
                self.logger.error(f"Failed to press back after exception: {back_e}")
            return False

    def navigate_back_from_reel(
        self,
        verify_xpath: Optional[str] = None,
        max_attempts: int = 3,
        timeout: int = 5,
    ) -> bool:
        """
        Navigates back from a full-screen reel view.
        Tries clicking a 'Back' button first, then falls back to the hardware/system back press.
        Optionally verifies exit by checking if a specific element (like the Like button) disappears.

        Args:
            verify_xpath (Optional[str]): XPath of an element expected *inside* the reel view
                                         (e.g., Like button) to confirm exit when it vanishes.
                                         If None, only performs back action without verification.
            max_attempts (int): Max number of back presses to attempt.
            timeout (int): Timeout for waiting for verify_xpath to vanish.

        Returns:
            bool: True if navigation back was likely successful, False otherwise.
        """
        self.logger.info("Attempting to navigate back from reel view...")
        back_button_xpath = self.xpath_config.back_button_desc  # Define in xpath_config

        # Try clicking the explicit back button first
        if self.click_if_exists(back_button_xpath, timeout=1):
            self.logger.info("Clicked explicit 'Back' button.")
            time.sleep(random.uniform(1.0, 1.5))  # Wait for transition
        else:
            # If no explicit button, use system back press
            self.logger.info(
                "No explicit 'Back' button found, using system back press."
            )
            try:
                self.device.press("back")
                time.sleep(random.uniform(0.8, 1.2))
            except Exception as e:
                self.logger.error(f"Failed to execute system back press: {e}")
                return False  # Cannot proceed if back press fails

        # Verification loop
        if verify_xpath:
            self.logger.debug(
                f"Verifying exit by waiting for '{verify_xpath}' to vanish..."
            )
            if self.wait_for_element_vanish(verify_xpath, timeout=timeout):
                self.logger.info("✅ Exited reel view (verified by element vanishing).")
                return True
            else:
                # Element still exists, maybe need another back press?
                self.logger.warning(
                    f"⚠️ Element '{verify_xpath}' still visible after first back action."
                )
                # Try pressing back again (up to max_attempts)
                for attempt in range(max_attempts - 1):
                    self.logger.info(
                        f"Attempting system back press again (attempt {attempt + 2}/{max_attempts})"
                    )
                    try:
                        self.device.press("back")
                        time.sleep(random.uniform(0.8, 1.2))
                        if self.wait_for_element_vanish(
                            verify_xpath, timeout=2
                        ):  # Shorter timeout for subsequent checks
                            self.logger.info(
                                "✅ Exited reel view (verified after additional back press)."
                            )
                            return True
                    except Exception as e:
                        self.logger.error(
                            f"Error on subsequent back press attempt: {e}"
                        )
                        break  # Stop trying if back press fails
                self.logger.error(
                    "❌ Failed to exit reel view after multiple back attempts."
                )
                return False
        else:
            # No verification requested, assume success after back action
            self.logger.info("✅ Back action performed (no verification requested).")
            return True

    def navigate_to_explore(self, timeout: int = 10) -> bool:
        """
        Navigates to the Search/Explore tab and waits for the search bar to appear.

        Args:
            timeout (int): Timeout to wait for the explore page elements.

        Returns:
            bool: True if navigation was successful, False otherwise.
        """
        self.logger.info("📍 Navigating to Explore page...")
        explore_tab_xpath = self.xpath_config.explore_tab_desc  # Define in xpath_config
        search_bar_xpath = (
            self.xpath_config.explore_search_bar_rid
        )  # Define in xpath_config

        # Tap randomly within the explore tab element
        if not self.tap_random_within_element(
            explore_tab_xpath, label="Explore Tab", timeout=5
        ):
            self.logger.error("❌ Failed to find and tap Explore tab.")
            return False

        # Wait for the search bar element to confirm the page loaded
        if self.wait_for_element_appear(search_bar_xpath, timeout=timeout):
            self.logger.info("✅ Explore page loaded successfully (search bar found).")
            return True
        else:
            self.logger.error(
                f"❌ Explore page failed to load within {timeout}s (search bar not found)."
            )
            return False
