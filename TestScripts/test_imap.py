# test_imap.py

import os
import sys

# ----------------------------
# 🧠 Ensure root path is in sys.path for module resolution
# This allows `Shared.` imports to work if this script is executed directly.
# Recommended usage is still: `python -m TestScripts.test_imap`
# ----------------------------
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ----------------------------
# 🚀 Imports (assumes Shared modules are reachable)
# ----------------------------
from Shared.Data.airtable_manager import AirtableClient
from Shared.Pop3.main import get_instagram_verification_code
from Shared.Utils.logger_config import setup_logger

logger = setup_logger(__name__)

# ----------------------------
# 🧪 Main Test Logic
# ----------------------------
if __name__ == "__main__":
    logger.info("🚀 Starting standalone email verification test...")

    try:
        airtable_client = AirtableClient()

        logger.info("📡 Fetching email credentials from Airtable...")
        credentials = airtable_client.get_warmup_credentials()

        if not credentials:
            logger.error("❌ No warmup credentials found. Exiting.")
            sys.exit(1)

        email = credentials["email"]
        password = credentials["password"]

        logger.info(f"📨 Attempting to retrieve Instagram code for {email}")
        code = get_instagram_verification_code(
            email_address=email,
            password=password,
            debug=True,
        )

        if code:
            logger.info(f"🎉 SUCCESS! Verification code is: {code}")
            print(f"\n🎉 SUCCESS! Verification code is: {code}")
        else:
            logger.warning("❌ No verification code was found in the email account.")
            print("\n❌ No verification code was found in the email account.")

    except Exception as e:
        logger.error(f"🔥 Fatal error during verification script: {e}", exc_info=True)
        sys.exit(1)
