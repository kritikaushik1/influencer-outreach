import pandas as pd

INPUT_FILE = "classified_influencers.csv"
OUTPUT_FILE = "qualified_influencers.csv"

df = pd.read_csv(INPUT_FILE)

qualified = df[
    (df["decision"] == "PASS")
    & (df["relevance_score"] >= 70)
    & (df["brand_fit_score"] >= 60)
].copy()

qualified = qualified.sort_values(
    ["relevance_score", "brand_fit_score"],
    ascending=False
)

qualified.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"Total classified: {len(df)}")
print(f"Qualified creators: {len(qualified)}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nTop qualified creators:")
print(
    qualified[
        [
            "channel_name",
            "subscriber_count",
            "sub_niche",
            "relevance_score",
            "brand_fit_score"
        ]
    ].head(20).to_string(index=False)
)