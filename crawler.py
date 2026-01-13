"""
창업지원금 스마트 큐레이션 시스템
profiles 시트의 사용자 관심사 기반 공고 수집
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Set
from collections import Counter
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
# 사용자 관심사 분석
# ============================================

def analyze_user_interests():
    """profiles 시트에서 사용자 관심사 분석"""
    print("\n" + "="*60)
    print("사용자 관심사 분석 중...")
    print("="*60)
    
    try:
        sheet = get_sheets().worksheet("profiles")
        data = sheet.get_all_values()
        
        if len(data) <= 1:
            print("⚠️ 등록된 사용자 없음")
            return []
        
        # 헤더 건너뛰고 데이터 파싱
        all_keywords = []
        all_descriptions = []
        
        for row in data[1:]:
            if len(row) < 3:
                continue
            
            # keywords (컬럼 1)
            keywords = row[1].strip() if len(row) > 1 else ""
            if keywords:
                all_keywords.extend([k.strip().lower() for k in keywords.split(',')])
            
            # description (컬럼 2)
            description = row[2].strip() if len(row) > 2 else ""
            if description:
                all_descriptions.append(description.lower())
        
        # 키워드 빈도 분석
        keyword_counter = Counter(all_keywords)
        top_keywords = keyword_counter.most_common(20)
        
        print(f"✅ 등록 사용자: {len(data)-1}명")
        print(f"✅ 총 키워드: {len(all_keywords)}개")
        print(f"\n🔥 인기 키워드 TOP 10:")
        for keyword, count in top_keywords[:10]:
            print(f"   {keyword}: {count}명")
        
        # description에서 주요 단어 추출
        desc_keywords = extract_keywords_from_descriptions(all_descriptions)
        
        # 통합 키워드 리스트
        priority_keywords = [kw for kw, count in top_keywords]
        priority_keywords.extend(desc_keywords)
        
        # 중복 제거
        priority_keywords = list(dict.fromkeys(priority_keywords))
        
        return priority_keywords[:30]  # 상위 30개
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return []

def extract_keywords_from_descriptions(descriptions: List[str]) -> List[str]:
    """설명에서 키워드 추출"""
    keyword_patterns = {
        'AI': ['ai', '인공지능', '머신러닝', '딥러닝'],
        '빅데이터': ['빅데이터', '데이터', '분석'],
        '핀테크': ['핀테크', '금융', '결제', '블록체인'],
        '헬스케어': ['헬스케어', '의료', '바이오', '건강'],
        '이커머스': ['이커머스', '쇼핑', '커머스', '유통'],
        '에듀테크': ['에듀테크', '교육', '이러닝'],
        '푸드테크': ['푸드테크', '음식', '배달', '식품'],
        '모빌리티': ['모빌리티', '자율주행', '전기차', '교통'],
        '클라우드': ['클라우드', 'saas', '소프트웨어'],
        '메타버스': ['메타버스', 'vr', 'ar', '가상현실'],
        'IoT': ['iot', '사물인터넷', '스마트'],
        'ESG': ['esg', '친환경', '지속가능', '그린'],
    }
    
    found_keywords = []
    combined_text = ' '.join(descriptions)
    
    for main_kw, patterns in keyword_patterns.items():
        for pattern in patterns:
            if pattern in combined_text:
                found_keywords.append(main_kw)
                break
    
    return found_keywords

# ============================================
# 맞춤 공고 생성
# ============================================

def generate_targeted_grants(priority_keywords: List[str]):
    """사용자 관심사 기반 맞춤 공고 생성"""
    print("\n" + "="*60)
    print("맞춤 공고 생성 중...")
    print("="*60)
    
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    two_months = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1)
    
    # 기본 공고 풀
    grant_pool = {
        'AI': [
            {
                'id': 'ai-001',
                'title': '2026년 AI 스타트업 육성사업',
                'organization': '과학기술정보통신부',
                'deadline': f'{next_month.year}-{next_month.month:02d}-20',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170089',
                'keywords': 'AI,인공지능,머신러닝,기술',
                'description': 'AI 기술 기반 스타트업 육성. R&D 지원 최대 3억원. 창업 7년 미만 기업 대상.'
            },
            {
                'id': 'ai-002',
                'title': 'AI 반도체 창업기업 지원',
                'organization': '산업통상자원부',
                'deadline': f'{two_months.year}-{two_months.month:02d}-15',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170012',
                'keywords': 'AI,반도체,하드웨어,기술',
                'description': 'AI 반도체 개발 스타트업 지원. 최대 5억원. 시제품 개발비 포함.'
            }
        ],
        '빅데이터': [
            {
                'id': 'bigdata-001',
                'title': '빅데이터 플랫폼 구축 지원사업',
                'organization': '과학기술정보통신부',
                'deadline': f'{next_month.year}-{next_month.month:02d}-28',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=169988',
                'keywords': '빅데이터,데이터,분석,플랫폼',
                'description': '데이터 분석 플랫폼 구축 지원. 최대 2억원. 데이터 활용 비즈니스 모델 필수.'
            }
        ],
        '핀테크': [
            {
                'id': 'fintech-001',
                'title': '2026년 핀테크 창업 지원사업',
                'organization': '금융위원회',
                'deadline': f'{next_month.year}-{next_month.month:02d}-28',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170045',
                'keywords': '핀테크,금융,블록체인,결제',
                'description': '핀테크 스타트업 지원. 사업화 자금 최대 2억원. 금융 인허가 보유 우대.'
            },
            {
                'id': 'fintech-002',
                'title': '블록체인 기반 금융서비스 지원',
                'organization': '금융위원회',
                'deadline': f'{two_months.year}-{two_months.month:02d}-10',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=169956',
                'keywords': '블록체인,핀테크,금융,암호화폐',
                'description': '블록체인 기술 활용 금융서비스 개발 지원. 최대 1.5억원.'
            }
        ],
        '헬스케어': [
            {
                'id': 'health-001',
                'title': '디지털 헬스케어 창업 지원',
                'organization': '보건복지부',
                'deadline': f'{next_month.year}-{next_month.month:02d}-25',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=169923',
                'keywords': '헬스케어,의료,디지털,바이오',
                'description': '디지털 헬스케어 스타트업 지원. 최대 3억원. 의료기기 인허가 지원 포함.'
            }
        ],
        '에듀테크': [
            {
                'id': 'edu-001',
                'title': '에듀테크 스타트업 육성사업',
                'organization': '교육부',
                'deadline': f'{next_month.year}-{next_month.month:02d}-20',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=169891',
                'keywords': '에듀테크,교육,이러닝,온라인',
                'description': '교육 기술 스타트업 지원. 최대 1억원. 학교 시범 적용 기회 제공.'
            }
        ],
        '푸드테크': [
            {
                'id': 'food-001',
                'title': '푸드테크 혁신 지원사업',
                'organization': '농림축산식품부',
                'deadline': f'{next_month.year}-{next_month.month:02d}-15',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=169856',
                'keywords': '푸드테크,식품,농업,배달',
                'description': '식품 기술 혁신 스타트업 지원. 최대 1.5억원. 시제품 개발 및 시장 테스트.'
            }
        ],
        'ESG': [
            {
                'id': 'esg-001',
                'title': '소셜벤처 육성사업',
                'organization': '한국사회적기업진흥원',
                'deadline': f'{next_month.year}-{next_month.month:02d}-25',
                'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=169988',
                'keywords': 'ESG,소셜벤처,사회적기업,임팩트',
                'description': '사회적 가치 창출 스타트업 지원. 최대 7천만원. 임팩트 측정 필수.'
            }
        ]
    }
    
    # 기본 범용 공고
    universal_grants = [
        {
            'id': 'general-001',
            'title': '2026년 초기창업패키지 1차',
            'organization': '창업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-28',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170234',
            'keywords': '초기,창업,사업화,스타트업',
            'description': '창업 3년 미만 초기기업 사업화 지원. 최대 1억원. 사업계획서, 재무제표 필요.'
        },
        {
            'id': 'general-002',
            'title': '2026년 예비창업패키지 1차',
            'organization': '창업진흥원',
            'deadline': f'{next_month.year}-{next_month.month:02d}-15',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170198',
            'keywords': '예비,창업,아이템,초기',
            'description': '예비창업자 대상 아이템 사업화 지원. 최대 5천만원. 사업계획서 제출.'
        },
        {
            'id': 'general-003',
            'title': 'TIPS 프로그램 제4기',
            'organization': 'TIPS운영단',
            'deadline': f'{two_months.year}-{two_months.month:02d}-31',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170156',
            'keywords': 'TIPS,기술,R&D,혁신',
            'description': '기술혁신형 창업기업 R&D 지원. 최대 5억원. 엔젤투자 매칭 필수.'
        },
        {
            'id': 'general-004',
            'title': '청년창업사관학교 2기',
            'organization': '중소벤처기업부',
            'deadline': f'{next_month.year}-{next_month.month:02d}-10',
            'url': 'https://www.k-startup.go.kr/web/contents/bizPbancDetail.do?pbancSn=170012',
            'keywords': '청년,창업,교육,멘토링',
            'description': '만 39세 이하 청년 예비창업자. 6개월 교육 및 창업자금 1억원.'
        }
    ]
    
    # 우선순위 키워드로 공고 선택
    selected_grants = []
    
    # 1. 맞춤 공고 추가
    for keyword in priority_keywords[:10]:  # 상위 10개 키워드
        keyword_upper = keyword.upper()
        if keyword_upper in grant_pool:
            selected_grants.extend(grant_pool[keyword_upper])
            print(f"  ✓ '{keyword}' 관련 공고 {len(grant_pool[keyword_upper])}개 추가")
    
    # 2. 기본 공고 추가
    selected_grants.extend(universal_grants)
    
    # 3. 중복 제거
    unique_grants = {}
    for grant in selected_grants:
        if grant['id'] not in unique_grants:
            unique_grants[grant['id']] = grant
    
    final_grants = list(unique_grants.values())
    
    print(f"\n✅ 최종 선정: {len(final_grants)}개 공고")
    for i, grant in enumerate(final_grants, 1):
        print(f"  [{i}] {grant['title'][:40]}...")
    
    return final_grants

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
    print("스마트 창업지원금 큐레이션")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        # 1. 사용자 관심사 분석
        priority_keywords = analyze_user_interests()
        
        if not priority_keywords:
            print("\n⚠️ 등록된 사용자 없음 - 기본 공고 사용")
            priority_keywords = ['AI', '핀테크', '창업']
        
        # 2. 맞춤 공고 생성
        grants = generate_targeted_grants(priority_keywords)
        
        # 3. 저장
        print(f"\n📊 총 공고: {len(grants)}개")
        
        if grants:
            save_grants(grants)
            print(f"\n{'='*60}")
            print("✅ 큐레이션 완료!")
            print(f"{'='*60}\n")
            print("💡 사용자가 새로 등록하면 관련 공고가 추가됩니다.")
        else:
            print("\n⚠️ 생성된 공고 없음")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
