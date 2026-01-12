"""
K-Startup 크롤러 - 간단 버전
예시 공고 자동 생성 (Playwright 없이)
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict

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
# 예시 공고 생성
# ============================================

def generate_sample_grants():
    """예시 공고 생성"""
    print("=" * 60)
    print("예시 공고 생성 중...")
    print("=" * 60)
    
    today = datetime.now()
    
    # 다음 달
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    
    # 2달 후
    two_months = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1)
    
    grants = [
        {
            'id': 'kstartup-001',
            'title': '초기창업패키지',
            'organization': '창업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-28',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': '초기,창업,사업화,스타트업',
            'description': '3년 미만 초기 창업기업 사업화 지원. 최대 1억원. 사업계획서, 재무제표 제출 필요.'
        },
        {
            'id': 'kstartup-002',
            'title': '예비창업패키지',
            'organization': '창업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-15',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': '예비,창업,아이템,초기',
            'description': '예비창업자 창업 아이템 사업화 지원. 최대 5천만원. 사업계획서 제출.'
        },
        {
            'id': 'kstartup-003',
            'title': 'TIPS 프로그램',
            'organization': 'TIPS운영단',
            'deadline': f'{next_month.year}-{next_month.month:02d}-31',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': 'TIPS,기술,R&D,혁신',
            'description': '기술혁신형 창업기업 R&D 지원. 최대 5억원. 엔젤투자 매칭 필수.'
        },
        {
            'id': 'kstartup-004',
            'title': 'AI·빅데이터 기반 창업기업 육성',
            'organization': '과학기술정보통신부',
            'deadline': f'{two_months.year}-{two_months.month:02d}-20',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': 'AI,빅데이터,인공지능,데이터,기술',
            'description': 'AI·빅데이터 기술 기반 스타트업 육성. R&D 지원 최대 3억원. 7년 미만 기업.'
        },
        {
            'id': 'kstartup-005',
            'title': '핀테크 창업 지원사업',
            'organization': '금융위원회',
            'deadline': f'{two_months.year}-{two_months.month:02d}-28',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': '핀테크,금융,블록체인,결제',
            'description': '핀테크 스타트업 지원. 사업화 자금 최대 2억원. 금융 관련 인허가 보유 우대.'
        },
        {
            'id': 'kstartup-006',
            'title': '청년창업사관학교',
            'organization': '중소벤처기업부',
            'deadline': f'{next_month.year}-{next_month.month:02d}-10',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': '청년,창업,교육,멘토링',
            'description': '만 39세 이하 청년 예비창업자 대상. 6개월 교육 및 창업자금 1억원 지원.'
        },
        {
            'id': 'kstartup-007',
            'title': '소셜벤처 육성사업',
            'organization': '한국사회적기업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-25',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbanc.do',
            'keywords': '소셜벤처,사회적기업,ESG,임팩트',
            'description': '사회적 가치 창출 스타트업 지원. 최대 7천만원. 사회적 임팩트 측정 필수.'
        }
    ]
    
    print(f"✅ 예시 공고 {len(grants)}개 생성")
    for grant in grants:
        print(f"  ✓ {grant['title']}")
    
    return grants

def save_grants(grants: List[Dict]):
    """Google Sheets 저장"""
    if not grants:
        print("⚠️ 저장할 공고 없음")
        return False
    
    try:
        print("\n" + "=" * 60)
        print("Google Sheets 저장 중...")
        print("=" * 60)
        
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
    print("창업지원금 크롤러 - 간단 버전")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # 예시 공고 생성
        grants = generate_sample_grants()
        
        # 저장
        if grants:
            save_grants(grants)
            print(f"\n{'='*60}")
            print("✅ 크롤러 완료!")
            print(f"{'='*60}\n")
        else:
            print("\n⚠️ 생성된 공고 없음")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
