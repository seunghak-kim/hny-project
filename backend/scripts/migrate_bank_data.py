"""
Bank Data Migration Script
Migrates JSON data from backend/data/bank/ to PostgreSQL database
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import psycopg2
from psycopg2.extras import execute_values

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Database connection settings (update with your actual settings)
DB_CONFIG = {
    'dbname': 'real_estate', # 데이터 베이스 
    'user': 'postgres',  # user 이름 
    'password': 'password', #  비밀번호 
    'host': 'localhost', 
    'port': 5432
}

# Path to bank JSON files
BANK_DATA_DIR = Path(__file__).parent.parent / 'data' / 'bank'


class BankDataMigrator:
    """Migrates bank product JSON data to PostgreSQL"""

    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.cursor = None

        # Cache for IDs to avoid repeated DB lookups
        self.bank_cache: Dict[str, int] = {}
        self.product_category_cache: Dict[str, int] = {}
        self.chunk_category_cache: Dict[str, int] = {}
        self.keyword_cache: Dict[str, int] = {}

    def connect(self):
        """Establish database connection"""
        print("Connecting to database...")
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        print("✓ Connected to database")

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Database connection closed")

    def get_or_create_bank(self, bank_name: str) -> int:
        """Get or create bank and return its ID"""
        if bank_name in self.bank_cache:
            return self.bank_cache[bank_name]

        self.cursor.execute(
            "SELECT id FROM banks WHERE bank_name = %s",
            (bank_name,)
        )
        result = self.cursor.fetchone()

        if result:
            bank_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO banks (bank_name) VALUES (%s) RETURNING id",
                (bank_name,)
            )
            bank_id = self.cursor.fetchone()[0]
            print(f"  + Created bank: {bank_name}")

        self.bank_cache[bank_name] = bank_id
        return bank_id

    def get_or_create_product_category(self, category_name: str) -> int:
        """Get or create product category and return its ID"""
        if category_name in self.product_category_cache:
            return self.product_category_cache[category_name]

        self.cursor.execute(
            "SELECT id FROM product_categories WHERE category_name = %s",
            (category_name,)
        )
        result = self.cursor.fetchone()

        if result:
            category_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO product_categories (category_name) VALUES (%s) RETURNING id",
                (category_name,)
            )
            category_id = self.cursor.fetchone()[0]
            print(f"  + Created product category: {category_name}")

        self.product_category_cache[category_name] = category_id
        return category_id

    def get_or_create_chunk_category(self, category_name: str) -> int:
        """Get or create chunk category and return its ID"""
        if category_name in self.chunk_category_cache:
            return self.chunk_category_cache[category_name]

        self.cursor.execute(
            "SELECT id FROM chunk_categories WHERE category_name = %s",
            (category_name,)
        )
        result = self.cursor.fetchone()

        if result:
            category_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO chunk_categories (category_name) VALUES (%s) RETURNING id",
                (category_name,)
            )
            category_id = self.cursor.fetchone()[0]
            print(f"  + Created chunk category: {category_name}")

        self.chunk_category_cache[category_name] = category_id
        return category_id

    def get_or_create_keyword(self, keyword: str) -> int:
        """Get or create keyword and return its ID"""
        if keyword in self.keyword_cache:
            return self.keyword_cache[keyword]

        self.cursor.execute(
            "SELECT id FROM keywords WHERE keyword = %s",
            (keyword,)
        )
        result = self.cursor.fetchone()

        if result:
            keyword_id = result[0]
        else:
            self.cursor.execute(
                "INSERT INTO keywords (keyword) VALUES (%s) RETURNING id",
                (keyword,)
            )
            keyword_id = self.cursor.fetchone()[0]

        self.keyword_cache[keyword] = keyword_id
        return keyword_id

    def insert_product(self, product_data: Dict) -> int:
        """Insert product and return its ID"""
        metadata = product_data['metadata']

        bank_id = self.get_or_create_bank(metadata['bank_name'])

        # Handle product_category - it can be a string or a list
        product_category = metadata['product_category']
        if isinstance(product_category, list):
            product_category = product_category[0] if product_category else '기타'

        category_id = self.get_or_create_product_category(product_category)

        # Parse date
        last_updated = None
        if metadata.get('last_updated'):
            try:
                last_updated = datetime.strptime(metadata['last_updated'], '%Y-%m-%d').date()
            except ValueError:
                pass

        self.cursor.execute("""
            INSERT INTO products (
                product_id, bank_id, product_category_id,
                product_name, summary, source_document_url, last_updated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                summary = EXCLUDED.summary,
                source_document_url = EXCLUDED.source_document_url,
                last_updated = EXCLUDED.last_updated,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            metadata['product_id'],
            bank_id,
            category_id,
            metadata['product_name'],
            metadata.get('summary'),
            metadata.get('source_document_url'),
            last_updated
        ))

        product_id = self.cursor.fetchone()[0]
        print(f"  ✓ Product: {metadata['product_name']}")
        return product_id

    def insert_content_chunks(self, product_id: int, chunks: List[Dict]):
        """Insert content chunks and their keywords"""
        for chunk in chunks:
            chunk_category_id = self.get_or_create_chunk_category(chunk['category'])

            # Insert chunk
            self.cursor.execute("""
                INSERT INTO content_chunks (
                    chunk_id, product_id, chunk_category_id, content_text
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content_text = EXCLUDED.content_text
                RETURNING id
            """, (
                chunk['chunk_id'],
                product_id,
                chunk_category_id,
                chunk['content_text']
            ))

            chunk_db_id = self.cursor.fetchone()[0]

            # Insert keywords
            if chunk.get('keywords'):
                # First, delete existing keywords for this chunk (in case of update)
                self.cursor.execute(
                    "DELETE FROM chunk_keywords WHERE chunk_id = %s",
                    (chunk_db_id,)
                )

                # Insert new keywords
                keyword_relations = []
                for keyword in chunk['keywords']:
                    keyword_id = self.get_or_create_keyword(keyword)
                    keyword_relations.append((chunk_db_id, keyword_id))

                if keyword_relations:
                    execute_values(
                        self.cursor,
                        "INSERT INTO chunk_keywords (chunk_id, keyword_id) VALUES %s ON CONFLICT DO NOTHING",
                        keyword_relations
                    )

    def migrate_file(self, file_path: Path):
        """Migrate a single JSON file"""
        print(f"\nProcessing: {file_path.name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            products = json.load(f)

        print(f"  Found {len(products)} products")

        for product in products:
            try:
                product_id = self.insert_product(product)

                if product.get('content_chunks'):
                    self.insert_content_chunks(product_id, product['content_chunks'])
                    print(f"    + {len(product['content_chunks'])} chunks")

            except Exception as e:
                print(f"  ✗ Error processing product {product.get('metadata', {}).get('product_id', 'unknown')}: {e}")
                raise

        self.conn.commit()
        print(f"✓ Committed {file_path.name}")

    def migrate_all(self):
        """Migrate all JSON files in the bank data directory"""
        json_files = sorted(BANK_DATA_DIR.glob('*.json'))

        if not json_files:
            print(f"No JSON files found in {BANK_DATA_DIR}")
            return

        print(f"\nFound {len(json_files)} JSON files to migrate:")
        for f in json_files:
            print(f"  - {f.name}")

        try:
            for json_file in json_files:
                self.migrate_file(json_file)

            print("\n" + "="*50)
            print("✓ Migration completed successfully!")
            print("="*50)

            # Print statistics
            self.print_statistics()

        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            self.conn.rollback()
            raise

    def print_statistics(self):
        """Print migration statistics"""
        print("\nDatabase Statistics:")

        tables = [
            ('banks', '은행'),
            ('product_categories', '상품 카테고리'),
            ('products', '금융 상품'),
            ('chunk_categories', '청크 카테고리'),
            ('content_chunks', '상세 정보 청크'),
            ('keywords', '키워드'),
            ('chunk_keywords', '청크-키워드 관계')
        ]

        for table, desc in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            print(f"  - {desc} ({table}): {count:,}")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate bank JSON data to PostgreSQL')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print("="*50)
    print("Bank Data Migration to PostgreSQL")
    print("="*50)

    # Update DB_CONFIG before running
    print("\n⚠️  Database configuration:")
    print(f"  Database: {DB_CONFIG['dbname']}")
    print(f"  User: {DB_CONFIG['user']}")
    print(f"  Host: {DB_CONFIG['host']}")
    print(f"  Port: {DB_CONFIG['port']}")

    if not args.yes:
        response = input("\nDo you want to proceed with migration? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return

    migrator = BankDataMigrator(DB_CONFIG)

    try:
        migrator.connect()
        migrator.migrate_all()
    except Exception as e:
        print(f"\nMigration error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        migrator.disconnect()


if __name__ == '__main__':
    main()
