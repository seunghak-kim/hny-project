"""
채팅 관련 테이블만 초기화하는 스크립트
부동산 데이터는 유지하고, 채팅/메모리 테이블만 재생성합니다.

생성되는 테이블:
- chat_sessions
- chat_messages
- checkpoints (LangGraph)
- checkpoint_blobs (LangGraph)
- checkpoint_writes (LangGraph)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.postgre_db import Base, engine
from app.models.chat import ChatSession, ChatMessage
import asyncio


async def drop_chat_tables():
    """채팅 관련 테이블만 삭제 (부동산 테이블 유지)"""
    print("\n🗑️  채팅 관련 테이블 삭제 중...")

    chat_tables = [
        'chat_messages',      # 메시지 (외래키 먼저 삭제)
        'chat_sessions',      # 세션
        'checkpoint_writes',  # LangGraph checkpoint writes
        'checkpoint_blobs',   # LangGraph checkpoint blobs
        'checkpoints'         # LangGraph checkpoints
    ]

    try:
        with engine.connect() as conn:
            for table in chat_tables:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    conn.commit()
                    print(f"   ✓ {table} 삭제됨")
                except Exception as e:
                    print(f"   ✗ {table}: {e}")

        print("✅ 채팅 테이블 삭제 완료")

    except Exception as e:
        print(f"⚠️  테이블 삭제 중 에러: {e}")
        import traceback
        traceback.print_exc()


def create_chat_tables():
    """채팅 관련 SQLAlchemy 테이블만 생성"""
    print("\n📦 채팅 테이블 생성 중...")

    # chat_sessions와 chat_messages만 생성
    tables_to_create = [ChatSession.__table__, ChatMessage.__table__]

    for table in tables_to_create:
        try:
            table.create(bind=engine, checkfirst=True)
            print(f"   ✓ {table.name} 생성됨")
        except Exception as e:
            print(f"   ✗ {table.name}: {e}")

    print("✅ 채팅 SQLAlchemy 테이블 생성 완료")


async def create_checkpoint_tables():
    """LangGraph checkpoint 테이블 생성 (AsyncPostgresSaver.setup() 사용)"""
    print("\n📦 LangGraph checkpoint 테이블 생성 중...")

    try:
        from app.service_agent.foundation.checkpointer import create_checkpointer

        # AsyncPostgresSaver 인스턴스 생성 및 setup 호출
        checkpointer = await create_checkpointer()
        print("   ✓ checkpoints")
        print("   ✓ checkpoint_blobs")
        print("   ✓ checkpoint_writes")
        print("✅ LangGraph checkpoint 테이블 생성 완료")

    except Exception as e:
        print(f"⚠️  Checkpoint 테이블 생성 중 에러: {e}")
        import traceback
        traceback.print_exc()


async def init_chat_database():
    """
    채팅 데이터베이스 초기화

    부동산 테이블은 유지하고 채팅 관련 테이블만 재생성합니다.
    """
    print("=" * 60)
    print("🚀 채팅 데이터베이스 초기화")
    print("=" * 60)

    # 1. 기존 채팅 테이블 삭제
    await drop_chat_tables()

    # 2. 채팅 SQLAlchemy 테이블 생성
    create_chat_tables()

    # 3. LangGraph checkpoint 테이블 생성
    await create_checkpoint_tables()

    print("\n" + "=" * 60)
    print("✅ 채팅 데이터베이스 초기화 완료!")
    print("=" * 60)
    print("\n📊 생성된 테이블:")
    print("   - chat_sessions")
    print("   - chat_messages")
    print("   - checkpoints")
    print("   - checkpoint_blobs")
    print("   - checkpoint_writes")
    print("\n💡 부동산 데이터는 유지되었습니다.")


if __name__ == "__main__":
    asyncio.run(init_chat_database())
