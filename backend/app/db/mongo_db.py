from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional, Dict, List, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    _instance: Optional['MongoDB'] = None
    _client: Optional[MongoClient] = None
    _databases: Dict[str, Database] = {}

    # 은행 컬렉션 매핑
    BANK_COLLECTIONS = {
        'k': 'k',
        'kb': 'kb',
        'hana': 'hana',
        'sinhan': 'sinhan',
        'shinhan': 'sinhan',  # alias
        'woori': 'woori',
        'kakao': 'kakao',
        'sc': 'sc'
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self.connect()

    def connect(self, mongodb_url: Optional[str] = None):
        """MongoDB 연결

        Args:
            mongodb_url: MongoDB 연결 URL (None이면 설정에서 가져옴)
        """
        try:
            url = mongodb_url or settings.MONGODB_URL or "mongodb://localhost:27017/"
            self._client = MongoClient(url)
            # 연결 테스트
            self._client.admin.command('ping')
            logger.info("MongoDB 연결 성공")
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {e}")
            raise

    def get_database(self, db_name: str) -> Database:
        """데이터베이스 가져오기 (캐싱)

        Args:
            db_name: 데이터베이스 이름

        Returns:
            Database 객체
        """
        if self._client is None:
            raise RuntimeError("MongoDB가 연결되지 않았습니다")

        if db_name not in self._databases:
            self._databases[db_name] = self._client[db_name]
            logger.debug(f"데이터베이스 캐시 추가: {db_name}")

        return self._databases[db_name]

    def get_collection(self, db_name: str, collection_name: str) -> Collection:
        """컬렉션 가져오기

        Args:
            db_name: 데이터베이스 이름
            collection_name: 컬렉션 이름

        Returns:
            Collection 객체
        """
        db = self.get_database(db_name)
        return db[collection_name]

    @property
    def bank_db(self) -> Database:
        """은행 데이터베이스 (하위 호환성)"""
        return self.get_database("bank")

    # 컬렉션 접근 메서드들 (하위 호환성)
    @property
    def k_collection(self) -> Collection:
        return self.get_collection("bank", "k")

    @property
    def kb_collection(self) -> Collection:
        return self.get_collection("bank", "kb")

    @property
    def hana_collection(self) -> Collection:
        return self.get_collection("bank", "hana")

    @property
    def sh_collection(self) -> Collection:
        return self.get_collection("bank", "sinhan")

    @property
    def woori_collection(self) -> Collection:
        return self.get_collection("bank", "woori")

    @property
    def kakao_collection(self) -> Collection:
        return self.get_collection("bank", "kakao")

    @property
    def sc_collection(self) -> Collection:
        return self.get_collection("bank", "sc")

    def get_bank_collection(self, bank_name: str) -> Collection:
        """은행 이름으로 컬렉션 가져오기

        Args:
            bank_name: 은행 이름 (k, kb, hana, sinhan, woori, kakao, sc)

        Returns:
            Collection 객체

        Raises:
            ValueError: 지원하지 않는 은행 이름
        """
        bank_key = bank_name.lower()
        if bank_key not in self.BANK_COLLECTIONS:
            raise ValueError(
                f"지원하지 않는 은행: {bank_name}\n"
                f"사용 가능한 은행: {', '.join(self.BANK_COLLECTIONS.keys())}"
            )

        collection_name = self.BANK_COLLECTIONS[bank_key]
        return self.get_collection("bank", collection_name)

    def list_collections(self, db_name: str) -> List[str]:
        """데이터베이스의 컬렉션 목록 조회

        Args:
            db_name: 데이터베이스 이름

        Returns:
            컬렉션 이름 리스트
        """
        db = self.get_database(db_name)
        return db.list_collection_names()

    def list_databases(self) -> List[str]:
        """데이터베이스 목록 조회

        Returns:
            데이터베이스 이름 리스트
        """
        if self._client is None:
            raise RuntimeError("MongoDB가 연결되지 않았습니다")
        return self._client.list_database_names()

    def collection_stats(self, db_name: str, collection_name: str) -> Dict[str, Any]:
        """컬렉션 통계 정보 조회

        Args:
            db_name: 데이터베이스 이름
            collection_name: 컬렉션 이름

        Returns:
            통계 정보 딕셔너리
        """
        collection = self.get_collection(db_name, collection_name)
        return {
            'count': collection.count_documents({}),
            'indexes': collection.index_information(),
            'name': collection.name
        }

    def drop_collection(self, db_name: str, collection_name: str):
        """컬렉션 삭제

        Args:
            db_name: 데이터베이스 이름
            collection_name: 컬렉션 이름
        """
        collection = self.get_collection(db_name, collection_name)
        collection.drop()
        logger.info(f"컬렉션 삭제: {db_name}.{collection_name}")

    def close(self):
        """MongoDB 연결 종료"""
        if self._client:
            self._client.close()
            self._databases.clear()
            logger.info("MongoDB 연결 종료")

# 전역 인스턴스
mongodb = MongoDB()


# 함수형 인터페이스 (import 스크립트 등에서 직접 사용)
def get_mongo_client(mongodb_url: Optional[str] = None) -> MongoClient:
    """새로운 MongoDB 클라이언트 생성

    Args:
        mongodb_url: MongoDB 연결 URL

    Returns:
        MongoClient 인스턴스
    """
    url = mongodb_url or settings.MONGODB_URL or "mongodb://localhost:27017/"
    return MongoClient(url)


def get_database(db_name: str, mongodb_url: Optional[str] = None) -> Database:
    """데이터베이스 가져오기

    Args:
        db_name: 데이터베이스 이름
        mongodb_url: MongoDB 연결 URL

    Returns:
        Database 인스턴스
    """
    client = get_mongo_client(mongodb_url)
    return client[db_name]


def get_collection(
    db_name: str,
    collection_name: str,
    mongodb_url: Optional[str] = None
) -> Collection:
    """컬렉션 가져오기

    Args:
        db_name: 데이터베이스 이름
        collection_name: 컬렉션 이름
        mongodb_url: MongoDB 연결 URL

    Returns:
        Collection 인스턴스
    """
    db = get_database(db_name, mongodb_url)
    return db[collection_name]
