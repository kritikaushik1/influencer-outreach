import os
import sys
import base64
import sqlite3
import pandas as pd
import streamlit as st

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CSV_FILE = os.path.join(
    BASE_DIR,
    "personalized_influencers.csv"
)

DB_FILE = os.path.join(
    BASE_DIR,
    "outreach.db"
)

TOKEN_FILE = os.path.join(
    BASE_DIR,
    "token.json"
)


# =========================================================
# GMAIL CONFIG
# =========================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


# =========================================================
# DATABASE IMPORT
# =========================================================

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import (
    initialize_db,
    get_outreach,
    save_generated,
    mark_sent,
    mark_failed
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="EDXSO AI Influencer Outreach",
    page_icon="📣",
    layout="wide"
)


# =========================================================
# LOAD CSV
# =========================================================

@st.cache_data
def load_data():

    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()

    return pd.read_csv(
        CSV_FILE
    )


# =========================================================
# LOAD DATABASE
# =========================================================

def load_outreach():

    initialize_db()

    if not os.path.exists(DB_FILE):
        return pd.DataFrame()

    conn = sqlite3.connect(
        DB_FILE
    )

    try:

        data = pd.read_sql_query(
            "SELECT * FROM outreach",
            conn
        )

    except Exception:

        data = pd.DataFrame()

    conn.close()

    return data


# =========================================================
# GMAIL SERVICE
# =========================================================

def get_gmail_service():

    if not os.path.exists(TOKEN_FILE):

        st.error(
            "Gmail token not found. "
            "Run gmail_sender.py once to complete OAuth."
        )

        return None

    try:

        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

        if credentials.expired and credentials.refresh_token:

            credentials.refresh(
                Request()
            )

            with open(
                TOKEN_FILE,
                "w"
            ) as token:

                token.write(
                    credentials.to_json()
                )

        if not credentials.valid:

            st.error(
                "Gmail authorization is invalid. "
                "Run gmail_sender.py again."
            )

            return None

        service = build(
            "gmail",
            "v1",
            credentials=credentials
        )

        return service

    except Exception as e:

        st.error(
            f"Gmail authentication error: {e}"
        )

        return None


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
# INITIALIZE
# =========================================================

initialize_db()

df = load_data()

outreach_df = load_outreach()


# =========================================================
# HEADER
# =========================================================

st.title(
    "📣 EDXSO AI Influencer Outreach"
)

st.caption(
    "AI-powered creator discovery, classification, "
    "personalization and Gmail outreach"
)

st.divider()


# =========================================================
# CHECK DATA
# =========================================================

if df.empty:

    st.error(
        "personalized_influencers.csv not found."
    )

    st.stop()


# =========================================================
# METRICS
# =========================================================

total_creators = len(df)

email_count = (
    df["public_email"]
    .astype(str)
    .str.contains(
        "@",
        na=False
    )
    .sum()
)

pass_count = (
    (
        df["decision"]
        == "PASS"
    ).sum()
    if "decision" in df.columns
    else 0
)

sent_count = 0

if (
    not outreach_df.empty
    and "status" in outreach_df.columns
):

    sent_count = (
        outreach_df["status"]
        == "Sent"
    ).sum()


col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Qualified Creators",
        total_creators
    )

with col2:

    st.metric(
        "Public Emails",
        email_count
    )

with col3:

    st.metric(
        "PASS Creators",
        pass_count
    )

with col4:

    st.metric(
        "Emails Sent",
        sent_count
    )


st.divider()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header(
    "🔎 Filters"
)

search = st.sidebar.text_input(
    "Search creator"
)

min_subscribers = st.sidebar.number_input(
    "Minimum subscribers",
    min_value=0,
    value=5000,
    step=1000
)

max_subscribers = st.sidebar.number_input(
    "Maximum subscribers",
    min_value=0,
    value=100000,
    step=1000
)


if st.sidebar.button(
    "🔄 Refresh Data"
):

    st.cache_data.clear()

    st.rerun()


# =========================================================
# FILTER
# =========================================================

filtered = df[
    (
        df["subscriber_count"]
        >= min_subscribers
    )
    &
    (
        df["subscriber_count"]
        <= max_subscribers
    )
].copy()


if search:

    search_lower = search.lower()

    filtered = filtered[
        filtered[
            "channel_name"
        ]
        .astype(str)
        .str.lower()
        .str.contains(
            search_lower,
            na=False
        )
    ]


# =========================================================
# CREATOR TABLE
# =========================================================

st.subheader(
    "👥 Creator Database"
)

display_columns = [
    "channel_name",
    "subscriber_count",
    "niche",
    "sub_niche",
    "relevance_score",
    "brand_fit_score",
    "public_email"
]

display_columns = [
    column
    for column in display_columns
    if column in filtered.columns
]

st.dataframe(
    filtered[display_columns],
    use_container_width=True,
    hide_index=True
)


st.divider()


# =========================================================
# CREATOR SELECT
# =========================================================

st.subheader(
    "👤 Creator Details"
)

creator_names = (
    filtered["channel_name"]
    .dropna()
    .tolist()
)


if not creator_names:

    st.warning(
        "No creators match the current filters."
    )

    st.stop()


selected_creator = st.selectbox(
    "Select creator",
    creator_names
)


creator = filtered[
    filtered["channel_name"]
    == selected_creator
].iloc[0]


# =========================================================
# DETAILS
# =========================================================

left, right = st.columns(2)


with left:

    st.markdown(
        f"## {creator['channel_name']}"
    )

    st.write(
        f"**Subscribers:** "
        f"{int(creator['subscriber_count']):,}"
    )

    st.write(
        f"**Niche:** "
        f"{creator.get('niche', 'N/A')}"
    )

    st.write(
        f"**Sub-niche:** "
        f"{creator.get('sub_niche', 'N/A')}"
    )

    st.write(
        f"**Relevance Score:** "
        f"{creator.get('relevance_score', 'N/A')}"
    )

    st.write(
        f"**Brand Fit Score:** "
        f"{creator.get('brand_fit_score', 'N/A')}"
    )

    if "youtube_url" in creator:

        youtube_url = str(
            creator["youtube_url"]
        )

        if youtube_url.startswith(
            "http"
        ):

            st.link_button(
                "▶ Open YouTube Channel",
                youtube_url
            )


with right:

    email = str(
        creator.get(
            "public_email",
            "Not Found"
        )
    ).strip()

    subject = str(
        creator.get(
            "email_subject",
            ""
        )
    ).strip()

    email_body = str(
        creator.get(
            "personalized_email",
            ""
        )
    ).strip()

    instagram_dm = str(
        creator.get(
            "instagram_dm",
            ""
        )
    ).strip()


    # -----------------------------------------------------
    # EMAIL
    # -----------------------------------------------------

    st.markdown(
        "### 📧 Public Email"
    )

    if "@" in email:

        st.success(
            email
        )

    else:

        st.warning(
            "No public email available."
        )


    # -----------------------------------------------------
    # SUBJECT
    # -----------------------------------------------------

    st.markdown(
        "### 📨 Email Subject"
    )

    st.code(
        subject,
        language=None
    )


    # -----------------------------------------------------
    # EMAIL BODY
    # -----------------------------------------------------

    st.markdown(
        "### ✉️ Personalized Email"
    )

    st.text_area(
        "Email Preview",
        value=email_body,
        height=250,
        disabled=True,
        label_visibility="collapsed"
    )


    # -----------------------------------------------------
    # INSTAGRAM DM
    # -----------------------------------------------------

    st.markdown(
        "### 💬 Instagram DM"
    )

    st.text_area(
        "Instagram DM",
        value=instagram_dm,
        height=150,
        disabled=True,
        label_visibility="collapsed"
    )


st.divider()


# =========================================================
# SEND EMAIL SECTION
# =========================================================

st.subheader(
    "🚀 Send Email"
)


if (
    not email
    or email.lower() == "not found"
    or "@" not in email
):

    st.info(
        "Email cannot be sent because no public "
        "email address is available."
    )

else:

    existing = get_outreach(
        email
    )

    if existing:

        current_status = existing[6]

        if current_status == "Sent":

            st.success(
                f"Already sent to {email}."
            )

        elif current_status == "Failed":

            st.warning(
                f"Previous attempt failed for {email}. "
                "You can retry."
            )

        else:

            st.info(
                f"Prepared for {email}. "
                "Ready to send."
            )

    else:

        current_status = "New"

        st.info(
            f"Ready to send to {email}."
        )


    st.warning(
        "Only send to a legitimate public/business "
        "contact address and follow applicable "
        "email/anti-spam requirements."
    )


    confirm = st.checkbox(
        "I confirm that I want to send this email."
    )


    if st.button(
        "📨 Send Email",
        type="primary",
        disabled=not confirm
    ):

        # ---------------------------------------------
        # Duplicate protection
        # ---------------------------------------------

        existing = get_outreach(
            email
        )

        if (
            existing
            and existing[6] == "Sent"
        ):

            st.error(
                "This email has already been sent."
            )

        else:

            # -----------------------------------------
            # Get Gmail
            # -----------------------------------------

            with st.spinner(
                "Connecting to Gmail..."
            ):

                service = get_gmail_service()


            if service is None:

                st.error(
                    "Could not connect to Gmail."
                )

            else:

                try:

                    # ---------------------------------
                    # Save generated outreach
                    # ---------------------------------

                    if not existing:

                        save_generated(
                            email=email,
                            channel_name=str(
                                creator[
                                    "channel_name"
                                ]
                            ),
                            email_subject=subject,
                            email_body=email_body,
                            instagram_dm=instagram_dm
                        )

                    # ---------------------------------
                    # Send
                    # ---------------------------------

                    with st.spinner(
                        f"Sending email to {email}..."
                    ):

                        result = send_email(
                            service=service,
                            to_email=email,
                            subject=subject,
                            body=email_body
                        )

                    # ---------------------------------
                    # Mark sent
                    # ---------------------------------

                    mark_sent(
                        email
                    )

                    st.success(
                        f"✅ Email sent successfully to {email}"
                    )

                    st.info(
                        f"Gmail Message ID: "
                        f"{result.get('id', 'N/A')}"
                    )

                    st.rerun()

                except Exception as e:

                    mark_failed(
                        email,
                        str(e)
                    )

                    st.error(
                        f"❌ Email failed: {e}"
                    )


st.divider()


# =========================================================
# OUTREACH TRACKING
# =========================================================

st.subheader(
    "📊 Outreach Tracking"
)

outreach_df = load_outreach()


if outreach_df.empty:

    st.info(
        "No outreach records yet."
    )

else:

    status_counts = (
        outreach_df["status"]
        .value_counts()
    )

    metric_columns = st.columns(
        len(status_counts)
    )

    for column, (status, count) in zip(
        metric_columns,
        status_counts.items()
    ):

        with column:

            st.metric(
                status,
                count
            )


    st.dataframe(
        outreach_df,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "EDXSO AI Influencer Outreach • "
    "YouTube + Gemini + Gmail API + SQLite + Streamlit"
)