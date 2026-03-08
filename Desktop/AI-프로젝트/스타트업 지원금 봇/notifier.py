"""
Slack DM 알림 모듈 (멀티테넌트)
"""

from slack_sdk import WebClient

from db import get_all_profiles, get_all_installations
from matcher import match_grant
from config import MAX_MATCH_RESULTS


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
        token = inst['bot_token']
        team_id = inst['team_id']

        # 해당 워크스페이스의 프로필만 필터
        team_profiles = [p for p in profiles if p.get('team_id') == team_id]
        if not team_profiles:
            continue

        total_profiles += len(team_profiles)
        client = WebClient(token=token)

        for profile in team_profiles:
            matches = match_grants_for_profile(profile, new_grants)
            if matches:
                try:
                    send_dm(client, profile['user_id'], matches)
                    sent_count += 1
                except Exception as e:
                    print(f"DM 발송 실패 ({team_id}/{profile['user_id']}): {e}")

    print(f"알림 발송 완료: {sent_count}/{total_profiles}명 ({len(installations)}개 워크스페이스)")


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


def send_dm(client: WebClient, user_id: str, matches: list[dict]):
    """Slack DM으로 매칭 결과 발송"""
    dm = client.conversations_open(users=user_id)
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

    client.chat_postMessage(
        channel=channel,
        text='\n'.join(lines),
    )
