# airtable_manager.py

import os
from datetime import datetime

import pytz
import requests
from dotenv import load_dotenv
from pyairtable import Api

from Shared.Utils.logger_config import setup_logger

logger = setup_logger(__name__)

# --- Load dotenv from project root ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    raise RuntimeError(f"🚨 .env file not found at expected location: {dotenv_path}")


class AirtableClient:
    def __init__(self, table_key: str = None):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        if not self.api_key:
            raise ValueError("Missing AIRTABLE_API_KEY in environment variables")

        self.api = Api(self.api_key)

        # These can now be manually assigned later
        self.base_id = None
        self.table_id = None
        self.view_name = None

        if table_key:
            table_map = {
                "content_alexis": {
                    "base_id": os.getenv("ALEXIS_BASE_ID"),
                    "table_id": os.getenv("ALEXIS_CONTENT_TABLE_ID"),
                    "view": "Unposted",
                },
                "content_maddison": {
                    "base_id": os.getenv("MADDISON_BASE_ID"),
                    "table_id": os.getenv("MADDISON_CONTENT_TABLE_ID"),
                    "view": "Unposted",
                },
                "warmup_accounts": {
                    "base_id": os.getenv("IG_ARMY_BASE_ID"),
                    "table_id": os.getenv("IG_ARMY_WARMUP_ACCOUNTS_TABLE_ID"),
                    "view": "Warmup",
                },
            }

            if table_key not in table_map:
                raise ValueError(f"Unsupported table key: '{table_key}'")

            config = table_map[table_key]
            self.base_id = config["base_id"]
            self.table_id = config["table_id"]
            self.view_name = config["view"]

            if not all([self.base_id, self.table_id, self.view_name]):
                raise ValueError(
                    f"Missing required environment variables for table key: '{table_key}'"
                )

    def get_unposted_records_for_today(self, max_count: int = 1):
        try:
            logger.info(f"📥 Fetching up to {max_count} unposted records for today...")

            table = self.api.table(self.base_id, self.table_id)
            records = table.all(view=self.view_name)

            bogota = pytz.timezone("America/Bogota")
            today_str = datetime.now(bogota).strftime("%Y-%m-%d")

            matching = []

            for record in records:
                fields = record.get("fields", {})
                schedule_raw = fields.get("Schedule Date")
                if not schedule_raw:
                    continue

                scheduled_date = schedule_raw.split("T")[0]

                if scheduled_date != today_str:
                    continue

                username = fields.get("Username")
                media_url = fields.get("Drive URL")
                raw_package = fields.get("Package Name")
                package_name = (
                    raw_package[0]
                    if isinstance(raw_package, list) and raw_package
                    else raw_package
                )

                matching.append(
                    {
                        "id": record["id"],
                        "fields": {
                            "username": username,
                            "package_name": package_name,
                            "media_url": media_url,
                        },
                    }
                )

                if len(matching) >= max_count:
                    break

            return matching

        except Exception as e:
            logger.error(
                f"❌ Error fetching multiple unposted records: {e}", exc_info=True
            )
            return []

    def mark_something_went_wrong_and_rotate(self, record_id: str):
        """
        Marks 'Something Went Wrong?' = True in Airtable, logs it, and returns a signal to rotate account.
        """
        try:
            self.update_record_fields(record_id, {"Something Went Wrong": True})
            logger.warning(
                f"⚠️ Marked record {record_id} as 'Something Went Wrong' = True"
            )
            return True
        except Exception as e:
            logger.error(
                f"❌ Failed to mark record {record_id} with 'Something Went Wrong': {e}"
            )
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

    def get_single_active_account(self, base_id: str, table_id: str, view_id: str):
        """
        Fetches a single active account from the specified Airtable base/table/view.
        Returns record with normalized fields and IDs.
        """
        try:
            logger.info("📡 Fetching active IG account from Airtable")
            logger.info(f"🧾 Base: {base_id} | Table: {table_id} | View: {view_id}")

            table = self.api.table(base_id, table_id)
            fields = [
                "Account",
                "Password",
                "Email",
                "Email Password",
                "Package Name",
                "Device ID",
            ]

            records = table.all(view=view_id, fields=fields, max_records=1)

            if not records:
                logger.warning("⚠️ No active accounts found in view")
                return None

            record = records[0]
            record_id = record.get("id")
            record_fields = record.get("fields", {})

            # Normalize array fields
            record_fields["Package Name"] = (
                record_fields.get("Package Name", [None])[0]
                if isinstance(record_fields.get("Package Name"), list)
                else record_fields.get("Package Name")
            )
            record_fields["Device ID"] = (
                record_fields.get("Device ID", [None])[0]
                if isinstance(record_fields.get("Device ID"), list)
                else record_fields.get("Device ID")
            )

            logger.info("✅ Active IG account found:")
            logger.info(f"  - Account: {record_fields.get('Account')}")
            logger.info(f"  - Package: {record_fields.get('Package Name')}")
            logger.info(f"  - Device:  {record_fields.get('Device ID')}")

            return {
                "id": record_id,
                "fields": record_fields,
                "base_id": base_id,
                "table_id": table_id,
            }

        except requests.exceptions.RequestException as api_error:
            logger.error(f"❌ Airtable API request failed: {api_error}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
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

            result.append(
                {
                    "record_id": record["id"],
                    "username": flatten(fields.get("Username")),
                    "device_id": flatten(fields.get("Device ID")),
                    "package_name": flatten(fields.get("Package Name")),
                }
            )

            if max_count and len(result) >= max_count:
                break

        return result

    def get_warmup_credentials(self):
        """
        Fetches email credentials for a single account from the 'warmup_accounts' view.
        This is a specialized function for the verification script.
        """
        try:
            # Configuration for warmup accounts, loaded from environment variables
            base_id = os.getenv("IG_ARMY_BASE_ID")
            table_id = os.getenv("IG_ARMY_ACCS_TABLE_ID")

            if not all([base_id, table_id]):
                raise ValueError(
                    "Missing IG_ARMY_BASE_ID or IG_ARMY_ACCS_TABLE_ID in .env file"
                )

            logger.info(
                f"📡 Fetching warmup account credentials from Base: {base_id}, Table: {table_id}"
            )

            table = self.api.table(base_id, table_id)

            # Specify the only two fields we need for this operation
            fields_to_fetch = ["Email", "Email Password"]

            # Fetch the first available record from the specified view
            records = table.all(fields=fields_to_fetch, max_records=1)

            if not records:
                logger.warning(
                    "⚠️ No accounts found in the 'Warmup' view to fetch credentials from."
                )
                return None

            record_fields = records[0].get("fields", {})
            email_address = record_fields.get("Email")
            email_password = record_fields.get("Email Password")

            if not email_address or not email_password:
                logger.error(
                    f"❌ Record {records[0].get('id')} is missing the 'Email' or 'Email Password' field."
                )
                return None

            logger.info(f"✅ Found credentials for email: {email_address}")
            return {"email": email_address, "password": email_password}

        except Exception as e:
            logger.error(
                f"❌ An error occurred while fetching warmup account credentials: {e}",
                exc_info=True,
            )
            return None

    def get_warmup_credentials_bulk(self, limit: int = 10):
        """
        Fetches email credentials for multiple accounts from the 'warmup_accounts' view.

        Args:
            limit (int): The maximum number of accounts to fetch.

        Returns:
            list: A list of dictionaries, where each dictionary contains the
                  email and password for an account. Returns an empty list on error.
        """
        try:
            base_id = os.getenv("IG_ARMY_BASE_ID")
            table_id = os.getenv("IG_ARMY_ACCS_TABLE_ID")

            if not all([base_id, table_id]):
                raise ValueError(
                    "Missing IG_ARMY_BASE_ID or IG_ARMY_ACCS_TABLE_ID in .env file"
                )

            logger.info(
                f"📡 Fetching up to {limit} warmup account credentials from Base: {base_id}, Table: {table_id}"
            )

            table = self.api.table(base_id, table_id)
            fields_to_fetch = ["Email", "Email Password"]

            # Fetch multiple records up to the specified limit
            records = table.all(fields=fields_to_fetch, max_records=limit)

            if not records:
                logger.warning(
                    "⚠️ No accounts found in the 'Warmup' view to fetch credentials from."
                )
                return []

            credentials_list = []
            for record in records:
                record_fields = record.get("fields", {})
                email_address = record_fields.get("Email")
                email_password = record_fields.get("Email Password")

                if not email_address or not email_password:
                    logger.warning(
                        f"Skipping record {record.get('id')} due to missing 'Email' or 'Email Password' field."
                    )
                    continue

                credentials_list.append(
                    {"email": email_address, "password": email_password}
                )

            logger.info(f"✅ Found credentials for {len(credentials_list)} accounts.")
            return credentials_list

        except Exception as e:
            logger.error(
                f"❌ An error occurred while fetching bulk warmup account credentials: {e}",
                exc_info=True,
            )
            return []

    # --- NEW FUNCTION ---
    def fetch_unused_accounts(self, max_records: int = 5) -> list:
        """
        Fetches account credentials from the 'Unused Accounts' view.

        Args:
            max_records (int): The maximum number of accounts to fetch. Defaults to 5.

        Returns:
            list: A list of dictionaries, each containing the credentials for one account.
                  Returns an empty list if no accounts are found or an error occurs.
        """
        try:
            # Assumes the same Base and Table ID as the warmup accounts
            base_id = os.getenv("IG_ARMY_BASE_ID")
            table_id = os.getenv("IG_ARMY_ACCS_TABLE_ID")
            view_name = "Unused Accounts"

            if not all([base_id, table_id]):
                raise ValueError(
                    "Missing IG_ARMY_BASE_ID or IG_ARMY_ACCS_TABLE_ID in .env file"
                )

            logger.info(
                f"📡 Fetching up to {max_records} accounts from view '{view_name}'..."
            )
            logger.info(f"   Base: {base_id}, Table: {table_id}")

            table = self.api.table(base_id, table_id)
            fields_to_fetch = [
                "Account",
                "Password",
                "Email",
                "Email Password",
                "Package Name",
                "Device ID",
            ]

            records = table.all(
                view=view_name, fields=fields_to_fetch, max_records=max_records
            )

            if not records:
                logger.warning(f"⚠️ No accounts found in the '{view_name}' view.")
                return []

            accounts_list = []
            for record in records:
                record_fields = record.get("fields", {})

                # Extract all required credentials
                ig_username = record_fields.get("Account")
                ig_password = record_fields.get("Password")
                email_address = record_fields.get("Email")
                email_password = record_fields.get("Email Password")
                package_name = record_fields.get("Package Name")
                device_id = record_fields.get("Device ID")

                # Ensure all four fields are present before adding
                if not all([ig_username, ig_password, email_address, email_password]):
                    logger.warning(
                        f"Skipping record {record.get('id')} due to missing credentials."
                    )
                    continue

                accounts_list.append(
                    {
                        "record_id": record.get("id"),
                        "instagram_username": ig_username,
                        "instagram_password": ig_password,
                        "email_address": email_address,
                        "email_password": email_password,
                        "package_name": package_name,
                        "device_id": device_id,
                    }
                )

            logger.info(
                f"✅ Successfully fetched credentials for {len(accounts_list)} accounts."
            )
            return accounts_list

        except Exception as e:
            logger.error(
                f"❌ An error occurred while fetching unused accounts: {e}",
                exc_info=True,
            )
            return []
