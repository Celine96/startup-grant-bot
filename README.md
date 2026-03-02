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

## 배포

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Celine96/startup-grant-bot)

## 환경변수

`.env.example` 참고
