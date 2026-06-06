-- Migration 001 — Architecture v2 (2026-06-06)
-- Adds: consecutive_verify_failures column, tenant_schema_mappings table
-- Safe to run multiple times (all statements use IF NOT EXISTS / DO NOTHING guards).

-- ── 1. Add consecutive_verify_failures to tenants ─────────────────────────────
-- Existing rows receive default 0.
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS consecutive_verify_failures INTEGER NOT NULL DEFAULT 0;

-- ── 2. Create tenant_schema_mappings table ────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenant_schema_mappings (
    id                VARCHAR PRIMARY KEY,
    tenant_id         VARCHAR NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    file_type         VARCHAR NOT NULL,          -- 'payments' | 'invoices'
    column_map        JSONB   NOT NULL,           -- {"Date": "date", "Amount": "amount", ...}
    schema_fingerprint VARCHAR NOT NULL,          -- sha256[:16] of sorted column names
    mapping_version   INTEGER NOT NULL DEFAULT 1,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast per-tenant lookups
CREATE INDEX IF NOT EXISTS idx_schema_mappings_tenant_filetype
  ON tenant_schema_mappings (tenant_id, file_type);

-- ── Verification ──────────────────────────────────────────────────────────────
-- Run this to confirm migration applied correctly:
-- SELECT column_name, data_type, column_default
--   FROM information_schema.columns
--  WHERE table_name = 'tenants' AND column_name = 'consecutive_verify_failures';
--
-- SELECT table_name FROM information_schema.tables
--  WHERE table_name = 'tenant_schema_mappings';
