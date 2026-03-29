from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated
import asyncio
from telegram.error import TelegramError
from telegram.constants import ParseMode

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    broadcasts = await db.list_broadcasts(limit=30)
    total_users = await db.count_users()
    return templates.TemplateResponse("broadcast.html", {
        "request": request,
        "broadcasts": broadcasts,
        "total_users": total_users,
        "current_page": "broadcast",
    })


@router.post("/send")
async def send_broadcast(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    msg_type = body.get("type", "text")
    content = body.get("content", {})
    target = body.get("target", "all")
    target_ids = body.get("target_ids", [])

    if target == "all":
        user_ids = await db.get_all_user_ids()
    else:
        user_ids = [int(x) for x in target_ids if str(x).isdigit()]

    bc_record = await db.create_broadcast(msg_type, content, target)
    bc_id = bc_record["id"]

    # Run broadcast in background
    from bot.main import get_app
    bot = get_app().bot

    success, fail = 0, 0
    for uid in user_ids:
        try:
            if msg_type == "photo":
                await bot.send_photo(
                    chat_id=uid,
                    photo=content.get("url", ""),
                    caption=content.get("caption", ""),
                    parse_mode=ParseMode.HTML,
                )
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=content.get("text", ""),
                    parse_mode=ParseMode.HTML,
                )
            success += 1
        except TelegramError:
            fail += 1
        await asyncio.sleep(0.05)

    await db.update_broadcast_stats(bc_id, success, fail)
    return JSONResponse({"ok": True, "success": success, "fail": fail, "total": success + fail})


@router.delete("/{broadcast_id}")
async def delete_broadcast(request: Request, broadcast_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    await db.delete_broadcast(broadcast_id)
    return JSONResponse({"ok": True})
