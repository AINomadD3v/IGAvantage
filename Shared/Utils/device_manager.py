# UploadBot/device_manager.py

import os
import re
import subprocess
import time
from typing import Optional, Tuple

from Shared.logger_config import setup_logger

# Assuming uiautomator2 device object might be needed for serial, import if necessary
# import uiautomator2 as u2


# Setup loggers for each class or a general module logger
logger_fm = setup_logger(name="DeviceFileManager")
logger_mc = setup_logger(name="MediaCleaner")

# --- Helper Function for ADB Commands ---
# Moved into the class that uses it, or could be a standalone utility
# def run_adb_command(command_list: list[str]) -> Optional[str]:
#     """Runs an ADB command list and returns stdout or None on error."""
#     # Add device serial if needed: cmd.insert(1, "-s") cmd.insert(2, device_id)
#     logger_fm.debug(f"Running ADB command: {' '.join(command_list)}")
#     result = subprocess.run(command_list, capture_output=True, text=True, check=False) # check=False to handle errors manually
#     if result.returncode != 0:
#         logger_fm.error(f"ADB command failed: {result.stderr.strip()}")
#         return None
#     logger_fm.debug(f"ADB command output: {result.stdout.strip()}")
#     return result.stdout.strip()


class DeviceFileManager:
    """Handles file operations on the Android device via ADB."""

    def __init__(self, device_serial: Optional[str] = None):
        """
        Initializes the DeviceFileManager.

        Args:
            device_serial (Optional[str]): The specific device serial ID to target.
                                           If None, ADB commands target the default/only connected device.
        """
        self.device_serial = device_serial
        self.logger = logger_fm  # Use the specific logger

    def _run_adb_command(self, command_list: list[str]) -> Optional[str]:
        """
        Internal helper to run an ADB command list, targeting the specific device if set.

        Args:
            command_list (list[str]): The ADB command and arguments as a list.

        Returns:
            Optional[str]: The stdout of the command, or None on error.
        """
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(
            command_list[1:]
        )  # Add the rest of the command skipping the initial 'adb'

        self.logger.debug(f"Running ADB command: {' '.join(cmd)}")
        try:
            # Using check=False and handling potential errors
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )  # Added timeout
            if result.returncode != 0:
                self.logger.error(
                    f"ADB command failed (code {result.returncode}): {result.stderr.strip()}"
                )
                return None
            self.logger.debug(f"ADB command output: {result.stdout.strip()}")
            return result.stdout.strip()
        except FileNotFoundError:
            self.logger.error(
                "❌ ADB command not found. Ensure ADB is installed and in your PATH."
            )
            return None
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ ADB command timed out: {' '.join(cmd)}")
            return None
        except Exception as e:
            self.logger.error(
                f"❌ Unexpected error running ADB command: {e}", exc_info=True
            )
            return None

    def push_media_to_device(
        self, local_file_path: str, account_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Pushes a local media file to a structured directory on the device via ADB
        and triggers media scans.

        Args:
            local_file_path (str): The path to the local file to push.
            account_name (str): The username associated with the content, used for directory naming.
            # device: The uiautomator2 device object is no longer needed here directly,
            #         but the serial ID should be passed during __init__.

        Returns:
            Tuple[bool, Optional[str]]: (Success status, Remote path on device or None).
        """
        try:
            if not os.path.exists(local_file_path):
                self.logger.error(f"Local file does not exist: {local_file_path}")
                return False, None

            # --- Determine Remote Path ---
            ext = os.path.splitext(local_file_path)[-1]
            # Sanitize account_name for directory use if necessary (replace spaces, special chars)
            dir_name = re.sub(r"[^\w\-]+", "_", account_name)  # Example sanitization
            remote_file_name = f"{dir_name}_{int(time.time())}{ext}"
            # Consider making base remote dir configurable
            remote_dir = f"/sdcard/Pictures/{dir_name}"
            remote_path = f"{remote_dir}/{remote_file_name}"
            self.logger.info(f"Target remote path: {remote_path}")

            # --- Create Remote Directory ---
            self.logger.debug(f"Ensuring remote directory exists: {remote_dir}")
            # Use _run_adb_command helper
            mkdir_result = self._run_adb_command(
                ["adb", "shell", "mkdir", "-p", remote_dir]
            )
            # mkdir command doesn't produce useful stdout on success, check error
            if mkdir_result is None and not self._check_if_dir_exists(
                remote_dir
            ):  # Check if dir exists if command seemed to fail
                self.logger.error(f"Failed to create remote directory: {remote_dir}")
                return False, None

            # --- Push File ---
            self.logger.info(f"Pushing '{local_file_path}' to '{remote_path}'...")
            push_result = self._run_adb_command(
                ["adb", "push", local_file_path, remote_path]
            )
            # ADB push provides output on success/failure in stdout/stderr, check return value
            if push_result is None:
                self.logger.error(f"ADB push failed for {local_file_path}")
                return False, None
            self.logger.info(f"📤 File pushed successfully to: {remote_path}")

            # --- Trigger Media Scan ---
            self.trigger_media_scan(remote_path)

            return True, remote_path

        except Exception as e:
            self.logger.error(f"Push to device failed: {e}", exc_info=True)
            return False, None

    def _check_if_dir_exists(self, remote_dir: str) -> bool:
        """Checks if a directory exists on the device using ADB."""
        check_cmd = ["adb", "shell", f"[ -d '{remote_dir}' ] && echo exists"]
        result = self._run_adb_command(check_cmd)
        return result == "exists"

    def trigger_media_scan(self, remote_file_path: Optional[str] = None):
        """
        Triggers media scanner on the device using multiple strategies.

        Args:
            remote_file_path (Optional[str]): Specific file path to scan. If None, scans common volumes.
        """
        self.logger.info(
            f"📣 Triggering media scan (for path: {remote_file_path or 'common volumes'})..."
        )
        scan_cmds = []
        # Specific file scan (if path provided)
        if remote_file_path:
            scan_cmds.append(
                [
                    "adb",
                    "shell",
                    "am",
                    "broadcast",
                    "-a",
                    "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                    "-d",
                    f"file://{remote_file_path}",
                ]
            )

        # General volume scans (always useful)
        scan_cmds.extend(
            [
                [
                    "adb",
                    "shell",
                    "cmd",
                    "media",
                    "scan",
                    "/sdcard/Pictures",
                ],  # Scan Pictures folder
                [
                    "adb",
                    "shell",
                    "cmd",
                    "media",
                    "scan",
                    "/sdcard/DCIM",
                ],  # Scan DCIM folder often helps
                # ["adb", "shell", "content", "call", "--method", "scan_volume", "--uri", "content://media", "--arg", "external_primary"] # Modern scan
            ]
        )

        for cmd_list in scan_cmds:
            self.logger.debug(f"Running scan command: {' '.join(cmd_list)}")
            self._run_adb_command(
                cmd_list
            )  # Run command, ignore output unless debugging needed

        self.logger.info("Media scan commands sent.")


class MediaCleaner:
    """Handles deleting media files/albums on the Android device via ADB."""

    def __init__(self, device_serial: Optional[str] = None):
        """
        Initializes the MediaCleaner.

        Args:
            device_serial (Optional[str]): The specific device serial ID to target.
        """
        self.device_serial = device_serial
        self.logger = logger_mc  # Use the specific logger

    def _run_adb_command(self, command_list: list[str]) -> Optional[str]:
        """Internal helper to run ADB commands, specific to MediaCleaner."""
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(command_list[1:])

        self.logger.debug(f"Running ADB command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=60
            )  # Longer timeout for deletion
            if result.returncode != 0:
                self.logger.error(
                    f"ADB command failed (code {result.returncode}): {result.stderr.strip()}"
                )
                return None
            self.logger.debug(f"ADB command output: {result.stdout.strip()}")
            return result.stdout.strip()
        except FileNotFoundError:
            self.logger.error(
                "❌ ADB command not found. Ensure ADB is installed and in your PATH."
            )
            return None
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ ADB command timed out: {' '.join(cmd)}")
            return None
        except Exception as e:
            self.logger.error(
                f"❌ Unexpected error running ADB command: {e}", exc_info=True
            )
            return None

    def delete_album(self, album_path: str) -> bool:
        """Deletes an entire directory on the device."""
        self.logger.info(f"Attempting to delete album: {album_path}")
        # Use double quotes for paths with potential spaces, echo for confirmation
        cmd = ["adb", "shell", f'rm -rf "{album_path}" && echo DELETED']
        result = self._run_adb_command(cmd)
        # Check if the echo confirmation is present
        if result and "DELETED" in result:
            self.logger.info(f"✅ Successfully deleted album: {album_path}")
            return True
        else:
            self.logger.error(
                f"❌ Failed to delete album or confirm deletion: {album_path}"
            )
            return False

    def clean_posted_media(self, album_path: str) -> bool:
        """High-level method to clean up a specific album after posting."""
        self.logger.info(f"Cleaning posted media in album: {album_path}")
        return self.delete_album(album_path)

    def clean_all_media(self) -> bool:
        """Deletes common media file types from standard DCIM and Pictures folders."""
        self.logger.warning(
            "Attempting to delete ALL common media files from DCIM and Pictures..."
        )
        # Careful with this command! Ensure paths and types are correct.
        # Using single quotes inside the shell command for robustness
        find_cmd = r'find /sdcard \( -path "/sdcard/DCIM/*" -o -path "/sdcard/Pictures/*" \) -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" \) -delete && echo DELETED_ALL'
        cmd = ["adb", "shell", find_cmd]
        result = self._run_adb_command(cmd)
        if result and "DELETED_ALL" in result:
            self.logger.info(
                "✅ Successfully deleted common media files from DCIM/Pictures."
            )
            return True
        else:
            self.logger.error(
                "❌ Failed to delete all common media files or confirm deletion."
            )
            return False
