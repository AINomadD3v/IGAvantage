# airtable_management.py

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from pyairtable import Api
from .logger_config import setup_logger

logger = setup_logger(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class AirtableClient:
    def __init__(self, model_name: str = "alexis"):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        
        model_map = {
            "alexis": {
                "base_id": os.getenv("ALEXIS_BASE_ID"),
                "table_id": os.getenv("ALEXIS_CONTENT_TABLE_ID")
            },
            "maddison": {
                "base_id": os.getenv("MADDISON_BASE_ID"),
                "table_id": os.getenv("MADDISON_CONTENT_TABLE_ID")
            }
        }

        if model_name not in model_map:
            raise ValueError(f"Unsupported model name: {model_name}")
        
        model_config = model_map[model_name]
        self.base_id = model_config["base_id"]
        self.table_id = model_config["table_id"]
        self.view_name = "Unposted"

        if not all([self.api_key, self.base_id, self.table_id]):
            raise ValueError("Missing required environment variables")

        self.api = Api(self.api_key)

    # --------- Posting System (from airtable_client.py) --------- #
    def get_single_unposted_record(self):
        """
        Pull a single unposted record from Airtable with required fields,
        where 'Schedule Date' matches today's date.
        """
        try:
            logger.info("Fetching a single unposted record...")
            table = self.api.table(self.base_id, self.table_id)

            fields = [
                'Username', 'Package Name',
                'Drive URL', 'Schedule Date'
            ]

            records = table.all(view=self.view_name, fields=fields)

            if not records:
                logger.warning("No unposted records found.")
                return None

            today = datetime.today().date()
            logger.info(f"📅 Looking for records with Schedule Date = {today.isoformat()}")

            for record in records:
                data = record.get("fields", {})
                username = data.get("Username")
                schedule_raw = data.get("Schedule Date")

                logger.debug(f"👀 Checking record: {username} | Schedule Date raw: {schedule_raw}")

                if not schedule_raw:
                    logger.debug("⏭️ Skipping — no schedule date")
                    continue

                try:
                    scheduled_date = datetime.fromisoformat(schedule_raw).date()
                except ValueError:
                    logger.warning(f"⚠️ Could not parse date: {schedule_raw}")
                    continue

                if scheduled_date != today:
                    logger.debug(f"⏭️ Skipping — not scheduled for today ({scheduled_date} != {today})")
                    continue

                record_id = record.get("id")
                raw_package = data.get("Package Name")
                package_name = raw_package[0] if isinstance(raw_package, list) and raw_package else raw_package

                logger.info(f"✅ Matched: {username} scheduled for {schedule_raw}")

                return {
                    "id": record_id,
                    "fields": {
                        "username": username,
                        "package_name": package_name,
                        "media_url": data.get("Drive URL"),
                    },
                }

            logger.warning("⚠️ No matching records with today's schedule date.")
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching unposted record: {e}", exc_info=True)
            return None


    def mark_something_went_wrong_and_rotate(self, record_id: str):
        """
        Marks 'Something Went Wrong?' = True in Airtable, logs it, and returns a signal to rotate account.
        """
        try:
            self.update_record_fields(record_id, {'Something Went Wrong?': True})
            logger.warning(f"⚠️ Marked record {record_id} as 'Something Went Wrong?' = True")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to mark record {record_id} with 'Something Went Wrong?': {e}")
            return False

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

    # --------- Account Rotation System (from original airtable_management.py) --------- #
    def get_table_records(self, base_id, table_name):
        try:
            table = self.api.table(base_id, table_name)
            return table.all()
        except Exception as e:
            logger.error(f"Error fetching records: {str(e)}")
            return []

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


# Optional test function
def main():
    client = AirtableClient()
    logger.info("Testing AirtableClient...")

    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_id = os.getenv('IG_ARMY_ACCOUNTS_TABLE_ID')
    unused_view_id = os.getenv('IG_ARMY_UNUSED_VIEW_ID')

    if not base_id or not table_id:
        logger.error("Missing base/table IDs for test")
        return

    account = client.get_single_active_account(base_id, table_id, unused_view_id)
    if account:
        logger.info("✅ Account retrieved successfully")


if __name__ == "__main__":
    main()

