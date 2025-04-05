# device_manager.py

import logging
import subprocess
from Shared.logger_config import setup_logger

logger = setup_logger(name='DeviceManager')

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
