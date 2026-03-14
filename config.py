"""
공통 설정 상수
"""

import os

# Slack OAuth
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_SCOPES = [
    "commands", "chat:write", "im:write",
    "users:read", "channels:read",
]

# Google Sheets 컬럼 정의
GRANT_COLUMNS = ["id", "title", "organization", "deadline", "url", "keywords", "description", "region", "max_amount"]
PROFILE_COLUMNS = ["team_id", "user_id", "keywords", "description", "stage", "region", "support_types", "min_amount", "founding_year", "previous_support", "revenue_range", "business_type", "ceo_age_range"]

# 매칭 설정
MAX_MATCH_RESULTS = 3
MAX_GRANTS_TO_SCAN = 20
MIN_DEADLINE_DAYS = 14
MIN_MATCH_SCORE = 0.25  # 25% 미만은 결과에서 제외

# 프로필 옵션
STAGE_OPTIONS = ["예비", "초기", "시드", "시리즈A"]

REGION_OPTIONS = [
    "전국(무관)", "서울", "경기", "인천", "부산", "대구", "광주",
    "대전", "울산", "세종", "강원", "충북", "충남",
    "전북", "전남", "경북", "경남", "제주",
]

FOUNDING_YEAR_OPTIONS = list(range(2015, 2027))

PREVIOUS_SUPPORT_OPTIONS = [
    "창업패키지(예비/초기)",
    "TIPS",
    "청년창업사관학교",
    "기타 정부지원사업",
]

REVENUE_RANGE_OPTIONS = ["1억 미만", "1억~5억", "5억~10억", "10억~50억", "50억 이상"]

BUSINESS_TYPE_OPTIONS = [
    "제조업", "정보통신업(SW/IT)", "도소매업", "음식/숙박업",
    "교육서비스업", "전문/과학기술업", "보건/사회복지", "문화/예술/여가",
    "건설업", "농림어업", "기타",
]

CEO_AGE_RANGE_OPTIONS = ["만 39세 이하 (청년)", "만 40~64세", "만 65세 이상 (시니어)"]

# API URLs
BIZINFO_API_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
KSTARTUP_API_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
KSTARTUP_WEB_URL = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
MSS_API_URL = "https://apis.data.go.kr/1421000/mssBizService_v2/getbizList_v2"
SMES_API_URL = "https://www.smes.go.kr/fnct/apiReqst/extPblancInfo"

# Google Sheets API 스코프
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
