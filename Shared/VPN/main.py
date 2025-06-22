import re
import time

from uiautomator2 import UiObjectNotFoundError


def extract_ip_number(content_desc: str) -> str:
    """
    Extract the #number from content-desc string like:
    "Connected to: United States, Miami #11513"
    Returns the number as string, or empty string if not found.
    """
    match = re.search(r"#(\d+)", content_desc)
    if match:
        return match.group(1)
    return ""


def main_flow(d):
    PACKAGE_NAME = "com.nordvpn.android"

    print(f"🚀 Launching {PACKAGE_NAME}")
    d.app_start(PACKAGE_NAME)
    time.sleep(3)  # allow app to stabilize

    # Based on the selected element, we search for android.view.View with content-desc starting with "Connected to:"
    xpath_connected = '//android.view.View[starts-with(@content-desc, "Connected to:")]'
    print("⏳ Waiting for VPN connection status view via XPath...")
    if not d.xpath(xpath_connected).wait(timeout=10):
        raise RuntimeError("❌ Could not find VPN connection status view in time.")

    status_view = d.xpath(xpath_connected)
    content_desc_before = status_view.info.get("contentDescription", "")
    if not content_desc_before.startswith("Connected to:"):
        raise RuntimeError(f"❌ Unexpected VPN status: '{content_desc_before}'")

    ip_before = extract_ip_number(content_desc_before)
    print(f"Current IP identifier before rotate: #{ip_before}")

    reconnect_btn = d(resourceId="connection_card_reconnect_button")
    if not reconnect_btn.wait(timeout=5):
        raise RuntimeError("❌ Reconnect button not found. UI may have changed.")

    reconnect_btn.click()
    print("🔄 Reconnect (rotate IP) button clicked. Waiting for IP to rotate...")

    time.sleep(7)  # wait for IP to rotate

    # Re-query the status view to get fresh content-desc with updated IP
    if not d.xpath(xpath_connected).wait(timeout=5):
        raise RuntimeError("❌ VPN connection status view disappeared after reconnect.")

    status_view = d.xpath(xpath_connected)
    content_desc_after = status_view.info.get("contentDescription", "")
    ip_after = extract_ip_number(content_desc_after)
    print(f"Current IP identifier after rotate: #{ip_after}")

    if ip_before == "" or ip_after == "":
        raise RuntimeError("❌ Could not extract IP number before or after rotation.")

    if ip_before == ip_after:
        raise RuntimeError(
            "❌ IP did NOT rotate: same number before and after reconnect."
        )
    else:
        print(f"✅ IP rotated successfully from #{ip_before} to #{ip_after}.")

    # Close the VPN app gracefully
    print(f"📴 Closing {PACKAGE_NAME} app...")
    d.app_stop(PACKAGE_NAME)
    print(f"✅ {PACKAGE_NAME} app closed.")


def main():
    import uiautomator2 as u2

    d = u2.connect()
    print("✅ Connected to device")

    try:
        main_flow(d)
    except UiObjectNotFoundError as e:
        print(f"❌ UI element not found: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
