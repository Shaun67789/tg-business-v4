"""
Members ordering flow (channel/group link + amount).
"""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from bot import database as db
from bot.keyboards import confirm_cancel_kb, owner_review_kb, cancel_kb, back_to_menu_kb
from bot.utils import (
    validate_channel_link, calculate_price, format_order_summary_user,
    format_order_summary_owner, notify_owner, notify_log_group, generate_order_id, escape_html
)
from bot.states import MEMBERS_LINK, MEMBERS_AMOUNT, MEMBERS_TXN, MEMBERS_CONFIRM


async def members_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prices = await db.get_price_config()
    per_1000 = prices["members_per_1000"]
    note = await db.get_setting("payment_note_members", "👥 ⚠️ No guarantee on members. Send payment after confirmation.")
    await query.edit_message_text(
        f"👥 <b>Members [⚠️ No Guarantee]</b>\n\n"
        f"💰 ৳{per_1000:,.2f} per 1,000 members\n\n"
        f"⚠️ <b>Note:</b> Members may drop. We do NOT guarantee retention.\n\n"
        f"{note}\n\n"
        f"🔗 <b>Send your channel or group link/username:</b>",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb(),
    )
    return MEMBERS_LINK


async def members_link_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not validate_channel_link(link):
        await update.message.reply_text(
            "❌ Invalid link. Send @username or https://t.me/username:", reply_markup=cancel_kb()
        )
        return MEMBERS_LINK
    ctx.user_data["members_link"] = link
    prices = await db.get_price_config()
    per_1000 = prices["members_per_1000"]
    await update.message.reply_text(
        f"✅ Link: <code>{escape_html(link)}</code>\n💰 ৳{per_1000:,.2f}/1,000\n\n<b>How many members?</b> (min 100):",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb()
    )
    return MEMBERS_AMOUNT


async def members_amount_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) < 100:
        await update.message.reply_text("❌ Enter a valid number (min 100):", reply_markup=cancel_kb())
        return MEMBERS_AMOUNT
    amount = int(text)
    prices = await db.get_price_config()
    total_bdt = calculate_price(amount, prices["members_per_1000"])
    ctx.user_data.update({"members_amount": amount, "members_price_bdt": total_bdt})
    payment_info = await db.get_setting("nagad_bkash_info", "📲 Nagad: 01xxxxxxxxx")
    await update.message.reply_text(
        f"👥 Members: <b>{amount:,}</b>\n💰 Total: <b>৳{total_bdt:,.2f}</b>\n\n{payment_info}\n\nEnter Transaction ID:",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb()
    )
    return MEMBERS_TXN


async def members_txn_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    txn_id = update.message.text.strip()
    user = update.effective_user
    if len(txn_id) < 4:
        await update.message.reply_text("❌ Invalid. Try again:", reply_markup=cancel_kb())
        return MEMBERS_TXN
    order_id = generate_order_id()
    ctx.user_data.update({"members_txn_id": txn_id, "members_order_id": order_id})
    details = {"Channel/Group": ctx.user_data["members_link"], "Members": f"{ctx.user_data['members_amount']:,}"}
    summary = format_order_summary_user("👥 Members", user, details, txn_id, order_id, ctx.user_data["members_price_bdt"])
    await update.message.reply_text(summary, parse_mode=ParseMode.HTML, reply_markup=confirm_cancel_kb(order_id))
    return MEMBERS_CONFIRM


async def members_place_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    txn_id = ctx.user_data["members_txn_id"]
    amount = ctx.user_data["members_amount"]
    price_bdt = ctx.user_data["members_price_bdt"]
    link = ctx.user_data["members_link"]
    details = {"Channel/Group": link, "Members": f"{amount:,}", "Telegram ID": str(user.id)}
    order = await db.create_order(user.id, "members", details, txn_id, price_bdt)
    owner_text = format_order_summary_owner("👥 Members", user, details, txn_id, order["order_id"], price_bdt)
    await notify_owner(ctx.bot, owner_text, reply_markup=owner_review_kb(order["order_id"]))
    await notify_log_group(ctx.bot, f"📥 NEW MEMBERS ORDER\n\n{owner_text}")
    await query.edit_message_text(
        f"✅ <b>Members Order Placed!</b>\n🆔 <code>{order['order_id']}</code>\n\n⏳ Processing.",
        parse_mode=ParseMode.HTML, reply_markup=back_to_menu_kb()
    )
    ctx.user_data.clear()
    return ConversationHandler.END
