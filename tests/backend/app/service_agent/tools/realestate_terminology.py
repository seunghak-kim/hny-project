"""
부동산 용어 추출 tools
현재 DB SQLite
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import numpy as np
from sentence_transformers import SentenceTransformer

# Config 추가
from app.service_agent.foundation.config import Config

from app.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

# 클래스 추가
class RealEstateTerminologyTool:
    """
    부동산 용어 검색 도구
    SQLite + FAISS 하이브리드 검색
    - SQLite: 부동산 용어 메타데이터 저장
    - FAISS: 의미 기반 벡터 검색
    """
    def __init__(
        self,
        sqlite_db_path: str | None = None,
        faiss_db_path: str | None = None,
        embedding_model_path: str | None = None
    ):
        """
        부동산 용어 도구 초기화

        Args:
            sqlite_db_path: SQLite DB 경로
            faiss_db_path: FAISS DB 경로
            embedding_model_path: 임베딩 모델 경로
        """
        self.sqlite_db_path = sqlite_db_path or str(Config.LEGAL_PATHS["sqlite_db"])
        self.faiss_db_path = faiss_db_path or str(Config.LEGAL_PATHS["faiss_db"])
        self.embedding_model_path = embedding_model_path or str(Config.LEGAL_PATHS["embedding_model"])

        # DatabaseManager를 통한 초기화
        self.db_manager = DatabaseManager(
            sqlite_db_path=self.sqlite_db_path,
            faiss_db_path=self.faiss_db_path,
            embedding_model_path=self.embedding_model_path
        ).initialization()

        # 부동산 용어집 law_id (부동산_용어_95가지)
        self.terminology_law_id = 28

        logger.info("RealEstateTerminologyTool initialized successfully")

    def search_terminology(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        부동산 용어 검색 (하이브리드)

        Args:
            query: 검색 쿼리 (예: "가계약금", "매매계약 관련 용어")
            top_k: 반환할 최대 결과 수
            category_filter: 카테고리 필터 (예: "매매거래", "임대차")

        Returns:
            검색 결과 딕셔너리
        """
        try:
            # 1. FAISS 벡터 검색
            vector_results = self._vector_search(query, top_k * 2)

            # 2. SQLite에서 부동산 용어만 필터링 및 상세 정보 조회
            terminology_results = self._get_terminology_details(
                vector_results,
                category_filter=category_filter
            )

            # 3. top_k만큼만 반환
            final_results = terminology_results[:top_k]

            return {
                "success": True,
                "query": query,
                "total_found": len(final_results),
                "results": final_results
            }

        except Exception as e:
            logger.error(f"Terminology search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }

    def get_all_terminologies(
        self,
        category_filter: Optional[str] = None,
        section_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        모든 부동산 용어 조회

        Args:
            category_filter: 카테고리 필터 (예: "매매거래")
            section_filter: 섹션 필터 (예: "매매 용어")

        Returns:
            전체 용어 목록
        """
        try:
            cursor = self.db_manager.sqlite_conn.cursor()

            # 기본 쿼리
            query = """
                SELECT
                    article_number,
                    article_title,
                    metadata_json,
                    chunk_ids
                FROM articles
                WHERE law_id = ?
            """
            params: List[Any] = [self.terminology_law_id]

            # 조건 추가
            if category_filter or section_filter:
                # metadata_json에서 필터링 (SQLite JSON 함수 사용)
                conditions: List[str] = []
                if category_filter:
                    conditions.append("json_extract(metadata_json, '$.term_category') = ?")
                    params.append(category_filter)
                if section_filter:
                    conditions.append("json_extract(metadata_json, '$.section') = ?")
                    params.append(section_filter)

                if conditions:
                    query += " AND " + " AND ".join(conditions)

            query += " ORDER BY article_number"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # 결과 파싱
            results = []
            for row in rows:
                metadata = json.loads(row['metadata_json']) if row['metadata_json'] else {}
                chunk_ids = json.loads(row['chunk_ids']) if row['chunk_ids'] else []

                # FAISS에서 실제 내용 가져오기
                content = self._get_content_from_faiss(chunk_ids)

                results.append({
                    "term_number": metadata.get("term_number"),
                    "term_name": metadata.get("term_name"),
                    "category": metadata.get("term_category"),
                    "section": metadata.get("section"),
                    "definition": content,
                    "is_legal_term": metadata.get("is_legal_term", False)
                })

            return {
                "success": True,
                "total_count": len(results),
                "results": results,
                "filters": {
                    "category": category_filter,
                    "section": section_filter
                }
            }

        except Exception as e:
            logger.error(f"Get all terminologies failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def get_term_by_name(self, term_name: str) -> Dict[str, Any]:
        """
        용어명으로 정확히 검색

        Args:
            term_name: 용어명 (예: "가계약금", "매도")

        Returns:
            용어 정보
        """
        try:
            cursor = self.db_manager.sqlite_conn.cursor()

            query = """
                SELECT
                    article_number,
                    metadata_json,
                    chunk_ids
                FROM articles
                WHERE law_id = ?
                AND json_extract(metadata_json, '$.term_name') = ?
            """

            cursor.execute(query, [self.terminology_law_id, term_name])
            row = cursor.fetchone()

            if not row:
                return {
                    "success": False,
                    "error": f"용어를 찾을 수 없습니다: {term_name}",
                    "term_name": term_name
                }

            metadata = json.loads(row['metadata_json']) if row['metadata_json'] else {}
            chunk_ids = json.loads(row['chunk_ids']) if row['chunk_ids'] else []

            # FAISS에서 실제 내용 가져오기
            content = self._get_content_from_faiss(chunk_ids)

            return {
                "success": True,
                "term_name": metadata.get("term_name"),
                "term_number": metadata.get("term_number"),
                "category": metadata.get("term_category"),
                "section": metadata.get("section"),
                "definition": content,
                "is_legal_term": metadata.get("is_legal_term", False)
            }

        except Exception as e:
            logger.error(f"Get term by name failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "term_name": term_name
            }

    # ========== 내부 헬퍼 메서드 ==========

    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """FAISS 벡터 검색"""
        try:
            # 쿼리 임베딩
            query_vector = self.db_manager.embedding_model.encode([query])[0]
            query_vector = np.array([query_vector], dtype='float32')

            # FAISS 검색
            distances, indices = self.db_manager.faiss_index.search(query_vector, top_k)

            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.db_manager.faiss_metadata):
                    metadata = self.db_manager.faiss_metadata[idx]
                    results.append({
                        "chunk_id": metadata.get("chunk_id"),
                        "content": metadata.get("content", ""),
                        "distance": float(distance),
                        "metadata": metadata
                    })

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return []

    def _get_terminology_details(
        self,
        vector_results: List[Dict[str, Any]],
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색 결과에서 부동산 용어만 필터링 및 상세 정보 조회"""
        try:
            terminology_results = []
            seen_terms = set()  # 중복 제거용

            for result in vector_results:
                chunk_id = result.get("chunk_id")
                if not chunk_id:
                    continue

                # SQLite에서 해당 chunk_id를 가진 부동산 용어 조회
                cursor = self.db_manager.sqlite_conn.cursor()

                # SQL Injection 방지: chunk_id 검증 및 escape
                # chunk_id가 안전한 문자열인지 확인 (영숫자, 하이픈, 언더스코어만 허용)
                import re
                if not re.match(r'^[a-zA-Z0-9_\-]+$', chunk_id):
                    logger.warning(f"Invalid chunk_id format: {chunk_id}")
                    continue

                # LIKE 패턴을 파라미터로 전달 (parameterized query 사용)
                like_pattern = f'%"{chunk_id}"%'

                query = """
                    SELECT
                        article_number,
                        metadata_json
                    FROM articles
                    WHERE law_id = ?
                    AND json_extract(chunk_ids, '$') LIKE ?
                """

                cursor.execute(query, [self.terminology_law_id, like_pattern])
                row = cursor.fetchone()

                if not row:
                    continue

                metadata = json.loads(row['metadata_json']) if row['metadata_json'] else {}
                term_name = metadata.get("term_name")

                # 중복 제거
                if term_name in seen_terms:
                    continue
                seen_terms.add(term_name)

                # 카테고리 필터링
                if category_filter and metadata.get("term_category") != category_filter:
                    continue

                terminology_results.append({
                    "term_name": term_name,
                    "term_number": metadata.get("term_number"),
                    "category": metadata.get("term_category"),
                    "section": metadata.get("section"),
                    "definition": result.get("content", ""),
                    "is_legal_term": metadata.get("is_legal_term", False),
                    "relevance_score": 1.0 - (result.get("distance", 1.0) / 2.0)  # 거리를 점수로 변환
                })

            return terminology_results

        except Exception as e:
            logger.error(f"Get terminology details failed: {e}", exc_info=True)
            return []

    def _get_content_from_faiss(self, chunk_ids: List[str]) -> str:
        """FAISS에서 chunk_ids로 실제 내용 가져오기"""
        try:
            contents = []
            for chunk_id in chunk_ids:
                if chunk_id in self.db_manager._faiss_meta_dict:
                    metadata = self.db_manager._faiss_meta_dict[chunk_id]
                    content = metadata.get("content", "")
                    if content:
                        contents.append(content)

            return " ".join(contents)

        except Exception as e:
            logger.error(f"Get content from FAISS failed: {e}", exc_info=True)
            return ""

    def get_categories(self) -> Dict[str, Any]:
        """사용 가능한 모든 카테고리 및 섹션 조회"""
        try:
            cursor = self.db_manager.sqlite_conn.cursor()

            query = """
                SELECT DISTINCT
                    json_extract(metadata_json, '$.term_category') as category,
                    json_extract(metadata_json, '$.section') as section
                FROM articles
                WHERE law_id = ?
                AND json_extract(metadata_json, '$.term_category') IS NOT NULL
                ORDER BY category, section
            """

            cursor.execute(query, [self.terminology_law_id])
            rows = cursor.fetchall()

            categories = {}
            for row in rows:
                category = row['category']
                section = row['section']

                if category not in categories:
                    categories[category] = []

                if section and section not in categories[category]:
                    categories[category].append(section)

            return {
                "success": True,
                "categories": categories
            }

        except Exception as e:
            logger.error(f"Get categories failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "categories": {}
            }