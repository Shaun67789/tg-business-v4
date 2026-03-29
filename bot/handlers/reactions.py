"""
Post Reactions ordering flow.
"""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from bot import database as db
from bot.keyboards import confirm_cancel_kb, owner_review_kb, cancel_kb, back_to_menu_kb
from bot.utils import (
    validate_post_link, calculate_price, format_order_summary_user,
    format_order_summary_owner, notify_owner, notify_log_group, generate_order_id
)
from bot.states import REACTIONS_LINK, REACTIONS_AMOUNT, REACTIONS_TXN, REACTIONS_CONFIRM


async def reactions_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prices = await db.get_price_config()
    per_1000 = prices["reactions_per_1000"]
    note = await db.get_setting("payment_note_reactions", "❤️ Send exact BDT via Nagad/bKash.")
    await query.edit_message_text(
        f"❤️ <b>Post Reactions</b>\n\n💰 ৳{per_1000:,.2f} per 1,000 reactions\n\n{note}\n\n"
        f"📎 <b>Send the post link:</b>",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb(),
    )
    return REACTIONS_LINK


async def reactions_link_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not validate_post_link(link):
        await update.message.reply_text("❌ Invalid link. Send a valid Telegram post link:", reply_markup=cancel_kb())
        return REACTIONS_LINK
    ctx.user_data["reactions_link"] = link
    prices = await db.get_price_config()
    per_1000 = prices["reactions_per_1000"]
    await update.message.reply_text(
        f"✅ Saved!\n💰 ৳{per_1000:,.2f} / 1,000 reactions\n\n<b>How many reactions?</b> (min 100):",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb()
    )
    return REACTIONS_AMOUNT


async def reactions_amount_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) < 100:
        await update.message.reply_text("❌ Enter a valid number (min 100):", reply_markup=cancel_kb())
        return REACTIONS_AMOUNT
    amount = int(text)
    prices = await db.get_price_config()
    total_bdt = calculate_price(amount, prices["reactions_per_1000"])
    ctx.user_data.update({"reactions_amount": amount, "reactions_price_bdt": total_bdt})
    payment_info = await db.get_setting("nagad_bkash_info", "📲 Nagad: 01xxxxxxxxx")
    await update.message.reply_text(
        f"❤️ Reactions: <b>{amount:,}</b>\n💰 Total: <b>৳{total_bdt:,.2f}</b>\n\n{payment_info}\n\n"
        f"Enter Transaction ID:",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb()
    )
    return REACTIONS_TXN


async def reactions_txn_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    txn_id = update.message.text.strip()
    user = update.effective_user
    if len(txn_id) < 4:
        await update.message.reply_text("❌ Invalid. Try again:", reply_markup=cancel_kb())
        return REACTIONS_TXN
    order_id = generate_order_id()
    ctx.user_data.update({"reactions_txn_id": txn_id, "reactions_order_id": order_id})
    details = {"Post Link": ctx.user_data["reactions_link"], "Reactions": f"{ctx.user_data['reactions_amount']:,}"}
    summary = format_order_summary_user("❤️ Post Reactions", user, details, txn_id, order_id, ctx.user_data["reactions_price_bdt"])
    await update.message.reply_text(summary, parse_mode=ParseMode.HTML, reply_markup=confirm_cancel_kb(order_id))
    return REACTIONS_CONFIRM


async def reactions_place_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    txn_id = ctx.user_data["reactions_txn_id"]
    amount = ctx.user_data["reactions_amount"]
    price_bdt = ctx.user_data["reactions_price_bdt"]
    link = ctx.user_data["reactions_link"]
    details = {"Post Link": link, "Reactions": f"{amount:,}", "Telegram ID": str(user.id)}
    order = await db.create_order(user.id, "reactions", details, txn_id, price_bdt)
    owner_text = format_order_summary_owner("❤️ Post Reactions", user, details, txn_id, order["order_id"], price_bdt)
    await notify_owner(ctx.bot, owner_text, reply_markup=owner_review_kb(order["order_id"]))
    await notify_log_group(ctx.bot, f"📥 NEW REACTIONS ORDER\n\n{owner_text}")
    await query.edit_message_text(
        f"✅ <b>Reactions Order Placed!</b>\n🆔 <code>{order['order_id']}</code>\n\n⏳ Processing.",
        parse_mode=ParseMode.HTML, reply_markup=back_to_menu_kb()
    )
    ctx.user_data.clear()
    return ConversationHandler.END
