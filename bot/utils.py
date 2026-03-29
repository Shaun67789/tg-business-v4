"""
Utility functions shared across handlers.
"""
from __future__ import annotations
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from telegram import Bot, Message
from telegram.constants import ParseMode
from telegram.error import TelegramError

from bot.config import OWNER_ID, LOG_GROUP_ID
from bot import database as db

logger = logging.getLogger(__name__)


def generate_order_id() -> str:
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_name(user) -> str:
    name = user.first_name or ""
    if user.last_name:
        name += f" {user.last_name}"
    return name.strip() or "Unknown"


def escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def validate_post_link(link: str) -> bool:
    """Validate a Telegram post link."""
    pattern = r"^https?://t\.me/.+/\d+"
    return bool(re.match(pattern, link.strip()))


def validate_channel_link(link: str) -> bool:
    """Validate a Telegram channel/group link."""
    pattern = r"^(https?://t\.me/|@)[a-zA-Z0-9_]+"
    return bool(re.match(pattern, link.strip()))


def calculate_price(amount: int, price_per_1000: float) -> float:
    return round((amount / 1000.0) * price_per_1000, 2)


async def notify_log_group(bot: Bot, text: str, reply_markup=None) -> Optional[Message]:
    """Send a message to the owner's log group."""
    if not LOG_GROUP_ID or LOG_GROUP_ID == 0:
        return None
    try:
        return await bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramError as e:
        logger.error(f"Failed to send to log group: {e}")
        return None


async def notify_owner(bot: Bot, text: str, reply_markup=None) -> Optional[Message]:
    """Send a message to the bot owner."""
    try:
        return await bot.send_message(
            chat_id=OWNER_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramError as e:
        logger.error(f"Failed to notify owner: {e}")
        return None


def format_order_summary_user(
    service: str,
    user,
    details: Dict[str, Any],
    txn_id: str,
    order_id: str,
    amount_bdt: float,
) -> str:
    name = escape_html(format_name(user))
    username = f"@{escape_html(user.username)}" if user.username else "No username"

    detail_lines = "\n".join(
        f"  • <b>{escape_html(k.replace('_', ' ').title())}:</b> {escape_html(str(v))}"
        for k, v in details.items()
    )

    return (
        f"📋 <b>Order Summary</b>\n\n"
        f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
        f"🛒 <b>Service:</b> {escape_html(service)}\n"
        f"👤 <b>Name:</b> {name}\n"
        f"📱 <b>Username:</b> {username}\n"
        f"💳 <b>Transaction ID:</b> <code>{escape_html(txn_id)}</code>\n"
        f"💰 <b>Amount:</b> ৳{amount_bdt:,.2f}\n"
        f"📦 <b>Details:</b>\n{detail_lines}\n"
        f"🕒 <b>Date/Time:</b> {now_str()}\n\n"
        f"Please confirm or cancel your order below."
    )


def format_order_summary_owner(
    service: str,
    user,
    details: Dict[str, Any],
    txn_id: str,
    order_id: str,
    amount_bdt: float,
) -> str:
    name = escape_html(format_name(user))
    username = f"@{escape_html(user.username)}" if user.username else "No username"

    detail_lines = "\n".join(
        f"  • <b>{escape_html(k.replace('_', ' ').title())}:</b> {escape_html(str(v))}"
        for k, v in details.items()
    )

    return (
        f"🔔 <b>NEW ORDER — {escape_html(service.upper())}</b>\n\n"
        f"🆔 Order ID: <code>{order_id}</code>\n"
        f"👤 Customer: {name} ({username})\n"
        f"🔑 Telegram ID: <code>{user.id}</code>\n"
        f"💳 TXN ID: <code>{escape_html(txn_id)}</code>\n"
        f"💰 Amount: ৳{amount_bdt:,.2f}\n"
        f"📦 Details:\n{detail_lines}\n"
        f"🕒 Time: {now_str()}"
    )


async def check_user_banned(telegram_id: int) -> bool:
    user = await db.get_user(telegram_id)
    return user is not None and user.get("is_banned", False)


def service_emoji(service: str) -> str:
    return {
        "stars": "🌟",
        "premium": "💎",
        "views": "👁",
        "reactions": "❤️",
        "members": "👥",
    }.get(service, "📦")


def status_emoji(status: str) -> str:
    return {
        "pending": "⏳",
        "confirmed": "✅",
        "cancelled": "🚫",
        "wrong_txn": "❌",
    }.get(status, "❓")
