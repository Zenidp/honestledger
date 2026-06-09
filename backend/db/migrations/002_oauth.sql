-- Migration 002: Google OAuth support
-- Tables: oauth_users, pending_reveals

CREATE TABLE IF NOT EXISTS oauth_users (
    id          TEXT PRIMARY KEY,
    google_id   TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    picture     TEXT,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oauth_users_google_id ON oauth_users(google_id);
CREATE INDEX IF NOT EXISTS idx_oauth_users_email     ON oauth_users(email);

CREATE TABLE IF NOT EXISTS pending_reveals (
    token_hash  TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    api_key_raw TEXT NOT NULL,
    user_email  TEXT,
    user_name   TEXT,
    user_picture TEXT,
    is_new_user BOOLEAN DEFAULT TRUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-clean expired reveals (optional, harmless if not run)
CREATE INDEX IF NOT EXISTS idx_pending_reveals_expires ON pending_reveals(expires_at);
