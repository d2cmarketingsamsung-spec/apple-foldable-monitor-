"""주간 실행 엔트리.

- trends rising queries 로 seed 키워드 확장 후보 수집 (핸드오프 §7)
- 뉴스 볼륨(2차) 수집
"""
from __future__ import annotations
import traceback
from .collectors import trends, news


def _run(name, fn):
    try:
        return fn()
    except Exception:
        print(f"[run_weekly] {name} 실패:\n{traceback.format_exc()}")


def main():
    _run("trends+rising", lambda: trends.collect(rising=True))
    _run("news", news.collect)


if __name__ == "__main__":
    main()
