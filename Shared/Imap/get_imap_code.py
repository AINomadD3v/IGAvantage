import email
import imaplib
import re

from bs4 import BeautifulSoup


def extract_body(msg):
    """Extracts email body as text (HTML or plain)."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            if ctype == "text/plain" and payload:
                return payload.decode(errors="replace")
            elif ctype == "text/html" and payload:
                html = payload.decode(errors="replace")
                return BeautifulSoup(html, "html.parser").get_text(separator=" ")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            html = payload.decode(errors="replace")
            return BeautifulSoup(html, "html.parser").get_text(separator=" ")
        elif isinstance(payload, str):
            return BeautifulSoup(payload, "html.parser").get_text(separator=" ")
        else:
            return str(payload)


def get_instagram_verification_code(
    email_address,
    password,
    imap_host="imap.poczta.onet.pl",
    imap_port=993,
    timeout=20,
    debug=False,
):
    """Fetches the latest Instagram verification code sent to the mailbox. Returns code or None."""
    CODE_REGEX = r"code to confirm your identity[:\s]*([0-9]{6})"
    found_code = None

    try:
        imap = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=timeout)
        imap.login(email_address, password)
        status, folders = imap.list()
        if status != "OK":
            if debug:
                print("Failed to list mailboxes.")
            imap.logout()
            return None
        # Check all folders for redundancy
        for folder_bytes in folders:
            folder = folder_bytes.decode().split(' "/" ')[-1].strip('"')
            if debug:
                print(f"\nChecking folder: {folder}")
            try:
                imap.select(f'"{folder}"')
                status, data = imap.search(None, "ALL")
                if status != "OK":
                    if debug:
                        print("Search failed in", folder)
                    continue
                msg_nums = data[0].split()[::-1]  # Newest first
                for num in msg_nums:
                    status, msg_data = imap.fetch(num, "(RFC822)")
                    if status != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = msg.get("Subject", "")
                    sender = msg.get("From", "")
                    # Strict match for Instagram code emails only
                    if not (
                        subject.strip().lower() == "verify your account"
                        and "security@mail.instagram.com" in sender.lower()
                    ):
                        continue
                    body = extract_body(msg)
                    if debug:
                        print(f"--- Email from {sender} | Subject: {subject} ---")
                        print(body[:500] if body else "[Empty body]")
                        print("--- END BODY PREVIEW ---")
                    # Extract code
                    match = re.search(CODE_REGEX, body, re.IGNORECASE)
                    if match:
                        found_code = match.group(1)
                        if debug:
                            print(
                                f"FOUND CODE: {found_code} (Subject: {subject}) (From: {sender})"
                            )
                        imap.logout()
                        return found_code
                # If we get here, nothing found in this folder
                if debug:
                    print("No code found in this folder.")
            except Exception as e:
                if debug:
                    print(f"Error with folder {folder}: {e}")
        imap.logout()
    except Exception as e:
        if debug:
            print(f"IMAP connection or login failed: {e}")
    if debug:
        print("No Instagram verification code found in any folder.")
    return None


# EXAMPLE USAGE:
if __name__ == "__main__":
    code = get_instagram_verification_code(
        "trippwaller@op.pl", "hadi551035", debug=True
    )
    if code:
        print(f"Verification code is: {code}")
    else:
        print("No verification code found.")
