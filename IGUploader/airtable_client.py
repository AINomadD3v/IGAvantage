# airtable_client.py

import os
from pyairtable import Api
from dotenv import load_dotenv
from logger_config import setup_logger

load_dotenv()
logger = setup_logger(__name__)

class AirtableClient:
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        self.base_id = os.getenv('ALEXIS_BASE_ID')
        self.table_id = os.getenv('ALEXIS_CONTENT_TABLE_ID')
        self.view_name = "Unposted"

        if not all([self.api_key, self.base_id, self.table_id]):
            raise ValueError("Missing required environment variables")

        self.api = Api(self.api_key)

    def get_single_unposted_record(self):
        """
        Pull a single unposted record from Airtable with required fields.
        """
        try:
            logger.info("Fetching a single unposted record...")
            table = self.api.table(self.base_id, self.table_id)

            fields = [
                'Username', 'Package Name', 'Caption',
                'Drive URL', 'Song'
            ]

            records = table.all(view=self.view_name, fields=fields, max_records=1)

            if not records:
                logger.warning("No unposted records found.")
                return None

            record = records[0]
            data = record.get('fields', {})
            record_id = record.get('id')

            # Safely extract package name (lookup field)
            raw_package = data.get('Package Name')
            if isinstance(raw_package, list):
                package_name = raw_package[0] if raw_package else None
            else:
                package_name = raw_package

            logger.info(f"✅ Pulled record for: {data.get('Username')}")

            return {
                'id': record_id,
                'fields': {
                    'username': data.get('Username'),
                    'package_name': package_name,
                    'caption': data.get('Caption'),
                    'media_url': data.get('Drive URL'),
                    'song': data.get('Song'),
                }
            }

        except Exception as e:
            logger.error(f"Error fetching unposted record: {e}")
            return None

    def update_record_fields(self, record_id: str, fields: dict):
        """
        Update arbitrary fields in Airtable record.
        """
        try:
            table = self.api.table(self.base_id, self.table_id)
            result = table.update(record_id, fields, typecast=True)
            logger.info(f"✅ Updated record {record_id} with fields: {fields}")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to update record: {e}")
            return None
