"""검색량 수집 (핸드오프 §6, §8).

기본: pytrends. 403 등 실패 시 SerpApi google_trends 로 폴백.
- interest_over_time: 최근 12주, WoW 변화율 계산
- related_queries(rising): seed 키워드 확장 (주간)
"""
from __future__ import annotations
import time
from ..common.config import KEYWORDS, SETTINGS, env, keywords_for
from ..common.storage import save_rows


def _patch_urllib3_retry() -> None:
    """urllib3 2.x 는 Retry(method_whitelist=) 를 제거 → pytrends 4.9.x 가 깨짐.
    kwarg 를 allowed_methods 로 넘겨주는 얇은 shim (urllib3 1.x 면 무해)."""
    try:
        import urllib3.util.retry as _r
        import inspect
        if "method_whitelist" in inspect.signature(_r.Retry.__init__).parameters:
            return
        _orig = _r.Retry.__init__

        def _init(self, *a, **kw):
            if "method_whitelist" in kw:
                kw["allowed_methods"] = kw.pop("method_whitelist")
            _orig(self, *a, **kw)

        _r.Retry.__init__ = _init
    except Exception:
        pass


def _pytrends_iot(keywords: list[str], geo: str) -> list[dict]:
    _patch_urllib3_retry()
    from pytrends.request import TrendReq

    py = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=0.5)
    out = []
    for chunk in _chunks(keywords, 5):
        py.build_payload(chunk, timeframe="today 3-m", geo=geo)
        df = py.interest_over_time()
        if df.empty:
            continue
        for kw in chunk:
            if kw not in df:
                continue
            s = df[kw].tolist()
            last, prev = _weekly_last_prev(s)
            out.append({
                "keyword": kw, "geo": geo,
                "value_last": last, "value_prev": prev,
                "wow_pct": _pct(prev, last), "source": "pytrends",
            })
        time.sleep(1)
    return out


def _serpapi_iot(keywords: list[str], geo: str) -> list[dict]:
    from ..common.serpapi import get as serpapi_get, QuotaExceeded, remaining

    if not env("SERPAPI_KEY"):
        return []
    # 폴백은 SERP 수집용 예산을 침범하지 않도록 소량만 (핵심 키워드 우선)
    budget = min(len(keywords), max(0, remaining() - 40), 6)
    out = []
    for kw in keywords[:budget]:
        try:
            r = serpapi_get({"engine": "google_trends", "q": kw, "geo": geo, "date": "today 3-m"})
        except QuotaExceeded:
            break
        data = r.get("interest_over_time", {}).get("timeline_data", [])
        vals = [int(p["values"][0].get("extracted_value", 0)) for p in data]
        last, prev = _weekly_last_prev(vals)
        out.append({
            "keyword": kw, "geo": geo, "value_last": last, "value_prev": prev,
            "wow_pct": _pct(prev, last), "source": "serpapi",
        })
        time.sleep(1)
    return out


def _rising_queries(keywords: list[str], geo: str) -> list[dict]:
    """related_queries(rising). Google 이 429 를 자주 뱉으므로 best-effort:
    청크별로 실패해도 다음 청크 계속, 청크 사이 간격을 넉넉히."""
    _patch_urllib3_retry()
    from pytrends.request import TrendReq

    py = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=1.0)
    out = []
    for chunk in _chunks(keywords, 5):
        for attempt in range(2):
            try:
                py.build_payload(chunk, timeframe="today 1-m", geo=geo)
                rq = py.related_queries()
                for seed, d in rq.items():
                    rising = d.get("rising")
                    if rising is None:
                        continue
                    for _, row in rising.iterrows():
                        out.append({"seed": seed, "geo": geo,
                                    "rising_query": row["query"], "value": int(row["value"])})
                break
            except Exception as e:
                if attempt == 0:
                    time.sleep(10)
                else:
                    print(f"[trends] rising {geo} {chunk} 실패: {e}")
        time.sleep(5)
    return out


def collect(rising: bool = False) -> list[dict]:
    all_rows = []
    for country in KEYWORDS["countries"]:
        geo = KEYWORDS["geo"][country]
        kws = [k["keyword"] for k in keywords_for(country)]
        try:
            rows = _pytrends_iot(kws, geo)
            if not rows:
                raise RuntimeError("pytrends 빈 결과")
        except Exception as e:
            print(f"[trends] {country} pytrends 실패({e}) -> SerpApi 폴백")
            rows = _serpapi_iot(kws, geo)
        for r in rows:
            r["country"] = country
        all_rows += rows
        if rising:
            save_rows("trends_rising", [{**r, "country": country}
                                        for r in _rising_queries(kws, geo)])
    save_rows("trends", all_rows)
    return all_rows


# --- helpers ---
def _chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]

def _weekly_last_prev(series: list[int]):
    if not series:
        return 0, 0
    if len(series) < 8:
        return series[-1], series[0]
    return round(sum(series[-7:]) / 7, 1), round(sum(series[-14:-7]) / 7, 1)

def _pct(prev, last):
    if not prev:
        return None
    return round((last - prev) / prev * 100, 1)


if __name__ == "__main__":
    import sys
    collect(rising="--rising" in sys.argv)
