import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
OWNER_ID: int = int(os.environ["OWNER_ID"])
LOG_GROUP_ID: int = int(os.environ.get("LOG_GROUP_ID", "0"))
WEBHOOK_URL: str = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}"

# ─── Supabase ────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]

# ─── Admin ───────────────────────────────────────────────────────
ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "changeme")
SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev_secret_change_me")

# ─── App ─────────────────────────────────────────────────────────
PORT: int = int(os.environ.get("PORT", 8000))
APP_ENV: str = os.environ.get("APP_ENV", "development")
IS_PRODUCTION: bool = APP_ENV == "production"
