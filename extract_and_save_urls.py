"""Extract URLs from images via GPT-4o Vision and write them to Notion."""
import os
import base64
import requests
import time
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


def fetch_all_candidates():
    candidates = []
    cursor = None
    while True:
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
                candidates.append({"id": page["id"], "title": title, "image_url": image_url})
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return candidates


def download_image_as_b64(url: str) -> tuple[str, str]:
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    return base64.standard_b64encode(r.content).decode(), mime


def extract_url_from_image(image_b64: str, mime_type: str) -> str:
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
    return r.json()["choices"][0]["message"]["content"].strip()


def save_url_to_notion(page_id: str, url: str) -> bool:
    # Ensure URL has a scheme
    if url and not url.startswith("http"):
        url = "https://" + url
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS_NOTION,
        json={"properties": {"URL": {"url": url}}},
    )
    return r.status_code == 200


def main():
    print("Fetching all ShoppingHome items with image but no URL...")
    candidates = fetch_all_candidates()
    print(f"Found {len(candidates)} candidates.\n")
    print("-" * 70)

    saved = 0
    skipped = 0
    errors = 0

    for i, item in enumerate(candidates, 1):
        title = item["title"][:55]
        print(f"{i:2}/{len(candidates)}  {title}")
        try:
            b64, mime = download_image_as_b64(item["image_url"])
            result = extract_url_from_image(b64, mime)

            if result == "NONE" or not result:
                print(f"       → Нет URL, пропускаем")
                skipped += 1
            else:
                ok = save_url_to_notion(item["id"], result)
                if ok:
                    print(f"       → {result} ✅")
                    saved += 1
                else:
                    print(f"       → {result} ⚠️  ошибка записи в Notion")
                    errors += 1
        except Exception as e:
            print(f"       ⚠️  Ошибка: {e}")
            errors += 1

        # Small pause to avoid rate limits
        time.sleep(0.3)

    print()
    print("-" * 70)
    print(f"Готово: записано {saved}, без URL {skipped}, ошибок {errors}")


if __name__ == "__main__":
    main()
