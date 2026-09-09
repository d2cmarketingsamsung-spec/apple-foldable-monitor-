"""수집 원본(data/*.jsonl) → '해석' 시트용 파생 지표 + 신호 플래그.

신호는 **삼성 관점**: 🔴 = 삼성에 불리 / 🟡 = 주의 / 🟢 = 양호 / ⚪ = 데이터 부족.
키워드 기반 간이 판정이므로 원본 시트(snippet)와 함께 볼 것.
"""
from __future__ import annotations
from collections import defaultdict
from .config import SETTINGS

_A = SETTINGS["alerts"]
SPIKE = _A["trends_wow_spike_pct"]        # 예: 40
DROP = _A["trends_wow_drop_pct"]          # 예: -30
NEG_RATIO = _A["llm_samsung_negative_ratio"]  # 예: 0.5


def _latest(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """key 조합별로 _ingested_at 이 가장 최근인 행만."""
    best: dict[tuple, dict] = {}
    for r in rows:
        k = tuple(r.get(x) for x in keys)
        if k not in best or r.get("_ingested_at", "") > best[k].get("_ingested_at", ""):
            best[k] = r
    return list(best.values())


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 1) if xs else None


def _row(section, label, value, note, flag):
    return [section, label, value, note, flag]


def build_rows(data: dict[str, list[dict]]) -> list[list]:
    rows: list[list] = []
    reds = 0

    # ---------- 검색량 ----------
    trends = _latest(data.get("trends", []), ("country", "keyword"))
    if trends:
        by_cat = defaultdict(list)
        for r in trends:
            by_cat[r.get("category")].append(r)
        prod_idx = _mean([r.get("value_last") for r in by_cat.get("product", [])])
        base_idx = _mean([r.get("value_last") for r in by_cat.get("baseline", [])])
        versus_wow = _mean([r.get("wow_pct") for r in by_cat.get("versus", [])])
        purch_wow = _mean([r.get("wow_pct") for r in by_cat.get("purchase", [])])
        prod_wow = _mean([r.get("wow_pct") for r in by_cat.get("product", [])])
        used_fallback = any(r.get("source") == "serpapi" for r in trends)

        if prod_idx is not None and base_idx:
            ratio = round(prod_idx / base_idx * 100, 0)
            flag = "🔴" if ratio >= 100 else "🟡" if ratio >= 50 else "🟢"
            reds += flag == "🔴"
            rows.append(_row("검색량", "폴더블 vs 일반 프로모델 관심비",
                             f"{ratio:.0f}%",
                             "product 키워드 검색량 ÷ baseline(iPhone 18 Pro) 검색량. "
                             "100%↑ = 폴더블이 주력만큼 관심, 50%↓ = 니치", flag))

        for name, val, up_bad in [("versus(삼성 비교) 검색 WoW", versus_wow, True),
                                  ("purchase(가격·예약) 검색 WoW", purch_wow, True),
                                  ("product(제품명) 검색 WoW", prod_wow, True)]:
            if val is None:
                continue
            flag = "🔴" if val >= SPIKE else "🟡" if val >= 10 else (
                "🟢" if val > DROP else "⚪")
            reds += flag == "🔴"
            rows.append(_row("검색량", name, f"{val:+.0f}%",
                             f"전주 대비. +{SPIKE}%↑면 급증 신호"
                             + ("  ← 삼성과 직접 비교 트래픽" if "versus" in name else ""),
                             flag))
        if used_fallback:
            rows.append(_row("검색량", "⚠ 데이터 출처", "SerpApi 폴백",
                             "pytrends 장애로 폴백 사용 중 — 값 변동성 큼, 무료 쿼터 소모", "🟡"))

        # 국가별 versus WoW
        for country in sorted({r.get("country") for r in by_cat.get("versus", [])}):
            v = _mean([r.get("wow_pct") for r in by_cat.get("versus", [])
                       if r.get("country") == country])
            if v is None:
                continue
            flag = "🔴" if v >= SPIKE else "🟡" if v >= 10 else "🟢"
            reds += flag == "🔴"
            rows.append(_row("검색량·국가", f"{country} 삼성비교 검색 WoW", f"{v:+.0f}%",
                             "국가별 비교 수요. KR 급등 시 방어 우선순위↑", flag))
    else:
        rows.append(_row("검색량", "데이터", "없음", "trends 수집 실패 또는 미실행", "⚪"))

    # ---------- SERP / AI Overview ----------
    serp = _latest(data.get("serp", []), ("country", "keyword"))
    if serp:
        n = len(serp)
        aio = [r for r in serp if str(r.get("ai_overview_present")).lower() in ("true", "1")]
        aio_sams = sum(1 for r in aio
                       if str(r.get("ai_overview_mentions_samsung")).lower() in ("true", "1"))
        aio_ref_sams = sum(1 for r in aio
                           if str(r.get("ai_overview_ref_samsung")).lower() in ("true", "1"))
        s_ranks = [r.get("samsung_rank") for r in serp if isinstance(r.get("samsung_rank"), (int, float))]
        a_ranks = [r.get("apple_rank") for r in serp if isinstance(r.get("apple_rank"), (int, float))]

        rows.append(_row("SERP", "AI Overview 노출률", f"{len(aio)}/{n}",
                         "구글 AI 요약이 뜨는 키워드 비중. 높을수록 클릭 없이 답 소비", "🟡" if aio else "🟢"))
        if aio:
            flag = "🟢" if aio_sams == len(aio) else "🟡" if aio_sams else "🟡"
            rows.append(_row("SERP", "AI 요약 내 삼성 언급", f"{aio_sams}/{len(aio)}",
                             "삼성이 빠지면 비교 맥락에서 소외. 언급돼도 논조는 snippet 확인 필요", flag))
            rows.append(_row("SERP", "AI 요약이 samsung.com 인용", f"{aio_ref_sams}/{len(aio)}",
                             "삼성 콘텐츠가 AI 답변에 반영되는지 (SEO 성과)",
                             "🟢" if aio_ref_sams else "🟡"))
        rows.append(_row("SERP", "samsung.com 평균 순위",
                         f"{_mean(s_ranks)}" if s_ranks else "권외",
                         f"핵심 키워드 검색 시 삼성 공식몰 노출 위치 (애플 {_mean(a_ranks) or '권외'}위). "
                         "권외/하락 시 비교 트래픽 확보 실패",
                         "🔴" if not s_ranks else "🟡" if (_mean(s_ranks) or 99) > 5 else "🟢"))
        if not s_ranks:
            reds += 1
    else:
        rows.append(_row("SERP", "데이터", "없음", "serp 수집 실패 / SerpApi 예산 소진", "⚪"))

    # ---------- LLM 언급 ----------
    llm = data.get("llm_mentions", [])
    if llm:
        latest_day = max(r.get("_ingested_at", "")[:10] for r in llm)
        cur = [r for r in llm if r.get("_ingested_at", "").startswith(latest_day)]
        sams = [r for r in cur if str(r.get("samsung_mentioned")).lower() in ("true", "1")]
        neg = [r for r in sams if r.get("samsung_sentiment") == "negative"]
        pos = [r for r in sams if r.get("samsung_sentiment") == "positive"]
        both = [r for r in cur if str(r.get("apple_mentioned")).lower() in ("true", "1")
                and str(r.get("samsung_mentioned")).lower() in ("true", "1")]
        a_first = [r for r in both if str(r.get("apple_first")).lower() in ("true", "1")]

        if sams:
            ratio = len(neg) / len(sams)
            flag = "🔴" if ratio >= NEG_RATIO else "🟡" if neg else "🟢"
            reds += flag == "🔴"
            rows.append(_row("LLM(Gemini)", "삼성 언급 논조",
                             f"부정 {len(neg)} / 긍정 {len(pos)} / 총 {len(sams)}",
                             f"부정 비중 {ratio:.0%} (임계 {NEG_RATIO:.0%}). 간이 판정 → snippet 확인", flag))
        if both:
            r2 = len(a_first) / len(both)
            flag = "🟡" if r2 >= 0.7 else "🟢"
            rows.append(_row("LLM(Gemini)", "애플 먼저 언급 비율", f"{r2:.0%}",
                             "AI가 애플 중심으로 서술하는 정도 (높을수록 삼성이 후순위)", flag))
        rows.append(_row("LLM(Gemini)", "응답 수집", f"{len(cur)}건 ({latest_day})",
                         "prompt 4종 × 언어 2종. openai/anthropic은 유료라 미포함", "🟢"))
    else:
        rows.append(_row("LLM(Gemini)", "데이터", "없음", "GEMINI_API_KEY 미설정 또는 실패", "⚪"))

    # ---------- 뉴스 ----------
    news = data.get("news_volume", [])
    for r in news:
        last, avg = r.get("gdelt_volume_last", 0), r.get("gdelt_volume_avg", 0)
        if not avg:
            continue
        ratio = last / avg
        flag = "🟡" if ratio >= 1.5 else "🟢"
        rows.append(_row("뉴스", f"GDELT 언급량 · {r.get('query')}", f"최근/평균 {ratio:.1f}x",
                         "1.5x↑ = 뉴스량 재급등 (내구성 논란·판매 발표 등 이벤트 가능성)", flag))

    # ---------- 종합 ----------
    verdict = ("🔴 삼성에 불리한 신호 다수" if reds >= 3
               else "🟡 일부 주의 신호" if reds >= 1
               else "🟢 특이 신호 없음")
    rows.insert(0, ["구분", "지표", "값", "해석", "신호"])
    rows.insert(0, ["종합", "삼성 관점 종합 판정", verdict,
                    f"🔴 신호 {reds}개. 데이터 1~2회치면 절대값보다 추세로 판단", ""])
    rows.insert(0, ["", "", "", "", ""])
    rows.insert(0, ["※ 신호 = 삼성 관점", "🔴 불리 · 🟡 주의 · 🟢 양호 · ⚪ 데이터부족",
                    "", "간이 판정이므로 원본 시트(snippet)와 교차 확인", ""])
    return rows
