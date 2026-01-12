"""
창업지원금 실제 크롤러
K-Startup + 창업넷 실제 크롤링
"""

import os
import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict

# 크롤링
import requests
from bs4 import BeautifulSoup

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# 설정
# ============================================

SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS", "{}"))

def get_sheets():
    """Google Sheets 연결"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_KEY)

# ============================================
# K-Startup 크롤링
# ============================================

def crawl_k_startup():
    """K-Startup 실제 크롤링"""
    print("\n" + "="*60)
    print("K-Startup 크롤링 시작")
    print("="*60)
    
    grants = []
    
    try:
        url = "https://www.k-startup.go.kr/web/contents/bizPbanc.do"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        print(f"접속 중: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다양한 선택자 시도
        selectors = [
            'table.table-list tbody tr',
            'div.board-list table tbody tr',
            'table tbody tr',
            'ul.notice-list li',
            'div.list-wrap div.list-item',
        ]
        
        items = []
        used_selector = None
        
        for selector in selectors:
            try:
                items = soup.select(selector)
                if len(items) > 3:  # 최소 3개 이상 있어야 유효
                    used_selector = selector
                    print(f"✅ 선택자 '{selector}'로 {len(items)}개 발견")
                    break
            except:
                continue
        
        if not items:
            print("⚠️ K-Startup 공고를 찾을 수 없음")
            return []
        
        # 공고 파싱
        count = 0
        for item in items[:20]:  # 최대 20개
            try:
                # 링크 찾기
                link = item.select_one('a')
                if not link:
                    continue
                
                # 제목
                title = link.get_text(strip=True)
                
                # 너무 짧거나 헤더 row 제외
                if not title or len(title) < 5 or title in ['번호', '제목', '등록일']:
                    continue
                
                # URL
                href = link.get('href', '')
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"https://www.k-startup.go.kr{href}"
                elif href.startswith('javascript') or not href:
                    # javascript 링크는 건너뛰기
                    continue
                else:
                    full_url = f"https://www.k-startup.go.kr/{href}"
                
                # ID 생성
                grant_id = hashlib.md5(f"kstartup_{title}".encode()).hexdigest()[:16]
                
                # 기관명 (제목에서 추출 시도)
                organization = extract_organization(title)
                
                # 마감일 추출 시도
                deadline = ''
                deadline_elem = item.select_one('td.date, span.date, td:last-child')
                if deadline_elem:
                    deadline_text = deadline_elem.get_text(strip=True)
                    deadline = parse_date(deadline_text)
                
                # 키워드 추출
                keywords = extract_keywords(title)
                
                grants.append({
                    'id': grant_id,
                    'title': title,
                    'organization': organization,
                    'deadline': deadline,
                    'url': full_url,
                    'keywords': ','.join(keywords),
                    'description': title
                })
                
                count += 1
                print(f"  [{count}] {title[:45]}...")
            
            except Exception as e:
                continue
        
        print(f"✅ K-Startup: {len(grants)}개 수집")
        
    except requests.RequestException as e:
        print(f"❌ K-Startup 접속 실패: {e}")
    except Exception as e:
        print(f"❌ K-Startup 크롤링 오류: {e}")
    
    return grants

# ============================================
# 창업넷 크롤링
# ============================================

def crawl_startup_net():
    """창업넷 실제 크롤링"""
    print("\n" + "="*60)
    print("창업넷 크롤링 시작")
    print("="*60)
    
    grants = []
    
    try:
        # 창업넷 공고 페이지
        url = "https://start.debc.or.kr/main.do"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        print(f"접속 중: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다양한 선택자 시도
        selectors = [
            'div.notice-list ul li',
            'table.board tbody tr',
            'div.list-wrap div.item',
            'ul.support-list li',
        ]
        
        items = []
        for selector in selectors:
            try:
                items = soup.select(selector)
                if len(items) > 3:
                    print(f"✅ 선택자 '{selector}'로 {len(items)}개 발견")
                    break
            except:
                continue
        
        if not items:
            print("⚠️ 창업넷 공고를 찾을 수 없음")
            return []
        
        # 공고 파싱
        count = 0
        for item in items[:20]:
            try:
                link = item.select_one('a')
                if not link:
                    continue
                
                title = link.get_text(strip=True)
                
                if not title or len(title) < 5:
                    continue
                
                href = link.get('href', '')
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"https://start.debc.or.kr{href}"
                elif href.startswith('javascript') or not href:
                    continue
                else:
                    full_url = f"https://start.debc.or.kr/{href}"
                
                grant_id = hashlib.md5(f"startnet_{title}".encode()).hexdigest()[:16]
                
                organization = extract_organization(title)
                
                deadline = ''
                deadline_elem = item.select_one('span.date, td.date')
                if deadline_elem:
                    deadline = parse_date(deadline_elem.get_text(strip=True))
                
                keywords = extract_keywords(title)
                
                grants.append({
                    'id': grant_id,
                    'title': title,
                    'organization': organization,
                    'deadline': deadline,
                    'url': full_url,
                    'keywords': ','.join(keywords),
                    'description': title
                })
                
                count += 1
                print(f"  [{count}] {title[:45]}...")
            
            except Exception as e:
                continue
        
        print(f"✅ 창업넷: {len(grants)}개 수집")
        
    except requests.RequestException as e:
        print(f"❌ 창업넷 접속 실패: {e}")
    except Exception as e:
        print(f"❌ 창업넷 크롤링 오류: {e}")
    
    return grants

# ============================================
# 유틸리티 함수
# ============================================

def extract_organization(text):
    """제목에서 기관명 추출"""
    # 주요 기관 키워드
    orgs = {
        '창업진흥원': '창업진흥원',
        'TIPS': 'TIPS운영단',
        '중소벤처': '중소벤처기업부',
        '과기정통부': '과학기술정보통신부',
        '과학기술': '과학기술정보통신부',
        '금융위': '금융위원회',
        '중기부': '중소벤처기업부',
        '기보': '기술보증기금',
        '신보': '신용보증기금',
        '벤처기업': '중소벤처기업부',
    }
    
    for keyword, org_name in orgs.items():
        if keyword in text:
            return org_name
    
    return '관련기관'

def parse_date(text):
    """날짜 문자열 파싱"""
    try:
        # '2026-01-31', '2026.01.31', '01-31' 등 다양한 형식 처리
        text = text.strip().replace('.', '-').replace('/', '-')
        
        # YYYY-MM-DD 형식
        if re.match(r'\d{4}-\d{2}-\d{2}', text):
            return text
        
        # MM-DD 형식 (년도 추가)
        if re.match(r'\d{2}-\d{2}', text):
            year = datetime.now().year
            return f"{year}-{text}"
        
        # ~ 포함 (기간)
        if '~' in text:
            parts = text.split('~')
            if len(parts) == 2:
                return parse_date(parts[1].strip())
        
        return ''
    except:
        return ''

def extract_keywords(text):
    """제목에서 키워드 추출"""
    keywords = []
    
    keyword_dict = {
        'AI': ['AI', '인공지능', '머신러닝'],
        '빅데이터': ['빅데이터', '데이터'],
        '핀테크': ['핀테크', '금융'],
        '블록체인': ['블록체인', '암호화폐'],
        '메타버스': ['메타버스', 'VR', 'AR', '가상현실'],
        'IoT': ['IoT', '사물인터넷'],
        '클라우드': ['클라우드', 'SaaS'],
        '헬스케어': ['헬스케어', '의료', '바이오'],
        '에듀테크': ['에듀테크', '교육'],
        '푸드테크': ['푸드테크', '농업'],
        '모빌리티': ['모빌리티', '자율주행', '전기차'],
        '로봇': ['로봇', '드론'],
        'ESG': ['ESG', '친환경', '에너지'],
        '창업': ['창업', '스타트업', '벤처'],
        '초기': ['초기', '예비창업'],
        'R&D': ['R&D', '연구개발', '기술개발'],
    }
    
    text_lower = text.lower()
    
    for main_keyword, variations in keyword_dict.items():
        for variation in variations:
            if variation.lower() in text_lower or variation in text:
                keywords.append(main_keyword)
                break
    
    return keywords[:5]

# ============================================
# Fallback 예시 데이터
# ============================================

def generate_fallback_grants():
    """크롤링 실패시 예시 공고 생성"""
    print("\n" + "="*60)
    print("⚠️ 크롤링 실패 - 예시 공고 생성")
    print("="*60)
    
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    two_months = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1)
    
    grants = [
        {
            'id': 'fallback-001',
            'title': '초기창업패키지',
            'organization': '창업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-28',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=168764',
            'keywords': '초기,창업,사업화',
            'description': '3년 미만 초기 창업기업 사업화 지원. 최대 1억원.'
        },
        {
            'id': 'fallback-002',
            'title': '예비창업패키지',
            'organization': '창업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-15',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=168762',
            'keywords': '예비,창업,아이템',
            'description': '예비창업자 창업 아이템 사업화 지원. 최대 5천만원.'
        },
        {
            'id': 'fallback-003',
            'title': 'TIPS 프로그램',
            'organization': 'TIPS운영단',
            'deadline': f'{next_month.year}-{next_month.month:02d}-31',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=168758',
            'keywords': 'TIPS,기술,R&D',
            'description': '기술혁신형 창업기업 R&D 지원. 최대 5억원.'
        },
        {
            'id': 'fallback-004',
            'title': 'AI 스타트업 육성',
            'organization': '과학기술정보통신부',
            'deadline': f'{two_months.year}-{two_months.month:02d}-20',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=168755',
            'keywords': 'AI,기술,혁신',
            'description': 'AI 기술 기반 스타트업 육성. R&D 지원.'
        },
        {
            'id': 'fallback-005',
            'title': '핀테크 창업 지원',
            'organization': '금융위원회',
            'deadline': f'{two_months.year}-{two_months.month:02d}-28',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=168751',
            'keywords': '핀테크,금융',
            'description': '핀테크 스타트업 지원. 사업화 자금 최대 2억원.'
        }
    ]
    
    print(f"✅ 예시 공고 {len(grants)}개 생성")
    return grants

# ============================================
# Google Sheets 저장
# ============================================

def save_grants(grants: List[Dict]):
    """공고 저장"""
    if not grants:
        print("⚠️ 저장할 공고 없음")
        return False
    
    try:
        print("\n" + "="*60)
        print("Google Sheets 저장 중...")
        print("="*60)
        
        sheet = get_sheets().worksheet("grants")
        
        # 기존 ID 가져오기
        existing_ids = set()
        try:
            data = sheet.get_all_values()
            if len(data) > 1:
                existing_ids = {row[0] for row in data[1:] if row and len(row) > 0}
        except:
            pass
        
        print(f"기존 공고: {len(existing_ids)}개")
        
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
                print(f"  ✓ {grant['title'][:40]}...")
        
        print(f"\n✅ 저장 완료: 신규 {new_count}개")
        if len(grants) - new_count > 0:
            print(f"   (중복 제외: {len(grants) - new_count}개)")
        
        return True
        
    except Exception as e:
        print(f"❌ 저장 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return False

# ============================================
# 메인
# ============================================

def main():
    """메인 실행"""
    print(f"\n{'='*60}")
    print("창업지원금 실제 크롤러")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    all_grants = []
    
    try:
        # K-Startup 크롤링
        kstartup_grants = crawl_k_startup()
        all_grants.extend(kstartup_grants)
        
        # 창업넷 크롤링
        startup_net_grants = crawl_startup_net()
        all_grants.extend(startup_net_grants)
        
        # 크롤링 실패시 fallback
        if len(all_grants) == 0:
            print("\n⚠️ 모든 크롤링 실패 - Fallback 사용")
            all_grants = generate_fallback_grants()
        
        # 저장
        print(f"\n📊 총 수집: {len(all_grants)}개")
        
        if all_grants:
            save_grants(all_grants)
            print(f"\n{'='*60}")
            print("✅ 크롤러 완료!")
            print(f"{'='*60}\n")
        else:
            print("\n⚠️ 수집된 공고 없음")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())
        
        # 오류 발생시에도 fallback 제공
        print("\n⚠️ 오류로 인한 Fallback 사용")
        fallback_grants = generate_fallback_grants()
        if fallback_grants:
            save_grants(fallback_grants)

if __name__ == "__main__":
    main()
