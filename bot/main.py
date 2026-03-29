"""
Bot Application — wires all handlers together.
Runs as a webhook (integrated with FastAPI).
"""
from __future__ import annotations
import logging
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)

from bot.config import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_URL
from bot.states import (
    START_JOIN_CHECK,
    STARS_AMOUNT, STARS_TXN, STARS_CONFIRM,
    PREMIUM_DURATION, PREMIUM_USERNAME, PREMIUM_TXN, PREMIUM_CONFIRM,
    VIEWS_LINK, VIEWS_AMOUNT, VIEWS_TXN, VIEWS_CONFIRM,
    REACTIONS_LINK, REACTIONS_AMOUNT, REACTIONS_TXN, REACTIONS_CONFIRM,
    MEMBERS_LINK, MEMBERS_AMOUNT, MEMBERS_TXN, MEMBERS_CONFIRM,
    BROADCAST_TEXT, BROADCAST_TYPE,
)

from bot.handlers import start as start_h
from bot.handlers import stars as stars_h
from bot.handlers import premium as premium_h
from bot.handlers import views as views_h
from bot.handlers import reactions as reactions_h
from bot.handlers import members as members_h
from bot.handlers import orders as orders_h
from bot.handlers import broadcast as bc_h

logger = logging.getLogger(__name__)

_app: Application | None = None


def build_application() -> Application:
    global _app

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Start / Onboarding ──────────────────────────────────────
    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_h.start)],
        states={
            START_JOIN_CHECK: [
                CallbackQueryHandler(start_h.check_joined_callback, pattern="^check_joined$"),
            ],
        },
        fallbacks=[CommandHandler("start", start_h.start)],
        allow_reentry=True,
    )
    app.add_handler(start_conv)

    # ── Telegram Stars ───────────────────────────────────────────
    stars_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(stars_h.stars_entry, pattern="^svc_stars$")],
        states={
            STARS_AMOUNT: [CallbackQueryHandler(stars_h.stars_amount_selected, pattern=r"^stars_\d+$")],
            STARS_TXN: [MessageHandler(filters.TEXT & ~filters.COMMAND, stars_h.stars_txn_received)],
            STARS_CONFIRM: [
                CallbackQueryHandler(stars_h.stars_place_order, pattern=r"^place_ORD-"),
                CallbackQueryHandler(stars_h.cancel_order_callback, pattern=r"^cancel_ord_"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(stars_h.generic_cancel, pattern="^cancel$"),
            CallbackQueryHandler(start_h.main_menu_callback, pattern="^main_menu$"),
            CommandHandler("cancel", stars_h.generic_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(stars_conv)

    # ── Telegram Premium ─────────────────────────────────────────
    premium_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(premium_h.premium_entry, pattern="^svc_premium$")],
        states={
            PREMIUM_DURATION: [CallbackQueryHandler(premium_h.premium_duration_selected, pattern=r"^premium_\d+$")],
            PREMIUM_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, premium_h.premium_username_received)],
            PREMIUM_TXN: [MessageHandler(filters.TEXT & ~filters.COMMAND, premium_h.premium_txn_received)],
            PREMIUM_CONFIRM: [
                CallbackQueryHandler(premium_h.premium_place_order, pattern=r"^place_ORD-"),
                CallbackQueryHandler(stars_h.cancel_order_callback, pattern=r"^cancel_ord_"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(stars_h.generic_cancel, pattern="^cancel$"),
            CallbackQueryHandler(start_h.main_menu_callback, pattern="^main_menu$"),
            CommandHandler("cancel", stars_h.generic_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(premium_conv)

    # ── Post Views ───────────────────────────────────────────────
    views_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(views_h.views_entry, pattern="^svc_views$")],
        states={
            VIEWS_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, views_h.views_link_received)],
            VIEWS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, views_h.views_amount_received)],
            VIEWS_TXN: [MessageHandler(filters.TEXT & ~filters.COMMAND, views_h.views_txn_received)],
            VIEWS_CONFIRM: [
                CallbackQueryHandler(views_h.views_place_order, pattern=r"^place_ORD-"),
                CallbackQueryHandler(stars_h.cancel_order_callback, pattern=r"^cancel_ord_"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(stars_h.generic_cancel, pattern="^cancel$"),
            CallbackQueryHandler(start_h.main_menu_callback, pattern="^main_menu$"),
            CommandHandler("cancel", stars_h.generic_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(views_conv)

    # ── Post Reactions ───────────────────────────────────────────
    reactions_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(reactions_h.reactions_entry, pattern="^svc_reactions$")],
        states={
            REACTIONS_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, reactions_h.reactions_link_received)],
            REACTIONS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reactions_h.reactions_amount_received)],
            REACTIONS_TXN: [MessageHandler(filters.TEXT & ~filters.COMMAND, reactions_h.reactions_txn_received)],
            REACTIONS_CONFIRM: [
                CallbackQueryHandler(reactions_h.reactions_place_order, pattern=r"^place_ORD-"),
                CallbackQueryHandler(stars_h.cancel_order_callback, pattern=r"^cancel_ord_"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(stars_h.generic_cancel, pattern="^cancel$"),
            CallbackQueryHandler(start_h.main_menu_callback, pattern="^main_menu$"),
            CommandHandler("cancel", stars_h.generic_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(reactions_conv)

    # ── Members ──────────────────────────────────────────────────
    members_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(members_h.members_entry, pattern="^svc_members$")],
        states={
            MEMBERS_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, members_h.members_link_received)],
            MEMBERS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, members_h.members_amount_received)],
            MEMBERS_TXN: [MessageHandler(filters.TEXT & ~filters.COMMAND, members_h.members_txn_received)],
            MEMBERS_CONFIRM: [
                CallbackQueryHandler(members_h.members_place_order, pattern=r"^place_ORD-"),
                CallbackQueryHandler(stars_h.cancel_order_callback, pattern=r"^cancel_ord_"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(stars_h.generic_cancel, pattern="^cancel$"),
            CallbackQueryHandler(start_h.main_menu_callback, pattern="^main_menu$"),
            CommandHandler("cancel", stars_h.generic_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(members_conv)

    # ── Broadcast (owner) ────────────────────────────────────────
    bc_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", bc_h.broadcast_start)],
        states={
            BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_h.broadcast_receive_text)],
            BROADCAST_TYPE: [
                CallbackQueryHandler(bc_h.broadcast_target_callback, pattern=r"^bc_target_"),
                CallbackQueryHandler(bc_h.broadcast_target_callback, pattern="^bc_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bc_h.broadcast_specific_ids),
            ],
        },
        fallbacks=[CommandHandler("cancel", stars_h.generic_cancel)],
    )
    app.add_handler(bc_conv)

    # ── Owner review callbacks ────────────────────────────────────
    app.add_handler(CallbackQueryHandler(orders_h.owner_review_handler, pattern=r"^ow_(confirm|wrongtxn|cancel)_"))

    # ── Misc callbacks ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(start_h.main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(start_h.my_orders_callback, pattern=r"^(my_orders|orders_page_\d+)$"))
    app.add_handler(CallbackQueryHandler(start_h.my_referral_callback, pattern="^my_referral$"))
    app.add_handler(CallbackQueryHandler(start_h.support_callback, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(start_h.my_stats_callback, pattern="^my_stats$"))

    _app = app
    return app


async def setup_webhook(app: Application) -> None:
    """Set the webhook URL with Telegram."""
    if WEBHOOK_URL:
        full_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
        await app.bot.set_webhook(url=full_url, drop_pending_updates=True)
        logger.info(f"Webhook set to: {full_url}")
    else:
        logger.warning("WEBHOOK_URL not set — webhook not registered.")


def get_app() -> Optional[Application]:
    """Return the running bot Application, or None if not started."""
    return _app
