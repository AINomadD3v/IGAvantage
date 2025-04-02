import time
import random
import hashlib
import uiautomator2 as u2
from typing import List, Dict, Optional
from Shared.stealth_typing import StealthTyper
from Shared.logger_config import setup_logger
from Shared.ui_helper import UIHelper
from reels_config import CONFIG


logger = setup_logger(__name__)

class ReelScroller:
    def __init__(self, device, ui_helper: UIHelper, config: dict,
                 airtable_client=None, account_info: Optional[Dict] = None):
        self.d = device
        self.ui = ui_helper
        self.config = config
        self.airtable = airtable_client
        self.account_info = account_info
        self.seen_hashes = set()
        self.actions = 0

    def run(self):
        if not self.navigate_to_explore():
            logger.error("🚫 Failed to navigate to Explore. Exiting.")
            return

        if not self.perform_keyword_search("model"):
            logger.error("🚫 Keyword search failed. Exiting.")
            return

        start_time = time.time()
        next_idle_at = random.randint(*self.config["idle_after_actions"])

        for i in range(self.config["max_scrolls"]):
            if time.time() - start_time > self.config["session_duration_secs"]:
                logger.info("⏰ Session time complete. Ending.")
                break

            logger.info(f"Scroll iteration {i + 1}")
            reels = self.extract_search_page_reels()
            if not reels:
                logger.info("No new reels found.")
                break

            logger.info(f"New reels: {len(reels)}")
            num_to_process = max(1, int(len(reels) * self.config["percent_reels_to_watch"]))
            to_process = random.sample(reels, num_to_process)

            for reel in to_process:
                logger.info(f"Selected reel [{reel['short_id']}] to process")
                self.process_reel(reel)
                self.actions += 1

                if self.actions >= next_idle_at:
                    idle_time = random.uniform(*self.config["idle_duration_range"])
                    logger.info(f"😴 Idle break for {idle_time:.2f}s")
                    time.sleep(idle_time)
                    self.actions = 0
                    next_idle_at = random.randint(*self.config["idle_after_actions"])

            self.random_delay("before_scroll")
            self.ui.scroll_up()

        logger.info(f"✅ Session complete. Total unique reels interacted: {len(self.seen_hashes)}")

    def extract_search_page_reels(self) -> List[Dict]:
        reels = []
        elements = self.d.xpath(f'//android.widget.FrameLayout[@resource-id="{self.config["package_name"]}:id/layout_container"]').all()
        logger.info(f"Found {len(elements)} layout containers")

        for el in elements:
            try:
                bounds = el.attrib.get("bounds", "")
                desc = el.attrib.get("content-desc", "reel")
                key = hashlib.sha1(bounds.encode("utf-8")).hexdigest()

                if key in self.seen_hashes:
                    continue

                self.seen_hashes.add(key)
                reels.append({
                    "id": key,
                    "short_id": key[:7],
                    "username": "unknown",
                    "type": "REEL",
                    "desc": desc,
                    "bounds": bounds
                })
            except Exception as e:
                logger.warning(f"Failed to parse reel container: {e}")
                continue

        return reels

    def navigate_to_explore(self) -> bool:
        explore_xpath = '//android.widget.FrameLayout[@content-desc="Search and explore"]'
        search_ready_xpath = f'//android.widget.EditText[@resource-id="{self.config["package_name"]}:id/action_bar_search_edit_text"]'

        logger.info("📍 Navigating to Explore page...")
        success = self.ui.tap_random_within_element(explore_xpath, label="Explore Tab")
        if not success:
            logger.warning("❌ Could not find Explore tab.")
            time.sleep(2)
            return False

        try:
            self.d.xpath(search_ready_xpath).wait(timeout=10.0)
            logger.info("✅ Explore page loaded.")
            return True
        except Exception:
            logger.warning("❌ Search bar not found after tapping Explore.")
            return False

    def perform_keyword_search(self, keyword: str) -> bool:
        logger.info(f"🔍 Performing keyword search: {keyword}")
        search_xpath = f'//*[@resource-id="{self.config["package_name"]}:id/action_bar_search_edit_text"]'
        posts_xpath = f'//*[@resource-id="{self.config["package_name"]}:id/title_text_view" and @text="Posts"]'
        typer = StealthTyper(device_id=self.d.serial)

        try:
            if not self.d.xpath(search_xpath).wait(timeout=10):
                logger.warning("❌ Search bar not found.")
                return False

            el = self.d.xpath(search_xpath).get(timeout=2.0)
            if not el:
                logger.warning("❌ Could not get reference to search bar element.")
                return False

            el.click()
            time.sleep(1)

            typer.type_text(keyword)
            typer.press_enter()
            logger.info("⏎ Enter pressed to start search.")
            time.sleep(2)

            self.d.swipe(540, 1300, 540, 900, 0.2)
            time.sleep(1.0)

            if not self.d.xpath(posts_xpath).wait(timeout=5.0):
                logger.error("❌ 'Posts' section not found after search. Can't continue.")
                return False

            logger.info("✅ 'Posts' section found — reels can now be extracted.")
            return True

        except Exception as e:
            logger.error(f"❌ Failed during keyword search flow: {e}")
            return False


    def process_reel(self, reel_post: Dict):
        full_watch_time = random.uniform(2.0, 10.0)
        like_delay = random.uniform(1.2, full_watch_time - 0.5)
        sample_pool = [random.uniform(1.0, full_watch_time - 0.2) for _ in range(3)]
        num_interactions = min(len(sample_pool), random.randint(1, 2))
        interaction_times = sorted(random.sample(sample_pool, k=num_interactions))

        logger.info(f"⏱️ Watching reel for {full_watch_time:.2f}s (like at ~{like_delay:.2f}s)")
        start = time.time()
        liked = False

        max_tap_attempts = 2
        for attempt in range(max_tap_attempts):
            logger.info(f"👆 Tapping reel for {reel_post['short_id']} (attempt {attempt+1})")
            if not self.ui.smart_button_clicker("Reel by", timeout=4):
                self.random_delay("after_post_tap")
            else:
                break
        else:
            logger.warning("Reel UI did not load, skipping.")
            return

        # --- Optional: Extract metadata (same logic as before) ---
        def get_desc(query):
            if time.time() - start > full_watch_time:
                return None
            try:
                el = self.d.xpath(query).get(timeout=2.0)
                return el.attrib.get("content-desc", "") if el else None
            except Exception:
                return None

        def get_text(query):
            if time.time() - start > full_watch_time:
                return None
            try:
                el = self.d.xpath(query).get(timeout=2.0)
                return el.attrib.get("text", "") if el else None
            except Exception:
                return None

        username = get_desc('//android.widget.ImageView[contains(@content-desc, "Profile picture of")]')
        caption = get_desc(f'//android.view.ViewGroup[@resource-id="{self.config["package_name"]}:id/clips_caption_component"]//android.view.ViewGroup[contains(@content-desc, "")]')
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
                self.light_interaction()
                interaction_times.pop(0)

            if not liked and elapsed >= like_delay and random.random() < self.config["like_probability"]:
                logger.info("Liking this reel mid-watch...")
                success = self.ui.smart_button_clicker("Like")
                time.sleep(1)
                if success:
                    if self.is_reel_liked():
                        logger.info("👍 Reel successfully liked")
                        liked = True
                    else:
                        logger.warning("⚠️ Like button clicked but state not confirmed as 'liked'")
                else:
                    logger.warning("❌ Failed to click Like button")

            time.sleep(0.4)

        # Exit reel
        if self.ui.smart_button_clicker("Back"):
            time.sleep(1.5)
        else:
            logger.warning("Back button not found after reel watch")

        for _ in range(10):
            if not self.d.xpath('//*[@content-desc="Like"]').exists:
                logger.info("✅ Exited reel view")
                break
            time.sleep(0.5)
        else:
            logger.warning("⚠️ Still detected in reel UI after back, continuing anyway")



    def light_interaction(self):
        action = random.choice(["pause_resume_tap", "swipe_comments", "side_scrub", "comment_scroll"])
        logger.info(f"👆 Performing light interaction: {action}")

        if action == "pause_resume_tap":
            x = random.randint(300, 800)
            y = random.randint(800, 1200)
            self.d.click(x, y)

        elif action == "swipe_comments":
            self.d.swipe(540, 1000, 540, 1300, 0.1)

        elif action == "side_scrub":
            x = random.randint(400, 700)
            y = random.randint(1000, 1300)
            self.d.swipe(x, y, x + random.randint(-50, 50), y, 0.1)

        elif action == "comment_scroll":
            logger.info("🗨️ Opening comments via comment button...")
            success = self.ui.tap_random_within_element('//android.widget.ImageView[@content-desc="Comment"]', label="Comment Button")
            if success:
                time.sleep(random.uniform(1.2, 2.0))
                self.d.swipe(540, 1600, 540, 1000, 0.2)
                time.sleep(random.uniform(1.5, 2.5))
                self.d.press("back")

    def random_delay(self, label: str):
        lo, hi = self.config["delays"].get(label, (1, 2))
        t = random.uniform(lo, hi)
        logger.debug(f"Sleeping {t:.2f}s ({label})")
        time.sleep(t)

    def is_reel_liked(self) -> bool:
        try:
            like_btn = self.d.xpath('//*[@resource-id="com.instagram.androie:id/like_button"]').get(timeout=2.0)
            selected = like_btn.attrib.get("selected")
            return selected == "true"
        except Exception as e:
            logger.warning(f"Could not determine like status: {e}")
            return False

def main():
    d = u2.connect()
    ui = UIHelper(d)

    # Allow overriding config params if needed
    config = CONFIG.copy()
    config["percent_reels_to_watch"] = 0.25  # override watch %
    config["like_probability"] = 0.65        # override like %

    logger.info("🚀 Starting Instagram reel scroller session...")
    scroller = ReelScroller(device=d, ui_helper=ui, config=config)

    if not scroller.navigate_to_explore():
        logger.error("❌ Failed to open Explore page. Aborting.")
        return

    if not scroller.perform_keyword_search("model"):
        logger.error("❌ Keyword search failed. Aborting.")
        return

    scroller.run()

if __name__ == "__main__":
    main()

