import os
import sys
import base64
import pandas as pd

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# =========================================================
# PROJECT PATH
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# =========================================================
# DATABASE
# =========================================================

from database.db import (
    initialize_db,
    save_generated,
    get_outreach,
    mark_sent,
    mark_failed
)


# =========================================================
# CONFIG
# =========================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

CREDENTIALS_FILE = os.path.join(
    BASE_DIR,
    "credentials.json"
)

TOKEN_FILE = os.path.join(
    BASE_DIR,
    "token.json"
)

CSV_FILE = os.path.join(
    BASE_DIR,
    "personalized_influencers.csv"
)

# IMPORTANT:
# True = emails will NOT actually be sent
# False = real emails will be sent
DRY_RUN = True


# =========================================================
# CHECK FILES
# =========================================================

def check_required_files():

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"credentials.json not found at:\n"
            f"{CREDENTIALS_FILE}"
        )

    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(
            f"personalized_influencers.csv not found at:\n"
            f"{CSV_FILE}"
        )


# =========================================================
# GMAIL AUTHENTICATION
# =========================================================

def get_gmail_service():

    creds = None

    # Existing token
    if os.path.exists(TOKEN_FILE):

        print("Existing token found.")

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # Token invalid / missing
    if not creds or not creds.valid:

        # Refresh existing token
        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            print("Refreshing Gmail token...")

            creds.refresh(
                Request()
            )

        else:

            print()
            print(
                "Starting Gmail OAuth authorization..."
            )
            print()

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            creds = flow.run_local_server(
                port=0,
                open_browser=True
            )

        # Save token
        with open(
            TOKEN_FILE,
            "w"
        ) as token:

            token.write(
                creds.to_json()
            )

        print()
        print(
            f"Token saved: {TOKEN_FILE}"
        )

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    return service


# =========================================================
# CREATE EMAIL
# =========================================================

def create_message(
    to_email,
    subject,
    body
):

    message = MIMEText(
        body,
        "plain",
        "utf-8"
    )

    message["to"] = to_email
    message["subject"] = subject

    encoded_message = (
        base64.urlsafe_b64encode(
            message.as_bytes()
        )
        .decode()
    )

    return {
        "raw": encoded_message
    }


# =========================================================
# SEND EMAIL
# =========================================================

def send_email(
    service,
    to_email,
    subject,
    body
):

    message = create_message(
        to_email,
        subject,
        body
    )

    result = (
        service.users()
        .messages()
        .send(
            userId="me",
            body=message
        )
        .execute()
    )

    return result


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 50)
    print("EDXSO Gmail Outreach")
    print("=" * 50)
    print()

    # Check files
    check_required_files()

    # Initialize database
    print("Initializing database...")

    initialize_db()

    # Load CSV
    print(
        "Loading personalized influencers..."
    )

    df = pd.read_csv(
        CSV_FILE
    )

    print(
        f"Loaded {len(df)} creators."
    )

    print()

    # Gmail service
    service = get_gmail_service()

    print()
    print(
        "Gmail API service ready."
    )

    print(
        f"DRY_RUN = {DRY_RUN}"
    )

    print()

    print("=" * 50)
    print("Starting outreach processing")
    print("=" * 50)
    print()

    for index, row in df.iterrows():

        channel_name = str(
            row.get(
                "channel_name",
                ""
            )
        ).strip()

        email = str(
            row.get(
                "public_email",
                ""
            )
        ).strip()

        subject = str(
            row.get(
                "email_subject",
                ""
            )
        ).strip()

        body = str(
            row.get(
                "personalized_email",
                ""
            )
        ).strip()

        instagram_dm = str(
            row.get(
                "instagram_dm",
                ""
            )
        ).strip()

        # -------------------------------------------------
        # Missing email
        # -------------------------------------------------

        if (
            not email
            or email.lower() == "not found"
            or "@" not in email
        ):

            print(
                f"[SKIP] {channel_name}"
            )

            print(
                "       No public email found."
            )

            print()

            continue

        # -------------------------------------------------
        # Duplicate protection
        # -------------------------------------------------

        existing = get_outreach(
            email
        )

        if existing:

            status = existing[6]

            print(
                f"[SKIP] {channel_name}"
            )

            print(
                f"       {email}"
            )

            print(
                f"       Already in database."
            )

            print(
                f"       Status: {status}"
            )

            print()

            continue

        # -------------------------------------------------
        # Save generated outreach
        # -------------------------------------------------

        save_generated(
            email=email,
            channel_name=channel_name,
            email_subject=subject,
            email_body=body,
            instagram_dm=instagram_dm
        )

        print(
            f"[{index + 1}/{len(df)}] "
            f"{channel_name}"
        )

        print(
            f"To: {email}"
        )

        print(
            f"Subject: {subject}"
        )

        # -------------------------------------------------
        # DRY RUN
        # -------------------------------------------------

        if DRY_RUN:

            print(
                "DRY RUN - Email NOT sent."
            )

            print(
                "Personalized email preview:"
            )

            print("-" * 50)

            print(
                body
            )

            print("-" * 50)

            print()

            continue

        # -------------------------------------------------
        # REAL EMAIL
        # -------------------------------------------------

        try:

            result = send_email(
                service=service,
                to_email=email,
                subject=subject,
                body=body
            )

            mark_sent(
                email
            )

            print(
                "Email sent successfully."
            )

            print(
                f"Message ID: "
                f"{result.get('id')}"
            )

        except Exception as e:

            mark_failed(
                email,
                str(e)
            )

            print(
                "Email sending failed."
            )

            print(
                f"Error: {e}"
            )

        print()

    print("=" * 50)
    print("Outreach processing complete.")
    print("=" * 50)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()