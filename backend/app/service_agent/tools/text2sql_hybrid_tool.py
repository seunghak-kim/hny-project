"""
Text2SQL Hybrid Tool - 템플릿과 LLM SQL 생성을 결합
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.service_agent.tools.sql_templates import SQLTemplateEngine
from app.service_agent.tools.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class Text2SQLHybridTool:
    """
    Text2SQL 하이브리드 도구
    템플릿 기반 SQL 생성 (안전하고 빠름)
    """

    def __init__(self):
        self.template_engine = SQLTemplateEngine()
        self.validator = SQLValidator()

        # 통계
        self.stats = {
            "template_attempts": 0,
            "template_success": 0,
            "validation_failures": 0
        }

    async def search(
        self,
        query: str,
        params: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        하이브리드 검색 실행

        전략:
        1. 템플릿 매칭 시도 (빠르고 안전)
        2. 모든 SQL은 검증 레이어 통과 필수

        Args:
            query: 사용자 쿼리
            params: 추출된 파라미터
            db: DB 세션

        Returns:
            검색 결과
        """
        logger.info(f"[Text2SQL Hybrid] Query: {query}")
        logger.info(f"[Text2SQL Hybrid] Params: {params}")

        # === 템플릿 시도 ===
        template_result = await self._try_template(query, params, db)

        if template_result.get("status") == "success":
            logger.info("[Text2SQL Hybrid] ✅ Template execution successful")
            self.stats["template_success"] += 1
            return template_result

        logger.info(f"[Text2SQL Hybrid] ⚠️ Template failed: {template_result.get('error')}")

        # === 모두 실패 - 에러 반환 ===
        return {
            "status": "error",
            "error": "Template SQL generation failed",
            "template_error": template_result.get("error"),
            "data": [],
            "result_count": 0
        }

    async def _try_template(
        self,
        query: str,
        params: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """템플릿 기반 실행 시도"""
        self.stats["template_attempts"] += 1

        try:
            # 1. 템플릿 매칭
            template_name = self.template_engine.match_template(query, params)

            if not template_name:
                return {
                    "status": "error",
                    "error": "No matching template",
                    "method": "template"
                }

            # 2. 신뢰도 검증
            confidence = self.template_engine.get_template_confidence(template_name, params)

            if confidence < 0.5:
                return {
                    "status": "error",
                    "error": f"Low confidence: {confidence:.2f}",
                    "method": "template"
                }

            # 3. SQL 렌더링
            sql = self.template_engine.render_template(template_name, params)

            # 4. SQL 검증
            validation = self.validator.validate(sql)
            if not validation["is_valid"]:
                self.stats["validation_failures"] += 1
                return {
                    "status": "error",
                    "error": f"Validation failed: {validation['error']}",
                    "method": "template"
                }

            # 5. 파라미터 준비
            execution_params = self._prepare_params(params)

            # 6. 실행
            result = db.execute(text(sql), execution_params)
            rows = result.fetchall()

            # 7. 결과 포맷팅
            data = self._format_results(rows, result.keys())

            logger.info(f"[Template] Executed successfully: {len(data)} results")

            return {
                "status": "success",
                "data": data,
                "method": "template",
                "template_name": template_name,
                "confidence": confidence,
                "result_count": len(data)
            }

        except Exception as e:
            logger.error(f"Template execution error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "method": "template"
            }

    def _prepare_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """파라미터 전처리"""
        execution_params = params.copy()

        # LIKE 연산자용 % 추가
        if "region" in execution_params:
            execution_params["region"] = f"%{execution_params['region']}%"

        # Enum 변환
        if "property_type" in execution_params:
            pt = execution_params["property_type"]
            if isinstance(pt, str):
                execution_params["property_type"] = pt.lower()

        if "transaction_type" in execution_params:
            tt = execution_params["transaction_type"]
            if isinstance(tt, str):
                execution_params["transaction_type"] = tt.lower()

        # 기본값 설정
        if "limit" not in execution_params:
            execution_params["limit"] = 10
        if "offset" not in execution_params:
            execution_params["offset"] = 0

        return execution_params

    def _format_results(self, rows: list, keys: list) -> list:
        """결과를 딕셔너리 리스트로 변환"""
        results = []
        for row in rows:
            result_dict = {}
            for i, key in enumerate(keys):
                value = row[i]
                # Decimal을 float로 변환
                if hasattr(value, '__float__'):
                    value = float(value)
                result_dict[key] = value
            results.append(result_dict)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """사용 통계 반환"""
        return {
            **self.stats,
            "template_success_rate": (
                self.stats["template_success"] / self.stats["template_attempts"]
                if self.stats["template_attempts"] > 0 else 0
            )
        }
