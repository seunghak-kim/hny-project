import re
import json
import os

def chunk_realtor_rule_to_json(
    input_path="공인중개사법 시행규칙(국토교통부령)(제01349호)(20240710).txt",
    output_path=None
):
    """
    공인중개사법 시행규칙을 조 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 7개 장(1개 삭제), 33개 조항, 별지 서식 많음
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
    rule_title = title_match.group(1).strip() if title_match else "공인중개사법 시행규칙"

    # 시행 정보 추출
    enforcement_match = re.search(r'\[시행\s+([^\]]+)\]', content)
    enforcement_info = enforcement_match.group(1).strip() if enforcement_match else ""

    # 국토교통부령 번호 추출
    rule_number_match = re.search(r'\[국토교통부령\s+제(\d+)호', content)
    rule_number = rule_number_match.group(1) if rule_number_match else ""

    # 모든 장 정보를 추출 (삭제된 장 포함)
    chapters = {}
    chapter_pattern = r'제(\d+)장\s+([^\n]+)'
    for match in re.finditer(chapter_pattern, content):
        chapter_num = int(match.group(1))
        chapter_title = match.group(2).strip()
        chapters[match.start()] = f"제{chapter_num}장 {chapter_title}"

    # 부칙 위치 찾기
    appendix_positions = []
    appendix_pattern = r'부칙\s*<[^>]+>'
    for match in re.finditer(appendix_pattern, content):
        appendix_positions.append(match.start())

    # 조항을 찾기 위한 정규표현식
    article_pattern = r'(제\d+조(?:의\d+)?)\s*(?:\(([^)]+)\)|삭제)'

    # 모든 조항 찾기
    article_matches = list(re.finditer(article_pattern, content))

    if not article_matches:
        print("경고: 조항을 찾을 수 없습니다.")
        return

    print(f"총 {len(article_matches)}개의 조항을 발견했습니다.")

    # 각 조항 처리
    for i, match in enumerate(article_matches):
        article_number = match.group(1)  # 제N조 또는 제N조의N

        # 삭제된 조항 처리
        if "삭제" in match.group(0):
            deletion_match = re.search(r'삭제\s*<([^>]+)>', content[match.start():match.start()+50])
            deletion_date = deletion_match.group(1) if deletion_match else ""

            # 현재 조항이 속한 장 찾기
            current_chapter = ""
            article_pos = match.start()
            for chapter_pos in sorted(chapters.keys(), reverse=True):
                if chapter_pos < article_pos:
                    current_chapter = chapters[chapter_pos]
                    break

            chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

            chunk_data = {
                "id": chunk_id,
                "text": f"{article_number} 삭제 <{deletion_date}>",
                "metadata": {
                    "rule_title": rule_title,
                    "rule_number": f"제{rule_number}호" if rule_number else "",
                    "enforcement_date": enforcement_info,
                    "chapter": current_chapter,
                    "article_number": article_number,
                    "article_title": "삭제",
                    "is_deleted": True,
                    "deletion_date": deletion_date
                }
            }
            chunks.append(chunk_data)
            continue

        # 일반 조항 처리
        article_title = match.group(2).strip() if match.group(2) else ""

        # 현재 조항이 속한 장 찾기
        current_chapter = ""
        article_pos = match.start()

        # 부칙에 속하는지 확인
        in_appendix = False
        appendix_info = ""

        for app_pos in appendix_positions:
            if article_pos > app_pos:
                in_appendix = True
                appendix_match = re.search(r'부칙\s*<([^>]+)>', content[app_pos:app_pos+100])
                if appendix_match:
                    appendix_info = f"부칙 <{appendix_match.group(1)}>"

        if not in_appendix:
            # 일반 조항인 경우 장 정보 찾기
            for chapter_pos in sorted(chapters.keys(), reverse=True):
                if chapter_pos < article_pos:
                    current_chapter = chapters[chapter_pos]
                    break

        # 조항 내용 추출
        content_start = match.end()
        content_end = len(content)

        # 다음 조항 위치
        if i < len(article_matches) - 1:
            content_end = min(content_end, article_matches[i + 1].start())

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

        # 별지 서식 참조 추출
        form_references = re.findall(r'별지\s*제\d+(?:호)?(?:의\d+)?(?:서식)?', article_content)

        # 법/영 참조 추출
        law_references = re.findall(r'법\s*제\d+조(?:의\d+)?', article_content)
        decree_references = re.findall(r'영\s*제\d+조(?:의\d+)?', article_content)

        # ID 생성
        chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

        # 전체 텍스트 조합
        full_text = f"{article_number}({article_title}) {article_content}"

        # 메타데이터 구성
        metadata = {
            "rule_title": rule_title,
            "rule_number": f"제{rule_number}호" if rule_number else "",
            "enforcement_date": enforcement_info,
            "chapter": current_chapter if not in_appendix else appendix_info,
            "article_number": article_number,
            "article_title": article_title,
            "is_deleted": False
        }

        # 별지 서식 참조가 있으면 메타데이터에 추가
        if form_references:
            metadata["form_references"] = list(set(form_references))

        # 법/영 참조가 있으면 메타데이터에 추가
        if law_references:
            metadata["law_references"] = list(set(law_references))
        if decree_references:
            metadata["decree_references"] = list(set(decree_references))

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

        # 장별 조항 수 계산
        chapter_counts = {}
        appendix_counts = 0
        deleted_count = 0
        form_ref_count = 0

        for chunk in chunks:
            if chunk['metadata'].get('is_deleted', False):
                deleted_count += 1
                continue

            chapter = chunk['metadata']['chapter']
            if '부칙' in chapter:
                appendix_counts += 1
            elif chapter and '삭제' not in chapter:
                chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1

            if chunk['metadata'].get('form_references'):
                form_ref_count += 1

        print("\n장별 조항 수:")
        for chapter, count in sorted(chapter_counts.items()):
            print(f"  {chapter}: {count}개 조항")
        if appendix_counts > 0:
            print(f"  부칙: {appendix_counts}개 조항")
        if deleted_count > 0:
            print(f"  삭제된 조항: {deleted_count}개")

        print(f"\n별지 서식 참조: {form_ref_count}개 조항에서 참조")

    except UnicodeEncodeError:
        print(f"\n[Rule information processed]")
        print(f"[Chapter statistics: {len(chapters)} chapters]")

    # JSON 파일 저장
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"\nSuccess! '{output_path}' file created.")
        print(f"Total {len(chunks)} articles processed.")
    except Exception as e:
        print(f"Error: Failed to save JSON file: {e}")

    return chunks


if __name__ == "__main__":
    # 실제 파일 처리
    chunk_realtor_rule_to_json()