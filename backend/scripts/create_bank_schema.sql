-- Bank Products Database Schema
-- PostgreSQL migration script for bank JSON data

-- Drop tables if exists (for clean migration)
DROP TABLE IF EXISTS chunk_keywords CASCADE;
DROP TABLE IF EXISTS keywords CASCADE;
DROP TABLE IF EXISTS content_chunks CASCADE;
DROP TABLE IF EXISTS chunk_categories CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS product_categories CASCADE;
DROP TABLE IF EXISTS banks CASCADE;

-- 1. Banks Master Table
CREATE TABLE banks (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Product Categories Master Table
CREATE TABLE product_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Products Table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL UNIQUE,
    bank_id INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    product_category_id INTEGER NOT NULL REFERENCES product_categories(id),
    product_name VARCHAR(255) NOT NULL,
    summary TEXT,
    source_document_url TEXT,
    last_updated DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Chunk Categories Master Table
CREATE TABLE chunk_categories (
    id SERIAL PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Content Chunks Table
CREATE TABLE content_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(100) NOT NULL UNIQUE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    chunk_category_id INTEGER NOT NULL REFERENCES chunk_categories(id),
    content_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Keywords Master Table
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Chunk-Keywords Relationship Table (Many-to-Many)
CREATE TABLE chunk_keywords (
    chunk_id INTEGER NOT NULL REFERENCES content_chunks(id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (chunk_id, keyword_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_products_bank_id ON products(bank_id);
CREATE INDEX idx_products_category_id ON products(product_category_id);
CREATE INDEX idx_products_product_id ON products(product_id);
CREATE INDEX idx_content_chunks_product_id ON content_chunks(product_id);
CREATE INDEX idx_content_chunks_category_id ON content_chunks(chunk_category_id);
CREATE INDEX idx_chunk_keywords_chunk_id ON chunk_keywords(chunk_id);
CREATE INDEX idx_chunk_keywords_keyword_id ON chunk_keywords(keyword_id);
CREATE INDEX idx_keywords_keyword ON keywords(keyword);

-- Full-text search index for content search (optional but recommended)
-- Note: Using 'simple' configuration. For Korean language support, install pg_korean extension
-- and replace 'simple' with 'korean' after installation
CREATE INDEX idx_content_chunks_text_search ON content_chunks USING gin(to_tsvector('simple', content_text));
CREATE INDEX idx_products_name_search ON products USING gin(to_tsvector('simple', product_name));
CREATE INDEX idx_products_summary_search ON products USING gin(to_tsvector('simple', summary));

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_banks_updated_at BEFORE UPDATE ON banks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE banks IS '은행 마스터 테이블';
COMMENT ON TABLE product_categories IS '상품 카테고리 마스터 테이블 (주택담보대출, 전세자금대출, 서민금융 등)';
COMMENT ON TABLE products IS '금융 상품 정보 테이블';
COMMENT ON TABLE chunk_categories IS '청크 카테고리 마스터 테이블 (자격조건, 대출한도, 대출금리 등)';
COMMENT ON TABLE content_chunks IS '상품 상세 정보 청크 테이블';
COMMENT ON TABLE keywords IS '키워드 마스터 테이블';
COMMENT ON TABLE chunk_keywords IS '청크-키워드 다대다 관계 테이블';
