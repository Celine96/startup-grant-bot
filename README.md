# startup-grant-bot

![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github)
![render](https://img.shields.io/badge/render-7500FF?style=for-the-badge&logo=render)

![Python](https://img.shields.io/badge/Python-3.13.0-3776AB?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-005571?style=for-the-badge&logo=fastapi)

스타트업 지원금 매칭 Slack 봇. 정부 지원사업을 자동 수집하고, 사용자 프로필에 맞는 지원금을 매칭하여 Slack DM으로 알림을 보냅니다.

## 구조

| 파일 | 역할 |
|------|------|
| `main.py` | Slack 봇 서버 (FastAPI) |
| `crawler.py` | 크론잡 - 데이터 수집 + 알림 |
| `db.py` | Google Sheets CRUD |
| `fetchers.py` | 데이터 소스 (API + 웹 스크래핑) |
| `matcher.py` | 매칭 알고리즘 |
| `notifier.py` | Slack DM 알림 |
| `config.py` | 공통 설정 상수 |

## 데이터 소스

매주 일요일 크론잡(`crawler.py`)이 아래 소스에서 지원사업 공고를 수집합니다. API 키가 설정된 소스만 활성화되며, 모든 API 키가 없을 경우 K-Startup 웹 스크래핑으로 fallback합니다.

| 소스 | 유형 | API URL | 환경변수 |
|------|------|---------|----------|
| 기업마당 (Bizinfo) | REST API (JSON) | `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do` | `BIZINFO_API_KEY` |
| K-Startup | 공공데이터포털 API (JSON) | `https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01` | `KSTARTUP_API_KEY` |
| 중소벤처기업부 (MSS) | 공공데이터포털 API (XML) | `https://apis.data.go.kr/1421000/mssBizService_v2/getbizList_v2` | `MSS_API_KEY` |
| 중소벤처24 (SMES) | REST API (JSON) | `https://www.smes.go.kr/fnct/apiReqst/extPblancInfo` | `SMES_API_KEY` |
| K-Startup 웹 | 웹 스크래핑 (fallback) | `https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do` | - |

수집된 공고는 Google Sheets `grants` 시트에 저장되며, 소스 간 제목 기반 중복 제거가 적용됩니다.

## 매칭 알고리즘

사용자 프로필과 지원사업 공고의 적합도를 0.0~1.0 점수로 산출합니다. 3가지 기준의 가중 합산 방식입니다.

| 기준 | 가중치 | 산출 방식 |
|------|--------|-----------|
| **키워드 매칭** | 60% | 프로필 키워드가 공고 텍스트(제목+설명+키워드)에 포함되는 비율. 제목에 매칭된 키워드가 있으면 1.3배 가산 (최대 1.0) |
| **창업 단계 매칭** | 20% | 프로필의 창업 단계(예비/초기/시드/시리즈A)에 해당하는 키워드가 공고에 포함되면 1.0, 아니면 0.0 |
| **설명 유사도** | 20% | 프로필 사업 설명에서 2자 이상 단어를 추출하여 공고 텍스트에 포함되는 비율 |

### 단계별 매칭 키워드

| 창업 단계 | 매칭 키워드 |
|-----------|-------------|
| 예비 | 예비창업, 예비, 아이템 |
| 초기 | 초기창업, 초기, 사업화, 창업패키지 |
| 시드 | 시드, TIPS, 기술창업, R&D |
| 시리즈A | 시리즈, TIPS, 스케일업, 성장 |

### 매칭 흐름

```
사용자 프로필 (키워드, 사업설명, 창업단계)
        ↓
   각 공고에 대해 3가지 기준 점수 산출
        ↓
   가중 합산 (키워드 60% + 단계 20% + 설명 20%)
        ↓
   상위 3건을 Slack DM으로 알림
```

## 배포

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Celine96/startup-grant-bot)

## 환경변수

`.env.example` 참고
