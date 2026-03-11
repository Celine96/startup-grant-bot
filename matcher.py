"""
매칭 알고리즘 모듈
"""

import re
from datetime import datetime, timedelta, timezone

from config import MIN_DEADLINE_DAYS


# ============================================
# description 파싱 유틸
# ============================================

def extract_amount(text: str) -> int | None:
    """description에서 최대 지원금액을 만원 단위로 추출. 없으면 None."""
    if not text:
        return None

    patterns = [
        (r'최대\s*(\d+(?:,\d+)*)\s*억\s*원', lambda m: int(m.group(1).replace(',', '')) * 10000),
        (r'최대\s*(\d+(?:,\d+)*)\s*천만\s*원', lambda m: int(m.group(1).replace(',', '')) * 1000),
        (r'최대\s*(\d+(?:,\d+)*)\s*만\s*원', lambda m: int(m.group(1).replace(',', ''))),
        (r'(\d+(?:,\d+)*)\s*억\s*원', lambda m: int(m.group(1).replace(',', '')) * 10000),
        (r'(\d+(?:,\d+)*)\s*천만\s*원', lambda m: int(m.group(1).replace(',', '')) * 1000),
        (r'(\d+(?:,\d+)*)\s*백만\s*원', lambda m: int(m.group(1).replace(',', '')) * 100),
    ]

    amounts = []
    for pattern, converter in patterns:
        for match in re.finditer(pattern, text):
            amounts.append(converter(match))

    return max(amounts) if amounts else None


def extract_region(title: str, keywords: str = '') -> str | None:
    """title의 [지역] 접두어 또는 keywords에서 지역명 추출. 없으면 None(전국 공고)."""
    bracket_match = re.match(r'\[([가-힣]+)\]', title)
    if bracket_match:
        return bracket_match.group(1)

    regions = [
        '서울', '경기', '인천', '부산', '대구', '광주', '대전',
        '울산', '세종', '강원', '충북', '충남', '전북', '전남',
        '경북', '경남', '제주',
    ]
    combined = f"{title} {keywords}"
    for region in regions:
        if region in combined:
            return region

    return None


def extract_documents(text: str) -> list[str]:
    """description에서 제출 서류 항목 추출."""
    if not text:
        return []

    doc_keywords = [
        '사업계획서', '재무제표', '법인등기부등본', '사업자등록증',
        '주주명부', '기술설명서', '특허증', '인허가증',
        '투자확인서', '재직증명서', '졸업증명서',
    ]

    return [doc for doc in doc_keywords if doc in text]


def format_amount(amount_manwon: int | None) -> str:
    """만원 단위 금액을 읽기 쉬운 문자열로 변환."""
    if amount_manwon is None:
        return '금액 미정'
    if amount_manwon >= 10000:
        eok = amount_manwon // 10000
        remainder = amount_manwon % 10000
        if remainder:
            return f'{eok}억 {remainder:,}만원'
        return f'{eok}억원'
    return f'{amount_manwon:,}만원'


# ============================================
# 사전 필터 (hard filter)
# ============================================

def pre_filter(grants: list[dict], profile: dict) -> list[dict]:
    """매칭 점수 산출 전 지역/마감일/금액으로 공고 필터링."""
    filtered = []
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=MIN_DEADLINE_DAYS)

    user_region = profile.get('region', '').strip()
    min_amount = profile.get('min_amount', 0) or 0

    for grant in grants:
        # 1. 마감일 필터: 최소 14일 여유
        deadline_str = str(grant.get('deadline', '')).strip()
        if deadline_str and len(deadline_str) == 10:
            try:
                deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                if deadline_date < cutoff:
                    continue
            except ValueError:
                pass

        # 2. 지역 필터: 사용자 지역과 공고 지역 매칭
        if user_region and user_region != '전국(무관)':
            grant_region = extract_region(
                grant.get('title', ''),
                grant.get('keywords', ''),
            )
            # 공고에 지역 표시가 있고 사용자 지역과 다르면 제외
            if grant_region and user_region not in grant_region and grant_region not in user_region:
                continue

        # 3. 금액 필터: 최소 희망 금액 이상
        if min_amount > 0:
            grant_amount = extract_amount(grant.get('description', ''))
            if grant_amount is not None and grant_amount < min_amount:
                continue

        filtered.append(grant)

    return filtered


# ============================================
# 매칭 점수 산출
# ============================================

def match_grant(grant: dict, profile: dict) -> tuple[float, str]:
    """공고와 프로필 매칭 (점수, 이유)"""
    try:
        profile_keywords = [k.lower().strip() for k in profile['keywords'] if k.strip()]

        grant_text = ' '.join([
            grant.get('title', ''),
            grant.get('description', ''),
            grant.get('keywords', ''),
        ]).lower()

        grant_title = grant.get('title', '').lower()

        # 1. 키워드 매칭 (가중치 60%)
        keyword_score, matched = _keyword_match(profile_keywords, grant_text, grant_title)

        # 2. 창업 단계 매칭 (가중치 20%)
        stage_score, stage_reason = _stage_match(grant, profile)

        # 3. 설명 유사도 (가중치 20%)
        desc_score = _description_match(grant, profile)

        total = keyword_score * 0.6 + stage_score * 0.2 + desc_score * 0.2

        # 사유 생성
        reasons = []
        if matched:
            reasons.append(f"키워드: {', '.join(matched)}")
        if stage_reason:
            reasons.append(stage_reason)
        if not reasons:
            reasons.append("일치하는 항목 없음")

        return total, ', '.join(reasons)

    except Exception as e:
        return 0.0, f"매칭 실패: {e}"


def _keyword_match(profile_keywords: list[str], grant_text: str, grant_title: str) -> tuple[float, list[str]]:
    """키워드 매칭 점수 (title 매칭 시 가산점)"""
    if not profile_keywords:
        return 0.0, []

    matched = [kw for kw in profile_keywords if kw in grant_text]
    if not matched:
        return 0.0, []

    # title에 매칭된 키워드는 가산점
    title_matched = [kw for kw in matched if kw in grant_title]
    score = len(matched) / len(profile_keywords)
    if title_matched:
        score = min(1.0, score * 1.3)
    return score, matched


def _stage_match(grant: dict, profile: dict) -> tuple[float, str]:
    """창업 단계 매칭 점수"""
    stage = profile.get('stage', '').lower()
    if not stage:
        return 0.0, ''

    grant_text = ' '.join([
        grant.get('title', ''),
        grant.get('description', ''),
        grant.get('keywords', ''),
    ]).lower()

    stage_keywords = {
        '예비': ['예비창업', '예비', '아이템'],
        '초기': ['초기창업', '초기', '사업화', '창업패키지'],
        '시드': ['시드', 'tips', '기술창업', 'r&d'],
        '시리즈a': ['시리즈', 'tips', '스케일업', '성장'],
    }

    keywords = stage_keywords.get(stage, [])
    matched = [kw for kw in keywords if kw in grant_text]

    if matched:
        return 1.0, f"단계 적합({stage})"
    return 0.0, ''


def _description_match(grant: dict, profile: dict) -> float:
    """설명 유사도 (substring 기반, 한국어 대응)"""
    profile_desc = profile.get('description', '')
    grant_text = ' '.join([
        grant.get('title', ''),
        grant.get('description', ''),
    ]).lower()

    if not profile_desc or not grant_text:
        return 0.0

    # 2자 이상 단어를 substring으로 검색
    words = [w for w in profile_desc.lower().split() if len(w) >= 2]
    if not words:
        return 0.0

    matched = sum(1 for w in words if w in grant_text)
    return matched / len(words)
