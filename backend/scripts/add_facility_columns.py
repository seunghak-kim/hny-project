"""
주변 시설 정보 컬럼 추가 스크립트
apartments, houses, villas, officetels 테이블에 nearby_subway_stations, nearby_schools, nearby_marts 컬럼 추가
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.postgre_db import engine

def add_facility_columns():
    """주변 시설 정보 컬럼 추가"""
    print("=" * 80)
    print("주변 시설 정보 컬럼 추가")
    print("=" * 80)

    tables = ['apartments', 'houses', 'villas', 'officetels']
    columns = [
        ('nearby_subway_stations', 'TEXT', '1km 이내 지하철역 정보(JSON)'),
        ('nearby_schools', 'TEXT', '인근 초중고 정보(JSON)'),
        ('nearby_marts', 'TEXT', '인근 마트 정보(JSON)')
    ]

    with engine.connect() as conn:
        for table in tables:
            print(f"\n[{table}] 테이블 처리 중...")

            for col_name, col_type, comment in columns:
                try:
                    # 컬럼이 이미 존재하는지 확인
                    result = conn.execute(text(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = '{table}'
                        AND column_name = '{col_name}'
                    """))

                    if result.fetchone():
                        print(f"  ✓ {col_name} - 이미 존재함")
                    else:
                        # 컬럼 추가
                        conn.execute(text(f"""
                            ALTER TABLE {table}
                            ADD COLUMN {col_name} {col_type}
                        """))

                        # 코멘트 추가
                        conn.execute(text(f"""
                            COMMENT ON COLUMN {table}.{col_name} IS '{comment}'
                        """))

                        conn.commit()
                        print(f"  + {col_name} - 추가 완료")

                except Exception as e:
                    print(f"  ✗ {col_name} - 오류: {e}")
                    conn.rollback()

    print("\n" + "=" * 80)
    print("✅ 컬럼 추가 완료!")
    print("=" * 80)

if __name__ == "__main__":
    add_facility_columns()
