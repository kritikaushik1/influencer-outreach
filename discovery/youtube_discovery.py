import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("YOUTUBE_API_KEY not found in .env")

BASE_URL = "https://www.googleapis.com/youtube/v3"


def search_channels(query, max_results=50):
    url = f"{BASE_URL}/search"

    params = {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": min(max_results, 50),
        "key": API_KEY,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json().get("items", [])


def get_channel_details(channel_ids):
    url = f"{BASE_URL}/channels"

    params = {
        "part": "snippet,statistics",
        "id": ",".join(channel_ids),
        "key": API_KEY,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json().get("items", [])


def collect_channels(queries):
    results = []

    for query in queries:
        print(f"Searching: {query}")

        search_results = search_channels(query, 50)

        channel_ids = [
            item["snippet"]["channelId"]
            for item in search_results
        ]

        # Remove duplicates
        channel_ids = list(dict.fromkeys(channel_ids))

        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i:i + 50]
            channels = get_channel_details(batch)

            for channel in channels:
                snippet = channel.get("snippet", {})
                stats = channel.get("statistics", {})

                results.append({
                    "channel_id": channel.get("id"),
                    "channel_name": snippet.get("title"),
                    "description": snippet.get("description", ""),
                    "country": snippet.get("country", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "subscriber_count": int(
                        stats.get("subscriberCount", 0)
                    ),
                    "video_count": int(
                        stats.get("videoCount", 0)
                    ),
                    "view_count": int(
                        stats.get("viewCount", 0)
                    ),
                    "youtube_url": (
                        f"https://www.youtube.com/channel/"
                        f"{channel.get('id')}"
                    ),
                })

        time.sleep(1)

    return results


if __name__ == "__main__":

    queries = [
        "technology",
        "tech reviews",
        "gadgets",
        "coding",
        "AI tools",
        "software",
        "productivity",
        "gaming technology",
    ]

    data = collect_channels(queries)

    df = pd.DataFrame(data)

    if not df.empty:
        df = df.drop_duplicates(
            subset=["channel_id"]
        )

        # Micro-influencer range:
        # 5,000 to 100,000 subscribers
        df = df[
            (df["subscriber_count"] >= 5000)
            & (df["subscriber_count"] <= 100000)
        ]

        df = df.sort_values(
            "subscriber_count",
            ascending=False
        )

    output_file = "youtube_channels.csv"
    df.to_csv(output_file, index=False)

    print()
    print(f"Found {len(df)} micro-influencers.")
    print(f"Saved to: {output_file}")