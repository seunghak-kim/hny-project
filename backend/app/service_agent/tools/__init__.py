"""
Tools Package
에이전트가 사용하는 도구 모음
"""

# =========================================================================
# 기존 Tools
# =========================================================================

from .market_data_tool import MarketDataTool
from .loan_data_tool import LoanDataTool

# 분석 도구들
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool, PolicyType

# =========================================================================
# 신규 Tools (chatbot_execute 병합)
# =========================================================================

# Legal Search (SQLite + FAISS)
from .legal_search_tool import LegalSearch

# 공공데이터 API Tools
from .building_registry_tool import BuildingRegistryTool

# Infrastructure Tool (카카오 API)
from .infrastructure_tool import InfrastructureTool

# 부동산 용어 사전
from .realestate_terminology import RealEstateTerminologyTool

# Real Estate Search (PostgreSQL)
from .real_estate_search_tool import RealEstateSearchTool

# =========================================================================
# Backward Compatibility Aliases
# =========================================================================

# LegalSearch 기본 이름
LegalSearchTool = LegalSearch

# RealEstateTerminology alias (더 짧은 이름)
RealEstateTerminology = RealEstateTerminologyTool

# 기존 HybridLegalSearch도 import 가능하게 유지
try:
    from .hybrid_legal_search import HybridLegalSearch
except ImportError:
    HybridLegalSearch = None

# LoanProductTool placeholder 유지
class LoanProductTool:
    """Placeholder for LoanProductTool"""
    pass

# =========================================================================
# Exports
# =========================================================================

__all__ = [
    # 기존 도구
    "MarketDataTool",
    "LoanDataTool",
    "LoanProductTool",

    # 분석 도구
    "ContractAnalysisTool",
    "MarketAnalysisTool",
    "ROICalculatorTool",
    "LoanSimulatorTool",
    "PolicyMatcherTool",
    "PolicyType",

    # 신규 도구 (chatbot_execute)
    "LegalSearch",
    "LegalSearchTool",  # Alias
    "BuildingRegistryTool",
    "InfrastructureTool",
    "RealEstateTerminologyTool",
    "RealEstateTerminology",  # Alias
    "RealEstateSearchTool",

    # Backward compatibility
    "HybridLegalSearch",
]
