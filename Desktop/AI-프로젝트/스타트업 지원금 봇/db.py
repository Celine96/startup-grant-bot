"""
Google Sheets CRUD 모듈
"""

import os
import json
from typing import List

import gspread
from google.oauth2.service_account import Credentials

from config import SHEETS_SCOPES

SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS", "{}"))


def get_sheets() -> gspread.Spreadsheet:
    """Google Sheets 연결"""
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=SHEETS_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_KEY)


def save_profile(user_id: str, data: dict) -> bool:
    """프로필 저장 (존재하면 업데이트, 없으면 추가)"""
    try:
        sheet = get_sheets().worksheet("profiles")
        row_data = [
            user_id,
            ','.join(data['keywords']),
            data['description'],
            data['stage'],
            data.get('region', ''),
            ','.join(data.get('support_types', []))
        ]
        try:
            cell = sheet.find(user_id)
            sheet.update(f'A{cell.row}:F{cell.row}', [row_data])
        except gspread.exceptions.CellNotFound:
            sheet.append_row(row_data)
        return True
    except Exception as e:
        print(f"프로필 저장 실패: {e}")
        return False


def get_profile(user_id: str) -> dict | None:
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
    except Exception:
        return None


def get_all_profiles() -> list[dict]:
    """모든 프로필 조회 (알림 발송용)"""
    try:
        sheet = get_sheets().worksheet("profiles")
        data = sheet.get_all_values()
        if len(data) <= 1:
            return []

        profiles = []
        for row in data[1:]:
            if len(row) < 3:
                continue
            profiles.append({
                'user_id': row[0],
                'keywords': row[1].split(',') if row[1] else [],
                'description': row[2],
                'stage': row[3] if len(row) > 3 else '',
                'region': row[4] if len(row) > 4 else '',
                'support_types': row[5].split(',') if len(row) > 5 and row[5] else []
            })
        return profiles
    except Exception as e:
        print(f"프로필 목록 조회 실패: {e}")
        return []


def get_recent_grants(limit: int = 20) -> list[dict]:
    """최근 공고 조회"""
    try:
        sheet = get_sheets().worksheet("grants")
        records = sheet.get_all_records()
        return records[-limit:] if len(records) > limit else records
    except Exception:
        return []


def save_grants(grants: List[dict]) -> int:
    """공고 저장 (중복 체크 포함, 저장 건수 반환)"""
    if not grants:
        return 0

    try:
        sheet = get_sheets().worksheet("grants")

        # 기존 ID 가져오기
        existing_ids = set()
        try:
            data = sheet.get_all_values()
            if len(data) > 1:
                existing_ids = {row[0] for row in data[1:] if row}
        except Exception:
            pass

        new_count = 0
        for grant in grants:
            if grant['id'] not in existing_ids:
                sheet.append_row([
                    grant['id'],
                    grant['title'],
                    grant['organization'],
                    grant['deadline'],
                    grant['url'],
                    grant.get('keywords', ''),
                    grant.get('description', '')
                ])
                new_count += 1

        print(f"공고 저장 완료: 신규 {new_count}개 (기존 {len(existing_ids)}개, 중복 제외 {len(grants) - new_count}개)")
        return new_count
    except Exception as e:
        print(f"공고 저장 실패: {e}")
        return 0
