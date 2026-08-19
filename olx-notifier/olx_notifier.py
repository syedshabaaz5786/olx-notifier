import os
import sys
import json
import time
import html
from urllib.parse import quote

# Fix Windows console UTF-8 printing
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Prefer curl_cffi for real browser TLS impersonation (bypasses Cloudflare)
try:
    from curl_cffi import requests as c_requests
    USE_CURL_CFFI = True
except ImportError:
    import requests as c_requests
    USE_CURL_CFFI = False

import requests as std_requests

# Load .env file if present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"Notice: Could not load .env file: {e}")

# Configuration
DEFAULT_QUERIES = "samsung s22 ultra, samsung s23 ultra, samsung note 20 ultra"
DEFAULT_LOCATIONS = "mumbai, bombay, maharashtra, bengaluru, bangalore, karnataka, powai, yelahanka"

raw_queries = os.getenv("SEARCH_QUERIES", os.getenv("SEARCH_QUERY", DEFAULT_QUERIES))
SEARCH_QUERIES = [q.strip() for q in raw_queries.split(",") if q.strip()]

raw_locations = os.getenv("LOCATION_FILTERS", DEFAULT_LOCATIONS)
LOCATION_FILTERS = [l.strip().lower() for l in raw_locations.split(",") if l.strip()]

OLX_REGION = os.getenv("OLX_REGION", "in").lower().strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SEEN_FILE = os.getenv("SEEN_FILE", "seen_ids.json")


def safe_float(val, default):
    if not val or not str(val).strip():
        return float(default)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(default)


MIN_PRICE = safe_float(os.getenv("MIN_PRICE"), 0)
MAX_PRICE = safe_float(os.getenv("MAX_PRICE"), 999999999)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
}


def load_seen_ids():
    """Load list of previously notified item IDs."""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Notice reading {SEEN_FILE}: {e}")
    return set()


def save_seen_ids(seen_ids):
    """Save updated list of notified item IDs."""
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen_ids), f, indent=2)
    except Exception as e:
        print(f"Notice saving {SEEN_FILE}: {e}")


def is_location_match(item):
    """Check if item location matches target locations (Mumbai & Bengaluru)."""
    if not LOCATION_FILTERS:
        return True
    
    locations = item.get("locations_resolved", {})
    resolved_str = " ".join([str(v) for v in locations.values()]).lower()
    loc_list_str = " ".join([json.dumps(l) for l in item.get("locations", [])]).lower()
    title_str = item.get("title", "").lower()
    desc_str = item.get("description", "").lower()

    combined_text = f"{resolved_str} {loc_list_str} {title_str} {desc_str}"

    return any(loc in combined_text for loc in LOCATION_FILTERS)


def send_telegram_notification(title, price, location, link, query_matched, description="", image_url=None):
    """Send notification to Telegram via Bot API."""
    safe_title = html.escape(title)
    safe_price = html.escape(str(price))
    safe_location = html.escape(location)
    safe_description = html.escape(description) if description else "No description provided."

    if len(safe_description) > 300:
        safe_description = safe_description[:297] + "..."

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[PREVIEW] New Match: {title} | {price} | {location}\nLink: {link}\n")
        return False

    message = (
        f"🚨 <b>New OLX Listing Alert!</b>\n"
        f"🔍 <i>Matched Search: {html.escape(query_matched.title())}</i>\n\n"
        f"📱 <b>Model:</b> {safe_title}\n"
        f"💰 <b>Price:</b> {safe_price}\n"
        f"📍 <b>Location:</b> {safe_location}\n\n"
        f"📝 <b>Description:</b>\n<i>{safe_description}</i>\n\n"
        f"🔗 <b>Direct OLX Ad Link:</b>\n{link}"
    )

    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": message,
            "parse_mode": "HTML",
        }
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

    try:
        res = std_requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"[SUCCESS] Telegram alert sent for: {title}")
            return True
        else:
            if image_url:
                return send_telegram_notification(title, price, location, link, query_matched, description, image_url=None)
            print(f"[ERROR] Telegram API Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[ERROR] Exception sending Telegram alert: {e}")
    return False


def fetch_olx_items_api_in(query):
    """Fetch items from OLX India JSON API using real Chrome TLS impersonation."""
    encoded_query = quote(query)
    api_url = f"https://www.olx.in/api/relevance/v2/search?query={encoded_query}&size=50"
    
    try:
        if USE_CURL_CFFI:
            response = c_requests.get(api_url, headers=HEADERS, impersonate="chrome124", timeout=15)
        else:
            response = std_requests.get(api_url, headers=HEADERS, timeout=15)

        if response.status_code != 200:
            print(f"[API Status {response.status_code} for query '{query}']")
            return []

        data = response.json()
        raw_items = data.get("data", [])
        parsed_items = []

        print(f"Fetched {len(raw_items)} total live items for '{query}'")

        for item in raw_items:
            item_id = str(item.get("id"))
            title = item.get("title", "No Title")
            desc = item.get("description", "").replace("\n", " ").strip()
            
            # Price parsing
            price_data = item.get("price", {})
            value = price_data.get("value", {}).get("raw")
            currency = price_data.get("value", {}).get("currency", {}).get("pre", "₹")
            display_price = price_data.get("value", {}).get("display", f"{currency} {value if value else 'N/A'}")
            
            if value and (value < MIN_PRICE or value > MAX_PRICE):
                continue

            # Location parsing
            locations = item.get("locations_resolved", {})
            city = locations.get("ADMIN_LEVEL_3_name", "")
            state = locations.get("ADMIN_LEVEL_1_name", "")
            sub_locality = locations.get("SUBLOCALITY_LEVEL_1_name", "") or locations.get("ADMIN_LEVEL_4_name", "")
            
            loc_parts = [p for p in [sub_locality, city, state] if p]
            location_str = ", ".join(loc_parts) or "Unknown Location"

            # Check location filter
            if not is_location_match(item):
                continue

            # Image & Link
            images = item.get("images", [])
            image_url = images[0].get("url") if images else None

            slug = item.get("slug", "")
            link = f"https://www.olx.in/item/{slug}-iid-{item_id}" if slug else f"https://www.olx.in/item/{item_id}"

            parsed_items.append({
                "id": item_id,
                "title": title,
                "price": display_price,
                "location": location_str,
                "description": desc,
                "link": link,
                "image_url": image_url,
                "query": query
            })

        return parsed_items
    except Exception as e:
        print(f"[Error fetching query '{query}']: {e}")
        return []


def check_olx():
    """Main check function."""
    print("==================================================")
    print(f"Target Queries: {SEARCH_QUERIES}")
    print(f"Target Locations: {LOCATION_FILTERS}")
    print("==================================================")
    
    seen_ids = load_seen_ids()
    total_new = 0

    for query in SEARCH_QUERIES:
        print(f"\nScanning OLX for: '{query}'...")
        items = fetch_olx_items_api_in(query)
        print(f"Found {len(items)} items matching location filter.")

        for item in reversed(items):
            item_id = item["id"]
            if item_id not in seen_ids:
                print(f"-> NEW MATCH! ID: {item_id} | Title: {item['title']} | Location: {item['location']}")
                send_telegram_notification(
                    title=item["title"],
                    price=item["price"],
                    location=item["location"],
                    link=item["link"],
                    query_matched=item["query"],
                    description=item["description"],
                    image_url=item["image_url"]
                )
                seen_ids.add(item_id)
                total_new += 1
                time.sleep(1)
        time.sleep(1)

    save_seen_ids(seen_ids)
    print(f"\nFinished check run. Total new alerts sent: {total_new}\n")


if __name__ == "__main__":
    check_olx()
