"""
Admin authentication — login/logout with session.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.config import ADMIN_USERNAME, ADMIN_PASSWORD

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


def is_authenticated(request: Request) -> bool:
    return request.session.get("admin_logged_in", False)


def require_auth(request: Request):
    """Call this in route handlers to redirect if not auth'd."""
    if not is_authenticated(request):
        raise RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin_logged_in"] = True
        return RedirectResponse(url="/admin/", status_code=303)
    return RedirectResponse(url="/admin/login?error=Invalid+credentials", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)
