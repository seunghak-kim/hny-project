-- ============================================
-- Housing Policy Tables Creation Script
-- ============================================
-- PostgreSQL Script
-- Created: 2025-11-25
-- Description: Creates all tables for housing policy management system
-- ============================================

-- ============================================
-- 1. Create ENUM Types
-- ============================================

-- 정책 상태 ENUM
CREATE TYPE policy_status AS ENUM (
    'recruiting',    -- 모집중
    'close',        -- 마감
    'always',       -- 상시
    'scheduled'     -- 예정
);

-- 대상 유형 ENUM
CREATE TYPE target_type AS ENUM (
    'youth',                  -- 청년
    'student',               -- 학생
    'job_seeker',            -- 구직자
    'newlywed',              -- 신혼부부
    'prospective_newlywed',  -- 예비 신혼부부
    'low_income',            -- 저소득층
    'elderly',               -- 노인
    'disabled',              -- 장애인
    'single_parent',         -- 한부모
    'welfare_recipient'      -- 복지 수급자
);

-- 소득 기준 유형 ENUM
CREATE TYPE income_criteria_type AS ENUM (
    'median',        -- 중위소득
    'urban_worker'   -- 도시근로자
);

-- 금융 지원 유형 ENUM
CREATE TYPE financial_support_type AS ENUM (
    'monthly_rent',   -- 월세 지원
    'interest',       -- 이자 지원
    'guarantee_fee',  -- 보증료 지원
    'deposit_loan'    -- 보증금 대출
);

-- 링크 유형 ENUM
CREATE TYPE link_type AS ENUM (
    'application',  -- 신청
    'info',        -- 정보
    'notice',      -- 공지
    'faq',         -- 자주묻는질문
    'resources'    -- 자료
);


-- ============================================
-- 2. Create Tables
-- ============================================

-- 2.1 Policy Categories Table (정책 카테고리)
CREATE TABLE policy_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    partent_id INTEGER,
    level INTEGER DEFAULT 1 NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Foreign Key for self-referencing
    CONSTRAINT fk_policy_categories_parent
        FOREIGN KEY (partent_id)
        REFERENCES policy_categories(id)
        ON DELETE SET NULL
);

-- Comments for policy_categories
COMMENT ON TABLE policy_categories IS '정책 카테고리';
COMMENT ON COLUMN policy_categories.name IS '정책 카테고리 이름';
COMMENT ON COLUMN policy_categories.partent_id IS '상위 카테고리 ID';
COMMENT ON COLUMN policy_categories.level IS '카테고리 레벨';
COMMENT ON COLUMN policy_categories.description IS '카테고리 설명';
COMMENT ON COLUMN policy_categories.is_active IS '활성화 여부';

-- Indexes for policy_categories
CREATE INDEX idx_policy_categories_parent_id ON policy_categories(partent_id);
CREATE INDEX idx_policy_categories_level ON policy_categories(level);


-- 2.2 Housing Policies Table (주택 정책)
CREATE TABLE housing_policies (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL,
    policy_name VARCHAR(200) NOT NULL,
    policy_code VARCHAR(50) UNIQUE,
    summary TEXT,
    description TEXT,
    application_method TEXT,
    application_url VARCHAR(500),
    officical_url VARCHAR(500),
    housing_requirements JSON,
    lease_conditions JSON,
    required_documments JSON,
    regional_limitations JSON,
    recruitment_info JSON,
    status policy_status DEFAULT 'always' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Foreign Key
    CONSTRAINT fk_housing_policies_category
        FOREIGN KEY (category_id)
        REFERENCES policy_categories(id)
        ON DELETE CASCADE
);

-- Comments for housing_policies
COMMENT ON TABLE housing_policies IS '주택 정책';
COMMENT ON COLUMN housing_policies.category_id IS '정책 카테고리 ID';
COMMENT ON COLUMN housing_policies.policy_name IS '정책명';
COMMENT ON COLUMN housing_policies.policy_code IS '정책 코드';
COMMENT ON COLUMN housing_policies.summary IS '정책 요약';
COMMENT ON COLUMN housing_policies.description IS '정책 상세 설명';
COMMENT ON COLUMN housing_policies.application_method IS '신청 방법';
COMMENT ON COLUMN housing_policies.application_url IS '신청링크';
COMMENT ON COLUMN housing_policies.officical_url IS '공식 안내페이지';
COMMENT ON COLUMN housing_policies.housing_requirements IS '주택 요건';
COMMENT ON COLUMN housing_policies.lease_conditions IS '임대 조건';
COMMENT ON COLUMN housing_policies.required_documments IS '필요 서류';
COMMENT ON COLUMN housing_policies.regional_limitations IS '지역별 지원한도';
COMMENT ON COLUMN housing_policies.recruitment_info IS '모집 정보';
COMMENT ON COLUMN housing_policies.status IS '정책 상태';
COMMENT ON COLUMN housing_policies.is_active IS '활성화 여부';

-- Indexes for housing_policies
CREATE INDEX idx_housing_policies_category_id ON housing_policies(category_id);
CREATE INDEX idx_housing_policies_policy_code ON housing_policies(policy_code);
CREATE INDEX idx_housing_policies_status ON housing_policies(status);


-- 2.3 Policy Target Types Table (정책 대상 유형)
CREATE TABLE policy_target_types (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    target_type target_type NOT NULL,
    age_min INTEGER,
    age_max INTEGER,
    specific_conditions TEXT,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Key
    CONSTRAINT fk_policy_target_types_policy
        FOREIGN KEY (policy_id)
        REFERENCES housing_policies(id)
        ON DELETE CASCADE
);

-- Comments for policy_target_types
COMMENT ON TABLE policy_target_types IS '정책 대상 유형';
COMMENT ON COLUMN policy_target_types.policy_id IS '정책 ID';
COMMENT ON COLUMN policy_target_types.target_type IS '대상 유형';
COMMENT ON COLUMN policy_target_types.age_min IS '최소 연령';
COMMENT ON COLUMN policy_target_types.age_max IS '최대 연령';
COMMENT ON COLUMN policy_target_types.specific_conditions IS '특정 조건';
COMMENT ON COLUMN policy_target_types.is_primary IS '주 대상 여부';

-- Indexes for policy_target_types
CREATE INDEX idx_policy_target_types_policy_id ON policy_target_types(policy_id);
CREATE INDEX idx_policy_target_types_target_type ON policy_target_types(target_type);


-- 2.4 Policy Eligibility Ranks Table (정책 자격 순위)
CREATE TABLE policy_eligibility_ranks (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    target_type INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    rank_name VARCHAR(50),
    target_description TEXT,
    income_criteria_percent INTEGER,
    income_criteria_tyoe income_criteria_type,
    asset_criteria DECIMAL(15, 2),
    car_asset_criteria DECIMAL(15, 2),
    additional_conditions JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Keys
    CONSTRAINT fk_policy_eligibility_ranks_policy
        FOREIGN KEY (policy_id)
        REFERENCES housing_policies(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_policy_eligibility_ranks_target
        FOREIGN KEY (target_type)
        REFERENCES policy_target_types(id)
        ON DELETE CASCADE,

    -- Unique Constraint
    CONSTRAINT idx_policy_eligibility_ranks_rank
        UNIQUE (policy_id, rank)
);

-- Comments for policy_eligibility_ranks
COMMENT ON TABLE policy_eligibility_ranks IS '정책 자격 순위';
COMMENT ON COLUMN policy_eligibility_ranks.policy_id IS '정책 ID';
COMMENT ON COLUMN policy_eligibility_ranks.target_type IS '대상 유형 ID';
COMMENT ON COLUMN policy_eligibility_ranks.rank IS '순위 (1, 2, 3)';
COMMENT ON COLUMN policy_eligibility_ranks.rank_name IS '순위 이름';
COMMENT ON COLUMN policy_eligibility_ranks.target_description IS '순위 대상 설명';
COMMENT ON COLUMN policy_eligibility_ranks.income_criteria_percent IS '소득 기준 백분율';
COMMENT ON COLUMN policy_eligibility_ranks.income_criteria_tyoe IS '소득 기준 유형';
COMMENT ON COLUMN policy_eligibility_ranks.asset_criteria IS '자산 기준';
COMMENT ON COLUMN policy_eligibility_ranks.car_asset_criteria IS '자동차 자산 기준';
COMMENT ON COLUMN policy_eligibility_ranks.additional_conditions IS '추가 기준';

-- Indexes for policy_eligibility_ranks
CREATE INDEX idx_policy_eligibility_ranks_policy_id ON policy_eligibility_ranks(policy_id);
CREATE INDEX idx_policy_eligibility_ranks_target_type ON policy_eligibility_ranks(target_type);


-- 2.5 Policy Financial Supports Table (정책 금융 지원)
CREATE TABLE policy_financial_supports (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    support_type financial_support_type NOT NULL,
    max_amount DECIMAL(15, 2),
    monthly_support DECIMAL(15, 2),
    interest_rate DECIMAL(5, 2),
    loan_limit_percent DECIMAL(5, 2),
    support_duration_months INTEGER,
    max_extension_years INTEGER,
    extension_conditions TEXT,
    partner_banks JSON,
    lifetime_limit INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Key
    CONSTRAINT fk_policy_financial_supports_policy
        FOREIGN KEY (policy_id)
        REFERENCES housing_policies(id)
        ON DELETE CASCADE
);

-- Comments for policy_financial_supports
COMMENT ON TABLE policy_financial_supports IS '정책 금융 지원';
COMMENT ON COLUMN policy_financial_supports.policy_id IS '정책 ID';
COMMENT ON COLUMN policy_financial_supports.support_type IS '지원 유형';
COMMENT ON COLUMN policy_financial_supports.max_amount IS '최대 지원 금액';
COMMENT ON COLUMN policy_financial_supports.monthly_support IS '월별 지원 금액';
COMMENT ON COLUMN policy_financial_supports.interest_rate IS '이자율';
COMMENT ON COLUMN policy_financial_supports.loan_limit_percent IS '대출 한도 비율';
COMMENT ON COLUMN policy_financial_supports.support_duration_months IS '지원 기간 (개월)';
COMMENT ON COLUMN policy_financial_supports.max_extension_years IS '최대 연장 기간 (년)';
COMMENT ON COLUMN policy_financial_supports.extension_conditions IS '연장 조건';
COMMENT ON COLUMN policy_financial_supports.partner_banks IS '제휴 은행 정보';
COMMENT ON COLUMN policy_financial_supports.lifetime_limit IS '생애 지원 횟수';

-- Indexes for policy_financial_supports
CREATE INDEX idx_policy_financial_supports_policy_id ON policy_financial_supports(policy_id);
CREATE INDEX idx_policy_financial_supports_support_type ON policy_financial_supports(support_type);


-- 2.6 Policy Contacts Table (정책 연락처)
CREATE TABLE policy_contacts (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    contract_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    display_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Key
    CONSTRAINT fk_policy_contacts_policy
        FOREIGN KEY (policy_id)
        REFERENCES housing_policies(id)
        ON DELETE CASCADE
);

-- Comments for policy_contacts
COMMENT ON TABLE policy_contacts IS '정책 연락처';
COMMENT ON COLUMN policy_contacts.policy_id IS '정책 ID';
COMMENT ON COLUMN policy_contacts.contract_name IS '기관/부서명';
COMMENT ON COLUMN policy_contacts.phone_number IS '전화번호';
COMMENT ON COLUMN policy_contacts.is_primary IS '주 연락처 여부';
COMMENT ON COLUMN policy_contacts.display_order IS '표시 순서';

-- Indexes for policy_contacts
CREATE INDEX idx_policy_contacts_policy_id ON policy_contacts(policy_id);


-- 2.7 Policy Links Table (정책 링크)
CREATE TABLE policy_links (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL,
    link_type link_type NOT NULL,
    link_name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Key
    CONSTRAINT fk_policy_links_policy
        FOREIGN KEY (policy_id)
        REFERENCES housing_policies(id)
        ON DELETE CASCADE
);

-- Comments for policy_links
COMMENT ON TABLE policy_links IS '정책 링크';
COMMENT ON COLUMN policy_links.policy_id IS '정책 ID';
COMMENT ON COLUMN policy_links.link_type IS '링크 유형';
COMMENT ON COLUMN policy_links.link_name IS '링크 이름';
COMMENT ON COLUMN policy_links.url IS '링크 URL';
COMMENT ON COLUMN policy_links.description IS '링크 설명';

-- Indexes for policy_links
CREATE INDEX idx_policy_links_policy_id ON policy_links(policy_id);
CREATE INDEX idx_policy_links_link_type ON policy_links(link_type);


-- ============================================
-- 3. Grant Permissions (Optional)
-- ============================================
-- Uncomment if you need to grant permissions to specific users/roles
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_user;


-- ============================================
-- 4. Verification Query
-- ============================================
-- Run this to verify all tables were created successfully
/*
SELECT
    table_name,
    (SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
    AND table_name IN (
    'policy_categories',
    'housing_policies',
    'policy_target_types',
    'policy_eligibility_ranks',
    'policy_financial_supports',
    'policy_contacts',
    'policy_links'
    )
ORDER BY table_name;
*/
