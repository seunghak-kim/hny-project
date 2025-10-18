import re
import json
import os

def chunk_real_estate_glossary_to_json(
    input_path="부동산_용어_95가지.txt",
    output_path=None
):
    """
    부동산 용어 95가지를 용어 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 법률 문서가 아닌 용어집 - 6개 섹션, 95개 용어
    법률 구조(조/항/호)가 아닌 섹션별 용어 정의로 구성
    """

    # 출력 파일명 자동 생성
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{base_name}_chunked.json"

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"오류: '{input_path}' 파일을 찾을 수 없습니다.")
        return
    except UnicodeDecodeError:
        try:
            with open(input_path, 'r', encoding='cp949') as f:
                content = f.read()
        except:
            print(f"오류: '{input_path}' 파일의 인코딩을 확인할 수 없습니다.")
            return

    chunks = []

    # BOM 제거
    content = content.replace('\ufeff', '')

    # 제목 추출
    title_match = re.search(r'^([^\n]+용어[^\n]*)', content, re.MULTILINE)
    glossary_title = title_match.group(1).strip() if title_match else "부동산 용어 95가지"

    # 섹션(카테고리) 정보 추출 및 위치 매핑
    sections = {}
    section_pattern = r'^([가-힣\s]+용어|재개발 및 재건축|그 외 부동산 기초 용어|부동산 대출 관련 용어|건축 용어|신조어 및 줄임말)$'

    for match in re.finditer(section_pattern, content, re.MULTILINE):
        section_title = match.group(1).strip()
        sections[match.start()] = section_title

    print(f"발견된 섹션: {list(sections.values())}")

    # 용어 항목 패턴: "번호. 용어명: 설명"
    term_pattern = r'^(\d+)\.\s*([^:]+):\s*(.+?)(?=^\d+\.\s|\Z)'

    # 모든 용어 찾기 (DOTALL 모드로 여러 줄에 걸친 설명 처리)
    term_matches = list(re.finditer(term_pattern, content, re.MULTILINE | re.DOTALL))

    if not term_matches:
        print("경고: 용어를 찾을 수 없습니다.")
        return

    print(f"총 {len(term_matches)}개의 용어를 발견했습니다.")

    # 섹션별 용어 수 카운트를 위한 딕셔너리
    section_term_count = {}

    # 각 용어 처리
    for i, match in enumerate(term_matches):
        term_number = match.group(1)  # 번호
        term_name = match.group(2).strip()  # 용어명
        term_definition = match.group(3).strip()  # 설명

        # 정의에서 불필요한 줄바꿈 정리
        term_definition = re.sub(r'\n+', ' ', term_definition)
        term_definition = re.sub(r'\s+', ' ', term_definition)
        term_definition = term_definition.strip()

        # 현재 용어가 속한 섹션 찾기
        current_section = ""
        term_pos = match.start()
        sorted_section_pos = sorted([pos for pos in sections.keys() if pos < term_pos], reverse=True)
        if sorted_section_pos:
            current_section = sections[sorted_section_pos[0]]
            # 섹션별 용어 수 카운트
            if current_section not in section_term_count:
                section_term_count[current_section] = 0
            section_term_count[current_section] += 1

        # ID 생성 (섹션 약어 + 번호)
        section_abbrev = {
            "매매 용어": "sale",
            "임대차 용어": "lease",
            "청약 용어": "subscription",
            "재개발 및 재건축": "redevelopment",
            "그 외 부동산 기초 용어": "basic",
            "부동산 대출 관련 용어": "loan",
            "건축 용어": "architecture",
            "신조어 및 줄임말": "slang"
        }
        section_code = section_abbrev.get(current_section, "unknown")
        chunk_id = f"term_{section_code}_{term_number}"

        # 전체 텍스트 조합
        full_text = f"{term_name}: {term_definition}"

        # 메타데이터 구성
        metadata = {
            "glossary_title": glossary_title,
            "section": current_section,
            "term_number": int(term_number),
            "term_name": term_name,
            "document_type": "glossary"
        }

        # 용어 유형 분류
        if current_section == "매매 용어":
            metadata["term_category"] = "매매거래"
        elif current_section == "임대차 용어":
            metadata["term_category"] = "임대차"
        elif current_section == "청약 용어":
            metadata["term_category"] = "청약분양"
        elif current_section == "재개발 및 재건축":
            metadata["term_category"] = "재개발재건축"
        elif current_section == "그 외 부동산 기초 용어":
            metadata["term_category"] = "기초용어"
        elif current_section == "부동산 대출 관련 용어":
            metadata["term_category"] = "대출금융"
        elif current_section == "건축 용어":
            metadata["term_category"] = "건축"
        elif current_section == "신조어 및 줄임말":
            metadata["term_category"] = "신조어"

        # 약어/줄임말 여부 확인
        if current_section == "신조어 및 줄임말":
            metadata["is_abbreviation"] = True

        # 세금 관련 용어 확인
        if any(keyword in term_name for keyword in ["세", "과세", "비과세"]):
            metadata["is_tax_related"] = True

        # 법적 용어 확인
        if any(keyword in term_definition for keyword in ["법", "규정", "의무", "권리", "계약"]):
            metadata["is_legal_term"] = True

        # 금융 관련 확인
        if any(keyword in term_name for keyword in ["대출", "금리", "원리금", "담보", "LTV", "DTI", "DSR"]):
            metadata["is_financial"] = True

        # 정의 길이
        metadata["definition_length"] = len(term_definition)

        chunk_data = {
            "id": chunk_id,
            "text": full_text,
            "metadata": metadata
        }
        chunks.append(chunk_data)

    # 통계 출력
    try:
        print(f"\n용어집명: {glossary_title}")
        print(f"\n총 {len(chunks)}개 용어 처리 완료")

        # 섹션별 통계
        if section_term_count:
            print(f"\n섹션별 용어 분포:")
            for section, count in section_term_count.items():
                print(f"  {section}: {count}개 용어")

        # 용어 유형별 통계
        category_count = {}
        for chunk in chunks:
            category = chunk['metadata'].get('term_category')
            if category:
                category_count[category] = category_count.get(category, 0) + 1

        if category_count:
            print(f"\n용어 카테고리 분포:")
            for category, count in category_count.items():
                print(f"  {category}: {count}개 용어")

        # 특성별 통계
        abbrev_count = sum(1 for chunk in chunks if chunk['metadata'].get('is_abbreviation'))
        tax_count = sum(1 for chunk in chunks if chunk['metadata'].get('is_tax_related'))
        legal_count = sum(1 for chunk in chunks if chunk['metadata'].get('is_legal_term'))
        financial_count = sum(1 for chunk in chunks if chunk['metadata'].get('is_financial'))

        if abbrev_count or tax_count or legal_count or financial_count:
            print(f"\n용어 특성 통계:")
            if abbrev_count:
                print(f"  약어/줄임말: {abbrev_count}개 용어")
            if tax_count:
                print(f"  세금 관련: {tax_count}개 용어")
            if legal_count:
                print(f"  법률 관련: {legal_count}개 용어")
            if financial_count:
                print(f"  금융 관련: {financial_count}개 용어")

        # 정의 길이 통계
        avg_length = sum(chunk['metadata']['definition_length'] for chunk in chunks) / len(chunks)
        max_length = max(chunk['metadata']['definition_length'] for chunk in chunks)
        min_length = min(chunk['metadata']['definition_length'] for chunk in chunks)

        print(f"\n정의 길이 통계:")
        print(f"  평균: {avg_length:.1f}자")
        print(f"  최대: {max_length}자")
        print(f"  최소: {min_length}자")

    except UnicodeEncodeError:
        print(f"\n[Glossary information processed]")
        print(f"Total {len(chunks)} terms processed.")
    except Exception as e:
        print(f"통계 출력 중 오류 발생: {e}")

    # JSON 파일 저장
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"\nSuccess! '{output_path}' file created.")
    except Exception as e:
        print(f"Error: Failed to save JSON file: {e}")

    return chunks


if __name__ == "__main__":
    chunk_real_estate_glossary_to_json()