# keywordExposure/email_reporter.py
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging # 로깅 임포트
from src.config import (
    EMAIL_SENDER, 
    EMAIL_PASSWORD, 
    EMAIL_RECIPIENTS
)

def generate_html_report(results_data: dict):
    """요약된 HTML 형식의 이메일 보고서 생성 (통합 보고서)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #333366; }}
            h2 {{ color: #666699; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            .summary-card {{ 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 15px; 
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .card-header {{ 
                font-size: 18px; 
                font-weight: bold; 
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 1px solid #eee;
            }}
            .stat-container {{
                display: flex;
                justify-content: space-between;
                flex-wrap: wrap;
            }}
            .stat-box {{
                flex: 1;
                min-width: 120px;
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                text-align: center;
            }}
            .success-box {{ background-color: rgba(0, 128, 0, 0.1); border: 1px solid rgba(0, 128, 0, 0.3); }}
            .warning-box {{ background-color: rgba(255, 165, 0, 0.1); border: 1px solid rgba(255, 165, 0, 0.3); }}
            .danger-box {{ background-color: rgba(255, 0, 0, 0.1); border: 1px solid rgba(255, 0, 0, 0.3); }}
            .number {{ font-size: 24px; font-weight: bold; margin: 5px 0; }}
            .label {{ font-size: 14px; color: #666; }}
            .success {{ color: green; }}
            .warning {{ color: orange; }}
            .danger {{ color: red; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; border-top: 1px solid #eee; padding-top: 10px; }}
            .detail-toggle {{ 
                background-color: #f8f8f8; 
                border: none; 
                padding: 8px 15px; 
                margin-top: 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                color: #666;
            }}
            .detail-toggle:hover {{ background-color: #ebebeb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>네이버 검색 노출 모니터링 통합 리포트</h1>
            <p>생성 시간: {now}</p>
    """
    
    total_exposed = 0
    total_not_exposed = 0
    total_no_url = 0
    total_valid_keywords = 0
    
    for keyword_result in results_data.get("results", []):
        keyword = keyword_result.get("keyword", "")
        urls = keyword_result.get("urls", [])
        
        if not urls:
            total_no_url += 1
            continue
            
        total_valid_keywords += 1
        exposed_count_in_item = sum(1 for url_item in urls if url_item.get("is_exposed", False))
        
        if exposed_count_in_item > 0:
            total_exposed += 1
        else:
            total_not_exposed += 1
    
    exposure_rate = 0 if total_valid_keywords == 0 else round(total_exposed / total_valid_keywords * 100)
    
    html += f"""
        <div class="summary-card">
            <div class="card-header">전체 키워드 노출 요약</div>
            <p>최종 업데이트: {results_data.get('timestamp', '알 수 없음')}</p>
            
            <div class="stat-container">
                <div class="stat-box success-box">
                    <div class="number success">{total_exposed}</div>
                    <div class="label">노출된 키워드</div>
                </div>
                <div class="stat-box danger-box">
                    <div class="number danger">{total_not_exposed}</div>
                    <div class="label">노출되지 않은 키워드</div>
                </div>
                <div class="stat-box warning-box">
                    <div class="number warning">{total_no_url}</div>
                    <div class="label">발행하지 않은 키워드</div>
                </div>
            </div>
            
            <p><strong>전체 노출률:</strong> <span class="{'success' if exposure_rate >= 70 else 'warning' if exposure_rate >= 30 else 'danger'}">{exposure_rate}%</span> (발행한 키워드 중)</p>
            <p><strong>발행한 키워드 총계:</strong> {total_valid_keywords} 개</p>
            <p><strong>전체 키워드 총계 (발행 + 미발행):</strong> {total_valid_keywords + total_no_url} 개</p>
        </div>
    """
    
    html += """
            <div class="footer">
                <p>이 이메일은 자동으로 생성되었습니다. 문의사항이 있으시면 관리자에게 연락하세요.</p>
                <p>※ 상세 정보는 <a href='https://minsweb.shop'>minsweb.shop</a>에서 확인하실 수 있습니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_email_report(results_data: dict):
    """이메일 보고서 전송"""
    logging.info(f"이메일 보고서 생성 중...") # print 대신 logging 사용
    
    try:
        today_date = datetime.now().strftime("%Y-%m-%d")
        email_subject = f"네이버 검색 노출 모니터링 통합 리포트 ({today_date})"
        
        html_content = generate_html_report(results_data)
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = ", ".join(EMAIL_RECIPIENTS)
        msg['Subject'] = email_subject
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            
        logging.info(f"이메일 보고서가 성공적으로 전송되었습니다.") # print 대신 logging 사용
        return True
    except Exception as e:
        logging.error(f"이메일 전송 중 오류 발생: {str(e)}", exc_info=True) # print 대신 logging 사용, 트레이스백 포함
        return False