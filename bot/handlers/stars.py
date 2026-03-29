"""
Telegram Stars ordering flow.
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from bot import database as db
from bot.keyboards import stars_amount_kb, confirm_cancel_kb, owner_review_kb, cancel_kb, back_to_menu_kb
from bot.utils import (
    format_name, escape_html, format_order_summary_user,
    format_order_summary_owner, notify_owner, notify_log_group, now_str
)
from bot.states import STARS_AMOUNT, STARS_TXN, STARS_CONFIRM

logger = logging.getLogger(__name__)


async def stars_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry from main menu callback button."""
    query = update.callback_query
    await query.answer("Please select the star amount to buy! ⭐", show_alert=True)

    prices = await db.get_price_config()
    payment_note = await db.get_setting("payment_note_stars", "💳 Please send the payment via <b>Nagad/bKash</b> to our number.")

    text = (
        f"🌟 <b>Telegram Stars</b>\n\n"
        f"{payment_note}\n\n"
        f"<b>Select the amount of Stars you want to buy:</b>"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=stars_amount_kb(prices["stars"]),
    )
    return STARS_AMOUNT


async def stars_amount_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    amount_str = query.data.replace("stars_", "")
    amount = int(amount_str)

    prices = await db.get_price_config()
    price_bdt = prices["stars"].get(amount_str, 0)

    ctx.user_data.update({
        "stars_amount": amount,
        "stars_price_bdt": price_bdt,
    })

    payment_info = await db.get_setting(
        "nagad_bkash_info",
        "📲 <b>Nagad:</b> 01xxxxxxxxx (Personal)\n📲 <b>bKash:</b> 01xxxxxxxxx (Personal)"
    )
    payment_note = await db.get_setting("payment_note_stars", "Send payment and enter Transaction ID below.")

    text = (
        f"⭐ <b>Stars Selected: {amount:,}</b>\n"
        f"💰 <b>Price: ৳{price_bdt:,.2f}</b>\n\n"
        f"{payment_info}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{payment_note}\n\n"
        f"📝 <b>Please send the Transaction ID to complete your order:</b>"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_kb(),
    )
    return STARS_TXN


async def stars_txn_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    txn_id = update.message.text.strip()
    user = update.effective_user

    if len(txn_id) < 4:
        await update.message.reply_text(
            "❌ Transaction ID seems too short. Please enter a valid Transaction ID:",
            reply_markup=cancel_kb(),
        )
        return STARS_TXN

    amount = ctx.user_data["stars_amount"]
    price_bdt = ctx.user_data["stars_price_bdt"]

    from bot.utils import generate_order_id
    order_id = generate_order_id()
    ctx.user_data["stars_txn_id"] = txn_id
    ctx.user_data["stars_order_id"] = order_id

    details = {"Stars Amount": f"{amount:,}", "Delivery Telegram": f"@{user.username or 'N/A'}"}
    summary = format_order_summary_user(
        service="🌟 Telegram Stars",
        user=user,
        details=details,
        txn_id=txn_id,
        order_id=order_id,
        amount_bdt=price_bdt,
    )
    await update.message.reply_text(
        summary,
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_cancel_kb(order_id),
    )
    return STARS_CONFIRM


async def stars_place_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("⏳ Placing your order...")
    user = update.effective_user

    order_id = query.data.replace("place_", "")
    txn_id = ctx.user_data.get("stars_txn_id", "")
    amount = ctx.user_data.get("stars_amount", 0)
    price_bdt = ctx.user_data.get("stars_price_bdt", 0)

    details = {"Stars Amount": f"{amount:,}", "Delivery Account": f"@{user.username or 'N/A'}", "Telegram ID": str(user.id)}

    # Save to DB
    order = await db.create_order(
        user_id=user.id,
        service="stars",
        details=details,
        txn_id=txn_id,
        amount_bdt=price_bdt,
    )

    # Notify owner
    owner_text = format_order_summary_owner(
        service="🌟 Telegram Stars",
        user=user,
        details=details,
        txn_id=txn_id,
        order_id=order["order_id"],
        amount_bdt=price_bdt,
    )
    await notify_owner(ctx.bot, owner_text, reply_markup=owner_review_kb(order["order_id"]))
    await notify_log_group(ctx.bot, f"📥 NEW ORDER\n\n{owner_text}")

    await query.edit_message_text(
        f"✅ <b>Order Placed Successfully!</b>\n\n"
        f"🆔 Order ID: <code>{order['order_id']}</code>\n\n"
        f"⏳ Your order is under review. You will be notified once confirmed.\n\n"
        f"Thank you for your purchase! 🙏",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_kb(),
    )
    ctx.user_data.clear()
    return ConversationHandler.END


async def cancel_order_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Order cancelled.")
    ctx.user_data.clear()
    await query.edit_message_text(
        "❌ <b>Order Cancelled.</b>\n\nYou can start a new order anytime.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_kb(),
    )
    return ConversationHandler.END


async def generic_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer("Cancelled.")
        ctx.user_data.clear()
        await update.callback_query.edit_message_text(
            "❌ Cancelled. Use /start to return to the menu.",
            reply_markup=back_to_menu_kb(),
        )
    elif update.message:
        ctx.user_data.clear()
        await update.message.reply_text(
            "❌ Cancelled. Use /start to return to the menu.",
            reply_markup=back_to_menu_kb(),
        )
    return ConversationHandler.END
