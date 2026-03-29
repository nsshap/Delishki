"""Generate a beautiful HTML gallery for ShoppingHome category."""
import sys
import os
import webbrowser
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip()
CATEGORY = "ShoppingHome"
OUTPUT_FILE = Path(__file__).parent / "shoppinghome_gallery.html"


def fetch_items():
    all_items = []
    cursor = None
    while True:
        body = {
            "filter": {"property": "Category", "select": {"equals": CATEGORY}},
            "sorts": [{"property": "Timestamp", "direction": "descending"}],
            "page_size": 100,
        }
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            headers={
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json=body,
        )
        data = r.json()
        for page in data.get("results", []):
            props = page["properties"]
            title_parts = props.get("Title", {}).get("title", [])
            context_parts = props.get("Context", {}).get("rich_text", [])
            url = props.get("URL", {}).get("url") or ""
            files = props.get("Preview", {}).get("files", [])
            image_url = files[0].get("file", {}).get("url", "") if files else ""
            all_items.append({
                "title": title_parts[0].get("plain_text", "") if title_parts else "",
                "context": context_parts[0].get("plain_text", "") if context_parts else "",
                "url": url,
                "image_url": image_url,
            })
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return all_items


def generate_html(items):
    items_json = json.dumps(items, ensure_ascii=False)
    with_images = [i for i in items if i["image_url"]]
    without_images = [i for i in items if not i["image_url"]]
    total = len(items)

    cards_html = []
    for item in items:
        title = item["title"].replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        context = item["context"].replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        url = item["url"].rstrip(")") if item["url"] else ""
        img = item["image_url"]

        if url and not url.startswith("http"):
            url = "https://" + url

        # Card is clickable if has URL
        card_attrs = ""
        if url:
            card_attrs = f' onclick="window.open(\'{url}\',\'_blank\')" style="cursor:pointer;"'

        img_block = ""
        if img:
            overlay = ""
            if url:
                display_url = url.replace("https://", "").replace("http://", "")
                overlay = f'<div class="card-overlay"><span>{display_url}</span></div>'
            elif img:
                overlay = '<div class="card-overlay card-overlay-none"><span>Нет ссылки</span></div>'
            img_block = f'<div class="card-img">{overlay}<img src="{img}" alt="{title}" loading="lazy" onerror="this.closest(\'.card-img\').style.display=\'none\'"></div>'

        context_block = f'<p class="card-context">{context}</p>' if context else ""

        link_badge = ""
        if url:
            display_url = url.replace("https://", "").replace("http://", "")
            link_badge = f'<span class="card-link">→ {display_url}</span>'
        else:
            link_badge = '<span class="card-no-link">Нет ссылки</span>'

        cards_html.append(f"""
        <div class="card"{card_attrs}>
            {img_block}
            <div class="card-body">
                <h3 class="card-title">{title}</h3>
                {context_block}
                {link_badge}
            </div>
        </div>""")

    cards = "\n".join(cards_html)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shopping Home — {total} предметов</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f5f5f0;
    color: #2d2d2d;
    min-height: 100vh;
  }}

  header {{
    background: #fff;
    border-bottom: 1px solid #e8e8e0;
    padding: 20px 32px;
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  header h1 {{
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.3px;
  }}

  .badge {{
    background: #f0f0eb;
    color: #666;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 13px;
  }}

  .search-wrap {{
    margin-left: auto;
  }}

  #search {{
    border: 1px solid #e0e0d8;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    width: 240px;
    background: #fafaf8;
    outline: none;
    transition: border-color 0.15s;
  }}

  #search:focus {{
    border-color: #bbb;
  }}

  .container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 32px 24px;
  }}

  .grid {{
    columns: 4 280px;
    column-gap: 16px;
  }}

  .card {{
    background: #fff;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 16px;
    break-inside: avoid;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
    transition: transform 0.15s, box-shadow 0.15s;
  }}

  .card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,.10);
  }}

  .card-img {{
    position: relative;
    overflow: hidden;
  }}

  .card-img img {{
    width: 100%;
    display: block;
    object-fit: cover;
    transition: transform 0.2s;
  }}

  .card:hover .card-img img {{
    transform: scale(1.03);
  }}

  .card-overlay {{
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.52);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.18s;
    z-index: 2;
  }}

  .card-overlay span {{
    color: #fff;
    font-size: 13px;
    font-weight: 500;
    text-align: center;
    padding: 0 12px;
    word-break: break-all;
  }}

  .card-overlay-none span {{
    color: #ccc;
  }}

  .card:hover .card-overlay {{
    opacity: 1;
  }}

  .card-body {{
    padding: 12px 14px 14px;
  }}

  .card-title {{
    font-size: 13.5px;
    font-weight: 500;
    line-height: 1.4;
    color: #1a1a1a;
  }}

  .card-context {{
    font-size: 12px;
    color: #888;
    margin-top: 5px;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .card-link {{
    display: inline-block;
    margin-top: 7px;
    font-size: 12px;
    color: #5b7fa6;
    font-weight: 500;
    word-break: break-all;
  }}

  .card-no-link {{
    display: inline-block;
    margin-top: 7px;
    font-size: 12px;
    color: #ccc;
  }}

  .hidden {{ display: none !important; }}

  @media (max-width: 600px) {{
    .grid {{ columns: 2 140px; }}
    header {{ padding: 14px 16px; }}
    .container {{ padding: 16px 12px; }}
    #search {{ width: 160px; }}
  }}
</style>
</head>
<body>

<header>
  <h1>🏠 Shopping Home</h1>
  <span class="badge">{total} предметов</span>
  <div class="search-wrap">
    <input id="search" type="text" placeholder="Поиск..." autocomplete="off">
  </div>
</header>

<div class="container">
  <div class="grid" id="grid">
{cards}
  </div>
</div>

<script>
  const search = document.getElementById('search');
  const cards = Array.from(document.querySelectorAll('.card'));

  search.addEventListener('input', () => {{
    const q = search.value.toLowerCase().trim();
    cards.forEach(card => {{
      const text = card.textContent.toLowerCase();
      card.classList.toggle('hidden', q.length > 0 && !text.includes(q));
    }});
  }});
</script>

</body>
</html>"""


if __name__ == "__main__":
    print(f"Fetching {CATEGORY} from Notion...")
    items = fetch_items()
    print(f"Found {len(items)} items ({sum(1 for i in items if i['image_url'])} with images)")

    html = generate_html(items)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Saved to {OUTPUT_FILE}")

    webbrowser.open(OUTPUT_FILE.as_uri())
    print("Opened in browser.")
