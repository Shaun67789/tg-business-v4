from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def stats_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    dashboard_stats = await db.get_dashboard_stats()
    revenue = await db.get_revenue_stats()
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats": dashboard_stats,
        "revenue": revenue,
        "current_page": "stats",
    })


@router.get("/api/chart-data")
async def chart_data(request: Request):
    """Return JSON for Chart.js graphs."""
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    revenue = await db.get_revenue_stats()
    orders = revenue.get("orders", [])

    # Group by date
    from collections import defaultdict
    by_date: dict = defaultdict(float)
    for o in orders:
        date = o["created_at"][:10]
        by_date[date] += o["amount_bdt"]

    sorted_dates = sorted(by_date.keys())
    return JSONResponse({
        "labels": sorted_dates,
        "revenue": [round(by_date[d], 2) for d in sorted_dates],
        "by_service": revenue.get("by_service", {}),
        "total": revenue.get("total", 0),
    })
