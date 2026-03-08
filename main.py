"""
창업지원금 매칭 슬랙봇
"""

import json
import sys

from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.oauth.oauth_settings import OAuthSettings
from fastapi import FastAPI, Request

from db import save_profile, get_profile, get_active_grants
from matcher import match_grant
from config import (
    MAX_MATCH_RESULTS,
    SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_SIGNING_SECRET, SLACK_SCOPES,
)
from oauth_store import GoogleSheetsInstallationStore, InMemoryOAuthStateStore

# ============================================
# 설정
# ============================================

_missing = [v for v in ('SLACK_CLIENT_ID', 'SLACK_CLIENT_SECRET', 'SLACK_SIGNING_SECRET')
            if not globals().get(v)]
if _missing:
    print(f"ERROR: 필수 환경변수가 설정되지 않았습니다: {', '.join(_missing)}")
    print("  Render Dashboard → Environment → 환경변수를 확인하세요.")
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

    team_id = command['team_id']

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
                }
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

    data = {
        'keywords': values["keywords"]["input"]["value"].split(','),
        'description': values["description"]["input"]["value"],
        'stage': values["stage"]["input"]["selected_option"]["value"]
    }

    data['keywords'] = [k.strip() for k in data['keywords'] if k.strip()]

    if save_profile(user_id, team_id, data):
        ack()
        client.chat_postMessage(
            channel=user_id,
            text="프로필 등록 완료! 매주 월요일 맞춤 공고를 받아보세요."
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

    team_id = command['team_id']
    profile = get_profile(command['user_id'], team_id)

    if profile:
        say(
            f"현재 프로필\n\n"
            f"키워드: {', '.join(profile['keywords'])}\n"
            f"사업: {profile['description']}\n"
            f"단계: {profile['stage']}"
        )
    else:
        say("프로필이 없습니다. `/register` 명령어로 등록하세요.")

@slack_app.command("/test")
def test_matching(ack, command, say):
    """매칭 테스트"""
    ack()

    user_id = command['user_id']
    team_id = command['team_id']
    profile = get_profile(user_id, team_id)

    if not profile:
        say("프로필을 먼저 등록하세요: `/register`")
        return

    grants = get_active_grants()

    if not grants:
        say("등록된 공고가 없습니다.")
        return

    results = []
    for grant in grants:
        score, reason = match_grant(grant, profile)
        if score > 0:
            results.append({
                'grant': grant,
                'score': score,
                'reason': reason
            })

    results.sort(key=lambda x: x['score'], reverse=True)

    if not results:
        say("매칭되는 공고가 없습니다.")
        return

    message = "매칭 결과\n\n"

    for result in results[:MAX_MATCH_RESULTS]:
        grant = result['grant']
        score = int(result['score'] * 100)

        message += f"매칭도 {score}% - {grant['title']}\n"
        message += f"  기관: {grant['organization']}\n"
        message += f"  사유: {result['reason']}\n"
        message += f"  링크: {grant['url']}\n\n"

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
