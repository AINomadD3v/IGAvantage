# instagram_actions.py

import re
import time
import random
import logging
import uiautomator2 as u2
from uiautomator2.image import ImageX
from typing import Optional, Tuple, Dict

from Shared.logger_config import setup_logger
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


    def click_by_xpath(self, xpath, timeout=10):
        try:
            element = self.device.xpath(xpath)
            if element.wait(timeout=timeout):
                element.click()
                self.logger.info(f"Clicked element with XPath: {xpath}")
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

    def new_image_post(self):
        if self.click_by_xpath(self.xpath_config.creation_tab):
            self.logger.debug("Navigated to the new post creation tab.")
        else:
            self.logger.error("Failed to navigate to the new post creation tab.")

    def select_image(self, timeout=10):
        try:
            self.logger.debug("Attempting to select the first image")
            self.logger.debug(f"XPath for image thumbnails: {self.xpath_config.image_thumbnails}")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                thumbnails = self.device.xpath(self.xpath_config.image_thumbnails).all()
                self.logger.debug(f"Thumbnail elements: {thumbnails}")
                
                if thumbnails:
                    first_image = thumbnails[0]
                    self.logger.debug(f"First image element: {first_image}")
                    
                    first_image.click()
                    self.logger.info("Clicked on the first image")
                    return True
                
                time.sleep(1)  # Wait a bit before checking again
            
            self.logger.error(f"No image thumbnails found after waiting {timeout} seconds.")
            return False
        
        except Exception as e:
            self.logger.error(f"Error while selecting the image: {str(e)}", exc_info=True)
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

            # Step 1: Click 'Add audio' button
            self.logger.info("🪩 Step 1: Clicking 'Add audio' button...")
            self.logger.debug(f"🔍 XPath: {self.xpath_config.add_sound}")
            if not self.insta_actions.click_by_xpath(self.xpath_config.add_sound):
                self.logger.error("❌ Failed to click 'Add audio' button")
                return False, "Failed to click Add audio button", None
            time.sleep(2)

            # Step 2a: Select trending tab
            self.logger.info("🎛️ Step 2a: Clicking trending tab in audio selector...")
            tab_xpath = '//androidx.compose.ui.platform.ComposeView[@resource-id="com.instagram.androie:id/tab_list_compose_view"]/android.view.View/android.view.View/android.view.View[2]'
            tab_container = self.device.xpath(tab_xpath)

            if not tab_container.wait(timeout=5):
                self.logger.error("❌ Audio tab container not found")
                return False, "Tab container not found", None

            children = tab_container.all()
            if not children:
                self.logger.error("❌ No children in tab container")
                return False, "No child elements found in tab container", None

            self.logger.debug(f"🧠 Found tab text: {children[0].text}")
            children[0].click()
            time.sleep(1)

            # Step 2b: Swipe bottom sheet up
            self.logger.info("📈 Step 2b: Swiping up bottom sheet to reveal full list...")
            handle_xpath = '//android.widget.ImageView[@resource-id="com.instagram.androie:id/bottom_sheet_drag_handle_prism"]'
            try:
                handle = self.device.xpath(handle_xpath).get(timeout=5)
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
            if not self.device.xpath(self.xpath_config.tracks_list).wait(timeout=5):
                self.logger.error("❌ Track list not found")
                return False, "Tracks list not found", None

            tracks = self.device.xpath(self.xpath_config.track_container).all()
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
            if not self.insta_actions.click_by_xpath(self.xpath_config.click_select_song):
                self.logger.error("❌ Failed to click 'Select Sound'")
                return False, "Failed to click Select Sound", None
            time.sleep(2)

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

if __name__ == "__main__":

    logger = setup_logger(__name__)
    device = u2.connect()

    PACKAGE_NAME = "com.instagram.androie"   # your actual clone package
    TEST_USERNAME = "lexjohnson764"          # must match folder name pushed earlier

    logger.info("🚀 Starting Instagram UI test from 'New Post' screen")

    interactions = InstagramInteractions(device, app_package=PACKAGE_NAME, airtable_manager=None)

    try:
        # Step 1: Open new post screen
        logger.info("📱 Opening new post screen...")
        interactions.new_post()
        time.sleep(1)

        # Step 2: Wait for and click "REEL" tab (uiautomator2 advanced smart XPath)
        logger.info("🎬 Waiting for 'REEL' tab and clicking it...")
        reel_xpath = device.xpath("REEL")
        if not reel_xpath.wait(timeout=10):
            logger.error("❌ 'REEL' tab not found")
            exit()
        reel_xpath.click()
        logger.info("✅ 'REEL' tab clicked")
        time.sleep(2)

        # Step 3: Wait for confirmation of entering "New reel" screen
        logger.info("🖼️ Waiting for 'New reel' text to confirm gallery loaded...")
        new_reel_xpath = device.xpath("New reel")
        if not new_reel_xpath.wait(timeout=10):
            logger.error("❌ 'New reel' screen not detected")
            exit()
        logger.info("✅ 'New reel' screen confirmed")

        # Step 4: Select the first video in the album
        logger.info("🎞️ Selecting first video in album")
        if not interactions.select_first_video():
            logger.error("❌ Failed to select first video")
            exit()
        time.sleep(2)

        # Step 5: Wait for 'Add audio' button to confirm reel editor is loaded
        logger.info("🕒 Waiting for 'Add audio' UI to confirm reel editor loaded...")
        add_audio_el = device.xpath("Add audio")
        if not add_audio_el.wait(timeout=10):
            logger.error("❌ 'Add audio' screen not detected")
            exit()
        logger.info("✅ 'Add audio' screen confirmed")

        # Step 6: Add sound to the reel
        logger.info("🎵 Adding sound to reel...")
        sound_adder = SoundAdder(device=device, app_package=PACKAGE_NAME, insta_actions=interactions)
        success, msg, song_info = sound_adder.add_music_to_reel()
        if not success:
            logger.error(f"❌ Failed to add sound: {msg}")
            exit()
        logger.info(f"✅ Sound added: {song_info.get('Full Reel Title')}")
        time.sleep(2)

        # TODO Need to add in caption, then it is done

        # Step 8: Share the reel
        logger.info("📤 Sharing the reel...")
        if not interactions.click_by_xpath(interactions.xpath_config.reels_share_button):
            logger.error("❌ Failed to share the reel")
            exit()
        logger.info("✅ Reel shared successfully!")

    except Exception as e:
        logger.error(f"💥 Exception during Instagram test flow: {e}", exc_info=True)

