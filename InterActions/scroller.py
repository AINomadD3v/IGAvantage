# InterActions/scroller.py

import hashlib
import random
import time
from typing import Optional, Tuple

import uiautomator2 as u2

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
    # Define fallback defaults here if necessary, or raise an error
    SCROLLER_CONFIG = {  # Example fallback structure
        "keywords": ["model", "fitness"],
        "delays": {"default": [1.0, 2.0]},
        "max_scrolls": 10,
        "percent_reels_to_watch": 0.5,
        "watch_time_range": [3.0, 6.0],
        "like_probability": 0.5,
        "comment_probability": 0.1,
        "idle_after_actions": [5, 10],
        "idle_duration_range": [3, 7],
    }

# Extract keywords from the loaded config
KEYWORDS = SCROLLER_CONFIG.get("keywords", ["model"])  # Provide a default keyword list
if not KEYWORDS:
    logger.warning("No keywords found in scroller config, using default: ['model']")
    KEYWORDS = ["model"]


# --- Utility Functions ---
def random_delay(label: str):
    """Sleeps for a random duration based on the label from SCROLLER_CONFIG."""
    # Access delays from the loaded SCROLLER_CONFIG dictionary
    delays_config = SCROLLER_CONFIG.get("delays", {})
    # Provide a default delay if the specific label isn't found
    lo, hi = delays_config.get(label, delays_config.get("default", [1.0, 2.0]))
    # Ensure lo and hi are valid numbers
    try:
        lo_f = float(lo)
        hi_f = float(hi)
        if hi_f < lo_f:  # Swap if order is wrong
            hi_f, lo_f = lo_f, hi_f
        t = random.uniform(lo_f, hi_f)
        logger.debug(f"Sleeping {t:.2f}s ({label})")
        time.sleep(t)
    except (TypeError, ValueError) as e:
        logger.error(
            f"Invalid delay config for '{label}': {lo}, {hi}. Using default 1s. Error: {e}"
        )
        time.sleep(1.0)


# --- Core Logic Functions (Refactored to use InstagramInteractions for ACTIONS, XPaths kept) ---


def extract_search_page_reels(insta_actions: InstagramInteractions) -> list[dict]:
    """
    Extracts reel information specifically from the search/explore results page.
    Uses insta_actions for device access but keeps original XPaths for now.
    """
    reels = []
    seen_this_screen = set()
    device = insta_actions.device  # Get device object from insta_actions

    try:
        # TODO: Refactor XPath to use xpath_config
        # Find potential containers using original direct XPath calls
        containers = (
            device.xpath("//android.widget.FrameLayout")
            & device.xpath(
                "^.*layout_container$"
            )  # Example - Check if this is still needed/correct
        ).all()
        logger.info(
            f"Found {len(containers)} potential layout containers on search page"
        )

        for container in containers:
            try:
                # Get container's specific XPath (less reliable, try to avoid if possible)
                container_xpath = container.get_xpath(
                    strip_index=True
                )  # This can be fragile

                # Skip image posts with 'photos by'
                # TODO: Refactor XPath to use xpath_config
                bad_btns = device.xpath(
                    f"{container_xpath}//android.widget.Button"
                ).all()
                is_image_post = False
                for btn in bad_btns:
                    # Accessing attrib directly - consider using insta_actions.get_element_attribute if needed elsewhere
                    btn_rid = btn.attrib.get("resource-id") or ""
                    btn_desc = btn.attrib.get("content-desc") or ""
                    if (
                        "image_button" in btn_rid  # Keep original literal
                        and "photos by" in btn_desc.lower()  # Keep original literal
                    ):
                        logger.debug(
                            "🧨 Skipping image post (found 'photos by' button)"
                        )
                        is_image_post = True
                        break
                if is_image_post:
                    continue  # Skip this container

                # Look for reel ImageViews inside this container
                # TODO: Refactor XPath to use xpath_config
                ivs = device.xpath(f"{container_xpath}//android.widget.ImageView").all()
                for iv in ivs:
                    # Accessing attrib directly
                    desc = iv.attrib.get("content-desc", "").strip()
                    bounds_str = iv.attrib.get(
                        "bounds", ""
                    ).strip()  # Keep bounds as string for now

                    if not desc or not bounds_str:
                        continue
                    # Keep original literal check
                    if "Reel by" not in desc:
                        continue

                    # Deduplicate within-screen
                    screen_key = desc  # Using full description as key
                    if screen_key in seen_this_screen:
                        continue
                    seen_this_screen.add(screen_key)

                    # Build post data
                    key = hashlib.sha1(screen_key.encode("utf-8")).hexdigest()
                    username = "unknown"
                    try:
                        # Attempt to parse username more reliably
                        username_part = desc.split("by", 1)[1]  # Split only once
                        username = username_part.split("at", 1)[0].strip()
                    except IndexError:
                        logger.warning(f"Could not parse username from desc: {desc}")

                    post = {
                        "id": key,
                        "short_id": key[:7],
                        "username": username,
                        "type": "REEL",
                        "desc": desc,  # This is the key identifier for tapping later
                        "bounds": bounds_str,  # Store original string format
                    }
                    logger.info(
                        f"[{post['short_id']}] ✅ Extracted Reel | @{username} | bounds={bounds_str}"
                    )
                    reels.append(post)

            # except StopIteration: # This was used before, ensure logic doesn't rely on it now
            #     continue
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to parse a container: {e}", exc_info=False
                )  # Keep logs cleaner
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
    # TODO: Refactor XPath to use xpath_config template
    reel_tap_xpath = f'//android.widget.ImageView[@content-desc="{reel_post["desc"]}"]'
    if not insta_actions.click_by_xpath(reel_tap_xpath, timeout=5):
        logger.error(
            f"❌ Failed to tap/open reel [{reel_post.get('short_id', 'N/A')}] using XPath: {reel_tap_xpath}"
        )
        return None

    random_delay("after_post_tap")  # Uses delay from SCROLLER_CONFIG

    # --- Extract reel metadata ---
    # TODO: Refactor XPaths to use xpath_config
    username_element_xpath = (
        '//android.widget.ImageView[contains(@content-desc, "Profile picture of")]'
    )
    username = insta_actions.get_element_attribute(
        username_element_xpath, "contentDescription", timeout=2
    )
    if username and "Profile picture of" in username:
        username = username.replace("Profile picture of", "").strip()

    # TODO: Refactor XPath to use xpath_config (ensure package name is correct or use placeholder)
    package_name = insta_actions.app_package  # Get package name from insta_actions
    caption_element_xpath = f'//android.view.ViewGroup[@resource-id="{package_name}:id/clips_caption_component"]//android.view.ViewGroup[contains(@content-desc, "")]'
    caption = insta_actions.get_element_text(caption_element_xpath, timeout=2)

    # TODO: Refactor XPath to use xpath_config
    likes_element_xpath = (
        '//android.view.ViewGroup[contains(@content-desc, "View likes")]'
    )
    likes = insta_actions.get_element_attribute(
        likes_element_xpath, "contentDescription", timeout=2
    )

    # TODO: Refactor XPath to use xpath_config
    reshares_element_xpath = (
        '//android.view.ViewGroup[contains(@content-desc, "Reshare number")]'
    )
    reshares = insta_actions.get_element_attribute(
        reshares_element_xpath, "contentDescription", timeout=2
    )

    # TODO: Refactor XPath to use xpath_config
    sound_element_xpath = (
        '//android.view.ViewGroup[contains(@content-desc, "Original audio")]'
    )
    sound = insta_actions.get_element_attribute(
        sound_element_xpath, "contentDescription", timeout=2
    )

    # TODO: Refactor XPath to use xpath_config
    follow_button_xpath = '//android.widget.Button[@text="Follow"]'
    follow_btn_exists = insta_actions.element_exists(follow_button_xpath)

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
                liked = insta_actions.like_current_post_or_reel()
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
            commented = insta_actions.simulate_open_close_comments()
            if commented:
                random_delay("after_comment")
            should_comment = False

        time.sleep(0.2)

    # --- Fallback Like ---
    if not liked and random.random() < like_probability:
        logger.info("📌 Fallback: Attempting like near end of watch window.")
        liked = insta_actions.like_current_post_or_reel()

    # --- Exit Reel View ---
    # TODO: Refactor XPath to use xpath_config
    like_button_xpath_for_verify = '//*[@content-desc="Like" or @content-desc="Unlike"]'
    insta_actions.navigate_back_from_reel(
        verify_element_disappears=like_button_xpath_for_verify
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
    Uses insta_actions for UI interactions and StealthTyper for input.
    Keeps original XPaths for now.
    """
    logger.info(f"🔍 Performing keyword search: {keyword}")
    device = insta_actions.device  # Get device for direct swipe/xpath calls below

    # TODO: Refactor XPath to use xpath_config
    search_xpath = f"//*[contains(@resource-id, 'action_bar_search_edit_text')]"
    # TODO: Refactor XPath to use xpath_config (ensure package name is correct)
    posts_xpath = f'//*[@resource-id="{CONFIG["package_name"]}:id/title_text_view" and @text="Posts"]'
    # TODO: Refactor XPath to use xpath_config
    results_recycler_xpath = "//*[contains(@resource-id, 'recycler_view')]"

    # Assuming StealthTyper is still needed for robust input
    typer = StealthTyper(device_id=insta_actions.device.serial)

    try:
        # Step 1: Locate and tap the search bar
        # Use insta_actions methods
        if not insta_actions.wait_for_element_appear(search_xpath, timeout=10):
            logger.error("❌ Search bar not found on Explore page.")
            return False
        if not insta_actions.click_by_xpath(search_xpath, timeout=2):
            logger.error("❌ Failed to click search bar.")
            return False
        logger.info("✅ Search bar tapped.")
        time.sleep(random.uniform(0.8, 1.2))  # Wait for keyboard potentially

        # Step 2: Type the keyword using StealthTyper
        typer.type_text(keyword)  # Keep direct StealthTyper call for now
        time.sleep(random.uniform(0.3, 0.6))
        typer.press_enter()  # Assumes StealthTyper has this method
        logger.info("⏎ Enter pressed to start search.")
        time.sleep(random.uniform(2.5, 4.0))  # Wait for search results to load

        # Step 3: Scroll slightly to reveal posts (use direct swipe for now)
        logger.info("↕️ Scrolling down slightly to reveal posts...")
        # Use insta_actions method
        insta_actions.scroll_up_humanlike()  # Scroll up = swipe down
        time.sleep(random.uniform(1.0, 1.5))

        # Step 4: Wait for the "Posts" section or results recycler view
        logger.info("🧭 Looking for posts section / results...")
        # Use insta_actions method
        if not insta_actions.wait_for_element_appear(
            results_recycler_xpath, timeout=10
        ):  # Wait for general results container
            logger.error(
                "❌ Search results recycler view not found after search. Can't continue."
            )
            # Optional: Check specifically for the "Posts" text element as well
            # if not insta_actions.element_exists(posts_xpath):
            #     logger.error("❌ 'Posts' text indicator also not found.")
            return False

        logger.info("✅ Search results loaded.")
        return True

    except Exception as e:
        logger.error(f"❌ Failed during keyword search flow: {e}", exc_info=True)
        return False


def run_warmup_session(
    insta_actions: InstagramInteractions, max_runtime_seconds: int = 180
):
    """
    Runs the main warmup/scrolling session logic. Uses insta_actions instance and SCROLLER_CONFIG.

    Args:
        insta_actions: The initialized InstagramInteractions instance.
        max_runtime_seconds: Maximum duration for the session.
    """
    device = insta_actions.device
    package_name = insta_actions.app_package

    # Get config values safely
    max_scrolls = SCROLLER_CONFIG.get("max_scrolls", 50)
    percent_reels_to_watch = SCROLLER_CONFIG.get("percent_reels_to_watch", 0.7)
    idle_after_actions_range = SCROLLER_CONFIG.get("idle_after_actions", [3, 6])
    idle_duration_range = SCROLLER_CONFIG.get("idle_duration_range", [2, 6])
    like_probability = SCROLLER_CONFIG.get(
        "like_probability", 0.5
    )  # Needed for process_reel call

    # --- Setup Popup Handler ---
    popup_handler = PopupHandler(device)
    # TODO: Set context for popup_handler if callbacks need it
    # popup_handler.set_context(...)
    popup_handler.register_watchers()
    popup_handler.start_watcher_loop()

    logger.info(f"📱 Ensuring Instagram app is open and ready: {package_name}")
    # TODO: Refactor XPath to use xpath_config
    explore_tab_xpath = (
        '//android.widget.FrameLayout[@content-desc="Search and explore"]'
    )
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
    if not insta_actions.navigate_to_explore(timeout=15):
        logger.error("🚫 Failed to navigate to Explore page. Exiting.")
        if popup_handler:
            popup_handler.stop_watcher_loop()
        insta_actions.close_app()
        return

    # --- Perform Keyword Search ---
    keyword = random.choice(KEYWORDS)  # Use keywords loaded from config
    logger.info(f"🎯 Chosen keyword for search: '{keyword}'")
    if not perform_keyword_search(insta_actions, keyword):
        logger.error("🚫 Keyword search failed. Exiting.")
        if popup_handler:
            popup_handler.stop_watcher_loop()
        insta_actions.close_app()
        return

    # --- Main Scrolling Loop ---
    start_time = time.time()
    actions_since_idle = 0
    # Ensure range values are integers for randint
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
            processing_result = process_reel(
                insta_actions=insta_actions,
                reel_post=reel_data,
                like_probability=like_probability,  # Pass loaded probability
                stop_callback=None,
            )
            seen_hashes.add(reel_data["id"])
            if processing_result:
                processing_result["original_desc"] = reel_data["desc"]
                processing_result["original_bounds"] = reel_data["bounds"]
                all_reels_processed_info.append(processing_result)

            actions_since_idle += 1
            if actions_since_idle >= next_idle_at:
                idle_time = random.uniform(*idle_duration_range)  # Use loaded range
                logger.info(f"😴 Idle break for {idle_time:.2f}s")
                time.sleep(idle_time)
                actions_since_idle = 0
                next_idle_at = random.randint(idle_min, idle_max)  # Use loaded range

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
    # --- Configuration and Setup ---
    client = AirtableClient(table_key="warmup_accounts")  # Keep Airtable logic
    warmup_records = client.get_pending_warmup_records()

    if not warmup_records:
        logger.info("No accounts scheduled for warmup today.")
        return

    logger.info(f"📦 Starting warmup session for {len(warmup_records)} accounts")

    # --- Loop Through Accounts ---
    for record in warmup_records:
        # Extract necessary info (handle potential missing keys)
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

        insta_actions = None  # Initialize for finally block
        try:
            # --- Connect to Device and Instantiate Interactions Class ---
            logger.info(f"🔌 Connecting to device: {device_id}")
            device = u2.connect(device_id, connect_timeout=20)  # Add timeout
            if not device.alive:
                raise ConnectionError(f"Failed to connect to device {device_id}")
            logger.info(f"✅ Connected to {device.serial}")

            # Instantiate the main interactions class
            insta_actions = InstagramInteractions(
                device, package_name, airtable_manager=None
            )  # Pass None for airtable if not needed by interactions

            # --- Run the Warmup Session ---
            run_warmup_session(
                insta_actions=insta_actions,  # Pass the instance
                max_runtime_seconds=180,  # Example runtime
            )

            # --- Update Airtable on Success ---
            client.update_record_fields(record_id, {"Daily Warmup Complete": True})
            logger.info(f"✅ Warmup complete and marked for @{username}")

        except ConnectionError as conn_err:
            logger.error(
                f"❌ Connection Error for @{username} on {device_id}: {conn_err}"
            )
            client.update_record_fields(
                record_id, {"Warmup Errors": f"Connection Error: {conn_err}"}
            )
        except Exception as e:
            logger.error(
                f"❌ Unhandled exception during warmup for @{username}: {e}",
                exc_info=True,
            )
            client.update_record_fields(
                record_id, {"Warmup Errors": f"Runtime Error: {e}"}
            )
        finally:
            # Ensure app is closed even if errors occurred mid-session
            if insta_actions:
                logger.info(f"Ensuring app is closed for @{username}...")
                insta_actions.close_app()  # Use the method
            logger.info(f"--- Finished processing for @{username} ---")
            # Add a delay between accounts if needed
            time.sleep(random.uniform(5, 10))


if __name__ == "__main__":
    main()
