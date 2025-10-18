from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
 
# Sync Engine (기존 코드 호환성)
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Session = SessionLocal  # 하위 호환성을 위해 유지

# Async Engine (SessionManager용) - psycopg3 async driver
async_database_url = settings.DATABASE_URL.replace('postgresql+psycopg://', 'postgresql+psycopg_async://')
async_engine = create_async_engine(async_database_url, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()

def get_db():
    """Sync database session (기존 코드용)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Async database session (SessionManager용)"""
    async with AsyncSessionLocal() as session:
        yield session
