"""
데이터 소스 모듈 - API + 웹 스크래핑 플러그인 구조
"""

import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import BIZINFO_API_URL, KSTARTUP_API_URL, KSTARTUP_WEB_URL


def fetch_all_grants() -> list[dict]:
    """사용 가능한 소스에서 순차적으로 지원사업 가져오기"""
    grants = []

    if os.getenv('BIZINFO_API_KEY'):
        print("Bizinfo API로 수집 중...")
        try:
            grants.extend(fetch_from_bizinfo())
            print(f"  Bizinfo: {len(grants)}건 수집")
        except Exception as e:
            print(f"  Bizinfo API 실패: {e}")

    if os.getenv('KSTARTUP_API_KEY'):
        print("K-Startup API로 수집 중...")
        try:
            kstartup_grants = fetch_from_kstartup()
            grants.extend(kstartup_grants)
            print(f"  K-Startup: {len(kstartup_grants)}건 수집")
        except Exception as e:
            print(f"  K-Startup API 실패: {e}")

    if not grants:
        print("API 키 없음 - 웹 스크래핑 fallback 사용...")
        try:
            grants.extend(fetch_from_web_scraping())
            print(f"  스크래핑: {len(grants)}건 수집")
        except Exception as e:
            print(f"  웹 스크래핑 실패: {e}")

    return grants


def fetch_from_bizinfo() -> list[dict]:
    """기업마당 API"""
    api_key = os.getenv('BIZINFO_API_KEY')
    grants = []
    page = 1

    while True:
        resp = requests.get(BIZINFO_API_URL, params={
            'crtfcKey': api_key,
            'dataType': 'json',
            'pageUnit': 50,
            'pageIndex': page,
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get('jsonArray', [])
        if not items:
            break

        for item in items:
            grants.append(normalize_grant_bizinfo(item))

        total = int(items[0].get('totCnt', 0)) if items else 0
        if page * 50 >= total:
            break
        page += 1

    return grants


def normalize_grant_bizinfo(raw: dict) -> dict:
    """Bizinfo 응답을 표준 스키마로 변환"""
    deadline = ''
    period = raw.get('reqstBeginEndDe', '')
    if '~' in period:
        deadline = period.split('~')[-1].strip()

    url = raw.get('pblancUrl', '')
    if url and not url.startswith('http'):
        url = f"https://www.bizinfo.go.kr{url}"

    description = raw.get('bsnsSumryCn', '')
    description = re.sub(r'<[^>]+>', '', description).strip()

    return {
        'id': f"bizinfo-{raw.get('pblancId', '')}",
        'title': raw.get('pblancNm', ''),
        'organization': raw.get('jrsdInsttNm', '') or raw.get('excInsttNm', ''),
        'deadline': deadline,
        'url': url,
        'keywords': raw.get('hashtags', '') or raw.get('pldirSportRealmLclasCodeNm', ''),
        'description': description[:500],
    }


def fetch_from_kstartup() -> list[dict]:
    """K-Startup API (data.go.kr)"""
    api_key = os.getenv('KSTARTUP_API_KEY')
    grants = []
    page = 1

    while True:
        resp = requests.get(KSTARTUP_API_URL, params={
            'serviceKey': api_key,
            'page': page,
            'perPage': 50,
            'returnType': 'json',
            'cond[rcrt_prgs_yn::EQ]': 'Y',
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get('data', [])
        if not items:
            break

        for item in items:
            grants.append(normalize_grant_kstartup(item))

        total = data.get('totalCount', 0)
        if page * 50 >= total:
            break
        page += 1

    return grants


def normalize_grant_kstartup(raw: dict) -> dict:
    """K-Startup 응답을 표준 스키마로 변환"""
    deadline = raw.get('pbanc_rcpt_end_dt', '')
    if deadline and len(deadline) == 8:
        deadline = f"{deadline[:4]}-{deadline[4:6]}-{deadline[6:8]}"

    return {
        'id': f"kstartup-{raw.get('pbanc_sn', '')}",
        'title': raw.get('biz_pbanc_nm', ''),
        'organization': raw.get('sprv_inst', '') or raw.get('pbanc_ntrp_nm', ''),
        'deadline': deadline,
        'url': raw.get('biz_aply_url', '') or raw.get('detl_pg_url', ''),
        'keywords': raw.get('supt_biz_clsfc', ''),
        'description': (raw.get('pbanc_ctnt', '') or raw.get('aply_trgt_ctnt', ''))[:500],
    }


def fetch_from_web_scraping() -> list[dict]:
    """k-startup.go.kr 공고 페이지 스크래핑 (API 키 없을 때 fallback)"""
    grants = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for page in range(1, 4):
        resp = requests.get(
            KSTARTUP_WEB_URL,
            params={'pageIndex': page},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        items = soup.select('div.board_list-wrap div.list_wrap > a')
        if not items:
            break

        for item in items:
            grant = parse_web_item(item)
            if grant:
                grants.append(grant)

    return grants


def parse_web_item(item) -> dict | None:
    """HTML 공고 항목 파싱"""
    try:
        href = item.get('href', '')
        pbanc_sn_match = re.search(r'go_view\((\d+)\)', href)
        if not pbanc_sn_match:
            pbanc_sn_match = re.search(r'pbancSn=(\d+)', href)
        if not pbanc_sn_match:
            return None
        pbanc_sn = pbanc_sn_match.group(1)

        title_el = item.select_one('p.tit')
        title = title_el.get_text(strip=True) if title_el else ''

        if not title:
            return None

        # 마감일 추출
        deadline = ''
        deadline_el = item.select_one('.right .txt')
        if deadline_el:
            text = deadline_el.get_text(strip=True)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if date_match:
                deadline = date_match.group(1)

        # 기관명, 프로그램명
        li_items = item.select('.ann_cont ul li')
        organization = ''
        program = ''
        if len(li_items) >= 2:
            program = li_items[0].get_text(strip=True)
            organization = li_items[1].get_text(strip=True)

        # 카테고리
        category = ''
        flag_el = item.select_one('.flag.type01, .flag:not(.day)')
        if flag_el:
            category = flag_el.get_text(strip=True)

        detail_url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={pbanc_sn}"

        return {
            'id': f"web-{pbanc_sn}",
            'title': title,
            'organization': organization,
            'deadline': deadline,
            'url': detail_url,
            'keywords': ','.join(filter(None, [category, program])),
            'description': f"{program} - {organization}" if program else title,
        }
    except Exception:
        return None
