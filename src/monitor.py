# keywordExposure/src/monitor.py
import json
import os
from datetime import datetime
from tqdm import tqdm
import logging # 로깅 임포트
# from src.config import OUTPUT_DIR

class KeywordMonitor:
    def __init__(self, scraper, keywords_list: list):
        self.scraper = scraper
        self.keywords_list = keywords_list
    
    @staticmethod
    def normalize_url(url):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        # URL의 도메인(netloc)과 경로(path)만 사용하여 비교
        # 프로토콜(scheme), 쿼리 파라미터, fragment는 모두 제거
        return parsed.netloc + parsed.path

    def check_url_in_results(self, target_url: str, search_urls: list) -> bool:
        """주어진 URL이 검색 결과에 포함되는지 확인 (정규화된 URL 비교)"""
        normalized_target = self.normalize_url(target_url)
        for url_in_search_results in search_urls:
            if self.normalize_url(url_in_search_results) == normalized_target:
                return True
        return False
        
    def monitor_keywords(self, pages_to_check=1):
        """모든 키워드 모니터링 - 이제 Notion에서 받은 키워드 리스트를 사용"""
        results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": []
        }
        
        valid_keywords = [item for item in self.keywords_list if item["urls"]]
        skipped_keywords = [item for item in self.keywords_list if not item["urls"]]
        
        logging.info(f"총 {len(valid_keywords)} 개의 키워드를 모니터링합니다...")
        if skipped_keywords:
            logging.warning(f"{len(skipped_keywords)} 개의 키워드는 URL이 없어 건너뜁니다.")
        
        for item in tqdm(valid_keywords, desc="키워드 검색 중"):
            keyword = item["keyword"]
            target_urls = item["urls"] # 리스트 형태일 수 있음
            page_id = item.get("page_id")
            
            logging.info(f"\n키워드 '{keyword}' 검색 중...")
            
            # 여기서 각 target_url에 대해 개별적으로 검사 로직을 수행합니다.
            # 하나의 키워드에 여러 target_url이 있을 수 있습니다.
            # 사용자 요구사항은 '간암 1기' 같은 단일 키워드에 대한 단일 URL 검사로 보입니다.
            # 만약 키워드당 하나의 대표 URL만 검사한다면 target_urls[0]을 사용합니다.
            # 여기서는 모든 target_urls에 대해 검사하되, 최종 상태는 모든 URL의 검사 결과를 종합하여 결정합니다.

            final_exposure_status = "미발행" # 기본값

            if not target_urls: # URL이 없는 경우 (이전 skipped_keywords에서 처리되지만, 만약을 위해)
                final_exposure_status = "미발행" 
                logging.info(f"  키워드 '{keyword}': 타겟 URL이 없어 '미발행' 처리합니다.")
            else:
                # 사용자 요구사항에 따라 첫 번째 타겟 URL만 검사한다고 가정합니다.
                # (하나의 키워드에 여러 URL이 있을 때의 복잡도를 줄이기 위함)
                # 만약 모든 URL이 이 로직을 따라야 한다면 루프를 추가해야 합니다.
                url_to_check = target_urls[0] # 첫 번째 URL만 검사 (대표 URL로 가정)
                
                # 1. 카페탭 검사
                logging.info(f"  URL '{url_to_check}'의 카페탭 노출 여부 확인 중...")
                cafe_soup = self.scraper.get_search_results(keyword, page=1, tab="cafe.all")
                cafe_urls = self.scraper.extract_urls(cafe_soup) if cafe_soup else []
                is_on_cafe_tab = self.check_url_in_results(url_to_check, cafe_urls)
                logging.info(f"  URL '{url_to_check}' 카페탭에 { '있음' if is_on_cafe_tab else '없음' }")

                if is_on_cafe_tab:
                    # 2. 메인탭 검사 (카페탭에 있을 경우에만)
                    logging.info(f"  URL '{url_to_check}'의 메인탭 노출 여부 확인 중...")
                    main_soup = self.scraper.get_search_results(keyword, page=1, tab="all")
                    main_urls = self.scraper.extract_urls(main_soup) if main_soup else []
                    is_on_main_tab = self.check_url_in_results(url_to_check, main_urls)
                    logging.info(f"  URL '{url_to_check}' 메인탭에 { '있음' if is_on_main_tab else '없음' }")

                    if is_on_main_tab:
                        final_exposure_status = "최상단 노출"
                        logging.info(f"  키워드 '{keyword}': 카페탭 및 메인탭 모두 노출 -> '최상단 노출'")
                    else:
                        final_exposure_status = "노출X"
                        logging.info(f"  키워드 '{keyword}': 카페탭에만 노출 -> '노출X'")
                else:
                    final_exposure_status = "저품질"
                    logging.info(f"  키워드 '{keyword}': 카페탭에 노출되지 않음 -> '저품질'")
            
            # 결과 저장 형식
            url_results_for_item = []
            # 모든 target_urls를 포함하되, 대표 URL의 is_exposed만 업데이트된 것으로 간주
            for i, url in enumerate(target_urls):
                url_results_for_item.append({
                    "url": url,
                    "is_exposed": (final_exposure_status == "최상단 노출") # 최상단 노출일 때만 True로 표시
                    # 더 상세한 상태를 저장하려면 여기에 final_exposure_status를 추가할 수 있습니다.
                })

            keyword_result = {
                "keyword": keyword,
                "urls": url_results_for_item, # 대표 URL 검사 결과가 반영된 urls 리스트
                "page_id": page_id,
                "exposure_status": final_exposure_status # 새로운 노출 상태 추가
            }
            results["results"].append(keyword_result)
        
        # URL이 없는 키워드 처리 (skipped_keywords)
        for item in skipped_keywords:
            keyword_result = {
                "keyword": item["keyword"],
                "urls": [],
                "page_id": item.get("page_id"),
                "exposure_status": "미발행" # URL이 없으므로 '미발행'
            }
            results["results"].append(keyword_result)
            
        logging.info("모니터링 결과가 생성되었습니다.")
        return results