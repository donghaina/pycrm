-- =========================================================
-- PostgreSQL Init SQL for Event-Driven CRM (org + crm schemas)
-- =========================================================

-- Optional but recommended
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------
-- Schemas
-- -------------------------
CREATE SCHEMA IF NOT EXISTS org;
CREATE SCHEMA IF NOT EXISTS crm;

-- -------------------------
-- Shared helper: updated_at trigger
-- -------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- ORG SCHEMA
-- =========================================================

-- -------------------------
-- org.company
-- -------------------------
CREATE TABLE IF NOT EXISTS org.companies (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name         TEXT NOT NULL,
  parent_id    UUID NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_companies_parent
    FOREIGN KEY (parent_id) REFERENCES org.companies(id)
    ON DELETE RESTRICT
);

-- Helpful index for hierarchy queries
CREATE INDEX IF NOT EXISTS idx_companies_parent_id ON org.companies(parent_id);
CREATE INDEX IF NOT EXISTS idx_companies_name ON org.companies(name);

CREATE TRIGGER trg_companies_set_updated_at
BEFORE UPDATE ON org.companies
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- -------------------------
-- org.user role enum (as CHECK for portability)
-- -------------------------
-- Roles: PARENT_ADMIN | CHILD_ADMIN | SALES | READONLY
CREATE TABLE IF NOT EXISTS org.users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NULL, -- optional; can be NULL if using x-user-id header in take-home
  company_id    UUID NOT NULL,
  role          TEXT NOT NULL,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_users_company
    FOREIGN KEY (company_id) REFERENCES org.companies(id)
    ON DELETE RESTRICT,

  CONSTRAINT chk_users_role
    CHECK (role IN ('PARENT_ADMIN', 'CHILD_ADMIN', 'SALES', 'READONLY'))
);

CREATE INDEX IF NOT EXISTS idx_users_company_id ON org.users(company_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON org.users(role);

CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON org.users
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =========================================================
-- CRM SCHEMA
-- =========================================================

-- -------------------------
-- Deal stage / review_status checks
-- -------------------------
-- stage: DRAFT | SUBMITTED | APPROVED | REJECTED
-- review_status: NOT_REQUIRED | PENDING | APPROVED | REJECTED | FAILED
CREATE TABLE IF NOT EXISTS crm.deals (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  child_company_id    UUID NOT NULL, -- logical FK to org.companies.id
  title               TEXT NOT NULL,
  amount              NUMERIC(12, 2) NOT NULL,
  currency            TEXT NOT NULL DEFAULT 'CAD',
  stage               TEXT NOT NULL DEFAULT 'DRAFT',
  review_status       TEXT NOT NULL DEFAULT 'NOT_REQUIRED',
  review_score        INT NULL,
  review_reason       TEXT NULL,
  reviewed_at         TIMESTAMPTZ NULL,
  created_by_user_id  UUID NOT NULL, -- logical FK to org.users.id
  version             INT NOT NULL DEFAULT 1,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_deals_amount_nonnegative
    CHECK (amount >= 0),

  CONSTRAINT chk_deals_stage
    CHECK (stage IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')),

  CONSTRAINT chk_deals_review_status
    CHECK (review_status IN ('NOT_REQUIRED', 'PENDING', 'APPROVED', 'REJECTED', 'FAILED')),

  CONSTRAINT chk_deals_currency_len
    CHECK (char_length(currency) BETWEEN 3 AND 10)
);

CREATE INDEX IF NOT EXISTS idx_deals_child_company_id ON crm.deals(child_company_id);
CREATE INDEX IF NOT EXISTS idx_deals_review_status ON crm.deals(review_status);
CREATE INDEX IF NOT EXISTS idx_deals_created_by_user_id ON crm.deals(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_deals_updated_at ON crm.deals(updated_at DESC);

CREATE TRIGGER trg_deals_set_updated_at
BEFORE UPDATE ON crm.deals
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Optional: enforce "Deal must belong to a CHILD company" at DB level
-- This requires cross-schema FK + trigger logic because "child" is encoded via parent_id.
-- For take-home, keep it in application logic. If you still want DB-level enforcement,
-- you can add a trigger that checks org.companies.parent_id IS NOT NULL.
CREATE OR REPLACE FUNCTION crm.enforce_deal_child_company()
RETURNS TRIGGER AS $$
DECLARE
  parent UUID;
BEGIN
  SELECT c.parent_id INTO parent
  FROM org.companies c
  WHERE c.id = NEW.child_company_id;

  IF parent IS NULL THEN
    RAISE EXCEPTION 'Deal must belong to a CHILD company (company_id=% is not a child)', NEW.child_company_id;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_deals_child_company ON crm.deals;
CREATE TRIGGER trg_deals_child_company
BEFORE INSERT OR UPDATE OF child_company_id ON crm.deals
FOR EACH ROW EXECUTE FUNCTION crm.enforce_deal_child_company();

-- -------------------------
-- Idempotency / Observability table: processed_events
-- -------------------------
CREATE TABLE IF NOT EXISTS crm.processed_events (
  event_id      UUID PRIMARY KEY,
  topic         TEXT NOT NULL,
  status        TEXT NOT NULL,
  error         TEXT NULL,
  error_type    TEXT NULL,
  error_stage   TEXT NULL,
  attempt_count INT NOT NULL DEFAULT 0,
  processed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_processed_events_status
    CHECK (status IN ('PROCESSED', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS idx_processed_events_topic ON crm.processed_events(topic);
CREATE INDEX IF NOT EXISTS idx_processed_events_processed_at ON crm.processed_events(processed_at DESC);

-- =========================================================
-- Optional: Convenience views (nice for debugging)
-- =========================================================

-- View: company tree basics
CREATE OR REPLACE VIEW org.v_company_hierarchy AS
SELECT
  c.id,
  c.name,
  c.parent_id,
  p.name AS parent_name
FROM org.companies c
LEFT JOIN org.companies p ON p.id = c.parent_id;

-- =========================================================
-- Seed data (minimal demo)
-- =========================================================
-- Parent company
INSERT INTO org.companies (id, name, parent_id)
VALUES ('11111111-1111-1111-1111-111111111111', 'Aerialytic Holdings', NULL)
ON CONFLICT (id) DO NOTHING;

-- Two child companies
INSERT INTO org.companies (id, name, parent_id)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'Aerialytic Canada', '11111111-1111-1111-1111-111111111111'),
  ('33333333-3333-3333-3333-333333333333', 'Aerialytic US',     '11111111-1111-1111-1111-111111111111')
ON CONFLICT (id) DO NOTHING;

-- Users: one parent admin, one child sales, one child readonly
INSERT INTO org.users (id, email, company_id, role)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'parent.admin@example.com', '11111111-1111-1111-1111-111111111111', 'PARENT_ADMIN'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'sales.ca@example.com',     '22222222-2222-2222-2222-222222222222', 'SALES'),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'readonly.us@example.com',  '33333333-3333-3333-3333-333333333333', 'READONLY')
ON CONFLICT (id) DO NOTHING;

-- Sample deal (belongs to CHILD company -> allowed)
INSERT INTO crm.deals (
  id, child_company_id, title, amount, currency, stage, review_status, created_by_user_id
) VALUES (
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  '22222222-2222-2222-2222-222222222222',
  'Enterprise Pilot - Phase 1',
  75000.00,
  'CAD',
  'SUBMITTED',
  'PENDING',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
)
ON CONFLICT (id) DO NOTHING;

-- =========================================================
-- End of init.sql
-- =========================================================
