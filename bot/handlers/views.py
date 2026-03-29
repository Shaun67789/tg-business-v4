"""
Post Views ordering flow (price per 1000, user provides post link + amount).
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from bot import database as db
from bot.keyboards import confirm_cancel_kb, owner_review_kb, cancel_kb, back_to_menu_kb
from bot.utils import (
    validate_post_link, calculate_price, escape_html,
    format_order_summary_user, format_order_summary_owner,
    notify_owner, notify_log_group, generate_order_id
)
from bot.states import VIEWS_LINK, VIEWS_AMOUNT, VIEWS_TXN, VIEWS_CONFIRM

logger = logging.getLogger(__name__)


async def views_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    prices = await db.get_price_config()
    per_1000 = prices["views_per_1000"]
    note = await db.get_setting("payment_note_views", "👁 Send exact BDT via Nagad/bKash and submit TXN ID.")

    await query.edit_message_text(
        f"👁 <b>Post Views</b>\n\n"
        f"💰 <b>Price:</b> ৳{per_1000:,.2f} per 1,000 views\n\n"
        f"{note}\n\n"
        f"📎 <b>Please send the Telegram post link:</b>\n"
        f"<i>Example: https://t.me/channel/123</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_kb(),
    )
    return VIEWS_LINK


async def views_link_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not validate_post_link(link):
        await update.message.reply_text(
            "❌ Invalid post link. Please send a valid Telegram post link:\n"
            "<i>https://t.me/channelname/123</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_kb(),
        )
        return VIEWS_LINK

    ctx.user_data["views_link"] = link
    prices = await db.get_price_config()
    per_1000 = prices["views_per_1000"]

    await update.message.reply_text(
        f"✅ Link saved!\n\n"
        f"💰 Price: ৳{per_1000:,.2f} per 1,000 views\n\n"
        f"<b>How many views do you want?</b> (Minimum: 1000)\n"
        f"Enter a number (e.g. 5000):",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_kb(),
    )
    return VIEWS_AMOUNT


async def views_amount_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) < 100:
        await update.message.reply_text("❌ Please enter a valid number (minimum 100):", reply_markup=cancel_kb())
        return VIEWS_AMOUNT

    amount = int(text)
    prices = await db.get_price_config()
    per_1000 = prices["views_per_1000"]
    total_bdt = calculate_price(amount, per_1000)
    ctx.user_data.update({"views_amount": amount, "views_price_bdt": total_bdt})

    payment_info = await db.get_setting("nagad_bkash_info", "📲 Nagad: 01xxxxxxxxx\n📲 bKash: 01xxxxxxxxx")

    await update.message.reply_text(
        f"👁 <b>Views: {amount:,}</b>\n"
        f"💰 <b>Total: ৳{total_bdt:,.2f}</b>\n\n"
        f"{payment_info}\n\n"
        f"📝 Please send exactly <b>৳{total_bdt:,.2f}</b> and enter your Transaction ID:",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_kb(),
    )
    return VIEWS_TXN


async def views_txn_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    txn_id = update.message.text.strip()
    user = update.effective_user

    if len(txn_id) < 4:
        await update.message.reply_text("❌ Invalid TXN ID. Please try again:", reply_markup=cancel_kb())
        return VIEWS_TXN

    order_id = generate_order_id()
    ctx.user_data.update({"views_txn_id": txn_id, "views_order_id": order_id})

    amount = ctx.user_data["views_amount"]
    price_bdt = ctx.user_data["views_price_bdt"]
    link = ctx.user_data["views_link"]

    details = {"Post Link": link, "Views Amount": f"{amount:,}"}
    summary = format_order_summary_user("👁 Post Views", user, details, txn_id, order_id, price_bdt)

    await update.message.reply_text(summary, parse_mode=ParseMode.HTML, reply_markup=confirm_cancel_kb(order_id))
    return VIEWS_CONFIRM


async def views_place_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("⏳ Placing order...")
    user = update.effective_user

    txn_id = ctx.user_data.get("views_txn_id", "")
    amount = ctx.user_data.get("views_amount", 0)
    price_bdt = ctx.user_data.get("views_price_bdt", 0)
    link = ctx.user_data.get("views_link", "")

    details = {"Post Link": link, "Views Amount": f"{amount:,}", "Telegram ID": str(user.id)}
    order = await db.create_order(user.id, "views", details, txn_id, price_bdt)

    owner_text = format_order_summary_owner("👁 Post Views", user, details, txn_id, order["order_id"], price_bdt)
    await notify_owner(ctx.bot, owner_text, reply_markup=owner_review_kb(order["order_id"]))
    await notify_log_group(ctx.bot, f"📥 NEW VIEWS ORDER\n\n{owner_text}")

    await query.edit_message_text(
        f"✅ <b>Views Order Placed!</b>\n\n🆔 <code>{order['order_id']}</code>\n\n⏳ Processing soon.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_kb(),
    )
    ctx.user_data.clear()
    return ConversationHandler.END
