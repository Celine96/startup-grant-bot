"""
창업지원금 매칭 슬랙봇
"""

import json
import sys
from datetime import datetime, timezone

from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.oauth.oauth_settings import OAuthSettings
from fastapi import FastAPI, Request

from db import save_profile, get_profile, get_active_grants
from matcher import match_grant, pre_filter, build_grant_card
from config import (
    MAX_MATCH_RESULTS, MIN_MATCH_SCORE, REGION_OPTIONS, FOUNDING_YEAR_OPTIONS, PREVIOUS_SUPPORT_OPTIONS,
    REVENUE_RANGE_OPTIONS, BUSINESS_TYPE_OPTIONS, CEO_AGE_RANGE_OPTIONS,
    SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_SIGNING_SECRET, SLACK_SCOPES,
)
from oauth_store import GoogleSheetsInstallationStore, InMemoryOAuthStateStore

# ============================================
# 설정
# ============================================

_missing = [v for v in ("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_SIGNING_SECRET")
            if not globals().get(v)]
if _missing:
    print(f"ERROR: 필수 환경변수가 설정되지 않았습니다: {', '.join(_missing)}")
    print("  Render Dashboard -> Environment -> 환경변수를 확인하세요.")
    sys.exit(1)

installation_store = GoogleSheetsInstallationStore()

slack_app = App(
    signing_secret=SLACK_SIGNING_SECRET,
    installation_store=installation_store,
    oauth_settings=OAuthSettings(
        client_id=SLACK_CLIENT_ID,
        client_secret=SLACK_CLIENT_SECRET,
        scopes=SLACK_SCOPES,
        state_store=InMemoryOAuthStateStore(),
        install_path="/slack/install",
        redirect_uri_path="/slack/oauth_redirect",
    ),
)


# ============================================
# 모달 빌더
# ============================================

def _build_register_blocks(region_options, existing=None):
    """프로필 등록 모달 블록 생성. existing이 있으면 pre-fill."""

    # 키워드
    kw_element = {
        "type": "plain_text_input",
        "action_id": "input",
        "placeholder": {"type": "plain_text", "text": "예: AI, SaaS, 헬스케어"},
    }
    if existing and existing.get("keywords"):
        kw_element["initial_value"] = ", ".join(existing["keywords"])

    # 연 매출 규모
    revenue_options = [
        {"text": {"type": "plain_text", "text": r}, "value": r}
        for r in REVENUE_RANGE_OPTIONS
    ]
    revenue_element = {
        "type": "static_select",
        "action_id": "input",
        "placeholder": {"type": "plain_text", "text": "매출 규모 선택"},
        "options": revenue_options,
    }
    if existing and existing.get("revenue_range"):
        for opt in revenue_options:
            if opt["value"] == existing["revenue_range"]:
                revenue_element["initial_option"] = opt
                break

    # 업종
    btype_options = [
        {"text": {"type": "plain_text", "text": b}, "value": b}
        for b in BUSINESS_TYPE_OPTIONS
    ]
    btype_element = {
        "type": "static_select",
        "action_id": "input",
        "placeholder": {"type": "plain_text", "text": "업종 선택"},
        "options": btype_options,
    }
    if existing and existing.get("business_type"):
        for opt in btype_options:
            if opt["value"] == existing["business_type"]:
                btype_element["initial_option"] = opt
                break

    # 대표자 연령대
    ceo_age_options = [
        {"text": {"type": "plain_text", "text": a}, "value": a}
        for a in CEO_AGE_RANGE_OPTIONS
    ]
    ceo_age_element = {
        "type": "static_select",
        "action_id": "input",
        "placeholder": {"type": "plain_text", "text": "연령대 선택"},
        "options": ceo_age_options,
    }
    if existing and existing.get("ceo_age_range"):
        for opt in ceo_age_options:
            if opt["value"] == existing["ceo_age_range"]:
                ceo_age_element["initial_option"] = opt
                break

    # 사업설명
    desc_element = {
        "type": "plain_text_input",
        "action_id": "input",
        "multiline": True,
        "placeholder": {"type": "plain_text", "text": "예: AI 기술 기반 결제 서비스. 주요 고객은 소상공인."},
    }
    if existing and existing.get("description"):
        desc_element["initial_value"] = existing["description"]

    # 창업 단계
    stage_options = [
        {"text": {"type": "plain_text", "text": s}, "value": s}
        for s in ["예비", "초기", "시드", "시리즈A"]
    ]
    stage_element = {
        "type": "static_select",
        "action_id": "input",
        "options": stage_options,
    }
    if existing and existing.get("stage"):
        for opt in stage_options:
            if opt["value"] == existing["stage"]:
                stage_element["initial_option"] = opt
                break

    # 소재지
    region_select_options = [
        {"text": {"type": "plain_text", "text": r}, "value": r}
        for r in REGION_OPTIONS
    ]
    region_element = {
        "type": "static_select",
        "action_id": "input",
        "options": region_select_options,
    }
    current_region = (existing or {}).get("region", "전국(무관)") or "전국(무관)"
    for opt in region_select_options:
        if opt["value"] == current_region:
            region_element["initial_option"] = opt
            break

    # 최소 금액
    amount_element = {
        "type": "plain_text_input",
        "action_id": "input",
        "placeholder": {"type": "plain_text", "text": "예: 5000 (만원 단위, 미입력시 필터 없음)"},
    }
    if existing and existing.get("min_amount"):
        amount_element["initial_value"] = str(existing["min_amount"])

    # 창업 연도
    year_options = [
        {"text": {"type": "plain_text", "text": str(y)}, "value": str(y)}
        for y in FOUNDING_YEAR_OPTIONS
    ]
    year_element = {
        "type": "static_select",
        "action_id": "input",
        "placeholder": {"type": "plain_text", "text": "창업 연도 선택"},
        "options": year_options,
    }
    if existing and existing.get("founding_year"):
        yr_str = str(existing["founding_year"])
        for opt in year_options:
            if opt["value"] == yr_str:
                year_element["initial_option"] = opt
                break

    # 기존 수혜 이력
    support_options = [
        {"text": {"type": "plain_text", "text": s}, "value": s}
        for s in PREVIOUS_SUPPORT_OPTIONS
    ]
    support_element = {
        "type": "checkboxes",
        "action_id": "input",
        "options": support_options,
    }
    if existing and existing.get("previous_support"):
        initial_opts = []
        for opt in support_options:
            if opt["value"] in existing["previous_support"]:
                initial_opts.append(opt)
        if initial_opts:
            support_element["initial_options"] = initial_opts

    blocks = [
        {
            "type": "input",
            "block_id": "keywords",
            "element": kw_element,
            "label": {"type": "plain_text", "text": "핵심 키워드 (쉼표 구분)"},
            "hint": {"type": "plain_text", "text": "매칭의 핵심입니다. 사업 분야 키워드를 2~5개 입력하세요."},
        },
        {
            "type": "input",
            "block_id": "description",
            "optional": True,
            "element": desc_element,
            "label": {"type": "plain_text", "text": "사업 설명 (선택)"},
            "hint": {"type": "plain_text", "text": "입력하면 매칭 정확도가 올라갑니다."},
        },
        {
            "type": "input",
            "block_id": "stage",
            "element": stage_element,
            "label": {"type": "plain_text", "text": "창업 단계"},
            "hint": {"type": "plain_text", "text": "공고별 지원 대상 단계(예비/초기 등)를 매칭합니다."},
        },
        {
            "type": "input",
            "block_id": "region",
            "element": region_element,
            "label": {"type": "plain_text", "text": "사업자 소재지 (시/도)"},
            "hint": {"type": "plain_text", "text": "사업자등록증 주소지 기준. 지역 제한 공고 필터링에 사용됩니다."},
        },
        {
            "type": "input",
            "block_id": "min_amount",
            "optional": True,
            "element": amount_element,
            "label": {"type": "plain_text", "text": "최소 희망 지원금액 (만원)"},
            "hint": {"type": "plain_text", "text": "이 금액 미만의 지원사업은 결과에서 제외됩니다."},
        },
        {
            "type": "input",
            "block_id": "founding_year",
            "optional": True,
            "element": year_element,
            "label": {"type": "plain_text", "text": "창업 연도"},
            "hint": {"type": "plain_text", "text": "업력 제한 공고 필터링에 사용됩니다. (예: 창업 3년 미만 조건)"},
        },
        {
            "type": "input",
            "block_id": "previous_support",
            "optional": True,
            "element": support_element,
            "label": {"type": "plain_text", "text": "기존 정부지원 수혜 이력"},
            "hint": {"type": "plain_text", "text": "중복 수혜 제한 공고 확인용."},
        },
        {
            "type": "input",
            "block_id": "revenue_range",
            "optional": True,
            "element": revenue_element,
            "label": {"type": "plain_text", "text": "연 매출 규모"},
            "hint": {"type": "plain_text", "text": "매출 규모 제한 공고 필터링에 사용됩니다."},
        },
        {
            "type": "input",
            "block_id": "business_type",
            "optional": True,
            "element": btype_element,
            "label": {"type": "plain_text", "text": "업종 (업태)"},
            "hint": {"type": "plain_text", "text": "업종 제한 또는 특화 공고 매칭에 사용됩니다."},
        },
        {
            "type": "input",
            "block_id": "ceo_age_range",
            "optional": True,
            "element": ceo_age_element,
            "label": {"type": "plain_text", "text": "대표자 연령대"},
            "hint": {"type": "plain_text", "text": "청년/시니어 대상 공고 필터링에 사용됩니다."},
        },
    ]
    return blocks


# ============================================
# 슬랙 봇
# ============================================

@slack_app.command("/register")
def register(ack, command, client, body):
    """프로필 등록 (기존 프로필 있으면 pre-fill)"""
    ack()

    team_id = command["team_id"]
    user_id = command["user_id"]

    # 기존 프로필 조회 (pre-fill용)
    existing = get_profile(user_id, team_id)

    region_options = [
        {"text": {"type": "plain_text", "text": r}, "value": r}
        for r in REGION_OPTIONS
    ]

    blocks = _build_register_blocks(region_options, existing)

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "profile_modal",
            "private_metadata": json.dumps({"team_id": team_id}),
            "title": {"type": "plain_text", "text": "프로필 등록"},
            "submit": {"type": "plain_text", "text": "등록"},
            "blocks": blocks,
        }
    )


@slack_app.view("profile_modal")
def handle_submission(ack, body, view, client):
    """프로필 저장"""
    user_id = body["user"]["id"]
    metadata = json.loads(view.get("private_metadata", "{}"))
    team_id = metadata.get("team_id", body.get("team", {}).get("id", ""))
    values = view["state"]["values"]

    # 최소 금액 파싱
    min_amount_raw = (values["min_amount"]["input"].get("value") or "").strip()
    min_amount = 0
    if min_amount_raw:
        try:
            min_amount = int(min_amount_raw.replace(",", ""))
        except ValueError:
            ack(response_action="errors", errors={"min_amount": "숫자만 입력해주세요 (예: 5000)"})
            return

    # 창업 연도
    founding_year = 0
    year_selection = values["founding_year"]["input"].get("selected_option")
    if year_selection:
        founding_year = int(year_selection["value"])

    # 기존 수혜 이력
    previous_support = []
    support_selection = values["previous_support"]["input"].get("selected_options", [])
    for opt in support_selection:
        previous_support.append(opt["value"])

    # 새 필드 파싱
    revenue_sel = values["revenue_range"]["input"].get("selected_option")
    revenue_range = revenue_sel["value"] if revenue_sel else ""
    btype_sel = values["business_type"]["input"].get("selected_option")
    business_type = btype_sel["value"] if btype_sel else ""
    ceo_age_sel = values["ceo_age_range"]["input"].get("selected_option")
    ceo_age_range = ceo_age_sel["value"] if ceo_age_sel else ""

    data = {
        "keywords": values["keywords"]["input"]["value"].split(","),
        "description": values["description"]["input"].get("value") or "",
        "stage": values["stage"]["input"]["selected_option"]["value"],
        "region": values["region"]["input"]["selected_option"]["value"],
        "min_amount": min_amount,
        "founding_year": founding_year,
        "previous_support": previous_support,
        "revenue_range": revenue_range,
        "business_type": business_type,
        "ceo_age_range": ceo_age_range,
    }

    data["keywords"] = [k.strip() for k in data["keywords"] if k.strip()]

    if save_profile(user_id, team_id, data):
        ack()

        amount_text = f"{min_amount:,}만원 이상" if min_amount else "필터 없음"
        year_text = f"{founding_year}년" if founding_year else "미설정"
        support_text = ", ".join(previous_support) if previous_support else "없음"
        revenue_text = revenue_range or "미설정"
        btype_text = business_type or "미설정"
        ceo_age_text = ceo_age_range or "미설정"

        client.chat_postMessage(
            channel=user_id,
            text=(
                f"프로필 등록 완료! 매주 화/금 맞춤 공고를 받아보세요.\n\n"
                f"키워드: {', '.join(data['keywords'])}\n"
                f"단계: {data['stage']}\n"
                f"소재지: {data['region']}\n"
                f"최소 금액: {amount_text}\n"
                f"창업 연도: {year_text}\n"
                f"수혜 이력: {support_text}\n"
                f"매출 규모: {revenue_text}\n"
                f"업종: {btype_text}\n"
                f"대표 연령대: {ceo_age_text}"
            )
        )
    else:
        ack()
        client.chat_postMessage(
            channel=user_id,
            text="저장 실패. 다시 시도해주세요."
        )


@slack_app.command("/profile")
def profile_command(ack, command, say):
    """프로필 확인"""
    ack()

    team_id = command["team_id"]
    profile = get_profile(command["user_id"], team_id)

    if profile:
        min_amt = profile.get("min_amount", 0)
        amount_text = f"{min_amt:,}만원 이상" if min_amt else "필터 없음"
        yr = profile.get("founding_year", 0)
        year_text = f"{yr}년" if yr else "미설정"
        prev = profile.get("previous_support", [])
        support_text = ", ".join(prev) if prev else "없음"
        revenue_text = profile.get("revenue_range") or "미설정"
        btype_text = profile.get("business_type") or "미설정"
        ceo_age_text = profile.get("ceo_age_range") or "미설정"

        say(
            f"현재 프로필\n\n"
            f"키워드: {', '.join(profile['keywords'])}\n"
            f"사업: {profile.get('description') or '미입력'}\n"
            f"단계: {profile['stage']}\n"
            f"소재지: {profile.get('region', '') or '미설정'}\n"
            f"최소 금액: {amount_text}\n"
            f"창업 연도: {year_text}\n"
            f"수혜 이력: {support_text}\n"
            f"매출 규모: {revenue_text}\n"
            f"업종: {btype_text}\n"
            f"대표 연령대: {ceo_age_text}"
        )
    else:
        say("프로필이 없습니다. `/register` 명령어로 등록하세요.")


@slack_app.command("/matching")
def test_matching(ack, command, say, client):
    """매칭 테스트 (Block Kit 카드형 결과)"""
    ack()

    user_id = command["user_id"]
    team_id = command["team_id"]
    profile = get_profile(user_id, team_id)

    if not profile:
        say("프로필을 먼저 등록하세요: `/register`")
        return

    grants = get_active_grants()

    if not grants:
        say("등록된 공고가 없습니다.")
        return

    # 사전 필터 적용
    filtered = pre_filter(grants, profile)

    if not filtered:
        say("조건에 맞는 공고가 없습니다. (지역/마감일/금액 필터 확인)")
        return

    results = []
    for grant in filtered:
        score, reason = match_grant(grant, profile)
        if score >= MIN_MATCH_SCORE:
            results.append({
                "grant": grant,
                "score": score,
                "reason": reason
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    if not results:
        say("매칭되는 공고가 없습니다.")
        return

    today = datetime.now(timezone.utc).date()
    top_results = results[:MAX_MATCH_RESULTS]

    # Block Kit 카드 생성
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "매칭 결과"}
        }
    ]

    for result in top_results:
        blocks.extend(build_grant_card(result, today))

    # fallback text
    fallback_lines = []
    for r in top_results:
        s = int(r["score"] * 100)
        fallback_lines.append(f"{s}% - {r['grant']['title']}")
    fallback = "매칭 결과: " + ", ".join(fallback_lines)

    say(text=fallback, blocks=blocks)


# ============================================
# FastAPI
# ============================================

api = FastAPI()
handler = SlackRequestHandler(slack_app)

@api.get("/")
def root():
    return {"status": "ok"}

@api.post("/slack/events")
async def slack_events(req: Request):
    return await handler.handle(req)

@api.post("/slack/commands")
async def slack_commands(req: Request):
    return await handler.handle(req)

@api.post("/slack/actions")
async def slack_actions(req: Request):
    return await handler.handle(req)

# OAuth 라우트 (slack_bolt 자동 처리)
@api.get("/slack/install")
async def slack_install(req: Request):
    return await handler.handle(req)

@api.get("/slack/oauth_redirect")
async def slack_oauth_redirect(req: Request):
    return await handler.handle(req)

# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)
