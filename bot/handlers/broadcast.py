"""
Admin broadcast handler (triggered via /broadcast command, owner only).
"""
from __future__ import annotations
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError

from bot import database as db
from bot.config import OWNER_ID
from bot.states import BROADCAST_TEXT, BROADCAST_TYPE

logger = logging.getLogger(__name__)


async def broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    await update.message.reply_text(
        "📢 <b>Broadcast System</b>\n\n"
        "Send your broadcast message.\n\n"
        "Supported formats:\n"
        "• Text message\n"
        "• <code>IMAGE: https://url | Caption text here</code> — for image+caption\n\n"
        "Send /cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return BROADCAST_TEXT


async def broadcast_receive_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text or ""
    msg_type = "text"
    content: dict = {}

    if text.startswith("IMAGE:"):
        parts = text[6:].split("|", 1)
        img_url = parts[0].strip()
        caption = parts[1].strip() if len(parts) > 1 else ""
        msg_type = "photo"
        content = {"url": img_url, "caption": caption}
        preview_text = f"📸 <b>Photo Broadcast Preview</b>\n🔗 URL: {img_url}\n📝 Caption: {caption}"
    else:
        content = {"text": text}
        preview_text = f"📝 <b>Text Broadcast Preview</b>\n\n{text}"

    ctx.user_data["broadcast_type"] = msg_type
    ctx.user_data["broadcast_content"] = content

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 All Users", callback_data="bc_target_all"),
            InlineKeyboardButton("🎯 Specific IDs", callback_data="bc_target_specific"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="bc_cancel")]
    ])

    await update.message.reply_text(
        f"{preview_text}\n\n━━━━━━━━━━━━━━━━━━\n<b>Select broadcast target:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return BROADCAST_TYPE


async def broadcast_target_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "bc_cancel":
        ctx.user_data.clear()
        await query.edit_message_text("❌ Broadcast cancelled.")
        return ConversationHandler.END

    if query.data == "bc_target_specific":
        await query.edit_message_text(
            "🎯 <b>Send target user IDs</b> separated by commas:\n<i>e.g. 123456789, 987654321</i>",
            parse_mode=ParseMode.HTML,
        )
        ctx.user_data["broadcast_target"] = "specific"
        return BROADCAST_TYPE

    # All users
    await query.edit_message_text("⏳ Starting broadcast to all users...")
    await _execute_broadcast(ctx, "all", None, query.message)
    return ConversationHandler.END


async def broadcast_specific_ids(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text or ""
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use comma-separated IDs.")
        return BROADCAST_TYPE

    if not ids:
        await update.message.reply_text("❌ No valid IDs found.")
        return BROADCAST_TYPE

    await update.message.reply_text(f"⏳ Broadcasting to {len(ids)} users...")
    await _execute_broadcast(ctx, "specific", ids, update.message)
    return ConversationHandler.END


async def _execute_broadcast(ctx: ContextTypes.DEFAULT_TYPE, target: str, ids, reply_msg):
    msg_type = ctx.user_data.get("broadcast_type", "text")
    content = ctx.user_data.get("broadcast_content", {})

    if target == "all":
        user_ids = await db.get_all_user_ids()
    else:
        user_ids = ids or []

    bc_record = await db.create_broadcast(msg_type, content, target)
    bc_id = bc_record["id"]

    success = 0
    fail = 0

    for uid in user_ids:
        try:
            if msg_type == "photo":
                await ctx.bot.send_photo(
                    chat_id=uid,
                    photo=content["url"],
                    caption=content.get("caption", ""),
                    parse_mode=ParseMode.HTML,
                )
            else:
                await ctx.bot.send_message(
                    chat_id=uid,
                    text=content["text"],
                    parse_mode=ParseMode.HTML,
                )
            success += 1
        except TelegramError:
            fail += 1
        await asyncio.sleep(0.05)  # Rate limit safety

    await db.update_broadcast_stats(bc_id, success, fail)

    report = (
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"✅ Success: <b>{success}</b>\n"
        f"❌ Failed: <b>{fail}</b>\n"
        f"📊 Total: <b>{success + fail}</b>"
    )
    try:
        await reply_msg.reply_text(report, parse_mode=ParseMode.HTML)
    except Exception:
        pass

    ctx.user_data.clear()
