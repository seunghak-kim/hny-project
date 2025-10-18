"""
PostgreSQL 데이터베이스 설정 및 연결 관리
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from typing import Optional, Dict, List
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class PostgreSQLManager:
    """PostgreSQL 데이터베이스 관리 클래스"""
    
    def __init__(self):
        self.engine = None
        self.connection_string = self._build_connection_string()
        
    def _build_connection_string(self) -> str:
        """연결 문자열 생성"""
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'real_estate')
        username = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', '')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    def connect(self) -> bool:
        """데이터베이스 연결"""
        try:
            self.engine = create_engine(self.connection_string)
            # 연결 테스트
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ PostgreSQL 데이터베이스 연결 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {e}")
            return False
    
    def create_tables(self) -> bool:
        """테이블 생성"""
        try:
            # 아파트 매매 테이블
            apt_trade_sql = """
            CREATE TABLE IF NOT EXISTS apt_trade (
                id SERIAL PRIMARY KEY,
                apt_name VARCHAR(100),
                deal_amount INTEGER,
                deal_year INTEGER,
                deal_month INTEGER,
                deal_day INTEGER,
                exclusive_area DECIMAL(10,2),
                floor_num INTEGER,
                build_year INTEGER,
                region_code VARCHAR(5),
                region_name VARCHAR(50),
                buyer_type VARCHAR(10),
                seller_type VARCHAR(10),
                dealing_type VARCHAR(20),
                land_lease VARCHAR(5),
                cancel_deal_date VARCHAR(20),
                cancel_deal_type VARCHAR(5),
                estate_agent_region VARCHAR(50),
                jibun VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # 아파트 전월세 테이블
            apt_rent_sql = """
            CREATE TABLE IF NOT EXISTS apt_rent (
                id SERIAL PRIMARY KEY,
                apt_name VARCHAR(100),
                deposit INTEGER,
                monthly_rent INTEGER,
                deal_year INTEGER,
                deal_month INTEGER,
                deal_day INTEGER,
                exclusive_area DECIMAL(10,2),
                floor_num INTEGER,
                build_year INTEGER,
                region_code VARCHAR(5),
                region_name VARCHAR(50),
                contract_term VARCHAR(20),
                contract_type VARCHAR(20),
                pre_deposit INTEGER,
                pre_monthly_rent INTEGER,
                use_rr_right VARCHAR(10),
                jibun VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # 오피스텔 매매 테이블
            offi_trade_sql = """
            CREATE TABLE IF NOT EXISTS offi_trade (
                id SERIAL PRIMARY KEY,
                building_name VARCHAR(100),
                deal_amount INTEGER,
                deal_year INTEGER,
                deal_month INTEGER,
                deal_day INTEGER,
                exclusive_area DECIMAL(10,2),
                floor_num INTEGER,
                build_year INTEGER,
                region_code VARCHAR(5),
                region_name VARCHAR(50),
                buyer_type VARCHAR(10),
                seller_type VARCHAR(10),
                dealing_type VARCHAR(20),
                cancel_deal_date VARCHAR(20),
                cancel_deal_type VARCHAR(5),
                estate_agent_region VARCHAR(50),
                jibun VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # 오피스텔 전월세 테이블
            offi_rent_sql = """
            CREATE TABLE IF NOT EXISTS offi_rent (
                id SERIAL PRIMARY KEY,
                building_name VARCHAR(100),
                deposit INTEGER,
                monthly_rent INTEGER,
                deal_year INTEGER,
                deal_month INTEGER,
                deal_day INTEGER,
                exclusive_area DECIMAL(10,2),
                floor_num INTEGER,
                build_year INTEGER,
                region_code VARCHAR(5),
                region_name VARCHAR(50),
                contract_term VARCHAR(20),
                contract_type VARCHAR(20),
                jibun VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # 단독/다가구 매매 테이블
            sh_trade_sql = """
            CREATE TABLE IF NOT EXISTS sh_trade (
                id SERIAL PRIMARY KEY,
                house_type VARCHAR(50),
                deal_amount INTEGER,
                deal_year INTEGER,
                deal_month INTEGER,
                deal_day INTEGER,
                exclusive_area DECIMAL(10,2),
                land_area DECIMAL(10,2),
                floor_num INTEGER,
                build_year INTEGER,
                region_code VARCHAR(5),
                region_name VARCHAR(50),
                buyer_type VARCHAR(10),
                seller_type VARCHAR(10),
                dealing_type VARCHAR(20),
                cancel_deal_date VARCHAR(20),
                cancel_deal_type VARCHAR(5),
                estate_agent_region VARCHAR(50),
                jibun VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # 단독/다가구 전월세 테이블
            sh_rent_sql = """
            CREATE TABLE IF NOT EXISTS sh_rent (
                id SERIAL PRIMARY KEY,
                house_type VARCHAR(50),
                deposit INTEGER,
                monthly_rent INTEGER,
                deal_year INTEGER,
                deal_month INTEGER,
                deal_day INTEGER,
                exclusive_area DECIMAL(10,2),
                land_area DECIMAL(10,2),
                floor_num INTEGER,
                build_year INTEGER,
                region_code VARCHAR(5),
                region_name VARCHAR(50),
                contract_term VARCHAR(20),
                contract_type VARCHAR(20),
                jibun VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            with self.engine.connect() as conn:
                conn.execute(text(apt_trade_sql))
                conn.execute(text(apt_rent_sql))
                conn.execute(text(offi_trade_sql))
                conn.execute(text(offi_rent_sql))
                conn.execute(text(sh_trade_sql))
                conn.execute(text(sh_rent_sql))
                conn.commit()
                
            logger.info("✅ 테이블 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 테이블 생성 실패: {e}")
            return False
    
    def insert_data(self, data: List[Dict], table_name: str, batch_size: int = 1000) -> bool:
        """데이터 배치 삽입"""
        try:
            if not data:
                logger.warning("삽입할 데이터가 없습니다.")
                return True
                
            df = pd.DataFrame(data)
            
            # 데이터 전처리
            df = self._preprocess_data(df, table_name)
            
            # 배치 삽입 (더 안전한 방법)
            total_rows = len(df)
            for i in range(0, total_rows, batch_size):
                batch = df.iloc[i:i+batch_size]
                try:
                    batch.to_sql(table_name, self.engine, if_exists='append', index=False, method=None)
                    logger.info(f"배치 삽입: {i+len(batch)}/{total_rows} 완료")
                except Exception as e:
                    logger.warning(f"배치 삽입 실패, 개별 처리: {e}")
                    # 개별 행 삽입으로 대체
                    for idx, row in batch.iterrows():
                        try:
                            row.to_frame().T.to_sql(table_name, self.engine, if_exists='append', index=False)
                        except Exception as row_error:
                            logger.error(f"행 {idx} 삽입 실패: {row_error}")
            
            logger.info(f"✅ {table_name} 테이블에 {total_rows}건 삽입 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터 삽입 실패: {e}")
            return False
    
    def _preprocess_data(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """데이터 전처리"""
        try:
            if table_name in ['apt_trade', 'offi_trade']:
                # 매매 데이터 전처리
                field_mapping = {
                    'aptNm': 'apt_name',
                    'offiNm': 'building_name',
                    'buildingNm': 'building_name',
                    'dealAmount': 'deal_amount',
                    'dealYear': 'deal_year',
                    'dealMonth': 'deal_month',
                    'dealDay': 'deal_day',
                    'excluUseAr': 'exclusive_area',
                    'floor': 'floor_num',
                    'buildYear': 'build_year',
                    'sggCd': 'region_code',
                    'umdNm': 'region_name',
                    'buyerGbn': 'buyer_type',
                    'slerGbn': 'seller_type',
                    'dealingGbn': 'dealing_type',
                    'landLeaseholdGbn': 'land_lease',
                    'cdealDay': 'cancel_deal_date',
                    'cdealType': 'cancel_deal_type',
                    'estateAgentSggNm': 'estate_agent_region',
                    'jibun': 'jibun'
                }
                
            elif table_name in ['apt_rent', 'offi_rent']:
                # 전월세 데이터 전처리
                field_mapping = {
                    'aptNm': 'apt_name',
                    'offiNm': 'building_name',
                    'buildingNm': 'building_name',
                    'deposit': 'deposit',
                    'monthlyRent': 'monthly_rent',
                    'dealYear': 'deal_year',
                    'dealMonth': 'deal_month',
                    'dealDay': 'deal_day',
                    'excluUseAr': 'exclusive_area',
                    'floor': 'floor_num',
                    'buildYear': 'build_year',
                    'sggCd': 'region_code',
                    'umdNm': 'region_name',
                    'contractTerm': 'contract_term',
                    'contractType': 'contract_type',
                    'preDeposit': 'pre_deposit',
                    'preMonthlyRent': 'pre_monthly_rent',
                    'useRRRight': 'use_rr_right',
                    'jibun': 'jibun',
                    # 추가 필드들
                    'rgstDate': 'created_at',
                    'depositGbn': 'deposit',
                    'rentGbn': 'monthly_rent'
                }
                
            elif table_name == 'sh_trade':
                # 단독/다가구 매매 데이터 전처리
                field_mapping = {
                    'houseType': 'house_type',
                    'dealAmount': 'deal_amount',
                    'dealYear': 'deal_year',
                    'dealMonth': 'deal_month',
                    'dealDay': 'deal_day',
                    'excluUseAr': 'exclusive_area',
                    'lotArea': 'land_area',
                    'plottageAr': 'land_area',  # 대지면적
                    'floor': 'floor_num',
                    'buildYear': 'build_year',
                    'sggCd': 'region_code',
                    'umdNm': 'region_name',
                    'buyerGbn': 'buyer_type',
                    'slerGbn': 'seller_type',
                    'dealingGbn': 'dealing_type',
                    'cdealDay': 'cancel_deal_date',
                    'cdealType': 'cancel_deal_type',
                    'estateAgentSggNm': 'estate_agent_region',
                    'jibun': 'jibun'
                }
                
            elif table_name == 'sh_rent':
                # 단독/다가구 전월세 데이터 전처리
                field_mapping = {
                    'houseType': 'house_type',
                    'deposit': 'deposit',
                    'monthlyRent': 'monthly_rent',
                    'dealYear': 'deal_year',
                    'dealMonth': 'deal_month',
                    'dealDay': 'deal_day',
                    'excluUseAr': 'exclusive_area',
                    'lotArea': 'land_area',
                    'plottageAr': 'land_area',  # 대지면적
                    'floor': 'floor_num',
                    'buildYear': 'build_year',
                    'sggCd': 'region_code',
                    'umdNm': 'region_name',
                    'contractTerm': 'contract_term',
                    'contractType': 'contract_type',
                    'jibun': 'jibun'
                }
            
            # 컬럼명 변경
            df = df.rename(columns=field_mapping)
            
            # 매핑되지 않은 컬럼 제거 (테이블에 존재하지 않는 컬럼들)
            table_columns = {
                'apt_trade': ['apt_name', 'deal_amount', 'deal_year', 'deal_month', 'deal_day', 
                             'exclusive_area', 'floor_num', 'build_year', 'region_code', 'region_name',
                             'buyer_type', 'seller_type', 'dealing_type', 'land_lease', 
                             'cancel_deal_date', 'cancel_deal_type', 'estate_agent_region', 'jibun'],
                'apt_rent': ['apt_name', 'deposit', 'monthly_rent', 'deal_year', 'deal_month', 'deal_day',
                            'exclusive_area', 'floor_num', 'build_year', 'region_code', 'region_name',
                            'contract_term', 'contract_type', 'pre_deposit', 'pre_monthly_rent', 
                            'use_rr_right', 'jibun'],
                'offi_trade': ['building_name', 'deal_amount', 'deal_year', 'deal_month', 'deal_day',
                              'exclusive_area', 'floor_num', 'build_year', 'region_code', 'region_name',
                              'buyer_type', 'seller_type', 'dealing_type', 'cancel_deal_date', 
                              'cancel_deal_type', 'estate_agent_region', 'jibun'],
                'offi_rent': ['building_name', 'deposit', 'monthly_rent', 'deal_year', 'deal_month', 'deal_day',
                             'exclusive_area', 'floor_num', 'build_year', 'region_code', 'region_name',
                             'contract_term', 'contract_type', 'jibun'],
                'sh_trade': ['house_type', 'deal_amount', 'deal_year', 'deal_month', 'deal_day',
                            'exclusive_area', 'land_area', 'floor_num', 'build_year', 'region_code', 
                            'region_name', 'buyer_type', 'seller_type', 'dealing_type', 
                            'cancel_deal_date', 'cancel_deal_type', 'estate_agent_region', 'jibun'],
                'sh_rent': ['house_type', 'deposit', 'monthly_rent', 'deal_year', 'deal_month', 'deal_day',
                           'exclusive_area', 'land_area', 'floor_num', 'build_year', 'region_code',
                           'region_name', 'contract_term', 'contract_type', 'jibun']
            }
            
            if table_name in table_columns:
                valid_columns = table_columns[table_name]
                df = df[[col for col in valid_columns if col in df.columns]]
            
            # 숫자 컬럼 변환 (pre_deposit, pre_monthly_rent 포함)
            numeric_columns = ['deal_amount', 'deposit', 'monthly_rent', 'exclusive_area', 'land_area',
                             'floor_num', 'build_year', 'deal_year', 'deal_month', 'deal_day',
                             'pre_deposit', 'pre_monthly_rent']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
            
            # 빈 문자열을 None으로 변경
            df = df.replace('', None)
            df = df.replace(' ', None)
            df = df.replace('nan', None)
            df = df.replace('NaN', None)
            
            # NaN을 None으로 변경
            df = df.where(pd.notnull(df), None)
            
            # 문자열 필드에서 숫자가 아닌 값들 정리
            string_columns = ['apt_name', 'building_name', 'house_type', 'region_name', 
                            'buyer_type', 'seller_type', 'dealing_type', 'contract_term', 
                            'contract_type', 'use_rr_right', 'jibun', 'cancel_deal_date', 
                            'cancel_deal_type', 'estate_agent_region', 'land_lease']
            
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str)
                    df[col] = df[col].replace('None', None)
                    df[col] = df[col].replace('nan', None)
            
            return df
            
        except Exception as e:
            logger.error(f"데이터 전처리 오류: {e}")
            return df
    
    def get_table_stats(self) -> Dict:
        """테이블 통계 조회"""
        try:
            tables = ['apt_trade', 'apt_rent', 'offi_trade', 'offi_rent', 'sh_trade', 'sh_rent']
            stats = {}
            
            with self.engine.connect() as conn:
                for table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    stats[table] = count
                    
            return stats
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}
    
    def remove_duplicates(self, table_name: str) -> bool:
        """테이블에서 중복 레코드 제거"""
        try:
            # 테이블별 중복 제거 기준 설정
            unique_columns = {
                'apt_trade': ['apt_name', 'deal_amount', 'deal_year', 'deal_month', 'deal_day', 'jibun'],
                'apt_rent': ['apt_name', 'deposit', 'monthly_rent', 'deal_year', 'deal_month', 'deal_day', 'jibun'],
                'offi_trade': ['building_name', 'deal_amount', 'deal_year', 'deal_month', 'deal_day', 'jibun'],
                'offi_rent': ['building_name', 'deposit', 'monthly_rent', 'deal_year', 'deal_month', 'deal_day', 'jibun'],
                'sh_trade': ['house_type', 'deal_amount', 'deal_year', 'deal_month', 'deal_day', 'jibun'],
                'sh_rent': ['house_type', 'deposit', 'monthly_rent', 'deal_year', 'deal_month', 'deal_day', 'jibun']
            }
            
            if table_name not in unique_columns:
                logger.error(f"지원하지 않는 테이블: {table_name}")
                return False
            
            columns = unique_columns[table_name]
            columns_str = ', '.join(columns)
            
            # 중복 제거 SQL 쿼리
            remove_duplicates_sql = f"""
            DELETE FROM {table_name} a USING (
                SELECT MIN(id) as id, {columns_str}
                FROM {table_name} 
                GROUP BY {columns_str} 
                HAVING COUNT(*) > 1
            ) b
            WHERE a.{columns_str.replace(', ', ' = b.').replace(columns_str, 'a.' + columns_str.replace(', ', ' AND a.'))} = b.{columns_str.replace(', ', ' AND b.')}
            AND a.id <> b.id;
            """
            
            # 더 간단한 방법으로 변경
            temp_table = f"{table_name}_temp"
            
            with self.engine.connect() as conn:
                # 1. 중복 제거된 데이터를 임시 테이블에 저장
                create_temp_sql = f"""
                CREATE TABLE {temp_table} AS
                SELECT DISTINCT ON ({columns_str}) *
                FROM {table_name}
                ORDER BY {columns_str}, id;
                """
                
                # 2. 기존 테이블 삭제
                drop_original_sql = f"DROP TABLE {table_name};"
                
                # 3. 임시 테이블을 원래 이름으로 변경
                rename_sql = f"ALTER TABLE {temp_table} RENAME TO {table_name};"
                
                conn.execute(text(create_temp_sql))
                conn.execute(text(drop_original_sql))
                conn.execute(text(rename_sql))
                conn.commit()
                
            logger.info(f"✅ {table_name} 테이블 중복 제거 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ {table_name} 중복 제거 실패: {e}")
            return False
    
    def clear_table(self, table_name: str) -> bool:
        """테이블의 모든 데이터 삭제"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {table_name}"))
                conn.commit()
            logger.info(f"✅ {table_name} 테이블 데이터 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"❌ {table_name} 테이블 삭제 실패: {e}")
            return False
    
    def clear_all_tables(self) -> bool:
        """모든 테이블의 데이터 삭제"""
        tables = ['apt_trade', 'apt_rent', 'offi_trade', 'offi_rent', 'sh_trade', 'sh_rent']
        success_count = 0
        
        for table in tables:
            if self.clear_table(table):
                success_count += 1
        
        logger.info(f"📊 {success_count}/{len(tables)} 테이블 삭제 완료")
        return success_count == len(tables)
    
    def remove_all_duplicates(self) -> bool:
        """모든 테이블에서 중복 제거"""
        tables = ['apt_trade', 'apt_rent', 'offi_trade', 'offi_rent', 'sh_trade', 'sh_rent']
        success_count = 0
        
        for table in tables:
            if self.remove_duplicates(table):
                success_count += 1
        
        logger.info(f"📊 {success_count}/{len(tables)} 테이블 중복 제거 완료")
        return success_count == len(tables)
    
    def close(self):
        """연결 종료"""
        if self.engine:
            self.engine.dispose()
            logger.info("데이터베이스 연결 종료")


if __name__ == "__main__":
    # 테스트
    db = PostgreSQLManager()
    if db.connect():
        db.create_tables()
        stats = db.get_table_stats()
        print("테이블 통계:", stats)
        db.close()