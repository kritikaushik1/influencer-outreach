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

INPUT_FILE = "youtube_channels.csv"
OUTPUT_FILE = "classified_influencers.csv"


def classify_creator(row):
    prompt = f"""
You are an influencer marketing analyst.

Analyze this YouTube creator:

Channel Name: {row.get("channel_name", "")}
Description: {row.get("description", "")}
Subscribers: {row.get("subscriber_count", 0)}
Videos: {row.get("video_count", 0)}
Total Views: {row.get("view_count", 0)}

Classify the creator for a technology-focused brand.

Return ONLY valid JSON in this exact structure:

{{
    "niche": "technology",
    "sub_niche": "",
    "content_themes": [],
    "audience": "",
    "relevance_score": 0,
    "brand_fit_score": 0,
    "decision": "PASS",
    "reason": ""
}}

Rules:
- relevance_score must be between 0 and 100
- brand_fit_score must be between 0 and 100
- decision must be either PASS or FAIL
- Focus on technology, gadgets, AI, software, coding,
  productivity, gaming technology and related topics.
- Do not invent facts.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        text = response.text.strip()

        # Remove markdown JSON fences if Gemini adds them
        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        result = json.loads(text)

        return result

    except Exception as e:
        print(f"Classification failed: {row.get('channel_name')}")
        print(e)

        return {
            "niche": "Unknown",
            "sub_niche": "",
            "content_themes": [],
            "audience": "",
            "relevance_score": 0,
            "brand_fit_score": 0,
            "decision": "FAIL",
            "reason": "Classification error"
        }


def main():

    df = pd.read_csv(INPUT_FILE)

    print(f"Loaded {len(df)} influencers.")
    print()

    results = []

    for index, row in df.iterrows():

        print(
            f"[{index + 1}/{len(df)}] "
            f"{row.get('channel_name', '')}"
        )

        result = classify_creator(row)

        results.append(result)

        # Small delay to reduce API rate-limit problems
        time.sleep(4)

    result_df = pd.DataFrame(results)

    final_df = pd.concat(
        [
            df.reset_index(drop=True),
            result_df.reset_index(drop=True)
        ],
        axis=1
    )

    final_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("Classification complete.")
    print(f"Saved to: {OUTPUT_FILE}")

    print()
    print("PASS creators:")

    print(
        final_df[
            final_df["decision"] == "PASS"
        ][
            [
                "channel_name",
                "subscriber_count",
                "niche",
                "sub_niche",
                "relevance_score",
                "brand_fit_score"
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()