"""Test URL extraction from images using GPT-4o Vision.
Reads 10 ShoppingHome items that have image but no URL, extracts URLs, prints results.
Does NOT write to Notion yet.
"""
import os
import base64
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

HEADERS_NOTION = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

VISION_PROMPT = """Look at this image carefully. It's likely a screenshot from Instagram, a shop, or an ad.

Your task: find any website URL or domain name visible in the image.
Look for: URLs in text, shop domains, Instagram handles (→ instagram.com/handle), watermarks, buttons like "Shop now" with a link, etc.

Rules:
- Return ONLY the URL/domain, nothing else. Example: "sasastore.nl" or "https://motelamiio.eu"
- If it's an Instagram handle like "@brandname", return "instagram.com/brandname"
- If there is NO URL or domain visible anywhere, return exactly: NONE
- Do not guess or make up URLs. Only return what is actually visible in the image."""


def fetch_candidates(limit=10):
    """Fetch items with image but no URL from Notion."""
    candidates = []
    cursor = None
    while len(candidates) < limit:
        body = {
            "filter": {"property": "Category", "select": {"equals": "ShoppingHome"}},
            "sorts": [{"property": "Timestamp", "direction": "descending"}],
            "page_size": 100,
        }
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            headers=HEADERS_NOTION,
            json=body,
        )
        data = r.json()
        for page in data.get("results", []):
            props = page["properties"]
            url = props.get("URL", {}).get("url") or ""
            files = props.get("Preview", {}).get("files", [])
            image_url = files[0].get("file", {}).get("url", "") if files else ""
            title_parts = props.get("Title", {}).get("title", [])
            title = title_parts[0].get("plain_text", "") if title_parts else ""
            if image_url and not url:
                candidates.append({
                    "id": page["id"],
                    "title": title,
                    "image_url": image_url,
                })
            if len(candidates) >= limit:
                break
        if not data.get("has_more") or len(candidates) >= limit:
            break
        cursor = data.get("next_cursor")
    return candidates[:limit]


def download_image_as_b64(url: str) -> tuple[str, str]:
    """Download image, return (base64_data, mime_type)."""
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    return base64.standard_b64encode(r.content).decode(), mime


def extract_url_from_image(image_b64: str, mime_type: str) -> str:
    """Ask GPT-4o Vision to extract URL from image. Returns URL string or 'NONE'."""
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}", "detail": "high"}},
                    ],
                }
            ],
            "max_tokens": 100,
            "temperature": 0,
        },
    )
    result = r.json()
    return result["choices"][0]["message"]["content"].strip()


def main():
    print(f"Fetching up to 10 ShoppingHome items with image but no URL...\n")
    candidates = fetch_candidates(10)
    print(f"Found {len(candidates)} candidates.\n")
    print("-" * 70)

    found = 0
    not_found = 0
    errors = 0

    for i, item in enumerate(candidates, 1):
        title = item["title"][:55]
        print(f"{i:2}. {title}")
        try:
            b64, mime = download_image_as_b64(item["image_url"])
            result = extract_url_from_image(b64, mime)
            if result == "NONE" or not result:
                print(f"    → Нет URL")
                not_found += 1
            else:
                print(f"    → {result}")
                found += 1
        except Exception as e:
            print(f"    ⚠️  Ошибка: {e}")
            errors += 1
        print()

    print("-" * 70)
    print(f"Итого: найдено {found}, не найдено {not_found}, ошибок {errors}")


if __name__ == "__main__":
    main()
