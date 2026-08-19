# 🔔 OLX New Item Listing Notifier (Zero-PC Cloud Setup)

Get instant mobile notifications (with item title, price, location, seller description, photo, and direct link) whenever a new matching Samsung phone is posted on OLX India!

This project runs **100% free in the cloud** using **GitHub Actions** and **Telegram**. Your PC does **NOT** need to remain powered on.

---

## 🚀 How It Works

1. **GitHub Actions** runs the Python script automatically every 30 minutes in the cloud.
2. The script queries OLX API for your target models:
   - **Samsung S22 Ultra**
   - **Samsung S23 Ultra**
   - **Samsung Note 20 Ultra**
3. Filters for your requested locations:
   - **Powai (Mumbai)**
   - **Yelahanka (Bengaluru)**
4. If a matching item is posted, sends a instant Telegram push alert to your phone with full seller description, photo, and direct OLX link.
5. Updates `seen_ids.json` in your repository so duplicate alerts are never sent.

---

## 🔑 Your Pre-configured GitHub Secrets

Copy and paste these exact values into your GitHub Repository (**Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret**):

| Secret Name | Exact Value to Copy | Description |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | `8861245186:AAGQVr3BAYU78liiDwoEB9W1KBa7Xlj8oJU` | Your Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | `1118627196` | Your Personal Telegram Chat ID |
| `SEARCH_QUERIES` | `samsung s22 ultra, samsung s23 ultra, samsung note 20 ultra` | Models tracked |
| `LOCATION_FILTERS` | `powai, mumbai, yelahanka, bengaluru, bangalore` | Locations filtered |
| `OLX_REGION` | `in` | OLX India |

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
