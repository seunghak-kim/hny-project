"""
Legal Data Migration Script
Migrates legal data from SQLite database to PostgreSQL database
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import psycopg2
from psycopg2.extras import execute_values, Json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Database connection settings (update with your actual settings)
POSTGRES_CONFIG = {
    'dbname': 'real_estate',  # 데이터베이스 이름
    'user': 'postgres',        # user 이름
    'password': 'password',    # 비밀번호
    'host': 'localhost',
    'port': 5432
}

# Path to SQLite database
SQLITE_DB_PATH = Path(__file__).parent.parent / 'data' / 'storage' / 'legal_info' / 'sqlite_db' / 'legal_metadata.db'


class LegalDataMigrator:
    """Migrates legal data from SQLite to PostgreSQL"""

    def __init__(self, postgres_config: Dict, sqlite_path: Path):
        self.postgres_config = postgres_config
        self.sqlite_path = sqlite_path
        self.pg_conn = None
        self.pg_cursor = None
        self.sqlite_conn = None
        self.sqlite_cursor = None

        # Mapping from SQLite law_id to PostgreSQL law_id
        self.law_id_mapping: Dict[int, int] = {}

    def connect_postgres(self):
        """Establish PostgreSQL database connection"""
        print("Connecting to PostgreSQL...")
        self.pg_conn = psycopg2.connect(**self.postgres_config)
        self.pg_cursor = self.pg_conn.cursor()
        print("✓ Connected to PostgreSQL")

    def connect_sqlite(self):
        """Establish SQLite database connection"""
        print(f"Connecting to SQLite database: {self.sqlite_path}")
        if not self.sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")

        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.row_factory = sqlite3.Row  # Enable column access by name
        self.sqlite_cursor = self.sqlite_conn.cursor()
        print("✓ Connected to SQLite")

    def disconnect(self):
        """Close all database connections"""
        if self.sqlite_cursor:
            self.sqlite_cursor.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.pg_cursor:
            self.pg_cursor.close()
        if self.pg_conn:
            self.pg_conn.close()
        print("✓ Database connections closed")

    def migrate_laws(self):
        """Migrate laws table from SQLite to PostgreSQL"""
        print("\n" + "="*50)
        print("Migrating Laws...")
        print("="*50)

        # Fetch all laws from SQLite
        self.sqlite_cursor.execute("""
            SELECT
                law_id, doc_type, title, number, enforcement_date,
                category, total_articles, last_article, source_file, created_at
            FROM laws
            ORDER BY law_id
        """)

        laws = self.sqlite_cursor.fetchall()
        print(f"Found {len(laws)} laws to migrate")

        migrated_count = 0
        for law in laws:
            try:
                # Insert into PostgreSQL
                self.pg_cursor.execute("""
                    INSERT INTO laws (
                        doc_type, title, number, enforcement_date,
                        category, total_articles, last_article, source_file, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING law_id
                """, (
                    law['doc_type'],
                    law['title'],
                    law['number'] if law['number'] else '',
                    law['enforcement_date'] if law['enforcement_date'] else '',
                    law['category'],
                    law['total_articles'] if law['total_articles'] else 0,
                    law['last_article'] if law['last_article'] else '',
                    law['source_file'] if law['source_file'] else '',
                    law['created_at'] if law['created_at'] else datetime.now()
                ))

                new_law_id = self.pg_cursor.fetchone()[0]
                self.law_id_mapping[law['law_id']] = new_law_id

                print(f"  ✓ Migrated: {law['title']} (SQLite ID: {law['law_id']} → PostgreSQL ID: {new_law_id})")
                migrated_count += 1

            except Exception as e:
                print(f"  ✗ Error migrating law {law['title']}: {e}")
                raise

        self.pg_conn.commit()
        print(f"\n✓ Successfully migrated {migrated_count} laws")

    def migrate_articles(self):
        """Migrate articles table from SQLite to PostgreSQL"""
        print("\n" + "="*50)
        print("Migrating Articles...")
        print("="*50)

        # Fetch all articles from SQLite
        self.sqlite_cursor.execute("""
            SELECT
                article_id, law_id, article_number, article_title,
                chapter, section, is_deleted, is_tenant_protection,
                is_tax_related, is_delegation, is_penalty_related,
                chunk_ids, metadata_json
            FROM articles
            ORDER BY article_id
        """)

        articles = self.sqlite_cursor.fetchall()
        print(f"Found {len(articles)} articles to migrate")

        migrated_count = 0
        batch_size = 100
        batch = []

        for article in articles:
            try:
                # Get the new law_id from mapping
                old_law_id = article['law_id']
                if old_law_id not in self.law_id_mapping:
                    print(f"  ⚠️  Warning: law_id {old_law_id} not found in mapping, skipping article {article['article_id']}")
                    continue

                new_law_id = self.law_id_mapping[old_law_id]

                # Parse metadata_json if it exists
                import json
                metadata_json = None
                if article['metadata_json']:
                    try:
                        metadata_json = json.loads(article['metadata_json'])
                    except json.JSONDecodeError:
                        metadata_json = None

                # Parse chunk_ids if it exists (it's stored as JSON string in SQLite)
                chunk_ids = None
                if article['chunk_ids']:
                    try:
                        chunk_ids = json.loads(article['chunk_ids'])
                    except (json.JSONDecodeError, TypeError):
                        chunk_ids = None

                batch.append((
                    new_law_id,
                    article['article_number'],
                    article['article_title'] if article['article_title'] else '',
                    article['chapter'],
                    article['section'],
                    bool(article['is_deleted']),
                    bool(article['is_tenant_protection']),
                    bool(article['is_tax_related']),
                    bool(article['is_delegation']),
                    bool(article['is_penalty_related']),
                    Json(chunk_ids) if chunk_ids else None,
                    Json(metadata_json) if metadata_json else None
                ))

                migrated_count += 1

                # Execute batch insert
                if len(batch) >= batch_size:
                    execute_values(
                        self.pg_cursor,
                        """
                        INSERT INTO articles (
                            law_id, article_number, article_title, chapter, section,
                            is_deleted, is_tenant_protection, is_tax_related,
                            is_delegation, is_penalty_related, chunk_ids, metadata_json
                        ) VALUES %s
                        """,
                        batch
                    )
                    self.pg_conn.commit()
                    print(f"  ✓ Migrated {migrated_count} articles...")
                    batch = []

            except Exception as e:
                print(f"  ✗ Error migrating article {article['article_id']}: {e}")
                raise

        # Insert remaining batch
        if batch:
            execute_values(
                self.pg_cursor,
                """
                INSERT INTO articles (
                    law_id, article_number, article_title, chapter, section,
                    is_deleted, is_tenant_protection, is_tax_related,
                    is_delegation, is_penalty_related, chunk_ids, metadata_json
                ) VALUES %s
                """,
                batch
            )
            self.pg_conn.commit()

        print(f"\n✓ Successfully migrated {migrated_count} articles")

    def migrate_legal_references(self):
        """Migrate legal_references table from SQLite to PostgreSQL"""
        print("\n" + "="*50)
        print("Migrating Legal References...")
        print("="*50)

        # Check if legal_references table exists and has data
        self.sqlite_cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='legal_references'
        """)

        if not self.sqlite_cursor.fetchone():
            print("  ⚠️  legal_references table not found in SQLite, skipping...")
            return

        # Fetch all legal references from SQLite
        self.sqlite_cursor.execute("""
            SELECT
                reference_id, source_article_id, reference_type,
                target_law_title, target_article_number, reference_text
            FROM legal_references
            ORDER BY reference_id
        """)

        references = self.sqlite_cursor.fetchall()
        print(f"Found {len(references)} legal references to migrate")

        if len(references) == 0:
            print("  No legal references to migrate")
            return

        # Note: The PostgreSQL LegalReference model structure is different from SQLite
        # SQLite: has source_article_id, reference_type, target_law_title, target_article_number
        # PostgreSQL: uses article_id as PK and duplicates article fields
        # This migration will skip legal_references as the schema is incompatible
        print("  ⚠️  Warning: PostgreSQL LegalReference schema is incompatible with SQLite schema")
        print("  ⚠️  Skipping legal_references migration - manual schema review needed")

    def migrate_all(self):
        """Migrate all data from SQLite to PostgreSQL"""
        print("\n" + "="*60)
        print("Starting Legal Data Migration: SQLite → PostgreSQL")
        print("="*60)

        try:
            self.migrate_laws()
            self.migrate_articles()
            self.migrate_legal_references()

            print("\n" + "="*60)
            print("✓ Migration completed successfully!")
            print("="*60)

            # Print statistics
            self.print_statistics()

        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            self.pg_conn.rollback()
            raise

    def print_statistics(self):
        """Print migration statistics"""
        print("\nPostgreSQL Database Statistics:")

        # Laws count
        self.pg_cursor.execute("SELECT COUNT(*) FROM laws")
        laws_count = self.pg_cursor.fetchone()[0]
        print(f"  - 법률 (laws): {laws_count:,}")

        # Articles count
        self.pg_cursor.execute("SELECT COUNT(*) FROM articles")
        articles_count = self.pg_cursor.fetchone()[0]
        print(f"  - 조항 (articles): {articles_count:,}")

        # Articles by flags
        self.pg_cursor.execute("""
            SELECT
                SUM(CASE WHEN is_tenant_protection THEN 1 ELSE 0 END) as tenant_protection,
                SUM(CASE WHEN is_tax_related THEN 1 ELSE 0 END) as tax_related,
                SUM(CASE WHEN is_delegation THEN 1 ELSE 0 END) as delegation,
                SUM(CASE WHEN is_penalty_related THEN 1 ELSE 0 END) as penalty_related,
                SUM(CASE WHEN is_deleted THEN 1 ELSE 0 END) as deleted
            FROM articles
        """)
        stats = self.pg_cursor.fetchone()
        print(f"\n  특수 조항 통계:")
        print(f"    - 임차인 보호: {stats[0]:,}")
        print(f"    - 세법 관련: {stats[1]:,}")
        print(f"    - 위임: {stats[2]:,}")
        print(f"    - 벌칙: {stats[3]:,}")
        print(f"    - 삭제됨: {stats[4]:,}")

    def verify_migration(self):
        """Verify that migration was successful"""
        print("\n" + "="*60)
        print("Verifying Migration...")
        print("="*60)

        # Compare counts
        self.sqlite_cursor.execute("SELECT COUNT(*) FROM laws")
        sqlite_laws = self.sqlite_cursor.fetchone()[0]

        self.pg_cursor.execute("SELECT COUNT(*) FROM laws")
        pg_laws = self.pg_cursor.fetchone()[0]

        print(f"Laws: SQLite={sqlite_laws}, PostgreSQL={pg_laws}")

        self.sqlite_cursor.execute("SELECT COUNT(*) FROM articles")
        sqlite_articles = self.sqlite_cursor.fetchone()[0]

        self.pg_cursor.execute("SELECT COUNT(*) FROM articles")
        pg_articles = self.pg_cursor.fetchone()[0]

        print(f"Articles: SQLite={sqlite_articles}, PostgreSQL={pg_articles}")

        if sqlite_laws == pg_laws and sqlite_articles == pg_articles:
            print("\n✓ Verification passed: All data migrated successfully!")
        else:
            print("\n⚠️  Warning: Count mismatch detected!")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate legal data from SQLite to PostgreSQL')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--verify', '-v', action='store_true', help='Verify migration after completion')
    parser.add_argument('--sqlite-path', type=str, help='Path to SQLite database (optional)')
    args = parser.parse_args()

    print("="*60)
    print("Legal Data Migration: SQLite → PostgreSQL")
    print("="*60)

    # Use custom SQLite path if provided
    sqlite_path = Path(args.sqlite_path) if args.sqlite_path else SQLITE_DB_PATH

    # Update POSTGRES_CONFIG before running
    print("\n⚠️  PostgreSQL configuration:")
    print(f"  Database: {POSTGRES_CONFIG['dbname']}")
    print(f"  User: {POSTGRES_CONFIG['user']}")
    print(f"  Host: {POSTGRES_CONFIG['host']}")
    print(f"  Port: {POSTGRES_CONFIG['port']}")

    print(f"\n📁 SQLite database path:")
    print(f"  {sqlite_path}")

    if not args.yes:
        response = input("\nDo you want to proceed with migration? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return

    migrator = LegalDataMigrator(POSTGRES_CONFIG, sqlite_path)

    try:
        migrator.connect_postgres()
        migrator.connect_sqlite()
        migrator.migrate_all()

        if args.verify:
            migrator.verify_migration()

    except Exception as e:
        print(f"\nMigration error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        migrator.disconnect()


if __name__ == '__main__':
    main()
