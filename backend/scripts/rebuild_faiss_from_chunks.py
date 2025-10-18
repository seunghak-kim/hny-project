"""
청크 파일에서 FAISS 벡터DB 재생성
기존 청크 JSON 파일들을 읽어서 FAISS 인덱스와 메타데이터 생성
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Paths
CHUNKED_DIR = backend_dir / "data" / "storage" / "legal_info" / "chunked"
FAISS_DIR = backend_dir / "data" / "storage" / "legal_info" / "faiss_db"
MODEL_PATH = backend_dir / "app" / "ml_models" / "KURE_v1"

# 출력 파일
FAISS_INDEX_FILE = FAISS_DIR / "legal_documents.index"
METADATA_FILE = FAISS_DIR / "legal_metadata.pkl"

def load_all_chunks():
    """청크 파일들 로드"""
    all_chunks = []

    # 1_공통, 2_임대차 등 카테고리별 폴더
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

        # 카테고리 폴더 내 모든 JSON 파일
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
                    all_chunks.append(chunk)

                print(f"   ✅ {json_file.name}: {len(chunks)}개 청크")

            except Exception as e:
                print(f"   ❌ {json_file.name} 로드 실패: {e}")

    return all_chunks

def rebuild_faiss():
    """FAISS 벡터DB 재생성"""

    print("=" * 80)
    print("FAISS 법률 벡터DB 재생성 (청크 파일 기반)")
    print("=" * 80)

    # 1. 청크 파일 로드
    print(f"\n[1/4] 청크 파일 로드 중... {CHUNKED_DIR}")
    chunks = load_all_chunks()
    print(f"   ✅ 총 {len(chunks)}개 청크 로드 완료")

    if len(chunks) == 0:
        print("   ❌ 청크 파일 없음!")
        return

    # 2. FAISS 디렉토리 생성
    print(f"\n[2/4] FAISS 디렉토리 준비 중... {FAISS_DIR}")
    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    # 기존 파일 백업 및 삭제
    from datetime import datetime
    import shutil

    if FAISS_INDEX_FILE.exists():
        backup_index = FAISS_DIR / f"legal_documents_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.index"
        shutil.copy(FAISS_INDEX_FILE, backup_index)
        print(f"   ✅ 인덱스 백업: {backup_index.name}")
        FAISS_INDEX_FILE.unlink()

    if METADATA_FILE.exists():
        backup_metadata = FAISS_DIR / f"legal_metadata_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        shutil.copy(METADATA_FILE, backup_metadata)
        print(f"   ✅ 메타데이터 백업: {backup_metadata.name}")
        METADATA_FILE.unlink()

    print(f"   ✅ FAISS 디렉토리 준비 완료")

    # 3. 임베딩 모델 로드
    print(f"\n[3/4] 임베딩 모델 로드 중...")
    if MODEL_PATH.exists():
        print(f"   - 경로: {MODEL_PATH}")
        model = SentenceTransformer(str(MODEL_PATH))
    else:
        print(f"   ⚠️  KURE_v1 없음, 대체 모델 사용: jhgan/ko-sbert-multitask")
        model = SentenceTransformer('jhgan/ko-sbert-multitask')

    # 임베딩 차원 확인
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"   ✅ 임베딩 모델 로드 완료 (차원: {embedding_dim})")

    # 4. 벡터 임베딩 및 FAISS 인덱스 생성
    print(f"\n[4/4] 벡터 임베딩 및 FAISS 인덱스 생성 중...")

    documents = []
    metadatas = []
    all_embeddings = []
    seen_chunk_ids = set()  # 중복 chunk_id 방지
    skipped_count = 0

    batch_size = 100

    for i in tqdm(range(0, len(chunks), batch_size), desc="Embedding"):
        batch = chunks[i:i+batch_size]
        batch_docs = []

        for chunk in batch:
            # chunk_id 추출 및 중복 체크
            chunk_id = chunk.get("id", "")
            law_title = chunk.get("law_title", "")

            # 법령별로 고유한 키 생성 (law_title + chunk_id)
            # 예: "공인중개사법(법률)(제19841호)(20241227)_article_1"
            unique_key = f"{law_title}_{chunk_id}"

            # 중복 chunk 스킵 (같은 법령 + 같은 chunk_id)
            if unique_key in seen_chunk_ids:
                skipped_count += 1
                continue

            seen_chunk_ids.add(unique_key)

            # 문서 내용
            content = chunk.get("content", "")
            if not content:
                content = chunk.get("text", "")

            if not content:
                continue

            # 청크 파일의 metadata 필드에서 정보 추출
            chunk_metadata = chunk.get("metadata", {})
            article_title = chunk_metadata.get("article_title", "")
            chapter = chunk_metadata.get("chapter", "")

            # ⭐ 제목 + 장 포함 임베딩 내용 생성 (검색 품질 개선)
            enhanced_content = content
            if article_title or chapter:
                parts = []
                if chapter:
                    parts.append(f"[{chapter}]")
                if article_title:
                    parts.append(article_title)

                if parts:
                    enhanced_content = f"{' '.join(parts)}\n{content}"

            # 메타데이터
            metadata = {
                "chunk_id": chunk.get("id", f"chunk_{len(metadatas)}"),
                "law_title": chunk.get("law_title", ""),
                "article_number": chunk_metadata.get("article_number", ""),
                "article_title": article_title,
                "doc_type": chunk.get("doc_type", "법률"),
                "category": chunk.get("category", ""),
                "chapter": chapter,
                "section": chunk_metadata.get("section", ""),
                "content": content  # 원본 텍스트 유지
            }

            documents.append(enhanced_content)  # 제목+장 포함 임베딩
            metadatas.append(metadata)
            batch_docs.append(enhanced_content)  # 제목+장 포함 임베딩

        if batch_docs:
            # 배치 임베딩 생성
            embeddings = model.encode(batch_docs, convert_to_tensor=False)
            all_embeddings.append(embeddings)

    # 모든 임베딩 합치기
    print("\n   - 임베딩 배열 통합 중...")
    all_embeddings = np.vstack(all_embeddings).astype('float32')
    print(f"   ✅ 임베딩 생성 완료: {all_embeddings.shape}")

    # FAISS 인덱스 생성 (L2 distance)
    print("\n   - FAISS 인덱스 생성 중...")
    index = faiss.IndexFlatL2(embedding_dim)
    index.add(all_embeddings)
    print(f"   ✅ FAISS 인덱스 생성 완료: {index.ntotal}개 벡터")

    # 인덱스 저장
    print(f"\n   - 인덱스 파일 저장 중: {FAISS_INDEX_FILE}")
    faiss.write_index(index, str(FAISS_INDEX_FILE))
    print(f"   ✅ 인덱스 저장 완료")

    # 메타데이터 저장 (pickle)
    print(f"\n   - 메타데이터 저장 중: {METADATA_FILE}")
    with open(METADATA_FILE, 'wb') as f:
        pickle.dump(metadatas, f)
    print(f"   ✅ 메타데이터 저장 완료")

    print(f"\n{'='*80}")
    print(f"✅ FAISS 벡터DB 재생성 완료!")
    print(f"   - 총 청크 로드: {len(chunks)}개")
    print(f"   - 중복 제거: {skipped_count}개")
    print(f"   - 고유 벡터: {len(metadatas)}개")
    print(f"   - 벡터 차원: {embedding_dim}")
    print(f"   - 인덱스 파일: {FAISS_INDEX_FILE}")
    print(f"   - 메타데이터 파일: {METADATA_FILE}")
    print(f"{'='*80}\n")

    # 검증
    print("검증 중...")
    print(f"✅ FAISS 인덱스 벡터 수: {index.ntotal}개")
    print(f"✅ 메타데이터 수: {len(metadatas)}개")

    # 샘플 검색 테스트
    print("\n샘플 검색 테스트:")
    query = "전세금 인상률"
    query_embedding = model.encode([query], convert_to_tensor=False).astype('float32')

    distances, indices = index.search(query_embedding, 3)

    print(f"✅ 검색 결과 (쿼리: '{query}'):")
    for i, idx in enumerate(indices[0]):
        if idx < len(metadatas):
            meta = metadatas[idx]
            print(f"   {i+1}. [{meta['law_title']}] {meta['content'][:100]}...")
            print(f"      거리: {distances[0][i]:.4f}")

if __name__ == "__main__":
    try:
        rebuild_faiss()
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
