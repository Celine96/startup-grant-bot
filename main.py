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
from matcher import match_grant, pre_filter, extract_amount, extract_documents, format_amount
from config import (
    MAX_MATCH_RESULTS, REGION_OPTIONS,
    SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_SIGNING_SECRET, SLACK_SCOPES,
)
from oauth_store import GoogleSheetsInstallationStore, InMemoryOAuthStateStore

# ============================================
# 설정
# ============================================

_missing = [v for v in ("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_SIGNING_SECRET")
            if not globals().get(v)]
if _missing:
    print(f"ERROR: 필수 환경변수가 설정되지 않았습니다: {", ".join(_missing)}")
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
# 슬랙 봇
# ============================================

@slack_app.command("/register")
def register(ack, command, client, body):
    """프로필 등록"""
    ack()

    team_id = command["team_id"]

    region_options = [
        {"text": {"type": "plain_text", "text": r}, "value": r}
        for r in REGION_OPTIONS
    ]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "profile_modal",
            "private_metadata": json.dumps({"team_id": team_id}),
            "title": {"type": "plain_text", "text": "프로필 등록"},
            "submit": {"type": "plain_text", "text": "등록"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "keywords",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "input",
                        "placeholder": {"type": "plain_text", "text": "예: AI, SaaS, 헬스케어"}
                    },
                    "label": {"type": "plain_text", "text": "핵심 키워드 (쉼표 구분)"}
                },
                {
                    "type": "input",
                    "block_id": "description",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "사업 설명 2-3문장"}
                    },
                    "label": {"type": "plain_text", "text": "사업 설명"}
                },
                {
                    "type": "input",
                    "block_id": "stage",
                    "element": {
                        "type": "static_select",
                        "action_id": "input",
                        "options": [
                            {"text": {"type": "plain_text", "text": "예비"}, "value": "예비"},
                            {"text": {"type": "plain_text", "text": "초기"}, "value": "초기"},
                            {"text": {"type": "plain_text", "text": "시드"}, "value": "시드"},
                            {"text": {"type": "plain_text", "text": "시리즈A"}, "value": "시리즈A"}
                        ]
                    },
                    "label": {"type": "plain_text", "text": "창업 단계"}
                },
                {
                    "type": "input",
                    "block_id": "region",
                    "element": {
                        "type": "static_select",
                        "action_id": "input",
                        "initial_option": {"text": {"type": "plain_text", "text": "전국(무관)"}, "value": "전국(무관)"},
                        "options": region_options,
                    },
                    "label": {"type": "plain_text", "text": "사업자 소재지 (시/도)"},
                    "hint": {"type": "plain_text", "text": "사업자등록증 주소지 기준. 지역 제한 공고 필터링에 사용됩니다."}
                },
                {
                    "type": "input",
                    "block_id": "min_amount",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "input",
                        "placeholder": {"type": "plain_text", "text": "예: 5000 (만원 단위, 미입력시 필터 없음)"}
                    },
                    "label": {"type": "plain_text", "text": "최소 희망 지원금액 (만원)"},
                    "hint": {"type": "plain_text", "text": "이 금액 미만의 지원사업은 결과에서 제외됩니다."}
                },
            ]
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

    data = {
        "keywords": values["keywords"]["input"]["value"].split(","),
        "description": values["description"]["input"]["value"],
        "stage": values["stage"]["input"]["selected_option"]["value"],
        "region": values["region"]["input"]["selected_option"]["value"],
        "min_amount": min_amount,
    }

    data["keywords"] = [k.strip() for k in data["keywords"] if k.strip()]

    if save_profile(user_id, team_id, data):
        ack()

        amount_text = f"{min_amount:,}만원 이상" if min_amount else "필터 없음"
        client.chat_postMessage(
            channel=user_id,
            text=(
                f"프로필 등록 완료! 매주 월요일 맞춤 공고를 받아보세요.\n\n"
                f"키워드: {", ".join(data["keywords"])}\n"
                f"단계: {data["stage"]}\n"
                f"소재지: {data["region"]}\n"
                f"최소 금액: {amount_text}"
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
        say(
            f"현재 프로필\n\n"
            f"키워드: {", ".join(profile["keywords"])}\n"
            f"사업: {profile["description"]}\n"
            f"단계: {profile["stage"]}\n"
            f"소재지: {profile.get("region", "") or "미설정"}\n"
            f"최소 금액: {amount_text}"
        )
    else:
        say("프로필이 없습니다. `/register` 명령어로 등록하세요.")

@slack_app.command("/test")
def test_matching(ack, command, say):
    """매칭 테스트"""
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
        if score > 0:
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
    message = "매칭 결과\n\n"

    for result in results[:MAX_MATCH_RESULTS]:
        grant = result["grant"]
        score = int(result["score"] * 100)
        desc = grant.get("description", "")

        # 마감일 D-day
        deadline_str = str(grant.get("deadline", "")).strip()
        if deadline_str and len(deadline_str) == 10:
            try:
                deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                d_day = (deadline_date - today).days
                deadline_display = f"{deadline_str} (D-{d_day})"
            except ValueError:
                deadline_display = deadline_str or "미정"
        else:
            deadline_display = deadline_str or "미정"

        # 금액
        amount = extract_amount(desc)
        amount_display = format_amount(amount)

        # 제출 서류
        docs = extract_documents(desc)
        docs_display = ", ".join(docs) if docs else "공고 확인 필요"

        message += f"매칭도 {score}% - {grant["title"]}\n"
        message += f"  기관: {grant["organization"]}\n"
        message += f"  마감: {deadline_display}\n"
        message += f"  금액: {amount_display}\n"
        message += f"  서류: {docs_display}\n"
        message += f"  사유: {result["reason"]}\n"
        message += f"  링크: {grant["url"]}\n\n"

    say(message)

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
