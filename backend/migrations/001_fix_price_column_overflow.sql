-- Migration: Fix price column integer overflow
-- Issue: Price values exceeding 2,147,483,647 (PostgreSQL INTEGER limit)
-- Solution: Change price columns from INTEGER to BIGINT
-- Date: 2025-10-29

-- Alter price columns in transactions table to BIGINT
ALTER TABLE transactions
    ALTER COLUMN sale_price TYPE BIGINT,
    ALTER COLUMN deposit TYPE BIGINT,
    ALTER COLUMN monthly_rent TYPE BIGINT,
    ALTER COLUMN min_sale_price TYPE BIGINT,
    ALTER COLUMN max_sale_price TYPE BIGINT,
    ALTER COLUMN min_deposit TYPE BIGINT,
    ALTER COLUMN max_deposit TYPE BIGINT,
    ALTER COLUMN min_monthly_rent TYPE BIGINT,
    ALTER COLUMN max_monthly_rent TYPE BIGINT;

-- Verify the changes
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM
    information_schema.columns
WHERE
    table_name = 'transactions'
    AND column_name LIKE '%price%' OR column_name LIKE '%deposit%' OR column_name LIKE '%rent%'
ORDER BY
    ordinal_position;
