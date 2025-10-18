"""
건축물대장 및 실거래가 정보 조회 API 모듈 (2024-2025 리팩토링 버전)
- 코드 중복 제거 및 일관성 개선
- SSL/TLS 연결 문제 해결
- 확장 가능한 아키텍처
- 전체 부동산 타입 지원 (아파트, 오피스텔, 연립다세대, 단독/다가구)
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from typing import Dict, List, Optional, Callable
from urllib.parse import urlencode, unquote
from dotenv import load_dotenv
import PublicDataReader as pdr
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class ResponseFormat(Enum):
    """응답 형식 열거형"""
    XML = "xml"
    JSON = "json"


@dataclass
class APIConfig:
    """API 설정 데이터 클래스"""
    service_key: str
    base_url: str
    timeout: int = 60
    max_retries: int = 5
    retry_delay: float = 2.0
    response_format: ResponseFormat = ResponseFormat.XML


class ValidationError(Exception):
    """입력값 검증 오류"""
    pass


class APIHelper:
    """API 공통 도우미 클래스"""
    
    @staticmethod
    def validate_lawd_cd(lawd_cd: str) -> str:
        """지역코드 검증"""
        if not lawd_cd or len(lawd_cd) != 5 or not lawd_cd.isdigit():
            raise ValidationError("지역코드(lawd_cd)는 5자리 숫자여야 합니다. (예: 11680)")
        return lawd_cd
    
    @staticmethod
    def validate_deal_ymd(deal_ymd: str) -> str:
        """거래년월 검증"""
        if not deal_ymd or len(deal_ymd) != 6 or not deal_ymd.isdigit():
            raise ValidationError("거래년월(deal_ymd)은 6자리 숫자여야 합니다. (예: 202401)")
        return deal_ymd
    
    @staticmethod
    def format_address_parts(bun: str = "", ji: str = "") -> tuple:
        """번지 정보 포맷팅"""
        return bun.zfill(4) if bun else "", ji.zfill(4) if ji else ""
    
    @staticmethod
    def decode_service_key(service_key: str) -> str:
        """서비스 키 디코딩"""
        return unquote(service_key) if '%' in service_key else service_key


class BaseAPIClient(ABC):
    """기본 API 클라이언트 추상 클래스 (개선된 버전)"""
    
    ENDPOINTS: Dict[str, str] = {}
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """간단한 HTTP 세션 생성 (SSL 복잡성 제거)"""
        session = requests.Session()
        
        # 브라우저 모방 헤더
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # 간단한 재시도 전략
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        
        return session
    
    @abstractmethod
    def _get_endpoint_url(self, endpoint: str) -> str:
        """엔드포인트 URL 반환"""
        pass
    
    @abstractmethod
    def _prepare_params(self, params: Dict) -> Dict:
        """파라미터 준비"""
        pass
    
    def _make_request_with_retry(self, url: str, params: Dict) -> requests.Response:
        """간단한 HTTP 요청 메서드 (SSL 복잡성 제거)"""
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"API 요청 실패 (최대 재시도 초과): {e}")
                time.sleep(self.config.retry_delay * (attempt + 1))  # 선형 백오프
    
    def _parse_response(self, response: requests.Response) -> Dict:
        """응답 파싱"""
        content = response.content
        
        if self.config.response_format == ResponseFormat.JSON:
            return self._parse_json_response(content)
        else:
            return self._parse_xml_response(content)
    
    def _parse_json_response(self, content: bytes) -> Dict:
        """JSON 응답 파싱"""
        try:
            data = json.loads(content.decode('utf-8'))
            
            if 'response' in data:
                response_data = data['response']
                header = response_data.get('header', {})
                body = response_data.get('body', {})
                
                result_code = header.get('resultCode', '')
                result_msg = header.get('resultMsg', '')
                
                if result_code in ['00', '000']:
                    items = body.get('items', {}).get('item', [])
                    if not isinstance(items, list):
                        items = [items] if items else []
                    
                    return {
                        'success': True,
                        'count': body.get('totalCount', len(items)),
                        'data': items,
                        'page_info': {
                            'page_no': body.get('pageNo', 1),
                            'num_of_rows': body.get('numOfRows', 10),
                            'total_count': body.get('totalCount', 0)
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Error {result_code}: {result_msg}",
                        'data': []
                    }
            
            return {'success': False, 'error': 'Invalid response format', 'data': []}
            
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {e}")
    
    def _parse_xml_response(self, content: bytes) -> Dict:
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(content)
            
            result_code = root.find('.//resultCode')
            result_msg = root.find('.//resultMsg')
            
            if result_code is not None and result_code.text in ['00', '000']:
                items = root.findall('.//item')
                
                buildings = []
                for item in items:
                    building = {}
                    for child in item:
                        building[child.tag] = child.text
                    buildings.append(building)
                
                total_count_elem = root.find('.//totalCount')
                page_no_elem = root.find('.//pageNo')
                num_of_rows_elem = root.find('.//numOfRows')
                
                return {
                    'success': True,
                    'count': len(buildings),
                    'data': buildings,
                    'page_info': {
                        'page_no': int(page_no_elem.text) if page_no_elem is not None and page_no_elem.text else 1,
                        'num_of_rows': int(num_of_rows_elem.text) if num_of_rows_elem is not None and num_of_rows_elem.text else 10,
                        'total_count': int(total_count_elem.text) if total_count_elem is not None and total_count_elem.text else len(buildings)
                    }
                }
            else:
                error_msg = result_msg.text if result_msg is not None else 'Unknown error'
                return {
                    'success': False,
                    'error': error_msg,
                    'data': []
                }
                
        except ET.ParseError as e:
            raise Exception(f"XML 파싱 오류: {e}")
    
    def _execute_api_call(self, endpoint_key: str, params: Dict, debug: bool = False) -> Dict:
        """API 호출 실행 (공통 메서드)"""
        if endpoint_key not in self.ENDPOINTS:
            raise ValueError(f"지원하지 않는 엔드포인트: {endpoint_key}")
        
        endpoint = self.ENDPOINTS[endpoint_key]
        url = self._get_endpoint_url(endpoint)
        prepared_params = self._prepare_params(params)
        
        if debug:
            query_string = urlencode(prepared_params, doseq=True)
            print(f"요청 URL: {url}?{query_string}")
        
        try:
            response = self._make_request_with_retry(url, prepared_params)
            result = self._parse_response(response)
            
            if debug:
                if result['success']:
                    print(f"API 호출 성공! 조회된 건수: {result.get('count', 0)}")
                else:
                    print(f"API 오류: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': []
            }


class TransactionPriceAPI(BaseAPIClient):
    """국토교통부 부동산 실거래가 API 클라이언트 (완전 리팩토링 버전)"""
    
    ENDPOINTS = {
        # 아파트
        'apt_trade': 'RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade',
        'apt_rent': 'RTMSDataSvcAptRent/getRTMSDataSvcAptRent',
        
        # 오피스텔
        'offi_trade': 'RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade',
        'offi_rent': 'RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent',
        
        # 연립다세대
        'rh_trade': 'RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade',
        
        # 단독/다가구
        'sh_trade': 'RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade',
        'sh_rent': 'RTMSDataSvcSHRent/getRTMSDataSvcSHRent',
    }
    
    def __init__(self, service_key: Optional[str] = None, response_format: ResponseFormat = ResponseFormat.XML):
        load_dotenv()
        service_key = service_key or os.getenv('SERVICE_KEY')
        
        if not service_key:
            raise ValueError("Service key가 설정되지 않았습니다.")
        
        config = APIConfig(
            service_key=service_key,
            base_url="http://apis.data.go.kr/1613000",
            response_format=response_format
        )
        super().__init__(config)
    
    def _get_endpoint_url(self, endpoint: str) -> str:
        return f"{self.config.base_url}/{endpoint}"
    
    def _prepare_params(self, params: Dict) -> Dict:
        decoded_key = APIHelper.decode_service_key(self.config.service_key)
        
        base_params = {
            'serviceKey': decoded_key,
            'numOfRows': '100',
            'pageNo': '1'
        }
        
        if self.config.response_format == ResponseFormat.JSON:
            base_params['_type'] = 'json'
        
        base_params.update({k: v for k, v in params.items() if v})
        return base_params
    
    def _create_standard_method(self, endpoint_key: str, description: str) -> Callable:
        """표준 API 메서드 생성 팩토리"""
        def api_method(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                      page_no: str = "1", debug: bool = False) -> Dict:
            f"""
            {description} 조회
            
            Args:
                lawd_cd: 지역코드 (법정동코드 앞 5자리)
                deal_ymd: 거래년월 (YYYYMM)
                num_of_rows: 페이지당 결과 수
                page_no: 페이지 번호
                debug: 디버그 모드
                
            Returns:
                Dict: API 응답 결과
            """
            # 공통 검증
            APIHelper.validate_lawd_cd(lawd_cd)
            APIHelper.validate_deal_ymd(deal_ymd)
            
            params = {
                'LAWD_CD': lawd_cd,
                'DEAL_YMD': deal_ymd,
                'numOfRows': num_of_rows,
                'pageNo': page_no
            }
            
            return self._execute_api_call(endpoint_key, params, debug)
        
        return api_method
    
    def get_apt_trade_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                          page_no: str = "1", debug: bool = False) -> Dict:
        """아파트 매매 실거래가 조회"""
        return self._create_standard_method('apt_trade', '아파트 매매 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_apt_rent_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                         page_no: str = "1", debug: bool = False) -> Dict:
        """아파트 전월세 실거래가 조회"""
        return self._create_standard_method('apt_rent', '아파트 전월세 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_offi_trade_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                           page_no: str = "1", debug: bool = False) -> Dict:
        """오피스텔 매매 실거래가 조회"""
        return self._create_standard_method('offi_trade', '오피스텔 매매 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_offi_rent_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                          page_no: str = "1", debug: bool = False) -> Dict:
        """오피스텔 전월세 실거래가 조회"""
        return self._create_standard_method('offi_rent', '오피스텔 전월세 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_rh_trade_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                         page_no: str = "1", debug: bool = False) -> Dict:
        """연립다세대 매매 실거래가 조회"""
        return self._create_standard_method('rh_trade', '연립다세대 매매 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_sh_trade_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                         page_no: str = "1", debug: bool = False) -> Dict:
        """단독/다가구 매매 실거래가 조회"""
        return self._create_standard_method('sh_trade', '단독/다가구 매매 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_sh_rent_data(self, lawd_cd: str, deal_ymd: str, num_of_rows: str = "100", 
                        page_no: str = "1", debug: bool = False) -> Dict:
        """단독/다가구 전월세 실거래가 조회"""
        return self._create_standard_method('sh_rent', '단독/다가구 전월세 실거래가')(
            self, lawd_cd, deal_ymd, num_of_rows, page_no, debug
        )
    
    def get_batch_data(self, lawd_cd: str, start_ym: str, end_ym: str, 
                      api_type: str = 'apt_trade', num_of_rows: str = "1000", 
                      debug: bool = False) -> List[Dict]:
        """기간별 부동산 실거래가 데이터 배치 조회"""
        from datetime import datetime
        
        if api_type not in self.ENDPOINTS:
            raise ValueError(f"지원하지 않는 API 타입: {api_type}. 지원 타입: {list(self.ENDPOINTS.keys())}")
        
        # 메서드 매핑
        method_map = {
            'apt_trade': self.get_apt_trade_data,
            'apt_rent': self.get_apt_rent_data,
            'offi_trade': self.get_offi_trade_data,
            'offi_rent': self.get_offi_rent_data,
            'rh_trade': self.get_rh_trade_data,
            'sh_trade': self.get_sh_trade_data,
            'sh_rent': self.get_sh_rent_data,
        }
        
        api_method = method_map[api_type]
        
        start_date = datetime.strptime(start_ym, '%Y%m')
        end_date = datetime.strptime(end_ym, '%Y%m')
        
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            deal_ymd = current_date.strftime('%Y%m')
            
            if debug:
                print(f"조회 중 ({api_type}): {lawd_cd} - {deal_ymd}")
            
            try:
                result = api_method(lawd_cd, deal_ymd, num_of_rows, debug=debug)
                
                if result['success'] and result['data']:
                    all_data.extend(result['data'])
                    if debug:
                        print(f"  -> {len(result['data'])}건 수집")
                elif debug:
                    print(f"  -> 데이터 없음 또는 오류: {result.get('error', 'Unknown')}")
                
                time.sleep(0.1)  # API 호출 간격
                
            except Exception as e:
                if debug:
                    print(f"  -> 오류 발생: {e}")
                continue
            
            # 다음 달로 이동
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        if debug:
            print(f"\n총 {len(all_data)}건의 데이터 수집 완료")
        
        return all_data


class BuildingHubAPI(BaseAPIClient):
    """건축HUB API 클라이언트 (리팩토링 버전)"""
    
    ENDPOINTS = {
        'building_info': 'getBrTitleInfo',
        'building_summary': 'getBrRecapTitleInfo',
        'building_floor': 'getBrFlrOulnInfo',
        'building_permit': 'getBrBasisOulnInfo',
        'building_dong': 'getBrDongOulnInfo',
        'building_ho': 'getBrHoOulnInfo',
    }
    
    def __init__(self, service_key: Optional[str] = None, response_format: ResponseFormat = ResponseFormat.XML):
        load_dotenv()
        service_key = service_key or os.getenv('SERVICE_KEY')
        
        if not service_key:
            raise ValueError("Service key가 설정되지 않았습니다.")
        
        config = APIConfig(
            service_key=service_key,
            base_url="http://apis.data.go.kr/1613000/BldRgstHubService",
            response_format=response_format
        )
        super().__init__(config)
    
    def _get_endpoint_url(self, endpoint: str) -> str:
        return f"{self.config.base_url}/{endpoint}"
    
    def _prepare_params(self, params: Dict) -> Dict:
        base_params = {
            'serviceKey': self.config.service_key,
            'numOfRows': '10',
            'pageNo': '1'
        }
        
        if self.config.response_format == ResponseFormat.JSON:
            base_params['_type'] = 'json'
        
        base_params.update({k: v for k, v in params.items() if v})
        return base_params
    
    def get_building_info(self, sigungu_cd: str, bjdong_cd: str, plat_gb_cd: str = "0", 
                         bun: str = "", ji: str = "", start_date: str = "", end_date: str = "", 
                         num_of_rows: str = "10", page_no: str = "1", debug: bool = False) -> Dict:
        """건축물대장 표제부 정보 조회"""
        bun_padded, ji_padded = APIHelper.format_address_parts(bun, ji)
        
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'platGbCd': plat_gb_cd,
            'bun': bun_padded,
            'ji': ji_padded,
            'startDate': start_date,
            'endDate': end_date,
            'numOfRows': num_of_rows,
            'pageNo': page_no
        }
        
        return self._execute_api_call('building_info', params, debug)


class RegionCodeManager:
    """지역 코드 관리 클래스"""
    
    def __init__(self):
        self._code_cache = None
    
    @property
    def code_data(self) -> pd.DataFrame:
        if self._code_cache is None:
            self._code_cache = pdr.code_bdong()
        return self._code_cache
    
    def get_region_codes(self, sigungu_name: str, bdong_name: str) -> Dict:
        """시군구명과 읍면동명으로 지역 코드 조회"""
        try:
            code = self.code_data
            
            result = code.loc[
                (code['시군구명'].str.contains(sigungu_name)) &
                (code['읍면동명'] == bdong_name)
            ]
            
            if result.empty:
                result = code.loc[
                    (code['시군구명'].str.contains(sigungu_name)) &
                    (code['읍면동명'].str.contains(bdong_name))
                ]
                
            if result.empty:
                raise ValueError(f"'{sigungu_name} {bdong_name}'에 해당하는 지역을 찾을 수 없습니다.")
            
            first_result = result.iloc[0]
            sigungu_code = first_result['시군구코드']
            bdong_code_full = first_result['법정동코드']
            bdong_code = bdong_code_full[len(sigungu_code):]
            
            return {
                'sigungu_name': sigungu_name,
                'bdong_name': bdong_name,
                'sigungu_code': sigungu_code,
                'bdong_code': bdong_code,
                'bdong_code_full': bdong_code_full,
                'region_info': first_result.to_dict(),
                'total_matches': len(result)
            }
            
        except Exception as e:
            raise Exception(f"지역 코드 조회 오류: {e}")


class DataExporter:
    """데이터 내보내기 유틸리티"""
    
    @staticmethod
    def to_json(data: Dict, filename: str, indent: int = 2) -> bool:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            print(f"JSON 저장 오류: {e}")
            return False
    
    @staticmethod
    def to_csv(data: List[Dict], filename: str) -> bool:
        try:
            if not data:
                raise ValueError("저장할 데이터가 없습니다.")
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            print(f"CSV 저장 오류: {e}")
            return False


# 하위 호환성을 위한 별칭
BuildingInfoAPI = BuildingHubAPI