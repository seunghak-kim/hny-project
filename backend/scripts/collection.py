"""
부동산 실거래가 데이터 수집 스크립트 (분리된 모델 기반)
2024년 11월 ~ 2025년 11월
서초구, 강남구, 송파구
파이프 라인 작업
1. 지역 코드 추출 O
2. 실거래가 api 연결
3. 카카오 api
4. csv 저장
"""
import os
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict
from dotenv import load_dotenv
import requests
import json
import sys
from pathlib import Path
from tqdm import tqdm

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# app
from app.utils.building_api import TransactionPriceAPI, RegionCodeManager
from app.models.building import Building
from app.models.region import Region
from app.models.infrastructure import Infrastructure
from app.models.transaction.transaction import Transaction
from app.models.transaction.sale_transaction import SaleTransaction
from app.models.transaction.rent_transaction import RentTransaction
from app.models.transaction.apartment import ApartmentSaleTransaction
from app.models.transaction.villa import VillaSaleTransaction
from app.models.transaction.house import HouseSaleTransaction
from app.models.enums import PropertyType, TransactionType
from app.db.postgre_db import SessionLocal, get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

load_dotenv()

# ==================== 상수 정의 ====================
# API 키
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

# 지역 정보
REGIONS = {
    '11650': '서초구',
    '11680': '강남구',
    '11710': '송파구'
}
CITY_NAME = '서울'
REGION_NAMES = ['서초구', '강남구', '송파구']

# 데이터 수집 기간
START_YM = '202411'
END_YM = '202511'

# API 설정
API_PAGE_SIZE = '1000'
KAKAO_API_DELAY = 0.5  # 카카오 API 호출 간 지연 시간 (초) - 429 에러 방지
FACILITY_SEARCH_RADIUS = 1000  # 주변 시설 검색 반경 (미터)
KAKAO_RETRY_MAX = 3  # 카카오 API 재시도 최대 횟수
KAKAO_RETRY_DELAY = 2  # 429 에러 시 대기 시간 (초)

# 카카오 카테고리 코드
CATEGORY_SUBWAY = 'SW8'  # 지하철역
CATEGORY_SCHOOL = 'SC4'  # 학교
CATEGORY_MART = 'MT1'    # 대형마트

# 배치 처리 설정
BATCH_COMMIT_SIZE = 100  # N건마다 커밋

# ==================== 전역 변수 ====================
transaction_api = TransactionPriceAPI()
region_code_manager = RegionCodeManager()

# 캐시 (성능 최적화용)
COORDINATE_CACHE: Dict[str, Tuple[Optional[float], Optional[float], Optional[str]]] = {}
building_cache: Dict[Tuple, int] = {}  # key: (address, name, property_type), value: building_id
region_cache: Dict[str, int] = {}  # key: legal_dong_code, value: region_id
region_name_cache: Dict[Tuple[str, str], int] = {}  # key: (gu_name, dong_name), value: region_id

def parse_int(val, default=0):
    if not val : return default
    try:
        return int(str(val).replace(',', '').strip())
    except:
        return default

def parse_str(val, default=None):
    if not val or val == '': return default
    return str(val).strip()

def parse_date(year, month, day):
    """년, 월, 일을 받아서 datetime 객체로 변환"""
    try:
        y = str(year).strip() if year else '2024'
        m = str(month).strip().zfill(2) if month else '01'
        d = str(day).strip().zfill(2) if day else '01'
        return datetime.strptime(f"{y}{m}{d}", "%Y%m%d")
    except:
        return datetime.now()

def parse_date_string(date_str):
    """
    다양한 형식의 날짜 문자열을 datetime으로 변환
    지원 형식: '24.04.24', '20240424', '2024-04-24' 등
    """
    if not date_str or date_str == '':
        return None

    try:
        date_str = str(date_str).strip()

        # 형식 1: YY.MM.DD (예: '24.04.24')
        if '.' in date_str and len(date_str.split('.')) == 3:
            parts = date_str.split('.')
            if len(parts[0]) == 2:  # 2자리 연도
                year = int('20' + parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return datetime(year, month, day)

        # 형식 2: YYYYMMDD (예: '20240424')
        if len(date_str) == 8 and date_str.isdigit():
            return datetime.strptime(date_str, "%Y%m%d")

        # 형식 3: YYYY-MM-DD (예: '2024-04-24')
        if '-' in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d")

        return None
    except Exception as e:
        print(f"Warning: Failed to parse date string '{date_str}': {e}")
        return None

def parse_float(val, default=0.0):
    """문자열을 float로 변환"""
    if not val:
        return default
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return default

# ==================== PostgreSQL 저장 헬퍼 함수 ====================

def initialize_regions(db: Session) -> None:
    """
    서초구, 강남구, 송파구의 모든 동(Region)을 DB에 미리 생성하고 캐시에 로드
    성능 최적화: 매번 DB 조회/생성 대신 초기에 한 번만 실행
    """
    global region_cache, region_name_cache

    logger.info("=" * 80)
    logger.info("Region 데이터 초기화 시작 (%s)", ", ".join(REGION_NAMES))
    logger.info("=" * 80)

    try:
        total_created = 0
        total_existing = 0

        # 각 구별로 모든 동 정보 가져오기
        for gu in REGION_NAMES:
            logger.info("[%s] 동 정보 조회 중...", gu)
            results_list = region_code_manager.get_dong_codes(CITY_NAME, gu)

            if not results_list:
                logger.warning("%s에 대한 동 정보를 찾을 수 없습니다.", gu)
                continue

            logger.info("[%s] %d개 동 발견", gu, len(results_list))

            # 각 동별로 Region 생성 또는 조회
            for result in results_list:
                legal_dong_code = result['법정동코드']
                gu_name = result['시군구명']
                dong_name = result['읍면동명']

                # DB에서 기존 Region 확인
                existing_region = db.query(Region).filter(
                    Region.legal_dong_code == legal_dong_code
                ).first()

                if existing_region:
                    # 캐시에 저장 (두 가지 방식)
                    region_cache[legal_dong_code] = existing_region.id
                    region_name_cache[(gu_name, dong_name)] = existing_region.id
                    total_existing += 1
                else:
                    # 새로운 Region 생성
                    new_region = Region(
                        legal_dong_code=legal_dong_code,
                        cido_name=result['시도명'],
                        gu_name=gu_name,
                        umd_name=dong_name
                    )
                    db.add(new_region)
                    db.flush()  # ID 즉시 할당

                    # 캐시에 저장 (두 가지 방식)
                    region_cache[legal_dong_code] = new_region.id
                    region_name_cache[(gu_name, dong_name)] = new_region.id
                    total_created += 1
                    logger.debug("생성: %s %s (코드: %s)", gu_name, dong_name, legal_dong_code)

        # 한 번에 커밋
        db.commit()

        logger.info("=" * 80)
        logger.info("Region 초기화 완료!")
        logger.info("  - 새로 생성: %d개", total_created)
        logger.info("  - 기존 로드: %d개", total_existing)
        logger.info("  - 법정동코드 캐시: %d개", len(region_cache))
        logger.info("  - 구/동 이름 캐시: %d개", len(region_name_cache))
        logger.info("=" * 80)

    except Exception as e:
        logger.error("Region 초기화 중 오류 발생: %s", str(e), exc_info=True)
        db.rollback()
        raise

def get_region_id_by_dong_code(legal_dong_code: str) -> Optional[int]:
    """
    법정동코드로 Region ID 조회 (캐시에서만 조회, O(1))

    Arguments:
        legal_dong_code: 법정동코드 (10자리)

    Returns:
        region_id 또는 None
    """
    return region_cache.get(legal_dong_code)

def get_region_id_by_dong_name(gu_name: str, dong_name: str) -> Optional[int]:
    """
    구 이름과 동 이름으로 Region ID 조회 (캐시에서만 조회, O(1))
    initialize_regions() 호출 후에만 사용 가능

    Arguments:
        gu_name: 구 이름 (예: 서초구, 강남구, 송파구)
        dong_name: 동 이름 (예: 잠원동, 방배동)

    Returns:
        region_id 또는 None
    """
    region_id = region_name_cache.get((gu_name, dong_name))
    if not region_id:
        logger.warning("Region not found in cache: %s/%s", gu_name, dong_name)
    return region_id

def check_building_exists(
    db: Session,
    address: str,
    name: str,
    building_type: PropertyType
) -> Optional[int]:
    """
    Building이 이미 존재하는지 확인하고 building_id 반환
    캐시 먼저 확인 후, 없으면 DB 조회

    Returns:
        building_id 또는 None (존재하지 않으면)
    """
    # 캐시 확인
    cache_key = (address, name, building_type.value)
    if cache_key in building_cache:
        return building_cache[cache_key]

    # DB 조회
    building = db.query(Building).filter(
        Building.address == address,
        Building.name == name,
        Building.building_type == building_type
    ).first()

    if building:
        # 캐시에 저장
        building_cache[cache_key] = building.id
        return building.id

    return None

def check_infrastructure_exists(db: Session, building_id: int) -> bool:
    """
    Building에 Infrastructure가 이미 존재하는지 확인

    Returns:
        True if exists, False otherwise
    """
    existing = db.query(Infrastructure).filter(
        Infrastructure.building_id == building_id
    ).first()

    return existing is not None

# ==================== PostgreSQL 저장 헬퍼 함수 ====================

def get_or_create_building(
    db: Session,
    address: str,
    name: str,
    building_type: PropertyType,
    region_code: str,
    legal_dong: str,
    lat: Optional[float],
    lng: Optional[float],
    build_year: Optional[str],
    min_area: Optional[float] = None,
    max_area: Optional[float] = None
) -> Optional[int]:
    """Building을 찾거나 생성하고 building_id 반환"""

    # 캐시 확인
    cache_key = (address, name, building_type.value)
    if cache_key in building_cache:
        return building_cache[cache_key]

    try:
        # 기존 Building 찾기
        building = db.query(Building).filter(
            Building.address == address,
            Building.name == name,
            Building.building_type == building_type
        ).first()

        if building:
            building_cache[cache_key] = building.id
            return building.id

        # Region ID 조회 - 캐시에서만 조회 (O(1), DB 접근 없음)
        gu_name = REGIONS.get(region_code)
        if not gu_name:
            logger.warning("Unknown region_code: %s", region_code)
            return None

        region_id = get_region_id_by_dong_name(gu_name, legal_dong)
        if not region_id:
            logger.warning("Could not get region_id: %s (%s/%s)", region_code, gu_name, legal_dong)
            return None

        # 새로운 Building 생성
        new_building = Building(
            building_type=building_type,
            name=name,
            build_year=build_year,
            min_area=min_area,
            max_area=max_area,
            region_id=region_id,
            legal_dong=legal_dong,
            address=address,
            latitude=lat,
            longitude=lng
        )
        db.add(new_building)
        db.commit()
        db.refresh(new_building)

        # 캐시에 저장
        building_cache[cache_key] = new_building.id
        return new_building.id

    except Exception as e:
        logger.error("Error creating building (%s, %s): %s", address, name, str(e), exc_info=True)
        db.rollback()
        return None

def create_infrastructure(
    db: Session,
    building_id: int,
    subway_stations: Optional[str],
    schools: Optional[str],
    marts: Optional[str]
) -> bool:
    """Infrastructure 생성"""
    try:
        # 기존 Infrastructure 확인
        existing = db.query(Infrastructure).filter(
            Infrastructure.building_id == building_id
        ).first()

        if existing:
            # 이미 존재하면 업데이트
            existing.nearby_subway_stations = subway_stations
            existing.nearby_schools = schools
            existing.nearby_marts = marts
        else:
            # 새로 생성
            infra = Infrastructure(
                building_id=building_id,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(infra)

        db.commit()
        return True
    except Exception as e:
        logger.error("Error creating infrastructure (building_id=%s): %s", building_id, str(e), exc_info=True)
        db.rollback()
        return False

def create_transaction(
    db: Session,
    building_id: int,
    transaction_type: TransactionType,
    exclusive_area: float,
    floor: int,
    trans_date: datetime
) -> Optional[int]:
    """Transaction 생성하고 transaction_id 반환"""
    try:
        transaction = Transaction(
            building_id=building_id,
            transaction_type=transaction_type,
            exclusive_area=exclusive_area,
            floor=floor,
            trans_date=trans_date
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction.id

    except Exception as e:
        logger.error("Error creating transaction (building_id=%s): %s", building_id, str(e), exc_info=True)
        db.rollback()
        return None

def create_sale_transaction(
    db: Session,
    transaction_id: int,
    deal_amount: int,
    cdeal_type: Optional[str] = None,
    cdeal_day: Optional[str] = None,
    dealing_gbn: Optional[str] = None,
    estate_agent_sgg_nm: Optional[str] = None,
    saler_gbn: Optional[str] = None,
    buyer_gbn: Optional[str] = None
) -> Optional[int]:
    """SaleTransaction 생성하고 sale_transaction_id 반환"""
    try:
        sale = SaleTransaction(
            transaction_id=transaction_id,
            deal_amount=deal_amount,
            cdeal_type=cdeal_type,
            cdeal_day=cdeal_day,
            dealing_gbn=dealing_gbn,
            estate_agent_sgg_nm=estate_agent_sgg_nm,
            saler_gbn=saler_gbn,
            buyer_gbn=buyer_gbn
        )
        db.add(sale)
        db.commit()
        db.refresh(sale)
        return sale.id
    except Exception as e:
        logger.error("Error creating sale transaction (transaction_id=%s): %s", transaction_id, str(e), exc_info=True)
        db.rollback()
        return None

def create_rent_transaction(
    db: Session,
    transaction_id: int,
    deposit: int,
    monthly_rent: int,
    contract_term: Optional[str] = None,
    contract_type: Optional[str] = None,
    user_rr_right: Optional[str] = None,
    pre_deposit: Optional[int] = None,
    pre_monthly_rent: Optional[int] = None
) -> Optional[int]:
    """RentTransaction 생성하고 rent_transaction_id 반환"""
    try:
        rent = RentTransaction(
            transaction_id=transaction_id,
            deposit=deposit,
            monthly_rent=monthly_rent,
            contract_term=contract_term,
            contract_type=contract_type,
            user_rr_right=user_rr_right,
            pre_deposit=pre_deposit,
            pre_monthly_rent=pre_monthly_rent
        )
        db.add(rent)
        db.commit()
        db.refresh(rent)
        return rent.id
    except Exception as e:
        logger.error("Error creating rent transaction (transaction_id=%s): %s", transaction_id, str(e), exc_info=True)
        db.rollback()
        return None

def create_apartment_sale_transaction(
    db: Session,
    sale_transaction_id: int,
    apt_dong: Optional[str] = None,
    land_leasehold_gbn: Optional[str] = None,
    rgst_date: Optional[str] = None
) -> bool:
    """ApartmentSaleTransaction 생성"""
    try:
        apt_sale = ApartmentSaleTransaction(
            sale_transaction_id=sale_transaction_id,
            apt_dong=parse_int(apt_dong),
            land_leasehold_gbn=land_leasehold_gbn,
            rgst_date=parse_date_string(rgst_date)
        )
        db.add(apt_sale)
        db.commit()
        return True
    except Exception as e:
        logger.error("Error creating apartment sale transaction (sale_transaction_id=%s): %s", sale_transaction_id, str(e), exc_info=True)
        db.rollback()
        return False

def create_villa_sale_transaction(
    db: Session,
    sale_transaction_id: int,
    land_area: Optional[float] = None
) -> bool:
    """VillaSaleTransaction 생성"""
    try:
        villa_sale = VillaSaleTransaction(
            sale_transaction_id=sale_transaction_id,
            land_area=land_area
        )
        db.add(villa_sale)
        db.commit()
        return True
    except Exception as e:
        logger.error("Error creating villa sale transaction (sale_transaction_id=%s): %s", sale_transaction_id, str(e), exc_info=True)
        db.rollback()
        return False

def create_house_sale_transaction(
    db: Session,
    sale_transaction_id: int,
    total_floor_area: Optional[float] = None,
    plottage_area: Optional[float] = None
) -> bool:
    """HouseSaleTransaction 생성"""
    try:
        house_sale = HouseSaleTransaction(
            sale_transaction_id=sale_transaction_id,
            total_floor_area=total_floor_area,
            plottage_area=plottage_area
        )
        db.add(house_sale)
        db.commit()
        return True
    except Exception as e:
        logger.error("Error creating house sale transaction (sale_transaction_id=%s): %s", sale_transaction_id, str(e), exc_info=True)
        db.rollback()
        return False

def get_coordinates_from_kakao(address: str, region_code: str = None) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    카카오 API를 사용하여 주소로부터 위경도 좌표와 동 정보를 추출

    Args:
        address: 지번 주소
        region_code: 지역 코드 (11650: 서초구, 11680: 강남구, 11710: 송파구)

    Returns:
        (latitude, longitude, dong) 튜플, 실패 시 (None, None, None)
    """
    # 캐시 확인
    if address in COORDINATE_CACHE:
        cached = COORDINATE_CACHE[address]
        # 캐시된 값이 2개짜리 튜플이면 3개로 변환
        if len(cached) == 2:
            return (cached[0], cached[1], None)
        return cached

    # API 키 확인
    if not KAKAO_REST_API_KEY:
        logger.error("카카오 REST API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        COORDINATE_CACHE[address] = (None, None, None)
        return (None, None, None)

    # 재시도 로직
    for attempt in range(KAKAO_RETRY_MAX):
        try:
            # 지역명 추가
            full_address = address
            if region_code and region_code in REGIONS:
                full_address = f"서울특별시 {REGIONS[region_code]} {address}"

            # 카카오 로컬 API 주소 검색
            url = "https://dapi.kakao.com/v2/local/search/address.json"
            headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
            params = {"query": full_address}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            # 403 Forbidden 에러 처리
            if response.status_code == 403:
                logger.error("카카오 API 403 Forbidden 에러. API 키 권한을 확인하세요. (키: %s...)", KAKAO_REST_API_KEY[:10] if KAKAO_REST_API_KEY else "None")
                logger.error("카카오 개발자 콘솔(https://developers.kakao.com)에서 플랫폼 설정과 REST API 키를 확인하세요.")
                COORDINATE_CACHE[address] = (None, None, None)
                return (None, None, None)

            # 429 에러 처리 (Too Many Requests)
            if response.status_code == 429:
                if attempt < KAKAO_RETRY_MAX - 1:
                    wait_time = KAKAO_RETRY_DELAY * (attempt + 1)
                    logger.warning("카카오 API 429 에러 (주소 검색), %d초 대기 후 재시도 (%d/%d)",
                                 wait_time, attempt + 1, KAKAO_RETRY_MAX)
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("카카오 API 429 에러 (주소 검색), 최대 재시도 횟수 초과")
                    COORDINATE_CACHE[address] = (None, None, None)
                    return (None, None, None)

            response.raise_for_status()
            data = response.json()

            if data.get("documents"):
                # 첫 번째 결과 사용
                doc = data["documents"][0]

                # address 또는 road_address에서 좌표 추출
                lat, lng, dong = None, None, None
                if doc.get("address"):
                    lat = float(doc["address"]["y"])
                    lng = float(doc["address"]["x"])
                    # 동 정보 추출 (region_3depth_name)
                    dong = doc["address"].get("region_3depth_name", "")
                elif doc.get("road_address"):
                    lat = float(doc["road_address"]["y"])
                    lng = float(doc["road_address"]["x"])
                    # road_address에서도 동 정보 가져오기
                    dong = doc.get("address", {}).get("region_3depth_name", "")

                # 캐시에 저장
                COORDINATE_CACHE[address] = (lat, lng, dong)

                if lat and lng:
                    logger.debug("좌표 및 동 추출 성공: %s -> (%s, %s, %s)", address, lat, lng, dong)

                # API 호출 간 지연 (429 에러 방지)
                time.sleep(KAKAO_API_DELAY)
                return (lat, lng, dong)
            else:
                logger.warning("좌표를 찾을 수 없음: %s", full_address)
                COORDINATE_CACHE[address] = (None, None, None)
                return (None, None, None)

        except requests.RequestException as e:
            if attempt < KAKAO_RETRY_MAX - 1:
                logger.warning("카카오 API 호출 실패 (주소 검색), 재시도 (%d/%d): %s",
                             attempt + 1, KAKAO_RETRY_MAX, str(e))
                time.sleep(KAKAO_RETRY_DELAY)
                continue
            else:
                logger.error("카카오 API 호출 실패 (주소 검색), 최대 재시도 횟수 초과: %s", str(e))
                COORDINATE_CACHE[address] = (None, None, None)
                return (None, None, None)

        except Exception as e:
            logger.error("좌표 추출 오류: %s", str(e), exc_info=True)
            COORDINATE_CACHE[address] = (None, None, None)
            return (None, None, None)

    # 모든 재시도 실패
    COORDINATE_CACHE[address] = (None, None, None)
    return (None, None, None)
    
    
def get_nearby_facilities(lat: float, lng: float, category_code: str, radius: int = 1000) -> Optional[str]:
    """
    카카오 API를 사용하여 주변 시설 정보를 가져옴 (재시도 로직 포함)

    Args:
        lat: 위도
        lng: 경도
        category_code: 카테고리 코드 (SW8: 지하철역, SC4: 학교, MT1: 대형마트)
        radius: 검색 반경 (미터, 기본 1000m)

    Returns:
        시설 정보 JSON 문자열, 실패 시 None
    """
    if not KAKAO_REST_API_KEY or not lat or not lng:
        return None

    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "category_group_code": category_code,
        "x": lng,  # 경도
        "y": lat,  # 위도
        "radius": radius,
        "sort": "distance"
    }

    # 재시도 로직
    for attempt in range(KAKAO_RETRY_MAX):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            # 429 에러 처리 (Too Many Requests)
            if response.status_code == 429:
                if attempt < KAKAO_RETRY_MAX - 1:
                    wait_time = KAKAO_RETRY_DELAY * (attempt + 1)  # Exponential backoff
                    logger.warning("카카오 API 429 에러 (category=%s), %d초 대기 후 재시도 (%d/%d)",
                                 category_code, wait_time, attempt + 1, KAKAO_RETRY_MAX)
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("카카오 API 429 에러 (category=%s), 최대 재시도 횟수 초과", category_code)
                    return None

            response.raise_for_status()
            data = response.json()

            if data.get("documents"):
                facilities = []
                for doc in data["documents"]:
                    facility = {
                        "name": doc.get("place_name"),
                        "category": doc.get("category_name"),
                        "address": doc.get("address_name"),
                        "road_address": doc.get("road_address_name"),
                        "distance": int(doc.get("distance", 0)),
                        "phone": doc.get("phone", "")
                    }
                    facilities.append(facility)

                return json.dumps(facilities, ensure_ascii=False) if facilities else None
            else:
                return None

        except requests.RequestException as e:
            if attempt < KAKAO_RETRY_MAX - 1:
                logger.warning("카카오 API 호출 실패 (category=%s), 재시도 (%d/%d): %s",
                             category_code, attempt + 1, KAKAO_RETRY_MAX, str(e))
                time.sleep(KAKAO_RETRY_DELAY)
                continue
            else:
                logger.error("카카오 API 호출 실패 (category=%s), 최대 재시도 횟수 초과: %s", category_code, str(e))
                return None
        except Exception as e:
            logger.error("시설 정보 추출 오류 (category=%s): %s", category_code, str(e))
            return None

    return None
    
def get_all_nearby_facilities(lat: Optional[float], lng: Optional[float]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    주변 모든 시설 정보를 가져옴

    Args:
        lat: 위도
        lng: 경도

    Returns:
        (지하철역, 학교, 마트) 정보 튜플
    """
    if not lat or not lng:
        return (None, None, None)

    # 1km 이내 지하철역
    subway_stations = get_nearby_facilities(lat, lng, CATEGORY_SUBWAY, FACILITY_SEARCH_RADIUS)
    time.sleep(KAKAO_API_DELAY)

    # 인근 학교 (초중고)
    schools = get_nearby_facilities(lat, lng, CATEGORY_SCHOOL, FACILITY_SEARCH_RADIUS)
    time.sleep(KAKAO_API_DELAY)

    # 인근 마트
    marts = get_nearby_facilities(lat, lng, CATEGORY_MART, FACILITY_SEARCH_RADIUS)
    time.sleep(KAKAO_API_DELAY)

    return (subway_stations, schools, marts)

#### Region dataset 만들기 

def get_region_code_csv(city_name:str, region_name:List[str], 
                    output_path:str = './data/real_estate/region.csv'):
    output_dir = os.path.dirname(output_path)
    data_list =  []
    for region in region_name:
        results = region_code_manager.get_dong_codes(city_name, region)
        for result in results:
            data_list.append([
                result['sigungu_code'],
                result['법정동코드'],
                result['시도명'],
                result['시군구명'],
                result['읍면동명']
            ])
            
    region_df = pd.DataFrame(data_list, columns=['code', 'legal_dong_code', 'cido_name','gu_name', 'umd_name'])
    # Region data csv 파일 만들기 
    region_df.to_csv(output_path, index=False)
    
def collect_apt_sale(api: TransactionPriceAPI, lawd_cd, db: Session):
    """아파트 매매 수집 (PostgreSQL)"""
    logger.info("아파트 매매 데이터 수집 시작: %s", REGIONS.get(lawd_cd))
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'apt_trade', API_PAGE_SIZE, True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 아파트 매매", unit="건"):
        name = parse_str(data.get('aptNm'))
        if not name:
            continue

        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        if '*' in address:
            continue  # 마스킹이 있으면 skip

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, name, PropertyType.APARTMENT)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            # Building이 이미 존재하는 경우
            # Infrastructure도 있는지 확인
            if check_infrastructure_exists(db, existing_building_id):
                # Building과 Infrastructure 모두 존재 -> 카카오 API 호출 불필요
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", name, address)
            else:
                # Building은 있지만 Infrastructure가 없음 -> 좌표가 있으면 Infrastructure 생성
                # Building 테이블에서 좌표 가져오기
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    # SQLAlchemy 타입 체커 문제 우회
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # Building이 존재하지 않음 -> 카카오 API 호출 필요
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # 1. Building 생성
            building_id = get_or_create_building(
                db=db,
                address=address,
                name=name,
                building_type=PropertyType.APARTMENT,
                region_code=lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('excluUseAr')),
                max_area=parse_float(data.get('excluUseAr'))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)

        # 3. Transaction 생성
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.SALE,
            exclusive_area=parse_float(data.get('excluUseAr')),
            floor=parse_int(data.get('floor'), 1),
            trans_date=trans_date
        )

        if not transaction_id:
            logger.debug("Transaction 생성 실패로 SKIP: %s", address)
            continue

        # 4. SaleTransaction 생성
        sale_transaction_id = create_sale_transaction(
            db=db,
            transaction_id=transaction_id,
            deal_amount=parse_int(data.get('dealAmount')),
            cdeal_type=parse_str(data.get('cdealType')),
            cdeal_day=parse_str(data.get('cdealDay')),
            dealing_gbn=parse_str(data.get('dealingGbn')),
            estate_agent_sgg_nm=parse_str(data.get('estateAgentSggNm')),
            saler_gbn=parse_str(data.get('slerGbn')),
            buyer_gbn=parse_str(data.get('buyerGbn'))
        )

        if not sale_transaction_id:
            logger.debug("SaleTransaction 생성 실패로 SKIP: %s", address)
            continue

        # 5. ApartmentSaleTransaction 생성
        create_apartment_sale_transaction(
            db=db,
            sale_transaction_id=sale_transaction_id,
            apt_dong=data.get('aptDong'),
            land_leasehold_gbn=parse_str(data.get('landLeaseholdGbn')),
            rgst_date=parse_str(data.get('rgstDate'))
        )

        count += 1

    logger.info("아파트 매매 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return 

def collect_apt_rent(api: TransactionPriceAPI, lawd_cd, db: Session):
    """아파트 전월세 수집 (PostgreSQL)"""
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'apt_rent', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 아파트 전월세", unit="건"):
        name = parse_str(data.get('aptNm'))
        if not name:
            continue

        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        if '*' in address:
            continue

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, name, PropertyType.APARTMENT)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            # Building이 이미 존재하는 경우
            if check_infrastructure_exists(db, existing_building_id):
                # Building과 Infrastructure 모두 존재 -> 카카오 API 호출 불필요
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", name, address)
            else:
                # Building은 있지만 Infrastructure가 없음 -> 좌표가 있으면 Infrastructure 생성
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # Building이 존재하지 않음 -> 카카오 API 호출 필요
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # 1. Building 생성
            building_id = get_or_create_building(
                db=db,
                address=address,
                name=name,
                building_type=PropertyType.APARTMENT,
                region_code=lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('excluUseAr')),
                max_area=parse_float(data.get('excluUseAr'))
            )

            if not building_id:
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)

        # 3. Transaction 생성
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.RENT,
            exclusive_area=parse_float(data.get('excluUseAr')),
            floor=parse_int(data.get('floor'), 1),
            trans_date=trans_date
        )

        if not transaction_id:
            continue

        # 4. RentTransaction 생성
        create_rent_transaction(
            db=db,
            transaction_id=transaction_id,
            deposit=parse_int(data.get('deposit')),
            monthly_rent=parse_int(data.get('monthlyRent')),
            contract_term=parse_str(data.get('contractTerm')),
            contract_type=parse_str(data.get('contractType')),
            user_rr_right=parse_str(data.get('useRRRight')),
            pre_deposit=parse_int(data.get('preDeposit')) if data.get('preDeposit') else None,
            pre_monthly_rent=parse_int(data.get('preMonthlyRent')) if data.get('preMonthlyRent') else None
        )

        count += 1

    logger.info("아파트 전월세 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return

def collect_office_sale(api, lawd_cd, db: Session):
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'offi_trade', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 오피스텔 매매", unit="건"):
        name = parse_str(data.get('offiNm')) # 오피스텔 이름
        if not name : continue
        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        if '*' in address:
            continue # 마스킹이 있으면 skip 주소가 정확히 어디인지 잘 모름

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, name, PropertyType.OFFICETEL)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            # Building이 이미 존재하는 경우
            if check_infrastructure_exists(db, existing_building_id):
                # Building과 Infrastructure 모두 존재 -> 카카오 API 호출 불필요
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", name, address)
            else:
                # Building은 있지만 Infrastructure가 없음 -> 좌표가 있으면 Infrastructure 생성
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # Building이 존재하지 않음 -> 카카오 API 호출 필요
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # 1. Building 생성
            building_id = get_or_create_building(
                db=db,
                address=address,
                name = name,
                region_code = lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                building_type=PropertyType.OFFICETEL,
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('excluUseAr')),
                max_area=parse_float(data.get('excluUseAr'))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)

        # 3. Transaction 생성
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.SALE,
            exclusive_area=parse_float(data.get('excluUseAr')),
            floor=parse_int(data.get('floor'), 1),
            trans_date=trans_date
        )
        if not transaction_id:
            print(f"SKIP Transaction 생성 실패: {address}")
            continue
        
        # 4. SaleTransaction 생성 
        sale_transaction_id = create_sale_transaction(
            db=db,
            transaction_id=transaction_id,
            deal_amount=parse_int(data.get('dealAmount')),
            cdeal_type=parse_str(data.get('cdealType')),
            cdeal_day=parse_str(data.get('cdealDay')),
            dealing_gbn=parse_str(data.get('dealingGbn')),
            estate_agent_sgg_nm=parse_str(data.get('estateAgentSggNm')),
            saler_gbn=parse_str(data.get('slerGbn')),
            buyer_gbn=parse_str(data.get('buyerGbn'))
        )
        if not sale_transaction_id:
            logger.debug("SaleTransaction 생성 실패로 SKIP: %s", address)
            continue

        count += 1  # 버그 수정: count 증가 추가

    logger.info("오피스텔 매매 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return 

def collect_office_rent(api, lawd_cd, db: Session):
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'offi_rent', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 오피스텔 전월세", unit="건"):
        name = parse_str(data.get('offiNm')) # 오피스텔 이름
        if not name : continue
        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        if '*' in address:
            continue # 마스킹이 있으면 skip 주소가 정확히 어디인지 잘 모름

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, name, PropertyType.OFFICETEL)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            if check_infrastructure_exists(db, existing_building_id):
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", name, address)
            else:
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            building_id = get_or_create_building(
                db=db,
                address=address,
                name = name,
                region_code = lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                building_type=PropertyType.OFFICETEL,
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('excluUseAr')),
                max_area=parse_float(data.get('excluUseAr'))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            create_infrastructure(db, building_id, subway_stations, schools, marts)
        
        # 3. Transaction 생성
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.RENT,
            exclusive_area=parse_float(data.get('excluUseAr')),
            floor=parse_int(data.get('floor'), 1),
            trans_date=trans_date
        )
        if not transaction_id:
            print(f"SKIP Transaction 생성 실패: {address}")
            continue
        
        # 4. RentTrasnaction 생성
        rent_transaction_id = create_rent_transaction(
            db=db,
            transaction_id=transaction_id,
            deposit=parse_int(data.get('deposit')),
            monthly_rent=parse_int(data.get('monthlyRent')),
            contract_term=parse_str(data.get('contractTerm')),
            contract_type=parse_str(data.get('contractType')),
            user_rr_right=parse_str(data.get('useRRRight')),
            pre_deposit=parse_int(data.get('preDeposit')) if data.get('preDeposit') else None,
            pre_monthly_rent=parse_int(data.get('preMonthlyRent')) if data.get('preMonthlyRent') else None
        )
        if not rent_transaction_id:
            print(f"SKIP RentTransaction 생성 실패: {address}")
            continue    
        count +=1 
    logger.info("오피스텔 전월세 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return 


def collect_house_sale(api, lawd_cd, db: Session):
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'sh_trade', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 단독/다가구 매매", unit="건"):
        house_type = data.get('houseType') # 주택유형
        if not house_type: continue
        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))
        if '*' in address:
            address = f"서울특별시 {parse_str(data.get('umdNm'))}" # 마스킹이 있으면 읍면동까지만 표시

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, house_type, PropertyType.HOUSE)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            if check_infrastructure_exists(db, existing_building_id):
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", house_type, address)
            else:
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            building_id = get_or_create_building(
                db=db,
                address=address,
                name = house_type,
                region_code = lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                building_type=PropertyType.HOUSE,
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('totFloorAr', 0.0)),
                max_area=parse_float(data.get('totFloorAr', 0.0))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)
        # 3. Transaction 생성
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.SALE,
            exclusive_area=parse_float(data.get('totalFloorAr', 0.0)),
            floor=parse_int(data.get('floor', 1)),
            trans_date=trans_date
        )
        if not transaction_id:
            print(f"SKIP Transaction 생성 실패: {address}")
            continue

        # 4. SaleTransaction 생성
        sale_transaction_id = create_sale_transaction(
            db=db,
            transaction_id=transaction_id,
            deal_amount=parse_int(data.get('dealAmount')),
            cdeal_type=parse_str(data.get('cdealType')),
            cdeal_day=parse_str(data.get('cdealDay')),
            dealing_gbn=parse_str(data.get('dealingGbn')),
            estate_agent_sgg_nm=parse_str(data.get('estateAgentSggNm')),
            saler_gbn=parse_str(data.get('slerGbn')),
            buyer_gbn=parse_str(data.get('buyerGbn'))
        )
        if not sale_transaction_id:
            print(f"SKIP SaleTransaction 생성 실패: {address}")
            continue
        
        # 5. HouseSaleTransaction 생성
        create_house_sale_transaction(
            db=db,
            sale_transaction_id=sale_transaction_id,
            total_floor_area=parse_float(data.get('totalFloorAr', 0.0)),
            plottage_area=parse_float(data.get('plottageAr', 0.0))
        )
        if not sale_transaction_id:
            print(f"SKIP HouseSaleTransaction 생성 실패: {address}")
            continue
    
        count +=1 
    logger.info("단독/다가구 매매 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return

# ==================== 미완성 함수들 ====================
def collect_house_rent(api, lawd_cd, db: Session):
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'sh_rent', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 단독/다가구 전월세", unit="건"):
        house_type = data.get('houseType') # 주택유형
        if not house_type: continue
        address = f"서울특별시 {parse_str(data.get('umdNm'))}" # 지번이 없어서 읍면동으로만 표시
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, house_type, PropertyType.HOUSE)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            if check_infrastructure_exists(db, existing_building_id):
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", house_type, address)
            else:
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            building_id = get_or_create_building(
                db=db,
                address=address,
                name = house_type,
                region_code = lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                building_type=PropertyType.HOUSE,
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('totalFloorAr', 0.0)),
                max_area=parse_float(data.get('totalFloorAr', 0.0))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)
        # 3. Transaction 생성
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.RENT,
            exclusive_area=parse_float(data.get('totalFloorAr', 0.0)),
            floor=parse_int(data.get('floor', 1)),
            trans_date=trans_date
        )
        if not transaction_id:
            print(f"SKIP Transaction 생성 실패: {address}")
            continue
        # 4. RentTransaction 생성
        rent_transaction_id = create_rent_transaction(
            db=db,
            transaction_id=transaction_id,
            deposit=parse_int(data.get('deposit')),
            monthly_rent=parse_int(data.get('monthlyRent')),
            contract_term=parse_str(data.get('contractTerm')),
            contract_type=parse_str(data.get('contractType')),
            user_rr_right=parse_str(data.get('useRRRight')),
            pre_deposit=parse_int(data.get('preDeposit')) if data.get('preDeposit') else None, 
            pre_monthly_rent=parse_int(data.get('preMonthlyRent')) if data.get('preMonthlyRent') else None
        )
        if not rent_transaction_id:
            print(f"SKIP RentTransaction 생성 실패: {address}")
            continue
        count +=1
    logger.info("단독/다가구 전월세 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return

def collect_villa_sale(api, lawd_cd, db: Session):
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'rh_trade', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 연립/다세대 매매", unit="건"):
        name = parse_str(data.get('mhouseNm')) or "연립다세대" # 빌라 이름 (없으면 기본값)
        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, name, PropertyType.VILLA)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            if check_infrastructure_exists(db, existing_building_id):
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", name, address)
            else:
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            building_id = get_or_create_building(
                db=db,
                address=address,
                name = name,
                region_code = lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                building_type=PropertyType.VILLA,
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('totFloorAr', 0.0)),
                max_area=parse_float(data.get('totFloorAr', 0.0))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)
        # 3. Transaction 생성
        
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.SALE,
            exclusive_area=parse_float(data.get('totFloorAr', 0.0)),
            floor=parse_int(data.get('floor', 1)),
            trans_date=trans_date
        )
    
        if not transaction_id:
            print(f"SKIP Transaction 생성 실패: {address}")
            continue
            
        # 4. SaleTransaction 생성
        sale_transaction_id = create_sale_transaction(
            db=db,
            transaction_id=transaction_id,
            deal_amount=parse_int(data.get('dealAmount')),
            cdeal_type=parse_str(data.get('cdealType')),
            cdeal_day=parse_str(data.get('cdealDay')),
            dealing_gbn=parse_str(data.get('dealingGbn')),
            estate_agent_sgg_nm=parse_str(data.get('estateAgentSggNm')),
            saler_gbn=parse_str(data.get('slerGbn')),
            buyer_gbn=parse_str(data.get('buyerGbn'))
        )
        if not sale_transaction_id:
            print(f"SKIP SaleTransaction 생성 실패: {address}")
            continue
        # 5. VillaSaleTransaction 생성
        create_villa_sale_transaction(
            db=db,
            sale_transaction_id=sale_transaction_id,
            land_area=parse_float(data.get('landArea', 0.0))
        )
        if not sale_transaction_id:
            print(f"SKIP VillaSaleTransaction 생성 실패: {address}")
            continue
        count +=1
    logger.info("연립/다세대 매매 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return


def collect_villa_rent(api, lawd_cd, db: Session):
    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'rh_rent', '1000', True)
    count = 0
    skipped_count = 0  # 스킵된 건수 추적

    for data in tqdm(data_list, desc=f"[{REGIONS.get(lawd_cd)}] 연립/다세대 전월세", unit="건"):
        name = parse_str(data.get('mhouseNm')) or "연립다세대" # 빌라 이름 (없으면 기본값)
        address = f"{parse_str(data.get('umdNm'))} {parse_str(data.get('jibun'))}"
        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        # ===== 최적화: Building 존재 여부 먼저 확인 =====
        existing_building_id = check_building_exists(db, address, name, PropertyType.VILLA)

        lat, lng, dong = None, None, None
        subway_stations, schools, marts = None, None, None

        if existing_building_id:
            if check_infrastructure_exists(db, existing_building_id):
                building_id = existing_building_id
                skipped_count += 1
                logger.debug("이미 등록된 건물 (카카오 API 스킵): %s - %s", name, address)
            else:
                building = db.query(Building).filter(Building.id == existing_building_id).first()
                if building:
                    lat_value: Optional[float] = building.latitude  # type: ignore
                    lng_value: Optional[float] = building.longitude  # type: ignore
                    if lat_value is not None and lng_value is not None:
                        subway_stations, schools, marts = get_all_nearby_facilities(lat_value, lng_value)
                        create_infrastructure(db, existing_building_id, subway_stations, schools, marts)
                building_id = existing_building_id
        else:
            # 카카오 API 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            if not lat or not lng:
                logger.debug("좌표를 찾을 수 없어 SKIP: %s", address)
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            building_id = get_or_create_building(
                db=db,
                address=address,
                name = name,
                region_code = lawd_cd,
                legal_dong=dong if dong else parse_str(data.get('umdNm'), ''),
                building_type=PropertyType.VILLA,
                lat=lat,
                lng=lng,
                build_year=parse_str(data.get('buildYear')),
                min_area=parse_float(data.get('totFloorAr', 0.0)),
                max_area=parse_float(data.get('totFloorAr', 0.0))
            )

            if not building_id:
                logger.debug("Building 생성 실패로 SKIP: %s", address)
                continue

            # 2. Infrastructure 생성
            create_infrastructure(db, building_id, subway_stations, schools, marts)
        # 3. Transaction 생성
        transaction_id = create_transaction(
            db=db,
            building_id=building_id,
            transaction_type=TransactionType.RENT,
            exclusive_area=parse_float(data.get('totFloorAr', 0.0)),
            floor=parse_int(data.get('floor', 1)),
            trans_date=trans_date
        )

        if not transaction_id:
            print(f"SKIP Transaction 생성 실패: {address}")
            continue

        # 4. RentTrasnaction 생성
        rent_transaction_id = create_rent_transaction(
            db=db,
            transaction_id=transaction_id,
            deposit=parse_int(data.get('deposit')),
            monthly_rent=parse_int(data.get('monthlyRent')),
            contract_term=parse_str(data.get('contractTerm')),
            contract_type=parse_str(data.get('contractType')),
            user_rr_right=parse_str(data.get('useRRRight')),
            pre_deposit=parse_int(data.get('preDeposit')) if data.get('preDeposit') else None,
            pre_monthly_rent=parse_int(data.get('preMonthlyRent')) if data.get('preMonthlyRent') else None
        )
        
        if not rent_transaction_id:
            print(f"SKIP RentTransaction 생성 실패: {address}")
            continue
        count +=1

    logger.info("연립/다세대 전월세 %d건 저장 완료 (카카오 API 스킵: %d건)", count, skipped_count)
    return 


if __name__ == '__main__':
    # DB 세션 생성
    db = SessionLocal()

    try:
        logger.info("=" * 80)
        logger.info("부동산 실거래가 데이터 수집 시작 (PostgreSQL)")
        logger.info("=" * 80)

        # ----------------------------------------------------------------------
        # 0. Region 데이터 초기화 (캐싱) - 성능 최적화의 핵심!
        # ----------------------------------------------------------------------
        initialize_regions(db)

        # ----------------------------------------------------------------------
        # 1. 데이터 수집 및 저장 (for 루프를 돌며 모든 지역 데이터 수집)
        # ----------------------------------------------------------------------
        for lawd_cd, region_name in tqdm(REGIONS.items()):
            logger.info("=" * 80)
            logger.info("[%s(%s)] 데이터 수집 시작", region_name, lawd_cd)
            logger.info("=" * 80)

            # # 아파트 매매 거래
            collect_apt_sale(transaction_api, lawd_cd, db)
            # # 아파트 전월세 거래
            collect_apt_rent(transaction_api, lawd_cd, db)
            # # 오피스텔 매매 거래
            collect_office_sale(transaction_api, lawd_cd, db)
            # # 오피스텔 전월세 거래
            collect_office_rent(transaction_api, lawd_cd, db)
            # # 빌라 매매 거래
            collect_villa_sale(transaction_api, lawd_cd, db)
            # 빌라 전월세 거래
            collect_villa_rent(transaction_api, lawd_cd, db)
            # 단독/다가구 매매 거래
            collect_house_sale(transaction_api, lawd_cd, db)
            # 단독/다가구 전월세 거래(미완성 함수)
            collect_house_rent(transaction_api, lawd_cd, db)

            logger.info("[%s(%s)] 데이터 수집 완료", region_name, lawd_cd)

        logger.info("=" * 80)
        logger.info("모든 데이터 수집 및 저장 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("데이터 수집 중 오류 발생: %s", str(e), exc_info=True)
        db.rollback()

    finally:
        db.close()
        logger.info("DB 세션 종료")