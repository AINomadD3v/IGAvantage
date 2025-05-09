import io
import os
import pickle
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from Shared.logger_config import setup_logger

logger = setup_logger(name="ContentManager")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class ContentManager:
    def __init__(
        self,
        credentials_path: str = "UploadBot/credentials.json",
        token_path: str = "token.pickle",
    ):
        self.logger = setup_logger(self.__class__.__name__)
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.drive_service = self._authenticate_google_drive()

    def _authenticate_google_drive(self):
        creds = None

        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                with open(self.token_path, "wb") as token:
                    pickle.dump(creds, token)

        return build("drive", "v3", credentials=creds)

    def extract_file_id(self, drive_url: str) -> Optional[str]:
        patterns = [
            r"/open\?id=([a-zA-Z0-9_-]+)",
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, drive_url)
            if match:
                return match.group(1)
        return None

    def detect_file_extension(self, file_metadata: dict, url: str) -> str:
        name = file_metadata.get("name", "")
        if "." in name:
            return "." + name.split(".")[-1].lower()

        mime_type = file_metadata.get("mimeType", "")
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
        }
        return mime_to_ext.get(mime_type, ".mp4")

    def download_drive_file(
        self, drive_url: str, output_folder: str
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        file_id = self.extract_file_id(drive_url)
        if not file_id:
            return False, None, None, None

        try:
            file_metadata = self.drive_service.files().get(fileId=file_id).execute()
            extension = self.detect_file_extension(file_metadata, drive_url)

            Path(output_folder).mkdir(parents=True, exist_ok=True)
            original_name = Path(file_metadata["name"]).stem
            output_path = os.path.join(output_folder, f"{original_name}{extension}")

            request = self.drive_service.files().get_media(fileId=file_id)
            with io.FileIO(output_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            mime_type = file_metadata.get("mimeType", None)
            return True, output_path, mime_type, file_id

        except Exception as e:
            self.logger.error(f"Failed to download from Drive: {e}", exc_info=True)
            return False, None, None, None
