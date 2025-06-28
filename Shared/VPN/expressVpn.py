import time

import uiautomator2 as u2


def main_flow(d):
    d = u2.connect()
    # Start the app by clicking the main button
    # Start the app by package name
    d.app_start("com.expressvpn.vpn")
    time.sleep(5)  # wait for app to open
    # Check if connected by locating the IP address element using XPath
    ip_xpath = '//*[@resource-id="com.expressvpn.vpn:id/ipaddress_label"]'
    ip_element = d.xpath(ip_xpath)
    if not ip_element.exists:
        print("Not connected or IP address element not found.")
        return

    ip_before = ip_element.get_text()
    print(f"Current IP before refresh: {ip_before}")

    # Click the refresh button
    refresh_xpath = '//*[@resource-id="com.expressvpn.vpn:id/refresh_icon"]'
    refresh_element = d.xpath(refresh_xpath)
    if not refresh_element.exists:
        print("Refresh button not found.")
        return
    refresh_element.click()
    time.sleep(5)  # wait for refresh

    # Get the IP after refresh
    ip_after = ip_element.get_text()
    print(f"Current IP after refresh: {ip_after}")

    if ip_before != ip_after:
        print("IP refreshed successfully.")
        # Close the app
        d.app_stop("com.expressvpn.vpn")
        print("App closed.")
    else:
        print("IP did not change after refresh.")


# Call the main function to run the script.
def main():
    import uiautomator2 as u2

    d = u2.connect()
    print("✅ Connected to device")

    try:
        main_flow(d)
    except Exception as e:
        print(f"❌ Error: {e}")
