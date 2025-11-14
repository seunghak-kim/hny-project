"""
Loan Data Tool - MongoDB 기반 대출 상품 정보 제공

MongoDB 'bank' 데이터베이스에서 대출 상품 정보 조회
컬렉션: kb, hana, sinhan, woori, kakao, sc, k
"""

import logging
from typing import Dict, Any, Optional, List
import re


logger = logging.getLogger(__name__)


class LoanDataTool:
    """MongoDB 기반 대출 상품 데이터 Tool"""

    def __init__(self):
        from app.db.mongo_db import mongodb

        self.mongodb = mongodb
        self.bank_collections = ['kb', 'hana', 'sinhan', 'woori', 'kakao', 'sc', 'k']

        # 은행 이름 매핑 (한글 → 영문 컬렉션명)
        self.bank_name_mapping = {
            '케이뱅크': 'k',
            'k뱅크': 'k',
            'KB': 'kb',
            'kb': 'kb',
            'KB국민은행': 'kb',
            '국민은행': 'kb',
            '하나': 'hana',
            '하나은행': 'hana',
            '신한': 'sinhan',
            '신한은행': 'sinhan',
            '우리': 'woori',
            '우리은행': 'woori',
            '카카오': 'kakao',
            '카카오뱅크': 'kakao',
            'SC': 'sc',
            'sc': 'sc',
            'SC제일': 'sc',
            'SC제일은행': 'sc'
        }

        logger.info(f"LoanDataTool initialized with MongoDB (collections: {', '.join(self.bank_collections)})")

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        MongoDB에서 대출 상품 검색

        Args:
            query: 검색 쿼리 (예: "주택담보대출", "전세자금대출")
            params: 검색 파라미터
                - loan_type: 대출 종류 ("주택담보대출", "전세자금대출", "신용대출")
                - bank: 특정 은행 지정
                - max_interest_rate: 최대 금리 제한
                - min_loan_amount: 최소 대출 한도

        Returns:
            검색 결과 딕셔너리
        """
        params = params or {}

        try:
            # 1. 대출 타입 추출
            loan_type = params.get('loan_type') or self._extract_loan_type(query)

            # 2. 은행 지정 여부 확인
            target_banks = self._extract_target_banks(query, params)

            logger.info(f"Loan search - type: {loan_type}, banks: {target_banks}, query: {query[:50]}")

            # 3. MongoDB에서 검색
            results = await self._search_from_mongodb(
                loan_type=loan_type,
                target_banks=target_banks,
                query=query,
                params=params
            )

            # 4. 결과 포맷팅
            formatted_results = self._format_results(results)

            return {
                "status": "success",
                "data": formatted_results,
                "result_count": len(formatted_results),
                "metadata": {
                    "loan_type": loan_type,
                    "searched_banks": target_banks,
                    "total_products": len(results)
                }
            }

        except Exception as e:
            logger.error(f"Loan search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "data": [],
                "result_count": 0
            }

    async def _search_from_mongodb(
        self,
        loan_type: Optional[str],
        target_banks: List[str],
        query: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """MongoDB에서 대출 상품 검색"""
        all_results = []

        # 검색할 컬렉션 결정
        collections_to_search = target_banks if target_banks else self.bank_collections

        for collection_name in collections_to_search:
            try:
                collection = self.mongodb.get_collection("bank", collection_name)

                # 검색 필터 구성
                search_filter = self._build_search_filter(loan_type, query, params)

                # MongoDB 쿼리 실행
                cursor = collection.find(search_filter).limit(10)  # 은행당 최대 10개

                for doc in cursor:
                    all_results.append({
                        'collection': collection_name,
                        'document': doc
                    })

            except Exception as e:
                logger.error(f"Failed to search collection '{collection_name}': {e}")
                continue

        return all_results

    def _build_search_filter(
        self,
        loan_type: Optional[str],
        query: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """MongoDB 검색 필터 구성"""
        filter_conditions = []

        # 1. 대출 타입 필터
        if loan_type:
            # product_name 또는 content_chunks에서 대출 타입 검색
            type_filter = {
                "$or": [
                    {"metadata.product_name": {"$regex": loan_type, "$options": "i"}},
                    {"metadata.summary": {"$regex": loan_type, "$options": "i"}},
                    {"content_chunks.content_text": {"$regex": loan_type, "$options": "i"}}
                ]
            }
            filter_conditions.append(type_filter)

        # 2. 쿼리 키워드 검색
        query_keywords = self._extract_keywords(query)
        if query_keywords:
            keyword_filter = {
                "$or": [
                    {"metadata.product_name": {"$regex": "|".join(query_keywords), "$options": "i"}},
                    {"metadata.summary": {"$regex": "|".join(query_keywords), "$options": "i"}},
                    {"content_chunks.keywords": {"$in": query_keywords}}
                ]
            }
            filter_conditions.append(keyword_filter)

        # 3. 필터 조합
        if filter_conditions:
            return {"$and": filter_conditions}
        else:
            return {}  # 모든 문서 반환

    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """검색 결과 포맷팅"""
        formatted = []

        for item in results:
            collection_name = item['collection']
            doc = item['document']

            metadata = doc.get('metadata', {})
            content_chunks = doc.get('content_chunks', [])

            # 주요 정보 추출
            product_info = {
                "bank_name": metadata.get('bank_name', self._get_bank_display_name(collection_name)),
                "product_name": metadata.get('product_name', ''),
                "product_category": metadata.get('product_category', ''),
                "summary": metadata.get('summary', ''),
                "source_url": metadata.get('source_document_url', ''),
                "last_updated": metadata.get('last_updated', '')
            }

            # content_chunks에서 주요 정보 추출
            details = self._extract_details_from_chunks(content_chunks)
            product_info.update(details)

            formatted.append(product_info)

        return formatted

    def _extract_details_from_chunks(self, chunks: List[Dict]) -> Dict[str, Any]:
        """content_chunks에서 상세 정보 추출"""
        details = {
            "qualifications": [],
            "target_properties": [],
            "loan_limits": [],
            "interest_rates": [],
            "repayment_methods": [],
            "required_documents": []
        }

        for chunk in chunks:
            category = chunk.get('category', '')
            content = chunk.get('content_text', '')

            if '자격조건' in category:
                details["qualifications"].append(content[:200])  # 최대 200자
            elif '대상주택' in category:
                details["target_properties"].append(content[:200])
            elif '대출한도' in category:
                details["loan_limits"].append(content[:200])
            elif '대출금리' in category:
                details["interest_rates"].append(content[:300])
            elif '상환방식' in category or '대출기간' in category:
                details["repayment_methods"].append(content[:200])
            elif '필요서류' in category:
                details["required_documents"].append(content[:200])

        # 리스트를 문자열로 변환 (첫 번째 항목만)
        for key in details:
            if details[key]:
                details[key] = details[key][0]
            else:
                details[key] = None

        return details

    def _extract_loan_type(self, query: str) -> Optional[str]:
        """쿼리에서 대출 종류 추출"""
        if "주택담보" in query or "담보대출" in query:
            return "주택담보대출"
        elif "전세" in query or "월세" in query or "임차" in query:
            return "전세자금대출"
        elif "신용" in query:
            return "신용대출"
        elif "보금자리" in query:
            return "보금자리론"
        return None

    def _extract_target_banks(self, query: str, params: Dict[str, Any]) -> List[str]:
        """쿼리 또는 params에서 대상 은행 추출"""
        # params에서 직접 지정된 경우
        if 'bank' in params:
            bank_param = params['bank']
            if bank_param in self.bank_name_mapping:
                return [self.bank_name_mapping[bank_param]]
            elif bank_param in self.bank_collections:
                return [bank_param]

        # 쿼리에서 은행 이름 추출
        for bank_korean, bank_code in self.bank_name_mapping.items():
            if bank_korean in query:
                return [bank_code]

        return []  # 빈 리스트 = 모든 은행 검색

    def _get_bank_display_name(self, collection_name: str) -> str:
        """컬렉션명 → 은행 표시 이름"""
        bank_display_names = {
            'k': '케이뱅크',
            'kb': 'KB국민은행',
            'hana': '하나은행',
            'sinhan': '신한은행',
            'woori': '우리은행',
            'kakao': '카카오뱅크',
            'sc': 'SC제일은행'
        }
        return bank_display_names.get(collection_name, collection_name.upper())

    def _extract_keywords(self, query: str) -> List[str]:
        """쿼리에서 키워드 추출"""
        # 불용어 제거
        stopwords = ['은', '는', '이', '가', '을', '를', '에서', '으로', '의', '대출', '상품']

        # 공백 및 특수문자 기준 분리
        tokens = re.findall(r'\w+', query)

        # 불용어 제거 및 2자 이상 키워드만 추출
        keywords = [token for token in tokens if token not in stopwords and len(token) >= 2]

        return keywords[:5]  # 최대 5개

    def get_statistics(self) -> Dict[str, Any]:
        """MongoDB 대출 상품 통계"""
        try:
            stats = {
                "total_banks": len(self.bank_collections),
                "banks": {}
            }

            for collection_name in self.bank_collections:
                collection = self.mongodb.get_collection("bank", collection_name)
                count = collection.count_documents({})
                stats["banks"][collection_name] = {
                    "name": self._get_bank_display_name(collection_name),
                    "product_count": count
                }

            stats["total_products"] = sum(bank["product_count"] for bank in stats["banks"].values())

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}
