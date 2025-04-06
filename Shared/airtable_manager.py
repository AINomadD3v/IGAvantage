# airtable_management.py

import os
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from pyairtable import Api
from .logger_config import setup_logger

logger = setup_logger(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class AirtableClient:
    def __init__(self, table_key: str = "content_alexis"):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        if not self.api_key:
            raise ValueError("Missing AIRTABLE_API_KEY in environment variables")

        table_map = {
            "content_alexis": {
                "base_id": os.getenv("ALEXIS_BASE_ID"),
                "table_id": os.getenv("ALEXIS_CONTENT_TABLE_ID"),
                "view": "Unposted"
            },
            "content_maddison": {
                "base_id": os.getenv("MADDISON_BASE_ID"),
                "table_id": os.getenv("MADDISON_CONTENT_TABLE_ID"),
                "view": "Unposted"
            },
            "warmup_accounts": {
                "base_id": os.getenv("IG_ARMY_BASE_ID"),
                "table_id": os.getenv("IG_ARMY_WARMUP_ACCOUNTS_TABLE_ID"),
                "view": "Warmup"
            }
        }

        if table_key not in table_map:
            raise ValueError(f"Unsupported table key: '{table_key}'")

        config = table_map[table_key]
        self.base_id = config["base_id"]
        self.table_id = config["table_id"]
        self.view_name = config["view"]

        if not all([self.base_id, self.table_id, self.view_name]):
            raise ValueError(f"Missing required environment variables for table key: '{table_key}'")

        self.api = Api(self.api_key)

    

    def get_unposted_records_for_today(self, max_count: int = 1):
        try:
            logger.info(f"📥 Fetching up to {max_count} unposted records for today...")

            table = self.api.table(self.base_id, self.table_id)
            records = table.all(view=self.view_name)

            bogota = pytz.timezone("America/Bogota")
            today_str = datetime.now(bogota).strftime("%Y-%m-%d")  # e.g., '2025-04-05'

            matching = []

            for record in records:
                fields = record.get("fields", {})
                schedule_raw = fields.get("Schedule Date")
                if not schedule_raw:
                    continue

                # Airtable returns ISO format like '2025-04-06T00:00:00.000Z'
                scheduled_date = schedule_raw.split("T")[0]  # Just the 'YYYY-MM-DD' part

                if scheduled_date != today_str:
                    continue

                username = fields.get("Username")
                media_url = fields.get("Drive URL")
                raw_package = fields.get("Package Name")
                package_name = raw_package[0] if isinstance(raw_package, list) and raw_package else raw_package

                matching.append({
                    "id": record["id"],
                    "fields": {
                        "username": username,
                        "package_name": package_name,
                        "media_url": media_url
                    }
                })

                if len(matching) >= max_count:
                    break

            return matching

        except Exception as e:
            logger.error(f"❌ Error fetching multiple unposted records: {e}", exc_info=True)
            return []

    def mark_something_went_wrong_and_rotate(self, record_id: str):
        """
        Marks 'Something Went Wrong?' = True in Airtable, logs it, and returns a signal to rotate account.
        """
        try:
            self.update_record_fields(record_id, {'Something Went Wrong': True})
            logger.warning(f"⚠️ Marked record {record_id} as 'Something Went Wrong' = True")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to mark record {record_id} with 'Something Went Wrong': {e}")
            return False

    def update_record_fields(self, record_id: str, fields: dict):
        """
        Update arbitrary fields in Airtable record.
        """
        try:
            table = self.api.table(self.base_id, self.table_id)
            result = table.update(record_id, fields, typecast=True)
            logger.debug(f"✅ Updated record {record_id} with fields: {fields}")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to update record: {e}")
            return None

    def get_single_active_account(self, base_id, table_name, unused_view_id):
        try:
            logger.info("Attempting to fetch active account...")
            table = self.api.table(base_id, table_name)

            fields = ['Account', 'Password', 'Email', 'Email Password', 'Package Name']
            records = table.all(view=unused_view_id, fields=fields, max_records=1)

            if not records:
                logger.warning("⚠️ No active accounts found in view")
                return None

            record = records[0]
            record_id = record.get('id')
            record_fields = record.get('fields', {})

            raw_package = record_fields.get('Package Name')
            record_fields['Package Name'] = raw_package[0] if isinstance(raw_package, list) and raw_package else None

            logger.info("✅ Active account found:")
            logger.info(f"  Account: {record_fields.get('Account')}")
            logger.info(f"  Package Name: {record_fields.get('Package Name')}")
            return {
                'id': record_id,
                'fields': record_fields
            }

        except requests.exceptions.RequestException as api_error:
            logger.error(f"API request failed: {str(api_error)}")
            return None
        except Exception as e:
            logger.error(f"Error in get_single_active_account: {str(e)}")
            return None

    def update_record(self, base_id, table_name, record_id, fields):
        try:
            table = self.api.table(base_id, table_name)
            updated_record = table.update(record_id, fields)
            logger.info(f"✅ Updated Airtable record {record_id}: {fields}")
            return updated_record
        except Exception as e:
            logger.error(f"❌ Failed to update Airtable record: {e}")
            return None

    def get_pending_warmup_records(self, max_count=None):
        """
        Fetch records that are in 'Warmup' status and not yet marked complete.
        """
        table = self.api.table(self.base_id, self.table_id)
        records = table.all(view="Warmup")

        result = []
        for record in records:
            fields = record.get("fields", {})
            if fields.get("Status") != "Warmup":
                continue
            if fields.get("Daily Warmup Complete") is True:
                continue

            def flatten(value):
                if isinstance(value, list) and value:
                    return value[0]
                return value

            result.append({
                "record_id": record["id"],
                "username": flatten(fields.get("Username")),
                "device_id": flatten(fields.get("Device ID")),
                "package_name": flatten(fields.get("Package Name")),
            })

            if max_count and len(result) >= max_count:
                break

        return result


if __name__ == "__main__":
    from pprint import pprint

    client = AirtableClient(table_key="warmup_accounts")  # model_name not needed anymore
    warmup_records = client.get_pending_warmup_records()

    print(f"🔍 Found {len(warmup_records)} warmup records pending:")
    for record in warmup_records:
        pprint(record)

