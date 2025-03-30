import uiautomator2 as u2
import time

def test_dismiss_about_reels_popup():
    print("🔗 Connecting to device...")
    d = u2.connect()

    print("🔍 Looking for 'About Reels' popup...")
    if d.xpath("About Reels").exists:
        print("✅ 'About Reels' text found")
        time.sleep(0.5)

        share_btn = d.xpath("Share")
        if share_btn.exists:
            print("📤 'Share' button found — clicking...")
            if share_btn.click_exists(timeout=3):
                print("✅ Clicked 'Share' button successfully")
            else:
                print("❌ Failed to click 'Share' button")
        else:
            print("❌ 'Share' button not found")
    else:
        print("ℹ️ 'About Reels' popup not present")

if __name__ == "__main__":
    test_dismiss_about_reels_popup()

