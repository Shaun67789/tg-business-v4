"""
Conversation states for all bot flows.
Using integer constants grouped by flow.
"""

# ─── Stars Flow ──────────────────────────────────────────────────
STARS_AMOUNT     = 10
STARS_TXN        = 11
STARS_CONFIRM    = 12

# ─── Premium Flow ────────────────────────────────────────────────
PREMIUM_DURATION = 20
PREMIUM_USERNAME = 21
PREMIUM_TXN      = 22
PREMIUM_CONFIRM  = 23

# ─── Views Flow ──────────────────────────────────────────────────
VIEWS_LINK       = 30
VIEWS_AMOUNT     = 31
VIEWS_TXN        = 32
VIEWS_CONFIRM    = 33

# ─── Reactions Flow ──────────────────────────────────────────────
REACTIONS_LINK   = 40
REACTIONS_AMOUNT = 41
REACTIONS_TXN    = 42
REACTIONS_CONFIRM = 43

# ─── Members Flow ────────────────────────────────────────────────
MEMBERS_LINK     = 50
MEMBERS_AMOUNT   = 51
MEMBERS_TXN      = 52
MEMBERS_CONFIRM  = 53

# ─── Referral / Start ────────────────────────────────────────────
START_JOIN_CHECK = 60

# ─── Broadcast (admin) ───────────────────────────────────────────
BROADCAST_TEXT   = 70
BROADCAST_TYPE   = 71
