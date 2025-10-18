"""
아파트/오피스텔 데이터 import 스크립트
CSV: realestate_apt_ofst_20251008.csv
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from sqlalchemy.orm import Session
from app.models.real_estate import RealEstate, Transaction, PropertyType, TransactionType, NearbyFacility
from scripts.import_utils import (
    parse_region_from_name,
    safe_int, safe_float, safe_decimal, safe_str,
    parse_completion_date, parse_tag_list, clean_school_list
)


def import_apt_ofst_row(db: Session, row: pd.Series) -> tuple[RealEstate, list[Transaction], NearbyFacility]:
    """
    아파트/오피스텔 CSV 한 행을 RealEstate + Transaction + NearbyFacility로 변환

    Args:
        db: 데이터베이스 세션
        row: CSV 데이터프레임의 한 행

    Returns:
        (RealEstate, [Transaction], NearbyFacility) 튜플
    """
    # 1. Region 생성/조회 (구/동 이름으로)
    gu = safe_str(row['구'], '')
    dong = safe_str(row['동'], '')
    region = parse_region_from_name(db, gu, dong)
    region_name = f"{gu} {dong}"

    # 2. PropertyType 결정
    real_estate_type_code = safe_str(row['realEstateTypeCode'], 'APT')
    property_type = PropertyType.APARTMENT if real_estate_type_code == 'APT' else PropertyType.OFFICETEL

    # 3. RealEstate 객체 생성
    marker_id = safe_str(row['markerId'])
    complex_name = safe_str(row['complexName'], 'Unknown')

    real_estate = RealEstate(
        property_type=property_type,
        code=marker_id,
        name=complex_name,
        region_id=region.id,

        # 주소 및 위치
        address=f"{region_name} {complex_name}",  # CSV에 도로명주소가 없으므로 조합
        latitude=safe_decimal(row['latitude']),
        longitude=safe_decimal(row['longitude']),

        # 건물 기본 스펙
        total_households=safe_int(row['totalHouseholdCount']),
        total_buildings=safe_int(row['totalDongCount']),
        completion_date=parse_completion_date(row['completionYearMonth']),
        min_exclusive_area=safe_float(row['minArea']),
        max_exclusive_area=safe_float(row['maxArea']),
        representative_area=safe_float(row['representativeArea']),
        floor_area_ratio=safe_float(row['floorAreaRatio']),

        # 매물 통계
        deal_count=safe_int(row['dealCount'], 0),
        lease_count=safe_int(row['leaseCount'], 0),
        rent_count=safe_int(row['rentCount'], 0),
        short_term_rent_count=safe_int(row['shortTermRentCount'], 0),
    )

    # 4. Transaction 리스트 생성 (가격 정보가 있는 경우만)
    transactions = []

    # 매매 거래
    min_sale = safe_int(row['매매_최저가'])
    max_sale = safe_int(row['매매_최고가'])
    if min_sale and min_sale > 0:
        transactions.append(Transaction(
            region_id=region.id,
            transaction_type=TransactionType.SALE,
            transaction_date=pd.Timestamp.now(),
            min_sale_price=min_sale,
            max_sale_price=max_sale or min_sale,
        ))

    # 전세 거래
    min_jeonse = safe_int(row['전세_최저가'])
    max_jeonse = safe_int(row['전세_최고가'])
    if min_jeonse and min_jeonse > 0:
        transactions.append(Transaction(
            region_id=region.id,
            transaction_type=TransactionType.JEONSE,
            transaction_date=pd.Timestamp.now(),
            min_deposit=min_jeonse,
            max_deposit=max_jeonse or min_jeonse,
        ))

    # 월세 거래
    min_monthly = safe_int(row['월세_최저가'])
    max_monthly = safe_int(row['월세_최고가'])
    if min_monthly and min_monthly > 0:
        transactions.append(Transaction(
            region_id=region.id,
            transaction_type=TransactionType.RENT,
            transaction_date=pd.Timestamp.now(),
            min_monthly_rent=min_monthly,
            max_monthly_rent=max_monthly or min_monthly,
        ))

    # 5. NearbyFacility 생성
    nearby = NearbyFacility(
        # 지하철
        subway_line=safe_str(row['지하철역명']),
        subway_distance=safe_int(row['지하철_거리_미터']),
        subway_walking_time=safe_int(row['지하철_도보_분']),

        # 학교
        elementary_schools=clean_school_list(row['초등학교']),
        middle_schools=clean_school_list(row['중학교']),
        high_schools=clean_school_list(row['고등학교']),
    )

    return real_estate, transactions, nearby


def import_apt_ofst_csv(db: Session, csv_path: str) -> dict:
    """
    아파트/오피스텔 CSV 파일 전체를 import

    Returns:
        {'success': int, 'error': int, 'total': int}
    """
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"[아파트/오피스텔] 총 {len(df)}개 레코드")

    success_count = 0
    error_count = 0

    for idx, row in df.iterrows():
        try:
            # 중복 체크 (markerId로)
            marker_id = safe_str(row['markerId'])
            existing = db.query(RealEstate).filter(RealEstate.code == marker_id).first()
            if existing:
                print(f"  [SKIP] 중복: {marker_id} - {row['complexName']}")
                continue

            real_estate, transactions, nearby = import_apt_ofst_row(db, row)

            # RealEstate 저장
            db.add(real_estate)
            db.flush()  # ID 생성

            # Transaction 저장
            for trans in transactions:
                trans.real_estate_id = real_estate.id
                db.add(trans)

            # NearbyFacility 저장
            nearby.real_estate_id = real_estate.id
            db.add(nearby)

            success_count += 1

            if success_count % 100 == 0:
                print(f"  📈 진행: {success_count}/{len(df)}")

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  ⚠️  Row {idx} - {row.get('complexName', 'Unknown')}: {e}")
            continue

    return {'success': success_count, 'error': error_count, 'total': len(df)}


if __name__ == "__main__":
    from app.db.postgre_db import SessionLocal
    from app.models.real_estate import Region, RealEstate, Transaction, NearbyFacility

    data_dir = project_root / "data" / "real_estate"
    csv_path = data_dir / "realestate_apt_ofst_20251008.csv"

    print("=" * 60)
    print("🏢 아파트/오피스텔 데이터 Import")
    print("=" * 60)

    if not csv_path.exists():
        print(f"\n❌ CSV 파일을 찾을 수 없습니다: {csv_path}")
        sys.exit(1)

    db = SessionLocal()

    try:
        print(f"\n📂 파일: {csv_path.name}")
        result = import_apt_ofst_csv(db, str(csv_path))
        db.commit()

        print(f"\n✅ 아파트/오피스텔: 성공 {result['success']:,}개, 실패 {result['error']:,}개")

        # 최종 통계
        print("\n" + "=" * 60)
        print("📈 데이터베이스 전체 통계:")
        print("=" * 60)
        print(f"  Regions:          {db.query(Region).count():5,}개")
        print(f"  RealEstates:      {db.query(RealEstate).count():5,}개")
        print(f"  Transactions:     {db.query(Transaction).count():5,}개")
        print(f"  NearbyFacilities: {db.query(NearbyFacility).count():5,}개")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    print("\n✅ Import 완료!")
