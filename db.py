"""
Google Sheets CRUD 모듈
"""

import os
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import List

import gspread
from google.oauth2.service_account import Credentials

from config import SHEETS_SCOPES

logger = logging.getLogger(__name__)

SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS", "{}"))

# Google Sheets 연결 캐시 (TTL 5분)
_cached_sheets = None
_cached_at = 0
_CACHE_TTL = 300


def get_sheets() -> gspread.Spreadsheet:
    """Google Sheets 연결 (5분 캐싱)"""
    global _cached_sheets, _cached_at
    now = time.time()
    if _cached_sheets and (now - _cached_at) < _CACHE_TTL:
        return _cached_sheets
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=SHEETS_SCOPES)
    client = gspread.authorize(creds)
    _cached_sheets = client.open_by_key(SPREADSHEET_KEY)
    _cached_at = now
    return _cached_sheets


# ============================================
# Installations CRUD
# ============================================

def _row_to_installation(row: list) -> dict:
    """시트 행 -> installation dict 변환"""
    return {
        "team_id": row[0],
        "team_name": row[1] if len(row) > 1 else "",
        "bot_token": row[2] if len(row) > 2 else "",
        "bot_user_id": row[3] if len(row) > 3 else "",
        "installed_at": row[4] if len(row) > 4 else "",
    }


def save_installation(team_id: str, data: dict) -> bool:
    """설치 정보 저장 (존재하면 업데이트, 없으면 추가)"""
    try:
        sheet = get_sheets().worksheet("installations")
        row_data = [
            team_id,
            data.get("team_name", ""),
            data["bot_token"],
            data.get("bot_user_id", ""),
            data.get("installed_at", datetime.now(timezone.utc).isoformat()),
        ]
        cell = sheet.find(team_id)
        if cell:
            sheet.update([row_data], f"A{cell.row}:E{cell.row}")
        else:
            sheet.append_row(row_data)
        return True
    except Exception as e:
        logger.error("설치 정보 저장 실패: %s", e)
        return False


def get_installation(team_id: str) -> dict | None:
    """설치 정보 조회"""
    try:
        sheet = get_sheets().worksheet("installations")
        cell = sheet.find(team_id)
        if not cell:
            return None
        row = sheet.row_values(cell.row)
        return _row_to_installation(row)
    except Exception as e:
        logger.error("설치 정보 조회 실패: %s", e)
        return None


def get_all_installations() -> list[dict]:
    """모든 설치 정보 조회"""
    try:
        sheet = get_sheets().worksheet("installations")
        data = sheet.get_all_values()
        if len(data) <= 1:
            return []

        installations = []
        for row in data[1:]:
            if len(row) < 3 or not row[0]:
                continue
            installations.append(_row_to_installation(row))
        return installations
    except Exception as e:
        logger.error("설치 목록 조회 실패: %s", e)
        return []


def delete_installation(team_id: str) -> bool:
    """설치 정보 삭제"""
    try:
        sheet = get_sheets().worksheet("installations")
        cell = sheet.find(team_id)
        if not cell:
            return False
        sheet.delete_rows(cell.row)
        return True
    except Exception as e:
        logger.error("설치 정보 삭제 실패: %s", e)
        return False


# ============================================
# Profiles CRUD (team_id 지원)
# ============================================

def save_profile(user_id: str, team_id: str, data: dict) -> bool:
    """프로필 저장 (team_id + user_id로 식별)"""
    try:
        sheet = get_sheets().worksheet("profiles")
        min_amount = data.get("min_amount", 0)
        row_data = [
            team_id,
            user_id,
            ",".join(data["keywords"]),
            data["description"],
            data["stage"],
            data.get("region", ""),
            ",".join(data.get("support_types", [])),
            str(min_amount) if min_amount else "",
        ]
        # team_id + user_id 조합으로 기존 행 검색
        existing_row = _find_profile_row(sheet, user_id, team_id)
        if existing_row:
            sheet.update([row_data], f"A{existing_row}:H{existing_row}")
        else:
            sheet.append_row(row_data)
        return True
    except Exception as e:
        logger.error("프로필 저장 실패: %s", e)
        return False


def get_profile(user_id: str, team_id: str) -> dict | None:
    """프로필 조회 (team_id + user_id)"""
    try:
        sheet = get_sheets().worksheet("profiles")
        row_num = _find_profile_row(sheet, user_id, team_id)
        if not row_num:
            return None
        row = sheet.row_values(row_num)
        return _row_to_profile(row)
    except Exception as e:
        logger.error("프로필 조회 실패: %s", e)
        return None


def get_all_profiles() -> list[dict]:
    """모든 프로필 조회 (알림 발송용, team_id 포함)"""
    try:
        sheet = get_sheets().worksheet("profiles")
        data = sheet.get_all_values()
        if len(data) <= 1:
            return []

        profiles = []
        for row in data[1:]:
            if len(row) < 4:
                continue
            profiles.append(_row_to_profile(row))
        return profiles
    except Exception as e:
        logger.error("프로필 목록 조회 실패: %s", e)
        return []


def _find_profile_row(sheet, user_id: str, team_id: str) -> int | None:
    """team_id + user_id로 행 번호 검색"""
    cells = sheet.findall(user_id)
    for cell in cells:
        row = sheet.row_values(cell.row)
        if row and row[0] == team_id and len(row) > 1 and row[1] == user_id:
            return cell.row
    return None


def _row_to_profile(row: list) -> dict:
    """시트 행 -> 프로필 dict 변환"""
    min_amount = 0
    if len(row) > 7 and row[7]:
        try:
            min_amount = int(row[7])
        except ValueError:
            pass

    return {
        "team_id": row[0],
        "user_id": row[1],
        "keywords": row[2].split(",") if len(row) > 2 and row[2] else [],
        "description": row[3] if len(row) > 3 else "",
        "stage": row[4] if len(row) > 4 else "",
        "region": row[5] if len(row) > 5 else "",
        "support_types": row[6].split(",") if len(row) > 6 and row[6] else [],
        "min_amount": min_amount,
    }


# ============================================
# Grants CRUD (변경 없음)
# ============================================

def get_active_grants() -> list[dict]:
    """마감 전 공고 전체 조회"""
    try:
        sheet = get_sheets().worksheet("grants")
        records = sheet.get_all_records()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        active = []
        for r in records:
            deadline = str(r.get("deadline", "")).strip()
            # 마감일 없거나, 파싱 불가하거나, 오늘 이후면 포함
            if not deadline or deadline >= today or len(deadline) != 10:
                active.append(r)
        return active
    except Exception as e:
        logger.error("공고 조회 실패: %s", e)
        return []


def get_recent_grants(limit: int = 20) -> list[dict]:
    """최근 공고 조회 (하위 호환용)"""
    try:
        sheet = get_sheets().worksheet("grants")
        records = sheet.get_all_records()
        return records[-limit:] if len(records) > limit else records
    except Exception as e:
        logger.error("공고 조회 실패: %s", e)
        return []


def save_grants(grants: List[dict]) -> int:
    """공고 저장 (중복 체크 포함, 저장 건수 반환)"""
    if not grants:
        return 0

    try:
        sheet = get_sheets().worksheet("grants")

        # 기존 ID + 제목 가져오기
        existing_ids = set()
        existing_titles = set()
        try:
            data = sheet.get_all_values()
            if len(data) > 1:
                for row in data[1:]:
                    if row:
                        existing_ids.add(row[0])
                        if len(row) > 1 and row[1]:
                            existing_titles.add(re.sub(r"\s+", "", row[1]).lower())
        except Exception as e:
            logger.warning("기존 공고 목록 조회 실패, 전체 저장 진행: %s", e)

        # 신규 공고만 필터링 (ID + 제목 중복 체크)
        new_grants = []
        for g in grants:
            normalized_title = re.sub(r"\s+", "", g["title"]).lower()
            if g["id"] not in existing_ids and normalized_title not in existing_titles:
                new_grants.append(g)
                existing_titles.add(normalized_title)
        if not new_grants:
            logger.info("공고 저장 완료: 신규 0개 (기존 %d개, 전체 중복)", len(existing_ids))
            return 0

        # 전체를 한 번의 API 호출로 저장 (rate limit 회피)
        rows = [
            [
                g["id"], g["title"], g["organization"],
                g["deadline"], g["url"],
                g.get("keywords", ""), g.get("description", "")
            ]
            for g in new_grants
        ]
        sheet.append_rows(rows, value_input_option="RAW")
        new_count = len(new_grants)

        logger.info("공고 저장 완료: 신규 %d개 (기존 %d개, 중복 제외 %d개)",
                     new_count, len(existing_ids), len(grants) - new_count)
        return new_count
    except Exception as e:
        logger.error("공고 저장 실패: %s", e)
        return 0
