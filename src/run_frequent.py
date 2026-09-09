"""1시간 주기 실행 (론칭 직후 집중 모니터링).

쿼터 부담이 없는 검색량 + LLM 3사 언급만. SERP/뉴스는 run_daily 로 분리.
"""
from __future__ import annotations
import traceback
from .common import alerts
from .collectors import trends, llm_mentions


def _run(name, fn):
    try:
        return fn()
    except Exception:
        print(f"[run_frequent] {name} 실패:\n{traceback.format_exc()}")
        return []


def main():
    t_rows = _run("trends", lambda: trends.collect(rising=False))
    l_rows = _run("llm_mentions", llm_mentions.collect)
    fired = alerts.check_trends_spikes(t_rows) + alerts.check_llm_samsung_sentiment(l_rows)
    if fired:
        alerts.notify("애플 폴더블 모니터링 — 임계치 알림", fired)


if __name__ == "__main__":
    main()
