import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

INPUT_FILE = "enriched_influencers.csv"
OUTPUT_FILE = "personalized_influencers.csv"


def generate_personalization(row):

    prompt = f"""
You are an influencer outreach specialist.

Create a personalized outreach message for this creator.

Creator:
Name: {row.get("channel_name", "")}
Niche: {row.get("niche", "")}
Sub-niche: {row.get("sub_niche", "")}
Description: {row.get("description", "")}
Subscribers: {row.get("subscriber_count", 0)}

Create:

1. A professional personalized email
2. A short Instagram DM

The email should:
- Have a natural subject line
- Mention the creator's specific niche/content
- Clearly explain the potential technology brand collaboration
- Be concise and professional
- Avoid fake claims
- Avoid mentioning information not provided

The Instagram DM should:
- Be friendly
- Be short
- Mention their content
- Suggest a collaboration
- Not sound like spam

Return ONLY valid JSON:

{{
    "email_subject": "",
    "email_body": "",
    "instagram_dm": ""
}}
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        text = response.text.strip()

        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        return json.loads(text)

    except Exception as e:

        print(
            f"Personalization failed for "
            f"{row.get('channel_name', '')}"
        )

        print(e)

        return {
            "email_subject": "",
            "email_body": "",
            "instagram_dm": ""
        }


def main():

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Loaded {len(df)} creators."
    )

    subjects = []
    emails = []
    dms = []

    for index, row in df.iterrows():

        print(
            f"[{index + 1}/{len(df)}] "
            f"{row.get('channel_name', '')}"
        )

        result = generate_personalization(
            row
        )

        subjects.append(
            result.get(
                "email_subject",
                ""
            )
        )

        emails.append(
            result.get(
                "email_body",
                ""
            )
        )

        dms.append(
            result.get(
                "instagram_dm",
                ""
            )
        )

        # Avoid Gemini rate limits
        time.sleep(4)

    df["email_subject"] = subjects
    df["personalized_email"] = emails
    df["instagram_dm"] = dms

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(
        "Personalization complete."
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()