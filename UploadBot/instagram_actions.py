# instagram_actions.py

import re
import time
import random
import logging
import uiautomator2 as u2
import subprocess
from uiautomator2.image import ImageX
from uiautomator2 import Direction
from typing import Optional, Tuple, Dict

from Shared.logger_config import setup_logger
from Shared.popup_handler import PopupHandler
from Shared.xpath_config import InstagramXPaths

logger = setup_logger(__name__)

class InstagramInteractions:
    def __init__(self, device, app_package, airtable_manager):
        self.device = device
        self.app_package = app_package
        self.xpath_config = InstagramXPaths(app_package)
        self.image_x = ImageX(device)
        self.airtable_manager = airtable_manager
        self.logger = setup_logger(__name__)

    def wait_for_app_ready(self, device, expected_xpath: str, retries: int = 3, delay: float = 2.0, timeout: int = 10):
        """
        Waits for the app to finish launching and be ready for UI inspection.
        Retries XPath inspection with backoff in case Accessibility is not ready yet.
        """
        self.logger.debug("🕵️ Waiting for app UI to become inspectable...")

        for attempt in range(1, retries + 1):
            try:
                el = device.xpath(expected_xpath)
                if el.wait(timeout=timeout):
                    self.logger.debug("✅ UI element detected: app appears ready")
                    return True
            except Exception as e:
                self.logger.warning(f"⚠️ UI not ready yet (attempt {attempt}/{retries}): {e}")
            
            wait_time = delay * attempt
            self.logger.info(f"⏳ Waiting {wait_time}s before retrying...")
            time.sleep(wait_time)

        logger.error("❌ App UI did not become inspectable in time.")
        return False

    def open_app(self) -> bool:

        try:
            logger.debug(f"🚀 Launching app via adb am start: {self.app_package}")

            # Strip whitespace in case Airtable value or env had extra space
            clean_package = self.app_package.strip()
            component = f"{clean_package}/.activity.MainTabActivity"

            subprocess.run([
                "adb", "shell", "am", "start",
                "-n", component
            ], check=True)

            time.sleep(2.5)
            self.device = u2.connect()

            for attempt in range(10):
                current = self.device.app_current()
                logger.debug(f"[{attempt+1}/10] Foreground app: {current}")
                if current.get("package") == clean_package:
                    logger.debug("✅ App is now in foreground")
                    return True
                time.sleep(1.0)

            logger.error("❌ App did not become foreground after retries")
            return False

        except Exception as e:
            logger.error(f"❌ Failed to launch app {self.app_package}: {e}", exc_info=True)
            return False

    def click_by_xpath(self, xpath, timeout=10):
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                center = element.center()
                self.device.click(*center)  # <-- ADB-level click
                self.logger.debug(f"Clicked element with XPath: {xpath} at {center}")
                return True
            else:
                self.logger.info(f"Element with XPath '{xpath}' not found after waiting {timeout} seconds.")
                return False
        except Exception as e:
            self.logger.error(f"Error while waiting for or clicking element with XPath '{xpath}': {str(e)}")
            return False


    def new_post(self):
        if self.click_by_xpath("//*[contains(@content-desc, 'Create')]"):
            self.logger.debug("Navigated to the new post creation tab.")
        else:
            self.logger.error("Failed to navigate to the new post creation tab.")

    def get_account_name(self):
        try:
            xpath = self.xpath_config.story_avatar
            elements = self.device.xpath(xpath).all()
            self.logger.debug(f"Found {len(elements)} elements matching the story avatar XPath")
            
            for element in elements:
                content_desc = element.attrib.get("content-desc")
                self.logger.debug(f"Element content description: {content_desc}")
                
                if content_desc:
                    username_match = re.search(r"([^']+)'s story at column", content_desc)
                    if username_match:
                        username = username_match.group(1)
                        self.logger.debug(f"Account name extracted: {username}")
                        return username
            
            self.logger.warning("No valid username found in content descriptions")
            
            # Fallback: try to get the username from the profile page
            profile_xpath = self.xpath_config.action_bar_large_title_auto_size
            profile_element = self.device.xpath(profile_xpath)
            if profile_element.exists:
                profile_username = profile_element.get_text()
                if profile_username:
                    self.logger.info(f"Fallback: Found username from profile page: {profile_username}")
                    return profile_username
            
            raise ValueError("No valid username found in content descriptions or profile page")
        except Exception as e:
            self.logger.error(f"Error in get_account_name: {e}")
            raise

    def find_and_click_album(self, album_name):
        self.logger.debug(f"Attempting to click album: {album_name}")
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
        Waits for and clicks the first fully loaded video thumbnail.
        A thumbnail is considered 'loaded' if its child View has a content-desc
        starting with 'Video thumbnail'.
        """
        grid_xpath = "//android.widget.GridView[contains(@resource-id, 'gallery_recycler_view')]/android.view.ViewGroup"
        loaded_thumb_xpath = ".//android.view.View[contains(@resource-id, 'gallery_grid_item_thumbnail') and starts-with(@content-desc, 'Video thumbnail')]"

        for second in range(timeout):
            try:
                elements = self.device.xpath(grid_xpath).all()

                if not elements:
                    self.logger.debug(f"⏳ [{second+1}/{timeout}] Grid empty, retrying...")
                    time.sleep(1)
                    continue

                for idx, container in enumerate(elements):
                    try:
                        # Narrow to only loaded thumbnails
                        thumbnail = container.elem.xpath(loaded_thumb_xpath)
                        if thumbnail:
                            self.logger.debug(f"🎯 Clicking loaded video at index {idx}")
                            container.click()
                            return True
                    except Exception as e:
                        self.logger.debug(f"⚠️ Skipping index {idx}, error: {e}")

                self.logger.debug(f"⏳ [{second+1}/{timeout}] No loaded videos found, retrying...")
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"💥 Exception during thumbnail check: {e}", exc_info=True)
                time.sleep(1)

        self.logger.error(f"❌ No fully loaded video thumbnails found after {timeout} seconds.")
        return False


    def wait_for_posted_caption(self, caption: str, username: str, timeout=120, poll_interval=2) -> bool:
        """
        Waits for confirmation that the reel was posted by:
        - Matching the caption prefix (40% match via starts-with or contains)
        - Detecting the insights pill
        - Matching the username profile picture element
        """
        if not caption:
            self.logger.error("❌ No caption provided for reel post verification")
            return False

        if not username:
            self.logger.error("❌ No username provided for fallback reel detection")
            return False

        trimmed_caption = caption.strip()[:40].replace('"', '').replace("'", "")
        caption_xpath = f"//android.view.ViewGroup[starts-with(@content-desc, '{trimmed_caption}')]"
        insights_xpath = "//android.view.ViewGroup[contains(@resource-id, 'clips_viewer_insights_pill')]"
        profile_xpath = f"//android.widget.ImageView[contains(@content-desc, 'Profile picture of {username}') or contains(@content-desc, '{username}')]"

        self.logger.debug(f"🔍 Waiting to verify Reel was posted")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.device.xpath(caption_xpath).exists:
                self.logger.info("✅ Caption detected in reel view")
                return True

            if self.device.xpath(insights_xpath).exists:
                self.logger.info("✅ Reel insights pill detected")
                return True

            if self.device.xpath(profile_xpath).exists:
                self.logger.info("✅ Username detected in posted reel")
                return True

            self.logger.debug("⏳ No match yet, polling again...")
            time.sleep(poll_interval)

        self.logger.error(f"❌ Reel post verification failed after {timeout} seconds")
        return False

    def close_app(self) -> bool:
        """
        Attempts to stop the Instagram app cleanly using u2 and falls back to ADB if needed.
        """
        pkg = self.app_package.strip()
        self.logger.debug(f"🛑 Attempting to stop app: {pkg}")

        try:
            self.device.app_stop(pkg)
            time.sleep(1)

            current_pkg = self.device.app_current().get("package")
            if current_pkg == pkg:
                self.logger.warning("⚠️ u2 stop failed, falling back to ADB")
                import subprocess
                subprocess.run(["adb", "shell", "am", "force-stop", pkg], check=True)
                self.logger.debug("✅ App stopped via ADB fallback")
            else:
                self.logger.debug("✅ App stopped successfully via u2")

            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to stop app: {e}", exc_info=True)
            return False






class SoundAdder:
    def __init__(self, device, app_package: str, insta_actions: InstagramInteractions):
        self.device = device
        self.app_package = app_package
        self.insta_actions = insta_actions
        self.xpath_config = InstagramXPaths(app_package)
        self.logger = setup_logger(__name__)
        
    def select_random_track(self) -> bool:
        try:
            self.logger.debug("Starting select_random_track method")
            self.logger.debug(f"Using tracks_list xpath: {self.xpath_config.tracks_list}")
            
            # First, wait for the tracks list to be visible
            tracks_list = self.device.xpath(self.xpath_config.tracks_list)
            self.logger.debug("Waiting for tracks list to be visible...")
            if not tracks_list.wait(timeout=5):
                self.logger.error(f"Tracks list not found using xpath: {self.xpath_config.tracks_list}")
                return False

            self.logger.debug("Tracks list found, getting all track containers...")
            self.logger.debug(f"Using track_container xpath: {self.xpath_config.track_container}")
            
            # Get all track containers
            tracks = self.device.xpath(self.xpath_config.track_container).all()
            if not tracks:
                self.logger.error(f"No tracks found in the list using xpath: {self.xpath_config.track_container}")
                return False

            self.logger.info(f"Found {len(tracks)} tracks available")
            
            # Select a random track
            random_track = random.choice(tracks)
            
            # Log the track info for debugging
            content_desc = random_track.attrib.get('content-desc', 'No description available')
            self.logger.info(f"Selected track: {content_desc}")
            
            # Click the selected track using its specific xpath
            track_xpath = random_track.get_xpath()
            self.logger.debug(f"Attempting to click track with xpath: {track_xpath}")
            click_result = self.insta_actions.click_by_xpath(track_xpath)
            self.logger.debug(f"Track click result: {click_result}")
            return click_result

        except Exception as e:
            self.logger.error(f"Error selecting random track: {str(e)}", exc_info=True)
            return False

    def add_music_to_reel(self) -> Tuple[bool, Optional[str], Optional[Dict[str, str]]]:
        """
        Add music to a reel and return success status, message, and song information
        """
        try:
            self.logger.debug("🎵 Starting add_music_to_reel method")

            # Step 1: Click 'Add audio' button using advanced search
            self.logger.debug("🪩 Step 1: Looking for 'Add audio' button using advanced XPath...")

            add_audio_button = self.device.xpath("Add audio")
            if not add_audio_button.wait(timeout=10):
                self.logger.error("❌ 'Add audio' button not found after waiting 10 seconds")
                return False, "Failed to find 'Add audio' button", None

            self.logger.debug(f"🧠 'Add audio' found: text={add_audio_button.get_text()}, center={add_audio_button.center()}")
            add_audio_button.click()
            self.logger.debug("✅ Clicked 'Add audio' button")
            time.sleep(2)

            # Step 2a: Attempt to click 'Trending' tab (optional fallback if not found)
            self.logger.debug("🎛️ Step 2a: Attempting to click 'Trending' tab in audio selector...")
            max_retries = 3
            trending_clicked = False

            for attempt in range(1, max_retries + 1):
                try:
                    trending_selector = self.device.xpath("Trending")
                    if trending_selector.exists:
                        trending_parent = trending_selector.get().parent()
                        self.logger.debug(f"🧠 Attempt {attempt}: Found 'Trending' tab parent, clicking...")
                        trending_parent.click()
                        self.logger.debug("✅ Clicked 'Trending' tab")
                        trending_clicked = True
                        time.sleep(1)
                        break
                    else:
                        self.logger.debug(f"⏳ Attempt {attempt}: 'Trending' tab not found yet")
                except Exception as e:
                    self.logger.warning(f"⚠️ Attempt {attempt}: Exception during click: {e}")
                time.sleep(1)

            if not trending_clicked:
                self.logger.warning("⚠️ 'Trending' tab not found after retries, skipping 'Select Sound' click")

            # Step 2b: Swipe bottom sheet up
            self.logger.debug("📈 Step 2b: Swiping up bottom sheet to reveal full list...")
            try:
                possible_ids = ["bottom_sheet_drag_handle_prism", "bottom_sheet_drag_handle"]
                handle = None

                for rid in possible_ids:
                    xpath = f"//*[contains(@resource-id, '{rid}')]"
                    selector = self.device.xpath(xpath)
                    if selector.exists:
                        handle = selector.get()
                        self.logger.debug(f"✅ Found drag handle using: '{rid}'")
                        break

                if handle is None:
                    self.logger.error("❌ No valid drag handle found using known resource-ids")
                    return False, "Drag handle not found", None

                start_x, start_y = handle.center()
                screen_height = self.device.info["displayHeight"]
                end_y = int(screen_height * 0.1)

                self.logger.debug(f"↕️ Swipe from ({start_x}, {start_y}) to ({start_x}, {end_y})")
                self.device.swipe(start_x, start_y, start_x, end_y, steps=10)
                self.logger.debug("✅ Swipe complete")

            except Exception as e:
                self.logger.error(f"❌ Failed to swipe bottom sheet: {e}")
                return False, "Swipe failed", None

            # Step 3: Wait for and select a random track
            self.logger.debug("🎼 Step 3: Waiting for track list and selecting a random track...")
            if not self.device.xpath("//*[contains(@resource-id, 'content_list') or contains(@resource-id, 'preview_items')]").wait(timeout=5):
                self.logger.error("❌ Track list not found")
                return False, "Tracks list not found", None

            tracks = self.device.xpath("//*[contains(@resource-id, 'track_container')]").all()
            if not tracks:
                self.logger.error("❌ No tracks found")
                return False, "No tracks found", None

            self.logger.debug(f"✅ Found {len(tracks)} track(s)")
            random_track = random.choice(tracks)
            content_desc = random_track.attrib.get("content-desc", "No description available")
            song_info = self.parse_track_info(content_desc)
            self.logger.debug(f"🎵 Selected track: {song_info.get('Full Reel Title')}")

            track_xpath = random_track.get_xpath()
            if not self.insta_actions.click_by_xpath(track_xpath):
                self.logger.error("❌ Failed to click selected track")
                return False, "Failed to click selected track", None
            time.sleep(1)

            # Step 4: Only click 'Select Sound' if trending was clicked
            if trending_clicked:
                self.logger.debug("🎧 Step 4: Clicking 'Select Sound' button...")
                if not self.insta_actions.click_by_xpath("//*[contains(@resource-id, 'select_button_tap_target')]"):
                    self.logger.error("❌ Failed to click 'Select Sound'")
                    return False, "Failed to click Select Sound", None
                time.sleep(2)

            self.logger.debug("🎚️ Waiting for scrubber view to load before interaction...")
            scrubber_xpath = "//*[contains(@resource-id, 'scrubber_recycler_view')]"
            scrubber = self.device.xpath(scrubber_xpath)

            if not scrubber.wait(timeout=10):
                self.logger.error("❌ Scrubber view not loaded after waiting")
                return False, "Scrubber view not loaded", song_info

            self.logger.debug("✅ Scrubber view loaded successfully")
            self.scrub_music()

            # Step 5: Confirm with 'Done'
            self.logger.debug("✅ Step 5: Clicking 'Done'")
            self.insta_actions.click_by_xpath(self.xpath_config.click_done)
            time.sleep(2)

            # Step 6: Finalize post with 'Next'
            self.logger.debug("📲 Step 6: Clicking 'Next' to finalize post")
            next_button_xpath = "//android.widget.Button[@content-desc='Next']"
            max_next_retries = 20

            for attempt in range(1, max_next_retries + 1):
                self.logger.debug(f"🔁 Attempt {attempt}/{max_next_retries} to click 'Next'")

                if not self.insta_actions.click_by_xpath(next_button_xpath):
                    self.logger.warning("⚠️ Failed to click 'Next' on this attempt")
                else:
                    self.logger.debug("✅ Clicked 'Next', checking if it disappears...")
                    if self.device.xpath(next_button_xpath).wait_gone(timeout=5):
                        self.logger.info("✅ 'Next' button disappeared — transition confirmed")
                        break
                    else:
                        self.logger.warning("⚠️ 'Next' button still visible after click — retrying...")

                time.sleep(4)

            else:
                self.logger.error("❌ 'Next' button did not disappear after multiple attempts")
                return False, "Next button stuck after retries", None

            self.logger.debug("🎉 add_music_to_reel completed successfully")
            return True, "Successfully added music to reel", song_info

        except Exception as e:
            self.logger.error(f"💥 Exception in add_music_to_reel: {str(e)}", exc_info=True)
            return False, f"Error occurred: {str(e)}", None

    def parse_track_info(self, content_desc: str) -> Dict[str, str]:
        try:
            # Remove "Select track " from the beginning
            content = content_desc.replace("Select track ", "")
            
            # Use regex to extract components
            pattern = r"(.*?) by (.*?),(\d+[KM]?) reels,(\d+:\d+)"
            match = re.match(pattern, content)
            
            if match:
                song_title, artist, reel_count, duration = match.groups()
                
                return {
                    'Song Used': song_title.strip(),
                    'Artist': artist.strip(),
                    'Reel Used Count': reel_count.strip(),
                    'Song duration': duration.strip(),
                    'Full Reel Title': content_desc  # Keep the full original string
                }
            else:
                # Fallback if regex doesn't match
                return {
                    'Full Reel Title': content_desc,
                    'raw_content': content
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing track info: {str(e)}")
            return {'Full Reel Title': content_desc}

    def scrub_music(self):
        """
        Performs multiple realistic touch gestures on the scrubber to simulate user seeking behavior.
        Includes randomized direction, duration, distance, jitter, and pauses.
        """
        import time
        import random

        self.logger.debug("🎚️ Scrubbing music with human-like multi-gesture realism...")

        try:
            scrubber_xpath = "//*[contains(@resource-id, 'scrubber_recycler_view')]"
            scrubber = self.device.xpath(scrubber_xpath)

            if not scrubber.wait(timeout=5):
                self.logger.error("❌ Scrubber view not found")
                return False

            el = scrubber.get()
            bounds = el.bounds
            screen_width = self.device.info["displayWidth"]
            screen_height = self.device.info["displayHeight"]

            gesture_count = random.randint(2, 4)  # realistic adjustment attempts
            self.logger.debug(f"🔁 Performing {gesture_count} gesture(s)")

            for g in range(gesture_count):
                direction = random.choice(["left", "right"])
                fraction = random.uniform(0.15, 0.4)  # smaller adjustments look human
                distance = int((bounds[2] - bounds[0]) * fraction)
                distance = -distance if direction == "left" else distance
                duration = random.uniform(0.3, 0.7)

                start_x = max(bounds[0] + 20, min(bounds[2] - 20, (bounds[0] + bounds[2]) // 2))
                start_y = (bounds[1] + bounds[3]) // 2 + random.randint(-2, 2)
                end_x = max(0, min(screen_width - 1, start_x + distance))
                end_y = start_y + random.randint(-2, 2)

                self.logger.debug(f"👆 Gesture {g+1}/{gesture_count}: {direction} swipe from ({start_x},{start_y}) → ({end_x},{end_y}) over {duration:.2f}s")

                self.device.touch.down(start_x, start_y)
                steps = 10
                for i in range(1, steps + 1):
                    t = i / steps
                    interp_x = int(start_x + (end_x - start_x) * t + random.uniform(-1, 1))
                    interp_y = int(start_y + (end_y - start_y) * t + random.uniform(-1, 1))
                    interp_x = max(0, min(screen_width - 1, interp_x))
                    interp_y = max(0, min(screen_height - 1, interp_y))
                    self.device.touch.move(interp_x, interp_y)
                    time.sleep(duration / steps)
                self.device.touch.up(interp_x, interp_y)

                pause = random.uniform(0.3, 1.0)
                self.logger.debug(f"⏸️ Pausing {pause:.2f}s before next gesture...")
                time.sleep(pause)

            self.logger.debug("✅ Finished all gesture scrubs")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to scrub music with gesture: {e}", exc_info=True)
            return False

