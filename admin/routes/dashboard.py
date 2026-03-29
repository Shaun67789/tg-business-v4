from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    
    stats = {}
    recent_orders = []
    error = None
    
    try:
        stats = await db.get_dashboard_stats()
        recent_orders = await db.list_orders(limit=10)
    except Exception as exc:
        error = f"Database connection error. Did you run supabase_schema.sql? Details: {exc}"

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_orders": recent_orders,
        "page": "dashboard",
        "error": error,
    })
