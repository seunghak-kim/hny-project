"""
데이터베이스 테이블 초기화 스크립트
테이블이 존재하면 모두 삭제하고 다시 생성합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.postgre_db import Base, engine, SessionLocal
from app.models.real_estate import Region, RealEstate, Transaction, NearbyFacility, RealEstateAgent
from app.models.users import User, UserFavorite, LocalAuth, UserProfile, SocialAuth
from app.models.chat import ChatSession, ChatMessage
from app.models.trust import TrustScore


def kill_all_connections():
    """모든 DB 연결 종료"""
    print("🔨 모든 데이터베이스 연결 종료 중...")

    with engine.connect() as conn:
        # 자동 커밋 모드로 전환
        conn.execute(text("COMMIT"))

        # 현재 연결을 제외한 모든 연결 종료
        result = conn.execute(text("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'real_estate'
            AND pid != pg_backend_pid();
        """))
        conn.commit()

    print("✅ 모든 연결 종료 완료")


def drop_all_tables():
    """모든 테이블 삭제 (CASCADE)"""
    print("\n🗑️  기존 테이블 삭제 중...")

    try:
        # 먼저 모든 연결 종료
        kill_all_connections()

        # 직접 DROP TABLE CASCADE 실행
        with engine.connect() as conn:
            # 모든 테이블 목록 가져오기
            result = conn.execute(text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public';
            """))

            tables = [row[0] for row in result]

            if tables:
                print(f"   삭제할 테이블: {len(tables)}개")
                for table in tables:
                    try:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                        conn.commit()
                        print(f"   ✓ {table}")
                    except Exception as e:
                        print(f"   ✗ {table}: {e}")

        print("✅ 모든 테이블 삭제 완료")

    except Exception as e:
        print(f"⚠️  테이블 삭제 중 에러: {e}")
        import traceback
        traceback.print_exc()


def create_all_tables():
    """모든 테이블 생성"""
    print("\n📦 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료\n")

    print("생성된 테이블:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


def init_database(drop_existing=True):
    """
    데이터베이스 초기화

    Args:
        drop_existing: True면 기존 테이블 삭제 후 재생성, False면 생성만
    """
    print("=" * 60)
    print("🚀 데이터베이스 초기화")
    print("=" * 60)

    if drop_existing:
        drop_all_tables()

    create_all_tables()

    print("\n" + "=" * 60)
    print("✅ 데이터베이스 초기화 완료!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='데이터베이스 초기화')
    parser.add_argument('--no-drop', action='store_true',
                        help='기존 테이블을 삭제하지 않고 생성만 시도')
    args = parser.parse_args()

    init_database(drop_existing=not args.no_drop)
