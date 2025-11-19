#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전국 시군구 및 읍면동 코드 생성기
- PublicDataReader 라이브러리를 사용하여 최신 법정동 코드를 가져옵니다.
- 코드를 시군구(5자리), 읍면동(5자리)으로 분리하여 저장합니다.
- 생성된 코드는 다른 스크립트에서 지역별 데이터 수집 시 활용할 수 있습니다.
"""

import PublicDataReader as pdr
import pandas as pd
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodeGenerator:
    """
    전국의 법정동 코드를 생성하고 관리하는 클래스.
    """

    def __init__(self, output_dir: str = '../data'):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.raw_data = None
        self.processed_data = None

    def fetch_codes(self) -> pd.DataFrame:
        """
        PublicDataReader를 통해 전국의 법정동 코드 데이터를 가져옵니다.
        """
        logger.info("🔄 PublicDataReader를 통해 최신 법정동 코드 데이터를 가져오는 중...")
        try:
            # 모든 법정동 코드를 가져옵니다. is_active 인자는 현재 지원되지 않습니다.
            df = pdr.code_bdong()
            if df.empty:
                logger.warning("⚠️ 데이터를 가져왔지만 비어있습니다. API 또는 라이브러리 상태를 확인하세요.")
                return pd.DataFrame()
            
            # '말소일자'가 없거나(NaN) 비어있는('') 데이터가 현재 사용 중인 코드입니다.
            self.raw_data = df[df['말소일자'].isnull() | (df['말소일자'] == '')].copy()
            
            logger.info(f"✅ 총 {len(self.raw_data)}개의 활성 법정동 데이터를 가져왔습니다.")
            
            return self.raw_data
        except Exception as e:
            logger.error(f"❌ 법정동 코드 데이터 가져오기 실패: {e}")
            return pd.DataFrame()

    def process_codes(self) -> pd.DataFrame:
        """
        가져온 원본 데이터를 가공하여 시군구 코드, 읍면동 코드를 분리합니다.
        """
        if self.raw_data is None or self.raw_data.empty:
            logger.error("❌ 가공할 데이터가 없습니다. 먼저 fetch_codes()를 실행하세요.")
            return pd.DataFrame()

        logger.info("⚙️ 법정동 코드 데이터 가공 시작...")
        df = self.raw_data.copy()

        # 법정동코드는 10자리 문자열로 처리
        df['법정동코드'] = df['법정동코드'].astype(str).str.zfill(10)

        # 시군구코드(앞 5자리)와 읍면동코드(뒤 5자리) 분리
        df['sigungu_code'] = df['법정동코드'].str[:5]
        df['eupmyeondong_code'] = df['법정동코드'].str[5:]

        # '폐지여부' 대신 '상태' 컬럼 추가
        df['상태'] = '존재'

        # 컬럼 순서 정리
        self.processed_data = df[['시도명', '시군구명', '읍면동명', '법정동코드', 'sigungu_code', 'eupmyeondong_code', '상태']]
        
        logger.info("✅ 데이터 가공 완료.")
        return self.processed_data

    def save_to_csv(self, filename: str = "legal_codes.csv") -> bool:
        """
        가공된 데이터를 CSV 파일로 저장합니다.
        """
        if self.processed_data is None or self.processed_data.empty:
            logger.error("❌ 저장할 데이터가 없습니다.")
            return False

        output_path = os.path.join(self.output_dir, filename)
        try:
            self.processed_data.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"💾 데이터가 '{output_path}' 파일로 성공적으로 저장되었습니다.")
            return True
        except Exception as e:
            logger.error(f"❌ 파일 저장 실패: {e}")
            return False


if __name__ == "__main__":
    generator = CodeGenerator()
    
    # 1. 코드 데이터 가져오기
    if not generator.fetch_codes().empty:
        # 2. 데이터 가공
        if not generator.process_codes().empty:
            # 3. CSV 파일로 저장
            generator.save_to_csv()