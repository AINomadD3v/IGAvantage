import os
import sys
import time

# ----------------------------
# 🧠 Ensure root path is in sys.path for module resolution
# ----------------------------
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ----------------------------
# 🚀 Imports
# ----------------------------
from Shared.Data.airtable_manager import AirtableClient
from Shared.Pop3.main import get_instagram_verification_code
from Shared.Utils.logger_config import setup_logger

logger = setup_logger(__name__)


# ----------------------------
# 🧪 Main Test Logic
# ----------------------------
def run_bulk_verification(accounts_to_test: int = 10):
    """
    Fetches a batch of credentials and runs the email verification test for each.

    Args:
        accounts_to_test (int): The number of accounts to run the test for.
    """
    logger.info(
        f"🚀 Starting bulk email verification test for {accounts_to_test} accounts..."
    )

    try:
        airtable_client = AirtableClient()

        logger.info(
            f"📡 Fetching credentials for {accounts_to_test} accounts from Airtable..."
        )

        # Use the new bulk method to get a list of credentials
        credentials_list = airtable_client.get_warmup_credentials_bulk(
            limit=accounts_to_test
        )

        if not credentials_list:
            logger.error("❌ No warmup credentials found. Exiting.")
            return

        success_count = 0
        fail_count = 0

        for i, credentials in enumerate(credentials_list):
            email = credentials["email"]
            password = credentials["password"]

            logger.info(
                f"--- Running test {i+1}/{len(credentials_list)} for {email} ---"
            )

            try:
                code = get_instagram_verification_code(
                    email_address=email,
                    password=password,
                    debug=True,
                )

                if code:
                    success_count += 1
                    logger.info(f"✅ SUCCESS! Verification code for {email} is: {code}")
                    print(
                        f"\n✅ SUCCESS ({i+1}/{len(credentials_list)})! Code for {email} is: {code}"
                    )
                else:
                    fail_count += 1
                    logger.warning(
                        f"❌ FAILED. No verification code was found for {email}."
                    )
                    print(
                        f"\n❌ FAILED ({i+1}/{len(credentials_list)}). No code found for {email}."
                    )

            except Exception as e:
                fail_count += 1
                logger.error(
                    f"🔥 An error occurred while processing {email}: {e}", exc_info=True
                )
                print(f"\n🔥 ERROR ({i+1}/{len(credentials_list)}) for {email}: {e}")

            # Optional: Add a small delay between tests to avoid rate-limiting
            if i < len(credentials_list) - 1:
                time.sleep(5)  # Delay for 5 seconds

        logger.info("--- 🏁 Bulk Test Summary ---")
        logger.info(f"Total Accounts Tested: {len(credentials_list)}")
        logger.info(f"✅ Successes: {success_count}")
        logger.info(f"❌ Failures: {fail_count}")
        logger.info("--- 🏁 End of Summary ---")

    except Exception as e:
        logger.error(
            f"🔥 A fatal error occurred during the bulk verification script: {e}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    # Define how many accounts you want to test
    NUMBER_OF_ACCOUNTS = 10
    run_bulk_verification(accounts_to_test=NUMBER_OF_ACCOUNTS)
