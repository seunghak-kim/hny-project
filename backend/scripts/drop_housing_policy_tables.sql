-- ============================================
-- Housing Policy Tables Drop Script
-- ============================================
-- PostgreSQL Script
-- Created: 2025-11-25
-- Description: Drops all housing policy tables and ENUM types
-- WARNING: This will DELETE ALL DATA in these tables!
-- ============================================

-- ============================================
-- 1. Drop Tables (in reverse dependency order)
-- ============================================

-- Drop child tables first
DROP TABLE IF EXISTS policy_links CASCADE;
DROP TABLE IF EXISTS policy_contacts CASCADE;
DROP TABLE IF EXISTS policy_financial_supports CASCADE;
DROP TABLE IF EXISTS policy_eligibility_ranks CASCADE;
DROP TABLE IF EXISTS policy_target_types CASCADE;

-- Drop parent tables
DROP TABLE IF EXISTS housing_policies CASCADE;
DROP TABLE IF EXISTS policy_categories CASCADE;


-- ============================================
-- 2. Drop ENUM Types
-- ============================================

DROP TYPE IF EXISTS link_type CASCADE;
DROP TYPE IF EXISTS financial_support_type CASCADE;
DROP TYPE IF EXISTS income_criteria_type CASCADE;
DROP TYPE IF EXISTS target_type CASCADE;
DROP TYPE IF EXISTS policy_status CASCADE;


-- ============================================
-- 3. Verification
-- ============================================
-- Run this to verify all tables were dropped
/*
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'policy_categories',
    'housing_policies',
    'policy_target_types',
    'policy_eligibility_ranks',
    'policy_financial_supports',
    'policy_contacts',
    'policy_links'
  );
*/

-- Verify ENUM types were dropped
/*
SELECT typname
FROM pg_type
WHERE typname IN (
    'policy_status',
    'target_type',
    'income_criteria_type',
    'financial_support_type',
    'link_type'
);
*/
