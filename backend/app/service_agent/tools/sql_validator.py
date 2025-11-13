"""
SQL Validator - SQL 안전성 검증
- SQL Injection 방어
- 구조 검증
- 읽기 전용 확인
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SQLValidator:
    """
    SQL 안전성 검증기
    - SQL Injection 방어
    - 구조 검증
    - 읽기 전용 확인
    """

    FORBIDDEN_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
        "ALTER", "CREATE", "REPLACE", "EXEC", "EXECUTE",
        "GRANT", "REVOKE", "ROLLBACK", "COMMIT"
    ]

    ALLOWED_TABLES = [
        "real_estates", "regions", "transactions",
        "nearby_facilities", "real_estate_agents", "trust_scores"
    ]

    def validate(self, sql: str) -> Dict[str, Any]:
        """
        SQL 검증

        Returns:
            {
                "is_valid": bool,
                "error": str | None,
                "warnings": list,
                "query_type": str
            }
        """
        warnings = []

        # 1. 기본 검증
        if not sql or not isinstance(sql, str):
            return {
                "is_valid": False,
                "error": "SQL is empty or invalid type",
                "warnings": [],
                "query_type": None
            }

        sql_upper = sql.upper()

        # 2. 금지된 키워드 검사
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                logger.error(f"[SECURITY] Forbidden keyword detected: {keyword}")
                return {
                    "is_valid": False,
                    "error": f"Forbidden keyword: {keyword}",
                    "warnings": warnings,
                    "query_type": None
                }

        # 3. SELECT 쿼리만 허용
        if not sql_upper.strip().startswith("SELECT"):
            return {
                "is_valid": False,
                "error": "Only SELECT queries allowed",
                "warnings": warnings,
                "query_type": "UNKNOWN"
            }

        # 4. 테이블 화이트리스트 검증
        tables = self._extract_tables(sql)
        invalid_tables = [t for t in tables if t not in self.ALLOWED_TABLES]

        if invalid_tables:
            return {
                "is_valid": False,
                "error": f"Invalid tables: {invalid_tables}",
                "warnings": warnings,
                "query_type": "SELECT"
            }

        # 5. LIMIT 절 확인 (권장사항)
        if "LIMIT" not in sql_upper:
            warnings.append("No LIMIT clause - may return too many rows")

        # 6. 주석 검사 (SQL Injection 시도)
        if "--" in sql or "/*" in sql:
            warnings.append("SQL contains comments")

        # 7. 세미콜론 검사 (다중 쿼리 실행 방지)
        if sql.count(";") > 1:
            return {
                "is_valid": False,
                "error": "Multiple statements detected",
                "warnings": warnings,
                "query_type": "SELECT"
            }

        logger.info(f"[SQL Validator] ✅ Validation passed")
        if warnings:
            logger.warning(f"[SQL Validator] Warnings: {warnings}")

        return {
            "is_valid": True,
            "error": None,
            "warnings": warnings,
            "query_type": "SELECT"
        }

    def _extract_tables(self, sql: str) -> list:
        """FROM 절에서 테이블 이름 추출"""
        # 간단한 정규식 기반 추출 (FROM ... JOIN 패턴)
        from_pattern = r'FROM\s+(\w+)'
        join_pattern = r'JOIN\s+(\w+)'

        tables = []

        # FROM 절 테이블
        from_matches = re.finditer(from_pattern, sql, re.IGNORECASE)
        for match in from_matches:
            tables.append(match.group(1).lower())

        # JOIN 절 테이블
        join_matches = re.finditer(join_pattern, sql, re.IGNORECASE)
        for match in join_matches:
            tables.append(match.group(1).lower())

        return list(set(tables))  # 중복 제거
