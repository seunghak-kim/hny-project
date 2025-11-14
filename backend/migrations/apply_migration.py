"""
Apply database migration to fix price column overflow issue
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.postgre_db import SessionLocal, engine
from sqlalchemy import text


def apply_migration():
    """Apply the migration to change INTEGER columns to BIGINT"""

    migration_sql = """
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
    """

    verify_sql = """
    SELECT
        column_name,
        data_type
    FROM
        information_schema.columns
    WHERE
        table_name = 'transactions'
        AND (column_name LIKE '%price%' OR column_name LIKE '%deposit%' OR column_name LIKE '%rent%')
    ORDER BY
        ordinal_position;
    """

    try:
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()

            try:
                print("Applying migration: Changing price columns from INTEGER to BIGINT...")
                connection.execute(text(migration_sql))

                print("\nVerifying changes...")
                result = connection.execute(text(verify_sql))

                print("\nColumn types after migration:")
                print("-" * 50)
                for row in result:
                    print(f"  {row.column_name:<25} {row.data_type}")

                # Commit transaction
                trans.commit()
                print("\n✅ Migration applied successfully!")

            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                raise

    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration: Fix Price Column Overflow")
    print("=" * 50)
    print()

    response = input("This will modify the database schema. Continue? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        apply_migration()
    else:
        print("Migration cancelled.")
