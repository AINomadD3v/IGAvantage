# post_reel.py
import os
import time
import uiautomator2 as u2
from typing import Tuple, Optional

from UploadBot.device_manager import MediaCleaner
from UploadBot.instagram_actions import InstagramInteractions, SoundAdder
from UploadBot.content_management import ContentManager
from Shared.logger_config import setup_logger
from Shared.airtable_manager import AirtableClient
from Shared.generate_caption import generate_and_enter_caption  
from Shared.popup_handler import PopupHandler
import threading

logger = setup_logger(__name__)

failure_triggered = threading.Event()

def handle_post_failure(record_id, airtable_client):
    global failure_triggered
    if not failure_triggered.is_set():
        logger.error("❌ Toast detected: 'Something went wrong'. Marking and aborting...")
        airtable_client.flag_failed_post_and_rotate(record_id)
        failure_triggered.set()

def post_reel(record: dict, PROJECT_ROOT: str, airtable_client: AirtableClient) -> Tuple[bool, Optional[str]]:
    logger.info("🎬 Starting post_reel process")

    device = u2.connect()
    global failure_triggered
    failure_triggered.clear()

    content_manager = ContentManager()
    fields = record["fields"]

    account_name = fields["username"]
    media_url = fields["media_url"]
    package_name = fields["package_name"]
    record_id = record["id"]

    insta_actions = InstagramInteractions(device, app_package=package_name, airtable_manager=airtable_client)
    popup_handler = PopupHandler(device)
    popup_handler.register_watchers()
    popup_handler.start_watcher_loop()

    remote_path = None
    airtable_success = False

    try:

        # Step 1: Launch the Instagram clone
        logger.info(f"🚀 Launching Instagram package: {package_name}")
        if not insta_actions.open_app():
            return False, f"Failed to launch app: {package_name}"

        # Step 2: Wait for Instagram home screen to confirm launch
        logger.info("🕵️ Waiting for Instagram home screen to confirm app launch...")
        expected_xpath = '//android.widget.Button[@content-desc="Instagram Home Feed"]'

        if not insta_actions.wait_for_app_ready(device, expected_xpath, retries=3):
            return False, "App launch failed or UI not ready"

        logger.info("✅ App launch confirmed by home feed button")

        if failure_triggered.is_set():
            return False, "Aborted due to 'Something went wrong' toast"


        # Step 3: Download media from Google Drive
        logger.info("☁️ Downloading media from Google Drive...")
        output_dir = os.path.join(PROJECT_ROOT, "temp")
        success, local_path, mime_type, _ = content_manager.download_drive_file(media_url, output_dir)
        if not success or not local_path:
            return False, "Download failed"
        logger.info(f"📂 Downloaded file to: {local_path}")

        # Step 4: Push media to device
        logger.info("📲 Pushing file to Android device...")
        push_success, remote_path = content_manager.push_media_to_device(local_path, account_name, "reel", device)
        if not push_success:
            return False, "Push to device failed"
        logger.info(f"✅ File pushed to: {remote_path}")

        # Step 5: Begin reel creation flow
        logger.info("📱 Opening new post screen...")
        insta_actions.new_post()
        time.sleep(1)

        if failure_triggered.is_set():
            return False, "Aborted due to 'Something went wrong' toast"

        # Step 6: Select "REEL" tab
        logger.info("🎬 Waiting for 'REEL' tab and clicking it...")
        reel_tab = device.xpath("REEL")
        if not reel_tab.wait(timeout=10):
            return False, "'REEL' tab not found"
        reel_tab.click()
        logger.info("✅ 'REEL' tab clicked")
        time.sleep(2)

        # Step 7: Confirm "New reel" screen loaded
        logger.info("🖼️ Waiting for 'New reel' screen...")
        new_reel_screen = device.xpath("New reel")
        if not new_reel_screen.wait(timeout=10):
            return False, "'New reel' screen not detected"
        logger.info("✅ 'New reel' screen confirmed")


        # Step 8-9: Retry loop for video selection + editor load
        max_video_select_retries = 3
        for attempt in range(1, max_video_select_retries + 1):
            logger.info(f"🎞️ Attempt {attempt}/{max_video_select_retries} to select first video and wait for editor...")

            if not insta_actions.select_first_video():
                logger.warning("⚠️ Video selection failed")
                time.sleep(2)
                continue

            time.sleep(2)
            add_audio_button = device.xpath("Add audio")
            if add_audio_button.wait(timeout=5):
                logger.info("✅ 'Add audio' screen confirmed")
                break
            else:
                logger.warning("⚠️ 'Add audio' button not found, retrying...")
                time.sleep(2)
        else:
            return False, "'Add audio' button not found after retries"


        # Step 10: Add music
        logger.info("🎵 Adding sound to reel...")
        sound_adder = SoundAdder(device=device, app_package=package_name, insta_actions=insta_actions)
        success, message, song_info = sound_adder.add_music_to_reel()
        if not success:
            return False, f"Sound add failed: {message}"
        logger.info(f"✅ Sound added: {song_info.get('Full Reel Title')}")
        time.sleep(2)

        if failure_triggered.is_set():
            return False, "Aborted due to 'Something went wrong' toast"

        device.watcher.run()  # force manual check


        # Step 11: Generate and enter caption
        logger.info("✍️ Writing AI-generated caption...")
        # Step 11: Generate and enter caption (with retry logic)
        max_caption_retries = 2
        caption = None

        for attempt in range(1, max_caption_retries + 1):
            logger.info(f"✍️ Attempting AI-generated caption entry (try {attempt}/{max_caption_retries})...")
            caption = generate_and_enter_caption(device, app_package=package_name)

            if caption:
                logger.info(f"✅ Caption entry succeeded on attempt {attempt}")
                break
            else:
                logger.warning(f"⚠️ Caption entry failed on attempt {attempt}")
                # Force-check for any interfering popups
                device.watcher.run()
                popup_handler.handle_all_popups()
                time.sleep(1.5)

        if not caption:
            return False, "Caption entry failed after retries"


        # Step 12: Share the reel
        logger.info("📤 Sharing the reel...")

        xpath = (
            "//*["
            "contains(@text, 'Next') or "
            "contains(@content-desc, 'Next') or "
            "contains(@content-desc, 'Share')"
            "]"
        )

        if not insta_actions.click_by_xpath(xpath):
            return False, "Failed to share reel"

        logger.info("✅ Reel shared successfully!")
        time.sleep(5)

        # Step 12.5: Confirm reel was actually posted
        logger.info("⏳ Waiting for posted reel to appear using caption...")
        if not insta_actions.wait_for_posted_caption(caption, username=account_name):
            return False, "Reel posted screen did not show expected caption"

        # Step 13: Update Airtable
        fields_to_update = {
            'Posted?': True,
            'Caption': caption,
            'Song': song_info.get('Full Reel Title') if song_info else None
        }
        airtable_success = airtable_client.update_record_fields(record_id, fields_to_update)
        if not airtable_success:
            logger.error("❌ Failed to update Airtable record")

        # Step 14: Clean up device media
        album_path = f"/sdcard/Pictures/{account_name}"
        media_cleaner = MediaCleaner()
        media_cleaner.clean_posted_media(album_path)

        # Step 15: Close the Instagram app
        logger.info("🛑 Closing Instagram app")
        device.app_stop(package_name)


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


def test_click_next_button(device):
    import time
    import logging

    logger = logging.getLogger(__name__)
    logger.info("🧪 Starting test: Click 'Next' button by visible text")

    try:
        xpath = (
            "//*[" 
            "contains(@text, 'Next') or "
            "contains(@content-desc, 'Next') or "
            "contains(@content-desc, 'Share')"
            "]"
        )

        selector = device.xpath(xpath)

        if not selector.wait(timeout=5):
            logger.error("❌ 'Next' button not found")
            return False

        el = selector.get()
        bounds = el.bounds
        center = el.center()

        logger.info(f"📍 'Next' button bounds: {bounds}, center: {center}")

        # ADB-level click
        device.click(*center)
        logger.info(f"✅ ADB click sent at: {center}")
        time.sleep(2)
        return True

    except Exception as e:
        logger.error(f"❌ Exception during Next button test: {e}", exc_info=True)
        return False

def main():
    model_map = {
        "1": "alexis",
        "2": "maddison"
    }

    print("Available models:")
    for k, v in model_map.items():
        print(f"{k}. {v}")

    selection = input("Select a model to process (enter number): ").strip()
    model = model_map.get(selection)

    if not model:
        logger.error("❌ Invalid selection. Exiting.")
        return

    logger.info(f"🚀 Starting Instagram reel posting flow for model: {model}")
    airtable_client = AirtableClient(model_name=model)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    device = u2.connect()
    logger.info(f"📱 Connected to device: {device.serial}")

    record = airtable_client.get_single_unposted_record()
    if not record:
        logger.error("❌ No unposted record found.")
        return

    success, message = post_reel(
        record=record,
        PROJECT_ROOT=PROJECT_ROOT,
        airtable_client=airtable_client
    )

    if success:
        logger.info(f"✅ Success: {message}")
    else:
        logger.error(f"❌ Failure: {message}")

if __name__ == "__main__":
    main()
