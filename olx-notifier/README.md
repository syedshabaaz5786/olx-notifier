# 🔔 OLX New Item Listing Notifier (Zero-PC Cloud Setup)

Get instant mobile notifications (with item title, price, location, seller description, photo, and direct link) whenever a new matching Samsung phone is posted on OLX India!

This project runs **100% free in the cloud** using **GitHub Actions** and **Telegram**. Your PC does **NOT** need to remain powered on.

---

## 🚀 How It Works

1. **GitHub Actions** runs the Python script automatically every 30 minutes in the cloud.
2. The script queries OLX API for your target models:
   - **Samsung S24 Ultra**
   - **Samsung S23 Ultra**
   - **Samsung S22 Ultra**
   - **Samsung Note 20 Ultra**
3. Filters for all locations in **Mumbai** and **Bangalore**.
4. Broadcasts instant Telegram push alerts to all subscribed users with photos and direct OLX links.
5. Updates `seen_ids.json` and `subscribers.json` so duplicate alerts are avoided.

---

## 🔑 GitHub Secrets Configuration

Configure your credentials privately in your GitHub Repository (**Settings ➔ Secrets and variables ➔ Actions ➔ Repository secrets**):

| Secret Name | Description |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Token from @BotFather (keep secret!) |
| `TELEGRAM_CHAT_ID` | Your Personal Telegram Chat ID |
| `SEARCH_QUERIES` | `samsung s22 ultra, samsung s23 ultra, samsung s24 ultra, samsung note 20 ultra` |
| `LOCATION_FILTERS` | `mumbai, bombay, maharashtra, bengaluru, bangalore, karnataka, powai, yelahanka` |
| `OLX_REGION` | `in` |

---

## ⚡ GitHub Permission Setup (Required)

1. In your GitHub repository, go to **Settings ➔ Actions ➔ General**.
2. Scroll down to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Click **Save**.

---

## 🧪 Testing Manually

1. Go to the **Actions** tab in your GitHub repository.
2. Select **OLX New Listing Notifier** on the left menu.
3. Click **Run workflow** ➔ **Run workflow**.
