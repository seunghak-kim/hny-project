-- ============================================
-- Housing Policy Sample Data Insert Script
-- ============================================
-- PostgreSQL Script
-- Created: 2025-11-25
-- Description: Inserts sample data for testing
-- ============================================

-- ============================================
-- 1. Insert Policy Categories
-- ============================================

-- 최상위 카테고리 (Level 1)
INSERT INTO policy_categories (name, partent_id, level, description, is_active)
VALUES
    ('임대주택', NULL, 1, '공공임대주택 관련 정책', TRUE),
    ('주거급여', NULL, 1, '주거급여 지원 관련 정책', TRUE),
    ('주택구입', NULL, 1, '주택구입 지원 관련 정책', TRUE),
    ('대출지원', NULL, 1, '주택대출 지원 관련 정책', TRUE);

-- 하위 카테고리 (Level 2)
INSERT INTO policy_categories (name, partent_id, level, description, is_active)
VALUES
    ('청년임대', (SELECT id FROM policy_categories WHERE name = '임대주택'), 2, '청년을 위한 임대주택', TRUE),
    ('신혼부부임대', (SELECT id FROM policy_categories WHERE name = '임대주택'), 2, '신혼부부를 위한 임대주택', TRUE),
    ('월세지원', (SELECT id FROM policy_categories WHERE name = '주거급여'), 2, '월세 지원 정책', TRUE),
    ('전세자금대출', (SELECT id FROM policy_categories WHERE name = '대출지원'), 2, '전세자금 대출 지원', TRUE);


-- ============================================
-- 2. Insert Housing Policies
-- ============================================

-- 청년 전세임대주택
INSERT INTO housing_policies (
    category_id,
    policy_name,
    policy_code,
    summary,
    description,
    application_method,
    application_url,
    officical_url,
    housing_requirements,
    lease_conditions,
    required_documments,
    regional_limitations,
    recruitment_info,
    status,
    is_active
)
VALUES (
    (SELECT id FROM policy_categories WHERE name = '청년임대'),
    '청년 전세임대주택',
    'YOUTH_LEASE_2024',
    '청년층의 주거비 부담을 덜어주기 위한 전세임대 지원 사업',
    '만 19세~39세 청년의 주거안정을 위해 기존 주택을 전세계약하여 저렴하게 재임대하는 제도입니다.',
    'LH 청약센터 온라인 신청 또는 방문 접수',
    'https://apply.lh.or.kr',
    'https://www.lh.or.kr/youth',
    '{"type": "기존주택", "min_area": 0, "max_area": 85, "unit": "m2"}',
    '{"deposit_limit": 150000000, "monthly_rent": 0, "contract_period": 2}',
    '["주민등록등본", "가족관계증명서", "소득증빙서류", "재학증명서(해당자)"]',
    '{"서울": 150000000, "수도권": 120000000, "광역시": 100000000, "기타": 80000000}',
    '{"period": "연 2회", "method": "선착순 및 추첨", "announcement": "LH 홈페이지"}',
    'recruiting',
    TRUE
);

-- 신혼부부 행복주택
INSERT INTO housing_policies (
    category_id,
    policy_name,
    policy_code,
    summary,
    description,
    application_method,
    application_url,
    officical_url,
    housing_requirements,
    lease_conditions,
    required_documments,
    regional_limitations,
    recruitment_info,
    status,
    is_active
)
VALUES (
    (SELECT id FROM policy_categories WHERE name = '신혼부부임대'),
    '신혼부부 행복주택',
    'NEWLYWED_HAPPY_2024',
    '신혼부부를 위한 공공임대주택 공급',
    '혼인 7년 이내 신혼부부에게 시세보다 저렴한 임대료로 최대 6년간 거주할 수 있는 공공임대주택을 공급합니다.',
    'LH 청약센터를 통한 온라인 청약',
    'https://apply.lh.or.kr',
    'https://www.lh.or.kr/newlywed',
    '{"type": "행복주택", "min_area": 45, "max_area": 85, "unit": "m2"}',
    '{"deposit_rate": 0.05, "monthly_rent_rate": 0.025, "contract_period": 6}',
    '["혼인관계증명서", "주민등록등본", "가족관계증명서", "소득증빙서류", "자산증빙서류"]',
    '{"전국": "면적별 차등"}',
    '{"period": "상시모집", "method": "자격심사 후 추첨", "announcement": "LH 홈페이지, 마이홈"}',
    'always',
    TRUE
);

-- 청년 월세 지원
INSERT INTO housing_policies (
    category_id,
    policy_name,
    policy_code,
    summary,
    description,
    application_method,
    application_url,
    officical_url,
    housing_requirements,
    lease_conditions,
    required_documments,
    regional_limitations,
    recruitment_info,
    status,
    is_active
)
VALUES (
    (SELECT id FROM policy_categories WHERE name = '월세지원'),
    '청년 월세 한시 특별지원',
    'YOUTH_RENT_2024',
    '청년의 월세 부담을 낮추기 위한 월세 지원금 지급',
    '만 19~34세 청년 중 소득 및 재산 요건을 충족하는 경우 월 최대 20만원씩 12개월간 월세를 지원합니다.',
    '복지로 온라인 신청',
    'https://www.bokjiro.go.kr',
    'https://www.molit.go.kr/youth',
    '{"type": "월세거주", "보증금_상한": 5000, "월세_상한": 70, "unit": "만원"}',
    '{"지원금액": 200000, "지원기간": 12, "unit": "개월"}',
    '["주민등록등본", "임대차계약서", "월세이체내역", "소득증빙서류"]',
    '{"전국": "동일"}',
    '{"period": "2024.12.31까지", "method": "선착순", "announcement": "복지로 홈페이지"}',
    'recruiting',
    TRUE
);


-- ============================================
-- 3. Insert Policy Target Types
-- ============================================

-- 청년 전세임대주택 대상
INSERT INTO policy_target_types (policy_id, target_type, age_min, age_max, specific_conditions, is_primary)
VALUES
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'youth', 19, 39, '무주택 세대구성원', TRUE),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'student', 19, 39, '대학생 또는 취업준비생', FALSE);

-- 신혼부부 행복주택 대상
INSERT INTO policy_target_types (policy_id, target_type, age_min, age_max, specific_conditions, is_primary)
VALUES
    ((SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'), 'newlywed', NULL, NULL, '혼인 7년 이내', TRUE),
    ((SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'), 'prospective_newlywed', NULL, NULL, '예비 신혼부부(혼인 예정)', FALSE);

-- 청년 월세 지원 대상
INSERT INTO policy_target_types (policy_id, target_type, age_min, age_max, specific_conditions, is_primary)
VALUES
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'), 'youth', 19, 34, '독립거주 무주택자', TRUE);


-- ============================================
-- 4. Insert Policy Eligibility Ranks
-- ============================================

-- 청년 전세임대주택 순위
INSERT INTO policy_eligibility_ranks (
    policy_id,
    target_type,
    rank,
    rank_name,
    target_description,
    income_criteria_percent,
    income_criteria_tyoe,
    asset_criteria,
    car_asset_criteria
)
VALUES
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'),
        (SELECT id FROM policy_target_types WHERE policy_id = (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024') AND target_type = 'youth' LIMIT 1),
        1,
        '1순위',
        '생계·의료급여 수급자',
        50,
        'median',
        28800000,
        NULL
    ),
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'),
        (SELECT id FROM policy_target_types WHERE policy_id = (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024') AND target_type = 'youth' LIMIT 1),
        2,
        '2순위',
        '차상위계층',
        100,
        'median',
        28800000,
        NULL
    );

-- 신혼부부 행복주택 순위
INSERT INTO policy_eligibility_ranks (
    policy_id,
    target_type,
    rank,
    rank_name,
    target_description,
    income_criteria_percent,
    income_criteria_tyoe,
    asset_criteria,
    car_asset_criteria
)
VALUES
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'),
        (SELECT id FROM policy_target_types WHERE policy_id = (SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024') AND target_type = 'newlywed' LIMIT 1),
        1,
        '소득 1순위',
        '도시근로자 월평균 소득 100% 이하',
        100,
        'urban_worker',
        28800000,
        3557000
    ),
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'),
        (SELECT id FROM policy_target_types WHERE policy_id = (SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024') AND target_type = 'newlywed' LIMIT 1),
        2,
        '소득 2순위',
        '도시근로자 월평균 소득 120% 이하',
        120,
        'urban_worker',
        28800000,
        3557000
    );


-- ============================================
-- 5. Insert Policy Financial Supports
-- ============================================

-- 청년 전세임대주택 금융지원
INSERT INTO policy_financial_supports (
    policy_id,
    support_type,
    max_amount,
    monthly_support,
    interest_rate,
    support_duration_months,
    max_extension_years,
    extension_conditions
)
VALUES
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'),
        'deposit_loan',
        150000000,
        NULL,
        1.0,
        24,
        4,
        '재계약 시 연장 가능'
    ),
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'),
        'monthly_rent',
        NULL,
        100000,
        NULL,
        24,
        4,
        '임차보증금 지원금액의 연 1.0~2.0% 수준'
    );

-- 신혼부부 행복주택 금융지원
INSERT INTO policy_financial_supports (
    policy_id,
    support_type,
    max_amount,
    interest_rate,
    support_duration_months,
    max_extension_years
)
VALUES
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'),
        'monthly_rent',
        NULL,
        2.5,
        72,
        0
    );

-- 청년 월세 지원 금융지원
INSERT INTO policy_financial_supports (
    policy_id,
    support_type,
    max_amount,
    monthly_support,
    support_duration_months,
    lifetime_limit
)
VALUES
    (
        (SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'),
        'monthly_rent',
        2400000,
        200000,
        12,
        1
    );


-- ============================================
-- 6. Insert Policy Contacts
-- ============================================

INSERT INTO policy_contacts (policy_id, contract_name, phone_number, is_primary, display_order)
VALUES
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'LH 청년전세임대 콜센터', '1600-1004', TRUE, 1),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'LH 서울지역본부', '02-1234-5678', FALSE, 2),
    ((SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'), 'LH 행복주택 콜센터', '1600-1004', TRUE, 1),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'), '주거급여 콜센터', '1600-0777', TRUE, 1),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'), '국토교통부 대표전화', '1599-0001', FALSE, 2);


-- ============================================
-- 7. Insert Policy Links
-- ============================================

INSERT INTO policy_links (policy_id, link_type, link_name, url, description)
VALUES
    -- 청년 전세임대주택 링크
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'application', '청약 신청하기', 'https://apply.lh.or.kr/youth', '청년 전세임대 청약 신청'),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'info', '상세 안내', 'https://www.lh.or.kr/youth/info', '정책 상세 정보'),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_LEASE_2024'), 'faq', '자주묻는질문', 'https://www.lh.or.kr/youth/faq', 'FAQ'),

    -- 신혼부부 행복주택 링크
    ((SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'), 'application', '청약 신청', 'https://apply.lh.or.kr/newlywed', '신혼부부 행복주택 청약'),
    ((SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'), 'info', '입주자모집공고', 'https://www.lh.or.kr/notice', '입주자 모집공고 확인'),
    ((SELECT id FROM housing_policies WHERE policy_code = 'NEWLYWED_HAPPY_2024'), 'resources', '자료실', 'https://www.lh.or.kr/resources', '서식 및 자료 다운로드'),

    -- 청년 월세 지원 링크
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'), 'application', '월세지원 신청', 'https://www.bokjiro.go.kr/youth', '복지로 온라인 신청'),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'), 'info', '정책 안내', 'https://www.molit.go.kr/youth/rent', '정책 상세 안내'),
    ((SELECT id FROM housing_policies WHERE policy_code = 'YOUTH_RENT_2024'), 'notice', '공지사항', 'https://www.molit.go.kr/notice', '공지사항 확인');


-- ============================================
-- 8. Verification Queries
-- ============================================

-- 전체 데이터 확인
/*
SELECT
    'policy_categories' as table_name,
    COUNT(*) as count
FROM policy_categories
UNION ALL
SELECT 'housing_policies', COUNT(*) FROM housing_policies
UNION ALL
SELECT 'policy_target_types', COUNT(*) FROM policy_target_types
UNION ALL
SELECT 'policy_eligibility_ranks', COUNT(*) FROM policy_eligibility_ranks
UNION ALL
SELECT 'policy_financial_supports', COUNT(*) FROM policy_financial_supports
UNION ALL
SELECT 'policy_contacts', COUNT(*) FROM policy_contacts
UNION ALL
SELECT 'policy_links', COUNT(*) FROM policy_links;
*/

-- 정책별 상세 정보 확인
/*
SELECT
    hp.policy_name,
    hp.policy_code,
    pc.name as category,
    COUNT(DISTINCT ptt.id) as target_types_count,
    COUNT(DISTINCT per.id) as eligibility_ranks_count,
    COUNT(DISTINCT pfs.id) as financial_supports_count,
    COUNT(DISTINCT pcon.id) as contacts_count,
    COUNT(DISTINCT pl.id) as links_count
FROM housing_policies hp
LEFT JOIN policy_categories pc ON hp.category_id = pc.id
LEFT JOIN policy_target_types ptt ON hp.id = ptt.policy_id
LEFT JOIN policy_eligibility_ranks per ON hp.id = per.policy_id
LEFT JOIN policy_financial_supports pfs ON hp.id = pfs.policy_id
LEFT JOIN policy_contacts pcon ON hp.id = pcon.policy_id
LEFT JOIN policy_links pl ON hp.id = pl.policy_id
GROUP BY hp.id, hp.policy_name, hp.policy_code, pc.name;
*/
