"""
부동산 실거래가 데이터 수집 스크립트 (분리된 모델 기반)
2024년 1월 ~ 2025년 11월
서초구, 강남구, 송파구
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import requests
import json

from app.db.postgre_db import SessionLocal
from app.utils.building_api import TransactionPriceAPI
from app.models.apartment import Apartment, ApartmentSaleTransaction, ApartmentRentTransaction
from app.models.house import House, HouseSaleTransaction, HouseRentTransaction
from app.models.villa import Villa, VillaSaleTransaction, VillaRentTransaction
from app.models.officetel import Officetel, OfficetelSaleTransaction, OfficetelRentTransaction
from app.models.real_estate import Region
from app.models.building import Building
from app.models.enums import PropertyType

load_dotenv()

# 카카오 API 키
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

# 위경도 캐시 (같은 주소는 재호출하지 않음)
COORDINATE_CACHE: Dict[str, Tuple[Optional[float], Optional[float]]] = {}

REGIONS = {'11650': '서초구', '11680': '강남구', '11710': '송파구'} # 지역 시군구코드 
START_YM = '202401' # 시작년도
END_YM = '202511'   # 종료년도

def safe_int(val, default=0):
    if not val: return default
    try:
        return int(str(val).replace(',', '').strip())
    except:
        return default

def safe_float(val, default=None):
    if not val: return default
    try:
        return float(val)
    except:
        return default

def safe_str(val, default=None):
    if not val or val == '': return default
    return str(val).strip()

def parse_date(year, month, day):
    try:
        y = str(year).strip() if year else '2024'
        m = str(month).strip().zfill(2) if month else '01'
        d = str(day).strip().zfill(2) if day else '01'
        return datetime.strptime(f"{y}{m}{d}", "%Y%m%d")
    except:
        return datetime.now()

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
        # 기존 캐시가 2-tuple이면 3-tuple로 변환
        if len(cached) == 2:
            return (cached[0], cached[1], None)
        return cached

    if not KAKAO_REST_API_KEY:
        print("KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        return (None, None, None)

    try:
        # 지역명 추가
        full_address = address
        if region_code and region_code in REGIONS:
            full_address = f"서울특별시 {REGIONS[region_code]} {address}"

        # 카카오 로컬 API - 주소 검색
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        params = {"query": full_address}

        response = requests.get(url, headers=headers, params=params, timeout=5)
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
                print(f"Success 좌표 및 동 추출: {address} -> ({lat}, {lng}, {dong})")

            return (lat, lng, dong)
        else:
            print(f"Warining 좌표를 찾을 수 없음: {full_address}")
            COORDINATE_CACHE[address] = (None, None, None)
            return (None, None, None)

    except requests.RequestException as e:
        print(f"Error 카카오 API 호출 실패: {e}")
        return (None, None, None)
    except Exception as e:
        print(f"Error 좌표 추출 오류: {e}")
        return (None, None, None)


def get_nearby_facilities(lat: float, lng: float, category_code: str, radius: int = 1000) -> Optional[str]:
    """
    카카오 API를 사용하여 주변 시설 정보를 가져옴

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

    try:
        url = "https://dapi.kakao.com/v2/local/search/category.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        params = {
            "category_group_code": category_code,
            "x": lng,  # 경도
            "y": lat,  # 위도
            "radius": radius,
            "sort": "distance"
        }

        response = requests.get(url, headers=headers, params=params, timeout=5)
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
        print(f"Error 카카오 API 호출 실패 ({category_code}): {e}")
        return None
    except Exception as e:
        print(f"Error 시설 정보 추출 오류 ({category_code}): {e}")
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
    subway_stations = get_nearby_facilities(lat, lng, "SW8", 1000)
    time.sleep(0.1)

    # 인근 학교 (초중고)
    schools = get_nearby_facilities(lat, lng, "SC4", 1000)
    time.sleep(0.1)

    # 인근 마트
    marts = get_nearby_facilities(lat, lng, "MT1", 1000)
    time.sleep(0.1)

    return (subway_stations, schools, marts)


def get_or_create_region(db, code, name): # 시군구 지역명 테이블 생성 
    region = db.query(Region).filter(Region.code == code).first()
    if not region:
        region = Region(code=code, name=name)
        db.add(region)
        db.flush()
    return region

def collect_apt_sale(db, api, lawd_cd, region): # 아파트 매매 수집 
    print(f"\n[아파트 매매] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(ApartmentSaleTransaction).filter(
        ApartmentSaleTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 아파트 매매 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'apt_trade', '1000', True)
    count = 0

    for data in data_list:
        name = safe_str(data.get('aptNm'))
        if not name: continue

        code = f"{data.get('sggCd')}_{name}_{data.get('jibun')}" # 코드명 다르게 설정해야하는거아님 ?
        apt = db.query(Apartment).filter(Apartment.complex_code == code).first()

        if not apt:
            address = f"{safe_str(data.get('umdNm'))} {safe_str(data.get('jibun'))}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.APARTMENT,
                name=name,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=safe_str(data.get('umdNm')),
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # Apartment 객체 생성 (중복 필드는 Building에만 저장)
            apt = Apartment(
                complex_code=code,
                name=name,
                region_id=region.id,
                building_id=building.id
            )
            db.add(apt)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(ApartmentSaleTransaction).filter(
            ApartmentSaleTransaction.apartment_id == apt.id,
            ApartmentSaleTransaction.transaction_date == trans_date,
            ApartmentSaleTransaction.floor == safe_str(data.get('floor'))
        ).first()

        if exists: continue

        trans = ApartmentSaleTransaction(
            apartment_id=apt.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deal_amount=safe_int(data.get('dealAmount')),
            exclusive_area=safe_float(data.get('excluUseAr')),
            floor=safe_str(data.get('floor')),
            dong=safe_str(data.get('umdNm'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"Complete 아파트 매매 {count}건 저장")
    return count

def collect_apt_rent(db, api, lawd_cd, region):
    print(f"\n[아파트 전월세] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(ApartmentRentTransaction).filter(
        ApartmentRentTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 아파트 전월세 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'apt_rent', '1000', True)
    count = 0

    for data in data_list:
        name = safe_str(data.get('aptNm'))
        if not name: continue

        code = f"{data.get('sggCd')}_{name}_{data.get('jibun')}"
        apt = db.query(Apartment).filter(Apartment.complex_code == code).first()

        if not apt:
            address = f"{safe_str(data.get('umdNm'))} {safe_str(data.get('jibun'))}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.APARTMENT,
                name=name,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=safe_str(data.get('umdNm')),
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # Apartment 객체 생성 (중복 필드는 Building에만 저장)
            apt = Apartment(
                complex_code=code,
                name=name,
                region_id=region.id,
                building_id=building.id
            )
            db.add(apt)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(ApartmentRentTransaction).filter(
            ApartmentRentTransaction.apartment_id == apt.id,
            ApartmentRentTransaction.transaction_date == trans_date,
            ApartmentRentTransaction.floor == safe_str(data.get('floor'))
        ).first()

        if exists: continue

        trans = ApartmentRentTransaction(
            apartment_id=apt.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deposit=safe_int(data.get('deposit')),
            monthly_rent=safe_int(data.get('monthlyRent')),
            exclusive_area=safe_float(data.get('excluUseAr')),
            floor=safe_str(data.get('floor'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"Complete 아파트 전월세 {count}건 저장")
    return count

def collect_offi_sale(db, api, lawd_cd, region):
    print(f"\n[오피스텔 매매] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(OfficetelSaleTransaction).filter(
        OfficetelSaleTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 오피스텔 매매 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'offi_trade', '1000', True)
    count = 0

    for data in data_list:
        name = safe_str(data.get('offiNm'))
        if not name: continue

        code = f"{data.get('sggCd')}_{name}_{data.get('jibun')}"
        offi = db.query(Officetel).filter(Officetel.complex_code == code).first()

        if not offi:
            address = f"{safe_str(data.get('umdNm'))} {safe_str(data.get('jibun'))}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.OFFICETEL,
                name=name,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=safe_str(data.get('umdNm')),
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # Officetel 객체 생성 (중복 필드는 Building에만 저장)
            offi = Officetel(
                complex_code=code,
                name=name,
                region_id=region.id,
                sgg_name=safe_str(data.get('sggNm')),
                building_id=building.id
            )
            db.add(offi)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(OfficetelSaleTransaction).filter(
            OfficetelSaleTransaction.officetel_id == offi.id,
            OfficetelSaleTransaction.transaction_date == trans_date,
            OfficetelSaleTransaction.floor == safe_str(data.get('floor'))
        ).first()

        if exists: continue

        trans = OfficetelSaleTransaction(
            officetel_id=offi.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deal_amount=safe_int(data.get('dealAmount')),
            exclusive_area=safe_float(data.get('excluUseAr')),
            floor=safe_str(data.get('floor'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"Complete 오피스텔 매매 {count}건 저장")
    return count

def collect_offi_rent(db, api, lawd_cd, region):
    print(f"\n[오피스텔 전월세] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(OfficetelRentTransaction).filter(
        OfficetelRentTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 오피스텔 전월세 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'offi_rent', '1000', True)
    count = 0

    for data in data_list:
        name = safe_str(data.get('offiNm'))
        if not name: continue

        code = f"{data.get('sggCd')}_{name}_{data.get('jibun')}"
        offi = db.query(Officetel).filter(Officetel.complex_code == code).first()

        if not offi:
            address = f"{safe_str(data.get('umdNm'))} {safe_str(data.get('jibun'))}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.OFFICETEL,
                name=name,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=safe_str(data.get('umdNm')),
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # Officetel 객체 생성 (중복 필드는 Building에만 저장)
            offi = Officetel(
                complex_code=code,
                name=name,
                region_id=region.id,
                sgg_name=safe_str(data.get('sggNm')),
                building_id=building.id
            )
            db.add(offi)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(OfficetelRentTransaction).filter(
            OfficetelRentTransaction.officetel_id == offi.id,
            OfficetelRentTransaction.transaction_date == trans_date,
            OfficetelRentTransaction.floor == safe_str(data.get('floor'))
        ).first()

        if exists: continue

        trans = OfficetelRentTransaction(
            officetel_id=offi.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deposit=safe_int(data.get('deposit')),
            monthly_rent=safe_int(data.get('monthlyRent')),
            exclusive_area=safe_float(data.get('excluUseAr')),
            floor=safe_str(data.get('floor'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"Complete 오피스텔 전월세 {count}건 저장")
    return count

def collect_house_sale(db, api, lawd_cd, region):
    print(f"\n[단독/다가구 매매] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(HouseSaleTransaction).filter(
        HouseSaleTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 단독/다가구 매매 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'sh_trade', '1000', True)
    count = 0
    total = len(data_list)
    print(f"총 {total}건의 데이터 처리 중...")

    for idx, data in enumerate(data_list, 1):
        # 진행 상황 표시 (10건마다)
        if idx % 10 == 0 or idx == 1:
            print(f"진행: {idx}/{total} ({idx*100//total}%)")

        house_type = safe_str(data.get('houseType'))
        if not house_type: continue

        jibun = safe_str(data.get('jibun'))
        umd_nm = safe_str(data.get('umdNm'))
        code = f"{data.get('sggCd')}_{house_type}_{jibun}"
        house = db.query(House).filter(House.property_code == code).first()

        if not house:
            address = f"{umd_nm} {jibun}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.HOUSE,
                name=house_type,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=umd_nm,
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # House 객체 생성 (중복 필드는 Building에만 저장)
            house = House(
                property_code=code,
                name=house_type,
                house_type=house_type,
                region_id=region.id,
                building_id=building.id
            )
            db.add(house)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(HouseSaleTransaction).filter(
            HouseSaleTransaction.house_id == house.id,
            HouseSaleTransaction.transaction_date == trans_date
        ).first()

        if exists: continue

        trans = HouseSaleTransaction(
            house_id=house.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deal_amount=safe_int(data.get('dealAmount')),
            total_floor_area=safe_float(data.get('totFlrAr')),
            plottage_area=safe_float(data.get('platArea'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"Complete 단독/다가구 매매 {count}건 저장")
    return count

def collect_house_rent(db, api, lawd_cd, region):
    print(f"\n[단독/다가구 전월세] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(HouseRentTransaction).filter(
        HouseRentTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 단독/다가구 전월세 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'sh_rent', '1000', True)
    count = 0
    total = len(data_list)
    print(f"총 {total}건의 데이터 처리 중...")

    for idx, data in enumerate(data_list, 1):
        # 진행 상황 표시 (10건마다)
        if idx % 10 == 0 or idx == 1:
            print(f"진행: {idx}/{total} ({idx*100//total}%)")

        house_type = safe_str(data.get('houseType'))
        if not house_type: continue

        jibun = safe_str(data.get('jibun'))
        umd_nm = safe_str(data.get('umdNm'))
        code = f"{data.get('sggCd')}_{house_type}_{jibun}"
        house = db.query(House).filter(House.property_code == code).first()

        if not house:
            address = f"{umd_nm} {jibun}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"  SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"  SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.HOUSE,
                name=house_type,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=umd_nm,
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # House 객체 생성 (중복 필드는 Building에만 저장)
            house = House(
                property_code=code,
                name=house_type,
                house_type=house_type,
                region_id=region.id,
                building_id=building.id
            )
            db.add(house)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(HouseRentTransaction).filter(
            HouseRentTransaction.house_id == house.id,
            HouseRentTransaction.transaction_date == trans_date
        ).first()

        if exists: continue

        trans = HouseRentTransaction(
            house_id=house.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deposit=safe_int(data.get('deposit')),
            monthly_rent=safe_int(data.get('monthlyRent')),
            total_floor_area=safe_float(data.get('totFlrAr'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"[완료] 단독/다가구 전월세 {count}건 저장")
    return count

def collect_villa_sale(db, api, lawd_cd, region):
    print(f"\n[연립/다세대 매매] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(VillaSaleTransaction).filter(
        VillaSaleTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 연립/다세대 매매 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'rh_trade', '1000', True)
    count = 0
    total = len(data_list)

    # 디버그: 첫 번째 데이터의 모든 필드 출력
    if data_list:
        print(f"\n Debug 첫 번째 데이터 샘플:")
        print(f"  사용 가능한 필드: {list(data_list[0].keys())}")
        print(f"  mhouseNm 값: '{data_list[0].get('mhouseNm')}'")

    print(f"  총 {total}건의 데이터 처리 중...")

    for idx, data in enumerate(data_list, 1):
        # 진행 상황 표시 (10건마다)
        if idx % 10 == 0 or idx == 1:
            print(f"진행: {idx}/{total} ({idx*100//total}%)")
        name = safe_str(data.get('mhouseNm'))
        if not name:
            # 디버그: 왜 스킵되는지 확인
            print(f"skip mhouseNm이 비어있음: {data.get('umdNm')} {data.get('jibun')}")
            continue

        jibun = safe_str(data.get('jibun'))
        umd_nm = safe_str(data.get('umdNm'))
        code = f"{data.get('sggCd')}_{name}_{jibun}"
        villa = db.query(Villa).filter(Villa.property_code == code).first()

        if not villa:
            address = f"{umd_nm} {jibun}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"[skip]]마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"[skip] 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.VILLA,
                name=name,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=umd_nm,
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # Villa 객체 생성 (중복 필드는 Building에만 저장)
            villa = Villa(
                property_code=code,
                name=name,
                region_id=region.id,
                building_id=building.id
            )
            db.add(villa)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(VillaSaleTransaction).filter(
            VillaSaleTransaction.villa_id == villa.id,
            VillaSaleTransaction.transaction_date == trans_date,
            VillaSaleTransaction.floor == safe_str(data.get('floor'))
        ).first()

        if exists: continue

        trans = VillaSaleTransaction(
            villa_id=villa.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deal_amount=safe_int(data.get('dealAmount')),
            exclusive_area=safe_float(data.get('excluUseAr')),
            land_area=safe_float(data.get('landAr')),
            floor=safe_str(data.get('floor'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"[완료] 연립/다세대 매매 {count}건 저장")
    return count

def collect_villa_rent(db, api, lawd_cd, region):
    print(f"\n[연립/다세대 전월세] {REGIONS[lawd_cd]} 수집 중...")

    # 이미 데이터가 있는지 확인
    existing_count = db.query(VillaRentTransaction).filter(
        VillaRentTransaction.region_id == region.id
    ).count()

    if existing_count > 0:
        print(f"SKIP 연립/다세대 전월세 데이터가 이미 존재합니다 ({existing_count}건). 수집을 건너뜁니다.")
        return 0

    data_list = api.get_batch_data(lawd_cd, START_YM, END_YM, 'rh_rent', '1000', True)
    count = 0
    total = len(data_list)

    # 디버그: 첫 번째 데이터의 모든 필드 출력
    if data_list:
        print(f"\n Debug 첫 번째 데이터 샘플:")
        print(f"  사용 가능한 필드: {list(data_list[0].keys())}")
        print(f"  mhouseNm 값: '{data_list[0].get('mhouseNm')}'")

    print(f"  총 {total}건의 데이터 처리 중...")

    for idx, data in enumerate(data_list, 1):
        # 진행 상황 표시 (10건마다)
        if idx % 10 == 0 or idx == 1:
            print(f"    진행: {idx}/{total} ({idx*100//total}%)")
        name = safe_str(data.get('mhouseNm'))
        if not name:
            # 디버그: 왜 스킵되는지 확인
            print(f"  SKIP mhouseNm이 비어있음: {data.get('umdNm')} {data.get('jibun')}")
            continue

        jibun = safe_str(data.get('jibun'))
        umd_nm = safe_str(data.get('umdNm'))
        code = f"{data.get('sggCd')}_{name}_{jibun}"
        villa = db.query(Villa).filter(Villa.property_code == code).first()

        if not villa:
            address = f"{umd_nm} {jibun}"

            # 주소에 마스킹 문자가 있으면 스킵
            if '*' in address:
                print(f"  SKIP 마스킹된 주소: {address}")
                continue

            # 카카오 API로 위경도 좌표 추출
            lat, lng, dong = get_coordinates_from_kakao(address, lawd_cd)

            # 좌표를 찾을 수 없으면 스킵
            if not lat or not lng:
                print(f"  SKIP 좌표를 찾을 수 없음: {address}")
                continue

            # 주변 시설 정보 가져오기
            subway_stations, schools, marts = get_all_nearby_facilities(lat, lng)

            # Building 객체 생성 및 저장
            building = Building(
                building_type=PropertyType.VILLA,
                name=name,
                build_year=safe_str(data.get('buildYear')),
                region_id=region.id,
                region_name=umd_nm,
                address=address,
                latitude=lat,
                longitude=lng,
                nearby_subway_stations=subway_stations,
                nearby_schools=schools,
                nearby_marts=marts
            )
            db.add(building)
            db.flush()

            # Villa 객체 생성 (중복 필드는 Building에만 저장)
            villa = Villa(
                property_code=code,
                name=name,
                region_id=region.id,
                building_id=building.id
            )
            db.add(villa)
            db.flush()

            # API 호출 제한 방지를 위한 짧은 대기
            if lat and lng:
                time.sleep(0.1)

        trans_date = parse_date(data.get('dealYear'), data.get('dealMonth'), data.get('dealDay'))

        exists = db.query(VillaRentTransaction).filter(
            VillaRentTransaction.villa_id == villa.id,
            VillaRentTransaction.transaction_date == trans_date,
            VillaRentTransaction.floor == safe_str(data.get('floor'))
        ).first()

        if exists: continue

        trans = VillaRentTransaction(
            villa_id=villa.id, region_id=region.id,
            deal_year=safe_str(data.get('dealYear')),
            deal_month=safe_str(data.get('dealMonth')),
            deal_day=safe_str(data.get('dealDay')),
            transaction_date=trans_date,
            deposit=safe_int(data.get('deposit')),
            monthly_rent=safe_int(data.get('monthlyRent')),
            exclusive_area=safe_float(data.get('excluUseAr')),
            floor=safe_str(data.get('floor'))
        )
        db.add(trans)
        count += 1

    db.commit()
    print(f"[완료] 연립/다세대 전월세 {count}건 저장")
    return count

def main():
    print("="*80)
    print("부동산 실거래가 데이터 수집 시작")
    print(f"기간: {START_YM} ~ {END_YM}")
    print(f"지역: {', '.join(REGIONS.values())}")
    print("="*80)

    db = SessionLocal()
    api = TransactionPriceAPI()
    stats = {}

    try:
        for lawd_cd, region_name in REGIONS.items():
            print(f"\n{'='*80}")
            print(f"[{region_name}] 데이터 수집 중...")
            print(f"{'='*80}")

            region = get_or_create_region(db, lawd_cd, region_name)

            try:
                stats[f'{region_name}_apt_sale'] = collect_apt_sale(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_apt_rent'] = collect_apt_rent(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_offi_sale'] = collect_offi_sale(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_offi_rent'] = collect_offi_rent(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_house_sale'] = collect_house_sale(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_house_rent'] = collect_house_rent(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_villa_sale'] = collect_villa_sale(db, api, lawd_cd, region)
                time.sleep(1)
                stats[f'{region_name}_villa_rent'] = collect_villa_rent(db, api, lawd_cd, region)
                time.sleep(1)
            except Exception as e:
                print(f"[오류] {region_name} 수집 중 오류: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "="*80)
        print("데이터 수집 완료!")
        print("="*80)
        print("\n[수집 통계]")
        for key, value in stats.items():
            print(f"  {key}: {value:,}건")
        print(f"\n  총합: {sum(stats.values()):,}건")
        print("="*80)
    finally:
        db.close()

if __name__ == "__main__":
    main()
