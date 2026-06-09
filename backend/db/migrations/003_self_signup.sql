-- Migration 003: Self-service signup (replaces Google OAuth)
-- Table: user_registrations

CREATE TABLE IF NOT EXISTS user_registrations (
    id         TEXT PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    name       TEXT,
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_registrations_email ON user_registrations(email);
