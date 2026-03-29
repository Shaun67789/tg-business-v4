"""
All InlineKeyboardMarkup builders for the bot.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional


# ─── Main Menu ───────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌟 Telegram Stars", callback_data="svc_stars"),
            InlineKeyboardButton("💎 Telegram Premium", callback_data="svc_premium"),
        ],
        [
            InlineKeyboardButton("👁 Post Views", callback_data="svc_views"),
            InlineKeyboardButton("❤️ Post Reactions", callback_data="svc_reactions"),
        ],
        [
            InlineKeyboardButton("👥 Members [⚠️ No Guarantee]", callback_data="svc_members"),
        ],
        [
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
            InlineKeyboardButton("🔗 My Referral Link", callback_data="my_referral"),
        ],
        [
            InlineKeyboardButton("💬 Support", callback_data="support"),
            InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
        ],
    ])


# ─── Stars ───────────────────────────────────────────────────────

def stars_amount_kb(prices: dict) -> InlineKeyboardMarkup:
    amounts = [50, 100, 200, 250, 300, 400, 500, 1000, 2500, 5000, 10000]
    rows = []
    row = []
    for i, amt in enumerate(amounts):
        price = prices.get(str(amt), "N/A")
        row.append(InlineKeyboardButton(
            f"⭐ {amt:,} — ৳{price}", callback_data=f"stars_{amt}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


# ─── Premium ─────────────────────────────────────────────────────

def premium_duration_kb(prices: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"3️⃣ 3 Months — ৳{prices.get('3','N/A')}", callback_data="premium_3"),
        ],
        [
            InlineKeyboardButton(f"6️⃣ 6 Months — ৳{prices.get('6','N/A')}", callback_data="premium_6"),
        ],
        [
            InlineKeyboardButton(f"🔱 12 Months — ৳{prices.get('12','N/A')}", callback_data="premium_12"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])


# ─── Confirm / Cancel (user side) ────────────────────────────────

def confirm_cancel_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Place Order", callback_data=f"place_{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_ord_{order_id}"),
        ]
    ])


# ─── Owner Review ─────────────────────────────────────────────────

def owner_review_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"ow_confirm_{order_id}"),
            InlineKeyboardButton("❌ Wrong TXN", callback_data=f"ow_wrongtxn_{order_id}"),
        ],
        [
            InlineKeyboardButton("🚫 Cancel Order", callback_data=f"ow_cancel_{order_id}"),
        ],
    ])


# ─── Back / Cancel generic ───────────────────────────────────────

def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="main_menu")]
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])


def cancel_flow_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        ]
    ])


# ─── Join Channel ────────────────────────────────────────────────

def join_channel_kb(channel_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Update Channel", url=channel_link)],
        [InlineKeyboardButton("✅ I've Joined — Check Now", callback_data="check_joined")],
    ])


# ─── My Orders (user) ────────────────────────────────────────────

def my_orders_nav_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"orders_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"orders_page_{page+1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


# ─── Support ─────────────────────────────────────────────────────

def support_kb(support_link: str) -> InlineKeyboardMarkup:
    rows = []
    if support_link:
        rows.append([InlineKeyboardButton("💬 Open Support Chat", url=support_link)])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)
