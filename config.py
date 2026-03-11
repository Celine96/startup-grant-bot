"""
공통 설정 상수
"""

import os

# Slack OAuth
SLACK_CLIENT_ID = os.getenv('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET')
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')
SLACK_SCOPES = [
    'commands', 'chat:write', 'im:write',
    'users:read', 'channels:read',
]

# Google Sheets 컬럼 정의
GRANT_COLUMNS = ['id', 'title', 'organization', 'deadline', 'url', 'keywords', 'description']
PROFILE_COLUMNS = ['team_id', 'user_id', 'keywords', 'description', 'stage', 'region', 'support_types', 'min_amount']

# 매칭 설정
MAX_MATCH_RESULTS = 3
MAX_GRANTS_TO_SCAN = 20
MIN_DEADLINE_DAYS = 14

# 프로필 옵션
STAGE_OPTIONS = ['예비', '초기', '시드', '시리즈A']

REGION_OPTIONS = [
    '전국(무관)', '서울', '경기', '인천', '부산', '대구', '광주',
    '대전', '울산', '세종', '강원', '충북', '충남',
    '전북', '전남', '경북', '경남', '제주',
]

# API URLs
BIZINFO_API_URL = 'https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do'
KSTARTUP_API_URL = 'https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01'
KSTARTUP_WEB_URL = 'https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do'
MSS_API_URL = 'https://apis.data.go.kr/1421000/mssBizService_v2/getbizList_v2'
SMES_API_URL = 'https://www.smes.go.kr/fnct/apiReqst/extPblancInfo'

# Google Sheets API 스코프
SHEETS_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
