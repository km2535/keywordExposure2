# keywordExposure/src/scraper.py
import requests
from bs4 import BeautifulSoup
import time
import random
import logging # 로깅 임포트
from urllib.parse import urlparse, urlunparse 

class NaverScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36 Edg/91.0.864.71'
        ]
        self.base_url = "https://search.naver.com/search.naver"
        
    def get_random_user_agent(self):
        """무작위 User-Agent 반환"""
        return random.choice(self.user_agents)
        
    def get_search_results(self, keyword: str, page: int = 1, tab: str = "all", delay: bool = True):
        """
        네이버 검색 결과를 가져오는 함수.
        tab 인자로 검색 탭 (예: 'cafe.all' for 카페, 'all' for 통합검색) 지정 가능.
        """
        if delay:
            time.sleep(random.uniform(0.5, 1.5))
            
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        params = {
            "query": keyword,
            "start": (page - 1) * 10 + 1
        }
        
        # 탭 파라미터 추가
        if tab == "cafe.all": # 카페탭
            params["ssc"] = "tab.cafe.all"
            tab_name = "카페탭"
        elif tab == "all": # 통합검색 (메인탭)
            params["ssc"] = "tab.all" # 명시적으로 통합검색 지정
            tab_name = "메인탭"
        else: # 기타 탭
            params["ssc"] = tab
            tab_name = f"{tab} 탭" # 사용자 정의 탭 이름
            
        try:
            logging.info(f"'{keyword}' 검색 중 ({tab_name} - 페이지 {page})...") # print 대신 logging 사용
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except Exception as e:
            logging.error(f"검색 결과 가져오기 실패 ({tab_name} - 페이지 {page}): {str(e)}", exc_info=True) # print 대신 logging 사용
            return None
            
    def extract_urls(self, soup):
        """검색 결과에서 URL을 추출하는 함수"""
        urls = []
        
        # 1. 가장 효과적인 방법: 모든 a 태그를 검색하고 모든 속성 확인
        # logging.info("모든 a 태그에서 URL 추출 시도...") # 너무 많은 로그로 주석 처리
        try:
            for a_tag in soup.find_all('a'):
                for attr_name, attr_value in a_tag.attrs.items():
                    if isinstance(attr_value, str) and ('http://' in attr_value or 'https://' in attr_value):
                        # 네이버 URL에 초점
                        if 'naver.com' in attr_value:
                            urls.append(attr_value)
        except Exception as e:
            logging.error(f"a 태그 처리 중 오류: {str(e)}", exc_info=True) # print 대신 logging 사용
        
        # 2. 구조적 접근: 네이버 검색 결과에서 자주 사용되는 패턴 찾기
        try:
            nocr_elements = soup.find_all(attrs={'nocr': True})
            # logging.info(f"{len(nocr_elements)}개의 nocr 속성 요소 발견") # 너무 많은 로그로 주석 처리
            
            for elem in nocr_elements:
                if elem.name == 'a' and elem.has_attr('href'):
                    urls.append(elem['href'])
                else:
                    for inner_a in elem.find_all('a', href=True):
                        urls.append(inner_a['href'])
        except Exception as e:
            logging.error(f"nocr 요소 처리 중 오류: {str(e)}", exc_info=True) # print 대신 logging 사용
        
        # 3. 일반적인 컨테이너 클래스 접근
        try:
            containers = []
            for div in soup.find_all('div'):
                if div.has_attr('class') and len(div['class']) >= 2:
                    containers.append(div)
            
            # logging.info(f"{len(containers)}개의 잠재적 컨테이너 발견") # 너무 많은 로그로 주석 처리
            
            for container in containers:
                for a in container.find_all('a', href=True):
                    if 'naver.com' in a['href']:
                        urls.append(a['href'])
        except Exception as e:
            logging.error(f"컨테이너 처리 중 오류: {str(e)}", exc_info=True) # print 대신 logging 사용
        
        # 4. 텍스트 기반 접근
        keywords = ["cafe", "blog", "카페", "블로그", "지식인", "포스트", "뉴스"]
        try:
            for keyword_text in keywords: # 'keyword' 변수명 충돌 피하기 위해 keyword_text로 변경
                for element in soup.find_all(text=lambda t: keyword_text in t.lower() if t else False):
                    parent = element.parent
                    for a in parent.find_all('a', href=True):
                        if 'naver.com' in a['href']:
                            urls.append(a['href'])
                    if parent.parent:
                        for a in parent.parent.find_all('a', href=True):
                            if 'naver.com' in a['href']:
                                urls.append(a['href'])
        except Exception as e:
            logging.error(f"키워드 기반 검색 중 오류: {str(e)}", exc_info=True) # print 대신 logging 사용
        
        # 네이버 카페/블로그 URL 정규화 (JWT 토큰 제거)
        normalized_urls = []
        for url in urls:
            parsed = urlparse(url)
            # URL의 도메인(netloc)과 경로(path)만 사용하고 나머지는 제거
            normalized_url = urlunparse(('', parsed.netloc, parsed.path, '', '', ''))
            normalized_urls.append(normalized_url)
        
        unique_urls = list(dict.fromkeys(normalized_urls))
        logging.info(f"총 {len(unique_urls)}개의 고유 URL을 추출했습니다.")
        
        # 디버깅: 모든 URL 출력은 비활성화
        # if unique_urls:
        #     logging.info("추출된 URL 목록:")
        
        return unique_urls