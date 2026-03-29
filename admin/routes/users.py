from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def users_list(request: Request, search: Optional[str] = None, page: int = 0):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    PAGE_SIZE = 25
    users = await db.list_users(limit=PAGE_SIZE, offset=page * PAGE_SIZE, search=search)
    total = await db.count_users()
    import math
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "search": search or "",
        "current_page": "users",
    })


@router.post("/{telegram_id}/ban")
async def ban_user(request: Request, telegram_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    await db.ban_user(telegram_id)
    return JSONResponse({"ok": True})


@router.post("/{telegram_id}/unban")
async def unban_user(request: Request, telegram_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    await db.unban_user(telegram_id)
    return JSONResponse({"ok": True})


@router.get("/{telegram_id}/orders", response_class=HTMLResponse)
async def user_orders(request: Request, telegram_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    user = await db.get_user(telegram_id)
    orders = await db.list_orders(user_id=telegram_id, limit=50)
    return templates.TemplateResponse("user_orders.html", {
        "request": request,
        "user": user,
        "orders": orders,
        "current_page": "users",
    })


@router.post("/{telegram_id}/message")
async def send_message_to_user(request: Request, telegram_id: int):
    """Send a custom message to a specific user via the bot."""
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    text = body.get("text", "")
    if not text:
        return JSONResponse({"error": "No text"}, status_code=400)
    from bot.main import get_app
    from telegram.constants import ParseMode
    bot_application = get_app()
    if not bot_application:
        return JSONResponse({"error": "Bot not running"}, status_code=503)
    try:
        await bot_application.bot.send_message(chat_id=telegram_id, text=text, parse_mode=ParseMode.HTML)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
