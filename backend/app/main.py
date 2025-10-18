import logging
import logging.handlers
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.service_agent.foundation.config import Config


# ============ Logging Configuration ============
def setup_logging():
    """Configure structured logging for the application"""

    # Ensure log directory exists
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    log_format = Config.LOGGING.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    date_format = Config.LOGGING.get("date_format", "%Y-%m-%d %H:%M:%S")
    log_level_str = Config.LOGGING.get("level", "INFO")
    log_level = getattr(logging, log_level_str.upper())

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # File handler (rotating)
    log_file = Config.LOG_DIR / "app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=7
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress third-party library logs (reduce noise)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)  # SQLite checkpointing
    logging.getLogger("httpx").setLevel(logging.WARNING)  # HTTP client (OpenAI API)
    logging.getLogger("openai").setLevel(logging.WARNING)  # OpenAI SDK
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Access logs
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # App-specific logs (keep detailed)
    logging.getLogger("app.service_agent").setLevel(logging.INFO)
    logging.getLogger("app.api").setLevel(logging.INFO)

    logging.info("=" * 80)
    logging.info("Logging configured successfully")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log file: {log_file}")
    logging.info("=" * 80)


# Setup logging before app initialization
setup_logging()


# ============ Application Lifespan (Startup/Shutdown) ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management
    - Startup: Supervisor pre-warming for faster first response
    - Shutdown: Cleanup resources
    """
    # Startup: Pre-warm TeamBasedSupervisor
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("🚀 Application Startup: Pre-warming TeamBasedSupervisor...")

    try:
        from app.api.chat_api import get_supervisor
        await get_supervisor(enable_checkpointing=True)
        logger.info("✅ TeamBasedSupervisor pre-warmed successfully")
        logger.info("   - First request will skip Supervisor initialization (~2.2초 단축)")
        logger.info("   - Expected first response time: ~5초 (vs 7초 without pre-warming)")
    except Exception as e:
        logger.warning(f"⚠️ Pre-warming failed (will initialize on first request): {e}")

    logger.info("=" * 80)

    yield

    # Shutdown: Cleanup
    logger.info("=" * 80)
    logger.info("🛑 Application Shutdown: Cleaning up resources...")

    try:
        from app.api.chat_api import _supervisor_instance
        if _supervisor_instance and _supervisor_instance.checkpointer:
            await _supervisor_instance._checkpoint_cm.__aexit__(None, None, None)
            logger.info("✅ Checkpointer connection closed")
    except Exception as e:
        logger.warning(f"⚠️ Cleanup warning: {e}")

    logger.info("=" * 80)


app = FastAPI(
    title="Chatbot App API",
    description="부동산 AI 챗봇 <도와줘 홈즈냥즈>",
    version="0.0.1",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.chat_api import router as chat_router
from app.api.error_handlers import register_error_handlers

# Include routers
app.include_router(chat_router)

# Register error handlers
register_error_handlers(app)

@app.get("/")
async def root():
    return {"message": "홈즈냥즈 API Server Running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
