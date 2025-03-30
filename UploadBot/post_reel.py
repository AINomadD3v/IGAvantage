# post_reel.py
import os
import time
import uiautomator2 as u2
from typing import Tuple, Optional

from logger_config import setup_logger
from airtable_client import AirtableClient
from device_manager import MediaCleaner
from instagram_actions import InstagramInteractions, SoundAdder
from content_management import ContentManager
from generate_caption import generate_and_enter_caption  

logger = setup_logger(__name__)

def post_reel(app_package_name: str, PROJECT_ROOT: str, airtable_client: AirtableClient) -> Tuple[bool, Optional[str]]:
    logger.info(f"🎬 Starting post_reel for {app_package_name}")

    device = u2.connect()
    content_manager = ContentManager()
    insta_actions = InstagramInteractions(device, app_package=app_package_name, airtable_manager=airtable_client)
    xpath_config = insta_actions.xpath_config

    remote_path = None
    airtable_success = False

    try:
        # Step 1: Get Airtable record
        logger.info("📥 Fetching unposted Airtable record...")
        record = airtable_client.get_single_unposted_record()
        if not record:
            return False, "No unposted record available"

        record_id = record['id']
        fields = record['fields']
        account_name = fields['username']
        media_url = fields['media_url']
        caption_from_airtable = fields.get('caption', '')
        media_type = 'reel'

        # Step 2: Download media from Google Drive
        logger.info("☁️ Downloading media from Google Drive...")
        output_dir = os.path.join(PROJECT_ROOT, "temp")
        success, local_path, mime_type, _ = content_manager.download_drive_file(media_url, output_dir)
        if not success or not local_path:
            return False, "Download failed"
        logger.info(f"📂 Downloaded file to: {local_path}")

        # Step 3: Push to device
        logger.info("📲 Pushing file to Android device...")
        push_success, remote_path = content_manager.push_media_to_device(local_path, account_name, media_type, device)
        if not push_success:
            return False, "Push to device failed"
        logger.info(f"✅ File pushed to: {remote_path}")

        # Step 4: Open Instagram post creation flow
        logger.info("📱 Opening new post screen...")
        insta_actions.new_post()
        time.sleep(1)

        # Step 5: Wait for and click "REEL" tab
        logger.info("🎬 Waiting for 'REEL' tab and clicking it...")
        reel_xpath = device.xpath("REEL")
        if not reel_xpath.wait(timeout=10):
            return False, "'REEL' tab not found"
        reel_xpath.click()
        logger.info("✅ 'REEL' tab clicked")
        time.sleep(2)

        # Step 6: Wait for "New reel" confirmation
        logger.info("🖼️ Waiting for 'New reel' screen...")
        new_reel_xpath = device.xpath("New reel")
        if not new_reel_xpath.wait(timeout=10):
            return False, "'New reel' screen not detected"
        logger.info("✅ 'New reel' screen confirmed")

        # Step 7: Select first video in folder (should only be one)
        logger.info("🎞️ Selecting first video")
        if not insta_actions.select_first_video():
            return False, "Failed to select first video"
        time.sleep(2)

        # Step 8: Wait for 'Add audio' confirmation
        logger.info("🕒 Waiting for 'Add audio' button to confirm editor loaded...")
        add_audio_el = device.xpath("Add audio")
        if not add_audio_el.wait(timeout=10):
            return False, "'Add audio' button not found"
        logger.info("✅ 'Add audio' screen confirmed")

        # Step 9: Add music
        logger.info("🎵 Adding sound to reel...")
        sound_adder = SoundAdder(device=device, app_package=app_package_name, insta_actions=insta_actions)
        success, message, song_info = sound_adder.add_music_to_reel()
        if not success:
            return False, f"Sound add failed: {message}"
        logger.info(f"✅ Sound added: {song_info.get('Full Reel Title')}")
        time.sleep(2)

        # Step 10: Generate and enter caption
        logger.info("✍️ Writing AI-generated caption...")
        caption = generate_and_enter_caption(device, app_package=app_package_name)
        if not caption:
            return False, "Caption entry failed"
        logger.info(f"✅ Caption entered: {caption}")
        time.sleep(2)

        # Step 10: Share the reel
        logger.info("📤 Sharing the reel...")
        if not insta_actions.click_by_xpath(xpath_config.reels_share_button):
            return False, "Failed to share reel"
        logger.info("✅ Reel shared successfully!")
        time.sleep(5)

        # Step 11: Update Airtable
        if record_id:
            fields_to_update = {
                'Posted?': True,
                'Caption': caption,  # from Step 10
                'Song': song_info.get('Full Reel Title') if song_info else None
            }

            airtable_success = airtable_client.update_record_fields(record_id, fields_to_update)

            if not airtable_success:
                logger.error("❌ Failed to update Airtable record")
        else:
            logger.error("❌ No valid Airtable record ID to update")


        # Step 12: Clean up device media
        album_path = f"/sdcard/Pictures/{account_name}"
        media_cleaner = MediaCleaner()
        media_cleaner.clean_posted_media(album_path)

        if airtable_success:
            return True, "✅ Reel posted and Airtable updated"
        else:
            return True, "⚠️ Reel posted, but Airtable update failed"

    except Exception as e:
        logger.error(f"💥 Exception during post_reel: {str(e)}", exc_info=True)
        return False, f"Error occurred: {str(e)}"

    finally:
        if remote_path and not airtable_success:
            try:
                os.remove(local_path)
                logger.info(f"🧹 Cleaned up local media: {local_path}")
            except Exception as e:
                logger.error(f"Failed to delete local media: {e}")


def main():
    logger.info("🚀 Starting full Instagram reel posting flow...")

    # Define constants
    PACKAGE_NAME = "com.instagram.androie"
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Connect device
    device = u2.connect()
    logger.info(f"📱 Connected to device: {device.serial}")

    # Initialize Airtable and start full reel posting flow
    airtable_client = AirtableClient()

    success, message = post_reel(
        app_package_name=PACKAGE_NAME,
        PROJECT_ROOT=PROJECT_ROOT,
        airtable_client=airtable_client
    )

    if success:
        logger.info(f"✅ Success: {message}")
    else:
        logger.error(f"❌ Failure: {message}")


if __name__ == "__main__":
    main()
