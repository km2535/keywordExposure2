# keywordExposure/src/reporter.py
import json
import os
from datetime import datetime
from tabulate import tabulate
import logging # 로깅 임포트
# from src.config import OUTPUT_DIR

class Reporter:
    def __init__(self, results_data: dict):
        self.results_data = results_data 
        
    def load_results(self):
        return self.results_data
            
    def generate_summary_text(self) -> str: # 함수명 변경 및 문자열 반환하도록 수정
        """키워드 노출 요약 문자열 생성 (통합 보고서)"""
        summary = self.generate_summary() # 기존 generate_summary 로직 재사용
        
        report_text = []
        report_text.append("=" * 50)
        report_text.append(f" 네이버 검색 노출 모니터링 통합 보고서")
        report_text.append("=" * 50)
        report_text.append(f"생성 시간: {summary['timestamp']}")
        
        report_text.append("\n[노출된 키워드]")
        if summary["exposed"]:
            exposed_data = [(item["keyword"], item["status"]) for item in summary["exposed"]]
            report_text.append(tabulate(exposed_data, headers=["키워드", "상태"], tablefmt="grid"))
        else:
            report_text.append("노출된 키워드가 없습니다.")
            
        report_text.append("\n[노출되지 않은 키워드]")
        if summary["not_exposed"]:
            not_exposed_data = [(item["keyword"], item["status"]) for item in summary["not_exposed"]]
            report_text.append(tabulate(not_exposed_data, headers=["키워드", "상태"], tablefmt="grid"))
        else:
            report_text.append("모든 키워드가 노출되었습니다.")
        
        return "\n".join(report_text)
    
    def generate_summary(self): # 이 함수는 내부적으로 요약 데이터를 생성하는 역할
        """키워드 노출 요약 데이터 생성 (내부용)"""
        results = self.results_data
        
        summary = {
            "timestamp": results["timestamp"],
            "exposed": [],
            "not_exposed": []
        }
        
        for keyword_result in results["results"]:
            keyword = keyword_result["keyword"]
            urls = keyword_result["urls"]
            
            all_exposed = all(url["is_exposed"] for url in urls) if urls else False
            any_exposed = any(url["is_exposed"] for url in urls) if urls else False
            
            exposed_count = sum(1 for url in urls if url["is_exposed"])
            total_count = len(urls)
            
            if total_count == 0:
                 summary["not_exposed"].append({
                    "keyword": keyword,
                    "status": "발행하지 않은 키워드"
                })
            elif all_exposed:
                summary["exposed"].append({
                    "keyword": keyword,
                    "status": f"모든 URL 노출 ({exposed_count}/{total_count})"
                })
            elif any_exposed:
                summary["exposed"].append({
                    "keyword": keyword,
                    "status": f"일부 URL 노출 ({exposed_count}/{total_count})"
                })
            else:
                summary["not_exposed"].append({
                    "keyword": keyword,
                    "status": f"노출 없음 (0/{total_count})"
                })
                
        return summary
        
    def print_report(self): # 이 메소드는 더 이상 콘솔 출력을 하지 않음
        logging.info("Reporter.print_report() 호출됨 (콘솔 출력은 비활성화됨).")
        # 실제 콘솔 출력을 원하지 않으므로, 이 메소드에서는 아무것도 출력하지 않습니다.
        # 필요하다면 generate_summary_text()를 호출하여 내용을 로깅할 수 있습니다.
        # logging.info(self.generate_summary_text())
    
    def export_json(self):
        logging.info("JSON 결과 내보내기 기능은 비활성화되었습니다.")
        pass