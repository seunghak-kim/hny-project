"""
Bank Loan Search Tool - 은행 대출 상품 검색
PostgreSQL 기반 은행 금융 상품 조회
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


class BankLoanSearchTool:
    """은행 대출 상품 검색 Tool (PostgreSQL 연동)"""

    def __init__(self):
        # Lazy import로 순환 참조 방지
        self._ensure_db_imports()
        logger.info("BankLoanSearchTool initialized with PostgreSQL connection")

    def _ensure_db_imports(self):
        """필요할 때만 import (Lazy Loading)"""
        if not hasattr(self, 'SessionLocal'):
            from app.db.postgre_db import SessionLocal
            from app.models.bank import (
                Bank,
                BankProduct,
                ProductCategory,
                ChunkCategory,
                ContentChunk,
                Keyword
            )

            self.SessionLocal = SessionLocal
            self.Bank = Bank
            self.BankProduct = BankProduct
            self.ProductCategory = ProductCategory
            self.ChunkCategory = ChunkCategory
            self.ContentChunk = ContentChunk
            self.Keyword = Keyword

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        은행 대출 상품 검색 (PostgreSQL)

        Args:
            query: 사용자 쿼리 (예: "전세대출", "주택담보대출")
            params: {
                "bank_name": "KB국민은행",  # 특정 은행
                "product_category": "주택담보대출",  # 상품 카테고리
                "keywords": ["LTV", "주택담보"],  # 키워드 리스트
                "similarity_threshold": 0.3,  # 유사도 검색 임계값
                "limit": 10,
                "offset": 0,
                "include_chunks": True,  # 상세 정보 포함 여부
                "include_keywords": True,  # 키워드 포함 여부
                "search_mode": "keyword" | "similarity" | "full"  # 검색 모드
            }

        Returns:
            {
                "status": "success" | "error",
                "data": [...],
                "result_count": int,
                "metadata": {
                    "bank_name": str,
                    "category": str,
                    "search_mode": str,
                    "data_source": "PostgreSQL"
                }
            }
        """
        params = params or {}

        try:
            # 파라미터 추출
            bank_name = params.get('bank_name')
            product_category = params.get('product_category')
            keywords = params.get('keywords', [])
            similarity_threshold = params.get('similarity_threshold', 0.3)
            limit = params.get('limit', 10)
            offset = params.get('offset', 0)
            include_chunks = params.get('include_chunks', True)
            include_keywords = params.get('include_keywords', True)
            search_mode = params.get('search_mode', 'full')

            # 쿼리에서 은행명 추출
            if not bank_name:
                bank_name = self._extract_bank_name(query)

            # 파라미터로 명시적으로 지정된 경우에만 카테고리 필터 적용
            # 쿼리에서 자동 추출은 하지 않음 (카테고리 이름이 상품명과 다를 수 있음)

            # 키워드 추출
            if not keywords:
                keywords = self._extract_keywords(query)

            logger.info(
                f"Bank loan search - query: '{query}', bank: {bank_name}, "
                f"category: {product_category}, keywords: {keywords}, mode: {search_mode}"
            )

            # 검색 실행
            db = self.SessionLocal()
            try:
                products, total_count = self._search_products(
                    db=db,
                    query=query,
                    bank_name=bank_name,
                    product_category=product_category,
                    keywords=keywords,
                    similarity_threshold=similarity_threshold,
                    limit=limit,
                    offset=offset,
                    search_mode=search_mode
                )

                # 결과 포맷팅
                result_data = []
                for product in products:
                    product_dict = {
                        "product_id": product.product_id,
                        "product_name": product.product_name,
                        "bank_name": product.bank.bank_name,
                        "category": product.product_category.category_name,
                        "summary": product.summary,
                        "source_url": product.source_document_url,
                        "last_updated": product.last_updated.isoformat() if product.last_updated else None
                    }

                    # 상세 정보 포함
                    if include_chunks and product.content_chunks:
                        product_dict["details"] = []
                        for chunk in product.content_chunks:
                            chunk_dict = {
                                "category": chunk.chunk_category.category_name,
                                "content": chunk.content_text
                            }
                            # 키워드 포함
                            if include_keywords and chunk.keywords:
                                chunk_dict["keywords"] = [kw.keyword for kw in chunk.keywords]
                            product_dict["details"].append(chunk_dict)

                    result_data.append(product_dict)

                return {
                    "status": "success",
                    "data": result_data,
                    "result_count": total_count,
                    "metadata": {
                        "query": query,
                        "bank_name": bank_name,
                        "category": product_category,
                        "keywords": keywords,
                        "search_mode": search_mode,
                        "limit": limit,
                        "offset": offset,
                        "data_source": "PostgreSQL"
                    }
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Bank loan search error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "data": [],
                "result_count": 0
            }

    def _search_products(
        self,
        db: Session,
        query: str,
        bank_name: Optional[str],
        product_category: Optional[str],
        keywords: List[str],
        similarity_threshold: float,
        limit: int,
        offset: int,
        search_mode: str
    ):
        """실제 검색 수행"""

        # 기본 쿼리
        query_obj = db.query(self.BankProduct).join(
            self.Bank
        ).join(
            self.ProductCategory
        ).options(
            joinedload(self.BankProduct.bank),
            joinedload(self.BankProduct.product_category),
            joinedload(self.BankProduct.content_chunks).joinedload(self.ContentChunk.chunk_category),
            joinedload(self.BankProduct.content_chunks).joinedload(self.ContentChunk.keywords)
        )

        # 필터 적용
        filters = []

        # 은행명 필터
        if bank_name:
            filters.append(self.Bank.bank_name.ilike(f"%{bank_name}%"))

        # 카테고리 필터
        if product_category:
            filters.append(self.ProductCategory.category_name.ilike(f"%{product_category}%"))

        # 검색 모드별 처리
        if search_mode == "similarity":
            # Trigram 유사도 검색
            similarity_expr = func.similarity(self.BankProduct.product_name, query)
            filters.append(similarity_expr > similarity_threshold)
            query_obj = query_obj.order_by(similarity_expr.desc())

        elif search_mode == "keyword":
            # 키워드 검색
            if keywords:
                keyword_filter = or_(*[
                    self.BankProduct.content_chunks.any(
                        self.ContentChunk.keywords.any(
                            self.Keyword.keyword.ilike(f"%{kw}%")
                        )
                    ) for kw in keywords
                ])
                filters.append(keyword_filter)

        else:  # full mode
            # 전체 검색 (상품명 + 요약 + 키워드)
            search_filters = []

            # 상품명 검색
            search_filters.append(self.BankProduct.product_name.ilike(f"%{query}%"))

            # 요약 검색
            if self.BankProduct.summary:
                search_filters.append(self.BankProduct.summary.ilike(f"%{query}%"))

            # 키워드 검색
            if keywords:
                search_filters.append(
                    self.BankProduct.content_chunks.any(
                        self.ContentChunk.keywords.any(
                            or_(*[self.Keyword.keyword.ilike(f"%{kw}%") for kw in keywords])
                        )
                    )
                )

            # search_filters가 있을 때만 추가
            if search_filters:
                filters.append(or_(*search_filters))

        # 필터 적용
        if filters:
            query_obj = query_obj.filter(and_(*filters))

        # 전체 카운트
        total_count = query_obj.count()

        # 페이지네이션 및 실행
        products = query_obj.limit(limit).offset(offset).all()

        return products, total_count

    def _extract_bank_name(self, query: str) -> Optional[str]:
        """쿼리에서 은행명 추출"""
        bank_keywords = {
            'KB': 'KB국민은행',
            '국민은행': 'KB국민은행',
            '국민': 'KB국민은행',
            '신한은행': '신한은행',
            '신한': '신한은행',
            '하나은행': '하나은행',
            '하나': '하나은행',
            '우리은행': '우리은행',
            '우리': '우리은행',
            '카카오뱅크': '카카오뱅크',
            '카카오': '카카오뱅크',
            'SC': 'SC제일은행',
            'SC제일': 'SC제일은행',
            '케이뱅크': '케이뱅크',
            'K뱅크': '케이뱅크'
        }

        for keyword, bank_name in bank_keywords.items():
            if keyword in query:
                return bank_name
        return None

    def _extract_category(self, query: str) -> Optional[str]:
        """쿼리에서 상품 카테고리 추출"""
        category_keywords = {
            '주택담보': '주택담보대출',
            '주택담보대출': '주택담보대출',
            '전세': '전세자금대출',
            '전세대출': '전세자금대출',
            '전세자금': '전세자금대출',
            '월세': '월세대출',
            '신용대출': '신용대출',
            '신용': '신용대출',
            '서민금융': '서민금융',
            '디딤돌': '디딤돌대출',
            '버팀목': '버팀목대출',
            '보금자리': '보금자리론'
        }

        for keyword, category in category_keywords.items():
            if keyword in query:
                return category
        return None

    def _extract_keywords(self, query: str) -> List[str]:
        """쿼리에서 키워드 추출"""
        keywords = []

        # 일반적인 대출 관련 키워드
        keyword_list = [
            'LTV', 'DTI', 'DSR', '금리', '한도', '대출', '자격조건',
            '대출기간', '상환방식', '중도상환', '보증료', '청년',
            '신혼부부', '생애최초', '무주택', '1주택'
        ]

        for keyword in keyword_list:
            if keyword in query:
                keywords.append(keyword)

        return keywords

    async def get_product_detail(self, product_id: str) -> Dict[str, Any]:
        """
        특정 상품의 상세 정보 조회

        Args:
            product_id: 상품 ID

        Returns:
            상품 상세 정보
        """
        try:
            db = self.SessionLocal()
            try:
                product = db.query(self.BankProduct).filter(
                    self.BankProduct.product_id == product_id
                ).options(
                    joinedload(self.BankProduct.bank),
                    joinedload(self.BankProduct.product_category),
                    joinedload(self.BankProduct.content_chunks).joinedload(self.ContentChunk.chunk_category),
                    joinedload(self.BankProduct.content_chunks).joinedload(self.ContentChunk.keywords)
                ).first()

                if not product:
                    return {
                        "status": "error",
                        "message": f"Product {product_id} not found"
                    }

                # 상세 정보 구성
                details = {}
                for chunk in product.content_chunks:
                    category = chunk.chunk_category.category_name
                    details[category] = {
                        "content": chunk.content_text,
                        "keywords": [kw.keyword for kw in chunk.keywords]
                    }

                return {
                    "status": "success",
                    "data": {
                        "product_id": product.product_id,
                        "product_name": product.product_name,
                        "bank_name": product.bank.bank_name,
                        "category": product.product_category.category_name,
                        "summary": product.summary,
                        "source_url": product.source_document_url,
                        "last_updated": product.last_updated.isoformat() if product.last_updated else None,
                        "details": details
                    }
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Get product detail error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    async def compare_products(self, product_ids: List[str]) -> Dict[str, Any]:
        """
        여러 상품 비교

        Args:
            product_ids: 비교할 상품 ID 리스트

        Returns:
            상품 비교 정보
        """
        try:
            db = self.SessionLocal()
            try:
                products = db.query(self.BankProduct).filter(
                    self.BankProduct.product_id.in_(product_ids)
                ).options(
                    joinedload(self.BankProduct.bank),
                    joinedload(self.BankProduct.product_category),
                    joinedload(self.BankProduct.content_chunks).joinedload(self.ContentChunk.chunk_category),
                    joinedload(self.BankProduct.content_chunks).joinedload(self.ContentChunk.keywords)
                ).all()

                comparison = []
                for product in products:
                    # 주요 정보 추출
                    details_summary = {}
                    for chunk in product.content_chunks:
                        category = chunk.chunk_category.category_name
                        # 주요 카테고리만 추출
                        if category in ['자격조건', '대출한도', '대출금리', '대출기간_상환방식']:
                            details_summary[category] = chunk.content_text[:200]  # 앞 200자만

                    comparison.append({
                        "product_id": product.product_id,
                        "product_name": product.product_name,
                        "bank_name": product.bank.bank_name,
                        "category": product.product_category.category_name,
                        "summary": product.summary,
                        "key_details": details_summary
                    })

                return {
                    "status": "success",
                    "data": comparison,
                    "comparison_count": len(comparison)
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Compare products error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    async def get_bank_statistics(self) -> Dict[str, Any]:
        """
        은행별 상품 통계

        Returns:
            은행별 상품 수 통계
        """
        try:
            db = self.SessionLocal()
            try:
                stats = db.query(
                    self.Bank.bank_name,
                    func.count(self.BankProduct.id).label('product_count')
                ).join(
                    self.BankProduct
                ).group_by(
                    self.Bank.bank_name
                ).order_by(
                    func.count(self.BankProduct.id).desc()
                ).all()

                return {
                    "status": "success",
                    "data": [
                        {
                            "bank_name": stat.bank_name,
                            "product_count": stat.product_count
                        }
                        for stat in stats
                    ]
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Get bank statistics error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
