import os
from pathlib import Path
import pickle
import io
import time
import subprocess
import re
from pathlib import Path
from typing import Tuple, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from Shared.logger_config import setup_logger

logger = setup_logger(name='ContentManager')

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class ContentManager:
    def __init__(self, credentials_path: str = 'UploadBot/credentials.json', token_path: str = 'token.pickle'):
        self.logger = setup_logger(self.__class__.__name__)
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.drive_service = self._authenticate_google_drive()

    def _authenticate_google_drive(self):
        creds = None

        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)


    def extract_file_id(self, drive_url: str) -> Optional[str]:
        patterns = [
            r'/open\?id=([a-zA-Z0-9_-]+)',
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, drive_url)
            if match:
                return match.group(1)
        return None

    def detect_file_extension(self, file_metadata: dict, url: str) -> str:
        name = file_metadata.get('name', '')
        if '.' in name:
            return '.' + name.split('.')[-1].lower()

        mime_type = file_metadata.get('mimeType', '')
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav'
        }
        return mime_to_ext.get(mime_type, '.mp4')

    def download_drive_file(self, drive_url: str, output_folder: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        file_id = self.extract_file_id(drive_url)
        if not file_id:
            return False, None, None, None

        try:
            file_metadata = self.drive_service.files().get(fileId=file_id).execute()
            extension = self.detect_file_extension(file_metadata, drive_url)

            Path(output_folder).mkdir(parents=True, exist_ok=True)
            original_name = Path(file_metadata['name']).stem
            output_path = os.path.join(output_folder, f"{original_name}{extension}")

            request = self.drive_service.files().get_media(fileId=file_id)
            with io.FileIO(output_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            mime_type = file_metadata.get('mimeType', None)
            return True, output_path, mime_type, file_id

        except Exception as e:
            self.logger.error(f"Failed to download from Drive: {e}", exc_info=True)
            return False, None, None, None


    def push_media_to_device(self, file_path: str, account_name: str, media_type: str, device) -> Tuple[bool, Optional[str]]:
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Local file does not exist: {file_path}")
                return False, None

            ext = os.path.splitext(file_path)[-1]
            dir_name = account_name
            remote_file_name = f"{account_name}_{int(time.time())}{ext}"
            remote_dir = f"/sdcard/Pictures/{dir_name}"
            remote_path = f"{remote_dir}/{remote_file_name}"

            # Create remote directory
            subprocess.run(f"adb shell mkdir -p {remote_dir}", shell=True, check=True)

            # Push file
            result = subprocess.run(["adb", "push", file_path, remote_path], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"ADB push failed: {result.stderr}")
                return False, None
            self.logger.info(f"📤 File pushed to: {remote_path}")

            # Multi-strategy rescan for Samsung + Huawei
            scan_cmds = [
                # Legacy media scan (works on Samsung)
                f"adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remote_path}",
                # Full volume rescan (works better on Huawei)
                "adb shell cmd media scan /sdcard/Pictures",
                # Modern content scan (for Android 10+)
                "adb shell content call --method scan_volume --uri content://media --arg external_primary",
            ]

            for cmd in scan_cmds:
                scan_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                self.logger.info(f"📣 Media scan attempted: {cmd}")
                self.logger.debug(f"Scan output: {scan_result.stdout.strip()}")

            return True, remote_path

        except Exception as e:
            self.logger.error(f"Push to device failed: {e}", exc_info=True)
            return False, None



     
