"""
Slack DM 알림 모듈
"""

import os

from slack_bolt import App

from db import get_all_profiles
from matcher import match_grant
from config import MAX_MATCH_RESULTS


def create_slack_app() -> App:
    """알림 전용 Slack 앱 인스턴스"""
    token = os.getenv('SLACK_BOT_TOKEN')
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN 환경변수가 설정되지 않았습니다")
    return App(token=token)


def notify_users(new_grants: list[dict]):
    """모든 프로필을 순회하며 매칭 결과 DM 발송"""
    profiles = get_all_profiles()
    if not profiles:
        print("알림 대상 프로필 없음")
        return

    app = create_slack_app()
    sent_count = 0

    for profile in profiles:
        matches = match_grants_for_profile(profile, new_grants)
        if matches:
            try:
                send_dm(app, profile['user_id'], matches)
                sent_count += 1
            except Exception as e:
                print(f"DM 발송 실패 ({profile['user_id']}): {e}")

    print(f"알림 발송 완료: {sent_count}/{len(profiles)}명")


def match_grants_for_profile(profile: dict, grants: list[dict]) -> list[dict]:
    """프로필과 지원금 매칭"""
    results = []
    for grant in grants:
        score, reason = match_grant(grant, profile)
        if score > 0:
            results.append({
                'grant': grant,
                'score': score,
                'reason': reason,
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:MAX_MATCH_RESULTS]


def send_dm(app: App, user_id: str, matches: list[dict]):
    """Slack DM으로 매칭 결과 발송"""
    dm = app.client.conversations_open(users=user_id)
    channel = dm['channel']['id']

    lines = ["새로운 맞춤 지원사업이 있습니다!\n"]
    for result in matches:
        grant = result['grant']
        score = int(result['score'] * 100)
        lines.append(f"매칭도 {score}% - {grant['title']}")
        lines.append(f"  기관: {grant['organization']}")
        lines.append(f"  마감: {grant.get('deadline', '미정')}")
        lines.append(f"  사유: {result['reason']}")
        lines.append(f"  링크: {grant['url']}")
        lines.append("")

    app.client.chat_postMessage(
        channel=channel,
        text='\n'.join(lines),
    )
