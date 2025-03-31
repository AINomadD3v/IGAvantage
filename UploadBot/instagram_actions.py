# instagram_actions.py

import re
import time
import random
import logging
import uiautomator2 as u2
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
        self.logger = logging.getLogger(__name__)

    def wait_for_app_ready(self, device, expected_xpath: str, retries: int = 3, delay: float = 2.0, timeout: int = 10):
        """
        Waits for the app to finish launching and be ready for UI inspection.
        Retries XPath inspection with backoff in case Accessibility is not ready yet.
        """
        self.logger.info("🕵️ Waiting for app UI to become inspectable...")

        for attempt in range(1, retries + 1):
            try:
                el = device.xpath(expected_xpath)
                if el.wait(timeout=timeout):
                    self.logger.info("✅ UI element detected: app appears ready")
                    return True
            except Exception as e:
                self.logger.warning(f"⚠️ UI not ready yet (attempt {attempt}/{retries}): {e}")
            
            wait_time = delay * attempt
            self.logger.info(f"⏳ Waiting {wait_time}s before retrying...")
            time.sleep(wait_time)

        logger.error("❌ App UI did not become inspectable in time.")
        return False


    def open_app(self):
        """
        Launch the Instagram clone via its package name.
        """
        try:
            self.logger.info(f"🚀 Launching app: {self.app_package}")
            self.device.app_start(self.app_package)
            time.sleep(2)  # brief delay to allow UI to load
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to launch app {self.app_package}: {str(e)}")
            return False

    def click_by_xpath(self, xpath, timeout=10):
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                center = element.center()
                self.device.click(*center)  # <-- ADB-level click
                self.logger.info(f"Clicked element with XPath: {xpath} at {center}")
                return True
            else:
                self.logger.info(f"Element with XPath '{xpath}' not found after waiting {timeout} seconds.")
                return False
        except Exception as e:
            self.logger.error(f"Error while waiting for or clicking element with XPath '{xpath}': {str(e)}")
            return False


    def new_post(self):
        if self.click_by_xpath(self.xpath_config.creation_tab):
            self.logger.info("Navigated to the new post creation tab.")
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
            self.logger.info(f"Successfully clicked on album: {album_name}")
            return True
        else:
            self.logger.error(f"Failed to click album: {album_name}")
            return False

    def select_first_video(self, timeout=10):
        try:
            if not self.device.xpath(self.xpath_config.video_thumbnails).wait(timeout):
                self.logger.error(f"No video thumbnails found after waiting {timeout} seconds.")
                return False
            
            first_video = self.device.xpath(self.xpath_config.video_thumbnails).get()
            
            if first_video is None:
                self.logger.error("No videos available.")
                return False
            
            first_video.click()
            # self.logger.info("Clicked on the first video")
            return True
        
        except Exception as e:
            self.logger.error(f"Error while selecting the first video: {str(e)}")
            return False


class SoundAdder:
    def __init__(self, device, app_package: str, insta_actions: InstagramInteractions):
        self.device = device
        self.app_package = app_package
        self.logger = logging.getLogger(__name__)
        self.insta_actions = insta_actions
        self.xpath_config = InstagramXPaths(app_package)
        self.logger.info(f"SoundAdder initialized with app_package: {app_package}")
        
    def select_random_track(self) -> bool:
        try:
            self.logger.info("Starting select_random_track method")
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
            self.logger.info("🎵 Starting add_music_to_reel method")

            # Step 1: Click 'Add audio' button using advanced search
            self.logger.info("🪩 Step 1: Looking for 'Add audio' button using advanced XPath...")

            # Advanced XPath: match either content-desc or text using smart matching
            add_audio_button = self.device.xpath("Add audio")  # Smart match: matches content-desc, text, or resource-id

            # Wait for it to appear
            if not add_audio_button.wait(timeout=10):
                self.logger.error("❌ 'Add audio' button not found after waiting 10 seconds")
                return False, "Failed to find 'Add audio' button", None

            # Log details and click
            self.logger.debug(f"🧠 'Add audio' found: text={add_audio_button.get_text()}, center={add_audio_button.center()}")
            add_audio_button.click()
            self.logger.info("✅ Clicked 'Add audio' button")
            time.sleep(2)


            # Step 2a: Select trending tab
            self.logger.info("🎛️ Step 2a: Clicking 'Trending' tab in audio selector...")

            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    trending_selector = self.device.xpath("Trending")
                    if trending_selector.exists:
                        trending_parent = trending_selector.get().parent()
                        self.logger.debug(f"🧠 Attempt {attempt}: Found 'Trending' tab parent, clicking...")
                        trending_parent.click()
                        self.logger.info("✅ Clicked 'Trending' tab")
                        time.sleep(1)
                        break
                    else:
                        self.logger.warning(f"⏳ Attempt {attempt}: 'Trending' tab not found yet")
                except Exception as e:
                    self.logger.warning(f"⚠️ Attempt {attempt}: Exception during click: {e}")
                time.sleep(1)
            else:
                self.logger.error("❌ Failed to click 'Trending' tab after multiple retries")
                return False, "'Trending' tab parent not found", None

            # Step 2b: Swipe bottom sheet up
            self.logger.info("📈 Step 2b: Swiping up bottom sheet to reveal full list...")
            try:
                possible_ids = ["bottom_sheet_drag_handle_prism", "bottom_sheet_drag_handle"]
                handle = None

                for rid in possible_ids:
                    xpath = f"//*[contains(@resource-id, '{rid}')]"
                    selector = self.device.xpath(xpath)
                    if selector.exists:
                        handle = selector.get()
                        self.logger.info(f"✅ Found drag handle using: '{rid}'")
                        break

                if handle is None:
                    self.logger.error("❌ No valid drag handle found using known resource-ids")
                    return False, "Drag handle not found", None

                start_x, start_y = handle.center()
                screen_height = self.device.info["displayHeight"]
                end_y = int(screen_height * 0.1)

                self.logger.debug(f"↕️ Swipe from ({start_x}, {start_y}) to ({start_x}, {end_y})")
                self.device.swipe(start_x, start_y, start_x, end_y, steps=10)
                self.logger.info("✅ Swipe complete")

            except Exception as e:
                self.logger.error(f"❌ Failed to swipe bottom sheet: {e}")
                return False, "Swipe failed", None


            # Step 3: Wait for and select a random track
            self.logger.info("🎼 Step 3: Waiting for track list and selecting a random track...")
            if not self.device.xpath("//*[contains(@resource-id, 'content_list')]").wait(timeout=5):
                self.logger.error("❌ Track list not found")
                return False, "Tracks list not found", None

            tracks = self.device.xpath("//*[contains(@resource-id, 'track_container')]").all()
            if not tracks:
                self.logger.error("❌ No tracks found")
                return False, "No tracks found", None

            self.logger.info(f"✅ Found {len(tracks)} track(s)")
            random_track = random.choice(tracks)
            content_desc = random_track.attrib.get("content-desc", "No description available")
            song_info = self.parse_track_info(content_desc)
            self.logger.info(f"🎵 Selected track: {song_info.get('Full Reel Title')}")

            track_xpath = random_track.get_xpath()
            if not self.insta_actions.click_by_xpath(track_xpath):
                self.logger.error("❌ Failed to click selected track")
                return False, "Failed to click selected track", None
            time.sleep(1)

            # Step 4: Confirm track selection
            self.logger.info("🎧 Step 4: Clicking 'Select Sound' button...")
            if not self.insta_actions.click_by_xpath("//*[contains(@resource-id, 'select_button_tap_target')]"):

                self.logger.error("❌ Failed to click 'Select Sound'")
                return False, "Failed to click Select Sound", None
            time.sleep(2)

            logger.info("Scrubbing song")
            self.scrub_music()

            # Step 5: Confirm with 'Done'
            self.logger.info("✅ Step 5: Clicking 'Done'")
            self.insta_actions.click_by_xpath(self.xpath_config.click_done)
            time.sleep(2)

            # Step 6: Finalize post with 'Next'
            self.logger.info("📲 Step 6: Clicking 'Next' to finalize post")
            self.insta_actions.click_by_xpath(self.xpath_config.next_button)
            time.sleep(1)

            self.logger.info("🎉 add_music_to_reel completed successfully")
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

        self.logger.info("🎚️ Scrubbing music with human-like multi-gesture realism...")

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
            self.logger.info(f"🔁 Performing {gesture_count} gesture(s)")

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

                self.logger.info(f"👆 Gesture {g+1}/{gesture_count}: {direction} swipe from ({start_x},{start_y}) → ({end_x},{end_y}) over {duration:.2f}s")

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

            self.logger.info("✅ Finished all gesture scrubs")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to scrub music with gesture: {e}", exc_info=True)
            return False




if __name__ == "__main__":
    logger = setup_logger(__name__)
    device = u2.connect()

    PACKAGE_NAME = "com.instagram.androie"

    logger.info("🚀 Starting test: randomly_scrub_music_position")

    try:
        # No popup handling, no Airtable or login needed
        interactions = InstagramInteractions(device, app_package=PACKAGE_NAME, airtable_manager=None)
        sound_adder = SoundAdder(device=device, app_package=PACKAGE_NAME, insta_actions=interactions)

        success = sound_adder.scrub_music()

        if success:
            logger.info("✅ Scrub music test passed")
        else:
            logger.error("❌ Scrub music test failed")

    except Exception as e:
        logger.error(f"💥 Exception during scrub test: {e}", exc_info=True)

# Full main testing function
# if __name__ == "__main__":
#     logger = setup_logger(__name__)
#     device = u2.connect()
#
#     PACKAGE_NAME = "com.instagram.androie"
#
#     logger.info("🚀 Starting test: add_music_to_reel with Trending watcher")
#
#     try:
#
#         popup_handler = PopupHandler(device)
#         interactions = InstagramInteractions(device, app_package=PACKAGE_NAME, airtable_manager=None)
#         sound_adder = SoundAdder(device=device, app_package=PACKAGE_NAME, insta_actions=interactions)
#         popup_handler.register_watchers()
#
#         success, msg, song_info = sound_adder.add_music_to_reel()
#
#         device.watcher.stop()  # stop watching once done
#
#         if success:
#             logger.info(f"✅ Music added successfully: {song_info}")
#         else:
#             logger.error(f"❌ Failed to add music: {msg}")
#
#     except Exception as e:
#         logger.error(f"💥 Exception during test: {e}", exc_info=True)
