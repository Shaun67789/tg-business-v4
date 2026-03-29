"""
Central database module. All interactions with Supabase go through here.
Uses lazy Supabase client initialization to avoid startup crashes.
"""
from __future__ import annotations
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client
from bot.config import SUPABASE_URL, SUPABASE_KEY

# ── Lazy client — created only on first DB call ───────────────────
_client: Optional[Client] = None


def _db() -> Client:
    """Return (or lazily create) the Supabase client."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(fn):
    """Run a sync supabase lambda in an executor."""
    return asyncio.get_event_loop().run_in_executor(None, fn)


# ═══════════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════════

async def get_user(telegram_id: int) -> Optional[Dict]:
    res = await _run(lambda: _db().table("users").select("*").eq("telegram_id", telegram_id).execute())
    return res.data[0] if res.data else None


async def upsert_user(telegram_id: int, username: str, first_name: str,
                       last_name: str, referred_by: Optional[str] = None) -> Dict:
    existing = await get_user(telegram_id)
    if existing:
        res = await _run(lambda: _db().table("users").update({
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "last_seen": _now(),
        }).eq("telegram_id", telegram_id).execute())
        return res.data[0]
    else:
        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "is_banned": False,
            "channel_joined": False,
            "referred_by": referred_by,
            "joined_at": _now(),
            "last_seen": _now(),
        }
        res = await _run(lambda: _db().table("users").insert(data).execute())
        return res.data[0]


async def mark_channel_joined(telegram_id: int) -> None:
    await _run(lambda: _db().table("users").update({"channel_joined": True}).eq("telegram_id", telegram_id).execute())


async def ban_user(telegram_id: int) -> None:
    await _run(lambda: _db().table("users").update({"is_banned": True}).eq("telegram_id", telegram_id).execute())


async def unban_user(telegram_id: int) -> None:
    await _run(lambda: _db().table("users").update({"is_banned": False}).eq("telegram_id", telegram_id).execute())


async def list_users(limit: int = 100, offset: int = 0,
                      search: Optional[str] = None, banned_only: bool = False) -> List[Dict]:
    def _query():
        q = _db().table("users").select("*", count="exact")
        if banned_only:
            q = q.eq("is_banned", True)
        if search:
            safe_id = search if search.isdigit() else "0"
            q = q.or_(f"username.ilike.%{search}%,first_name.ilike.%{search}%,telegram_id.eq.{safe_id}")
        return q.order("joined_at", desc=True).range(offset, offset + limit - 1).execute()
    res = await _run(_query)
    return res.data


async def count_users() -> int:
    res = await _run(lambda: _db().table("users").select("id", count="exact").execute())
    return res.count or 0


async def get_all_user_ids() -> List[int]:
    res = await _run(lambda: _db().table("users").select("telegram_id").eq("is_banned", False).execute())
    return [r["telegram_id"] for r in res.data]


# ═══════════════════════════════════════════════════════════════════
# ORDERS
# ═══════════════════════════════════════════════════════════════════

async def create_order(user_id: int, service: str, details: Dict[str, Any],
                        txn_id: str, amount_bdt: float) -> Dict:
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    data = {
        "order_id": order_id,
        "user_id": user_id,
        "service": service,
        "details": details,
        "txn_id": txn_id,
        "amount_bdt": amount_bdt,
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }
    res = await _run(lambda: _db().table("orders").insert(data).execute())
    return res.data[0]


async def get_order(order_id: str) -> Optional[Dict]:
    res = await _run(lambda: _db().table("orders").select("*").eq("order_id", order_id).execute())
    return res.data[0] if res.data else None


async def update_order_status(order_id: str, status: str) -> Dict:
    res = await _run(lambda: _db().table("orders").update({
        "status": status, "updated_at": _now()
    }).eq("order_id", order_id).execute())
    return res.data[0]


async def list_orders(limit: int = 50, offset: int = 0,
                       status: Optional[str] = None, service: Optional[str] = None,
                       user_id: Optional[int] = None) -> List[Dict]:
    def _query():
        q = _db().table("orders").select("*", count="exact")
        if status:
            q = q.eq("status", status)
        if service:
            q = q.eq("service", service)
        if user_id:
            q = q.eq("user_id", user_id)
        return q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    res = await _run(_query)
    return res.data


async def count_orders(status: Optional[str] = None) -> int:
    def _query():
        q = _db().table("orders").select("id", count="exact")
        if status:
            q = q.eq("status", status)
        return q.execute()
    res = await _run(_query)
    return res.count or 0


async def get_revenue_stats() -> Dict:
    res = await _run(lambda: _db().table("orders")
        .select("amount_bdt,service,status,created_at")
        .eq("status", "confirmed").execute())
    orders = res.data
    total = sum(o["amount_bdt"] for o in orders)
    by_service: Dict[str, float] = {}
    for o in orders:
        by_service[o["service"]] = by_service.get(o["service"], 0) + o["amount_bdt"]
    return {"total": total, "by_service": by_service, "orders": orders}


# ═══════════════════════════════════════════════════════════════════
# SETTINGS (key-value store)
# ═══════════════════════════════════════════════════════════════════

_settings_cache: Dict[str, str] = {}


async def _refresh_settings() -> None:
    global _settings_cache
    res = await _run(lambda: _db().table("settings").select("*").execute())
    _settings_cache = {r["key"]: r["value"] for r in res.data}


async def get_setting(key: str, default: str = "") -> str:
    if not _settings_cache:
        await _refresh_settings()
    return _settings_cache.get(key, default)


async def set_setting(key: str, value: str) -> None:
    await _run(lambda: _db().table("settings").upsert({"key": key, "value": value}).execute())
    _settings_cache[key] = value


async def get_all_settings() -> Dict[str, str]:
    await _refresh_settings()
    return dict(_settings_cache)


async def get_price_config() -> Dict[str, Any]:
    """Returns all price-related settings as a structured dict."""
    await _refresh_settings()
    return {
        "stars": {
            "50":    float(_settings_cache.get("price_stars_50",    "75")),
            "100":   float(_settings_cache.get("price_stars_100",   "145")),
            "200":   float(_settings_cache.get("price_stars_200",   "285")),
            "250":   float(_settings_cache.get("price_stars_250",   "350")),
            "300":   float(_settings_cache.get("price_stars_300",   "420")),
            "400":   float(_settings_cache.get("price_stars_400",   "560")),
            "500":   float(_settings_cache.get("price_stars_500",   "695")),
            "1000":  float(_settings_cache.get("price_stars_1000",  "1380")),
            "2500":  float(_settings_cache.get("price_stars_2500",  "3400")),
            "5000":  float(_settings_cache.get("price_stars_5000",  "6700")),
            "10000": float(_settings_cache.get("price_stars_10000", "13200")),
        },
        "premium": {
            "3":  float(_settings_cache.get("price_premium_3",  "950")),
            "6":  float(_settings_cache.get("price_premium_6",  "1800")),
            "12": float(_settings_cache.get("price_premium_12", "3400")),
        },
        "views_per_1000":     float(_settings_cache.get("price_views_per_1000",     "30")),
        "reactions_per_1000": float(_settings_cache.get("price_reactions_per_1000", "50")),
        "members_per_1000":   float(_settings_cache.get("price_members_per_1000",   "200")),
    }


# ═══════════════════════════════════════════════════════════════════
# REFERRALS
# ═══════════════════════════════════════════════════════════════════

async def create_referral_link(code: str, label: str, created_info: str = "") -> Dict:
    data = {
        "code": code,
        "label": label,
        "created_info": created_info,
        "clicks": 0,
        "conversions": 0,
        "created_at": _now(),
    }
    res = await _run(lambda: _db().table("referral_links").insert(data).execute())
    return res.data[0]


async def get_referral_link(code: str) -> Optional[Dict]:
    res = await _run(lambda: _db().table("referral_links").select("*").eq("code", code).execute())
    return res.data[0] if res.data else None


async def increment_referral_click(code: str, user_id: int) -> None:
    link = await get_referral_link(code)
    if not link:
        return
    await _run(lambda: _db().table("referral_events").insert({
        "link_code": code, "user_id": user_id,
        "event_type": "click", "created_at": _now(),
    }).execute())
    clicks = (link["clicks"] or 0) + 1
    await _run(lambda: _db().table("referral_links").update({"clicks": clicks}).eq("code", code).execute())


async def increment_referral_conversion(code: str, user_id: int) -> None:
    link = await get_referral_link(code)
    if not link:
        return
    await _run(lambda: _db().table("referral_events").insert({
        "link_code": code, "user_id": user_id,
        "event_type": "conversion", "created_at": _now(),
    }).execute())
    conv = (link["conversions"] or 0) + 1
    await _run(lambda: _db().table("referral_links").update({"conversions": conv}).eq("code", code).execute())


async def list_referral_links() -> List[Dict]:
    res = await _run(lambda: _db().table("referral_links").select("*").order("created_at", desc=True).execute())
    return res.data


async def delete_referral_link(link_id: int) -> None:
    await _run(lambda: _db().table("referral_links").delete().eq("id", link_id).execute())


# ═══════════════════════════════════════════════════════════════════
# BROADCASTS
# ═══════════════════════════════════════════════════════════════════

async def create_broadcast(message_type: str, content: Dict, target: str) -> Dict:
    data = {
        "message_type": message_type,
        "content": content,
        "target": target,
        "status": "sending",
        "success_count": 0,
        "fail_count": 0,
        "sent_at": _now(),
    }
    res = await _run(lambda: _db().table("broadcasts").insert(data).execute())
    return res.data[0]


async def update_broadcast_stats(broadcast_id: int, success: int, fail: int) -> None:
    await _run(lambda: _db().table("broadcasts").update({
        "success_count": success,
        "fail_count": fail,
        "status": "completed",
    }).eq("id", broadcast_id).execute())


async def list_broadcasts(limit: int = 50) -> List[Dict]:
    res = await _run(lambda: _db().table("broadcasts").select("*").order("sent_at", desc=True).limit(limit).execute())
    return res.data


async def delete_broadcast(broadcast_id: int) -> None:
    await _run(lambda: _db().table("broadcasts").delete().eq("id", broadcast_id).execute())


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════

async def get_dashboard_stats() -> Dict:
    total_users = await count_users()
    pending   = await count_orders("pending")
    confirmed = await count_orders("confirmed")
    cancelled = await count_orders("cancelled")
    wrong_txn = await count_orders("wrong_txn")
    revenue   = await get_revenue_stats()
    return {
        "total_users":       total_users,
        "pending_orders":    pending,
        "confirmed_orders":  confirmed,
        "cancelled_orders":  cancelled,
        "wrong_txn_orders":  wrong_txn,
        "total_revenue":     revenue["total"],
        "revenue_by_service": revenue["by_service"],
    }
