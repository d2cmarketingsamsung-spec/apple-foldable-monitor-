"""하루 1회 실행 (SerpApi 쿼터 절약 대상).

- SERP + AI Overview  (핵심 8키워드: product·versus)
- 연관검색어 rising 확장
- 뉴스 볼륨 (GDELT + Google Alerts RSS)
"""
from __future__ import annotations
import traceback
from .collectors import trends, serp, news


def _run(name, fn):
    try:
        return fn()
    except Exception:
        print(f"[run_daily] {name} 실패:\n{traceback.format_exc()}")


def main():
    _run("serp", serp.collect)
    _run("trends_rising", lambda: trends.collect(rising=True))
    _run("news", news.collect)


if __name__ == "__main__":
    main()
