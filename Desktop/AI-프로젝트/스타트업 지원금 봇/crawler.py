"""
창업지원금 크롤러 크론잡
데이터 수집 → 저장 → 알림
"""

from datetime import datetime

from db import save_grants
from fetchers import fetch_all_grants
from notifier import notify_users


def main():
    print(f"\n{'='*60}")
    print("창업지원금 크롤러")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    try:
        # 1. 데이터 수집
        grants = fetch_all_grants()
        print(f"\n수집 완료: {len(grants)}건")

        if not grants:
            print("수집된 공고 없음 - 종료")
            return

        # 2. 저장 (중복 체크 포함)
        new_count = save_grants(grants)
        print(f"신규 저장: {new_count}건")

        # 3. 새 공고가 있으면 알림 발송
        if new_count > 0:
            # 새로 저장된 공고만 필터링 (id 기준)
            notify_users(grants)

        print(f"\n{'='*60}")
        print("크롤러 완료")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
