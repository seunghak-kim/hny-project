"""
Decision Logger - LLM 의사결정 로깅 시스템
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.service_agent.foundation.config import Config

logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    LLM의 의사결정 데이터를 수집하는 로깅 시스템
    - 에이전트 선택 결정 로깅
    - 도구 선택 결정 로깅
    - 실행 결과 업데이트
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        초기화

        Args:
            db_path: SQLite DB 경로 (기본값: Config.AGENT_LOGGING_DIR / "decisions.db")
        """
        self.db_path = db_path or (Config.AGENT_LOGGING_DIR / "decisions.db")
        self._initialize_database()

    def _initialize_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # agent_decisions 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query TEXT NOT NULL,
                    selected_agents TEXT NOT NULL,
                    reasoning TEXT,
                    confidence REAL,
                    execution_result TEXT,
                    execution_time_ms INTEGER,
                    success INTEGER DEFAULT 1
                )
            """)

            # tool_decisions 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    query TEXT NOT NULL,
                    available_tools TEXT NOT NULL,
                    selected_tools TEXT NOT NULL,
                    reasoning TEXT,
                    confidence REAL,
                    execution_results TEXT,
                    total_execution_time_ms INTEGER,
                    success INTEGER DEFAULT 1
                )
            """)

            conn.commit()
            conn.close()

            logger.info(f"DecisionLogger initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize DecisionLogger database: {e}")
            raise

    def log_agent_decision(
        self,
        query: str,
        selected_agents: List[str],
        reasoning: str = "",
        confidence: float = 0.0
    ) -> Optional[int]:
        """
        에이전트 선택 결정 로깅

        Args:
            query: 사용자 질문
            selected_agents: 선택된 에이전트 목록
            reasoning: 선택 이유
            confidence: 확신도 (0.0~1.0)

        Returns:
            decision_id: 로깅된 레코드 ID (실패 시 None)
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()
            selected_agents_json = json.dumps(selected_agents, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO agent_decisions (
                    timestamp, query, selected_agents, reasoning, confidence
                ) VALUES (?, ?, ?, ?, ?)
            """, (timestamp, query, selected_agents_json, reasoning, confidence))

            decision_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.debug(f"Logged agent decision: ID={decision_id}, agents={selected_agents}")
            return decision_id

        except Exception as e:
            logger.error(f"Failed to log agent decision: {e}", exc_info=True)
            return None

    def log_tool_decision(
        self,
        agent_type: str,
        query: str,
        available_tools: Dict[str, Any],
        selected_tools: List[str],
        reasoning: str = "",
        confidence: float = 0.0
    ) -> Optional[int]:
        """
        도구 선택 결정 로깅

        Args:
            agent_type: 에이전트 타입 (search, analysis 등)
            query: 사용자 질문
            available_tools: 사용 가능한 도구 정보
            selected_tools: 선택된 도구 목록
            reasoning: 선택 이유
            confidence: 확신도 (0.0~1.0)

        Returns:
            decision_id: 로깅된 레코드 ID (실패 시 None)
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()
            available_tools_json = json.dumps(available_tools, ensure_ascii=False)
            selected_tools_json = json.dumps(selected_tools, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO tool_decisions (
                    timestamp, agent_type, query, available_tools,
                    selected_tools, reasoning, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, agent_type, query, available_tools_json,
                selected_tools_json, reasoning, confidence
            ))

            decision_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.debug(
                f"Logged tool decision: ID={decision_id}, "
                f"agent={agent_type}, tools={selected_tools}"
            )
            return decision_id

        except Exception as e:
            logger.error(f"Failed to log tool decision: {e}", exc_info=True)
            return None

    def update_agent_execution_result(
        self,
        decision_id: int,
        execution_result: str,
        execution_time_ms: int,
        success: bool = True
    ) -> bool:
        """
        에이전트 실행 결과 업데이트

        Args:
            decision_id: 업데이트할 결정 ID
            execution_result: 실행 결과 요약
            execution_time_ms: 실행 시간 (밀리초)
            success: 성공 여부

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE agent_decisions
                SET execution_result = ?,
                    execution_time_ms = ?,
                    success = ?
                WHERE id = ?
            """, (execution_result, execution_time_ms, 1 if success else 0, decision_id))

            conn.commit()
            conn.close()

            logger.debug(f"Updated agent execution result: ID={decision_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update agent execution result: {e}", exc_info=True)
            return False

    def update_tool_execution_results(
        self,
        decision_id: int,
        execution_results: Dict[str, Any],
        total_execution_time_ms: int,
        success: bool = True
    ) -> bool:
        """
        도구 실행 결과 업데이트

        Args:
            decision_id: 업데이트할 결정 ID
            execution_results: 각 도구별 실행 결과 (dict)
            total_execution_time_ms: 총 실행 시간 (밀리초)
            success: 전체 성공 여부

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            execution_results_json = json.dumps(execution_results, ensure_ascii=False)

            cursor.execute("""
                UPDATE tool_decisions
                SET execution_results = ?,
                    total_execution_time_ms = ?,
                    success = ?
                WHERE id = ?
            """, (execution_results_json, total_execution_time_ms, 1 if success else 0, decision_id))

            conn.commit()
            conn.close()

            logger.debug(f"Updated tool execution results: ID={decision_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update tool execution results: {e}", exc_info=True)
            return False

    def get_decisions_by_date(
        self,
        start_date: str,
        end_date: str,
        decision_type: str = "both"
    ) -> Dict[str, List[Dict]]:
        """
        날짜 범위로 결정 조회

        Args:
            start_date: 시작 날짜 (ISO format)
            end_date: 종료 날짜 (ISO format)
            decision_type: 결정 타입 ("agent", "tool", "both")

        Returns:
            {"agent_decisions": [...], "tool_decisions": [...]}
        """
        result = {"agent_decisions": [], "tool_decisions": []}

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Dict 형태로 반환
            cursor = conn.cursor()

            if decision_type in ["agent", "both"]:
                cursor.execute("""
                    SELECT * FROM agent_decisions
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """, (start_date, end_date))
                result["agent_decisions"] = [dict(row) for row in cursor.fetchall()]

            if decision_type in ["tool", "both"]:
                cursor.execute("""
                    SELECT * FROM tool_decisions
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """, (start_date, end_date))
                result["tool_decisions"] = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return result

        except Exception as e:
            logger.error(f"Failed to get decisions by date: {e}", exc_info=True)
            return result

    def get_tool_usage_stats(
        self,
        agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        도구 사용 통계

        Args:
            agent_type: 특정 에이전트 타입 (None이면 전체)

        Returns:
            {
                "total_decisions": int,
                "tool_frequency": {tool_name: count, ...},
                "avg_confidence": float,
                "success_rate": float
            }
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # 조건 설정
            where_clause = ""
            params = []
            if agent_type:
                where_clause = "WHERE agent_type = ?"
                params.append(agent_type)

            # 전체 결정 수
            cursor.execute(f"""
                SELECT COUNT(*) FROM tool_decisions {where_clause}
            """, params)
            total_decisions = cursor.fetchone()[0]

            # 도구별 빈도
            cursor.execute(f"""
                SELECT selected_tools FROM tool_decisions {where_clause}
            """, params)
            tool_frequency = {}
            for row in cursor.fetchall():
                tools = json.loads(row[0])
                for tool in tools:
                    tool_frequency[tool] = tool_frequency.get(tool, 0) + 1

            # 평균 confidence
            cursor.execute(f"""
                SELECT AVG(confidence) FROM tool_decisions {where_clause}
            """, params)
            avg_confidence = cursor.fetchone()[0] or 0.0

            # 성공률
            cursor.execute(f"""
                SELECT AVG(success) FROM tool_decisions {where_clause}
            """, params)
            success_rate = cursor.fetchone()[0] or 0.0

            conn.close()

            return {
                "total_decisions": total_decisions,
                "tool_frequency": tool_frequency,
                "avg_confidence": avg_confidence,
                "success_rate": success_rate
            }

        except Exception as e:
            logger.error(f"Failed to get tool usage stats: {e}", exc_info=True)
            return {
                "total_decisions": 0,
                "tool_frequency": {},
                "avg_confidence": 0.0,
                "success_rate": 0.0
            }
