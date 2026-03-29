from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def referrals_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    links = await db.list_referral_links()
    from bot.config import WEBHOOK_URL
    bot_username = ""
    try:
        from bot.main import get_app
        bot_info = await get_app().bot.get_me()
        bot_username = bot_info.username
    except Exception:
        pass
    return templates.TemplateResponse("referrals.html", {
        "request": request,
        "links": links,
        "bot_username": bot_username,
        "current_page": "referrals",
    })


@router.post("/create")
async def create_referral(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    label = body.get("label", "")
    created_info = body.get("created_info", "")
    code = body.get("code") or uuid.uuid4().hex[:8].upper()
    link = await db.create_referral_link(code=code, label=label, created_info=created_info)
    return JSONResponse({"ok": True, "link": link})


@router.delete("/{link_id}")
async def delete_referral(request: Request, link_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    await db.delete_referral_link(link_id)
    return JSONResponse({"ok": True})
