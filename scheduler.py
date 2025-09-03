# keywordExposure/scheduler.py
import schedule
import time
import os
import sys
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler  # RotatingFileHandler 임포트
from src.config import DEFAULT_PAGES, SCHEDULER_INTERVAL

# main.py의 통합 실행 로직을 직접 임포트합니다.
from main import execute_monitoring_all_keywords 

# 현재 스크립트 디렉토리의 절대 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# 로깅 설정 (RotatingFileHandler 적용)
# ==============================================================================

LOG_FILENAME = os.path.join(SCRIPT_DIR, 'monitoring_scheduler.log')

# 루트 로거를 가져오고, 레벨을 설정합니다.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 기존에 붙어있을 수 있는 핸들러들을 모두 제거합니다 (중복 로깅 방지).
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 로그 출력 형식 정의
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# RotatingFileHandler 설정
# - 로그 파일 크기가 5MB가 되면 파일을 교체합니다.
# - 최대 3개의 백업 파일을 유지합니다 (monitoring_scheduler.log.1, .2, .3)
# - encoding='utf-8'은 한글 로그가 깨지지 않도록 합니다.
handler = RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3,
    encoding='utf-8'
)
handler.setFormatter(formatter)  # 핸들러에 포맷 적용

# 로거에 핸들러 추가
logger.addHandler(handler)

# ==============================================================================

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
            
        # 7시 정각에만 이메일을 보내는 로직은 아래의 스케줄러가 담당하므로 여기서는 제거하거나 주석처리해도 됩니다.
        # 아래 스케줄러('schedule.every().day.at("07:00")')가 이 역할을 대신합니다.
        # if current_hour == 7 and current_minute == 0:
        #     logging.info("예약된 시간(7시 정각)입니다. 이메일 보고서를 전송합니다.")
        #     run_email_report_scheduled()
        # else:
        #     logging.info(f"예약된 시간이 아닙니다(현재 {current_hour}시 {current_minute}분). 이메일 보고서를 전송하지 않습니다.")
                
    except Exception as e:
        logging.error(f"모니터링 실행 중 오류 발생: {e}")
        logging.error(traceback.format_exc())

def run_email_report_scheduled():
    """이메일 보고서만 전송하는 함수 (스케줄러용)"""
    logging.info("이메일 보고서 전송 작업 시작")
    
    global last_monitoring_results
    if not last_monitoring_results:
        logging.error("전송할 모니터링 결과가 없습니다. 이메일 전송을 중단합니다.")
        # 모니터링을 한번 더 실행하여 최신 결과를 가져오도록 시도할 수 있습니다.
        logging.info("결과가 없으므로, 이메일 전송 전 최신 모니터링을 시도합니다.")
        run_monitoring_task()
        if not last_monitoring_results:
            logging.error("재시도 후에도 결과가 없어 이메일 전송을 중단합니다.")
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
    # schedule.every(1).minutes.do(run_monitoring_task)  # 테스트를 위해 1분으로 변경 (원래대로 돌리려면 위 라인 사용)
    
    schedule.every().day.at("07:00").do(run_email_report_scheduled)
    
    logging.info("초기 모니터링 실행 중...")
    run_monitoring_task()
    
    logging.info(f"스케줄러가 {SCHEDULER_INTERVAL}시간마다 모니터링을 실행하도록 설정되었습니다.")
    logging.info("매일 아침 7시에 이메일 보고서를 전송하도록 설정되었습니다.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) # CPU 사용량을 줄이기 위해 1초 대기로 변경
    except KeyboardInterrupt:
        logging.info("사용자에 의해 스케줄러가 중지되었습니다.")
    except Exception as e:
        logging.error(f"스케줄러 실행 중 오류 발생: {str(e)}")
        logging.error(traceback.format_exc())