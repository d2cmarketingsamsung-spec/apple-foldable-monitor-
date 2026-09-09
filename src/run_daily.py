"""매일 실행 엔트리 (1차 우선순위: 검색량·SERP·AI Overview·LLM 3사).

각 수집기는 독립적으로 실패해도 나머지를 막지 않음.
"""
from __future__ import annotations
import traceback
from .common import alerts
from .collectors import trends, serp, llm_mentions


def _run(name, fn):
    try:
        return fn()
    except Exception:
        print(f"[run_daily] {name} 전체 실패:\n{traceback.format_exc()}")
        return []


def main():
    t_rows = _run("trends", lambda: trends.collect(rising=False))
    _run("serp", serp.collect)
    l_rows = _run("llm_mentions", llm_mentions.collect)

    fired = alerts.check_trends_spikes(t_rows) + alerts.check_llm_samsung_sentiment(l_rows)
    if fired:
        alerts.notify("애플 폴더블 모니터링 — 임계치 알림", fired)


if __name__ == "__main__":
    main()
