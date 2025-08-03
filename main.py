# keywordExposure/main.py
import os
import argparse
import sys
import logging
from datetime import datetime
import pytz
from src.scraper import NaverScraper
from src.monitor import KeywordMonitor
from src.reporter import Reporter
from src.config import DEFAULT_PAGES
from src.notion_manager import NotionClient, NotionAPIError

def execute_monitoring_all_keywords(pages_to_check: int) -> dict:
    overall_monitoring_results = {}

    try:
        notion_client = NotionClient()
        all_notion_pages = notion_client.query_all_pages() 

    except NotionAPIError as e:
        logging.error(f"Notion API 오류: {e}", exc_info=True)
        return {}
    except Exception as e:
        logging.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        return {}


    all_keywords_from_notion = []
    for page in all_notion_pages:
        properties = page.get("properties", {})
        page_id = page.get("id")

        keyword_property = properties.get("키워드", {}).get("title")
        keyword_text = keyword_property[0].get("plain_text") if keyword_property and len(keyword_property) > 0 else None
        
        urls_list = []
        original_url_property = properties.get("작성 글 URL", {}).get("url")
        if original_url_property:
            urls_list.append(original_url_property.strip())

        if keyword_text:
            all_keywords_from_notion.append({
                "keyword": keyword_text,
                "urls": urls_list,
                "page_id": page_id,
                "current_properties": properties 
            })

    if not all_keywords_from_notion:
        logging.warning("노션 데이터베이스에서 모니터링할 키워드를 찾을 수 없습니다.")
        return {}

    logging.info(f"노션에서 총 {len(all_keywords_from_notion)}개의 키워드를 가져와 모니터링합니다.")

    scraper = NaverScraper()
    monitor = KeywordMonitor(scraper, all_keywords_from_notion)
    
    logging.info("네이버 검색 노출 모니터링을 시작합니다...")
    results = monitor.monitor_keywords(pages_to_check=pages_to_check)
    
    reporter = Reporter(results) 
    
    overall_monitoring_results = results
    
    # === "상위 노출 여부" 및 "업데이트 날짜" 속성 업데이트 로직 ===
    logging.info("⏳ 노션 데이터베이스 '상위 노출 여부' 및 '업데이트 날짜' 속성 업데이트 시작...")
    
    kst_timezone = pytz.timezone('Asia/Seoul')
    current_datetime_kst = datetime.now(kst_timezone)
    current_datetime_iso = current_datetime_kst.strftime("%Y-%m-%dT%H:%M:%S%z")

    for keyword_result_item in overall_monitoring_results.get("results", []):
        page_id = keyword_result_item.get("page_id")
        keyword = keyword_result_item.get("keyword")
        
        # monitor.py에서 새로 추가된 exposure_status를 가져옵니다.
        new_exposure_status_name = keyword_result_item.get("exposure_status") 

        current_notion_properties = None
        for item in all_keywords_from_notion:
            if item.get("page_id") == page_id:
                current_notion_properties = item.get("current_properties", {})
                break

        if not page_id or not current_notion_properties:
            logging.warning(f"키워드 '{keyword}'에 대한 페이지 ID 또는 현재 속성을 찾을 수 없어 '상위 노출 여부'를 업데이트할 수 없습니다.")
            continue

        current_exposure_status_prop = current_notion_properties.get("상위 노출 여부", {}).get("status")
        current_status_name_in_notion = current_exposure_status_prop.get("name") if current_exposure_status_prop else "N/A"

        # 새로운 상태가 현재 노션의 상태와 다를 경우에만 업데이트 수행
        if new_exposure_status_name and new_exposure_status_name != current_status_name_in_notion:
            properties_to_update = {
                "상위 노출 여부": { 
                    "status": {
                        "name": new_exposure_status_name # monitor.py에서 결정된 상태 사용
                    }
                },
                "업데이트 날짜": { 
                    "date": {
                        "start": current_datetime_iso, 
                        "end": None 
                    }
                }
            }
            
            try:
                notion_client.update_page(page_id=page_id, properties=properties_to_update)
                logging.info(f"키워드 '{keyword}' (ID: {page_id})의 '상위 노출 여부'를 '{new_exposure_status_name}'으로 변경하고 '업데이트 날짜'를 '{current_datetime_iso}'으로 업데이트 완료. (이전 상태: '{current_status_name_in_notion}')")
            except NotionAPIError as e:
                logging.error(f"키워드 '{keyword}' (ID: {page_id})의 '상위 노출 여부' 업데이트 실패: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"키워드 '{keyword}' (ID: {page_id}) 업데이트 중 예상치 못한 오류 발생: {e}", exc_info=True)
        else:
            logging.info(f"키워드 '{keyword}' (ID: {page_id})의 '상위 노출 여부'가 변경되지 않아 업데이트를 건너뜁니다. (현재: '{current_status_name_in_notion}')")

    logging.info("✅ 노션 데이터베이스 '상위 노출 여부' 속성 업데이트 완료.")
    # === "상위 노출 여부" 및 "업데이트 날짜" 속성 업데이트 로직 끝 ===

    return overall_monitoring_results

def main():
    logging.info("main.py 실행")
    parser = argparse.ArgumentParser(description='네이버 검색 노출 모니터링 도구')
    parser.add_argument('--pages', type=int, default=DEFAULT_PAGES, help='검색할 페이지 수')
    parser.add_argument('--category', type=str, default='all', 
                      help='모니터링할 키워드 카테고리 (이제 모든 키워드를 통합하여 처리)')
    parser.add_argument('--all-categories', action='store_true',
                      help='모든 카테고리 실행 (이제 기본 동작)')
    
    args = parser.parse_args()
    
    execute_monitoring_all_keywords(args.pages)
    
if __name__ == "__main__":
    main()