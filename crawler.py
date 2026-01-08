"""
K-Startup 크롤러 - 초간단 버전
"""

import os
import json
import time
import hashlib
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# 설정
SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS", "{}"))

def get_sheets():
    """Google Sheets 연결"""
    creds = Credentials.from_service_account_info(
        GOOGLE_CREDS,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_KEY)

def crawl_k_startup():
    """
    K-Startup 크롤링
    
    실제 사이트 구조에 맞춰 수정 필요!
    여기서는 예시 구조만 제공
    """
    print("K-Startup 크롤링 시작...")
    
    grants = []
    
    # 예시 URL (실제로는 K-Startup 공고 페이지)
    url = "https://www.k-startup.go.kr/web/contents/bizPbanc.do"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 예시: 실제 사이트 구조에 맞춰 선택자 수정 필요
        # 공고 항목 찾기 (가상의 선택자)
        items = soup.select('.notice-item')[:10]  # 최대 10개
        
        for item in items:
            try:
                title_elem = item.select_one('.title')
                link_elem = item.select_one('a')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    href = link_elem.get('href', '')
                    url = f"https://www.k-startup.go.kr{href}" if not href.startswith('http') else href
                    
                    # ID 생성
                    grant_id = hashlib.md5(f"kstartup_{title}".encode()).hexdigest()[:16]
                    
                    grants.append({
                        'id': grant_id,
                        'title': title,
                        'organization': 'K-Startup',
                        'deadline': '',
                        'url': url,
                        'keywords': '',
                        'description': title
                    })
                    
                    print(f"  ✓ {title[:50]}...")
            
            except Exception as e:
                print(f"  ✗ 항목 파싱 오류: {e}")
                continue
        
        time.sleep(2)  # 요청 간격
    
    except Exception as e:
        print(f"크롤링 오류: {e}")
    
    print(f"크롤링 완료: {len(grants)}건")
    return grants

def save_grants(grants):
    """공고 저장"""
    try:
        sheet = get_sheets().worksheet("grants")
        
        # 기존 ID 목록
        existing_ids = set()
        try:
            records = sheet.get_all_records()
            existing_ids = {r['id'] for r in records if 'id' in r}
        except:
            # 시트가 비어있으면 헤더 추가
            sheet.append_row(['id', 'title', 'organization', 'deadline', 'url', 'keywords', 'description'])
        
        # 신규만 저장
        new_count = 0
        for grant in grants:
            if grant['id'] not in existing_ids:
                sheet.append_row([
                    grant['id'],
                    grant['title'],
                    grant['organization'],
                    grant['deadline'],
                    grant['url'],
                    grant['keywords'],
                    grant['description']
                ])
                new_count += 1
        
        print(f"신규 공고 {new_count}건 저장")
        return True
    
    except Exception as e:
        print(f"저장 실패: {e}")
        return False

def main():
    """크롤러 실행"""
    print("=" * 50)
    print("창업지원금 크롤러")
    print("=" * 50)
    
    # 크롤링
    grants = crawl_k_startup()
    
    # 저장
    if grants:
        save_grants(grants)
    else:
        print("수집된 공고 없음")
    
    print("=" * 50)
    print("완료")
    print("=" * 50)

if __name__ == "__main__":
    main()
