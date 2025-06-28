# TestScripts/test_fetch_unused.py

import os
import pprint  # Used for printing dictionaries and lists cleanly

# Adjust the path to import from the Shared directory
import sys

# This adds the project root to the Python path, allowing imports from Shared
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from Shared.Data.airtable_manager import AirtableClient
from Shared.Utils.logger_config import setup_logger

# Setup a logger for the test script
logger = setup_logger(__name__)


def test_fetch_function():
    """
    Tests the fetch_unused_accounts function from AirtableClient.
    """
    logger.info("--- Starting Test for fetch_unused_accounts ---")

    try:
        # 1. Initialize the Airtable Client
        # We don't need a table_key here since the function hardcodes the IDs it needs.
        airtable_client = AirtableClient()
        logger.info("AirtableClient initialized successfully.")

        # 2. Define how many records we want to test with
        records_to_fetch = 5
        logger.info(f"Attempting to fetch {records_to_fetch} unused accounts...")

        # 3. Call the new function
        unused_accounts = airtable_client.fetch_unused_accounts(
            max_records=records_to_fetch
        )

        # 4. Analyze and print the results
        if not unused_accounts:
            logger.warning(
                "Function returned no accounts. This could be correct if the 'Unused Accounts' view is empty."
            )
            logger.warning("Please check your Airtable to confirm.")
            return

        logger.info(f"✅ Successfully fetched {len(unused_accounts)} accounts.")

        print("\n--- Fetched Account Data ---")
        # Using pprint for a more readable output of the list of dictionaries
        pprint.pprint(unused_accounts)
        print("--------------------------\n")

        # Optional: A simple check to ensure data format is as expected
        first_account = unused_accounts[0]
        expected_keys = [
            "record_id",
            "instagram_username",
            "instagram_password",
            "email_address",
            "email_password",
        ]

        # Check if all expected keys are in the first record
        if all(key in first_account for key in expected_keys):
            logger.info(
                "✅ Data format check passed. All expected keys are present in the first record."
            )
        else:
            logger.error(
                "❌ Data format check failed. Some keys are missing from the record."
            )
            logger.error(f"Expected keys: {expected_keys}")
            logger.error(f"Actual keys: {list(first_account.keys())}")

    except Exception as e:
        logger.error(
            f"💥 An unexpected error occurred during the test: {e}", exc_info=True
        )

    finally:
        logger.info("--- Test Finished ---")


if __name__ == "__main__":
    # This block allows you to run the script directly from the command line
    test_fetch_function()
