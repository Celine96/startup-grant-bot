"""
창업지원금 매칭 슬랙봇 - 초간단 버전
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from fastapi import FastAPI
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ============================================
# 설정
# ============================================

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS", "{}"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# ============================================
# Google Sheets DB
# ============================================

def get_sheets():
    """Google Sheets 연결"""
    creds = Credentials.from_service_account_info(
        GOOGLE_CREDS,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_KEY)

def save_profile(user_id: str, data: dict):
    """프로필 저장"""
    try:
        sheet = get_sheets().worksheet("profiles")
        # 기존 찾기
        try:
            cell = sheet.find(user_id)
            row = cell.row
            # 업데이트
            sheet.update(f'A{row}:F{row}', [[
                user_id,
                ','.join(data['keywords']),
                data['description'],
                data['stage'],
                data.get('region', ''),
                ','.join(data.get('support_types', []))
            ]])
        except:
            # 새로 추가
            sheet.append_row([
                user_id,
                ','.join(data['keywords']),
                data['description'],
                data['stage'],
                data.get('region', ''),
                ','.join(data.get('support_types', []))
            ])
        return True
    except Exception as e:
        print(f"프로필 저장 실패: {e}")
        return False

def get_profile(user_id: str):
    """프로필 조회"""
    try:
        sheet = get_sheets().worksheet("profiles")
        cell = sheet.find(user_id)
        row = sheet.row_values(cell.row)
        return {
            'user_id': row[0],
            'keywords': row[1].split(',') if row[1] else [],
            'description': row[2],
            'stage': row[3],
            'region': row[4] if len(row) > 4 else '',
            'support_types': row[5].split(',') if len(row) > 5 and row[5] else []
        }
    except:
        return None

def get_recent_grants(days=7):
    """최근 공고 조회"""
    try:
        sheet = get_sheets().worksheet("grants")
        records = sheet.get_all_records()
        # 최근 N일 필터링 (간단 버전: 그냥 최근 20개)
        return records[-20:] if len(records) > 20 else records
    except:
        return []

def save_grants(grants: List[dict]):
    """공고 저장"""
    try:
        sheet = get_sheets().worksheet("grants")
        for grant in grants:
            sheet.append_row([
                grant['id'],
                grant['title'],
                grant['organization'],
                grant['deadline'],
                grant['url'],
                grant.get('keywords', ''),
                grant.get('description', '')
            ])
        return True
    except Exception as e:
        print(f"공고 저장 실패: {e}")
        return False

# ============================================
# AI 매칭
# ============================================

def match_grant(grant: dict, profile: dict) -> tuple:
    """공고와 프로필 매칭 (점수, 이유)"""
    
    prompt = f"""
다음 창업 지원금 공고와 창업자 프로필의 매칭도를 분석해주세요.

**창업자 프로필:**
- 키워드: {', '.join(profile['keywords'])}
- 사업: {profile['description']}
- 단계: {profile['stage']}

**지원금 공고:**
- 제목: {grant['title']}
- 기관: {grant['organization']}
- 설명: {grant.get('description', grant['title'])}

다음 형식으로만 응답하세요:
점수: [0.0~1.0 숫자]
이유: [한 줄 설명]
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 파싱
        score = 0.0
        reason = "분석 실패"
        
        for line in text.split('\n'):
            if line.startswith('점수:'):
                score = float(line.replace('점수:', '').strip())
            elif line.startswith('이유:'):
                reason = line.replace('이유:', '').strip()
        
        return score, reason
    except:
        return 0.0, "매칭 분석 실패"

# ============================================
# 슬랙 봇
# ============================================

slack_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

@slack_app.command("/register")
def register(ack, command, client, body):
    """프로필 등록"""
    ack()
    
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "profile_modal",
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
    values = view["state"]["values"]
    
    data = {
        'keywords': values["keywords"]["input"]["value"].split(','),
        'description': values["description"]["input"]["value"],
        'stage': values["stage"]["input"]["selected_option"]["value"]
    }
    
    # 키워드 정리
    data['keywords'] = [k.strip() for k in data['keywords'] if k.strip()]
    
    if save_profile(user_id, data):
        ack()
        client.chat_postMessage(
            channel=user_id,
            text="✅ 프로필 등록 완료! 매주 월요일 맞춤 공고를 받아보세요."
        )
    else:
        ack()
        client.chat_postMessage(
            channel=user_id,
            text="❌ 저장 실패. 다시 시도해주세요."
        )

@slack_app.command("/status")
def status(ack, command, say):
    """프로필 확인"""
    ack()
    
    profile = get_profile(command['user_id'])
    
    if profile:
        say(f"""
📋 **현재 프로필**

🔑 키워드: {', '.join(profile['keywords'])}
📝 사업: {profile['description']}
🚀 단계: {profile['stage']}
        """)
    else:
        say("프로필이 없습니다. `/register` 명령어로 등록하세요.")

@slack_app.command("/test")
def test_matching(ack, command, say):
    """매칭 테스트"""
    ack()
    
    user_id = command['user_id']
    profile = get_profile(user_id)
    
    if not profile:
        say("프로필을 먼저 등록하세요: `/register`")
        return
    
    grants = get_recent_grants()
    
    if not grants:
        say("등록된 공고가 없습니다.")
        return
    
    # 첫 공고로 테스트
    grant = grants[0]
    score, reason = match_grant(grant, profile)
    
    say(f"""
🧪 **매칭 테스트**

공고: {grant['title']}
매칭도: {int(score*100)}%
이유: {reason}
    """)

# ============================================
# FastAPI
# ============================================

api = FastAPI()
handler = SlackRequestHandler(slack_app)

@api.get("/")
def root():
    return {"status": "ok"}

@api.post("/slack/events")
async def slack_events(req):
    return await handler.handle(req)

@api.post("/slack/commands")
async def slack_commands(req):
    return await handler.handle(req)

@api.post("/slack/actions")
async def slack_actions(req):
    return await handler.handle(req)

# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)
