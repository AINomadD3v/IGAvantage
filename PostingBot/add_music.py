import os  # Added for capture_frames_from_current_reel
import random
import re
import subprocess
import time
from typing import Dict, Optional, Tuple

import uiautomator2 as u2

from Shared.logger_config import setup_logger

# Assuming SwipeHelper class is moved to its own file
from Shared.xpath_config import InstagramXPaths

logger = setup_logger("AddMusic")


class SoundAdder:
    def __init__(self, device, app_package: str, insta_actions: InstagramInteractions):
        self.device = device
        self.app_package = app_package
        self.insta_actions = insta_actions
        self.xpath_config = InstagramXPaths(app_package)
        self.logger = logger

    def select_random_track(self) -> bool:
        try:
            self.logger.debug("Starting select_random_track method")
            self.logger.debug(
                f"Using tracks_list xpath: {self.xpath_config.tracks_list}"
            )

            # First, wait for the tracks list to be visible
            tracks_list = self.device.xpath(self.xpath_config.tracks_list)
            self.logger.debug("Waiting for tracks list to be visible...")
            if not tracks_list.wait(timeout=5):
                self.logger.error(
                    f"Tracks list not found using xpath: {self.xpath_config.tracks_list}"
                )
                return False

            self.logger.debug("Tracks list found, getting all track containers...")
            self.logger.debug(
                f"Using track_container xpath: {self.xpath_config.track_container}"
            )

            # Get all track containers
            tracks = self.device.xpath(self.xpath_config.track_container).all()
            if not tracks:
                self.logger.error(
                    f"No tracks found in the list using xpath: {self.xpath_config.track_container}"
                )
                return False

            self.logger.info(f"Found {len(tracks)} tracks available")

            # Select a random track
            random_track = random.choice(tracks)

            # Log the track info for debugging
            content_desc = random_track.attrib.get(
                "content-desc", "No description available"
            )
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
            self.logger.debug(
                "🪩 Step 1: Looking for 'Add audio' button using advanced XPath..."
            )

            add_audio_button = self.device.xpath(
                self.xpath_config.add_audio_text_or_desc_general
            )
            if not add_audio_button.wait(timeout=10):
                self.logger.error(
                    "❌ 'Add audio' button not found after waiting 10 seconds"
                )
                return False, "Failed to find 'Add audio' button", None

            self.logger.debug(
                f"🧠 'Add audio' found: text={add_audio_button.get_text()}, center={add_audio_button.center()}"
            )
            add_audio_button.click()
            self.logger.debug("✅ Clicked 'Add audio' button")
            time.sleep(2)

            # Step 2a: Attempt to click 'Trending' tab (optional fallback if not found)
            self.logger.debug(
                "🎛️ Step 2a: Attempting to click 'Trending' tab in audio selector..."
            )
            max_retries = 3
            trending_clicked = False

            for attempt in range(1, max_retries + 1):
                try:
                    trending_selector = self.device.xpath(
                        self.xpath_config.trending_text_or_desc_general
                    )
                    if trending_selector.exists:
                        trending_parent = trending_selector.get().parent()
                        self.logger.debug(
                            f"🧠 Attempt {attempt}: Found 'Trending' tab parent, clicking..."
                        )
                        trending_parent.click()
                        self.logger.debug("✅ Clicked 'Trending' tab")
                        trending_clicked = True
                        time.sleep(1)
                        break
                    else:
                        self.logger.debug(
                            f"⏳ Attempt {attempt}: 'Trending' tab not found yet"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Attempt {attempt}: Exception during click: {e}"
                    )
                time.sleep(1)

            if not trending_clicked:
                self.logger.warning(
                    "⚠️ 'Trending' tab not found after retries, skipping 'Select Sound' click"
                )

            # Step 2b: Swipe bottom sheet up
            self.logger.debug(
                "📈 Step 2b: Swiping up bottom sheet to reveal full list..."
            )
            try:
                possible_ids = self.xpath_config.audio_bottom_sheet_drag_handle_rids
                handle = None

                for rid in possible_ids:
                    xpath = f"//*[contains(@resource-id, '{rid}')]"
                    selector = self.device.xpath(xpath)
                    if selector.exists:
                        handle = selector.get()
                        self.logger.debug(f"✅ Found drag handle using: '{rid}'")
                        break

                if handle is None:
                    self.logger.error(
                        "❌ No valid drag handle found using known resource-ids"
                    )
                    return False, "Drag handle not found", None

                start_x, start_y = handle.center()
                screen_height = self.device.info["displayHeight"]
                end_y = int(screen_height * 0.1)

                self.logger.debug(
                    f"↕️ Swipe from ({start_x}, {start_y}) to ({start_x}, {end_y})"
                )
                self.device.swipe(start_x, start_y, start_x, end_y, steps=10)
                self.logger.debug("✅ Swipe complete")

            except Exception as e:
                self.logger.error(f"❌ Failed to swipe bottom sheet: {e}")
                return False, "Swipe failed", None

            # Step 3: Wait for and select a random track
            self.logger.debug(
                "🎼 Step 3: Waiting for track list and selecting a random track..."
            )
            if not self.device.xpath(self.xpath_config.audio_tracks_list_general).wait(
                timeout=5
            ):
                self.logger.error("❌ Track list not found")
                return False, "Tracks list not found", None

            tracks = self.device.xpath(
                "//*[contains(@resource-id, 'track_container')]"
            ).all()
            if not tracks:
                self.logger.error("❌ No tracks found")
                return False, "No tracks found", None

            self.logger.debug(f"✅ Found {len(tracks)} track(s)")
            random_track = random.choice(tracks)
            content_desc = random_track.attrib.get(
                "content-desc", "No description available"
            )
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
                if not self.insta_actions.click_by_xpath(
                    self.xpath_config.audio_select_song_button_general
                ):
                    self.logger.error("❌ Failed to click 'Select Sound'")
                    return False, "Failed to click Select Sound", None
                time.sleep(2)

            self.logger.debug(
                "🎚️ Waiting for scrubber view to load before interaction..."
            )
            scrubber_xpath = self.xpath_config.audio_scrubber_view
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
            next_button_xpath = self.xpath_config.next_button
            max_next_retries = 20

            for attempt in range(1, max_next_retries + 1):
                self.logger.debug(
                    f"🔁 Attempt {attempt}/{max_next_retries} to click 'Next'"
                )

                if not self.insta_actions.click_by_xpath(next_button_xpath):
                    self.logger.warning("⚠️ Failed to click 'Next' on this attempt")
                else:
                    self.logger.debug("✅ Clicked 'Next', checking if it disappears...")
                    if self.device.xpath(next_button_xpath).wait_gone(timeout=5):
                        self.logger.info(
                            "✅ 'Next' button disappeared — transition confirmed"
                        )
                        break
                    else:
                        self.logger.warning(
                            "⚠️ 'Next' button still visible after click — retrying..."
                        )

                time.sleep(4)

            else:
                self.logger.error(
                    "❌ 'Next' button did not disappear after multiple attempts"
                )
                return False, "Next button stuck after retries", None

            self.logger.debug("🎉 add_music_to_reel completed successfully")
            return True, "Successfully added music to reel", song_info

        except Exception as e:
            self.logger.error(
                f"💥 Exception in add_music_to_reel: {str(e)}", exc_info=True
            )
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
                    "Song Used": song_title.strip(),
                    "Artist": artist.strip(),
                    "Reel Used Count": reel_count.strip(),
                    "Song duration": duration.strip(),
                    "Full Reel Title": content_desc,  # Keep the full original string
                }
            else:
                # Fallback if regex doesn't match
                return {"Full Reel Title": content_desc, "raw_content": content}

        except Exception as e:
            self.logger.error(f"Error parsing track info: {str(e)}")
            return {"Full Reel Title": content_desc}

    def scrub_music(self):
        """
        Performs multiple realistic touch gestures on the scrubber to simulate user seeking behavior.
        Includes randomized direction, duration, distance, jitter, and pauses.
        """

        self.logger.debug("🎚️ Scrubbing music with human-like multi-gesture realism...")

        try:
            scrubber_xpath = self.xpath_config.audio_scrubber_view
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

                start_x = max(
                    bounds[0] + 20, min(bounds[2] - 20, (bounds[0] + bounds[2]) // 2)
                )
                start_y = (bounds[1] + bounds[3]) // 2 + random.randint(-2, 2)
                end_x = max(0, min(screen_width - 1, start_x + distance))
                end_y = start_y + random.randint(-2, 2)

                self.logger.debug(
                    f"👆 Gesture {g+1}/{gesture_count}: {direction} swipe from ({start_x},{start_y}) → ({end_x},{end_y}) over {duration:.2f}s"
                )

                self.device.touch.down(start_x, start_y)
                steps = 10
                for i in range(1, steps + 1):
                    t = i / steps
                    interp_x = int(
                        start_x + (end_x - start_x) * t + random.uniform(-1, 1)
                    )
                    interp_y = int(
                        start_y + (end_y - start_y) * t + random.uniform(-1, 1)
                    )
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
            self.logger.error(
                f"❌ Failed to scrub music with gesture: {e}", exc_info=True
            )
            return False
