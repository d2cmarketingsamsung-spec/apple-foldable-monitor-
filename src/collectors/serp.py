"""SERP 노출 + AI Overview / AI Mode 수집 (핸드오프 §6, §10-2).

SerpApi Google Search API. 무료 250회/월 쿼터 → 국가×핵심 카테고리로 제한.
"""
from __future__ import annotations
import time, requests
from ..common.config import KEYWORDS, SETTINGS, env, keywords_for
from ..common.storage import save_rows

APPLE_DOMAINS = ("apple.com",)
SAMSUNG_DOMAINS = ("samsung.com",)


def _search(query: str, loc: dict) -> dict:
    r = requests.get("https://serpapi.com/search", params={
        "engine": "google", "q": query,
        "gl": loc["gl"], "hl": loc["hl"], "google_domain": loc["google_domain"],
        "api_key": env("SERPAPI_KEY"),
    }, timeout=40)
    return r.json()


def _ai_overview(page: dict, loc: dict) -> dict:
    """AI Overview 블록. page_token 이 오면 전용 엔드포인트로 재조회."""
    ai = page.get("ai_overview")
    if ai and "page_token" in ai:
        r = requests.get("https://serpapi.com/search", params={
            "engine": "google_ai_overview", "page_token": ai["page_token"],
            "api_key": env("SERPAPI_KEY"),
        }, timeout=40)
        ai = r.json().get("ai_overview", ai)
    if not ai:
        return {"ai_overview_present": False}
    text = " ".join(b.get("snippet", "") for b in ai.get("text_blocks", []))
    refs = [s.get("link", "") for s in ai.get("references", [])]
    return {
        "ai_overview_present": True,
        "ai_overview_mentions_apple": _has(text, ["apple", "iphone fold", "iphone ultra"]),
        "ai_overview_mentions_samsung": _has(text, ["samsung", "galaxy"]),
        "ai_overview_ref_apple": any("apple.com" in u for u in refs),
        "ai_overview_ref_samsung": any("samsung.com" in u for u in refs),
        "ai_overview_snippet": text[:500],
    }


def collect() -> list[dict]:
    loc_map = SETTINGS["serp"]["engine_locale"]
    rows = []
    for country in KEYWORDS["countries"]:
        loc = loc_map[country]
        # 쿼터 절약: product 1개 + versus 1개만 (국가당 2회)
        picks = keywords_for(country, ["product"])[:1] + keywords_for(country, ["versus"])[:1]
        for kw in picks:
            page = _search(kw["keyword"], loc)
            organic = page.get("organic_results", []) or []
            top10 = organic[:10]
            row = {
                "country": country, "keyword": kw["keyword"], "category": kw["category"],
                "organic_count": len(organic),
                "apple_rank": _rank(top10, APPLE_DOMAINS),
                "samsung_rank": _rank(top10, SAMSUNG_DOMAINS),
                "has_news_pack": "top_stories" in page,
                "has_video_pack": "inline_videos" in page,
                **_ai_overview(page, loc),
            }
            rows.append(row)
            time.sleep(1.5)
    save_rows("serp", rows)
    return rows


def _rank(results, domains):
    for i, r in enumerate(results, 1):
        if any(d in (r.get("link") or "") for d in domains):
            return i
    return None

def _has(text, needles):
    t = text.lower()
    return any(n in t for n in needles)


if __name__ == "__main__":
    collect()
