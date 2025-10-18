"""
Tools Package
에이전트가 사용하는 도구 모음
"""

# Note: Some tools are being refactored - using available tools only
# from .legal_search_tool import LegalSearchTool
# from .loan_product_tool import LoanProductTool
from .market_data_tool import MarketDataTool
from .loan_data_tool import LoanDataTool

# Create placeholder classes for missing tools to avoid import errors
class LegalSearchTool:
    """Placeholder for LegalSearchTool"""
    pass

class LoanProductTool:
    """Placeholder for LoanProductTool"""
    pass

# 분석 도구들
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool, PolicyType

__all__ = [
    # 기존 도구
    "LegalSearchTool",
    "LoanProductTool",
    "MarketDataTool",
    # 분석 도구
    "ContractAnalysisTool",
    "MarketAnalysisTool",
    "ROICalculatorTool",
    "LoanSimulatorTool",
    "PolicyMatcherTool",
    "PolicyType"
]