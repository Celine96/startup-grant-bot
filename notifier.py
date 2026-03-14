"""
Slack DM 알림 모듈 (멀티테넌트)
"""

from datetime import datetime, timezone

from slack_sdk import WebClient

from db import get_all_profiles, get_all_installations
from matcher import match_grant, pre_filter, build_grant_card
from config import MAX_MATCH_RESULTS, MIN_MATCH_SCORE


def notify_users(new_grants: list[dict]):
    """모든 설치된 워크스페이스의 프로필을 순회하며 매칭 결과 DM 발송"""
    installations = get_all_installations()
    if not installations:
        print("설치된 워크스페이스 없음")
        return

    profiles = get_all_profiles()
    if not profiles:
        print("알림 대상 프로필 없음")
        return

    sent_count = 0
    total_profiles = 0

    for inst in installations:
        token = inst["bot_token"]
        team_id = inst["team_id"]

        team_profiles = [p for p in profiles if p.get("team_id") == team_id]
        if not team_profiles:
            continue

        total_profiles += len(team_profiles)
        client = WebClient(token=token)

        for profile in team_profiles:
            matches = match_grants_for_profile(profile, new_grants)
            if matches:
                try:
                    send_dm(client, profile["user_id"], matches)
                    sent_count += 1
                except Exception as e:
                    print(f"DM 발송 실패 ({team_id}/{profile['user_id']}): {e}")

    print(f"알림 발송 완료: {sent_count}/{total_profiles}명 ({len(installations)}개 워크스페이스)")


def match_grants_for_profile(profile: dict, grants: list[dict]) -> list[dict]:
    """프로필과 지원금 매칭 (사전 필터 적용)"""
    filtered = pre_filter(grants, profile)

    results = []
    for grant in filtered:
        score, reason = match_grant(grant, profile)
        if score >= MIN_MATCH_SCORE:
            results.append({
                "grant": grant,
                "score": score,
                "reason": reason,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:MAX_MATCH_RESULTS]


def _build_result_blocks(matches: list[dict]) -> list[dict]:
    """매칭 결과를 Slack Block Kit 블록으로 변환"""
    today = datetime.now(timezone.utc).date()

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "새로운 맞춤 지원사업이 있습니다!"}
        }
    ]

    for result in matches:
        blocks.extend(build_grant_card(result, today))

    return blocks


def send_dm(client: WebClient, user_id: str, matches: list[dict]):
    """Slack DM으로 매칭 결과 발송 (Block Kit)"""
    dm = client.conversations_open(users=user_id)
    channel = dm["channel"]["id"]

    blocks = _build_result_blocks(matches)

    # fallback text (Block Kit 미지원 환경용)
    fallback_lines = []
    for result in matches:
        grant = result["grant"]
        score = int(result["score"] * 100)
        fallback_lines.append(f"{score}% - {grant['title']}")
    fallback = "새로운 맞춤 지원사업: " + ", ".join(fallback_lines)

    client.chat_postMessage(
        channel=channel,
        text=fallback,
        blocks=blocks,
    )
