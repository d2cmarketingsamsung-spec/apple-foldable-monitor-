"""무거운 수집 (매시간 실행, SerpApi 예산 가드로 자동 조절).

- SERP + AI Overview  (핵심 8키워드: product·versus)
- 연관검색어 rising 확장
- 뉴스 볼륨 (GDELT + Google Alerts RSS)
- Excel 리포트 메일 (기본 하루 1회, email_hour_utc 실행에서만)
"""
from __future__ import annotations
import traceback, datetime as dt
from .collectors import trends, serp, news
from .common import report
from .common.config import SETTINGS


def _run(name, fn):
    try:
        return fn()
    except Exception:
        print(f"[run_daily] {name} 실패:\n{traceback.format_exc()}")


def main():
    _run("serp", serp.collect)
    _run("trends_rising", lambda: trends.collect(rising=True))
    _run("news", news.collect)

    rc = SETTINGS.get("report", {})
    if rc.get("email_every_run") or dt.datetime.utcnow().hour == rc.get("email_hour_utc", 17):
        _run("email_report", report.email_report)
    else:
        print("[run_daily] 리포트 메일 시각 아님 → 생략")


if __name__ == "__main__":
    main()
