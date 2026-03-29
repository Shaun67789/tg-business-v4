"""
Telegram Premium ordering flow.
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from bot import database as db
from bot.keyboards import premium_duration_kb, confirm_cancel_kb, owner_review_kb, cancel_kb, back_to_menu_kb
from bot.utils import (
    format_order_summary_user, format_order_summary_owner,
    notify_owner, notify_log_group, generate_order_id, escape_html
)
from bot.states import PREMIUM_DURATION, PREMIUM_USERNAME, PREMIUM_TXN, PREMIUM_CONFIRM

logger = logging.getLogger(__name__)

DURATION_LABELS = {"3": "3 Months", "6": "6 Months", "12": "12 Months"}


async def premium_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    prices = await db.get_price_config()
    payment_note = await db.get_setting("payment_note_premium", "💎 Pay via Nagad/bKash and submit Transaction ID.")

    text = (
        f"💎 <b>Telegram Premium</b>\n\n"
        f"{payment_note}\n\n"
        f"<b>Select subscription duration:</b>"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=premium_duration_kb(prices["premium"]),
    )
    return PREMIUM_DURATION


async def premium_duration_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    duration = query.data.replace("premium_", "")
    prices = await db.get_price_config()
    price_bdt = prices["premium"].get(duration, 0)
    label = DURATION_LABELS.get(duration, f"{duration} months")

    ctx.user_data.update({"premium_duration": duration, "premium_price_bdt": price_bdt, "premium_label": label})

    await query.edit_message_text(
        f"💎 <b>Premium Selected: {label}</b>\n"
        f"💰 <b>Price: ৳{price_bdt:,.2f}</b>\n\n"
        f"📝 <b>Please enter the Telegram username or phone number of the account to receive Premium:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_kb(),
    )
    return PREMIUM_USERNAME


async def premium_username_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    target = update.message.text.strip()
    ctx.user_data["premium_target"] = target

    payment_info = await db.get_setting(
        "nagad_bkash_info",
        "📲 <b>Nagad:</b> 01xxxxxxxxx\n📲 <b>bKash:</b> 01xxxxxxxxx"
    )
    price_bdt = ctx.user_data["premium_price_bdt"]
    label = ctx.user_data["premium_label"]

    text = (
        f"💎 <b>Premium: {label}</b>\n"
        f"👤 <b>Target Account:</b> {escape_html(target)}\n"
        f"💰 <b>Amount to Pay: ৳{price_bdt:,.2f}</b>\n\n"
        f"{payment_info}\n\n"
        f"📝 <b>Now enter your Transaction ID:</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=cancel_kb())
    return PREMIUM_TXN


async def premium_txn_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    txn_id = update.message.text.strip()
    user = update.effective_user

    if len(txn_id) < 4:
        await update.message.reply_text("❌ Invalid Transaction ID. Please enter again:", reply_markup=cancel_kb())
        return PREMIUM_TXN

    order_id = generate_order_id()
    ctx.user_data.update({"premium_txn_id": txn_id, "premium_order_id": order_id})

    label = ctx.user_data["premium_label"]
    price_bdt = ctx.user_data["premium_price_bdt"]
    target = ctx.user_data["premium_target"]

    details = {"Duration": label, "Target Account": target}
    summary = format_order_summary_user("💎 Telegram Premium", user, details, txn_id, order_id, price_bdt)

    await update.message.reply_text(summary, parse_mode=ParseMode.HTML, reply_markup=confirm_cancel_kb(order_id))
    return PREMIUM_CONFIRM


async def premium_place_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("⏳ Placing your order...")
    user = update.effective_user

    txn_id = ctx.user_data.get("premium_txn_id", "")
    price_bdt = ctx.user_data.get("premium_price_bdt", 0)
    label = ctx.user_data.get("premium_label", "")
    target = ctx.user_data.get("premium_target", "")

    details = {"Duration": label, "Target Account": target, "Telegram ID": str(user.id)}

    order = await db.create_order(user.id, "premium", details, txn_id, price_bdt)

    owner_text = format_order_summary_owner("💎 Telegram Premium", user, details, txn_id, order["order_id"], price_bdt)
    await notify_owner(ctx.bot, owner_text, reply_markup=owner_review_kb(order["order_id"]))
    await notify_log_group(ctx.bot, f"📥 NEW ORDER\n\n{owner_text}")

    await query.edit_message_text(
        f"✅ <b>Order Placed!</b>\n\n🆔 Order ID: <code>{order['order_id']}</code>\n\n⏳ Awaiting confirmation.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_kb(),
    )
    ctx.user_data.clear()
    return ConversationHandler.END
