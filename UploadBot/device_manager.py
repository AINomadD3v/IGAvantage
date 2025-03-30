# device_manager.py

import time
import logging
import subprocess
from typing import List 
import uiautomator2 as u2
from xpath_config import InstagramXPaths
from instagram_actions import InstagramInteractions
from logger_config import setup_logger

logger = setup_logger(__name__)

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


class InstagramCore:
    def __init__(self, airtable_manager):
        self.logger = setup_logger(self.__class__.__name__)
        self.device = None
        self.xpath_config = None
        self.app_package = "com.instagram.android"  # Default package name
        self.airtable_manager = airtable_manager
        self.interactions = None

    def connect_to_device(self, device_id):
        try:
            self.device = u2.connect(device_id)
            if self.app_package:
                self.xpath_config = InstagramXPaths(self.app_package)
            else:
                logging.warning("app_package is None. XPath config not initialized.")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to device {device_id}: {e}")
            return False

    def open_instagram_app(self, package_name="com.instagram.android", max_attempts=5):
        if not self.device:
            logging.error("No device connected. Please connect to a device first.")
            return False

        self.app_package = package_name
        self.xpath_config = InstagramXPaths(package_name)

        if self.interactions is None:
            self.interactions = InstagramInteractions(self.device, package_name, self.airtable_manager)
        else:
            self.interactions.app_package = package_name
            self.interactions.xpath_config = self.xpath_config

        for attempt in range(max_attempts):
            logging.info(f"Attempt {attempt + 1} to open Instagram app with package name: {package_name}")
            self.device.app_start(package_name)

            time.sleep(3)  # Wait for 3 seconds after opening the app

            try:
                account_name = self.interactions.get_account_name()
                if account_name:
                    logging.info(f"Successfully opened Instagram app. Logged in as: {account_name}")
                    return True
            except ValueError:
                logging.info("Couldn't get account name, checking for TOS popup")

            # Modified TOS popup handling
            try:
                # Log the XPath we're using for debugging
                logging.debug(f"Checking for TOS popup with XPath: {self.xpath_config.tos_popup}")
                
                # Use exists() method directly on the XPath selector
                tos_exists = self.device(xpath=self.xpath_config.tos_popup).exists(timeout=2)
                
                if tos_exists:
                    logging.info("TOS popup found. App is open but not logged in.")
                    return True
                else:
                    logging.debug("TOS popup not found")

            except Exception as e:
                logging.warning(f"Error during TOS popup check: {str(e)}")
                logging.debug(f"Exception details: {type(e).__name__}")
                # Continue with the next attempt rather than failing immediately

            logging.warning("Failed to confirm app state. Retrying...")

        logging.error(f"Failed to open and confirm Instagram app after {max_attempts} attempts.")
        return False

    
class MediaCleaner:
    def __init__(self):
        pass

    def run_adb_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"ADB command failed: {result.stderr}")
            return None
        return result.stdout.strip()

    def delete_album(self, album_path):
        cmd = ['adb', 'shell', f'rm -rf "{album_path}" && echo "DELETED"']
        
        result = self.run_adb_command(cmd)
        if result and "DELETED" in result:
            logging.info(f"Successfully deleted album: {album_path}")
            return True
        else:
            logging.error(f"Failed to delete album: {album_path}")
            return False

    def clean_posted_media(self, album_path):
        if self.delete_album(album_path):
            return True
        else:
            logging.error(f"Failed to clean up posted media in '{album_path}'. Please check the device connection and try again.")
            return False

    def clean_all_media(self):
        cmd = ['adb', 'shell', r'find /sdcard \( -path "*/DCIM/*" -o -path "*/Pictures/*" \) -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.mp4" \) -delete && echo "DELETED"'] 
        result = self.run_adb_command(cmd)
        if result and "DELETED" in result:
            logging.info(f"Successfully deleted media files:")
            return True
        else:
            logging.error(f"Failed to delete media files in:")
            return False
