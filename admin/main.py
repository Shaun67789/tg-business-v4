"""
FastAPI Admin Panel — main application.
Integrates bot webhook + admin web routes.
Bot startup errors are caught so admin panel stays alive.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from bot.config import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_URL, SECRET_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

_bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_app
    try:
        from bot.main import build_application, setup_webhook
        logger.info("Initialising Telegram bot…")
        _bot_app = build_application()
        await _bot_app.initialize()
        await _bot_app.start()
        await setup_webhook(_bot_app)
        logger.info("Bot started and webhook registered.")
    except Exception as exc:
        logger.error(f"Bot failed to start (admin panel still running): {exc}", exc_info=True)
    yield
    if _bot_app:
        try:
            await _bot_app.stop()
            await _bot_app.shutdown()
        except Exception as exc:
            logger.error(f"Error stopping bot: {exc}")


app = FastAPI(title="TG Business Admin", lifespan=lifespan)

# ── Middleware ──────────────────────────────────────────────────
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=86400)

# ── Static files & templates ───────────────────────────────────
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

# ── Webhook endpoint ───────────────────────────────────────────
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    if _bot_app is None:
        return JSONResponse({"ok": False, "error": "Bot not running"}, status_code=503)
    try:
        from telegram import Update
        data = await request.json()
        update = Update.de_json(data, _bot_app.bot)
        await _bot_app.process_update(update)
        return JSONResponse({"ok": True})
    except Exception as exc:
        logger.error(f"Webhook error: {exc}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


# ── Health check ───────────────────────────────────────────────
@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok", "bot": "running" if _bot_app else "stopped"}


# ── Admin routes (imported here to avoid circular imports) ─────
from admin.routes import auth, dashboard, orders, users, settings, referrals, broadcast, stats  # noqa: E402

app.include_router(auth.router,       prefix="/admin",           tags=["Auth"])
app.include_router(dashboard.router,  prefix="/admin",           tags=["Dashboard"])
app.include_router(orders.router,     prefix="/admin/orders",    tags=["Orders"])
app.include_router(users.router,      prefix="/admin/users",     tags=["Users"])
app.include_router(settings.router,   prefix="/admin/settings",  tags=["Settings"])
app.include_router(referrals.router,  prefix="/admin/referrals", tags=["Referrals"])
app.include_router(broadcast.router,  prefix="/admin/broadcast", tags=["Broadcast"])
app.include_router(stats.router,      prefix="/admin/stats",     tags=["Stats"])


# ── Root redirect ──────────────────────────────────────────────
@app.get("/")
@app.head("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/")
