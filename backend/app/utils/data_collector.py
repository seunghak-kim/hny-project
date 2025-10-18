#!/usr/bin/env python3
"""
부동산 실거래가 데이터 수집기 (2025년 1월 기준)
PostgreSQL 저장 포함
"""

from building_api import TransactionPriceAPI, RegionCodeManager
from database_config import PostgreSQLManager
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RealEstateDataCollector:
    """부동산 실거래가 데이터 수집기"""
    
    def __init__(self):
        self.api = TransactionPriceAPI()
        self.db = PostgreSQLManager()
        self.region_manager = RegionCodeManager()
        
        # 2025년 1월 설정
        self.target_year_month = "202501"
        
        # 주요 지역 코드 (강남3구 + 추가 지역)
        self.target_regions = {
            "11680": "강남구",
            "11650": "서초구", 
            "11710": "송파구",
        }
        
        # 수집할 데이터 타입
        self.data_types = [
            ('apt_trade', 'apt_trade', '아파트 매매'),
            ('apt_rent', 'apt_rent', '아파트 전월세'),
            ('offi_trade', 'offi_trade', '오피스텔 매매'),
            ('offi_rent', 'offi_rent', '오피스텔 전월세'),
            ('sh_trade', 'sh_trade', '단독/다가구 매매'),
            ('sh_rent', 'sh_rent', '단독/다가구 전월세')
        ]
    
    def setup_database(self) -> bool:
        """데이터베이스 초기 설정"""
        logger.info("🔧 데이터베이스 설정 시작...")
        
        if not self.db.connect():
            logger.error("데이터베이스 연결 실패")
            return False
            
        if not self.db.create_tables():
            logger.error("테이블 생성 실패")
            return False
            
        logger.info("✅ 데이터베이스 설정 완료")
        return True
    
    def collect_region_data(self, region_code: str, region_name: str) -> Dict:
        """특정 지역의 모든 데이터 수집"""
        logger.info(f"📍 {region_name}({region_code}) 데이터 수집 시작...")
        
        results = {
            'region_code': region_code,
            'region_name': region_name,
            'data': {},
            'summary': {}
        }
        
        for api_type, table_name, description in self.data_types:
            logger.info(f"  🔍 {description} 수집 중...")
            
            try:
                # API 메서드 동적 호출
                if api_type == 'apt_trade':
                    data = self.api.get_apt_trade_data(region_code, self.target_year_month, "1000", debug=False)
                elif api_type == 'apt_rent':
                    data = self.api.get_apt_rent_data(region_code, self.target_year_month, "1000", debug=False)
                elif api_type == 'offi_trade':
                    data = self.api.get_offi_trade_data(region_code, self.target_year_month, "1000", debug=False)
                elif api_type == 'offi_rent':
                    data = self.api.get_offi_rent_data(region_code, self.target_year_month, "1000", debug=False)
                elif api_type == 'sh_trade':
                    data = self.api.get_sh_trade_data(region_code, self.target_year_month, "1000", debug=False)
                elif api_type == 'sh_rent':
                    data = self.api.get_sh_rent_data(region_code, self.target_year_month, "1000", debug=False)
                
                if data['success'] and data['data']:
                    results['data'][table_name] = data['data']
                    results['summary'][description] = len(data['data'])
                    logger.info(f"    ✅ {description}: {len(data['data'])}건 수집")
                else:
                    results['data'][table_name] = []
                    results['summary'][description] = 0
                    logger.info(f"    ⚠️ {description}: 데이터 없음")
                
                # API 호출 간격
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"    ❌ {description} 수집 실패: {e}")
                results['data'][table_name] = []
                results['summary'][description] = 0
        
        total_collected = sum(results['summary'].values())
        logger.info(f"📊 {region_name} 총 수집: {total_collected}건")
        
        return results
    
    def save_to_database(self, region_data: Dict) -> bool:
        """데이터베이스 저장"""
        region_name = region_data['region_name']
        logger.info(f"💾 {region_name} 데이터베이스 저장 시작...")
        
        success_count = 0
        total_count = len(self.data_types)
        
        for api_type, table_name, description in self.data_types:
            data = region_data['data'].get(table_name, [])
            
            if data:
                if self.db.insert_data(data, table_name):
                    logger.info(f"    ✅ {description}: {len(data)}건 저장 완료")
                    success_count += 1
                else:
                    logger.error(f"    ❌ {description}: 저장 실패")
            else:
                logger.info(f"    ⚠️ {description}: 저장할 데이터 없음")
                success_count += 1  # 데이터가 없는 것도 정상으로 처리
        
        success_rate = success_count / total_count * 100
        logger.info(f"📈 {region_name} 저장 완료율: {success_rate:.1f}%")
        
        return success_rate == 100.0
    
    def collect_all_regions(self) -> Dict:
        """모든 지역 데이터 수집"""
        logger.info("🚀 전체 지역 데이터 수집 시작...")
        logger.info(f"📅 수집 기간: {self.target_year_month[:4]}년 {self.target_year_month[4:]}월")
        logger.info(f"🎯 대상 지역: {len(self.target_regions)}개 지역")
        
        start_time = datetime.now()
        overall_results = {
            'start_time': start_time,
            'regions': {},
            'summary': {
                'total_regions': len(self.target_regions),
                'success_regions': 0,
                'total_records': 0,
                'by_type': {}
            }
        }
        
        # 데이터베이스 설정
        if not self.setup_database():
            logger.error("데이터베이스 설정 실패로 수집 중단")
            return overall_results
        
        # 각 지역별 데이터 수집
        for region_code, region_name in self.target_regions.items():
            try:
                # 데이터 수집
                region_data = self.collect_region_data(region_code, region_name)
                
                # 데이터베이스 저장
                if self.save_to_database(region_data):
                    overall_results['summary']['success_regions'] += 1
                
                # 결과 저장
                overall_results['regions'][region_code] = region_data
                
                # 전체 통계 업데이트
                for data_type, count in region_data['summary'].items():
                    if data_type not in overall_results['summary']['by_type']:
                        overall_results['summary']['by_type'][data_type] = 0
                    overall_results['summary']['by_type'][data_type] += count
                    overall_results['summary']['total_records'] += count
                
                logger.info(f"✅ {region_name} 처리 완료\n")
                
            except Exception as e:
                logger.error(f"❌ {region_name} 처리 중 오류: {e}\n")
                continue
        
        # 최종 결과
        end_time = datetime.now()
        duration = end_time - start_time
        overall_results['end_time'] = end_time
        overall_results['duration'] = duration
        
        self.print_final_summary(overall_results)
        
        return overall_results
    
    def print_final_summary(self, results: Dict):
        """최종 수집 결과 요약"""
        logger.info("=" * 60)
        logger.info("🎯 데이터 수집 최종 결과")
        logger.info("=" * 60)
        
        summary = results['summary']
        duration = results['duration']
        
        logger.info(f"📊 전체 통계:")
        logger.info(f"  • 처리 지역: {summary['success_regions']}/{summary['total_regions']} ({summary['success_regions']/summary['total_regions']*100:.1f}%)")
        logger.info(f"  • 총 수집 건수: {summary['total_records']:,}건")
        logger.info(f"  • 소요 시간: {duration}")
        
        logger.info(f"\n📈 데이터 타입별 수집 현황:")
        for data_type, count in summary['by_type'].items():
            logger.info(f"  • {data_type}: {count:,}건")
        
        # 데이터베이스 최종 통계
        db_stats = self.db.get_table_stats()
        logger.info(f"\n💾 데이터베이스 저장 현황:")
        for table, count in db_stats.items():
            logger.info(f"  • {table}: {count:,}건")
        
        logger.info("=" * 60)
    
    def export_to_csv(self, results: Dict, output_dir: str = "../../data/data_real_estate_exports"):
        """결과를 CSV로 내보내기"""
        import os
        
        logger.info("📤 CSV 내보내기 시작...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        for region_code, region_data in results['regions'].items():
            region_name = region_data['region_name']
            
            for table_name, data in region_data['data'].items():
                if data:
                    df = pd.DataFrame(data)
                    filename = f"{output_dir}/{region_name}_{table_name}_{self.target_year_month}.csv"
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                    logger.info(f"  ✅ {filename} 저장 완료")
        
        logger.info("📤 CSV 내보내기 완료")


def main():
    """메인 실행 함수"""
    print("🏠 부동산 실거래가 데이터 수집기 시작")
    print("📅 수집 대상: 2025년 1월")
    print("🎯 수집 타입: 아파트/오피스텔/단독다가구 매매/전월세")
    print("💾 저장소: PostgreSQL")
    print("-" * 50)
    
    collector = RealEstateDataCollector()
    
    try:
        # 전체 데이터 수집
        results = collector.collect_all_regions()
        
        # CSV 내보내기 (선택사항)
        collector.export_to_csv(results)
        
        print("\n🎉 데이터 수집 완료!")
        
    except Exception as e:
        logger.error(f"❌ 데이터 수집 중 오류 발생: {e}")
    
    finally:
        # 데이터베이스 연결 종료
        collector.db.close()


if __name__ == "__main__":
    main()