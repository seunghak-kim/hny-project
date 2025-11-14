import re
import json
import os

def chunk_housing_law_to_json(
    input_path="주택법(법률)(제20048호)(20240717).txt",
    output_path=None
):
    """
    주택법을 조 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 6개 장(Chapter)과 절(Section) 구분, 129개 조항
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

    # 제목 및 메타데이터 추출
    title_match = re.search(r'^([^\n]+법)\s*\[', content, re.MULTILINE)
    law_title = title_match.group(1).strip() if title_match else "주택법"

    # 시행 정보 추출
    enforcement_match = re.search(r'\[시행\s+([^\]]+)\]', content)
    enforcement_info = enforcement_match.group(1).strip() if enforcement_match else ""

    # 법률 번호 추출
    law_number_match = re.search(r'\[법률\s+제(\d+)호', content)
    law_number = law_number_match.group(1) if law_number_match else ""

    # 장(Chapter) 정보 추출
    chapter_pattern = r'(제\d+장)\s+([^\n]+)'
    chapter_matches = list(re.finditer(chapter_pattern, content))

    # 절(Section) 정보 추출
    section_pattern = r'(제\d+절)\s+([^\n]+)'
    section_matches = list(re.finditer(section_pattern, content))

    # 부칙 위치 찾기
    appendix_positions = []
    appendix_pattern = r'부칙\s*<[^>]+>'
    for match in re.finditer(appendix_pattern, content):
        appendix_positions.append(match.start())

    # 조항을 찾기 위한 정규표현식 (제8조의2 같은 형식 포함)
    article_pattern = r'(제\d+조(?:의\d+)?)\s*\(([^)]+)\)'

    # 모든 조항 찾기
    article_matches = list(re.finditer(article_pattern, content))

    if not article_matches:
        print("경고: 조항을 찾을 수 없습니다.")
        return

    print(f"총 {len(article_matches)}개의 조항을 발견했습니다.")
    print(f"총 {len(chapter_matches)}개의 장을 발견했습니다.")
    print(f"총 {len(section_matches)}개의 절을 발견했습니다.")

    # 각 조항 처리
    for i, match in enumerate(article_matches):
        article_number = match.group(1)  # 제N조 또는 제N조의N
        article_title = match.group(2).strip()  # 괄호 안의 제목
        article_pos = match.start()

        # 현재 조항이 속한 장 찾기
        current_chapter = ""
        current_chapter_title = ""
        for ch_match in chapter_matches:
            if ch_match.start() < article_pos:
                current_chapter = ch_match.group(1)
                current_chapter_title = ch_match.group(2).strip()
            else:
                break

        # 현재 조항이 속한 절 찾기
        current_section = ""
        current_section_title = ""
        for sec_match in section_matches:
            if sec_match.start() < article_pos:
                current_section = sec_match.group(1)
                current_section_title = sec_match.group(2).strip()
            else:
                break

        # 부칙에 속하는지 확인
        in_appendix = False
        appendix_info = ""

        for app_pos in appendix_positions:
            if article_pos > app_pos:
                in_appendix = True
                appendix_match = re.search(r'부칙\s*<([^>]+)>', content[app_pos:app_pos+100])
                if appendix_match:
                    appendix_info = f"부칙 <{appendix_match.group(1)}>"

        # 조항 내용 추출
        content_start = match.end()
        content_end = len(content)

        # 다음 조항 위치
        if i < len(article_matches) - 1:
            content_end = min(content_end, article_matches[i + 1].start())

        # 부칙 위치 확인
        for app_pos in appendix_positions:
            if content_start < app_pos < content_end:
                content_end = app_pos

        article_content = content[content_start:content_end].strip()

        # 불필요한 공백 정리
        article_content = re.sub(r'\n\s*\n+', '\n', article_content)
        article_content = article_content.strip()

        # 벌칙 관련 키워드 확인
        penalty_keywords = ['벌금', '징역', '과태료', '벌칙', '과징금']
        has_penalty = any(keyword in article_content for keyword in penalty_keywords)

        # 타법 참조 추출
        other_law_references = re.findall(r'「[^」]+」', article_content)

        # ID 생성
        chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

        # 전체 텍스트 조합 (장, 절 정보 포함)
        structure_info = ""
        if current_chapter:
            structure_info += f"{current_chapter} {current_chapter_title}"
        if current_section:
            structure_info += f" > {current_section} {current_section_title}"
        if structure_info:
            structure_info += " > "

        full_text = f"{structure_info}{article_number}({article_title}) {article_content}"

        # 메타데이터 구성
        metadata = {
            "law_title": law_title,
            "law_number": f"제{law_number}호" if law_number else "",
            "enforcement_date": enforcement_info,
            "article_number": article_number,
            "article_title": article_title
        }

        # 장 정보 추가
        if current_chapter:
            metadata["chapter"] = current_chapter
            metadata["chapter_title"] = current_chapter_title

        # 절 정보 추가
        if current_section:
            metadata["section"] = current_section
            metadata["section_title"] = current_section_title

        # 부칙인 경우 메타데이터에 추가
        if in_appendix:
            metadata["in_appendix"] = True
            metadata["appendix_info"] = appendix_info

        # 벌칙 관련 조항인지 표시
        if has_penalty:
            metadata["has_penalty"] = True

        # 타법 참조가 있으면 메타데이터에 추가
        if other_law_references:
            metadata["other_law_references"] = list(set(other_law_references))

        # 권한 위임 조항인지 확인
        if "위임" in article_title or "대통령령" in article_content or "국토교통부령" in article_content:
            metadata["is_delegation"] = True

        chunk_data = {
            "id": chunk_id,
            "text": full_text,
            "metadata": metadata
        }
        chunks.append(chunk_data)

    # 통계 출력
    try:
        print(f"\n법률명: {law_title}")
        print(f"법률번호: 제{law_number}호" if law_number else "")
        print(f"시행일: {enforcement_info}")
        print(f"\n총 {len(chunks)}개 조항 처리 완료")

        # 장별 통계
        chapters = {}
        for chunk in chunks:
            chapter = chunk['metadata'].get('chapter', '장 구분 없음')
            chapters[chapter] = chapters.get(chapter, 0) + 1

        print(f"\n장별 조항 수:")
        for chapter, count in sorted(chapters.items()):
            print(f"  {chapter}: {count}개")

        # 특성 통계
        penalty_count = sum(1 for chunk in chunks if chunk['metadata'].get('has_penalty'))
        delegation_count = sum(1 for chunk in chunks if chunk['metadata'].get('is_delegation'))
        law_ref_count = sum(1 for chunk in chunks if chunk['metadata'].get('other_law_references'))

        if penalty_count or delegation_count or law_ref_count:
            print(f"\n조항 특성 통계:")
            if penalty_count:
                print(f"  벌칙 관련 조항: {penalty_count}개")
            if delegation_count:
                print(f"  권한 위임 조항: {delegation_count}개")
            if law_ref_count:
                print(f"  타법 참조 조항: {law_ref_count}개")

    except UnicodeEncodeError:
        print(f"\n[Law information processed]")
        print(f"Total {len(chunks)} articles processed.")

    # JSON 파일 저장
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"\nSuccess! '{output_path}' file created.")
    except Exception as e:
        print(f"Error: Failed to save JSON file: {e}")

    return chunks


if __name__ == "__main__":
    chunk_housing_law_to_json()