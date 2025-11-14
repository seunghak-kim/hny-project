"""
Hybrid Legal Search System
계층적 하이브리드 구조: SQLite (메타데이터) + FAISS (벡터 검색)

아키텍처:
1. SQLite: 빠른 메타데이터 쿼리 및 필터링
   - 법령 기본 정보 (laws 테이블)
   - 조항 상세 정보 (articles 테이블)
   - 법령 간 참조 관계 (legal_references 테이블)

2. FAISS: 시맨틱 벡터 검색
   - 문맥 기반 법률 조항 검색
   - 임베딩 모델: KURE_v1
   - Enhanced 임베딩: [장] 제목\n본문

검색 전략:
- Hybrid Search: SQLite 필터 + FAISS 벡터 검색
- Metadata-First: 빠른 메타데이터 기반 필터링 후 벡터 검색
- Vector-First: 벡터 검색 후 SQLite로 상세 정보 보강
"""

import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Config import 추가
from app.service_agent.foundation.config import Config


logger = logging.getLogger(__name__)


class HybridLegalSearch:
    """
    하이브리드 법률 검색 시스템
    SQLite 메타데이터 + FAISS 벡터 검색
    """

    def __init__(
        self,
        sqlite_db_path: Optional[str] = None,
        faiss_db_path: Optional[str] = None,
        embedding_model_path: Optional[str] = None
    ):
        """
        초기화 - Config를 사용하여 경로 자동 설정

        Args:
            sqlite_db_path: SQLite DB 경로 (None이면 Config에서 가져옴)
            faiss_db_path: FAISS DB 경로 (None이면 Config에서 가져옴)
            embedding_model_path: 임베딩 모델 경로 (None이면 Config에서 가져옴)
        """
        # Config에서 경로 가져오기
        self.sqlite_db_path = sqlite_db_path or str(Config.LEGAL_PATHS["sqlite_db"])
        self.faiss_db_path = faiss_db_path or str(Config.LEGAL_PATHS["faiss_db"])
        self.embedding_model_path = embedding_model_path or str(Config.LEGAL_PATHS["embedding_model"])

        # 초기화
        self._init_sqlite()
        self._init_faiss()
        self._init_embedding_model()

        logger.info("HybridLegalSearch initialized successfully")

    def _init_sqlite(self):
        """SQLite 초기화"""
        try:
            self.sqlite_conn = sqlite3.connect(self.sqlite_db_path, check_same_thread=False)
            self.sqlite_conn.row_factory = sqlite3.Row
            logger.info(f"SQLite DB connected: {self.sqlite_db_path}")
        except Exception as e:
            logger.error(f"SQLite initialization failed: {e}")
            raise

    def _init_faiss(self):
        """FAISS 초기화"""
        try:
            # FAISS 인덱스 로드
            faiss_index_path = Path(self.faiss_db_path) / "legal_documents.index"
            self.faiss_index = faiss.read_index(str(faiss_index_path))

            # 메타데이터 로드
            metadata_path = Path(self.faiss_db_path) / "legal_metadata.pkl"
            with open(metadata_path, 'rb') as f:
                self.faiss_metadata = pickle.load(f)

            # 빠른 조회를 위한 chunk_id → metadata dict 생성
            self._faiss_meta_dict = {
                meta.get("chunk_id"): meta
                for meta in self.faiss_metadata
            }

            logger.info(f"FAISS loaded: {self.faiss_index.ntotal} vectors, {len(self.faiss_metadata)} metadata")
        except Exception as e:
            logger.error(f"FAISS initialization failed: {e}")
            raise

    def _init_embedding_model(self):
        """임베딩 모델 초기화"""
        try:
            if Path(self.embedding_model_path).exists():
                self.embedding_model = SentenceTransformer(self.embedding_model_path)
                logger.info(f"Embedding model loaded: {self.embedding_model_path}")
            else:
                raise FileNotFoundError(f"Embedding model not found: {self.embedding_model_path}")
        except Exception as e:
            logger.error(f"Embedding model initialization failed: {e}")
            raise

    # =========================================================================
    # SQLite 메타데이터 쿼리
    # =========================================================================

    def get_law_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """법령명으로 법령 조회"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "SELECT * FROM laws WHERE title LIKE ?",
            (f"%{title}%",)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_articles_by_law_id(self, law_id: int, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """법령 ID로 조항 목록 조회"""
        cursor = self.sqlite_conn.cursor()

        if include_deleted:
            cursor.execute(
                "SELECT * FROM articles WHERE law_id = ? ORDER BY article_number",
                (law_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM articles WHERE law_id = ? AND is_deleted = 0 ORDER BY article_number",
                (law_id,)
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_article_by_number(self, law_title: str, article_number: str) -> Optional[Dict[str, Any]]:
        """법령명 + 조항 번호로 특정 조항 조회"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            SELECT a.* FROM articles a
            JOIN laws l ON a.law_id = l.law_id
            WHERE l.title LIKE ? AND a.article_number = ? AND a.is_deleted = 0
            """,
            (f"%{law_title}%", article_number)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_laws_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리로 법령 검색"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "SELECT * FROM laws WHERE category = ? ORDER BY title",
            (category,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def search_laws_by_doc_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """문서 타입으로 법령 검색"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "SELECT * FROM laws WHERE doc_type = ? ORDER BY title",
            (doc_type,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_tenant_protection_articles(self) -> List[Dict[str, Any]]:
        """임차인 보호 조항 조회"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            SELECT a.*, l.title as law_title
            FROM articles a
            JOIN laws l ON a.law_id = l.law_id
            WHERE a.is_tenant_protection = 1 AND a.is_deleted = 0
            ORDER BY l.title, a.article_number
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_chunk_ids_for_article(self, article_id: int) -> List[str]:
        """조항의 FAISS chunk ID 목록 조회"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "SELECT chunk_ids FROM articles WHERE article_id = ?",
            (article_id,)
        )
        row = cursor.fetchone()

        if row and row["chunk_ids"]:
            try:
                return json.loads(row["chunk_ids"])
            except:
                return []
        return []

    # =========================================================================
    # 쿼리 전처리
    # =========================================================================

    def _enhance_query_for_search(self, query: str) -> str:
        """
        쿼리를 문서 형식과 유사하게 변환

        문서 형식: "[장] 제목\n본문"
        쿼리 형식: "키워드\n원본 쿼리"

        Args:
            query: 원본 검색 쿼리

        Returns:
            Enhanced 쿼리 (키워드 + 원본)
        """
        try:
            import re

            # 법률 용어 리스트 (확장 가능)
            legal_terms = [
                # 공인중개사 관련
                "자격시험", "응시", "조건", "등록", "중개사", "중개업", "공인중개사",
                # 임대차 관련
                "전세금", "인상률", "임대차", "계약", "보증금", "갱신", "임차인",
                "임대인", "월세", "전세", "계약서", "설명의무",
                # 주택 관련
                "주택", "공동주택", "아파트", "다세대", "분양", "임대주택",
                # 법률 용어
                "금지행위", "손해배상", "권리", "의무", "벌칙", "과태료",
                # 절차 관련
                "신고", "허가", "승인", "검사", "확인", "제출"
            ]

            # 쿼리에서 키워드 추출
            keywords = []

            # 법률 용어 매칭 (조사 포함)
            for term in legal_terms:
                # 조사 포함 패턴
                patterns = [term, f"{term}에", f"{term}의", f"{term}을", f"{term}를",
                           f"{term}은", f"{term}는", f"{term}이", f"{term}가"]
                if any(p in query for p in patterns):
                    if term not in keywords:  # 중복 방지
                        keywords.append(term)

            # 키워드가 있으면 제목 형식으로 변환
            if keywords:
                # 최대 3개 키워드 사용
                title = " ".join(keywords[:3])
                enhanced = f"{title}\n{query}"
                logger.debug(f"Query enhanced: '{query}' → '{enhanced}'")
                return enhanced

            # 키워드 없으면 원본 그대로
            return query

        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")
            return query

    # =========================================================================
    # FAISS 벡터 검색
    # =========================================================================

    def _rerank_by_legal_hierarchy(
        self,
        results: Dict[str, Any],
        n_results: int = 10
    ) -> Dict[str, Any]:
        """
        법률 계층 구조를 고려하여 검색 결과 재정렬

        법률 계층: 법률 > 시행령 > 시행규칙 > 대법원규칙

        전략:
        1. 벡터 유사도 기반으로 후보 검색 (n_results * 3)
        2. doc_type 우선순위에 따라 가중치 부여
        3. 조정된 스코어로 재정렬
        4. 상위 n_results 반환

        Args:
            results: FAISS 검색 결과
            n_results: 최종 반환할 결과 개수

        Returns:
            재정렬된 검색 결과
        """
        # doc_type 우선순위 가중치
        doc_type_weights = {
            "법률": 3.0,          # 최우선
            "시행령": 2.0,        # 2순위
            "시행규칙": 1.0,      # 3순위
            "대법원규칙": 1.5,    # 중간
            "용어집": 0.5         # 최하위
        }

        # 결과와 스코어 리스트
        reranked = []

        for i in range(len(results["ids"])):
            meta = results["metadatas"][i]
            distance = results["distances"][i]
            doc_type = meta.get("doc_type", "시행규칙")

            # 유사도 스코어 (distance가 낮을수록 유사도 높음)
            similarity_score = 1.0 / (1.0 + distance)

            # doc_type 가중치 적용
            weight = doc_type_weights.get(doc_type, 1.0)

            # 최종 스코어 = 유사도 * 가중치
            final_score = similarity_score * weight

            reranked.append({
                "index": i,
                "score": final_score,
                "doc_type": doc_type,
                "distance": distance
            })

        # 스코어 기준 정렬 (높은 순)
        reranked.sort(key=lambda x: x["score"], reverse=True)

        # 상위 n_results 선택
        top_indices = [item["index"] for item in reranked[:n_results]]

        # 재정렬된 결과 구성
        return {
            "ids": [results["ids"][i] for i in top_indices],
            "documents": [results["documents"][i] for i in top_indices],
            "metadatas": [results["metadatas"][i] for i in top_indices],
            "distances": [results["distances"][i] for i in top_indices]
        }

    def vector_search(
        self,
        query: str,
        n_results: int = 10,
        where_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        벡터 검색 (FAISS)

        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            where_filters: 메타데이터 필터 (예: {"doc_type": "법률"})

        Returns:
            FAISS 검색 결과 (ChromaDB와 동일한 형식)
        """
        try:
            # ⭐ 쿼리 전처리 추가
            enhanced_query = self._enhance_query_for_search(query)

            # 쿼리 임베딩
            query_embedding = self.embedding_model.encode(enhanced_query, convert_to_tensor=False)
            query_embedding = query_embedding.astype('float32').reshape(1, -1)

            # ⭐ FAISS 검색 (법률 계층 재정렬을 위해 3배 검색)
            search_n = n_results * 3
            distances, indices = self.faiss_index.search(query_embedding, search_n)

            # 결과 구성
            ids = []
            documents = []
            metadatas = []
            result_distances = []

            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.faiss_metadata):
                    meta = self.faiss_metadata[idx]

                    # where_filters 적용
                    if where_filters:
                        skip = False
                        for key, value in where_filters.items():
                            if meta.get(key) != value:
                                skip = True
                                break
                        if skip:
                            continue

                    ids.append(meta.get("chunk_id", f"chunk_{idx}"))
                    documents.append(meta.get("content", ""))
                    metadatas.append(meta)
                    result_distances.append(float(distances[0][i]))

            # 임시 결과 (재정렬 전)
            temp_results = {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
                "distances": result_distances
            }

            # ⭐ 법률 계층 구조 기반 재정렬
            if len(ids) > 0:
                final_results = self._rerank_by_legal_hierarchy(temp_results, n_results)
            else:
                final_results = temp_results

            return final_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

    # =========================================================================
    # 하이브리드 검색 전략
    # =========================================================================

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        doc_type: Optional[str] = None,
        category: Optional[str] = None,
        is_tenant_protection: Optional[bool] = None,
        is_tax_related: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색: SQLite 필터 + FAISS 벡터 검색

        Args:
            query: 검색 쿼리
            limit: 결과 개수
            doc_type: 문서 타입 필터 (법률/시행령/시행규칙 등)
            category: 카테고리 필터
            is_tenant_protection: 임차인 보호 조항 필터
            is_tax_related: 세금 관련 조항 필터

        Returns:
            통합 검색 결과
        """
        logger.info(f"Hybrid search: query='{query}', doc_type={doc_type}, category={category}")

        # 1단계: FAISS 벡터 검색
        where_filters = {}
        if doc_type:
            where_filters["doc_type"] = doc_type

        vector_results = self.vector_search(query, n_results=limit * 2, where_filters=where_filters if where_filters else None)

        if not vector_results["ids"]:
            logger.warning("No vector search results found")
            return []

        # 2단계: SQLite로 메타데이터 보강
        enriched_results = []

        for i, doc_id in enumerate(vector_results["ids"]):
            metadata = vector_results["metadatas"][i]
            document = vector_results["documents"][i]
            distance = vector_results["distances"][i]

            # 법령 정보 조회
            law_title = metadata.get("law_title", "")
            article_number = metadata.get("article_number", "")

            article = self.get_article_by_number(law_title, article_number)

            if article:
                # 추가 필터 적용
                if category:
                    law = self.get_law_by_title(law_title)
                    if not law or law.get("category") != category:
                        continue

                if is_tenant_protection is not None:
                    if article.get("is_tenant_protection", 0) != int(is_tenant_protection):
                        continue

                if is_tax_related is not None:
                    if article.get("is_tax_related", 0) != int(is_tax_related):
                        continue

                # 결과 구성
                enriched_results.append({
                    "chunk_id": doc_id,
                    "law_title": law_title,
                    "article_number": article_number,
                    "article_title": article.get("article_title", ""),
                    "chapter": article.get("chapter"),
                    "section": article.get("section"),
                    "content": document,
                    "relevance_score": 1 - distance,  # Distance → Similarity
                    "is_tenant_protection": bool(article.get("is_tenant_protection", 0)),
                    "is_tax_related": bool(article.get("is_tax_related", 0)),
                    "metadata": metadata
                })

                if len(enriched_results) >= limit:
                    break

        logger.info(f"Hybrid search completed: {len(enriched_results)} results")
        return enriched_results

    def search_specific_article(self, law_title: str, article_number: str) -> Optional[Dict[str, Any]]:
        """
        특정 조항 검색 (예: "주택임대차보호법 제7조")

        Args:
            law_title: 법령명
            article_number: 조항 번호 (예: "제7조")

        Returns:
            조항 상세 정보 + FAISS 내용
        """
        logger.info(f"Searching specific article: {law_title} {article_number}")

        # SQLite에서 조항 메타데이터 조회
        article = self.get_article_by_number(law_title, article_number)

        if not article:
            logger.warning(f"Article not found: {law_title} {article_number}")
            return None

        # FAISS에서 chunk 내용 조회
        chunk_ids = self.get_chunk_ids_for_article(article["article_id"])

        chunks = []
        if chunk_ids:
            try:
                # FAISS 메타데이터 dict에서 chunk_id로 검색 (O(1) 조회)
                for chunk_id in chunk_ids:
                    meta = self._faiss_meta_dict.get(chunk_id)
                    if meta:
                        chunks.append(meta.get("content", ""))
            except Exception as e:
                logger.error(f"Failed to retrieve chunks from FAISS: {e}")

        # 결과 구성
        return {
            "article_id": article["article_id"],
            "law_title": law_title,
            "article_number": article_number,
            "article_title": article.get("article_title", ""),
            "chapter": article.get("chapter"),
            "section": article.get("section"),
            "content": "\n".join(chunks) if chunks else "",
            "chunks": chunks,
            "chunk_count": len(chunks),
            "is_tenant_protection": bool(article.get("is_tenant_protection", 0)),
            "is_tax_related": bool(article.get("is_tax_related", 0)),
            "is_delegation": bool(article.get("is_delegation", 0)),
            "is_penalty_related": bool(article.get("is_penalty_related", 0)),
            "metadata_json": article.get("metadata_json")
        }

    def get_law_statistics(self) -> Dict[str, Any]:
        """법률 DB 통계 조회"""
        cursor = self.sqlite_conn.cursor()

        # 총 법령 수
        cursor.execute("SELECT COUNT(*) as total FROM laws")
        total_laws = cursor.fetchone()["total"]

        # 문서 타입별 분포
        cursor.execute("SELECT doc_type, COUNT(*) as count FROM laws GROUP BY doc_type")
        doc_type_dist = {row["doc_type"]: row["count"] for row in cursor.fetchall()}

        # 카테고리별 분포
        cursor.execute("SELECT category, COUNT(*) as count FROM laws GROUP BY category")
        category_dist = {row["category"]: row["count"] for row in cursor.fetchall()}

        # 총 조항 수
        cursor.execute("SELECT COUNT(*) as total FROM articles WHERE is_deleted = 0")
        total_articles = cursor.fetchone()["total"]

        # 특수 조항 수
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE is_tenant_protection = 1")
        tenant_protection_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE is_tax_related = 1")
        tax_related_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE is_delegation = 1")
        delegation_count = cursor.fetchone()["count"]

        return {
            "total_laws": total_laws,
            "total_articles": total_articles,
            "doc_type_distribution": doc_type_dist,
            "category_distribution": category_dist,
            "special_articles": {
                "tenant_protection": tenant_protection_count,
                "tax_related": tax_related_count,
                "delegation": delegation_count
            },
            "faiss_vectors": self.faiss_index.ntotal
        }

    def close(self):
        """리소스 정리"""
        if hasattr(self, 'sqlite_conn'):
            self.sqlite_conn.close()
            logger.info("SQLite connection closed")

    # =========================================================================
    # 비동기 지원 메서드 (search_executor 호환)
    # =========================================================================

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        통합 검색 메서드 - search_executor와 호환

        Args:
            query: 검색 쿼리
            params: 검색 파라미터
                - mode: 검색 모드 ('hybrid', 'vector', 'specific')
                - limit: 결과 개수
                - doc_type: 문서 타입
                - category: 카테고리
                - is_tenant_protection: 임차인 보호 조항 필터
                - is_tax_related: 세금 관련 조항 필터

        Returns:
            검색 결과 (status, data, count, query 포함)
        """
        params = params or {}
        mode = params.get('mode', 'hybrid')

        try:
            # 검색 모드에 따라 적절한 메서드 호출
            if mode == 'hybrid':
                results = self.hybrid_search(
                    query=query,
                    limit=params.get('limit', 10),
                    doc_type=params.get('doc_type'),
                    category=params.get('category'),
                    is_tenant_protection=params.get('is_tenant_protection'),
                    is_tax_related=params.get('is_tax_related')
                )
            elif mode == 'vector':
                vector_results = self.vector_search(
                    query=query,
                    n_results=params.get('limit', 10),
                    where_filters=params.get('where_filters')
                )
                # vector_search 결과를 표준 형식으로 변환
                results = []
                for i, doc_id in enumerate(vector_results.get("ids", [])):
                    results.append({
                        "doc_id": doc_id,
                        "content": vector_results["documents"][i] if i < len(vector_results.get("documents", [])) else "",
                        "metadata": vector_results["metadatas"][i] if i < len(vector_results.get("metadatas", [])) else {},
                        "relevance_score": 1 - vector_results["distances"][i] if i < len(vector_results.get("distances", [])) else 0
                    })
            elif mode == 'specific':
                # 특정 조문 검색 (예: "주택임대차보호법 제7조")
                import re
                pattern = r'(.+?)\s*제(\d+)조(?:의(\d+))?'
                match = re.search(pattern, query)

                if match:
                    law_title = match.group(1).strip()
                    article_num = match.group(2)
                    sub_num = match.group(3)
                    article_number = f"제{article_num}조" + (f"의{sub_num}" if sub_num else "")

                    result = self.search_specific_article(law_title, article_number)
                    results = [result] if result else []
                else:
                    results = []
            else:
                # 기본: hybrid 검색
                results = self.hybrid_search(
                    query=query,
                    limit=params.get('limit', 10)
                )

            return {
                "status": "success",
                "data": results,
                "count": len(results),
                "total_count": len(results),
                "query": query,
                "mode": mode
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": [],
                "count": 0,
                "query": query
            }


# =========================================================================
# 유틸리티 함수
# =========================================================================

def create_hybrid_legal_search(
    data_dir: Optional[Path] = None
) -> HybridLegalSearch:
    """
    HybridLegalSearch 인스턴스 생성 (기본 경로 사용)

    Args:
        data_dir: 데이터 디렉토리 (None이면 기본 경로)

    Returns:
        HybridLegalSearch 인스턴스
    """
    if data_dir is None:
        # 기본 경로 설정
        backend_dir = Path(__file__).parent.parent.parent.parent
        data_dir = backend_dir / "data" / "storage" / "legal_info"

    sqlite_db_path = str(data_dir / "sqlite_db" / "legal_metadata.db")
    faiss_db_path = str(data_dir / "faiss_db")

    # 임베딩 모델 경로
    embedding_model_path = str(backend_dir / "app" / "ml_models" / "KURE_v1")

    return HybridLegalSearch(
        sqlite_db_path=sqlite_db_path,
        faiss_db_path=faiss_db_path,
        embedding_model_path=embedding_model_path
    )
