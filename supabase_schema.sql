-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  TG BUSINESS BOT — SUPABASE DATABASE SCHEMA                     ║
-- ║  Paste this entire file into the Supabase SQL Editor and run it. ║
-- ╚══════════════════════════════════════════════════════════════════╝

-- ─── Enable UUID extension ────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ══════════════════════════════════════════════════════════════════
-- USERS
-- ══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT      UNIQUE NOT NULL,
    username        TEXT        DEFAULT '',
    first_name      TEXT        DEFAULT '',
    last_name       TEXT        DEFAULT '',
    is_banned       BOOLEAN     DEFAULT FALSE,
    channel_joined  BOOLEAN     DEFAULT FALSE,
    referred_by     TEXT        DEFAULT NULL,   -- referral code or user_id string
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    last_seen       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_username    ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);

-- ══════════════════════════════════════════════════════════════════
-- ORDERS
-- ══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS orders (
    id          BIGSERIAL PRIMARY KEY,
    order_id    TEXT        UNIQUE NOT NULL,
    user_id     BIGINT      NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    service     TEXT        NOT NULL,  -- stars | premium | views | reactions | members
    details     JSONB       DEFAULT '{}',
    txn_id      TEXT        NOT NULL DEFAULT '',
    amount_bdt  NUMERIC(12,2) DEFAULT 0,
    status      TEXT        NOT NULL DEFAULT 'pending',  -- pending|confirmed|cancelled|wrong_txn
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id  ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_service  ON orders(service);
CREATE INDEX IF NOT EXISTS idx_orders_created  ON orders(created_at DESC);

-- ══════════════════════════════════════════════════════════════════
-- SETTINGS (key–value store for all editable bot settings)
-- ══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT DEFAULT ''
);

-- Insert default values
INSERT INTO settings (key, value) VALUES
    ('welcome_message',        '🛒 <b>Welcome to our service shop!</b>\n\nChoose a service to get started:'),
    ('update_channel_link',    'https://t.me/yourchannel'),
    ('update_channel_username','yourchannel'),
    ('update_channel_name',    'Our Updates Channel'),
    ('support_link',           'https://t.me/yoursupport'),
    ('support_text',           '📞 <b>Need help?</b>\n\nContact our support team below.'),
    ('nagad_bkash_info',       '📲 <b>Nagad:</b> 01XXXXXXXXX (Personal)\n📲 <b>bKash:</b> 01XXXXXXXXX (Personal)'),
    ('payment_note_stars',     '💫 Send the exact amount via Nagad or bKash, then submit your Transaction ID below.'),
    ('payment_note_premium',   '💎 Send payment via Nagad or bKash and enter your Transaction ID.'),
    ('payment_note_views',     '👁 Calculate your total, send via Nagad/bKash, then submit Transaction ID.'),
    ('payment_note_reactions', '❤️ Send payment and enter Transaction ID.'),
    ('payment_note_members',   '👥 Send payment and enter Transaction ID. (No Guarantee on retention)'),
    -- Stars prices (BDT)
    ('price_stars_50',     '75'),
    ('price_stars_100',    '145'),
    ('price_stars_200',    '285'),
    ('price_stars_250',    '350'),
    ('price_stars_300',    '420'),
    ('price_stars_400',    '560'),
    ('price_stars_500',    '695'),
    ('price_stars_1000',   '1380'),
    ('price_stars_2500',   '3400'),
    ('price_stars_5000',   '6700'),
    ('price_stars_10000',  '13200'),
    -- Premium prices (BDT)
    ('price_premium_3',    '950'),
    ('price_premium_6',    '1800'),
    ('price_premium_12',   '3400'),
    -- Service prices per 1000 (BDT)
    ('price_views_per_1000',     '30'),
    ('price_reactions_per_1000', '50'),
    ('price_members_per_1000',   '200')
ON CONFLICT (key) DO NOTHING;

-- ══════════════════════════════════════════════════════════════════
-- REFERRAL LINKS
-- ══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS referral_links (
    id            BIGSERIAL PRIMARY KEY,
    code          TEXT        UNIQUE NOT NULL,
    label         TEXT        DEFAULT '',
    created_info  TEXT        DEFAULT '',         -- admin notes / user info
    clicks        INTEGER     DEFAULT 0,
    conversions   INTEGER     DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ref_links_code ON referral_links(code);

-- ══════════════════════════════════════════════════════════════════
-- REFERRAL EVENTS (granular tracking)
-- ══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS referral_events (
    id          BIGSERIAL PRIMARY KEY,
    link_code   TEXT        NOT NULL,
    user_id     BIGINT      NOT NULL,
    event_type  TEXT        NOT NULL,  -- click | conversion
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ref_events_code    ON referral_events(link_code);
CREATE INDEX IF NOT EXISTS idx_ref_events_user_id ON referral_events(user_id);

-- ══════════════════════════════════════════════════════════════════
-- BROADCASTS
-- ══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS broadcasts (
    id            BIGSERIAL PRIMARY KEY,
    message_type  TEXT        NOT NULL DEFAULT 'text',   -- text | photo
    content       JSONB       DEFAULT '{}',
    target        TEXT        NOT NULL DEFAULT 'all',    -- all | specific
    status        TEXT        NOT NULL DEFAULT 'sending', -- sending | completed
    success_count INTEGER     DEFAULT 0,
    fail_count    INTEGER     DEFAULT 0,
    sent_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_broadcasts_sent_at ON broadcasts(sent_at DESC);

-- ══════════════════════════════════════════════════════════════════
-- USEFUL VIEWS (optional, for analytics)
-- ══════════════════════════════════════════════════════════════════

-- Revenue summary per service
CREATE OR REPLACE VIEW revenue_by_service AS
SELECT
    service,
    COUNT(*) AS total_orders,
    SUM(amount_bdt) FILTER (WHERE status = 'confirmed') AS confirmed_revenue,
    COUNT(*) FILTER (WHERE status = 'confirmed') AS confirmed_count,
    COUNT(*) FILTER (WHERE status = 'pending')   AS pending_count
FROM orders
GROUP BY service;

-- Daily order stats
CREATE OR REPLACE VIEW daily_order_stats AS
SELECT
    DATE(created_at) AS order_date,
    COUNT(*) AS total_orders,
    SUM(amount_bdt) FILTER (WHERE status = 'confirmed') AS revenue
FROM orders
GROUP BY DATE(created_at)
ORDER BY order_date DESC;

-- User referral stats
CREATE OR REPLACE VIEW referral_stats AS
SELECT
    rl.code,
    rl.label,
    rl.clicks,
    rl.conversions,
    CASE WHEN rl.clicks > 0 THEN ROUND(rl.conversions::numeric / rl.clicks * 100, 1) ELSE 0 END AS conversion_rate
FROM referral_links rl
ORDER BY rl.conversions DESC;

-- ══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (disable for service role key usage)
-- ══════════════════════════════════════════════════════════════════
-- If you're using the service_role key in your app, RLS is bypassed.
-- These policies are for anon key usage only.

-- ALTER TABLE users    DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders   DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE settings DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE referral_links  DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE referral_events DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE broadcasts      DISABLE ROW LEVEL SECURITY;

-- ══════════════════════════════════════════════════════════════════
-- DONE — Schema created successfully!
-- ══════════════════════════════════════════════════════════════════
