-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    acc_no TEXT PRIMARY KEY,
    tg_id INTEGER UNIQUE,
    name TEXT,
    mobile TEXT UNIQUE,
    password_hash TEXT,
    balance REAL DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    ban_reason TEXT,
    banned_at DATETIME,
    banned_by INTEGER,
    referred_by TEXT,
    membership_active INTEGER DEFAULT 0,
    membership_expiry DATETIME,
    daily_withdrawal_limit REAL DEFAULT 5000,
    weekly_withdrawal_limit REAL DEFAULT 20000,
    monthly_withdrawal_limit REAL DEFAULT 50000,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. OTP
CREATE TABLE IF NOT EXISTS otp (
    mobile TEXT PRIMARY KEY,
    otp_code TEXT,
    expires_at DATETIME,
    attempts INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. WORKING URLS
CREATE TABLE IF NOT EXISTS working_urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. DEPOSIT AMOUNTS
CREATE TABLE IF NOT EXISTS deposit_amounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER,
    amount REAL,
    deposit_structure TEXT,
    max_limit INTEGER,
    used_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. URL ROTATION
CREATE TABLE IF NOT EXISTS url_rotation (
    user_acc TEXT PRIMARY KEY,
    last_url_id INTEGER
);

-- 6. ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_acc TEXT,
    url_id INTEGER,
    deposit_amount_id INTEGER,
    deposit_amount REAL,
    deposit_structure TEXT,
    working_url TEXT,
    uid TEXT,
    withdrawal_amount REAL,
    proof_file_ids TEXT,
    proof_message_id INTEGER,
    proof_caption TEXT,
    proof_type TEXT,
    status TEXT DEFAULT 'created',
    fail_reason TEXT,
    reward_amount REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    completed_at DATETIME
);

-- 7. WITHDRAWALS
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_acc TEXT,
    amount REAL,
    processing_fee REAL,
    actual_cost REAL,
    profit REAL,
    total_deducted REAL,
    method TEXT,
    wallet_address TEXT,
    upi_id TEXT,
    account_holder TEXT,
    bank_name TEXT,
    account_no TEXT,
    ifsc TEXT,
    status TEXT DEFAULT 'pending',
    admin_note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME
);

-- 8. MEMBERSHIP PLANS
CREATE TABLE IF NOT EXISTS membership_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    duration_days INTEGER,
    description TEXT,
    qr_file_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. MEMBERSHIPS
CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_acc TEXT,
    plan_id INTEGER,
    plan_name TEXT,
    amount REAL,
    duration_days INTEGER,
    utr TEXT,
    payment_proof_file_id TEXT,
    status TEXT DEFAULT 'pending',
    admin_note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME
);

-- 10. REFERRALS
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_acc TEXT,
    referred_acc TEXT,
    commission_earned REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 11. TRANSACTIONS
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_acc TEXT,
    type TEXT,
    amount REAL,
    ref_id INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 12. SETTINGS
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR IGNORE INTO settings (key, value) VALUES
('order_timeout_minutes', '40'),
('crypto_fee', '40'),
('crypto_actual_cost', '30'),
('upi_fee', '10'),
('upi_actual_cost', '5'),
('bank_fee', '15'),
('bank_actual_cost', '10'),
('commission_type', 'percent'),
('commission_value', '10'),
('membership_required', '1'),
('browser_message', 'browser mein kholo (Chrome, UC, etc.)'),
('min_withdrawal', '100');

-- 13. ADMINS
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    phone TEXT UNIQUE,
    password_hash TEXT,
    role TEXT DEFAULT 'admin',
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 14. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    message TEXT,
    is_sent INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- DEFAULT SUPERADMIN
INSERT OR IGNORE INTO admins (username, phone, password_hash, role)
VALUES (
    'admin',
    '0000000000',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr7Z8j9K',
    'superadmin'
);
