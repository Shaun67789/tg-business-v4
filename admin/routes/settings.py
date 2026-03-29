from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

SETTINGS_FIELDS = [
    # General
    ("welcome_message", "Welcome Message", "textarea", "general"),
    ("update_channel_link", "Update Channel Link (URL)", "text", "general"),
    ("update_channel_username", "Update Channel Username (no @)", "text", "general"),
    ("update_channel_name", "Update Channel Display Name", "text", "general"),
    ("support_link", "Support Chat Link", "text", "general"),
    ("support_text", "Support Page Text", "textarea", "general"),
    # Payment
    ("nagad_bkash_info", "Nagad/bKash Payment Info (HTML)", "textarea", "payment"),
    ("payment_note_stars", "Payment Note — Stars (HTML)", "textarea", "payment"),
    ("payment_note_premium", "Payment Note — Premium (HTML)", "textarea", "payment"),
    ("payment_note_views", "Payment Note — Views (HTML)", "textarea", "payment"),
    ("payment_note_reactions", "Payment Note — Reactions (HTML)", "textarea", "payment"),
    ("payment_note_members", "Payment Note — Members (HTML)", "textarea", "payment"),
    # Stars Prices
    ("price_stars_50", "Stars ×50 Price (BDT)", "number", "prices_stars"),
    ("price_stars_100", "Stars ×100 Price (BDT)", "number", "prices_stars"),
    ("price_stars_200", "Stars ×200 Price (BDT)", "number", "prices_stars"),
    ("price_stars_250", "Stars ×250 Price (BDT)", "number", "prices_stars"),
    ("price_stars_300", "Stars ×300 Price (BDT)", "number", "prices_stars"),
    ("price_stars_400", "Stars ×400 Price (BDT)", "number", "prices_stars"),
    ("price_stars_500", "Stars ×500 Price (BDT)", "number", "prices_stars"),
    ("price_stars_1000", "Stars ×1000 Price (BDT)", "number", "prices_stars"),
    ("price_stars_2500", "Stars ×2500 Price (BDT)", "number", "prices_stars"),
    ("price_stars_5000", "Stars ×5000 Price (BDT)", "number", "prices_stars"),
    ("price_stars_10000", "Stars ×10000 Price (BDT)", "number", "prices_stars"),
    # Premium Prices
    ("price_premium_3", "Premium 3 Months Price (BDT)", "number", "prices_premium"),
    ("price_premium_6", "Premium 6 Months Price (BDT)", "number", "prices_premium"),
    ("price_premium_12", "Premium 12 Months Price (BDT)", "number", "prices_premium"),
    # Service Prices per 1000
    ("price_views_per_1000", "Views Price per 1,000 (BDT)", "number", "prices_services"),
    ("price_reactions_per_1000", "Reactions Price per 1,000 (BDT)", "number", "prices_services"),
    ("price_members_per_1000", "Members Price per 1,000 (BDT)", "number", "prices_services"),
]


@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    all_settings = await db.get_all_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": all_settings,
        "fields": SETTINGS_FIELDS,
        "current_page": "settings",
    })


@router.post("/update")
async def update_settings(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    for key, value in body.items():
        await db.set_setting(key, str(value))
    return JSONResponse({"ok": True, "updated": len(body)})
