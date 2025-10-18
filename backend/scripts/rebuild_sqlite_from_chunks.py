"""
청크 파일에서 SQLite 메타데이터 DB 재생성
FAISS와 동일한 1,700개 데이터로 재생성
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import json
import sqlite3
from datetime import datetime

# Paths
CHUNKED_DIR = backend_dir / "data" / "storage" / "legal_info" / "chunked"
SQLITE_DB_PATH = backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db"
SCHEMA_FILE = backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "schema.sql"

def load_all_chunks():
    """청크 파일들 로드 (FAISS와 동일)"""
    all_chunks = []

    category_folders = [
        "1_공통 매매_임대차",
        "2_임대차_전세_월세",
        "3_공급_및_관리_매매_분양",
        "4_기타"
    ]

    for category in category_folders:
        category_path = CHUNKED_DIR / category
        if not category_path.exists():
            continue

        for json_file in category_path.glob("*_chunked.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 파일명에서 법률명 추출
                law_title = json_file.stem.replace("_chunked", "")

                # chunks 배열 처리
                if isinstance(data, dict) and "chunks" in data:
                    chunks = data["chunks"]
                elif isinstance(data, list):
                    chunks = data
                else:
                    print(f"⚠️  알 수 없는 형식: {json_file.name}")
                    continue

                for chunk in chunks:
                    chunk["law_title"] = law_title
                    chunk["category"] = category
                    chunk["source_file"] = json_file.name
                    all_chunks.append(chunk)

                print(f"   ✅ {json_file.name}: {len(chunks)}개 청크")

            except Exception as e:
                print(f"   ❌ {json_file.name} 로드 실패: {e}")

    return all_chunks


def rebuild_sqlite():
    """SQLite 메타데이터 DB 재생성"""

    print("=" * 80)
    print("SQLite 법률 메타데이터 DB 재생성 (청크 파일 기반)")
    print("=" * 80)

    # 1. 청크 파일 로드
    print(f"\n[1/5] 청크 파일 로드 중... {CHUNKED_DIR}")
    chunks = load_all_chunks()
    print(f"   ✅ 총 {len(chunks)}개 청크 로드 완료")

    if len(chunks) == 0:
        print("   ❌ 청크 파일 없음!")
        return

    # 2. 기존 DB 백업 및 삭제
    print(f"\n[2/5] 기존 DB 백업 및 삭제 중...")
    if SQLITE_DB_PATH.exists():
        backup_path = SQLITE_DB_PATH.parent / f"legal_metadata_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        shutil.copy(SQLITE_DB_PATH, backup_path)
        print(f"   ✅ 백업 생성: {backup_path.name}")

        SQLITE_DB_PATH.unlink()
        print(f"   ✅ 기존 DB 삭제")

    # 3. DB 생성 및 스키마 적용
    print(f"\n[3/5] 새 DB 생성 및 스키마 적용 중...")
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    cursor = conn.cursor()

    # 스키마 적용
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    print(f"   ✅ 스키마 적용 완료")

    # 4. 법령별로 그룹화
    print(f"\n[4/5] 데이터 처리 중...")

    from collections import defaultdict
    laws_dict = defaultdict(list)

    for chunk in chunks:
        law_title = chunk.get("law_title", "")
        laws_dict[law_title].append(chunk)

    print(f"   ✅ 총 {len(laws_dict)}개 법령")

    # 5. DB에 데이터 삽입
    print(f"\n[5/5] DB에 데이터 삽입 중...")

    total_articles = 0

    for law_title, law_chunks in laws_dict.items():
        # metadata에서 정보 추출
        first_chunk_meta = law_chunks[0].get("metadata", {})

        # doc_type 결정
        if "용어" in law_title:
            doc_type = "용어집"
        elif "규칙" in law_title:
            if "대법원" in law_title:
                doc_type = "대법원규칙"
            else:
                doc_type = "시행규칙"
        elif "시행령" in law_title:
            doc_type = "시행령"
        elif "법률" in law_title or "법(" in law_title:
            doc_type = "법률"
        else:
            doc_type = "기타"

        # 법령 정보 추출
        category = law_chunks[0].get("category", "")
        source_file = law_chunks[0].get("source_file", "")

        # 법령번호 추출 (파일명에서)
        import re
        number_match = re.search(r'제(\d+)호', law_title)
        law_number = f"제{number_match.group(1)}호" if number_match else None

        # 시행일 추출
        date_match = re.search(r'(\d{8})', law_title)
        enforcement_date = None
        if date_match:
            date_str = date_match.group(1)
            enforcement_date = f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"

        # laws 테이블에 삽입
        cursor.execute(
            """
            INSERT INTO laws (doc_type, title, number, enforcement_date, category,
                             total_articles, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_type, law_title, law_number, enforcement_date, category,
             len(law_chunks), source_file)
        )

        law_id = cursor.lastrowid

        # articles 테이블에 삽입
        article_counter = 0
        seen_chunk_ids = set()  # 중복 chunk_id 방지

        for chunk in law_chunks:
            chunk_metadata = chunk.get("metadata", {})

            article_number = chunk_metadata.get("article_number", "")
            article_title = chunk_metadata.get("article_title", "")
            chapter = chunk_metadata.get("chapter", "")
            section = chunk_metadata.get("section", "")

            # chunk_id 추출 (FAISS와 매칭용, 고유성 보장용)
            chunk_id = chunk.get("id", "")

            # 중복 chunk_id 스킵 (원본 청크 파일의 중복 데이터)
            if chunk_id in seen_chunk_ids:
                print(f"      ⚠️  중복 스킵: chunk_id={chunk_id}")
                continue

            seen_chunk_ids.add(chunk_id)
            chunk_ids = json.dumps([chunk_id]) if chunk_id else None

            # article_number가 없는 경우 (용어집 등) chunk_id 사용
            if not article_number:
                article_number = chunk_id if chunk_id else f"item_{article_counter}"
            # else 블록 제거: article_number는 원본 그대로 사용 (예: "제1조")
            # 고유성은 chunk_ids 필드가 보장 (본문/부칙 구분 가능)

            # 특수 플래그 판단
            content = chunk.get("text", "")
            is_tenant_protection = 1 if any(term in content for term in ["임차인", "전세", "보증금"]) else 0
            is_tax_related = 1 if any(term in content for term in ["세금", "과세", "조세"]) else 0
            is_delegation = 1 if "위임" in content or "정하는 바에 따라" in content else 0
            is_penalty_related = 1 if any(term in content for term in ["벌칙", "벌금", "징역"]) else 0

            # 전체 메타데이터 JSON
            metadata_json = json.dumps(chunk_metadata, ensure_ascii=False)

            cursor.execute(
                """
                INSERT INTO articles (law_id, article_number, article_title, chapter, section,
                                     is_deleted, is_tenant_protection, is_tax_related,
                                     is_delegation, is_penalty_related, chunk_ids, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (law_id, article_number, article_title, chapter, section,
                 0, is_tenant_protection, is_tax_related, is_delegation, is_penalty_related,
                 chunk_ids, metadata_json)
            )

            total_articles += 1
            article_counter += 1

        print(f"   ✅ {law_title[:50]:50s}: {len(law_chunks):3d}개 조항")

    conn.commit()
    conn.close()

    print(f"\n{'='*80}")
    print(f"✅ SQLite 메타데이터 DB 재생성 완료!")
    print(f"   - 총 법령: {len(laws_dict)}개")
    print(f"   - 총 조항: {total_articles}개")
    print(f"   - DB 파일: {SQLITE_DB_PATH}")
    print(f"{'='*80}\n")

    # 검증
    print("검증 중...")
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM laws")
    law_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM articles WHERE is_deleted = 0")
    article_count = cursor.fetchone()[0]

    cursor.execute("SELECT doc_type, COUNT(*) FROM laws GROUP BY doc_type")
    doc_types = cursor.fetchall()

    print(f"✅ 법령 수: {law_count}개")
    print(f"✅ 조항 수: {article_count}개")
    print(f"\n문서 타입별 분포:")
    for doc_type, count in doc_types:
        print(f"   - {doc_type:15s}: {count:2d}개")

    # 샘플 조회
    print(f"\n샘플 조회 (첫 번째 법령):")
    cursor.execute(
        """
        SELECT l.title, a.article_number, a.article_title
        FROM articles a
        JOIN laws l ON a.law_id = l.law_id
        WHERE a.is_deleted = 0
        LIMIT 3
        """
    )
    for title, article_num, article_title in cursor.fetchall():
        print(f"   - [{title[:40]}] {article_num} {article_title}")

    conn.close()


if __name__ == "__main__":
    try:
        rebuild_sqlite()
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
