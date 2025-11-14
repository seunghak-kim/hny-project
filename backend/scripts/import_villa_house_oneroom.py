"""
빌라/다가구/원룸 데이터 import 스크립트
CSV: real_estate_vila_20251008.csv, realestate_oneroom_20251008csv.csv
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from sqlalchemy.orm import Session
from app.models.real_estate import (
    RealEstate, Transaction, PropertyType, TransactionType,
    NearbyFacility, RealEstateAgent
)
from scripts.import_utils import (
    get_or_create_region, parse_region_from_name,
    safe_int, safe_float, safe_decimal, safe_str,
    parse_completion_date, parse_tag_list, clean_school_list
)


def import_individual_property_row(db: Session, row: pd.Series) -> tuple[RealEstate, Transaction, NearbyFacility, RealEstateAgent]:
    """
    빌라/다가구/원룸 CSV 한 행을 RealEstate + Transaction + NearbyFacility + Agent로 변환

    Args:
        db: 데이터베이스 세션
        row: CSV 데이터프레임의 한 행

    Returns:
        (RealEstate, Transaction, NearbyFacility, RealEstateAgent) 튜플
    """
    # 1. Region 생성/조회
    # cortarNo가 있으면 사용, 없으면 구/동으로 조회
    cortarNo = safe_str(row.get('cortarNo', ''))
    gu = safe_str(row['구'], '')
    dong = safe_str(row['동'], '')

    if cortarNo:
        region_name = f"{gu} {dong}"
        region = get_or_create_region(db, cortarNo, region_name)
    else:
        region = parse_region_from_name(db, gu, dong)

    # 2. PropertyType 결정
    real_estate_type_code = safe_str(row['realEstateTypeCode'], 'C02')
    type_map = {
        'C01': PropertyType.ONEROOM,
        'C02': PropertyType.VILLA,
        'C03': PropertyType.HOUSE,
    }
    property_type = type_map.get(real_estate_type_code, PropertyType.VILLA)

    # 3. RealEstate 객체 생성 (개별 매물 단위)
    article_no = safe_str(row['atclNo'])
    property_name = safe_str(row['atclNm'], 'Unknown')

    real_estate = RealEstate(
        property_type=property_type,
        code=article_no,  # 매물번호를 code로 사용
        name=property_name,
        region_id=region.id,

        # 주소 및 위치
        address=f"{gu} {dong} {property_name}",
        latitude=safe_decimal(row['latitude']),
        longitude=safe_decimal(row['longitude']),

        # 건물 기본 스펙 (개별 매물이므로 대부분 None)
        total_households=safe_int(row['totalHouseholdCount']),
        total_buildings=safe_int(row['totalDongCount']),
        completion_date=None,  # 개별 매물은 준공년월 없음
        floor_area_ratio=safe_float(row['floorAreaRatio']),

        # 개별 매물 상세 정보
        exclusive_area=safe_float(row['spc1']),  # 전용면적
        supply_area=safe_float(row['spc2']),  # 공급면적
        exclusive_area_pyeong=safe_float(row['spc1_pyeong']),
        supply_area_pyeong=safe_float(row['spc2_pyeong']),
        direction=safe_str(row['direction']),  # 방향
        floor_info=safe_str(row['flrInfo']),  # 층 정보

        # 건물 설명
        building_description=safe_str(row['atclFetrDesc']),
        tag_list=parse_tag_list(row['tagList']),

        # 매물 통계
        deal_count=safe_int(row['dealCount'], 0),
        lease_count=safe_int(row['leaseCount'], 0),
        rent_count=safe_int(row['rentCount'], 0),
        short_term_rent_count=safe_int(row['shortTermRentCount'], 0),
    )

    # 4. Transaction 생성 (개별 매물 가격)
    trade_type_code = safe_str(row['tradeTypeCode'], 'B2')
    sale_price = safe_int(row['매매가'], 0)
    deposit = safe_int(row['보증금'], 0)
    monthly_rent = safe_int(row['월세'], 0)

    # 거래 유형 결정
    if sale_price > 0:
        transaction_type = TransactionType.SALE
    elif monthly_rent > 0:
        transaction_type = TransactionType.RENT
    elif deposit > 0:
        transaction_type = TransactionType.JEONSE
    else:
        transaction_type = TransactionType.RENT  # 기본값

    transaction = Transaction(
        region_id=region.id,
        transaction_type=transaction_type,
        transaction_date=pd.Timestamp.now(),

        # 개별 거래 가격
        sale_price=sale_price,
        deposit=deposit,
        monthly_rent=monthly_rent,

        # 가격 범위 (동일 매물이므로 동일값)
        min_sale_price=sale_price,
        max_sale_price=sale_price,
        min_deposit=deposit,
        max_deposit=deposit,
        min_monthly_rent=monthly_rent,
        max_monthly_rent=monthly_rent,

        # 매물 번호
        article_no=article_no,
        article_confirm_ymd=safe_str(row['atclCfmYmd']),
    )

    # 5. NearbyFacility 생성
    nearby = NearbyFacility(
        subway_line=safe_str(row['지하철역명']),
        subway_distance=safe_int(row['지하철_거리_미터']),
        subway_walking_time=safe_int(row['지하철_도보_분']),
        elementary_schools=clean_school_list(row['초등학교']),
        middle_schools=clean_school_list(row['중학교']),
        high_schools=clean_school_list(row['고등학교']),
    )

    # 6. RealEstateAgent 생성
    agent = RealEstateAgent(
        agent_name=safe_str(row['rltrNm']),
        company_name=safe_str(row['cpNm']),
        is_direct_trade=(safe_str(row['directTradYn']) == 'Y'),
    )

    return real_estate, transaction, nearby, agent


def import_individual_property_csv(db: Session, csv_path: str, property_type_name: str) -> dict:
    """
    빌라/다가구/원룸 CSV 파일 전체를 import

    Args:
        db: 데이터베이스 세션
        csv_path: CSV 파일 경로
        property_type_name: "빌라" | "원룸" | "다가구"

    Returns:
        {'success': int, 'error': int, 'total': int}
    """
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"[{property_type_name}] 총 {len(df)}개 레코드")

    success_count = 0
    error_count = 0

    for idx, row in df.iterrows():
        try:
            # 중복 체크 (atclNo로)
            article_no = safe_str(row['atclNo'])
            existing = db.query(RealEstate).filter(RealEstate.code == article_no).first()
            if existing:
                print(f"  [SKIP] 중복: {article_no}")
                continue

            real_estate, transaction, nearby, agent = import_individual_property_row(db, row)

            # RealEstate 저장
            db.add(real_estate)
            db.flush()  # ID 생성

            # Transaction 저장
            transaction.real_estate_id = real_estate.id
            db.add(transaction)

            # NearbyFacility 저장
            nearby.real_estate_id = real_estate.id
            db.add(nearby)

            # RealEstateAgent 저장
            agent.real_estate_id = real_estate.id
            db.add(agent)

            success_count += 1

            if (success_count % 200) == 0:
                print(f"  📈 진행: {success_count:,}/{len(df)}")

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  ⚠️  Row {idx} - {row.get('atclNm', 'Unknown')}: {e}")
            continue

    return {'success': success_count, 'error': error_count, 'total': len(df)}


if __name__ == "__main__":
    import argparse
    from app.db.postgre_db import SessionLocal
    from app.models.real_estate import Region, RealEstate, Transaction, NearbyFacility, RealEstateAgent

    # 커맨드라인 argument 파싱
    parser = argparse.ArgumentParser(description='빌라/원룸/다가구 데이터 import')
    parser.add_argument('--type', choices=['villa', 'oneroom', 'all'], default=None,
                        help='Import 타입: villa, oneroom, all')
    parser.add_argument('--auto', action='store_true',
                        help='대화형 입력 없이 자동 실행 (--type과 함께 사용)')
    args = parser.parse_args()

    data_dir = project_root / "data" / "real_estate"

    print("=" * 60)
    print("🏠 빌라/원룸 데이터 Import")
    print("=" * 60)

    # 자동 실행 모드
    if args.auto and args.type:
        choice_map = {'villa': '1', 'oneroom': '2', 'all': '3'}
        choice = choice_map[args.type]
        print(f"\n[자동 실행 모드] {args.type} 선택됨")
    else:
        # 사용자 선택
        print("\n어떤 데이터를 import하시겠습니까?")
        print("1. 빌라 (6,631개)")
        print("2. 원룸 (1,013개)")
        print("3. 둘 다")
        choice = input("\n선택 (1/2/3): ").strip()

    db = SessionLocal()
    results = {}

    try:
        if choice in ['1', '3']:
            # 빌라 import
            csv_vila = data_dir / "real_estate_vila_20251008.csv"
            if csv_vila.exists():
                print("\n" + "=" * 60)
                print("📂 빌라 데이터 Import")
                print("=" * 60)
                result = import_individual_property_csv(db, str(csv_vila), "빌라")
                db.commit()
                results['빌라'] = result
                print(f"\n✅ 빌라: 성공 {result['success']:,}개, 실패 {result['error']:,}개")
            else:
                print(f"\n❌ 빌라 CSV 파일을 찾을 수 없습니다: {csv_vila}")

        if choice in ['2', '3']:
            # 원룸 import
            csv_oneroom = data_dir / "realestate_oneroom_20251008csv.csv"
            if csv_oneroom.exists():
                print("\n" + "=" * 60)
                print("📂 원룸 데이터 Import")
                print("=" * 60)
                result = import_individual_property_csv(db, str(csv_oneroom), "원룸")
                db.commit()
                results['원룸'] = result
                print(f"\n✅ 원룸: 성공 {result['success']:,}개, 실패 {result['error']:,}개")
            else:
                print(f"\n❌ 원룸 CSV 파일을 찾을 수 없습니다: {csv_oneroom}")

        # 최종 통계
        print("\n" + "=" * 60)
        print("📈 데이터베이스 전체 통계:")
        print("=" * 60)
        print(f"  Regions:          {db.query(Region).count():5,}개")
        print(f"  RealEstates:      {db.query(RealEstate).count():5,}개")
        print(f"  Transactions:     {db.query(Transaction).count():5,}개")
        print(f"  NearbyFacilities: {db.query(NearbyFacility).count():5,}개")
        print(f"  RealEstateAgents: {db.query(RealEstateAgent).count():5,}개")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    print("\n✅ Import 완료!")