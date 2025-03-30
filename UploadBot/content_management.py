import os
from pathlib import Path
import pickle
import io
import time
import hashlib
import subprocess
import re
from pathlib import Path
from typing import Tuple, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from Shared.logger_config import setup_logger

logger = setup_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class ContentManager:
    def __init__(self, credentials_path: str = 'config/credentials.json', token_path: str = 'token.pickle'):
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
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
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
            dir_name = account_name  # ✅ No media_type suffix
            remote_file_name = f"{account_name}_{int(time.time())}{ext}"
            remote_path = f"/sdcard/Pictures/{dir_name}/{remote_file_name}"

            # Create remote directory
            mkdir_cmd = f"adb shell mkdir -p /sdcard/Pictures/{dir_name}"
            subprocess.run(mkdir_cmd, shell=True, check=True)

            # Push file
            push_cmd = ['adb', 'push', file_path, remote_path]
            result = subprocess.run(push_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"ADB push failed: {result.stderr}")
                return False, None

            # ✅ Refresh specific file in media store
            refresh_cmd = f"adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remote_path}"
            subprocess.run(refresh_cmd, shell=True, check=True)
            self.logger.info(f"Media scanner broadcast sent for: {remote_path}")

            # Optional: confirm file exists
            verify_cmd = f"adb shell ls {remote_path}"
            verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if "No such file" in verify_result.stderr:
                self.logger.error(f"File not found on device after push: {remote_path}")
                return False, None

            self.logger.info(f"File pushed to: {remote_path}")
            return True, remote_path

        except Exception as e:
            self.logger.error(f"Push to device failed: {e}", exc_info=True)
            return False, None

     
