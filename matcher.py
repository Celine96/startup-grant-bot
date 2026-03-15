"""
매칭 알고리즘 모듈
"""

import re
from datetime import datetime, timedelta, timezone

from config import MIN_DEADLINE_DAYS, MIN_MATCH_SCORE


# ============================================
# description 파싱 유틸
# ============================================

def extract_amount(text: str) -> int | None:
    """description에서 최대 지원금액을 만원 단위로 추출. 없으면 None."""
    if not text:
        return None

    patterns = [
        (r"최대\s*(\d+(?:,\d+)*)\s*억\s*원", lambda m: int(m.group(1).replace(",", "")) * 10000),
        (r"최대\s*(\d+(?:,\d+)*)\s*천만\s*원", lambda m: int(m.group(1).replace(",", "")) * 1000),
        (r"최대\s*(\d+(?:,\d+)*)\s*만\s*원", lambda m: int(m.group(1).replace(",", ""))),
        (r"(\d+(?:,\d+)*)\s*억\s*원", lambda m: int(m.group(1).replace(",", "")) * 10000),
        (r"(\d+(?:,\d+)*)\s*천만\s*원", lambda m: int(m.group(1).replace(",", "")) * 1000),
        (r"(\d+(?:,\d+)*)\s*백만\s*원", lambda m: int(m.group(1).replace(",", "")) * 100),
    ]

    amounts = []
    for pattern, converter in patterns:
        for match in re.finditer(pattern, text):
            amounts.append(converter(match))

    return max(amounts) if amounts else None


def extract_region(title: str, keywords: str = "", grant_region: str = "") -> str | None:
    """공고의 지역 정보 추출. grant_region(구조화 필드) 우선, 없으면 title/keywords에서 파싱."""
    if grant_region:
        return grant_region

    bracket_match = re.match(r"\[([가-힣]+)\]", title)
    if bracket_match:
        return bracket_match.group(1)

    regions = [
        "서울", "경기", "인천", "부산", "대구", "광주", "대전",
        "울산", "세종", "강원", "충북", "충남", "전북", "전남",
        "경북", "경남", "제주",
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
        "사업계획서", "재무제표", "법인등기부등본", "사업자등록증",
        "주주명부", "기술설명서", "특허증", "인허가증",
        "투자확인서", "재직증명서", "졸업증명서",
        "정관", "4대보험 가입자명부", "원천징수이행상황신고서",
        "부가가치세 신고서", "IR자료", "벤처확인서", "이력서", "통장사본",
    ]

    return [doc for doc in doc_keywords if doc in text]


def extract_business_age_limit(text: str) -> int | None:
    """description에서 '창업 N년 미만' 같은 업력 제한을 추출. 없으면 None."""
    if not text:
        return None

    patterns = [
        r"창업\s*(\d+)\s*년\s*미만",
        r"(\d+)\s*년\s*미만\s*(?:창업|기업)",
        r"창업\s*(\d+)\s*년\s*이내",
        r"(\d+)\s*년\s*이내\s*(?:창업|기업)",
    ]

    limits = []
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            limits.append(int(match.group(1)))

    return min(limits) if limits else None


def format_amount(amount_manwon: int | None) -> str:
    """만원 단위 금액을 읽기 쉬운 문자열로 변환."""
    if amount_manwon is None:
        return "금액 미정"
    if amount_manwon >= 10000:
        eok = amount_manwon // 10000
        remainder = amount_manwon % 10000
        if remainder:
            return f"{eok}억 {remainder:,}만원"
        return f"{eok}억원"
    return f"{amount_manwon:,}만원"


def get_grant_amount(grant: dict) -> int | None:
    """공고의 지원금액 조회. 구조화 필드 우선, 없으면 description 파싱."""
    structured = grant.get("max_amount")
    if structured:
        try:
            return int(structured)
        except (ValueError, TypeError):
            pass
    return extract_amount(grant.get("description", ""))


# ============================================
# 사전 필터 (hard filter)
# ============================================

# 중복수혜 필터용 키워드 매핑
DUPLICATE_KEYWORDS = {
    "창업패키지(예비/초기)": ["창업패키지", "예비창업패키지", "초기창업패키지"],
    "TIPS": ["tips", "팁스"],
    "청년창업사관학교": ["사관학교"],
}


def pre_filter(grants: list[dict], profile: dict) -> list[dict]:
    """매칭 점수 산출 전 지역/마감일/금액/업력/중복수혜/연령대/업종으로 공고 필터링."""
    filtered = []
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=MIN_DEADLINE_DAYS)

    user_region = profile.get("region", "").strip()
    min_amount = profile.get("min_amount", 0) or 0
    founding_year = profile.get("founding_year", 0) or 0
    previous_support = profile.get("previous_support", [])
    ceo_age_range = profile.get("ceo_age_range", "").strip()
    business_type = profile.get("business_type", "").strip()

    for grant in grants:
        # 1. 마감일 필터: 최소 14일 여유
        deadline_str = str(grant.get("deadline", "")).strip()
        if deadline_str and len(deadline_str) == 10:
            try:
                deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                if deadline_date < cutoff:
                    continue
            except ValueError:
                pass

        # 2. 지역 필터
        if user_region and user_region != "전국(무관)":
            grant_region = extract_region(
                grant.get("title", ""),
                grant.get("keywords", ""),
                grant.get("region", ""),
            )
            if grant_region and user_region not in grant_region and grant_region not in user_region:
                continue

        # 3. 금액 필터
        if min_amount > 0:
            grant_amount = get_grant_amount(grant)
            if grant_amount is not None and grant_amount < min_amount:
                continue

        # 4. 업력(창업연도) 필터
        if founding_year > 0:
            desc = grant.get("description", "")
            age_limit = extract_business_age_limit(desc)
            if age_limit is not None:
                business_age = today.year - founding_year
                if business_age >= age_limit:
                    continue

        # 5. 중복수혜 필터
        if previous_support:
            grant_text_lower = " ".join([
                grant.get("title", ""), grant.get("description", ""),
            ]).lower()
            duplicate_markers = ["중복 수혜 불가", "재선정 불가", "수혜기업 제외", "중복수혜 불가", "중복지원 불가"]
            has_duplicate_restriction = any(m in grant_text_lower for m in duplicate_markers)
            if has_duplicate_restriction:
                excluded = False
                for support in previous_support:
                    keywords = DUPLICATE_KEYWORDS.get(support, [])
                    if any(kw.lower() in grant_text_lower for kw in keywords):
                        excluded = True
                        break
                if excluded:
                    continue

        # 6. 대표자 연령대 필터 (제목 기준만)
        if ceo_age_range:
            grant_title = grant.get("title", "")
            if ceo_age_range == "만 39세 이하 (청년)":
                if "시니어" in grant_title or "노인" in grant_title or "장년" in grant_title:
                    continue
            elif ceo_age_range == "만 40~64세":
                if "청년" in grant_title:
                    continue
                if "시니어" in grant_title or "노인" in grant_title:
                    continue
            elif ceo_age_range == "만 65세 이상 (시니어)":
                if "청년" in grant_title:
                    continue

        # 7. 업종 제한 필터 (명시적 제외만)
        if business_type:
            grant_text_lower = " ".join([
                grant.get("title", ""), grant.get("description", ""),
            ]).lower()
            if business_type == "제조업" and "비제조" in grant_text_lower:
                continue
            if business_type != "제조업" and "제조업만" in grant_text_lower:
                continue
            # "XX업 제외" 패턴
            if f"{business_type} 제외" in grant_text_lower:
                continue

        filtered.append(grant)

    return filtered


# ============================================
# 키워드 토크나이저
# ============================================

def _tokenize_keyword(kw: str) -> list[str]:
    """복합 키워드를 서브토큰으로 분해.
    'AI 제조자동화' -> ['ai', '제조자동화']
    '주문제작(PoD)' -> ['주문제작', 'pod']
    'K-컬처 굿즈' -> ['컬처', '굿즈']
    """
    # 괄호 내용을 별도 토큰으로 분리
    parts = re.split(r'[()\[\]\s/,·]+', kw)
    # 하이픈 분리 (단, 영문 약어 보존)
    expanded = []
    for p in parts:
        if '-' in p and not p.replace('-', '').isascii():
            expanded.extend(p.split('-'))
        else:
            expanded.append(p)
    # 1자 이하 제거, lowercase
    return [t.lower().strip() for t in expanded if len(t.strip()) >= 2]


# ============================================
# 매칭 점수 산출
# ============================================

def _amount_bonus(grant: dict, profile: dict) -> float:
    """금액 보너스 (최대 0.07) — 지원금 규모에 따른 가산."""
    amount = get_grant_amount(grant)
    if amount is None:
        return 0.0
    min_amt = profile.get("min_amount", 0) or 0
    if min_amt <= 0:
        if amount >= 10000:
            return 0.07
        if amount >= 5000:
            return 0.04
        if amount >= 1000:
            return 0.02
        return 0.01
    ratio = amount / min_amt
    if ratio >= 3.0:
        return 0.07
    if ratio >= 2.0:
        return 0.04
    if ratio >= 1.5:
        return 0.02
    return 0.01


def _deadline_bonus(grant: dict) -> float:
    """마감 여유 보너스 (최대 0.03) — 준비 시간이 충분할수록 높은 점수."""
    deadline_str = str(grant.get("deadline", "")).strip()
    if not deadline_str or len(deadline_str) != 10:
        return 0.0
    try:
        days_left = (datetime.strptime(deadline_str, "%Y-%m-%d").date() - datetime.now(timezone.utc).date()).days
        if days_left >= 45:
            return 0.03
        if days_left >= 30:
            return 0.02
        return 0.01
    except ValueError:
        return 0.0


def match_grant(grant: dict, profile: dict) -> tuple[float, str]:
    """공고와 프로필 매칭 (점수, 이유)"""
    try:
        profile_keywords = [k.strip() for k in profile["keywords"] if k.strip()]

        grant_text = " ".join([
            grant.get("title", ""),
            grant.get("description", ""),
            grant.get("keywords", ""),
        ]).lower()

        grant_title = grant.get("title", "").lower()
        grant_keywords_field = grant.get("keywords", "").lower()

        # 1. 키워드 매칭 (가중치 50%)
        keyword_score, matched = _keyword_match(
            profile_keywords, grant_text, grant_title, grant_keywords_field,
        )

        # 2. 창업 단계 매칭 (가중치 15%)
        stage_score, stage_reason = _stage_match(grant, profile)

        # 3. 설명 유사도 (가중치 15%)
        desc_score = _description_match(grant, profile)

        relevance = keyword_score * 0.50 + stage_score * 0.15 + desc_score * 0.15

        # 업종 보너스 (최대 0.10)
        business_type = profile.get("business_type", "")
        btype_matched = _business_type_match(grant, business_type) if business_type else False
        btype_bonus = 0.10 if btype_matched else 0.0

        # 금액 보너스 (최대 0.07)
        amt_bonus = _amount_bonus(grant, profile)

        # 마감 여유 보너스 (최대 0.03)
        dl_bonus = _deadline_bonus(grant)

        total = min(1.0, relevance + btype_bonus + amt_bonus + dl_bonus)

        # 사유 생성
        reasons = []
        if matched:
            reasons.append(f"키워드: {', '.join(matched)}")
        if stage_reason:
            reasons.append(stage_reason)
        if btype_matched:
            reasons.append(f"업종 적합({business_type})")
        if not reasons:
            reasons.append("일치하는 항목 없음")

        return total, ", ".join(reasons)

    except Exception as e:
        return 0.0, f"매칭 실패: {e}"


def _keyword_match(
    profile_keywords: list[str],
    grant_text: str,
    grant_title: str,
    grant_keywords_field: str,
) -> tuple[float, list[str]]:
    """키워드 매칭 점수 - 매칭 위치(title/keywords/desc)별 차등 점수."""
    if not profile_keywords:
        return 0.0, []

    scores = []
    matched_keywords = []
    for kw in profile_keywords:
        tokens = _tokenize_keyword(kw)
        if not tokens:
            scores.append(0.0)
            continue
        if any(t in grant_title for t in tokens):
            scores.append(1.0)
            matched_keywords.append(kw)
        elif any(t in grant_keywords_field for t in tokens):
            scores.append(0.7)
            matched_keywords.append(kw)
        elif any(t in grant_text for t in tokens):
            scores.append(0.4)
            matched_keywords.append(kw)
        else:
            scores.append(0.0)

    return (sum(scores) / len(scores)), matched_keywords


def _stage_match(grant: dict, profile: dict) -> tuple[float, str]:
    """창업 단계 매칭 점수 - exact/strong/weak 3단계 그라데이션."""
    stage = profile.get("stage", "").lower()
    if not stage:
        return 0.0, ""

    grant_text = " ".join([
        grant.get("title", ""),
        grant.get("description", ""),
        grant.get("keywords", ""),
    ]).lower()

    stage_keywords = {
        "예비": {"exact": ["예비창업"], "strong": ["아이템"], "weak": ["예비"]},
        "초기": {"exact": ["초기창업"], "strong": ["사업화", "창업패키지"], "weak": ["초기"]},
        "시드": {"exact": ["기술창업"], "strong": ["tips", "r&d"], "weak": ["시드"]},
        "시리즈a": {"exact": ["스케일업"], "strong": ["tips", "시리즈"], "weak": ["성장"]},
    }

    tiers = stage_keywords.get(stage, {})
    if any(kw in grant_text for kw in tiers.get("exact", [])):
        return 1.0, f"단계 적합({stage})"
    if any(kw in grant_text for kw in tiers.get("strong", [])):
        return 0.7, f"단계 적합({stage})"
    if any(kw in grant_text for kw in tiers.get("weak", [])):
        return 0.3, f"단계 관련({stage})"
    return 0.0, ""


def _word_weight(word: str) -> float:
    """단어 길이 기반 가중치 — 구체적 단어일수록 높은 비중."""
    if len(word) >= 4:
        return 1.5
    if len(word) >= 3:
        return 1.0
    return 0.5


def _description_match(grant: dict, profile: dict) -> float:
    """설명 유사도 (substring 기반, 단어 길이 가중치 적용)"""
    profile_desc = profile.get("description", "")
    grant_text = " ".join([
        grant.get("title", ""),
        grant.get("description", ""),
    ]).lower()

    if not profile_desc or not grant_text:
        return 0.0

    words = [w for w in profile_desc.lower().split() if len(w) >= 2]
    if not words:
        return 0.0

    weighted_total = sum(_word_weight(w) for w in words)
    weighted_matched = sum(_word_weight(w) for w in words if w in grant_text)
    return weighted_matched / weighted_total


# ============================================
# 업종 매칭
# ============================================

_BUSINESS_TYPE_KEYWORDS = {
    "제조업": ["제조", "생산", "공장"],
    "정보통신업(SW/IT)": ["it", "sw", "소프트웨어", "정보통신", "ict", "디지털"],
    "도소매업": ["도소매", "유통", "판매", "커머스"],
    "음식/숙박업": ["음식", "외식", "숙박", "요식"],
    "교육서비스업": ["교육", "에듀", "edtech"],
    "전문/과학기술업": ["연구", "기술", "과학", "r&d"],
    "보건/사회복지": ["의료", "헬스", "바이오", "복지", "보건"],
    "문화/예술/여가": ["문화", "콘텐츠", "예술", "관광", "여가"],
    "건설업": ["건설", "건축", "시공"],
    "농림어업": ["농업", "농촌", "어업", "임업", "스마트팜"],
}


def _business_type_match(grant: dict, business_type: str) -> bool:
    """공고 텍스트에 사용자의 업종 관련 키워드가 있으면 True."""
    if not business_type:
        return False

    keywords = _BUSINESS_TYPE_KEYWORDS.get(business_type, [])
    if not keywords:
        return False

    grant_text = " ".join([
        grant.get("title", ""),
        grant.get("description", ""),
        grant.get("keywords", ""),
    ]).lower()

    return any(kw in grant_text for kw in keywords)


# ============================================
# 카드 빌더 (main.py, notifier.py 공용)
# ============================================

def build_grant_card(result: dict, today) -> list[dict]:
    """매칭 결과 1건을 Slack Block Kit 블록 리스트로 변환.

    정보 위계: 지원 가능 → 마감일 → 금액 → 제목 → 매칭 사유/서류
    """
    grant = result["grant"]
    score = int(result["score"] * 100)
    desc = grant.get("description", "")

    # 마감일 D-day
    deadline_str = str(grant.get("deadline", "")).strip()
    d_day_text = ""
    deadline_short = ""
    if deadline_str and len(deadline_str) == 10:
        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            d_day = (deadline_date - today).days
            d_day_text = f"D-{d_day}"
            deadline_short = f"{deadline_date.month}/{deadline_date.day}"
        except ValueError:
            pass

    # 금액
    amount = get_grant_amount(grant)
    amount_display = format_amount(amount)

    # 제출 서류
    docs = extract_documents(desc)
    docs_display = ", ".join(docs) if docs else "공고 확인 필요"

    # 1행: 지원 가능 + D-day
    line1 = ":white_check_mark: 지원 가능"
    if d_day_text:
        line1 += f"  {d_day_text}"
        if deadline_short:
            line1 += f" (마감 {deadline_short})"

    # 2행: 제목
    line2 = f"*{grant['title']}*"

    # 3행: 금액 볼드 + 기관명
    if amount_display != "금액 미정":
        line3 = f":moneybag: *{amount_display}* · {grant['organization']}"
    else:
        line3 = f"{grant['organization']}"

    # 4행: 매칭 사유
    line4 = f"매칭 {score}%: {result['reason']}"

    section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{line1}\n{line2}\n{line3}",
        },
    }

    url = grant.get("url", "")
    if url:
        section["accessory"] = {
            "type": "button",
            "text": {"type": "plain_text", "text": "공고 보기"},
            "url": url,
        }

    blocks = [section]

    # context: 매칭 사유 + 서류
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": line4},
            {"type": "mrkdwn", "text": f"서류: {docs_display}"},
        ]
    })
    blocks.append({"type": "divider"})

    return blocks
