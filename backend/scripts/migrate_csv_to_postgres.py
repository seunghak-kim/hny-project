#!/usr/bin/env python3
"""
CSV 데이터를 PostgreSQL로 마이그레이션하는 간소화된 스크립트
지도 표시에 필요한 데이터에 집중: 부동산 정보 + 가격 정보
"""

import csv
import sys
import uuid
import hashlib
from pathlib import Path
from decimal import Decimal
from sqlalchemy.orm import Session

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.db.postgre_db import engine, Base, SessionLocal
from app.models.real_estate import RealEstate, Transaction, Region, PropertyType, TransactionType, NearbyFacility, RealEstateAgent

# 경로 설정
BACKEND_DATA_DIR = Path(__file__).parent.parent / "data" / "real_estate"

# 백엔드 CSV 파일들
BACKEND_CSVS = [
    BACKEND_DATA_DIR / "realestate_apt_ofst_20251008.csv",
    BACKEND_DATA_DIR / "real_estate_vila_20251008.csv",
    BACKEND_DATA_DIR / "realestate_oneroom_20251008csv.csv"
]


def map_property_type(type_name: str) -> PropertyType:
    """부동산 타입 문자열을 Enum으로 매핑"""
    type_mapping = {
        "아파트": PropertyType.APARTMENT,
        "오피스텔": PropertyType.OFFICETEL,
        "원룸": PropertyType.ONEROOM,
        "빌라": PropertyType.VILLA,
        "연립": PropertyType.VILLA,
        "다세대": PropertyType.VILLA,
        "단독/다가구": PropertyType.HOUSE,
        "단독": PropertyType.HOUSE,
        "다가구": PropertyType.HOUSE,
    }

    for key, value in type_mapping.items():
        if key in type_name:
            return value

    return PropertyType.APARTMENT  # 기본값


def get_or_create_region(db: Session, region_code: str, region_name: str) -> Region:
    """지역 정보 조회 또는 생성"""
    region = db.query(Region).filter(Region.code == region_code).first()
    if not region:
        region = Region(code=region_code, name=region_name)
        db.add(region)
        db.flush()
    return region


def safe_int(value, default=None):
    """안전한 int 변환"""
    if not value or value == '':
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=None):
    """안전한 float 변환"""
    if not value or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal(value, default=None):
    """안전한 Decimal 변환"""
    if not value or value == '':
        return default
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return default


def migrate_csv_to_postgres():
    """CSV 데이터를 PostgreSQL로 마이그레이션 (간소화)"""

    print("=" * 80)
    print("🏠 CSV → PostgreSQL 마이그레이션 시작 (Simplified)")
    print("=" * 80)
    print()

    # 테이블 생성
    print("📋 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ 테이블 생성 완료")
    print()

    db = SessionLocal()

    try:
        # 기존 데이터 삭제 (선택사항) - 외래키 순서대로 삭제
        print("🗑️  기존 데이터 삭제 중...")
        db.query(NearbyFacility).delete()
        db.query(RealEstateAgent).delete()
        db.query(Transaction).delete()
        db.query(RealEstate).delete()
        db.query(Region).delete()
        db.commit()
        print("   ✅ 기존 데이터 삭제 완료")
        print()

        total_properties = 0
        type_counts = {}
        existing_properties = set()  # 중복 체크용

        for csv_file in BACKEND_CSVS:
            if not csv_file.exists():
                print(f"⚠️  파일 없음: {csv_file}")
                continue

            print(f"📖 처리 중: {csv_file.name}")

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0

                for row in reader:
                    try:
                        # CSV 형식 감지 (apt/ofst vs vila/oneroom)
                        is_apt_format = 'complexName' in row or 'markerId' in row

                        # 필수 데이터 추출
                        if is_apt_format:
                            complex_name = row.get('complexName', '').strip()
                            marker_id = row.get('markerId', '')
                            completion = row.get('completionYearMonth', '')
                        else:
                            # vila/oneroom 형식
                            complex_name = row.get('atclNm', '').strip()
                            marker_id = row.get('atclNo', '')
                            completion = row.get('atclCfmYmd', '')

                        latitude = row.get('latitude', '').strip()
                        longitude = row.get('longitude', '').strip()

                        if not complex_name or not latitude or not longitude:
                            continue

                        # markerId가 없으면 생성 (이름 + 좌표 기반 해시)
                        if not marker_id:
                            # MD5 hash로 고유 ID 생성 (30자 이내)
                            hash_input = f"{complex_name}_{latitude}_{longitude}"
                            marker_id = hashlib.md5(hash_input.encode()).hexdigest()[:24]

                        # 중복 체크 (같은 마커 ID는 한 번만 처리)
                        if marker_id in existing_properties:
                            continue
                        existing_properties.add(marker_id)

                        # 부동산 타입
                        type_name = row.get('realEstateTypeName', '').strip()
                        property_type = map_property_type(type_name)

                        # 지역 정보
                        gu = row.get('구', '').strip()
                        dong = row.get('동', '').strip()
                        region_code = f"{gu}_{dong}" if gu and dong else "Unknown"
                        region_name = f"{gu} {dong}" if gu and dong else "Unknown"

                        region = get_or_create_region(db, region_code, region_name)

                        # 주소 생성
                        address = f"{gu} {dong} {complex_name}" if gu and dong else complex_name

                        # completion_date 정규화 (YYYYMM 형식, 최대 6자)
                        if completion and len(completion) > 6:
                            # "25.10.02." 같은 형식을 "202510"으로 변환 시도
                            completion = completion.replace('.', '').strip()[:6]

                        # RealEstate 객체 생성
                        real_estate = RealEstate(
                            property_type=property_type,
                            code=marker_id,
                            name=complex_name,
                            region_id=region.id,
                            address=address,
                            latitude=safe_decimal(latitude),
                            longitude=safe_decimal(longitude),
                            total_households=safe_int(row.get('totalHouseholdCount')),
                            total_buildings=safe_int(row.get('totalDongCount')),
                            completion_date=completion[:6] if completion else None,
                            min_exclusive_area=safe_float(row.get('minArea')),
                            max_exclusive_area=safe_float(row.get('maxArea')),
                            deal_count=safe_int(row.get('dealCount'), 0),
                            lease_count=safe_int(row.get('leaseCount'), 0),
                            rent_count=safe_int(row.get('rentCount'), 0),
                        )
                        db.add(real_estate)
                        db.flush()  # ID를 얻기 위해

                        # Transaction 데이터 생성 (가격 정보) - UUID로 고유성 보장
                        # 매매 거래
                        매매_최저가 = safe_int(row.get('매매_최저가'))
                        매매_최고가 = safe_int(row.get('매매_최고가'))
                        if 매매_최저가 or 매매_최고가:
                            transaction = Transaction(
                                real_estate_id=real_estate.id,
                                region_id=region.id,
                                transaction_type=TransactionType.SALE,
                                min_sale_price=매매_최저가 or 0,
                                max_sale_price=매매_최고가 or 0,
                                article_no=f"{marker_id}_sale_{uuid.uuid4().hex[:8]}",
                            )
                            db.add(transaction)

                        # 전세 거래
                        전세_최저가 = safe_int(row.get('전세_최저가'))
                        전세_최고가 = safe_int(row.get('전세_최고가'))
                        if 전세_최저가 or 전세_최고가:
                            transaction = Transaction(
                                real_estate_id=real_estate.id,
                                region_id=region.id,
                                transaction_type=TransactionType.JEONSE,
                                min_deposit=전세_최저가 or 0,
                                max_deposit=전세_최고가 or 0,
                                article_no=f"{marker_id}_jeonse_{uuid.uuid4().hex[:8]}",
                            )
                            db.add(transaction)

                        # 월세 거래
                        월세_최저가 = safe_int(row.get('월세_최저가'))
                        월세_최고가 = safe_int(row.get('월세_최고가'))
                        if 월세_최저가 or 월세_최고가:
                            transaction = Transaction(
                                real_estate_id=real_estate.id,
                                region_id=region.id,
                                transaction_type=TransactionType.RENT,
                                min_monthly_rent=월세_최저가 or 0,
                                max_monthly_rent=월세_최고가 or 0,
                                article_no=f"{marker_id}_rent_{uuid.uuid4().hex[:8]}",
                            )
                            db.add(transaction)

                        count += 1
                        type_counts[type_name] = type_counts.get(type_name, 0) + 1

                        # 배치 커밋 (1000개마다)
                        if count % 1000 == 0:
                            db.commit()
                            print(f"   진행 중... {count}개 처리")

                    except Exception as e:
                        print(f"   ⚠️  행 처리 실패: {e}")
                        db.rollback()
                        continue

                db.commit()
                print(f"   ✅ {count}개 속성 마이그레이션 완료")
                total_properties += count

        print()
        print("=" * 80)
        print("✅ 마이그레이션 완료!")
        print(f"📊 총 {total_properties}개 부동산 데이터 저장")
        print()
        print("📊 유형별 통계:")
        for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"   - {type_name}: {count:,}개")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_csv_to_postgres()
