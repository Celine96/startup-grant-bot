"""
멀티테넌트 마이그레이션 스크립트 (1회성)

기존 단일 워크스페이스 데이터를 멀티테넌트 구조로 변환:
1. profiles 시트에 team_id 컬럼 추가 (A열 삽입)
2. 기존 행들에 현재 워크스페이스 team_id 채우기
3. installations 시트에 현재 SLACK_BOT_TOKEN 등록

사용법:
  TEAM_ID=T1234567 SLACK_BOT_TOKEN=xoxb-... python migrate.py
"""

import os
import sys
from datetime import datetime

import gspread

from db import get_sheets, save_installation


def migrate():
    team_id = os.getenv('TEAM_ID')
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    team_name = os.getenv('TEAM_NAME', '')

    if not team_id:
        print("ERROR: TEAM_ID 환경변수를 설정하세요.")
        print("  Slack 앱 → About → Team ID에서 확인")
        sys.exit(1)
    if not bot_token:
        print("ERROR: SLACK_BOT_TOKEN 환경변수를 설정하세요.")
        sys.exit(1)

    spreadsheet = get_sheets()

    # ----------------------------------------
    # 1. profiles 시트에 team_id 컬럼 추가
    # ----------------------------------------
    print("1. profiles 시트 마이그레이션...")
    try:
        sheet = spreadsheet.worksheet("profiles")
        data = sheet.get_all_values()

        if not data:
            print("   profiles 시트가 비어있음 - 헤더만 생성")
            sheet.update('A1:G1', [['team_id', 'user_id', 'keywords', 'description', 'stage', 'region', 'support_types']])
        else:
            header = data[0]
            if header[0] == 'team_id':
                print("   이미 team_id 컬럼이 존재함 - 스킵")
            else:
                # A열에 team_id 삽입
                new_data = [['team_id'] + header]
                for row in data[1:]:
                    new_data.append([team_id] + row)

                # 기존 범위를 새 데이터로 덮어쓰기
                end_col = chr(ord('A') + len(new_data[0]) - 1)
                sheet.update(f'A1:{end_col}{len(new_data)}', new_data)
                print(f"   {len(data) - 1}개 프로필에 team_id={team_id} 추가 완료")
    except gspread.exceptions.WorksheetNotFound:
        print("   profiles 시트 없음 - 새로 생성")
        sheet = spreadsheet.add_worksheet(title="profiles", rows=100, cols=7)
        sheet.update('A1:G1', [['team_id', 'user_id', 'keywords', 'description', 'stage', 'region', 'support_types']])

    # ----------------------------------------
    # 2. installations 시트 생성 + 현재 토큰 등록
    # ----------------------------------------
    print("2. installations 시트 설정...")
    try:
        spreadsheet.worksheet("installations")
        print("   installations 시트가 이미 존재함")
    except Exception:
        print("   installations 시트 새로 생성")
        inst_sheet = spreadsheet.add_worksheet(title="installations", rows=100, cols=5)
        inst_sheet.update('A1:E1', [['team_id', 'team_name', 'bot_token', 'bot_user_id', 'installed_at']])

    # 현재 토큰 등록
    save_installation(team_id, {
        'team_name': team_name,
        'bot_token': bot_token,
        'bot_user_id': '',
        'installed_at': datetime.utcnow().isoformat(),
    })
    print(f"   team_id={team_id} 설치 정보 저장 완료")

    # ----------------------------------------
    # 완료
    # ----------------------------------------
    print("\n마이그레이션 완료!")
    print("이제 SLACK_BOT_TOKEN 환경변수 대신 SLACK_CLIENT_ID, SLACK_CLIENT_SECRET을 사용합니다.")


if __name__ == "__main__":
    migrate()
