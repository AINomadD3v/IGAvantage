# Shared.scroller.py

import time
import random
import hashlib
import uiautomator2 as u2
from Shared import popup_handler
from Shared.ui_helper import UIHelper
from Shared.logger_config import setup_logger
from Shared.stealth_typing import StealthTyper
from Shared.airtable_manager import AirtableClient
from Shared.core_ig_actions import launch_app_via_adb
from Shared.popup_handler import PopupHandler

logger = setup_logger(name='Scroller')

KEYWORDS = ["female model", "female fitness", "american model", "bikini", "gym girl", "fit girls", "fitness model", "hot woman", "blonde model", "asian model" ]

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
    "max_scrolls": 100,
    "percent_reels_to_watch": 0.8,  # 0.0 to 1.0
    "watch_time_range": (4.0, 9.0),  # 👈 Add this

    # Interaction probabilities
    "like_probability": 0.7,
    "comment_probability": 0.25,

    # Idle behavior
    "idle_after_actions": (3, 6),
    "idle_duration_range": (2, 6),

    # Package name
    "package_name": "com.instagram.androig",
}

def force_stop_app(device, package_name):
    logger.info(f"🧹 Force-stopping {package_name}")
    device.app_stop(package_name)
    device.shell(f"am force-stop {package_name}")
    time.sleep(1)  # Let Android finalize cleanup

def random_delay(label):
    lo, hi = CONFIG["delays"].get(label, (1, 2))
    t = random.uniform(lo, hi)
    logger.debug(f"Sleeping {t:.2f}s ({label})")
    time.sleep(t)

def extract_search_page_reels(device):
    reels = []
    seen_this_screen = set()
    containers = (device.xpath('//android.widget.FrameLayout') & device.xpath('^.*layout_container$')).all()
    logger.info(f"Found {len(containers)} layout containers")

    for container in containers:
        try:
            container_xpath = container.get_xpath(strip_index=True)

            # Skip image posts with 'photos by'
            bad_btns = device.xpath(f'{container_xpath}//android.widget.Button').all()
            for btn in bad_btns:
                if "image_button" in (btn.attrib.get("resource-id") or "") and "photos by" in (btn.attrib.get("content-desc") or "").lower():
                    logger.debug("🧨 Skipping image post (image_button + photos by)")
                    raise StopIteration

            # Look for all reel ImageViews inside this container
            ivs = device.xpath(f'{container_xpath}//android.widget.ImageView').all()
            for iv in ivs:
                desc = iv.attrib.get("content-desc", "").strip()
                bounds = iv.attrib.get("bounds", "").strip()
                if not desc or not bounds:
                    continue
                if "Reel by" not in desc:
                    continue

                # Deduplicate within-screen
                screen_key = desc
                if screen_key in seen_this_screen:
                    continue
                seen_this_screen.add(screen_key)

                # Build post
                key = hashlib.sha1(screen_key.encode("utf-8")).hexdigest()
                username = desc.split("by")[1].split("at")[0].strip()
                post = {
                    "id": key,
                    "short_id": key[:7],
                    "username": username,
                    "type": "REEL",
                    "desc": desc,
                    "bounds": bounds,
                }
                logger.info(f"[{post['short_id']}] ✅ Reel | @{username} | bounds={bounds}")
                reels.append(post)

        except StopIteration:
            continue
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse reel container: {e}")
            continue

    return reels


def process_reel(device, reel_post, ui, like_probability, stop_callback):
    full_watch_time = random.uniform(*CONFIG["watch_time_range"])
    like_delay = random.uniform(1.2, full_watch_time - 0.5)
    interaction_times = sorted(random.sample(
        [random.uniform(1.0, full_watch_time - 0.2) for _ in range(3)],
        k=min(2, 3)
    ))

    logger.info(f"⏱️ Watching reel for {full_watch_time:.2f}s (like at ~{like_delay:.2f}s)")
    start = time.time()
    end = start + full_watch_time
    liked = False
    commented = False
    should_comment = random.random() < CONFIG["comment_probability"]
    next_interaction = interaction_times.pop(0) if interaction_times else None

    # Tap the reel
    if not attempt_reel_tap(device, reel_post):
        return

    random_delay("after_post_tap")

    # Extract reel metadata (non-blocking, quick)
    username = get_desc(device, '//android.widget.ImageView[contains(@content-desc, "Profile picture of")]', full_watch_time, start)
    caption = get_desc(device, f'//android.view.ViewGroup[@resource-id="{CONFIG["package_name"]}:id/clips_caption_component"]//android.view.ViewGroup[contains(@content-desc, "")]', full_watch_time, start)
    likes = get_desc(device, '//android.view.ViewGroup[contains(@content-desc, "View likes")]', full_watch_time, start)
    reshares = get_desc(device, '//android.view.ViewGroup[contains(@content-desc, "Reshare number")]', full_watch_time, start)
    sound = get_desc(device, '//android.view.ViewGroup[contains(@content-desc, "Original audio")]', full_watch_time, start)
    follow_btn = get_text(device, '//android.widget.Button[@text="Follow"]', full_watch_time, start)

    if sound and "• Original audio" in sound:
        sound = sound.split("• Original audio")[0].strip()

    logger.info(f"[REEL DATA] user={username}, likes={likes}, reshares={reshares}, caption={caption}, sound={sound}, follow={follow_btn}")

    # Central timing loop
    while time.time() < end:
        elapsed = time.time() - start

        if next_interaction and elapsed >= next_interaction:
            light_interaction(device)
            next_interaction = interaction_times.pop(0) if interaction_times else None

        if not liked and elapsed >= like_delay and random.random() < like_probability:
            liked = attempt_like(device, ui)
            if liked:
                logger.info("❤️ Like confirmed.")
            else:
                logger.warning("❌ Like failed or blocked.")
                if stop_callback:
                    stop_callback()
                break

        if not commented and should_comment and elapsed >= full_watch_time * 0.6:
            commented = attempt_comment(device, ui)

        time.sleep(0.2)

    # Fallback like
    if not liked and random.random() < like_probability:
        logger.info("📌 Fallback: Liking reel near end of watch window.")
        liked = attempt_like(device, ui)

    exit_reel_view(device)

    return {
        "username": username,
        "likes": likes,
        "reshares": reshares,
        "caption": caption,
        "liked": liked,
        "commented": commented
    }
def light_interaction(device):
    action = random.choice(["tap_to_pause_resume", "mini_horizontal_scrub", "minor_volume_change"])

    if action == "tap_to_pause_resume":
        # Light tap near center — simulates pausing and resuming
        x = random.randint(400, 700)
        y = random.randint(800, 1100)
        device.click(x, y)
        logger.info("👆 Light interaction: pause/resume tap")

    elif action == "mini_horizontal_scrub":
        # Slight side scrub motion — mimics user testing timeline
        x = random.randint(400, 600)
        y = random.randint(1000, 1300)
        offset = random.randint(10, 30)
        device.swipe(x, y, x + offset, y, 0.05)
        logger.info("👉 Light interaction: mini scrub")

    elif action == "minor_volume_change":
        # Simulates user pressing volume up/down quickly
        key = random.choice(["KEYCODE_VOLUME_UP", "KEYCODE_VOLUME_DOWN"])
        device.shell(f"input keyevent {key}")
        logger.info(f"🔊 Light interaction: {key.replace('KEYCODE_', '').lower()}")

def get_desc(device, xpath, timeout_window, start_time):
    if time.time() - start_time > timeout_window:
        return None
    try:
        el = device.xpath(xpath).get(timeout=2.0)
        return el.attrib.get("content-desc", "") if el else None
    except Exception:
        return None

def get_text(device, xpath, timeout_window, start_time):
    if time.time() - start_time > timeout_window:
        return None
    try:
        el = device.xpath(xpath).get(timeout=2.0)
        return el.attrib.get("text", "") if el else None
    except Exception:
        return None

def attempt_reel_tap(device, reel_post):
    for attempt in range(2):
        try:
            reel_xpath = f'//android.widget.ImageView[@content-desc="{reel_post["desc"]}"]'
            el = device.xpath(reel_xpath).get(timeout=2.0)
            el.click()
            logger.info(f"👆 Clicked reel via XPath: {reel_xpath}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to click reel (attempt {attempt + 1}): {e}")
    return False

def attempt_like(device, ui):
    try:
        el = device.xpath('//*[@content-desc="Like"]').get(timeout=1.5)
        bounds = el.attrib.get("bounds", "")
        ui._tap_random_in_bounds(bounds, label="Like Button")
        time.sleep(1.0)
        el = device.xpath('//*[@content-desc="Like"]').get(timeout=1.5)
        return el.attrib.get("selected") == "true"
    except Exception as e:
        logger.warning(f"⚠️ Failed to like: {e}")
        return False

def attempt_comment(device, ui):
    logger.info("💬 Attempting to comment mid-watch...")
    try:
        if ui.tap_random_within_element('//*[contains(@content-desc, "Comment")]', label="Comment Button"):
            time.sleep(1.5)
            device.swipe(540, 1600, 540, 1000, 0.2)
            time.sleep(1.5)
            device.press("back")
            logger.info("💬 Comment interaction complete")
            return True
    except Exception as e:
        logger.warning(f"⚠️ Failed to perform comment interaction: {e}")
    return False

def exit_reel_view(device):
    try:
        back_btn = device.xpath('//*[@content-desc="Back"]')
        if back_btn.exists:
            back_btn.get().click()
            logger.info("🖐 Back button clicked directly")
        time.sleep(1.5)
    except Exception as e:
        logger.warning(f"Failed to click Back button: {e}")

    for _ in range(10):
        if not device.xpath('//*[@content-desc="Like"]').exists:
            logger.info("✅ Exited reel view")
            return
        time.sleep(0.5)
    logger.warning("⚠️ Still in reel UI after back")


def navigate_to_explore(device, ui):
    explore_xpath = '//android.widget.FrameLayout[@content-desc="Search and explore"]'
    search_ready_xpath = "//*[contains(@resource-id, 'action_bar_search_edit_text')]"

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
    search_xpath = f"//*[contains(@resource-id, 'action_bar_search_edit_text')]"
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
        time.sleep(3)

        # Step 3: Scroll slightly to reveal posts
        logger.info("↕️ Scrolling to skip account results...")
        device.swipe(540, 1300, 540, 900, 0.4)
        time.sleep(1.0)

        # Step 4: Wait for the "Posts" section
        logger.info("🧭 Looking for 'Posts' section...")
        if not device.xpath("//*[contains(@resource-id, 'recycler_view')]").wait(timeout=5.0):
            logger.error("❌ 'Posts' section not found after search. Can't continue.")
            return False

        logger.info("✅ 'Posts' section found — reels can now be extracted.")
        return True

    except Exception as e:
        logger.error(f"❌ Failed during keyword search flow: {e}")
        return False

def run_warmup_session(device_id, package_name, max_runtime_seconds=180, ui_helper=None):
    d = u2.connect(device_id)
    CONFIG["package_name"] = package_name
    ui = ui_helper or UIHelper(d)

    popup_handler = PopupHandler(d, helper=ui)
    popup_handler.register_watchers()
    d.watcher.start()

    logger.info(f"📱 Launching Instagram app: {package_name}")
    try:
        launch_app_via_adb(device_id, package_name)
        logger.info("🕒 Waiting 15s to allow popup watchers to trigger...")
        time.sleep(15)


        explore_xpath = '//android.widget.FrameLayout[@content-desc="Search and explore"]'
        if not d.xpath(explore_xpath).wait(timeout=15.0):
            raise RuntimeError("Instagram UI not detected after launch")

        logger.info("✅ Instagram UI ready — Explore tab found")
    except Exception as e:
        logger.error(f"❌ Failed to launch Instagram app via ADB: {e}")
        return


    seen_hashes = set()
    all_reels = []
    session_stats = []

    if not navigate_to_explore(d, ui):
        logger.error("🚫 Failed to navigate to Explore. Exiting.")
        return

    keyword = random.choice(KEYWORDS)
    logger.info(f"🎯 Chosen keyword: '{keyword}'")

    if not perform_keyword_search(d, keyword):
        logger.error("🚫 Keyword search failed. Exiting.")
        return

    start_time = time.time()
    actions = 0
    next_idle_at = random.randint(*CONFIG["idle_after_actions"])

    for i in range(CONFIG["max_scrolls"]):
        elapsed = time.time() - start_time
        if elapsed > max_runtime_seconds:
            logger.info(f"⏰ Runtime limit ({max_runtime_seconds}s) exceeded. Ending session.")
            break

        logger.info(f"Scroll iteration {i + 1}")
        retries = 0
        reels = []

        while retries < 3:
            all_detected = extract_search_page_reels(d)
            reels = [r for r in all_detected if r["id"] not in seen_hashes]
            if reels:
                break
            retries += 1
            logger.info(f"🔁 No new reels found, scrolling up (retry {retries}/3)...")
            random_delay("before_scroll")
            ui.scroll_up()

        if not reels:
            logger.info("🚫 No new reels found after retries. Ending session.")
            break

        logger.info(f"New reels: {len(reels)}")
        num_to_process = max(1, int(len(reels) * CONFIG["percent_reels_to_watch"]))
        to_process = random.sample(reels, num_to_process)

        for reel in to_process:
            logger.info(f"🎬 Processing reel [{reel['short_id']}]")
            result = process_reel(d, reel, ui, CONFIG["like_probability"], stop_callback=None)

            seen_hashes.add(reel["id"])
            all_reels.append(reel)

            if result:
                session_stats.append(result)

            actions += 1
            if actions >= next_idle_at:
                idle_time = random.uniform(*CONFIG["idle_duration_range"])
                logger.info(f"😴 Idle break for {idle_time:.2f}s")
                time.sleep(idle_time)
                actions = 0
                next_idle_at = random.randint(*CONFIG["idle_after_actions"])

        random_delay("before_scroll")
        ui.scroll_up()

    duration = time.time() - start_time
    logger.info(f"🕒 Warmup session runtime: {duration:.2f}s")
    logger.info(f"✅ Warmup complete. Total unique reels interacted: {len(all_reels)}")

    total_liked = sum(1 for r in session_stats if r.get("liked"))
    total_comments = sum(1 for r in session_stats if r.get("commented"))

    logger.info("📊 Session Summary:")
    logger.info(f"   - Total Reels Watched: {len(session_stats)}")
    logger.info(f"   - Total Reels Liked:   {total_liked}")
    logger.info(f"   - Comment Scrolls:     {total_comments}")
    logger.info("   - Reels interacted with:")
    for r in session_stats:
        logger.info(f"     @{r['username']}: liked={r['liked']}, comments={r['commented']}, likes='{r['likes']}', reshares='{r['reshares']}'")

    # 🧹 Fully terminate the app before returning
    force_stop_app(d, package_name)

def main():
    client = AirtableClient(table_key="warmup_accounts")
    warmup_records = client.get_pending_warmup_records()

    logger.info(f"📦 Starting warmup session for {len(warmup_records)} accounts")

    last_package = None

    for record in warmup_records:
        username = record["username"]
        device_id = record["device_id"]
        package_name = record["package_name"]
        record_id = record["record_id"]

        logger.info(f"🚀 Running warmup for @{username} on {device_id} ({package_name})")

        try:
            if last_package and last_package != package_name:
                logger.info(f"🧹 Stopping previous app: {last_package}")
                d = u2.connect(device_id)
                d.app_stop(last_package)
                time.sleep(1)

            # 🔌 Inject context for Airtable + PopupHandler
            d = u2.connect(device_id)
            ui = UIHelper(d)
            ui.airtable_client = client
            ui.record_id = record_id
            ui.package_name = package_name
            ui.base_id = client.base_id
            ui.table_id = client.table_id

            run_warmup_session(
                device_id=device_id,
                package_name=package_name,
                max_runtime_seconds=180,
                ui_helper=ui
            )

            client.update_record_fields(record_id, {"Daily Warmup Complete": True})
            logger.info(f"✅ Warmup complete and marked for @{username}")
            last_package = package_name

        except Exception as e:
            logger.error(f"❌ Warmup failed for @{username}: {e}")
            client.update_record_fields(record_id, {"Warmup Errors": str(e)})

if __name__ == "__main__":
    main()
