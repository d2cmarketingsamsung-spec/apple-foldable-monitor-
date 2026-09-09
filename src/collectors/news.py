"""뉴스 볼륨 (핸드오프 §6, §10-5, 2차 우선순위).

GDELT DOC 2.0 API(넓게) + Google Alerts RSS(정밀). 둘 다 무료.
Google Alerts 피드 URL은 config/settings.yaml 대신 환경변수 GOOGLE_ALERTS_FEEDS
(콤마구분)로 주입.
"""
from __future__ import annotations
import os, datetime as dt, requests, feedparser
from ..common.storage import save_rows

QUERIES = ['"iPhone Fold"', '"iPhone Ultra" Apple foldable', '"foldable iPhone"']


def _gdelt(query: str) -> dict:
    r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params={
        "query": query, "mode": "timelinevolinfo", "timespan": "7d", "format": "json",
    }, timeout=40)
    try:
        series = r.json().get("timeline", [{}])[0].get("data", [])
    except Exception:
        series = []
    vals = [p.get("value", 0) for p in series]
    return {"query": query, "gdelt_points": len(vals),
            "gdelt_volume_last": vals[-1] if vals else 0,
            "gdelt_volume_avg": round(sum(vals) / len(vals), 4) if vals else 0}


def _alerts() -> list[dict]:
    feeds = [u for u in os.environ.get("GOOGLE_ALERTS_FEEDS", "").split(",") if u.strip()]
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
    out = []
    for url in feeds:
        d = feedparser.parse(url.strip())
        for e in d.entries:
            pub = getattr(e, "published_parsed", None)
            when = dt.datetime(*pub[:6], tzinfo=dt.timezone.utc) if pub else None
            if when and when < cutoff:
                continue
            out.append({"source": "google_alerts", "title": e.get("title", ""),
                        "link": e.get("link", ""), "published": e.get("published", "")})
    return out


def collect() -> list[dict]:
    rows = [_gdelt(q) for q in QUERIES]
    save_rows("news_volume", rows)
    save_rows("news_articles", _alerts())
    return rows


if __name__ == "__main__":
    collect()
