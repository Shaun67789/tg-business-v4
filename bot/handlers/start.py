"""
/start handler with referral and channel-join flow.
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from bot import database as db
from bot.keyboards import main_menu_kb, join_channel_kb, back_to_menu_kb
from bot.utils import format_name, check_user_banned
from bot.states import START_JOIN_CHECK

logger = logging.getLogger(__name__)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    args = ctx.args or []

    # Referral code from deep link
    ref_code: str | None = None
    if args and args[0].startswith("ref_"):
        ref_code = args[0][4:]
        await db.increment_referral_click(ref_code, user.id)

    # Upsert user
    await db.upsert_user(
        telegram_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        referred_by=ref_code,
    )

    # Check if banned
    if await check_user_banned(user.id):
        await update.message.reply_text(
            "🚫 You have been banned from using this bot. Contact support if you think this is a mistake."
        )
        return ConversationHandler.END

    # Store ref_code for later
    ctx.user_data["pending_ref_code"] = ref_code

    # Check if already joined the update channel
    db_user = await db.get_user(user.id)
    if db_user and db_user.get("channel_joined"):
        return await _show_main_menu(update, ctx)

    # Must join channel first
    channel_link = await db.get_setting("update_channel_link", "https://t.me/yourchannel")
    channel_name = await db.get_setting("update_channel_name", "Our Updates Channel")

    welcome_text = (
        f"👋 <b>Welcome, {user.first_name}!</b>\n\n"
        f"To use this bot, you must first join our official update channel.\n\n"
        f"📢 <b>{channel_name}</b>\n\n"
        f"After joining, click the button below to verify and continue."
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=join_channel_kb(channel_link),
    )
    return START_JOIN_CHECK


async def check_joined_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Verify membership in channel
    channel_username = await db.get_setting("update_channel_username", "")
    if channel_username:
        try:
            member = await ctx.bot.get_chat_member(
                chat_id=f"@{channel_username.lstrip('@')}",
                user_id=user.id,
            )
            if member.status in ("member", "administrator", "creator"):
                await db.mark_channel_joined(user.id)

                # Count referral conversion
                ref_code = ctx.user_data.pop("pending_ref_code", None)
                if ref_code:
                    await db.increment_referral_conversion(ref_code, user.id)

                await query.edit_message_text(
                    f"✅ <b>Verified!</b> Welcome aboard, {user.first_name}!",
                    parse_mode=ParseMode.HTML,
                )
                return await _show_main_menu_query(update, ctx)
            else:
                channel_link = await db.get_setting("update_channel_link", "https://t.me/yourchannel")
                await query.answer("❌ You haven't joined yet! Please join first.", show_alert=True)
                return START_JOIN_CHECK
        except Exception as e:
            logger.error(f"Channel check error: {e}")
            # If we can't verify, let them pass (fallback)
            await db.mark_channel_joined(user.id)
            return await _show_main_menu_query(update, ctx)
    else:
        # No channel configured, just let them in
        await db.mark_channel_joined(user.id)
        return await _show_main_menu_query(update, ctx)


async def main_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await _show_main_menu_query(update, ctx)


async def _show_main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    welcome_msg = await db.get_setting(
        "welcome_message",
        "🛒 <b>Welcome to our service shop!</b>\n\nChoose a service to get started:"
    )
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )
    return ConversationHandler.END


async def _show_main_menu_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    welcome_msg = await db.get_setting(
        "welcome_message",
        "🛒 <b>Welcome to our service shop!</b>\n\nChoose a service to get started:"
    )
    try:
        await query.edit_message_text(
            welcome_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )
    except Exception:
        await query.message.reply_text(
            welcome_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )
    return ConversationHandler.END


async def my_orders_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Parse page
    data = query.data
    page = 0
    if data.startswith("orders_page_"):
        page = int(data.split("_")[-1])

    PAGE_SIZE = 5
    orders = await db.list_orders(limit=PAGE_SIZE, offset=page * PAGE_SIZE, user_id=user.id)
    total_orders = await db.count_orders()

    if not orders:
        await query.edit_message_text(
            "📦 <b>My Orders</b>\n\nYou have no orders yet.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_kb(),
        )
        return

    from bot.utils import service_emoji, status_emoji, escape_html
    text = "📦 <b>My Orders</b>\n\n"
    for o in orders:
        svc = escape_html(o["service"])
        oid = escape_html(o["order_id"])
        status = o["status"]
        amt = o["amount_bdt"]
        date = o["created_at"][:10]
        text += (
            f"{service_emoji(o['service'])} <b>{svc}</b> | {status_emoji(status)} {status.upper()}\n"
            f"   🆔 <code>{oid}</code> | ৳{amt:,.0f} | {date}\n\n"
        )

    from bot.keyboards import my_orders_nav_kb
    import math
    total_pages = max(1, math.ceil(total_orders / PAGE_SIZE))
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=my_orders_nav_kb(page, total_pages),
    )


async def my_referral_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    bot_username = (await ctx.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    db_user = await db.get_user(user.id)
    ref_count = 0
    if db_user:
        # Count users referred by this person
        from bot.database import _client
        import asyncio
        res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _client.table("users").select("id", count="exact")
                .eq("referred_by", str(user.id)).execute()
        )
        ref_count = res.count or 0

    text = (
        f"🔗 <b>Your Referral Link</b>\n\n"
        f"Share this link to invite friends:\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 <b>Total Referrals:</b> {ref_count}\n\n"
        f"Earn rewards for every verified referral!"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_kb(),
    )


async def support_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    support_link = await db.get_setting("support_link", "")
    support_text = await db.get_setting("support_text", "📞 Contact our support team for help with your orders.")

    from bot.keyboards import support_kb
    await query.edit_message_text(
        support_text,
        parse_mode=ParseMode.HTML,
        reply_markup=support_kb(support_link),
    )


async def my_stats_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    orders = await db.list_orders(user_id=user.id, limit=1000)
    total = len(orders)
    confirmed = sum(1 for o in orders if o["status"] == "confirmed")
    pending = sum(1 for o in orders if o["status"] == "pending")
    spent = sum(o["amount_bdt"] for o in orders if o["status"] == "confirmed")

    from bot.database import _client
    import asyncio
    res = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _client.table("users").select("id", count="exact")
            .eq("referred_by", str(user.id)).execute()
    )
    refs = res.count or 0

    text = (
        f"📊 <b>My Statistics</b>\n\n"
        f"📦 Total Orders: <b>{total}</b>\n"
        f"✅ Confirmed: <b>{confirmed}</b>\n"
        f"⏳ Pending: <b>{pending}</b>\n"
        f"💰 Total Spent: <b>৳{spent:,.2f}</b>\n"
        f"🔗 Referrals: <b>{refs}</b>\n"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_kb(),
    )
