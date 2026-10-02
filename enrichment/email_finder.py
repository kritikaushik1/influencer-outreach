import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

INPUT_FILE = "qualified_influencers.csv"
OUTPUT_FILE = "enriched_influencers.csv"

EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

# Ignore obvious non-contact/example emails
BAD_EMAIL_PARTS = [
    "example.com",
    "domain.com",
    "sentry.io",
    "wixpress.com",
]


def extract_email(text):
    """Extract a publicly visible email from text."""

    if not text:
        return None

    matches = re.findall(
        EMAIL_PATTERN,
        text
    )

    for email in matches:
        email = email.strip().lower()

        if not any(
            bad in email
            for bad in BAD_EMAIL_PARTS
        ):
            return email

    return None


def fetch_page(url):
    """Download a public webpage."""

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        if response.status_code == 200:
            return response.text

    except requests.RequestException:
        pass

    return ""


def extract_links(html, base_url):
    """Extract useful public links from a webpage."""

    if not html:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(
            base_url,
            href
        )

        if full_url.startswith("http"):
            links.append(full_url)

    return list(dict.fromkeys(links))


def find_contact_pages(links):
    """Find likely contact/business pages."""

    keywords = [
        "contact",
        "business",
        "work-with-me",
        "workwithme",
        "collab",
        "collaboration",
        "partnership",
        "about",
    ]

    contact_links = []

    for link in links:

        lower = link.lower()

        if any(
            keyword in lower
            for keyword in keywords
        ):
            contact_links.append(link)

    return contact_links[:5]


def find_email_from_website(url):
    """Search a publicly linked website for a contact email."""

    html = fetch_page(url)

    if not html:
        return None

    # Check homepage first
    email = extract_email(html)

    if email:
        return email

    links = extract_links(
        html,
        url
    )

    contact_pages = find_contact_pages(
        links
    )

    for contact_url in contact_pages:

        contact_html = fetch_page(
            contact_url
        )

        email = extract_email(
            contact_html
        )

        if email:
            return email

        time.sleep(0.5)

    return None


def find_email_for_creator(row):

    # --------------------------------------------------
    # 1. YouTube channel description
    # --------------------------------------------------

    description = str(
        row.get(
            "description",
            ""
        )
    )

    email = extract_email(
        description
    )

    if email:
        return email, "YouTube description"

    # --------------------------------------------------
    # 2. YouTube URL
    # --------------------------------------------------

    youtube_url = str(
        row.get(
            "youtube_url",
            ""
        )
    )

    if not youtube_url.startswith(
        "http"
    ):
        return None, "Not Found"

    html = fetch_page(
        youtube_url
    )

    if not html:
        return None, "Not Found"

    # Check visible/page source text
    email = extract_email(
        html
    )

    if email:
        return email, "YouTube page"

    # --------------------------------------------------
    # 3. Public links on YouTube page
    # --------------------------------------------------

    links = extract_links(
        html,
        youtube_url
    )

    # Remove YouTube internal links
    external_links = []

    for link in links:

        domain = urlparse(
            link
        ).netloc.lower()

        if (
            domain
            and "youtube.com" not in domain
            and "youtu.be" not in domain
        ):
            external_links.append(link)

    # --------------------------------------------------
    # 4. Search linked public websites
    # --------------------------------------------------

    for website in external_links[:5]:

        print(
            f"    Checking website: {website}"
        )

        email = find_email_from_website(
            website
        )

        if email:
            return (
                email,
                "Public website"
            )

        time.sleep(0.5)

    return None, "Not Found"


def main():

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Loaded {len(df)} qualified creators."
    )
    print()

    emails = []
    sources = []

    for index, row in df.iterrows():

        name = row.get(
            "channel_name",
            "Unknown"
        )

        print(
            f"[{index + 1}/{len(df)}] {name}"
        )

        email, source = find_email_for_creator(
            row
        )

        if email:

            print(
                f"  Email: {email}"
            )

            print(
                f"  Source: {source}"
            )

            emails.append(email)
            sources.append(source)

        else:

            print(
                "  Email: Not Found"
            )

            emails.append(
                "Not Found"
            )

            sources.append(
                "Not Found"
            )

        print()

        # Small delay to avoid hammering websites
        time.sleep(1)

    df["public_email"] = emails

    df["email_source"] = sources

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    found = sum(
        email != "Not Found"
        for email in emails
    )

    not_found = (
        len(emails) - found
    )

    print(
        "================================"
    )

    print(
        "Email enrichment complete."
    )

    print(
        f"Total creators: {len(df)}"
    )

    print(
        f"Emails found: {found}"
    )

    print(
        f"Emails not found: {not_found}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()