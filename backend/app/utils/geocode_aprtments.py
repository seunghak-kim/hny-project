# 파일명: geocode_apartments.py
# 카카오 API를 사용하여 주소를 위경도 좌표로 변환하는 스크립트

import pandas as pd
import requests
from tqdm import tqdm
import time
from dotenv import load_dotenv
import os 
# --------------------------------------------------------------------------
# 중요: 1단계에서 발급받은 본인의 REST API 키를 아래에 붙여넣어 주세요!
# --------------------------------------------------------------------------
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
# --------------------------------------------------------------------------


def get_coordinates_kakao(address, use_keyword=False):
    """
    카카오 로컬 API를 사용하여 주소로부터 위경도 좌표를 반환하는 함수
    use_keyword: True면 키워드 검색, False면 주소 검색
    """
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    
    if use_keyword:
        url = f"https://dapi.kakao.com/v2/local/search/keyword.json?query={address}"
    else:
        url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['documents']:
            location = data['documents'][0]
            if use_keyword:
                return (float(location['y']), float(location['x']))
            else:
                return (float(location['y']), float(location['x']))
        else:
            return (None, None)
            
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return (None, None)
    except Exception as e:
        print(f"주소 변환 중 알 수 없는 오류 발생: '{address}' | 오류: {e}")
        return (None, None)

# --- 코드 실행 시작 ---

# 1. CSV 파일 불러오기
try:
    residential_df = pd.read_csv('./data/residential.csv')
    office_df = pd.read_csv('./data/office.csv')
    print("파일을 성공적으로 불러왔습니다.")
except FileNotFoundError:
    print("오류: 'residential.csv' 또는 'office.csv' 파일을 찾을 수 없습니다.")
    exit()

# 2. 데이터 합치기 및 주소 생성
combined_df = pd.concat([residential_df, office_df], ignore_index=True)

# 건물명 정제 함수
def clean_building_name(name):
    """건물명에서 불필요한 문자열 제거"""
    if pd.isna(name):
        return ""
    
    # 괄호 내용 제거
    name = str(name).split('(')[0].strip()
    
    # 아파트, 빌라, 오피스텔 등 공통 접미사 제거
    suffixes_to_remove = ['아파트', 'APT', '빌라', '빌리지', '오피스텔', '타워', '센터', '플레이스', 
                         '하우스', '맨션', '팰리스', '캐슬', '파크', '가든', '힐', '뷰', '시티']
    
    for suffix in suffixes_to_remove:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    
    return name

# 다양한 주소 형태 생성
combined_df['단지명_정제'] = combined_df['단지명'].apply(clean_building_name)
combined_df['기본주소'] = '서울 ' + combined_df['구'] + ' ' + combined_df['동']
combined_df['상세주소'] = combined_df['기본주소'] + ' ' + combined_df['단지명_정제']
combined_df['원본주소'] = '서울 ' + combined_df['구'] + ' ' + combined_df['동'] + ' ' + combined_df['단지명']

# 중복 주소 제거를 위해 원본주소 기준으로 처리
unique_data = combined_df.drop_duplicates(subset=['원본주소']).copy()
print(f"총 {len(unique_data)}개의 고유한 주소에 대한 좌표를 카카오 API로 찾습니다.")

# 3. 좌표 변환 실행 (개선된 다단계 시도)
def get_coordinates_with_fallback(row):
    """다단계 fallback으로 좌표 검색"""
    attempts = [
        (row['원본주소'], False, "원본 주소"),
        (row['상세주소'], False, "정제된 주소"),
        (row['원본주소'], True, "원본 키워드 검색"),
        (row['상세주소'], True, "정제된 키워드 검색"),
        (row['기본주소'], False, "기본 주소"),
        (row['기본주소'], True, "기본 키워드 검색")
    ]
    
    for address, use_keyword, method in attempts:
        if pd.isna(address) or address.strip() == '':
            continue
            
        lat, lon = get_coordinates_kakao(address, use_keyword)
        if lat is not None and lon is not None:
            return lat, lon, method, address
        time.sleep(0.02)
    
    return None, None, "모든 시도 실패", ""

coordinate_results = {}
for idx, row in tqdm(unique_data.iterrows(), desc="주소 변환 진행률", total=len(unique_data)):
    lat, lon, method, used_address = get_coordinates_with_fallback(row)
    
    if lat is None:
        print(f"'{row['원본주소']}' 좌표 변환 실패")
    
    coordinate_results[row['원본주소']] = {
        'lat': lat, 
        'lon': lon, 
        'method': method,
        'used_address': used_address
    }

# 4. 원본 데이터에 좌표 추가
combined_df['위도'] = combined_df['원본주소'].map(lambda addr: coordinate_results.get(addr, {}).get('lat'))
combined_df['경도'] = combined_df['원본주소'].map(lambda addr: coordinate_results.get(addr, {}).get('lon'))
combined_df['변환방법'] = combined_df['원본주소'].map(lambda addr: coordinate_results.get(addr, {}).get('method'))
combined_df['사용된주소'] = combined_df['원본주소'].map(lambda addr: coordinate_results.get(addr, {}).get('used_address'))

# 5. 결과 파일 저장
output_filename = 'real_estate_with_coordinates_kakao.csv'
combined_df.to_csv(output_filename, index=False, encoding='utf-8-sig')

# 6. 결과 통계 출력
total_count = len(combined_df)
success_count = combined_df['위도'].notna().sum()
failure_count = total_count - success_count

print("\n--- ✅ 작업 완료 ---")
print(f"정확한 위경도 좌표가 추가된 파일이 '{output_filename}'으로 저장되었습니다.")
print(f"\n📊 변환 결과 통계:")
print(f"- 전체 데이터: {total_count:,}개")
print(f"- 성공: {success_count:,}개 ({success_count/total_count*100:.1f}%)")
print(f"- 실패: {failure_count:,}개 ({failure_count/total_count*100:.1f}%)")

# 변환 방법별 통계
method_stats = combined_df['변환방법'].value_counts()
print(f"\n🔍 변환 방법별 성공 통계:")
for method, count in method_stats.items():
    if method != "모든 시도 실패":
        print(f"- {method}: {count:,}개")

print("\n결과 미리보기 (상위 5개):")
print(combined_df[['단지명', '원본주소', '위도', '경도', '변환방법']].head())