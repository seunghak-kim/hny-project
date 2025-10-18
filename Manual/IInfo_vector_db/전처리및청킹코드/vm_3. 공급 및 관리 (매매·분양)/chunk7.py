import re
import json
import os

def chunk_housing_law_rule_to_json(
    input_path="주택법 시행규칙(국토교통부령)(제01373호)(20250203).txt",
    output_path=None
):
    """
    주택법 시행규칙을 조 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 5개 장(Chapter)과 절(Section) 구분, 63개 조항
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
    title_match = re.search(r'^([^\n]+시행규칙)', content, re.MULTILINE)
    rule_title = title_match.group(1).strip() if title_match else "주택법 시행규칙"

    # 시행 정보 추출
    enforcement_match = re.search(r'\[시행\s+([^\]]+)\]', content)
    enforcement_info = enforcement_match.group(1).strip() if enforcement_match else ""

    # 국토교통부령 번호 추출
    rule_number_match = re.search(r'\[국토교통부령\s+제(\d+)호', content)
    rule_number = rule_number_match.group(1) if rule_number_match else ""

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

        # 별지 서식 참조 추출
        form_references = re.findall(r'별지\s*제\d+(?:호)?(?:서식)?', article_content)

        # 법/영 참조 추출
        law_references = re.findall(r'법\s*제\d+조(?:의\d+)?', article_content)
        decree_references = re.findall(r'영\s*제\d+조(?:의\d+)?', article_content)

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
            "rule_title": rule_title,
            "rule_number": f"제{rule_number}호" if rule_number else "",
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

        # 별지 서식 참조가 있으면 메타데이터에 추가
        if form_references:
            metadata["form_references"] = list(set(form_references))

        # 법/영 참조가 있으면 메타데이터에 추가
        if law_references:
            metadata["law_references"] = list(set(law_references))
        if decree_references:
            metadata["decree_references"] = list(set(decree_references))

        # 규제의 재검토 조항인지 확인
        if "규제의 재검토" in article_title:
            metadata["is_regulatory_review"] = True

        chunk_data = {
            "id": chunk_id,
            "text": full_text,
            "metadata": metadata
        }
        chunks.append(chunk_data)

    # 통계 출력
    try:
        print(f"\n시행규칙명: {rule_title}")
        print(f"국토교통부령번호: 제{rule_number}호" if rule_number else "")
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

        # 참조 통계
        form_count = sum(1 for chunk in chunks if chunk['metadata'].get('form_references'))
        law_count = sum(1 for chunk in chunks if chunk['metadata'].get('law_references'))
        decree_count = sum(1 for chunk in chunks if chunk['metadata'].get('decree_references'))

        if form_count or law_count or decree_count:
            print(f"\n참조 통계:")
            if form_count:
                print(f"  별지 서식 참조: {form_count}개 조항")
            if law_count:
                print(f"  법 참조: {law_count}개 조항")
            if decree_count:
                print(f"  영 참조: {decree_count}개 조항")

    except UnicodeEncodeError:
        print(f"\n[Rule information processed]")
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
    chunk_housing_law_rule_to_json()