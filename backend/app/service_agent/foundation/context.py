"""
Context Definitions for LangGraph 0.6.x
Runtime metadata passed through the context parameter
Updated with improved naming conventions
"""

from typing import TypedDict, Optional, Dict, List, Any
from dataclasses import dataclass, field
import os
from datetime import datetime
import uuid


# ============ Context Types ============

@dataclass
class LLMContext:
    """
    LLM configuration for runtime context
    Used with LangGraph 0.6+ Runtime object for typed access
    """
    # ========== Provider Settings ==========
    provider: str = "openai"  # openai, azure, mock
    api_key: Optional[str] = None
    organization: Optional[str] = None

    # ========== Model Overrides ==========
    model_overrides: Optional[Dict[str, str]] = field(default_factory=dict)
    # Example: {"intent": "gpt-4", "planning": "gpt-4o"}

    # ========== Parameter Overrides ==========
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None

    # ========== User Context ==========
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # ========== Feature Flags ==========
    enable_retry: bool = True
    enable_logging: bool = True

class AgentContext(TypedDict):
    """
    Runtime context for agents
    Contains metadata and configuration passed at execution time
    This is READ-ONLY during execution
    Updated for LangGraph 0.6+ with LLMContext

    Naming Convention:
    - chat_* : LangGraph/Chatbot system identifiers (string)
    - db_* : Database reference IDs (integer)
    - No prefix : Other runtime metadata
    """

    # ========== LangGraph System Identifiers ==========
    chat_user_ref: str              # Chatbot user reference (e.g., "user_abc123")
    chat_session_id: str            # Chatbot session ID (e.g., "session_xyz789")
    chat_thread_id: Optional[str]   # LangGraph thread ID for checkpointing

    # ========== Database References (when linked) ==========
    db_user_id: Optional[int]       # Actual DB users.user_id (BIGINT)
    db_session_id: Optional[int]    # Actual DB chat_sessions.session_id (BIGINT)

    # ========== Runtime Info ==========
    request_id: Optional[str]       # Unique request ID
    timestamp: Optional[str]        # Request timestamp
    original_query: Optional[str]   # Original user input

    # ========== Authentication ==========
    api_keys: Optional[Dict[str, str]]  # Service API keys (runtime injection)

    # ========== User Settings ==========
    language: Optional[str]         # User language (ko, en, etc.)

    # ========== Execution Control ==========
    debug_mode: Optional[bool]      # Enable debug logging
    trace_enabled: Optional[bool]   # Enable detailed tracing

    # ========== LLM Configuration (LangGraph 0.6+) ==========
    llm_context: Optional[LLMContext]  # LLM runtime configuration


class SubgraphContext(TypedDict):
    """
    Context for subgraphs (filtered subset of AgentContext)
    Used when invoking DataCollectionSubgraph, AnalysisSubgraph, etc.
    """

    # ========== Required (from parent) ==========
    chat_user_ref: str
    chat_session_id: str
    chat_thread_id: Optional[str]

    # ========== Database References ==========
    db_user_id: Optional[int]
    db_session_id: Optional[int]

    # ========== Optional (from parent) ==========
    request_id: Optional[str]
    language: Optional[str]
    debug_mode: Optional[bool]

    # ========== Subgraph Identification ==========
    parent_agent: str           # Name of parent agent
    subgraph_name: str         # Name of current subgraph

    # ========== Subgraph Parameters ==========
    suggested_tools: Optional[List[str]]  # Tool hints for subgraph
    analysis_depth: Optional[str]         # shallow, normal, deep
    db_paths: Optional[Dict[str, str]]   # Database paths for data collection


# ============ Context Factory Functions ============

def create_agent_context(
    chat_user_ref: str = None,
    chat_session_id: str = None,
    db_user_id: int = None,
    db_session_id: int = None,
    llm_context: LLMContext = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create AgentContext with required fields and optional values

    Args:
        chat_user_ref: Chatbot user reference (auto-generated if not provided)
        chat_session_id: Chatbot session ID (auto-generated if not provided)
        db_user_id: Database user ID (optional)
        db_session_id: Database session ID (optional)
        **kwargs: Optional context fields

    Returns:
        Context dictionary ready for LangGraph
    """
    # Auto-generate chatbot identifiers if not provided
    if not chat_user_ref:
        chat_user_ref = f"user_{uuid.uuid4().hex[:12]}"
    if not chat_session_id:
        chat_session_id = f"session_{uuid.uuid4().hex[:12]}"

    # Start with required fields
    context = {
        # Chatbot system identifiers
        "chat_user_ref": chat_user_ref,
        "chat_session_id": chat_session_id,
        "chat_thread_id": kwargs.get("chat_thread_id") or f"thread_{uuid.uuid4().hex[:8]}",

        # Database references (optional)
        "db_user_id": db_user_id,
        "db_session_id": db_session_id,

        # Runtime metadata
        "request_id": kwargs.get("request_id") or f"req_{uuid.uuid4().hex[:8]}",
        "timestamp": kwargs.get("timestamp") or datetime.now().isoformat(),
        "original_query": kwargs.get("original_query"),

        # Settings
        "api_keys": kwargs.get("api_keys", {}),
        "language": kwargs.get("language", "ko"),
        "debug_mode": kwargs.get("debug_mode", False),
        "trace_enabled": kwargs.get("trace_enabled", False),

        # LLM Configuration
        "llm_context": llm_context or create_default_llm_context(),
    }

    # Remove None values for cleaner context
    return {k: v for k, v in context.items() if v is not None}


def create_agent_context_from_db_user(
    db_user_id: int,
    db_session_id: int = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create AgentContext starting from database user

    Args:
        db_user_id: Database user ID
        db_session_id: Database session ID (optional, will create new if not provided)
        **kwargs: Additional context fields

    Returns:
        Context with both chat and DB identifiers
    """
    # Generate chat identifiers linked to DB user
    chat_user_ref = f"dbuser_{db_user_id}_{uuid.uuid4().hex[:8]}"
    chat_session_id = f"dbsession_{db_session_id or 'new'}_{uuid.uuid4().hex[:8]}"

    return create_agent_context(
        chat_user_ref=chat_user_ref,
        chat_session_id=chat_session_id,
        db_user_id=db_user_id,
        db_session_id=db_session_id,
        **kwargs
    )


def create_subgraph_context(
    parent_context: Dict[str, Any],
    parent_agent: str,
    subgraph_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create context for subgraphs (filtered subset of parent context)

    Args:
        parent_context: Parent agent's context
        parent_agent: Parent agent name
        subgraph_name: Subgraph name
        **kwargs: Additional subgraph-specific parameters

    Returns:
        Filtered context for subgraph
    """
    context = {
        # Chatbot identifiers from parent
        "chat_user_ref": parent_context["chat_user_ref"],
        "chat_session_id": parent_context["chat_session_id"],
        "chat_thread_id": parent_context.get("chat_thread_id"),

        # Database references from parent
        "db_user_id": parent_context.get("db_user_id"),
        "db_session_id": parent_context.get("db_session_id"),

        # Optional fields from parent
        "request_id": parent_context.get("request_id"),
        "language": parent_context.get("language", "ko"),
        "debug_mode": parent_context.get("debug_mode", False),

        # Subgraph identification
        "parent_agent": parent_agent,
        "subgraph_name": subgraph_name,

        # Subgraph-specific parameters
        "suggested_tools": kwargs.get("suggested_tools", []),
        "analysis_depth": kwargs.get("analysis_depth", "normal"),
        "db_paths": kwargs.get("db_paths", {}),
    }

    # Remove None values for cleaner context
    return {k: v for k, v in context.items() if v is not None}


def create_default_llm_context() -> LLMContext:
    """
    Create default LLM context from Config

    Config가 이미 .env를 로드했으므로 Config에서 값을 가져옴

    Returns:
        LLMContext with default settings
    """
    from app.service_agent.foundation.config import Config

    return LLMContext(
        provider=Config.LLM_DEFAULTS.get("provider", "openai"),
        api_key=Config.LLM_DEFAULTS.get("api_key"),
        organization=Config.LLM_DEFAULTS.get("organization"),
    )


def create_llm_context_with_overrides(
    base_context: LLMContext = None,
    **overrides
) -> LLMContext:
    """
    Create LLM context with overrides

    Args:
        base_context: Base context to start from (optional)
        **overrides: Field overrides

    Returns:
        New LLMContext with overrides applied
    """
    base = base_context or create_default_llm_context()

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(base, key):
            setattr(base, key, value)

    return base


def extract_api_keys_from_env() -> Dict[str, str]:
    """
    Extract API keys from environment variables

    Returns:
        Dictionary of API keys
    """
    api_keys = {}

    # Common API key patterns
    key_patterns = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]

    for key in key_patterns:
        value = os.getenv(key)
        if value:
            # Convert to lowercase key for consistency
            api_keys[key.lower()] = value

    return api_keys


def validate_context(context: Dict[str, Any]) -> bool:
    """
    Validate context has required fields

    Args:
        context: Context dictionary

    Returns:
        True if valid, raises ValueError if not
    """
    required_fields = ["chat_user_ref", "chat_session_id"]

    for field in required_fields:
        if field not in context:
            raise ValueError(f"Missing required context field: {field}")

    # Check type consistency
    if "db_user_id" in context and context["db_user_id"] is not None:
        if not isinstance(context["db_user_id"], int):
            raise ValueError(f"db_user_id must be integer, got {type(context['db_user_id'])}")

    if "db_session_id" in context and context["db_session_id"] is not None:
        if not isinstance(context["db_session_id"], int):
            raise ValueError(f"db_session_id must be integer, got {type(context['db_session_id'])}")

    return True