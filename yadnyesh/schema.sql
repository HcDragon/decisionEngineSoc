-- ============================================================
-- Smart SOC Target Website — Supabase Database Schema
-- ============================================================
-- Run this entire file in Supabase SQL Editor:
-- https://supabase.com/dashboard → SQL Editor → New query → Paste → Run
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────
-- TABLE: users
-- Stores registered users and hashed passwords
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id             UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  username       TEXT        UNIQUE NOT NULL,
  password_hash  TEXT        NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- TABLE: login_attempts
-- Logs every login request hitting /api/login
-- Used by the ML model & Decision Engine to detect brute force
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS login_attempts (
  id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  username     TEXT        NOT NULL,
  ip_address   TEXT        NOT NULL DEFAULT '127.0.0.1',
  success      BOOLEAN     NOT NULL DEFAULT FALSE,
  status_code  INTEGER     NOT NULL DEFAULT 401,
  user_agent   TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast time-range queries (used by the dashboard)
CREATE INDEX IF NOT EXISTS idx_login_attempts_created_at ON login_attempts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip         ON login_attempts(ip_address);

-- ─────────────────────────────────────────────
-- TABLE: incidents
-- Stores every decision made by Arav's Decision Engine
-- Synced here via the /api/incident POST endpoint
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents (
  id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  incident_id      TEXT        UNIQUE NOT NULL,           -- e.g. "INC-a1b2c3d4"
  attack_type      TEXT        NOT NULL,                  -- e.g. "Dictionary Brute Force"
  src_ip           TEXT,
  confidence       FLOAT,
  risk_score       FLOAT,
  severity         TEXT,                                  -- LOW | MEDIUM | HIGH | CRITICAL
  priority         TEXT,                                  -- P1 | P2 | P3 | P4
  automation_level INTEGER,                              -- 0-5
  playbook         TEXT,
  incident_status  TEXT        DEFAULT 'OPEN',            -- OPEN | AUTO_MITIGATED | PENDING_APPROVAL | LOGGED
  analyst_required BOOLEAN     DEFAULT FALSE,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status     ON incidents(incident_status);

-- ─────────────────────────────────────────────
-- TABLE: alerts
-- Human-visible alerts for high-risk incidents
-- Analyst can acknowledge them from the dashboard
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
  id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  incident_id      TEXT        REFERENCES incidents(incident_id) ON DELETE CASCADE,
  message          TEXT        NOT NULL,
  severity         TEXT        NOT NULL DEFAULT 'HIGH',
  acknowledged     BOOLEAN     DEFAULT FALSE,
  acknowledged_by  TEXT,
  acknowledged_at  TIMESTAMPTZ,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at  ON alerts(created_at DESC);

-- ─────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- Enable RLS and allow service_role (backend) full access
-- ─────────────────────────────────────────────
ALTER TABLE users           ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_attempts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents       ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts          ENABLE ROW LEVEL SECURITY;

-- Allow the backend (service role key) to do everything
CREATE POLICY "Service role full access - users"
  ON users FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - login_attempts"
  ON login_attempts FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - incidents"
  ON incidents FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access - alerts"
  ON alerts FOR ALL USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────
-- VIEWS (convenient for dashboard queries)
-- ─────────────────────────────────────────────

-- Recent 100 login attempts with failure rate
CREATE OR REPLACE VIEW recent_activity AS
SELECT
  ip_address,
  COUNT(*)                                         AS total_attempts,
  COUNT(*) FILTER (WHERE success = FALSE)          AS failed_attempts,
  ROUND(
    COUNT(*) FILTER (WHERE success = FALSE)::NUMERIC
    / NULLIF(COUNT(*), 0) * 100, 2
  )                                                AS failure_rate_pct,
  MIN(created_at)                                  AS first_seen,
  MAX(created_at)                                  AS last_seen
FROM login_attempts
GROUP BY ip_address
ORDER BY total_attempts DESC;
