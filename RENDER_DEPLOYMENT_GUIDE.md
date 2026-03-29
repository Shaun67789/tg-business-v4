# 🚀 Render Deployment Guide
## TG Business Bot — Complete Step-by-Step

---

## Prerequisites

- ✅ A [Render](https://render.com) account (free tier works)
- ✅ A [Supabase](https://supabase.com) account (free tier works)
- ✅ A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- ✅ Your Telegram User ID (from [@userinfobot](https://t.me/userinfobot))
- ✅ This codebase pushed to a GitHub/GitLab repository

---

## Step 1 — Set Up Supabase

1. Go to [supabase.com](https://supabase.com) → **New Project**
2. Choose a name (e.g. `tg-business`) and set a strong database password
3. Wait for the project to provision (~1 minute)
4. Go to **SQL Editor** → **New Query**
5. **Paste the entire contents** of `supabase_schema.sql` and click **Run**
6. Verify all tables were created under **Table Editor**

### Get your credentials:
- Go to **Project Settings → API**
- Copy **Project URL** → this is `SUPABASE_URL`
- Copy **service_role** key (not anon!) → this is `SUPABASE_KEY`

> ⚠️ Use the **service_role** key so Row Level Security is bypassed.

---

## Step 2 — Set Up the Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) → `/newbot`
2. Follow prompts, choose a name and username
3. Copy the **token** → this is `BOT_TOKEN`
4. Get your Telegram ID from [@userinfobot](https://t.me/userinfobot) → `OWNER_ID`
5. Create a **Telegram group** for order logs:
   - Create the group → Add your bot as admin
   - Get the group ID (use [@getidsbot](https://t.me/getidsbot)) → `LOG_GROUP_ID`
6. Create or pick an **update/announcement channel**:
   - Add the bot as admin
   - Get the channel username (without @) → used in admin settings

---

## Step 3 — Deploy to Render

### 3.1 Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourname/tg-business.git
git push -u origin main
```

### 3.2 Create Render Web Service
1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repository
3. Configure:
   | Setting | Value |
   |---|---|
   | **Name** | `tg-business-bot` |
   | **Environment** | `Python 3` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn admin.main:app --host 0.0.0.0 --port $PORT` |
   | **Plan** | Free |

### 3.3 Add Environment Variables
In the **Environment** tab, add:

| Key | Value |
|---|---|
| `BOT_TOKEN` | Your bot token from BotFather |
| `OWNER_ID` | Your Telegram numeric ID |
| `LOG_GROUP_ID` | Group ID (e.g. `-1001234567890`) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase **service_role** key |
| `ADMIN_USERNAME` | Choose a username (e.g. `admin`) |
| `ADMIN_PASSWORD` | Choose a **strong** password |
| `SECRET_KEY` | A random 64-char string |
| `APP_ENV` | `production` |
| `PORT` | `8000` |

> 💡 Generate SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

### 3.4 Set WEBHOOK_URL (after first deploy)
1. Click **Deploy** and wait for build to complete
2. Copy your Render URL (e.g. `https://tg-business-bot.onrender.com`)
3. Go back to **Environment** tab → add:
   - `WEBHOOK_URL` = `https://tg-business-bot.onrender.com`
4. Click **Manual Deploy → Deploy latest commit**

### 3.5 Verify Deployment
- Visit `https://your-app.onrender.com/health` → should return `{"status":"ok","bot":"running"}`
- Visit `https://your-app.onrender.com/admin/` → admin login page

---

## Step 4 — Configure the Bot (Admin Panel)

1. Open `https://your-app.onrender.com/admin/`
2. Login with your `ADMIN_USERNAME` and `ADMIN_PASSWORD`
3. Go to **⚙️ Settings**:
   - **General tab**: Set welcome message, update channel link/username/name, support link
   - **Payment tab**: Set your Nagad/bKash number and payment notes per service
   - **Stars Prices tab**: Set prices for each star amount
   - **Premium Prices tab**: Set 3/6/12 month prices
   - **Service Prices tab**: Set prices per 1,000 for Views/Reactions/Members
4. Go to **🔗 Referrals** → create your first referral link

---

## Step 5 — Keep the Bot Alive (Free Tier)

Render free tier sleeps after 15 minutes of inactivity.

### Option A: UptimeRobot (Recommended, free)
1. Go to [uptimerobot.com](https://uptimerobot.com) → Sign up free
2. **New Monitor** → HTTP(S)
3. URL: `https://your-app.onrender.com/health`
4. Interval: **Every 5 minutes**
5. Save → Done ✅

### Option B: Render Cron Job
Add a second service in Render as a Cron Job that pings your health endpoint.

---

## Step 6 — Test Your Bot

1. Open Telegram → search your bot → `/start`
2. Verify the welcome message + channel join flow appears
3. Test each service order flow
4. Check admin panel → **📦 Orders** for incoming orders
5. Approve an order → verify user notification

---

## File Structure Reference

```
TG BUSINESS/
├── bot/
│   ├── config.py           # Env vars
│   ├── database.py         # All Supabase operations
│   ├── keyboards.py        # All InlineKeyboardMarkup
│   ├── states.py           # ConversationHandler state constants
│   ├── utils.py            # Helpers
│   └── handlers/
│       ├── start.py        # /start + referral + join verification
│       ├── stars.py        # Stars ordering flow
│       ├── premium.py      # Premium ordering flow
│       ├── views.py        # Views ordering flow
│       ├── reactions.py    # Reactions ordering flow
│       ├── members.py      # Members ordering flow
│       ├── orders.py       # Owner approval callbacks
│       └── broadcast.py    # Admin broadcast via bot command
├── admin/
│   ├── main.py             # FastAPI app + webhook integration
│   ├── routes/             # Admin panel API routes
│   └── templates/          # Jinja2 HTML templates
├── supabase_schema.sql     # Run this in Supabase SQL Editor
├── requirements.txt
├── Procfile
├── render.yaml
└── .env.example            # Copy to .env for local dev
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Bot not responding | Check `WEBHOOK_URL` is set correctly and redeploy |
| `SUPABASE_KEY` error | Make sure you used **service_role** key, not anon |
| Admin panel 500 error | Check all env vars are set; view Render logs |
| Orders not appearing | Verify `LOG_GROUP_ID` is correct and bot is group admin |
| Channel join not verifying | Set `update_channel_username` in Settings (without @) |
| Free tier sleeping | Set up UptimeRobot pinging `/health` every 5 min |

---

## Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy env file
cp .env.example .env
# Edit .env with your credentials

# 3. For local testing, comment out webhook setup in bot/main.py
#    and use polling instead (for development only)

# 4. Run the server
uvicorn admin.main:app --reload --port 8000

# 5. Admin panel at http://localhost:8000/admin/
```

---

> 🔐 **Security Reminder**: Never commit `.env` to Git. Add it to `.gitignore`.

```gitignore
.env
__pycache__/
*.pyc
.DS_Store
```
