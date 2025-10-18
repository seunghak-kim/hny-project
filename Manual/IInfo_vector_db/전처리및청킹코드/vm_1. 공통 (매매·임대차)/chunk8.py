import re
import json
import os

def chunk_registration_rule_to_json(
    input_path="부동산등기규칙(대법원규칙)(제03169호)(20250801).txt",
    output_path=None
):
    """
    부동산등기규칙을 조 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 7개 장, 관(Section) 구조 포함, 199개 조항의 대규모 규칙
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
    title_match = re.search(r'^([^\n]+규칙)', content, re.MULTILINE)
    rule_title = title_match.group(1).strip() if title_match else "부동산등기규칙"

    # 시행 정보 추출
    enforcement_match = re.search(r'\[시행\s+([^\]]+)\]', content)
    enforcement_info = enforcement_match.group(1).strip() if enforcement_match else ""

    # 대법원규칙 번호 추출
    rule_number_match = re.search(r'\[대법원규칙\s+제(\d+)호', content)
    rule_number = rule_number_match.group(1) if rule_number_match else ""

    # 모든 장 정보를 추출
    chapters = {}
    chapter_pattern = r'제(\d+)장\s+([^\n]+)'
    for match in re.finditer(chapter_pattern, content):
        chapter_num = int(match.group(1))
        chapter_title = match.group(2).strip()
        chapters[match.start()] = f"제{chapter_num}장 {chapter_title}"

    # 모든 관(Section) 정보를 추출
    sections = {}
    section_pattern = r'제(\d+)관\s+([^\n]+)'
    for match in re.finditer(section_pattern, content):
        section_num = int(match.group(1))
        section_title = match.group(2).strip()
        sections[match.start()] = f"제{section_num}관 {section_title}"

    # 부칙 위치 찾기
    appendix_positions = []
    appendix_pattern = r'부칙\s*<[^>]+>'
    for match in re.finditer(appendix_pattern, content):
        appendix_positions.append(match.start())

    # 조항을 찾기 위한 정규표현식 (제N조의N, 제N조의N의N 형식 포함)
    article_pattern = r'(제\d+조(?:의\d+)*)\s*\(([^)]+)\)'

    # 모든 조항 찾기
    article_matches = list(re.finditer(article_pattern, content))

    if not article_matches:
        print("경고: 조항을 찾을 수 없습니다.")
        return

    print(f"총 {len(article_matches)}개의 조항을 발견했습니다.")

    # 각 조항 처리
    for i, match in enumerate(article_matches):
        article_number = match.group(1)  # 제N조, 제N조의N, 제N조의N의N 등
        article_title = match.group(2).strip()  # 괄호 안의 제목

        # 현재 조항의 위치
        article_pos = match.start()

        # 현재 조항이 속한 장 찾기
        current_chapter = ""
        for chapter_pos in sorted(chapters.keys(), reverse=True):
            if chapter_pos < article_pos:
                current_chapter = chapters[chapter_pos]
                break

        # 현재 조항이 속한 관 찾기
        current_section = ""
        for section_pos in sorted(sections.keys(), reverse=True):
            if section_pos < article_pos:
                # 관이 현재 장 내에 있는지 확인
                section_chapter = ""
                for chapter_pos in sorted(chapters.keys(), reverse=True):
                    if chapter_pos < section_pos:
                        section_chapter = chapters[chapter_pos]
                        break
                if section_chapter == current_chapter:
                    current_section = sections[section_pos]
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

        # 다음 관 위치 확인
        next_section_match = re.search(r'\n제\d+관\s+', content[content_start:])
        if next_section_match:
            content_end = min(content_end, content_start + next_section_match.start())

        # 다음 장 위치 확인
        next_chapter_match = re.search(r'\n제\d+장\s+', content[content_start:])
        if next_chapter_match:
            content_end = min(content_end, content_start + next_chapter_match.start())

        # 부칙 위치 확인
        next_appendix_match = re.search(r'\n부칙\s*<', content[content_start:])
        if next_appendix_match:
            content_end = min(content_end, content_start + next_appendix_match.start())

        article_content = content[content_start:content_end].strip()

        # 불필요한 공백 정리
        article_content = re.sub(r'\n\s*\n+', '\n', article_content)
        article_content = article_content.strip()

        # ID 생성 (제67조의2의3 -> article_67_2_3)
        chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

        # 전체 텍스트 조합
        full_text = f"{article_number}({article_title}) {article_content}"

        # 메타데이터 구성
        metadata = {
            "rule_title": rule_title,
            "rule_number": f"제{rule_number}호" if rule_number else "",
            "enforcement_date": enforcement_info,
            "chapter": current_chapter if not in_appendix else "",
            "section": current_section if not in_appendix else "",
            "article_number": article_number,
            "article_title": article_title
        }

        # 부칙인 경우 메타데이터 업데이트
        if in_appendix:
            metadata["in_appendix"] = True
            metadata["appendix_info"] = appendix_info

        chunk_data = {
            "id": chunk_id,
            "text": full_text,
            "metadata": metadata
        }
        chunks.append(chunk_data)

    # 통계 출력
    try:
        print(f"\n규칙명: {rule_title}")
        print(f"대법원규칙번호: 제{rule_number}호" if rule_number else "")
        print(f"시행일: {enforcement_info}")

        # 장별, 관별 조항 수 계산
        chapter_counts = {}
        section_counts = {}
        appendix_counts = 0

        for chunk in chunks:
            if chunk['metadata'].get('in_appendix', False):
                appendix_counts += 1
            else:
                chapter = chunk['metadata']['chapter']
                section = chunk['metadata']['section']

                if chapter:
                    chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
                if section:
                    section_counts[section] = section_counts.get(section, 0) + 1

        print(f"\n총 {len(chapters)}개 장, {len(sections)}개 관")
        print("\n장별 조항 수:")
        for chapter, count in sorted(chapter_counts.items()):
            print(f"  {chapter}: {count}개 조항")

        # 관이 있는 경우에만 출력
        if section_counts:
            print("\n주요 관별 조항 수:")
            # 상위 10개 관만 표시 (너무 많을 수 있으므로)
            for section, count in sorted(section_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {section}: {count}개 조항")

        if appendix_counts > 0:
            print(f"\n부칙: {appendix_counts}개 조항")

        print(f"\n총 {len(chunks)}개 조항 처리 완료")

    except UnicodeEncodeError:
        print(f"\n[Rule information processed]")
        print(f"[Statistics: {len(chapters)} chapters, {len(sections)} sections]")
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
    # 실제 파일 처리
    chunk_registration_rule_to_json()