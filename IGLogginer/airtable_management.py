# airtable_management.py

from pyairtable import Api
from dotenv import load_dotenv
import os
import requests
from logger_config import setup_logger

logger = setup_logger(__name__)

load_dotenv()

class AirtableClient:
    def __init__(self):
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY not found in environment variables")
        
        # Create the API instance
        self.api = Api(self.api_key)
        

    def get_table_records(self, base_id, table_name):
        try:
            table = self.api.table(base_id, table_name)
            records = table.all()
            return records
        except Exception as e:
            print(f"Error fetching records: {str(e)}")
            return []

    def get_single_active_account(self, base_id, table_name, unused_view_id):
        try:
            logger.info("Attempting to fetch active account...")
            logger.info("Creating table instance...")
            table = self.api.table(base_id, table_name)

            # Define expected fields
            fields = ['Account', 'Password', 'Email', 'Email Password', 'Package Name']

            logger.info("Querying Airtable from view...")
            try:
                logger.info("Making API request...")
                records = table.all(
                    view=unused_view_id,
                    fields=fields,
                    max_records=1,
                )
                logger.info("API request completed")
                logger.info(f"Number of records found: {len(records) if records else 0}")

                if records:
                    first_record = records[0]
                    record_id = first_record.get('id')
                    record_fields = first_record.get('fields', {})

                    # Unwrap 'Package Name' if it's a list
                    raw_package = record_fields.get('Package Name')
                    if isinstance(raw_package, list) and raw_package:
                        record_fields['Package Name'] = raw_package[0]
                    else:
                        record_fields['Package Name'] = None

                    logger.info("✅ Active account found:")
                    logger.info(f"  Account: {record_fields.get('Account')}")
                    logger.info(f"  Password: {record_fields.get('Password')}")
                    logger.info(f"  Email: {record_fields.get('Email')}")
                    logger.info(f"  Email Password: {record_fields.get('Email Password')}")
                    logger.info(f"  Package Name: {record_fields.get('Package Name')}")

                    return {
                        'id': record_id,
                        'fields': record_fields
                    }

                logger.warning("⚠️ No active accounts found in view")
                return None

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

def main():
    logger.info("Starting Airtable client...")
    load_dotenv()
    client = AirtableClient()

    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_id = os.getenv('IG_ARMY_ACCOUNTS_TABLE_ID')
    unused_view_id = os.getenv('IG_ARMY_UNUSED_VIEW_ID')

    logger.info(f"Using Base ID: {base_id}")
    logger.info(f"Using Table ID: {table_id}")
    
    if not base_id or not table_id:
        logger.error("Missing required environment variables")
        raise ValueError("AIRTABLE_BASE_ID or IG_ACCOUNTS_TABLE_ID not found in environment variables")
    
    account = client.get_single_active_account(base_id, table_id, unused_view_id)
    
if __name__ == "__main__":
    main()

