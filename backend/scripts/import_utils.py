"""
부동산 데이터 import 공통 유틸리티 함수
"""
import pandas as pd
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.real_estate import Region


def get_or_create_region(db: Session, region_code: str, region_name: str) -> Region:
    """
    지역 코드로 Region을 조회하거나 생성

    Args:
        db: 데이터베이스 세션
        region_code: 법정동코드 또는 cortarNo
        region_name: 지역명 (구 동)

    Returns:
        Region 객체
    """
    region = db.query(Region).filter(Region.code == region_code).first()
    if not region:
        region = Region(code=region_code, name=region_name)
        db.add(region)
        db.flush()
    return region


def parse_region_from_name(db: Session, gu: str, dong: str) -> Region:
    """
    구와 동 이름으로 지역 정보를 조회하거나 생성

    성능을 위해 간단하게 "구-동" 형식의 코드를 사용합니다.

    Args:
        db: 데이터베이스 세션
        gu: 구 이름 (예: "강남구")
        dong: 동 이름 (예: "대치동")

    Returns:
        Region 객체
    """
    region_code = f"{gu}-{dong}"
    region_name = f"{gu} {dong}"

    return get_or_create_region(db, region_code, region_name)


def safe_int(value, default=None) -> int | None:
    """안전하게 int로 변환"""
    if pd.isna(value):
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=None) -> float | None:
    """안전하게 float로 변환"""
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal(value, default=None) -> Decimal | None:
    """안전하게 Decimal로 변환 (좌표용)"""
    if pd.isna(value):
        return default
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return default


def safe_str(value, default=None) -> str | None:
    """안전하게 str로 변환"""
    if pd.isna(value) or value == '':
        return default
    return str(value).strip()


def parse_completion_date(value) -> str | None:
    """준공년월을 YYYYMM 형식으로 변환"""
    if pd.isna(value):
        return None
    date_str = str(value).strip()
    # YYYYMM 형식 검증
    if len(date_str) == 6 and date_str.isdigit():
        return date_str
    return None


def parse_tag_list(value) -> list[str] | None:
    """태그 리스트 파싱 (문자열 -> 리스트)"""
    if pd.isna(value) or value == '':
        return None

    # 이미 리스트인 경우
    if isinstance(value, list):
        return value

    # 문자열인 경우: "['tag1', 'tag2']" 형식 파싱
    try:
        import ast
        result = ast.literal_eval(value)
        if isinstance(result, list):
            return result
    except:
        pass

    # 쉼표로 구분된 문자열
    if ',' in str(value):
        return [tag.strip() for tag in str(value).split(',')]

    return [str(value).strip()]


def clean_school_list(value) -> str | None:
    """학교 목록 정리 (따옴표 제거)"""
    if pd.isna(value) or value == '':
        return None
    return str(value).replace('"', '').strip()
