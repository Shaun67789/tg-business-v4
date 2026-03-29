"""
Owner approval callbacks — handles confirm/wrong_txn/cancel for all order types.
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

from bot import database as db
from bot.utils import notify_log_group, escape_html, status_emoji, service_emoji

logger = logging.getLogger(__name__)

STATUS_MAP = {
    "ow_confirm": ("confirmed", "✅ Confirmed"),
    "ow_wrongtxn": ("wrong_txn", "❌ Wrong Transaction ID"),
    "ow_cancel": ("cancelled", "🚫 Cancelled"),
}

USER_MESSAGES = {
    "confirmed": (
        "✅ <b>Order Confirmed!</b>\n\n"
        "🆔 Order ID: <code>{order_id}</code>\n"
        "🛒 Service: {service}\n\n"
        "Your order has been <b>confirmed</b> and is now being processed. Thank you! 🙏"
    ),
    "wrong_txn": (
        "❌ <b>Wrong Transaction ID</b>\n\n"
        "🆔 Order ID: <code>{order_id}</code>\n\n"
        "The transaction ID you provided could not be verified. "
        "Please check and place a new order with the correct ID.\n\n"
        "Contact support if you need help. 💬"
    ),
    "cancelled": (
        "🚫 <b>Order Cancelled</b>\n\n"
        "🆔 Order ID: <code>{order_id}</code>\n\n"
        "Your order has been cancelled by the admin. "
        "Please contact support for more information. 💬"
    ),
}


async def owner_review_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Only owner can use these buttons
    from bot.config import OWNER_ID
    if user.id != OWNER_ID:
        await query.answer("⛔ You are not authorized.", show_alert=True)
        return

    data = query.data  # e.g. "ow_confirm_ORD-ABCD1234"
    parts = data.split("_", 2)
    action_key = f"{parts[0]}_{parts[1]}"  # "ow_confirm"
    order_id = parts[2] if len(parts) > 2 else ""

    if action_key not in STATUS_MAP:
        return

    new_status, label = STATUS_MAP[action_key]

    # Update order in DB
    order = await db.get_order(order_id)
    if not order:
        await query.answer("Order not found.", show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer(f"Order already {order['status']}.", show_alert=True)
        return

    await db.update_order_status(order_id, new_status)

    # Notify user
    customer_id = order["user_id"]
    svc = f"{service_emoji(order['service'])} {order['service'].title()}"
    user_msg = USER_MESSAGES[new_status].format(order_id=order_id, service=svc)
    try:
        await ctx.bot.send_message(
            chat_id=customer_id,
            text=user_msg,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        logger.warning(f"Could not notify customer {customer_id}: {e}")

    # Update the owner's message
    original = query.message.text or ""
    await query.edit_message_text(
        f"{original}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Decision:</b> {label}\n"
        f"<b>By:</b> @{escape_html(user.username or str(user.id))}",
        parse_mode=ParseMode.HTML,
    )

    # Log to group
    await notify_log_group(
        ctx.bot,
        f"📋 <b>ORDER UPDATE</b>\n\n"
        f"🆔 {order_id}\n"
        f"Status: <b>{label}</b>\n"
        f"Customer ID: <code>{customer_id}</code>"
    )
