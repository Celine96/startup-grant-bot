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

        # 1. 키워드 매칭 (가중치 60%)
        keyword_score, matched = _keyword_match(profile_keywords, grant_text)

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


def _keyword_match(profile_keywords: list[str], grant_text: str) -> tuple[float, list[str]]:
    """키워드 매칭 점수"""
    if not profile_keywords:
        return 0.0, []

    matched = [kw for kw in profile_keywords if kw in grant_text]
    score = len(matched) / len(profile_keywords)
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
    """설명 유사도 (단어 겹침 기반)"""
    profile_desc = profile.get('description', '').lower()
    grant_desc = ' '.join([
        grant.get('title', ''),
        grant.get('description', ''),
    ]).lower()

    if not profile_desc or not grant_desc:
        return 0.0

    profile_words = set(profile_desc.split())
    grant_words = set(grant_desc.split())

    # 1~2글자 불용어 제거
    profile_words = {w for w in profile_words if len(w) > 2}
    grant_words = {w for w in grant_words if len(w) > 2}

    if not profile_words:
        return 0.0

    overlap = profile_words & grant_words
    return len(overlap) / len(profile_words) if profile_words else 0.0
