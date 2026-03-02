"""
공통 설정 상수
"""

# Google Sheets 컬럼 정의
GRANT_COLUMNS = ['id', 'title', 'organization', 'deadline', 'url', 'keywords', 'description']
PROFILE_COLUMNS = ['user_id', 'keywords', 'description', 'stage', 'region', 'support_types']

# 매칭 설정
MAX_MATCH_RESULTS = 3
MAX_GRANTS_TO_SCAN = 20

# 프로필 옵션
STAGE_OPTIONS = ['예비', '초기', '시드', '시리즈A']

# API URLs
BIZINFO_API_URL = 'https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do'
KSTARTUP_API_URL = 'https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01'
KSTARTUP_WEB_URL = 'https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do'

# Google Sheets API 스코프
SHEETS_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
