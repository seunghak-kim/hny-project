"""부동산 관련 Enum 타입 정의"""
import enum


class PropertyType(enum.Enum):
    """부동산 종류"""
    APARTMENT = "apartment"  # 아파트
    OFFICETEL = "officetel"  # 오피스텔
    HOUSE = "house"  # 단독/다가구
    VILLA = "villa"  # 연립/다세대


class TransactionType(enum.Enum):
    """거래 유형"""
    SALE = "sale"  # 매매
    RENT = "rent"  # 전/월세


class ContractType(enum.Enum):
    """계약 구분"""
    NEW = "new"  # 신규
    RENEWAL = "renewal"  # 갱신


class DealType(enum.Enum):
    """거래 타입"""
    BROKERAGE = "brokerage"  # 중개거래
    DIRECT = "direct"  # 직거래


class UseRRRight(enum.Enum):
    """갱신요구권 사용 여부"""
    USED = "used"  # 사용
    NOT_USED = "not_used"  # 미사용


class HouseType(enum.Enum):
    """단독/다가구 주택 유형"""
    DETACHED = "detached"  # 단독
    MULTI_FAMILY = "multi_family"  # 다가구
