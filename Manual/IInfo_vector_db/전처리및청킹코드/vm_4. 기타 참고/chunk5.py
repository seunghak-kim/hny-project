import re
import json
import os

def chunk_price_disclosure_law_to_json(
    input_path="부동산 가격공시에 관한 법률(법률)(제17459호)(20201210).txt",
    output_path=None
):
    """
    부동산 가격공시에 관한 법률(기본법)을 조 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 6개 장(Chapter), 38개 조항, 기본법
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
    title_match = re.search(r'^([^\n]+법률)', content, re.MULTILINE)
    law_title = title_match.group(1).strip() if title_match else "부동산 가격공시에 관한 법률"

    # 시행 정보 추출
    enforcement_match = re.search(r'\[시행\s+([^\]]+)\]', content)
    enforcement_info = enforcement_match.group(1).strip() if enforcement_match else ""

    # 법률 번호 추출
    law_number_match = re.search(r'\[법률\s+제(\d+)호', content)
    law_number = law_number_match.group(1) if law_number_match else ""

    # 장(chapter) 정보 추출 및 위치 매핑
    chapters = {}
    chapter_pattern = r'제(\d+)장\s+([^\n]+)'
    for match in re.finditer(chapter_pattern, content):
        chapter_num = match.group(1)
        chapter_title = match.group(2).strip()
        chapters[match.start()] = f"제{chapter_num}장 {chapter_title}"

    # 부칙 위치 찾기
    appendix_positions = []
    appendix_pattern = r'부칙\s*<[^>]+>'
    for match in re.finditer(appendix_pattern, content):
        appendix_positions.append(match.start())

    # 조항을 찾기 위한 정규표현식 (제9조의2 같은 형식 포함)
    article_pattern = r'(제\d+조(?:의\d+)?)\s*\(([^)]+)\)'

    # 모든 조항 찾기
    article_matches = list(re.finditer(article_pattern, content))

    if not article_matches:
        print("경고: 조항을 찾을 수 없습니다.")
        return

    print(f"총 {len(article_matches)}개의 조항을 발견했습니다.")

    # 장별 조항 수 카운트를 위한 딕셔너리
    chapter_article_count = {}

    # 각 조항 처리
    for i, match in enumerate(article_matches):
        article_number = match.group(1)  # 제N조 또는 제N조의N
        article_title = match.group(2).strip()  # 괄호 안의 제목

        # 현재 조가 속한 장 찾기
        current_chapter = ""
        article_pos = match.start()
        sorted_chapter_pos = sorted([pos for pos in chapters.keys() if pos < article_pos], reverse=True)
        if sorted_chapter_pos:
            current_chapter = chapters[sorted_chapter_pos[0]]
            # 장별 조항 수 카운트
            if current_chapter not in chapter_article_count:
                chapter_article_count[current_chapter] = 0
            chapter_article_count[current_chapter] += 1

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

        # 법 참조 추출
        law_references = re.findall(r'「[^」]+」', article_content)

        # 대통령령 참조 추출
        decree_references = re.findall(r'대통령령(?:으로)?\s*(?:정하는)?', article_content)

        # 국토교통부령 참조 추출
        rule_references = re.findall(r'국토교통부령(?:으로)?\s*(?:정하는)?', article_content)

        # 조항 내 항목 개수 확인 (1., 2., 3. 등)
        item_count = len(re.findall(r'^\d+\.', article_content, re.MULTILINE))

        # ID 생성
        chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

        # 전체 텍스트 조합
        full_text = f"{article_number}({article_title}) {article_content}"

        # 메타데이터 구성
        metadata = {
            "law_title": law_title,
            "law_number": f"제{law_number}호" if law_number else "",
            "enforcement_date": enforcement_info,
            "article_number": article_number,
            "article_title": article_title,
            "item_count": item_count
        }

        # 장 정보가 있으면 추가
        if current_chapter:
            metadata["chapter"] = current_chapter

        # 부칙인 경우 메타데이터에 추가
        if in_appendix:
            metadata["in_appendix"] = True
            metadata["appendix_info"] = appendix_info

        # 법 참조가 있으면 메타데이터에 추가
        if law_references:
            metadata["law_references"] = list(set(law_references))

        # 대통령령 참조가 있으면 메타데이터에 추가
        if decree_references:
            metadata["has_decree_reference"] = True

        # 국토교통부령 참조가 있으면 메타데이터에 추가
        if rule_references:
            metadata["has_rule_reference"] = True

        # 조항 유형 분류
        if "목적" in article_title:
            metadata["article_type"] = "목적"
        elif "정의" in article_title:
            metadata["article_type"] = "정의"
        elif "위원회" in article_title:
            metadata["article_type"] = "위원회"
        elif "공시" in article_title:
            metadata["article_type"] = "공시"
        elif "이의신청" in article_title:
            metadata["article_type"] = "이의신청"
        elif "벌칙" in article_title or "과태료" in article_title:
            metadata["article_type"] = "벌칙"

        # 가격공시 대상 분류
        if "표준지" in article_title or "지가" in article_title:
            metadata["price_disclosure_target"] = "토지"
        elif "표준주택" in article_title or "개별주택" in article_title:
            metadata["price_disclosure_target"] = "단독주택"
        elif "공동주택" in article_title:
            metadata["price_disclosure_target"] = "공동주택"
        elif "비주거용" in article_title:
            metadata["price_disclosure_target"] = "비주거용부동산"

        # 주요 키워드 확인
        key_terms = ["적정가격", "조사ㆍ평가", "조사ㆍ산정", "감정평가", "공시기준일", "이의신청",
                    "부동산원", "중앙부동산가격공시위원회"]
        if any(term in article_content for term in key_terms):
            metadata["has_key_terms"] = True

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
        if chapter_article_count:
            print(f"\n장별 조항 분포:")
            for chapter, count in sorted(chapter_article_count.items()):
                print(f"  {chapter}: {count}개 조항")

        # 참조 통계
        law_count = sum(1 for chunk in chunks if chunk['metadata'].get('law_references'))
        decree_count = sum(1 for chunk in chunks if chunk['metadata'].get('has_decree_reference'))
        rule_count = sum(1 for chunk in chunks if chunk['metadata'].get('has_rule_reference'))

        if law_count or decree_count or rule_count:
            print(f"\n참조 통계:")
            if law_count:
                print(f"  타 법률 참조: {law_count}개 조항")
            if decree_count:
                print(f"  대통령령 참조: {decree_count}개 조항")
            if rule_count:
                print(f"  국토교통부령 참조: {rule_count}개 조항")

        # 조항 유형 통계
        article_types = {}
        for chunk in chunks:
            article_type = chunk['metadata'].get('article_type')
            if article_type:
                article_types[article_type] = article_types.get(article_type, 0) + 1

        if article_types:
            print(f"\n조항 유형 분포:")
            for article_type, count in article_types.items():
                print(f"  {article_type}: {count}개 조항")

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
    chunk_price_disclosure_law_to_json()