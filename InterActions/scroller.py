import uiautomator2 as u2
from stealth_typing import StealthTyper
import time
import hashlib
import random
from Shared.ui_helper import UIHelper
from Shared.logger_config import setup_logger

logger = setup_logger(name='Scroller')

setup_logger(name=__name__)
CONFIG = {
    # Delay ranges (in seconds)
    "delays": {
        "after_like": (1.8, 2.3),
        "between_scrolls": (2.0, 3.0),
        "before_scroll": (1.5, 2.2),
        "after_post_tap": (1.0, 1.5),
        "after_comment": (1.2, 2.0),
        "comment_scroll": (1.5, 2.5),
        "back_delay": 1.0,
    },

    # Session settings
    "session_duration_secs": 120,
    "max_scrolls": 100,
    "percent_reels_to_watch": 0.2,  # 0.0 to 1.0

    # Interaction probabilities
    "like_probability": 0.8,
    "comment_probability": 0.15,

    # Idle behavior
    "idle_after_actions": (3, 6),
    "idle_duration_range": (2, 9),

    # Package name
    "package_name": "com.instagram.androie",
}

def random_delay(label):
    lo, hi = CONFIG["delays"].get(label, (1, 2))
    t = random.uniform(lo, hi)
    logger.debug(f"Sleeping {t:.2f}s ({label})")
    time.sleep(t)

def extract_visible_reels(device, seen_hashes):
    reels = []
    elements = device.xpath('//android.widget.Button[contains(@content-desc, "Reel by")]').all()
    logger.info(f"Found {len(elements)} reel elements on screen")

    for el in elements:
        desc = el.attrib.get("content-desc", "")
        bounds = el.attrib.get("bounds", "")
        if not desc or not bounds:
            continue

        key = hashlib.sha1(desc.encode("utf-8")).hexdigest()
        if key in seen_hashes:
            continue

        seen_hashes.add(key)
        post = {
            "id": key,
            "short_id": key[:7],
            "username": desc.split("by")[1].split("at")[0].strip() if "by" in desc else "unknown",
            "type": "REEL",
            "desc": desc,
            "bounds": bounds  # Removed element/xpath to avoid stale refs
        }
        logger.info(f"[{post['short_id']}] @{post['username']} | REEL | {desc} | bounds={bounds}")
        reels.append(post)

    return reels
def extract_search_page_reels(device, seen_hashes):
    reels = []
    elements = device.xpath(f'//android.widget.FrameLayout[@resource-id="{CONFIG["package_name"]}:id/layout_container"]').all()
    logger.info(f"Found {len(elements)} layout containers")

    for el in elements:
        try:
            bounds = el.attrib.get("bounds", "")
            desc = el.attrib.get("content-desc", "reel")  # fallback tag
            key = hashlib.sha1(bounds.encode("utf-8")).hexdigest()

            if key in seen_hashes:
                continue

            seen_hashes.add(key)
            post = {
                "id": key,
                "short_id": key[:7],
                "username": "unknown",  # No desc in these
                "type": "REEL",
                "desc": desc,
                "bounds": bounds
            }
            logger.info(f"[{post['short_id']}] Search Page Reel | bounds={bounds}")
            reels.append(post)
        except Exception as e:
            logger.warning(f"Failed to parse reel container: {e}")
            continue

    return reels


def process_reel(device, reel_post, ui, like_probability, stop_callback):
    full_watch_time = random.uniform(2.0, 10.0)
    like_delay = random.uniform(1.2, full_watch_time - 0.5)
    sample_pool = [random.uniform(1.0, full_watch_time - 0.2) for _ in range(3)]
    num_interactions = min(len(sample_pool), random.randint(1, 2))
    interaction_times = sorted(random.sample(sample_pool, k=num_interactions))

    logger.info(f"⏱️ Watching reel for {full_watch_time:.2f}s (like at ~{like_delay:.2f}s)")
    start = time.time()
    liked = False

    # Retry tap loop (in case UI loads late)
    max_tap_attempts = 2
    for attempt in range(max_tap_attempts):
        logger.info(f"👆 Tapping reel at bounds {reel_post['bounds']} for {reel_post['short_id']} (attempt {attempt+1})")
        ui._tap_random_in_bounds(reel_post['bounds'], label="Reel Post")
        random_delay("after_post_tap")

        # Confirm reel UI is loaded by checking Like button has bounds
        like_btn = device.xpath('//*[@content-desc="Like"]')
        try:
            el = like_btn.get(timeout=4.0)
            if el and el.attrib.get("bounds"):
                break  # UI loaded
        except Exception:
            pass

        if attempt == max_tap_attempts - 1:
            logger.warning("Reel UI did not load, skipping.")
            return

    def get_desc(query):
        if time.time() - start > full_watch_time:
            return None
        try:
            el = device.xpath(query).get(timeout=2.0)
            return el.attrib.get("content-desc", "") if el else None
        except Exception:
            return None

    def get_text(query):
        if time.time() - start > full_watch_time:
            return None
        try:
            el = device.xpath(query).get(timeout=2.0)
            return el.attrib.get("text", "") if el else None
        except Exception:
            return None

    username = get_desc('//android.widget.ImageView[contains(@content-desc, "Profile picture of")]')
    caption = get_desc(f'//android.view.ViewGroup[@resource-id="{CONFIG["package_name"]}:id/clips_caption_component"]//android.view.ViewGroup[contains(@content-desc, "")]')
    likes = get_desc('//android.view.ViewGroup[contains(@content-desc, "View likes")]')
    reshares = get_desc('//android.view.ViewGroup[contains(@content-desc, "Reshare number")]')
    sound = get_desc('//android.view.ViewGroup[contains(@content-desc, "Original audio")]')
    follow_btn = get_text('//android.widget.Button[@text="Follow"]')

    if sound and "• Original audio" in sound:
        sound = sound.split("• Original audio")[0].strip()

    logger.info(f"[REEL DATA] user={username}, likes={likes}, reshares={reshares}, caption={caption}, sound={sound}, follow={follow_btn}")

    while time.time() - start < full_watch_time:
        elapsed = time.time() - start

        if interaction_times and elapsed >= interaction_times[0]:
            light_interaction(device, ui)
            interaction_times.pop(0)

        if not liked and elapsed >= like_delay and random.random() < like_probability:
            logger.info("Liking this reel mid-watch...")
            try:
                like_bounds = device.xpath('//*[@content-desc="Like"]').get(timeout=1.0).attrib.get("bounds", "")
                ui._tap_random_in_bounds(like_bounds, label="Like Button")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Failed to like: {e}")

            for _ in range(3):
                if device.xpath(f'//*[@resource-id="{CONFIG["package_name"]}:id/image_button"]').exists:
                    logger.warning("⚠️ Instagram blocked the like action")
                    stop_callback()
                    return
                time.sleep(1)

            liked = True

        time.sleep(0.4)

    # Back out once after reel watch
    back_btn = device.xpath('//*[@content-desc="Back"]')
    if back_btn.exists:
        try:
            bounds = back_btn.get().attrib.get("bounds", "")
            ui._tap_random_in_bounds(bounds, label="Back Button")
            time.sleep(1.5)
        except Exception as e:
            logger.warning(f"Failed to tap Back button: {e}")
    else:
        logger.warning("Back button not found after reel watch")

    # Wait until the Like button is no longer present (indicates exit from reel)
    for _ in range(10):
        if not device.xpath('//*[@content-desc="Like"]').exists:
            logger.info("✅ Exited reel view")
            break
        time.sleep(0.5)
    else:
        logger.warning("⚠️ Still detected in reel UI after back, continuing anyway")


def light_interaction(device, ui):
    action = random.choice(["pause_resume_tap", "swipe_comments", "side_scrub", "comment_scroll"])
    logger.info(f"👆 Performing light interaction: {action}")

    if action == "pause_resume_tap":
        x = random.randint(300, 800)
        y = random.randint(800, 1200)
        device.click(x, y)

    elif action == "swipe_comments":
        device.swipe(540, 1000, 540, 1300, 0.1)

    elif action == "side_scrub":
        x = random.randint(400, 700)
        y = random.randint(1000, 1300)
        device.swipe(x, y, x + random.randint(-50, 50), y, 0.1)

    elif action == "comment_scroll":
        logger.info("🗨️ Opening comments via comment button...")
        success = ui.tap_random_within_element('//android.widget.ImageView[@content-desc="Comment"]', label="Comment Button")
        if success:
            time.sleep(random.uniform(1.2, 2.0))
            device.swipe(540, 1600, 540, 1000, 0.2)
            time.sleep(random.uniform(1.5, 2.5))
            device.press("back")

def navigate_to_explore(device, ui):
    explore_xpath = '//android.widget.FrameLayout[@content-desc="Search and explore"]'
    search_ready_xpath = '//android.widget.EditText[@resource-id="com.instagram.androie:id/action_bar_search_edit_text"]'

    logger.info("📍 Navigating to Explore page...")
    success = ui.tap_random_within_element(explore_xpath, label="Explore Tab")
    if not success:
        logger.warning("❌ Could not find Explore tab.")
        time.sleep(2)
        return False

    try:
        device.xpath(search_ready_xpath).wait(timeout=10.0)
        logger.info("✅ Explore page loaded.")
        return True
    except Exception:
        logger.warning("❌ Search bar not found after tapping Explore.")
        return False




def perform_keyword_search(device, keyword):
    logger.info(f"🔍 Performing keyword search: {keyword}")
    search_xpath = f'//*[@resource-id="{CONFIG["package_name"]}:id/action_bar_search_edit_text"]'
    posts_xpath = f'//*[@resource-id="{CONFIG["package_name"]}:id/title_text_view" and @text="Posts"]'
    typer = StealthTyper(device_id=device.serial)

    try:
        # Step 1: Locate and tap the search bar
        if not device.xpath(search_xpath).wait(timeout=10):
            logger.warning("❌ Search bar not found.")
            return False

        el = device.xpath(search_xpath).get(timeout=2.0)
        if not el:
            logger.warning("❌ Could not get reference to search bar element.")
            return False

        logger.info("✅ Search bar found, tapping...")
        el.click()
        time.sleep(1)

        # Step 2: Type the keyword
        typer.type_text(keyword)
        time.sleep(0.5)
        typer.press_enter()
        logger.info("⏎ Enter pressed to start search.")
        time.sleep(2)

        # Step 3: Scroll slightly to reveal posts
        logger.info("↕️ Scrolling to skip account results...")
        device.swipe(540, 1300, 540, 900, 0.2)
        time.sleep(1.0)

        # Step 4: Wait for the "Posts" section
        logger.info("🧭 Looking for 'Posts' section...")
        if not device.xpath(posts_xpath).wait(timeout=5.0):
            logger.error("❌ 'Posts' section not found after search. Can't continue.")
            return False

        logger.info("✅ 'Posts' section found — reels can now be extracted.")
        return True

    except Exception as e:
        logger.error(f"❌ Failed during keyword search flow: {e}")
        return False

def main():
    d = u2.connect()
    ui = UIHelper(d)
    seen_hashes = set()
    all_reels = []

    if not navigate_to_explore(d, ui):
        logger.error("🚫 Failed to navigate to Explore. Exiting.")
        return

    if not perform_keyword_search(d, "model"):
        logger.error("🚫 Keyword search failed. Exiting.")
        return

    start_time = time.time()
    actions = 0
    next_idle_at = random.randint(*CONFIG["idle_after_actions"])

    for i in range(CONFIG["max_scrolls"]):
        if time.time() - start_time > CONFIG["session_duration_secs"]:
            logger.info("⏰ Session time complete. Ending.")
            break

        logger.info(f"Scroll iteration {i + 1}")
        reels = extract_search_page_reels(d, seen_hashes)
        if not reels:
            logger.info("No new reels found.")
            break

        logger.info(f"New reels: {len(reels)}")
        all_reels.extend(reels)

        num_to_process = max(1, int(len(reels) * CONFIG["percent_reels_to_watch"]))
        to_process = random.sample(reels, num_to_process)

        for reel in to_process:
            logger.info(f"Selected reel [{reel['short_id']}] to process")
            process_reel(d, reel, ui, CONFIG["like_probability"], stop_callback=None)
            actions += 1

            if actions >= next_idle_at:
                idle_time = random.uniform(*CONFIG["idle_duration_range"])
                logger.info(f"😴 Idle break for {idle_time:.2f}s")
                time.sleep(idle_time)
                actions = 0
                next_idle_at = random.randint(*CONFIG["idle_after_actions"])

        random_delay("before_scroll")
        ui.scroll_up()

    logger.info(f"✅ Session complete. Total unique reels interacted: {len(all_reels)}")



if __name__ == "__main__":
    main()
