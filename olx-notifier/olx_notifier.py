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
DEFAULT_QUERIES = "samsung s22 ultra, samsung s23 ultra, samsung s24 ultra, samsung note 20 ultra"
raw_queries = os.getenv("SEARCH_QUERIES", os.getenv("SEARCH_QUERY", DEFAULT_QUERIES))
SEARCH_QUERIES = [q.strip() for q in raw_queries.split(",") if q.strip()]

OLX_REGION = os.getenv("OLX_REGION", "in").lower().strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1118627196")
SEEN_FILE = os.getenv("SEEN_FILE", "seen_ids.json")
SUBSCRIBERS_FILE = os.getenv("SUBSCRIBERS_FILE", "subscribers.json")

# Keywords covering 100% of all Mumbai and Bangalore / Bengaluru locations
MUMBAI_KEYWORDS = [
    "mumbai", "bombay", "navi mumbai", "thane", "powai", "andheri", "bandra", "dadar",
    "borivali", "kurla", "malad", "chembur", "ghatkopar", "kandivali", "goregaon",
    "mira road", "bhayandar", "worli", "juhu", "vashi", "kalyan", "dombivli", "panvel"
]

BANGALORE_KEYWORDS = [
    "bangalore", "bengaluru", "yelahanka", "rajaji nagar", "indiranagar", "whitefield",
    "koramangala", "electronic city", "jayanagar", "btm", "hsr", "marathahalli",
    "hebbal", "malleshwaram", "banashankari", "thanisandra", "majestic", "yeshwanthpur",
    "bellandur", "sarjapur", "kengeri", "kalyan nagar", "nagawara", "kr puram"
]


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


def load_subscribers():
    """Load all subscribed Telegram chat IDs."""
    subscribers = set()
    
    # 1. Add chat IDs from environment variables
    if TELEGRAM_CHAT_ID:
        for cid in TELEGRAM_CHAT_ID.split(","):
            cid = cid.strip()
            if cid:
                subscribers.add(cid)
    
    # 2. Add chat IDs from subscribers.json file
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for cid in saved:
                    subscribers.add(str(cid).strip())
        except Exception as e:
            print(f"Notice reading {SUBSCRIBERS_FILE}: {e}")

    # 3. Auto-discover any new users who interacted with the bot on Telegram
    if TELEGRAM_BOT_TOKEN:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            res = std_requests.get(url, timeout=10)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for update in updates:
                    msg = update.get("message") or update.get("edited_message")
                    if msg:
                        chat = msg.get("chat", {})
                        cid = str(chat.get("id"))
                        first_name = chat.get("first_name", "Friend")
                        if cid and cid not in subscribers:
                            print(f"[NEW SUBSCRIBER DISCOVERED] User: {first_name} | Chat ID: {cid}")
                            subscribers.add(cid)
                            # Send welcome confirmation to new user
                            welcome_msg = (
                                f"🎉 <b>Welcome {first_name}!</b>\n\n"
                                f"You are now <b>Subscribed</b> to the OLX Deal Alert Bot!\n\n"
                                f"📱 <b>Models Tracked:</b>\n"
                                f"• Samsung S24 Ultra\n"
                                f"• Samsung S23 Ultra\n"
                                f"• Samsung S22 Ultra\n"
                                f"• Samsung Note 20 Ultra\n\n"
                                f"📍 <b>Locations:</b> All of Mumbai & Bangalore\n\n"
                                f"<i>You will receive instant alerts right here whenever a new listing is posted!</i>"
                            )
                            std_requests.post(
                                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                                json={"chat_id": cid, "text": welcome_msg, "parse_mode": "HTML"},
                                timeout=10
                            )
        except Exception as e:
            print(f"Notice auto-discovering subscribers: {e}")

    # Save all unique subscribers back to file
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(subscribers), f, indent=2)
    except Exception as e:
        print(f"Notice saving {SUBSCRIBERS_FILE}: {e}")

    return list(subscribers)


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
    """Check if item location belongs to ANY location in Mumbai or Bangalore."""
    locations = item.get("locations_resolved", {})
    city = str(locations.get("ADMIN_LEVEL_3_name", "")).lower()
    state = str(locations.get("ADMIN_LEVEL_1_name", "")).lower()
    sub_locality = str(locations.get("SUBLOCALITY_LEVEL_1_name", "") or locations.get("ADMIN_LEVEL_4_name", "")).lower()
    
    loc_combined = f"{sub_locality} {city} {state}".strip()
    if not loc_combined:
        # Fallback to locations array
        loc_combined = " ".join([json.dumps(l) for l in item.get("locations", [])]).lower()

    in_mumbai = any(k in loc_combined for k in MUMBAI_KEYWORDS)
    in_bangalore = any(k in loc_combined for k in BANGALORE_KEYWORDS)

    return in_mumbai or in_bangalore


def send_telegram_notification(title, price, location, link, query_matched, subscribers, description="", image_url=None):
    """Broadcast notification to ALL subscribed Telegram users."""
    safe_title = html.escape(title)
    safe_price = html.escape(str(price))
    safe_location = html.escape(location)
    safe_description = html.escape(description) if description else "No description provided."

    if len(safe_description) > 300:
        safe_description = safe_description[:297] + "..."

    if not TELEGRAM_BOT_TOKEN or not subscribers:
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

    success_count = 0
    for chat_id in subscribers:
        try:
            if image_url:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                payload = {
                    "chat_id": chat_id,
                    "photo": image_url,
                    "caption": message,
                    "parse_mode": "HTML",
                }
            else:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                }

            res = std_requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                success_count += 1
            else:
                # Fallback to text message if photo fails
                if image_url:
                    text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    std_requests.post(text_url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            print(f"[ERROR] Failed sending alert to chat_id {chat_id}: {e}")

    print(f"[BROADCAST] Alert for '{title}' delivered to {success_count}/{len(subscribers)} subscribers.")
    return success_count > 0


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

            # Check location filter (All Mumbai & Bangalore)
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
    """Main check function broadcasting to all subscribers."""
    subscribers = load_subscribers()
    print("==================================================")
    print(f"Target Models: {SEARCH_QUERIES}")
    print(f"Target Locations: ALL OF MUMBAI & BANGALORE")
    print(f"Subscribers List: {subscribers}")
    print("==================================================")
    
    seen_ids = load_seen_ids()
    total_new = 0

    for query in SEARCH_QUERIES:
        print(f"\nScanning OLX for: '{query}'...")
        items = fetch_olx_items_api_in(query)
        print(f"Found {len(items)} items in Mumbai/Bangalore.")

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
                    subscribers=subscribers,
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
