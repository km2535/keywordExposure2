# keywordExposure/scheduler.py
import schedule
import time
import os
import sys
import logging
import traceback
from datetime import datetime
from src.config import DEFAULT_PAGES, SCHEDULER_INTERVAL

# main.py의 통합 실행 로직을 직접 임포트합니다.
from main import execute_monitoring_all_keywords 

# 현재 스크립트 디렉토리의 절대 경로 (로깅 파일 경로 등을 위해 유지)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 로깅 설정: 콘솔 출력(StreamHandler)을 제거하고 파일에만 로깅
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'monitoring_scheduler.log'))
        # logging.StreamHandler() # 이 줄을 제거하여 콘솔 출력 비활성화
    ]
)

# email_reporter 모듈을 확실히 로드하기 위해 시스템 경로에 현재 디렉토리 추가
sys.path.insert(0, SCRIPT_DIR) 

# 이제 email_reporter를 임포트
try:
    from email_reporter import send_email_report
    logging.info("email_reporter 모듈을 성공적으로 로드했습니다.")
except ImportError as e:
    logging.error(f"email_reporter 모듈 로드 실패: {str(e)}")
    logging.error(f"시스템 경로: {sys.path}")
    sys.exit(1)

# 모니터링 결과를 저장할 전역 변수 (이메일 전송 시 사용)
last_monitoring_results = {}

def run_monitoring_task():
    """모니터링 스크립트 실행"""
    logging.info("모니터링 작업 시작")
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    
    logging.info(f"실행 시간: {current_time}")
    
    # main.py의 핵심 통합 로직을 직접 호출
    global last_monitoring_results
    try:
        logging.info("모니터링 실행 함수 호출 시작")
        results_from_monitoring = execute_monitoring_all_keywords(DEFAULT_PAGES)
        
        if results_from_monitoring:
            last_monitoring_results = results_from_monitoring
            logging.info("모니터링 작업 완료")
        else:
            logging.warning("모니터링 결과가 비어 있습니다. 이메일 보고서 전송이 어려울 수 있습니다.")
            
        if current_hour == 7 and current_minute == 0:
            logging.info("예약된 시간(7시 정각)입니다. 이메일 보고서를 전송합니다.")
            run_email_report_scheduled()
        else:
            logging.info(f"예약된 시간이 아닙니다(현재 {current_hour}시 {current_minute}분). 이메일 보고서를 전송하지 않습니다.")
                
    except Exception as e:
        logging.error(f"모니터링 실행 중 오류 발생: {e}")
        logging.error(traceback.format_exc())

def run_email_report_scheduled():
    """이메일 보고서만 전송하는 함수 (스케줄러용)"""
    logging.info("이메일 보고서 전송 작업 시작")
    
    global last_monitoring_results
    if not last_monitoring_results:
        logging.error("전송할 모니터링 결과가 없습니다. 이메일 전송을 중단합니다.")
        return False

    try:
        logging.info("이메일 전송 함수 호출 시작")
        email_sent = send_email_report(last_monitoring_results)
        
        if email_sent:
            logging.info("이메일 보고서 전송 완료")
            return True
        else:
            logging.error("이메일 보고서 전송 실패")
            return False
    except Exception as e:
        logging.error(f"이메일 보고서 전송 중 예외 발생: {str(e)}")
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logging.info("네이버 검색 노출 모니터링 스케줄러가 시작되었습니다.")
    
    schedule.every(SCHEDULER_INTERVAL).hours.do(run_monitoring_task)
    
    schedule.every().day.at("07:00").do(run_email_report_scheduled)
    
    logging.info("초기 모니터링 실행 중...")
    run_monitoring_task()
    
    logging.info(f"스케줄러가 {SCHEDULER_INTERVAL}시간마다 모니터링을 실행하도록 설정되었습니다.")
    logging.info("매일 아침 7시에 이메일 보고서를 전송하도록 설정되었습니다.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("사용자에 의해 스케줄러가 중지되었습니다.")
    except Exception as e:
        logging.error(f"스케줄러 실행 중 오류 발생: {str(e)}")
        logging.error(traceback.format_exc())