# UploadBot/post_reel.py

import datetime  # Added for potential timestamping
import os
import threading
import time
from typing import Optional, Tuple

import uiautomator2 as u2

# --- Shared Dependencies ---
from Shared.airtable_manager import AirtableClient

# Assuming this function will also be refactored to use InstagramInteractions later
from Shared.generate_caption import generate_and_enter_caption
from Shared.logger_config import setup_logger
from Shared.popup_handler import PopupHandler

# Assuming SoundAdder is moved to its own file:
from UploadBot.add_music import SoundAdder

# --- UploadBot Dependencies ---
from UploadBot.content_management import ContentManager  # Handles Drive/Local files
from UploadBot.device_manager import MediaCleaner  # Handles ADB file cleanup

# Import the main UI driver and the separated SoundAdder
from UploadBot.instagram_actions import InstagramInteractions

logger = setup_logger(__name__)

# --- Global Event for Critical Failures (e.g., from watchers) ---
# Consider moving this logic into a more robust error handling system if needed
failure_triggered = threading.Event()


def handle_post_failure(record_id, airtable_client):
    """Callback for critical failures detected by watchers."""
    global failure_triggered
    if not failure_triggered.is_set():
        logger.error(
            "❌ Critical Failure Detected (e.g., Toast): 'Something went wrong'. Marking record and aborting..."
        )
        # Ensure airtable_client has this method or adapt as needed
        if hasattr(airtable_client, "flag_failed_post_and_rotate"):
            airtable_client.flag_failed_post_and_rotate(record_id)
        else:
            logger.warning(
                "Airtable client missing 'flag_failed_post_and_rotate' method."
            )
            # Fallback to generic update?
            airtable_client.update_record_fields(
                record_id, {"Status": "Error - Critical Failure"}
            )

        failure_triggered.set()  # Signal other parts of the script to stop


# --- Main Reel Posting Workflow ---


def post_reel(
    record: dict, project_root: str, airtable_client: AirtableClient
) -> Tuple[bool, Optional[str]]:
    """
    Orchestrates the entire process of posting an Instagram Reel.

    Args:
        record (dict): Airtable record containing post details (username, media_url, package_name, id).
        project_root (str): The root path of the project for finding temporary directories.
        airtable_client (AirtableClient): Instance for updating Airtable records.

    Returns:
        Tuple[bool, Optional[str]]: (Success status, Message)
    """
    record_id = record.get("id", "N/A")
    logger.info(f"🎬 Starting post_reel process for record ID: {record_id}")

    insta_actions: Optional[InstagramInteractions] = (
        None  # Initialize for finally block
    )
    popup_handler: Optional[PopupHandler] = None
    local_path: Optional[str] = None  # Ensure local_path is defined for finally block
    device: Optional[u2.Device] = None  # Initialize device for finally block

    global failure_triggered
    failure_triggered.clear()  # Reset failure flag for this run

    try:
        # --- Setup ---
        # Connect to device for this specific task run
        # Note: device_id should ideally come from the record for multi-device setups
        device_id_from_record = record.get("fields", {}).get(
            "device_id"
        )  # Assuming it might be here
        logger.info(f"🔌 Connecting to device: {device_id_from_record or 'default'}")
        device = u2.connect(
            device_id_from_record
        )  # Connect to specific or default device
        # Verify connection instead of using .alive
        try:
            info = device.info  # Attempt a basic interaction
            logger.info(
                f"✅ Connected to {device.serial} - Product: {info.get('productName', 'N/A')}"
            )
        except Exception as conn_err:
            raise ConnectionError(
                f"Failed to connect or communicate with device {device_id_from_record or 'default'}: {conn_err}"
            )

        content_manager = ContentManager()  # Handles file download/push
        media_cleaner = MediaCleaner()  # Handles device file cleanup via ADB

        fields = record.get("fields", {})
        account_name = fields.get("username")
        media_url = fields.get("media_url")
        package_name = fields.get("package_name")
        # record_id already fetched

        if not all([account_name, media_url, package_name, record_id]):
            missing = [
                k
                for k, v in {
                    "username": account_name,
                    "media_url": media_url,
                    "package_name": package_name,
                    "id": record_id,
                }.items()
                if not v
            ]
            # Ensure record_id is str before returning error message
            record_id_str = str(record_id) if record_id else "N/A"
            return (
                False,
                f"Missing required record fields for {record_id_str}: {missing}",
            )

        # Instantiate the core UI interaction class
        insta_actions = InstagramInteractions(
            device,
            app_package=package_name,
            airtable_manager=airtable_client,  # Pass airtable_client if needed by insta_actions
        )

        # Setup Popup Handling
        # Pass device object; ensure PopupHandler doesn't rely on deleted UIHelper methods
        popup_handler = PopupHandler(device)
        popup_handler.register_watchers()
        # Note: start_watcher_loop starts a daemon thread. Stopping is handled in finally.
        popup_handler.start_watcher_loop()

        # --- Workflow Steps ---

        # Step 1 & 2: Launch App and Wait for Home Screen
        logger.info(f"🚀 Launching/Focusing Instagram app: {package_name}")
        # Use the readiness_xpath feature of the enhanced open_app
        home_ready_xpath = (
            insta_actions.xpath_config.home_feed_ready_identifier
        )  # Ensure defined in config
        if not insta_actions.open_app(
            readiness_xpath=home_ready_xpath, readiness_timeout=30, max_retries=3
        ):
            # open_app now includes waiting for readiness
            return False, f"Failed to launch or ready app: {package_name}"
        logger.info("✅ App launch confirmed and home screen ready.")

        # Check if a critical failure was detected during launch/wait
        if failure_triggered.is_set():
            return False, "Aborted: Critical failure detected during app launch."

        # Step 3: Download media from Google Drive
        logger.info(f"☁️ Downloading media from Google Drive URL: {media_url}")
        # Define temp dir relative to project root
        output_dir = os.path.join(project_root, "temp_media")  # Use consistent name
        success, local_path, mime_type, _ = content_manager.download_drive_file(
            media_url, output_dir
        )
        if not success or not local_path:
            return False, f"Media download failed from URL: {media_url}"
        logger.info(f"📂 Media downloaded locally to: {local_path}")

        # Step 4: Push media to device
        logger.info(f"📲 Pushing file to Android device ({device.serial})...")
        # Pass device object to push method
        push_success, remote_path = content_manager.push_media_to_device(
            local_path, account_name, "reel", device
        )
        if not push_success or not remote_path:
            return False, f"Pushing media to device failed for {local_path}"
        logger.info(f"✅ File pushed to device path: {remote_path}")

        # Step 5: Begin reel creation flow
        logger.info("📱 Navigating to new post screen...")
        if not insta_actions.new_post():  # new_post now returns bool
            return False, "Failed to click the 'New Post' button."
        # Replace sleep with wait for the next screen element (e.g., REEL tab)
        reel_tab_xpath = (
            insta_actions.xpath_config.reel_creation_tab_general
        )  # Ensure defined in config
        if not insta_actions.wait_for_element_appear(reel_tab_xpath, timeout=10):
            return (
                False,
                "Gallery/Camera screen with REEL tab did not appear after clicking New Post.",
            )
        logger.info("✅ New post screen loaded.")

        if failure_triggered.is_set():
            return False, "Aborted: Critical failure detected."

        # Step 6: Select "REEL" tab
        logger.info("🎬 Selecting 'REEL' tab...")
        if not insta_actions.click_by_xpath(reel_tab_xpath, timeout=5):
            return False, "'REEL' tab not found or click failed."
        logger.info("✅ 'REEL' tab clicked.")
        # Replace sleep with wait for "New reel" screen confirmation element
        new_reel_indicator_xpath = (
            insta_actions.xpath_config.new_reel_screen_identifier_general
        )  # Ensure defined in config
        if not insta_actions.wait_for_element_appear(
            new_reel_indicator_xpath, timeout=10
        ):
            # Try clicking REEL tab again? Sometimes a double tap is needed.
            logger.warning(
                "First REEL tab click might not have registered, trying again..."
            )
            time.sleep(0.5)
            if not insta_actions.click_by_xpath(reel_tab_xpath, timeout=3):
                logger.error("Second attempt to click REEL tab failed.")
                return False, "'REEL' tab click failed."
            if not insta_actions.wait_for_element_appear(
                new_reel_indicator_xpath, timeout=10
            ):
                return (
                    False,
                    "'New reel' screen indicator not detected after clicking REEL tab.",
                )

        # Step 7: Confirm "New reel" screen loaded (already done by wait above)
        logger.info("✅ 'New reel' screen confirmed.")

        # Step 8-9: Retry loop for video selection + wait for editor screen
        max_video_select_retries = 3
        editor_ready = False
        add_audio_btn_xpath = (
            insta_actions.xpath_config.add_audio_text_or_desc_general
        )  # Ensure defined
        for attempt in range(1, max_video_select_retries + 1):
            logger.info(
                f"🎞️ Attempt {attempt}/{max_video_select_retries} to select first video..."
            )
            if not insta_actions.select_first_video(timeout=15):  # Increased timeout
                logger.warning(f"⚠️ Video selection failed on attempt {attempt}.")
                time.sleep(1)
                # Optional: Refresh gallery? Swipe down slightly?
                # insta_actions.swipe_screen(direction="down", intensity=0.2)
                continue  # Try selecting again

            logger.info(
                "✅ Video selected. Waiting for editor screen ('Add audio' button)..."
            )
            # Wait for the 'Add audio' button as indicator that editor loaded
            if insta_actions.wait_for_element_appear(
                add_audio_btn_xpath, timeout=15
            ):  # Increased timeout
                logger.info("✅ Editor screen confirmed ('Add audio' button found).")
                editor_ready = True
                break  # Exit loop on success
            else:
                logger.warning(
                    f"⚠️ Editor screen not detected after selecting video (attempt {attempt}). Retrying selection."
                )
                # Press back to hopefully return to gallery before retrying
                insta_actions.navigate_back_from_reel()  # Use the back method
                time.sleep(1)  # Short delay before retrying video selection

        if not editor_ready:
            return (
                False,
                "Failed to select video and reach editor screen after retries.",
            )

        # Step 10: Add music
        logger.info("🎵 Adding sound to reel...")
        # Instantiate SoundAdder using the insta_actions instance
        sound_adder = SoundAdder(
            device=insta_actions.device,  # Pass device if needed
            app_package=package_name,
            insta_actions=insta_actions,  # Pass the main interactions object
        )
        success, message, song_info = (
            sound_adder.add_music_to_reel()
        )  # Call method on SoundAdder
        if not success:
            # Attempt to recover by going back if possible
            insta_actions.navigate_back_from_reel()
            return False, f"Sound add failed: {message}"
        logger.info(
            f"✅ Sound added: {song_info.get('Full Reel Title', 'N/A') if song_info else 'N/A'}"
        )
        # Replace sleep with wait for the next screen (caption input)
        caption_field_xpath = (
            insta_actions.xpath_config.reel_caption_text_view
        )  # Use correct XPath from config
        if not insta_actions.wait_for_element_appear(caption_field_xpath, timeout=15):
            return (
                False,
                "Caption screen did not appear after adding music/clicking next.",
            )
        logger.info("✅ Caption screen loaded.")

        if failure_triggered.is_set():
            return False, "Aborted: Critical failure detected."

        # Step 11: Generate and enter caption (with retry logic)
        # NOTE: generate_and_enter_caption itself needs refactoring to use insta_actions
        logger.info("✍️ Generating and entering AI-generated caption...")
        max_caption_retries = 2
        caption = None
        for attempt in range(1, max_caption_retries + 1):
            logger.info(f"Attempt {attempt}/{max_caption_retries} for caption...")
            # Pass device object for now, until generate_and_enter_caption is refactored
            # TODO: Refactor generate_and_enter_caption to accept insta_actions instance
            caption = generate_and_enter_caption(device, app_package=package_name)
            if caption:
                logger.info(f"✅ Caption entry succeeded on attempt {attempt}")
                break
            else:
                logger.warning(
                    f"⚠️ Caption entry failed on attempt {attempt}. Checking popups..."
                )
                # Force-check for any interfering popups
                if popup_handler:
                    if hasattr(
                        popup_handler, "handle_all_popups"
                    ):  # Check if method exists
                        popup_handler.handle_all_popups()
                    else:
                        logger.warning(
                            "PopupHandler does not have 'handle_all_popups' method."
                        )
                        device.watcher.run()  # Manual trigger as fallback
                time.sleep(1.5)  # Keep short sleep after popup handling

        if not caption:
            # Attempt recovery before failing
            insta_actions.navigate_back_from_reel()
            return False, "Caption entry failed after retries."
        logger.info(
            "✅ Caption entered and verified."
        )  # Assuming generate_and_enter_caption includes verification

        # Step 12: Share the reel
        logger.info("📤 Sharing the reel...")
        share_button_xpath = (
            insta_actions.xpath_config.final_share_or_next_button
        )  # Ensure defined
        if not insta_actions.click_by_xpath(share_button_xpath, timeout=10):
            # Attempt recovery
            insta_actions.navigate_back_from_reel()
            return False, "Failed to click Share/Next button."
        logger.info("✅ Share/Next button clicked.")

        # Step 12.5: Confirm reel was actually posted (replace sleep)
        logger.info("⏳ Verifying post by waiting for caption/profile elements...")
        if not insta_actions.wait_for_posted_caption(
            caption, username=account_name, timeout=180
        ):  # Increased timeout
            logger.warning(
                "⚠️ Reel post confirmation failed (caption/profile elements not found). Post may still be uploading."
            )
            # Decide how to handle this: fail, or proceed but flag uncertainty?
            # For now, treat as failure for simplicity:
            return (
                False,
                "Reel posted screen did not show expected elements after sharing.",
            )
        logger.info("✅ Reel post confirmed on screen.")

        # Step 13: Update Airtable
        logger.info(f"💾 Updating Airtable record {record_id}...")
        fields_to_update = {
            "Posted?": True,
            "Caption": caption,
            "Song": song_info.get("Full Reel Title") if song_info else None,
            "Post Timestamp": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),  # Add timestamp
            "Status": "Posted",  # Update status field
        }
        # Ensure record_id is a string before calling update
        if isinstance(record_id, str):
            airtable_success = airtable_client.update_record_fields(
                record_id, fields_to_update
            )
            if not airtable_success:
                logger.error(f"❌ Failed to update Airtable record ID: {record_id}")
            else:
                logger.info(f"✅ Airtable record {record_id} updated.")
        else:
            logger.error(
                f"❌ Invalid record_id type ({type(record_id)}) for Airtable update."
            )
            airtable_success = False  # Mark as failed if ID is invalid

        # Step 14: Clean up device media (using MediaCleaner)
        logger.info("🧹 Cleaning up media from device...")
        # Construct path based on how push_media_to_device organizes it
        album_path = (
            f"/sdcard/Pictures/{account_name}"  # Ensure this matches push logic
        )
        media_cleaner.clean_posted_media(
            album_path
        )  # clean_posted_media logs its own success/failure

        # Step 15: Close App (moved to finally block)

        # --- Final Result ---
        if airtable_success:
            return True, "✅ Reel posted and Airtable updated successfully."
        else:
            # Post succeeded, but Airtable failed
            return True, "⚠️ Reel posted, but Airtable update failed."

    except ConnectionError as e:
        logger.error(
            f"💥 Connection Error during post_reel for {record_id}: {e}", exc_info=True
        )
        return False, f"Connection Error: {e}"
    except Exception as e:
        logger.error(
            f"💥 Unhandled Exception during post_reel for {record_id}: {e}",
            exc_info=True,
        )
        return False, f"Runtime Error: {e}"

    finally:
        # --- Cleanup ---
        logger.info(f"--- Running post_reel cleanup for {record_id} ---")
        # Stop popup watcher thread
        if device and hasattr(device, "watcher"):
            try:
                logger.info("🛑 Stopping device watcher...")
                device.watcher.stop()
                # Optional: Remove all watchers if needed for clean state
                # device.watcher.remove()
            except Exception as e_watch:
                logger.error(f"Error stopping device watcher: {e_watch}")

        # Ensure app is closed
        if insta_actions:
            logger.info(f"🚪 Ensuring app {insta_actions.app_package} is closed...")
            insta_actions.close_app()

        # Clean up downloaded local media file
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"🧹 Cleaned up local media file: {local_path}")
            except OSError as e_clean:
                logger.error(
                    f"Failed to delete local media file {local_path}: {e_clean}"
                )
        logger.info(f"--- Finished post_reel for {record_id} ---")


def main():
    """Main function to run the reel posting process based on user input."""
    # --- Model Selection ---
    model_map = {"1": "alexis", "2": "maddison"}  # Consider loading from config
    print("Available models:")
    for k, v in model_map.items():
        print(f"{k}. {v}")
    selection = input("Select a model to process (enter number): ").strip()
    model_name = model_map.get(selection)
    if not model_name:
        logger.error("❌ Invalid model selection. Exiting.")
        return

    # --- Number of Records ---
    num_to_process_str = input(
        f"How many records for '{model_name}' to process today? "
    ).strip()
    try:
        count = int(num_to_process_str)
        if count <= 0:
            raise ValueError("Count must be positive.")
    except ValueError:
        logger.error(f"❌ Invalid number '{num_to_process_str}'. Exiting.")
        return

    # --- Initialization ---
    # Corrected: Use table_key based on model name pattern
    airtable_table_key = f"content_{model_name}"
    airtable_client = AirtableClient(table_key=airtable_table_key)
    # Calculate project root dynamically
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger.info(f"Project Root determined as: {project_root}")

    # --- Fetch Records ---
    logger.info(f"Fetching up to {count} unposted records for '{model_name}'...")
    records = airtable_client.get_unposted_records_for_today(max_count=count)
    if not records:
        logger.info("✅ No scheduled records found for today.")
        return
    logger.info(f"Found {len(records)} records to process.")

    # --- Process Records ---
    for i, record in enumerate(records, 1):
        record_id = record.get("id", "N/A")
        username = record.get("fields", {}).get("username", "N/A")
        logger.info(
            f"--- Processing record {i}/{len(records)} (ID: {record_id}, User: {username}) ---"
        )

        success, message = post_reel(
            record=record,
            project_root=project_root,
            airtable_client=airtable_client,  # Pass the initialized client
        )

        if success:
            logger.info(f"✅ Result for {record_id}: {message}")
        else:
            logger.error(f"❌ Failure for {record_id}: {message}")
            # Update Airtable to mark failure
            # Ensure record_id is string before calling
            record_id_str = record.get("id")
            if isinstance(record_id_str, str):
                # Use the specific method if available, otherwise generic update
                if hasattr(airtable_client, "mark_something_went_wrong_and_rotate"):
                    airtable_client.mark_something_went_wrong_and_rotate(record_id_str)
                else:
                    logger.warning(
                        "Airtable client missing 'mark_something_went_wrong_and_rotate' method."
                    )
                    airtable_client.update_record_fields(
                        record_id_str,
                        {"Status": "Error - Post Failed", "Notes": message},
                    )
            else:
                logger.error(
                    f"Cannot mark failure for record with invalid ID: {record_id_str}"
                )

            # Ask user whether to continue after a failure
            user_input = (
                input("An error occurred. Continue with the next record? (y/n): ")
                .strip()
                .lower()
            )
            if user_input != "y":
                logger.info("🛑 Exiting by user request after failure.")
                break  # Exit the loop

    logger.info("--- All scheduled records processed ---")


if __name__ == "__main__":
    main()
