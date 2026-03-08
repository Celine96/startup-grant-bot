"""
매칭 알고리즘 모듈
"""


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
