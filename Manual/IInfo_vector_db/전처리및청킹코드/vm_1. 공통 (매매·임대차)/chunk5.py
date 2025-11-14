import re
import json
import os

def chunk_rule_to_json(
    input_path="부동산 거래신고 등에 관한 법률 시행규칙(국토교통부령)(제01294호)(20240101).txt",
    output_path=None
):
    """
    부동산 거래신고 등에 관한 법률 시행규칙을 조 단위로 청킹하고 JSON 파일로 저장합니다.
    특징: 장(Chapter) 구분이 없는 시행규칙 구조
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
    rule_title = title_match.group(1).strip() if title_match else "시행규칙"

    # 약칭 추출
    abbrev_match = re.search(r'\(약칭:\s*([^)]+)\)', content)
    abbreviation = abbrev_match.group(1).strip() if abbrev_match else ""

    # 시행 정보 추출
    enforcement_match = re.search(r'\[시행\s+([^\]]+)\]', content)
    enforcement_info = enforcement_match.group(1).strip() if enforcement_match else ""

    # 규칙 번호 추출
    rule_number_match = re.search(r'\[국토교통부령\s+제(\d+)호', content)
    rule_number = rule_number_match.group(1) if rule_number_match else ""

    # 부칙 위치 찾기
    appendix_positions = []
    appendix_pattern = r'부칙\s*<[^>]+>'
    for match in re.finditer(appendix_pattern, content):
        appendix_positions.append(match.start())

    # 조항을 찾기 위한 정규표현식
    # 삭제된 조항도 포함 (예: 제22조 삭제 <2020. 10. 27.>)
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

            chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

            chunk_data = {
                "id": chunk_id,
                "text": f"{article_number} 삭제 <{deletion_date}>",
                "metadata": {
                    "rule_title": rule_title,
                    "abbreviation": abbreviation,
                    "rule_number": f"제{rule_number}호" if rule_number else "",
                    "enforcement_date": enforcement_info,
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

        # 부칙에 속하는지 확인
        in_appendix = False
        appendix_info = ""
        article_pos = match.start()

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

        # ID 생성
        chunk_id = "article_" + article_number.replace("제", "").replace("조", "").replace("의", "_")

        # 전체 텍스트 조합
        if article_title:
            full_text = f"{article_number}({article_title}) {article_content}"
        else:
            full_text = f"{article_number} {article_content}"

        # 메타데이터 구성
        metadata = {
            "rule_title": rule_title,
            "abbreviation": abbreviation,
            "rule_number": f"제{rule_number}호" if rule_number else "",
            "enforcement_date": enforcement_info,
            "article_number": article_number,
            "article_title": article_title,
            "is_deleted": False
        }

        # 부칙인 경우 메타데이터에 추가
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
        if abbreviation:
            print(f"약칭: {abbreviation}")
        print(f"규칙번호: 제{rule_number}호" if rule_number else "")
        print(f"시행일: {enforcement_info}")

        # 삭제된 조항 수 계산
        deleted_count = sum(1 for chunk in chunks if chunk['metadata'].get('is_deleted', False))
        appendix_count = sum(1 for chunk in chunks if chunk['metadata'].get('in_appendix', False))
        active_count = len(chunks) - deleted_count - appendix_count

        print(f"\n조항 통계:")
        print(f"  유효 조항: {active_count}개")
        print(f"  삭제 조항: {deleted_count}개")
        print(f"  부칙 조항: {appendix_count}개")
        print(f"  총 조항: {len(chunks)}개")

    except UnicodeEncodeError:
        print(f"\n[Rule information processed]")
        print(f"Total {len(chunks)} articles processed.")

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
    chunk_rule_to_json()