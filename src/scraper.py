# keywordExposure/src/scraper.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time
import random
import logging

class NaverScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0' 
        ]
        self.referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://search.yahoo.com/",
            "https://duckduckgo.com/",
            "https://www.youtube.com/"
        ]
        self.base_url = "https://search.naver.com/search.naver"
        self.session = self._create_session() # 클래스 생성 시 세션 객체 생성

    def _create_session(self):
        """
        재시도 로직과 헤더가 설정된 requests.Session 객체를 생성합니다.
        """
        session = requests.Session()
        
        # 기본 헤더 설정 (세션 전체에 적용)
        session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "User-Agent": random.choice(self.user_agents),
            "Referer": random.choice(self.referers), # Referer를 랜덤화
        })
        
        # 재시도 전략 설정 (네트워크 오류 등에 대응)
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def get_search_results(self, keyword: str, page: int = 1, tab: str = "all", delay: bool = True):
        if delay:
            time.sleep(random.uniform(1.5, 3.0)) # 딜레이 시간을 더 늘립니다.

        params = {
            "query": keyword,
        }
        
        tab_name = f"{tab} 탭"
        if tab == "cafe.all":
            params.update({
                "ssc": "tab.cafe.all"
            })
            tab_name = "카페탭"
        elif tab == "all":
            params.update({"sm": "top_hty", "ssc": "tab.all", "start": (page - 1) * 10 + 1})
            tab_name = "메인탭"
        else:
            params["ssc"] = tab
            
        try:
            logging.info(f"'{keyword}' 검색 중 ({tab_name} - 페이지 {page})...")
            # self.session.get을 사용하여 요청
            response = self.session.get(self.base_url, params=params, timeout=10)
            
            # 403 Forbidden 같은 클라이언트 오류는 여기서 직접 처리
            if response.status_code == 403:
                logging.error(f"'{keyword}' 검색 실패: 403 Forbidden - 서버에서 접근을 차단했습니다. 잠시 후 다시 시도합니다.")
                # 세션의 User-Agent를 변경하여 다음 요청에 대비
                self.session.headers.update({"User-Agent": random.choice(self.user_agents)})
                return None
            
            response.raise_for_status() # 403 이외의 다른 HTTP 오류 발생 시 예외 발생
            
            return BeautifulSoup(response.text, 'html.parser')
            
        except requests.exceptions.RequestException as e:
            logging.error(f"검색 중 심각한 오류 발생 ({tab_name} - '{keyword}'): {e}", exc_info=False)
            return None

    def normalize_url(self, url: str) -> str:
        """URL에서 불필요한 쿼리 파라미터를 제거하여 정규화합니다."""
        if '?' in url:
            return url.split('?')[0]
        return url

    def extract_urls(self, soup: BeautifulSoup) -> list:
        if not soup:
            return []

        links = soup.select('a.title_link, a.api_txt_lines, a.total_tit, a.sub_link, .total_tit a, a.fds-comps-right-image-text-title, a.dsc_link')
        
        extracted_urls = set()
        for link in links:
            href = link.get('href')
            if href and ('cafe.naver.com' in href or 'blog.naver.com' in href):
                normalized = self.normalize_url(href)
                extracted_urls.add(normalized)
        
        unique_urls = list(extracted_urls)
        logging.info(f"총 {len(unique_urls)}개의 고유 URL을 추출했습니다.")
        return unique_urls