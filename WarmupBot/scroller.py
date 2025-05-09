# InterActions/scroller.py

import hashlib
import random
import time
from typing import Optional, Tuple

import uiautomator2 as u2  # Keep for type hints if needed

from Shared.airtable_manager import AirtableClient  # Keep for main function logic

# Import the config loader functions
from Shared.config_loader import get_scroller_config, load_yaml_config

# --- Core Dependencies ---
from Shared.logger_config import setup_logger
from Shared.popup_handler import PopupHandler  # Keep for popup handling
from Shared.stealth_typing import StealthTyper  # Keep for keyword search typing

# --- Import the main Instagram UI driver ---
# Adjust path if InstagramInteractions moves to Shared later
from UploadBot.instagram_actions import InstagramInteractions

logger = setup_logger(name="Scroller")  # Use the specific logger name

# --- Load Configuration ---
# Load the entire config once at the start
load_yaml_config()  # Ensure the main config file is loaded
SCROLLER_CONFIG = get_scroller_config()  # Get the specific section for the scroller
if not SCROLLER_CONFIG:
    logger.error(
        "Scroller configuration not found in config.yaml! Using default values."
    )

# Extract keywords from the loaded config
KEYWORDS = SCROLLER_CONFIG.get("keywords", ["model"])  # Provide a default keyword list
if not KEYWORDS:
    logger.warning("No keywords found in scroller config, using default: ['model']")
    KEYWORDS = ["model"]


# --- Utility Functions ---
def random_delay(label: str):
    """Sleeps for a random duration based on the label from SCROLLER_CONFIG."""
    delays_config = SCROLLER_CONFIG.get("delays", {})
    lo, hi = delays_config.get(label, delays_config.get("default", [1.0, 2.0]))
    try:
        lo_f = float(lo)
        hi_f = float(hi)
        if hi_f < lo_f:
            hi_f, lo_f = lo_f, hi_f  # Swap if order is wrong
        t = random.uniform(lo_f, hi_f)
        logger.debug(f"Sleeping {t:.2f}s ({label})")
        time.sleep(t)
    except (TypeError, ValueError) as e:
        logger.error(
            f"Invalid delay config for '{label}': {lo}, {hi}. Using default 1s. Error: {e}"
        )
        time.sleep(1.0)


# --- Core Logic Functions (Refactored to use InstagramInteractions and Centralized XPaths) ---


def extract_search_page_reels(insta_actions: InstagramInteractions) -> list[dict]:
    """
    Extracts reel information specifically from the search/explore results page.
    Uses insta_actions for device access and XPath configuration.
    """
    reels = []
    seen_this_screen = set()
    device = insta_actions.device
    xpath_config = insta_actions.xpath_config  # Get XPath config

    try:
        # Find potential containers using XPath from config
        containers = device.xpath(xpath_config.search_layout_container_frame).all()
        # Optional: Further filter containers if a more specific pattern exists, e.g., by resource-id
        # containers = [c for c in containers if re.match(xpath_config.search_layout_container_rid_pattern, c.info.get("resourceID", ""))]
        logger.info(
            f"Found {len(containers)} potential layout containers on search page"
        )

        for container in containers:
            try:
                # Skip image posts with 'photos by'
                # Search relative to container
                bad_btns = container.xpath(xpath_config.search_image_post_button).all()
                is_image_post = False
                for btn in bad_btns:
                    btn_info = btn.info
                    btn_rid = btn_info.get("resourceID", "")
                    btn_desc = btn_info.get("contentDescription", "")
                    # TODO: Move "image_button", "photos by" literals to config if needed
                    if "image_button" in btn_rid and "photos by" in btn_desc.lower():
                        logger.debug(
                            "🧨 Skipping image post (found 'photos by' button)"
                        )
                        is_image_post = True
                        break
                if is_image_post:
                    continue

                # Look for reel ImageViews inside this container (relative search)
                ivs = container.xpath(xpath_config.search_reel_imageview).all()
                for iv in ivs:
                    iv_info = iv.info
                    desc = iv_info.get("contentDescription", "").strip()
                    bounds = iv_info.get("bounds")  # Get bounds dict

                    bounds_str = ""
                    if bounds:
                        bounds_str = f"[{bounds.get('left', 0)},{bounds.get('top', 0)}][{bounds.get('right', 0)},{bounds.get('bottom', 0)}]"

                    if not desc or not bounds_str:
                        continue
                    # TODO: Move "Reel by" literal to config if needed
                    if "Reel by" not in desc:
                        continue

                    screen_key = desc
                    if screen_key in seen_this_screen:
                        continue
                    seen_this_screen.add(screen_key)

                    key = hashlib.sha1(screen_key.encode("utf-8")).hexdigest()
                    username = "unknown"
                    try:
                        username_part = desc.split("by", 1)[1]
                        username = username_part.split("at", 1)[0].strip()
                    except IndexError:
                        logger.warning(f"Could not parse username from desc: {desc}")

                    post = {
                        "id": key,
                        "short_id": key[:7],
                        "username": username,
                        "type": "REEL",
                        "desc": desc,
                        "bounds": bounds_str,
                    }
                    logger.info(
                        f"[{post['short_id']}] ✅ Extracted Reel | @{username} | bounds={bounds_str}"
                    )
                    reels.append(post)

            except Exception as e:
                logger.warning(f"⚠️ Failed to parse a container: {e}", exc_info=False)
                continue

    except Exception as outer_e:
        logger.error(
            f"💥 Error extracting reels from search page: {outer_e}", exc_info=True
        )

    return reels


def process_reel(
    insta_actions: InstagramInteractions,
    reel_post: dict,
    stop_callback: Optional[callable] = None,
) -> Optional[dict]:
    """
    Processes a single reel: watches, interacts (like/comment), extracts data.
    Uses methods from the insta_actions instance and configuration from SCROLLER_CONFIG.
    Uses XPaths from insta_actions.xpath_config.

    Args:
        insta_actions: The initialized InstagramInteractions instance.
        reel_post: Dictionary containing reel info ('desc' is used for tapping).
        stop_callback: Optional function to call if a critical error occurs.

    Returns:
        Optional dictionary with extracted data and interaction results, or None on failure.
    """
    # Get config values safely with defaults
    watch_time_range = SCROLLER_CONFIG.get("watch_time_range", [3.0, 6.0])
    like_probability = SCROLLER_CONFIG.get("like_probability", 0.5)
    comment_probability = SCROLLER_CONFIG.get("comment_probability", 0.1)

    full_watch_time = random.uniform(*watch_time_range)
    like_delay = random.uniform(1.2, max(1.3, full_watch_time - 0.5))
    interaction_times = sorted(
        random.sample(
            [random.uniform(1.0, max(1.1, full_watch_time - 0.2)) for _ in range(3)],
            k=min(2, 3),
        )
    )

    logger.info(
        f"⏱️ Watching reel [{reel_post.get('short_id', 'N/A')}] for {full_watch_time:.2f}s (like at ~{like_delay:.2f}s)"
    )
    start_time = time.time()
    end_time = start_time + full_watch_time
    liked = False
    commented = False
    should_comment = random.random() < comment_probability
    next_interaction_time = interaction_times.pop(0) if interaction_times else None

    # --- Tap the reel to open it ---
    # Use the XPath template from config
    reel_tap_xpath = insta_actions.xpath_config.search_reel_imageview_template.format(
        reel_post["desc"]
    )
    if not insta_actions.click_by_xpath(reel_tap_xpath, timeout=5):
        logger.error(
            f"❌ Failed to tap/open reel [{reel_post.get('short_id', 'N/A')}] using XPath: {reel_tap_xpath}"
        )
        return None

    random_delay("after_post_tap")

    # --- Extract reel metadata ---
    # Use XPaths from config
    username = insta_actions.get_element_attribute(
        insta_actions.xpath_config.reel_profile_picture_desc_contains,
        "contentDescription",
        timeout=2,
    )
    if username and "Profile picture of" in username:
        username = username.replace("Profile picture of", "").strip()

    caption = insta_actions.get_element_text(
        insta_actions.xpath_config.reel_caption_container,  # Use the defined property
        timeout=2,
    )

    likes = insta_actions.get_element_attribute(
        insta_actions.xpath_config.reel_likes_button_desc,
        "contentDescription",
        timeout=2,
    )

    reshares = insta_actions.get_element_attribute(
        insta_actions.xpath_config.reel_reshare_button_desc,
        "contentDescription",
        timeout=2,
    )

    sound = insta_actions.get_element_attribute(
        insta_actions.xpath_config.reel_audio_link_desc_contains,
        "contentDescription",
        timeout=2,
    )

    follow_btn_exists = insta_actions.element_exists(
        insta_actions.xpath_config.reel_follow_button_text
    )

    if sound and "• Original audio" in sound:
        sound = sound.split("• Original audio")[0].strip()
    if likes and "likes" in likes.lower():
        likes = likes.lower().replace("view likes", "").strip()

    logger.info(
        f"[REEL DATA] user={username}, likes={likes}, reshares={reshares}, caption_preview={caption[:50] if caption else 'N/A'}..., sound={sound}, follow_visible={follow_btn_exists}"
    )

    # --- Central timing loop for interactions ---
    while time.time() < end_time:
        elapsed = time.time() - start_time

        if next_interaction_time and elapsed >= next_interaction_time:
            insta_actions.perform_light_interaction()
            next_interaction_time = (
                interaction_times.pop(0) if interaction_times else None
            )

        if not liked and elapsed >= like_delay:
            if random.random() < like_probability:
                liked = (
                    insta_actions.like_current_post_or_reel()
                )  # This method uses config XPaths internally
                if liked:
                    logger.info("❤️ Like successful.")
                    random_delay("after_like")
                else:
                    logger.warning("❌ Like attempt failed or blocked.")
                    if stop_callback:
                        stop_callback()
            else:
                liked = False
                like_delay = float("inf")

        if not commented and should_comment and elapsed >= full_watch_time * 0.6:
            commented = (
                insta_actions.simulate_open_close_comments()
            )  # This method uses config XPaths internally
            if commented:
                random_delay("after_comment")
            should_comment = False

        time.sleep(0.2)

    # --- Fallback Like ---
    if not liked and random.random() < like_probability:
        logger.info("📌 Fallback: Attempting like near end of watch window.")
        liked = insta_actions.like_current_post_or_reel()

    # --- Exit Reel View ---
    # Use the specific XPath from config for verification
    like_unlike_xpath_for_verify = (
        insta_actions.xpath_config.reel_like_or_unlike_button_desc
    )
    insta_actions.navigate_back_from_reel(  # Renamed from navigate_back_from_reel
        verify_element_disappears=like_unlike_xpath_for_verify
    )
    random_delay("back_delay")

    return {
        "username": username,
        "likes_text": likes,
        "reshares_text": reshares,
        "caption": caption,
        "sound": sound,
        "follow_visible": follow_btn_exists,
        "liked": liked,
        "commented": commented,
    }


def perform_keyword_search(insta_actions: InstagramInteractions, keyword: str) -> bool:
    """
    Performs a keyword search on the Explore page.
    Uses insta_actions for UI interactions and config XPaths. Uses StealthTyper for input.
    """
    logger.info(f"🔍 Performing keyword search: {keyword}")
    xpath_config = insta_actions.xpath_config  # Get config object

    # Use XPaths from config
    search_xpath = xpath_config.explore_search_bar_rid
    results_recycler_xpath = xpath_config.search_results_recycler_view

    typer = StealthTyper(device_id=insta_actions.device.serial)

    try:
        if not insta_actions.wait_for_element_appear(search_xpath, timeout=10):
            logger.error("❌ Search bar not found on Explore page.")
            return False
        if not insta_actions.click_by_xpath(search_xpath, timeout=2):
            logger.error("❌ Failed to click search bar.")
            return False
        logger.info("✅ Search bar tapped.")
        time.sleep(random.uniform(0.8, 1.2))

        typer.type_text(keyword)
        time.sleep(random.uniform(0.3, 0.6))
        typer.press_enter()
        logger.info("⏎ Enter pressed to start search.")
        time.sleep(random.uniform(2.5, 4.0))

        logger.info("↕️ Scrolling down slightly to reveal posts...")
        insta_actions.scroll_up_humanlike()
        time.sleep(random.uniform(1.0, 1.5))

        logger.info("🧭 Looking for posts section / results...")
        if not insta_actions.wait_for_element_appear(
            results_recycler_xpath, timeout=10
        ):
            logger.error(
                "❌ Search results recycler view not found after search. Can't continue."
            )
            return False

        logger.info("✅ Search results loaded.")
        return True

    except Exception as e:
        logger.error(f"❌ Failed during keyword search flow: {e}", exc_info=True)
        return False


def run_warmup_session(insta_actions: InstagramInteractions):
    """
    Runs the main warmup/scrolling session logic. Uses insta_actions instance and SCROLLER_CONFIG.

    Args:
        insta_actions: The initialized InstagramInteractions instance.
    """
    # Get config values safely
    max_runtime_seconds = SCROLLER_CONFIG.get("max_runtime_seconds", 180)
    max_scrolls = SCROLLER_CONFIG.get("max_scrolls", 50)
    percent_reels_to_watch = SCROLLER_CONFIG.get("percent_reels_to_watch", 0.7)
    idle_after_actions_range = SCROLLER_CONFIG.get("idle_after_actions", [3, 6])
    idle_duration_range = SCROLLER_CONFIG.get("idle_duration_range", [2, 6])

    device = insta_actions.device
    package_name = insta_actions.app_package

    # --- Setup Popup Handler ---
    popup_handler = PopupHandler(device)
    # TODO: Set context for popup_handler if callbacks need it
    # popup_handler.set_context(...)
    popup_handler.register_watchers()
    popup_handler.start_watcher_loop()

    logger.info(f"📱 Ensuring Instagram app is open and ready: {package_name}")
    # Use XPath from config for readiness check
    explore_tab_xpath = insta_actions.xpath_config.explore_tab_desc
    if not insta_actions.open_app(
        readiness_xpath=explore_tab_xpath, readiness_timeout=30
    ):
        logger.error("❌ Failed to launch/ready Instagram app. Exiting warmup session.")
        if popup_handler:
            popup_handler.stop_watcher_loop()
        return

    logger.info("✅ Instagram app is ready.")

    seen_hashes = set()
    all_reels_processed_info = []

    # --- Navigate to Explore ---
    if not insta_actions.navigate_to_explore(
        timeout=15
    ):  # This method uses config XPaths internally now
        logger.error("🚫 Failed to navigate to Explore page. Exiting.")
        if popup_handler:
            popup_handler.stop_watcher_loop()
        insta_actions.close_app()
        return

    # --- Perform Keyword Search ---
    keyword = random.choice(KEYWORDS)  # Use keywords loaded from config
    logger.info(f"🎯 Chosen keyword for search: '{keyword}'")
    if not perform_keyword_search(
        insta_actions, keyword
    ):  # This method uses config XPaths internally now
        logger.error("🚫 Keyword search failed. Exiting.")
        if popup_handler:
            popup_handler.stop_watcher_loop()
        insta_actions.close_app()
        return

    # --- Main Scrolling Loop ---
    start_time = time.time()
    actions_since_idle = 0
    idle_min, idle_max = map(int, idle_after_actions_range)
    next_idle_at = random.randint(idle_min, idle_max)

    for i in range(max_scrolls):
        elapsed = time.time() - start_time
        if elapsed > max_runtime_seconds:
            logger.info(
                f"⏰ Runtime limit ({max_runtime_seconds}s) exceeded. Ending session."
            )
            break

        logger.info(f"--- Scroll iteration {i + 1}/{max_scrolls} ---")

        # extract_search_page_reels still uses hardcoded XPaths internally for now
        all_detected_this_screen = extract_search_page_reels(insta_actions)
        new_reels_on_screen = [
            r for r in all_detected_this_screen if r["id"] not in seen_hashes
        ]

        if not new_reels_on_screen:
            logger.info(f"🔁 No new reels found on screen, scrolling up...")
            random_delay("before_scroll")
            insta_actions.scroll_up_humanlike()
            time.sleep(random.uniform(0.5, 1.5))
            continue

        logger.info(f"Found {len(new_reels_on_screen)} new reels on screen.")

        num_to_process = max(1, int(len(new_reels_on_screen) * percent_reels_to_watch))
        reels_to_process = random.sample(new_reels_on_screen, num_to_process)
        logger.info(f"Processing {len(reels_to_process)} of them.")

        for reel_data in reels_to_process:
            if time.time() - start_time > max_runtime_seconds:
                logger.info("⏰ Runtime limit reached during reel processing.")
                break

            logger.info(
                f"🎬 Processing reel [{reel_data['short_id']}] by @{reel_data['username']}"
            )
            # process_reel now uses config XPaths internally where applicable
            processing_result = process_reel(
                insta_actions=insta_actions, reel_post=reel_data, stop_callback=None
            )
            seen_hashes.add(reel_data["id"])
            if processing_result:
                processing_result["original_desc"] = reel_data["desc"]
                processing_result["original_bounds"] = reel_data["bounds"]
                all_reels_processed_info.append(processing_result)

            actions_since_idle += 1
            if actions_since_idle >= next_idle_at:
                idle_time = random.uniform(*idle_duration_range)
                logger.info(f"😴 Idle break for {idle_time:.2f}s")
                time.sleep(idle_time)
                actions_since_idle = 0
                next_idle_at = random.randint(idle_min, idle_max)

        if time.time() - start_time > max_runtime_seconds:
            logger.info("⏰ Runtime limit reached after processing reels.")
            break

        random_delay("before_scroll")
        insta_actions.scroll_up_humanlike()
        random_delay("between_scrolls")

    # --- Session End ---
    duration = time.time() - start_time
    logger.info(f"🕒 Warmup session finished. Runtime: {duration:.2f}s")
    logger.info(f"✅ Total unique reels processed: {len(all_reels_processed_info)}")

    if popup_handler:
        logger.info("🛑 Stopping popup watchers...")
        popup_handler.stop_watcher_loop()

    logger.info(f"🧹 Closing app: {package_name}")
    insta_actions.close_app()

    # --- Log Summary ---
    total_liked = sum(1 for r in all_reels_processed_info if r.get("liked"))
    total_comments_simulated = sum(
        1 for r in all_reels_processed_info if r.get("commented")
    )
    logger.info("📊 Session Summary:")
    logger.info(f"  - Total Reels Processed: {len(all_reels_processed_info)}")
    logger.info(f"  - Total Reels Liked:     {total_liked}")
    logger.info(f"  - Comment Interactions:  {total_comments_simulated}")


def main():
    """Main function to run the warmup session based on Airtable records."""
    # --- Configuration and Setup ---
    client = AirtableClient(table_key="warmup_accounts")
    warmup_records = client.get_pending_warmup_records()

    if not warmup_records:
        logger.info("No accounts scheduled for warmup today.")
        return

    logger.info(f"📦 Starting warmup session for {len(warmup_records)} accounts")

    # --- Loop Through Accounts ---
    for record in warmup_records:
        username = record.get("username", "UnknownUser")
        device_id = record.get("device_id")
        package_name = record.get("package_name")
        record_id = record.get("record_id")

        if not device_id or not package_name or not record_id:
            logger.error(
                f"Skipping record for user '{username}' due to missing device_id, package_name, or record_id."
            )
            continue

        logger.info(
            f"--- Running warmup for @{username} on {device_id} ({package_name}) ---"
        )

        insta_actions = None
        try:
            logger.info(f"🔌 Connecting to device: {device_id}")
            device = u2.connect(device_id, connect_timeout=20)
            try:
                info = device.info
                logger.info(
                    f"✅ Connected to {device.serial} - Product: {info.get('productName', 'N/A')}"
                )
            except Exception as conn_err:
                raise ConnectionError(
                    f"Failed to connect or communicate with device {device_id}: {conn_err}"
                )

            insta_actions = InstagramInteractions(
                device, package_name, airtable_manager=None
            )

            # --- Run the Warmup Session ---
            max_runtime = SCROLLER_CONFIG.get("max_runtime_seconds", 180)
            run_warmup_session(
                insta_actions=insta_actions, max_runtime_seconds=max_runtime
            )

            # --- Update Airtable on Success ---
            if isinstance(record_id, str):
                client.update_record_fields(record_id, {"Daily Warmup Complete": True})
                logger.info(f"✅ Warmup complete and marked for @{username}")
            else:
                logger.error(
                    f"Cannot mark warmup complete due to invalid record_id: {record_id}"
                )

        except ConnectionError as conn_err:
            logger.error(
                f"❌ Connection Error for @{username} on {device_id}: {conn_err}"
            )
            if isinstance(record_id, str):
                client.update_record_fields(
                    record_id, {"Warmup Errors": f"Connection Error: {conn_err}"}
                )
        except Exception as e:
            logger.error(
                f"❌ Unhandled exception during warmup for @{username}: {e}",
                exc_info=True,
            )
            if isinstance(record_id, str):
                client.update_record_fields(
                    record_id, {"Warmup Errors": f"Runtime Error: {e}"}
                )
        finally:
            if insta_actions:
                logger.info(f"Ensuring app is closed for @{username}...")
                insta_actions.close_app()
            logger.info(f"--- Finished processing for @{username} ---")
            time.sleep(random.uniform(5, 10))


if __name__ == "__main__":
    main()
