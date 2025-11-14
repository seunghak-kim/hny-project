"""
System Configuration
Static settings that don't change during runtime
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent.parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """
    System-wide static configuration
    These values are read at startup and don't change during execution
    """

    # ============ System Paths ============
    BASE_DIR = Path(__file__).parent.parent.parent.parent  # Project root
    DB_DIR = BASE_DIR / "database" / "storage"
    CHECKPOINT_DIR = BASE_DIR / "data" / "system" / "checkpoints"  # Changed to specified path
    AGENT_LOGGING_DIR = BASE_DIR / "data" / "system" / "agent_logging"  # LLM decision logging
    LOG_DIR = BASE_DIR / "logs"

    # Create directories if they don't exist
    for directory in [CHECKPOINT_DIR, AGENT_LOGGING_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    # ============ Database Paths (Active) ============
    DATABASES = {
        "real_estate_listings": DB_DIR / "real_estate" / "listings.db",      # Property listings DB
        "regional_info": DB_DIR / "real_estate" / "regional_stats.db",       # Regional statistics DB
        "user_profiles": DB_DIR / "user" / "profiles.db",                    # User profiles DB
        "user_data": DB_DIR / "user" / "data.db",                            # User data DB
        # Legal information databases
        "legal_metadata": BASE_DIR / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db",
    }

    # ============ Legal Search Paths ============
    LEGAL_INFO_BASE = BASE_DIR / "data" / "storage" / "legal_info"
    LEGAL_PATHS = {
        "faiss_db": LEGAL_INFO_BASE / "faiss_db",                            # FAISS vector database
        "sqlite_db": LEGAL_INFO_BASE / "sqlite_db" / "legal_metadata.db",   # SQLite metadata
        "embedding_model": BASE_DIR / "app" / "ml_models" / "KURE_v1",  # Korean Legal Embedding Model
    }

    # ============ Model Settings (Active) ============
    DEFAULT_MODELS = {
        "intent": "gpt-4o-mini",      # Fast for intent analysis
        "planning": "gpt-4o",          # Accurate for planning
    }

    DEFAULT_MODEL_PARAMS = {
        "intent": {"temperature": 0.3, "max_tokens": 500},
        "planning": {"temperature": 0.3, "max_tokens": 2000},
    }

    # ============ System Timeouts (Active) ============
    TIMEOUTS = {
        "agent": 30,           # Individual agent timeout (seconds)
        "llm": 20,             # LLM call timeout
    }

    # ============ System Limits ============
    LIMITS = {
        "max_recursion": 25,
        "max_retries": 3,
        "max_message_length": 10000,
        "max_sql_results": 1000,
    }

    # ============ Execution Settings (Active) ============
    EXECUTION = {
        "enable_checkpointing": True,  # Checkpointing enabled
    }

    # ============ Logging Settings ============
    LOGGING = {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "file_rotation": "daily",
        "max_log_size": "100MB",
        "backup_count": 7
    }

    # ============ Feature Flags (Active) ============
    FEATURES = {
        "enable_llm_planning": True,  # LLM planning enabled
    }

    # ============ LLM Configuration (LangGraph 0.6+) ============
    LLM_DEFAULTS = {
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "organization": os.getenv("OPENAI_ORG_ID"),
        "models": {
            # Cognitive prompts
            "intent_analysis": "gpt-4o-mini",      # Intent analysis
            "plan_generation": "gpt-4o-mini",      # Execution planning

            # Execution prompts
            "keyword_extraction": "gpt-4o-mini",   # Keyword extraction for search
            "insight_generation": "gpt-4o",        # Insight generation from analysis
            "response_synthesis": "gpt-4o-mini",   # Response synthesis

            # Common prompts
            "error_response": "gpt-4o-mini",       # Error response generation

            # Legacy mappings (backward compatibility)
            "intent": "gpt-4o-mini",
            "planning": "gpt-4o-mini",
            "search": "gpt-4o-mini",
            "analysis": "gpt-4o"
        },
        "default_params": {
            "temperature": 0.3,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        },
        "retry": {
            "max_attempts": 3,
            "backoff_seconds": 1.0
        }
    }

    # ============ Helper Methods ============

    @classmethod
    def get_database_path(cls, db_name: str) -> Path:
        """Get database path by name"""
        return cls.DATABASES.get(db_name, cls.DB_DIR / f"{db_name}.db")

    @classmethod
    def get_checkpoint_path(cls, agent_name: str, session_id: str) -> Path:
        """Get checkpoint database path for an agent session"""
        checkpoint_dir = cls.CHECKPOINT_DIR / agent_name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / f"{session_id}.db"

    @classmethod
    def get_model_config(cls, model_type: str) -> Dict[str, Any]:
        """Get model configuration by type"""
        return {
            "model": cls.DEFAULT_MODELS.get(model_type, "gpt-4o-mini"),
            **cls.DEFAULT_MODEL_PARAMS.get(model_type, {})
        }

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        issues = []

        # Check database paths exist
        for name, path in cls.DATABASES.items():
            if not path.parent.exists():
                issues.append(f"Database directory missing: {path.parent}")

        # Check required directories
        for directory in [cls.CHECKPOINT_DIR, cls.LOG_DIR]:
            if not directory.exists():
                issues.append(f"Required directory missing: {directory}")

        if issues:
            print("Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        return True

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "databases": {k: str(v) for k, v in cls.DATABASES.items()},
            "models": cls.DEFAULT_MODELS,
            "timeouts": cls.TIMEOUTS,
            "limits": cls.LIMITS,
            "features": cls.FEATURES
        }