from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bot import database as db
from admin.routes.auth import is_authenticated
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def orders_list(
    request: Request,
    status: Optional[str] = None,
    service: Optional[str] = None,
    page: int = 0,
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    PAGE_SIZE = 20
    orders = await db.list_orders(limit=PAGE_SIZE, offset=page * PAGE_SIZE, status=status, service=service)
    total = await db.count_orders(status=status)
    import math
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    return templates.TemplateResponse("orders.html", {
        "request": request,
        "orders": orders,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "status_filter": status,
        "service_filter": service,
        "current_page": "orders",
    })


@router.post("/{order_id}/status")
async def update_order_status(request: Request, order_id: str):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    new_status = body.get("status")
    if new_status not in ("pending", "confirmed", "cancelled", "wrong_txn"):
        return JSONResponse({"error": "Invalid status"}, status_code=400)
    order = await db.update_order_status(order_id, new_status)
    return JSONResponse({"ok": True, "order_id": order_id, "status": new_status})
