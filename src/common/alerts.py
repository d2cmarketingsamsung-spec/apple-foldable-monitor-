"""임계치 초과 알림 (핸드오프 §7). Slack Webhook / 이메일(stub)."""
from __future__ import annotations
import json, requests
from .config import env, SETTINGS


def notify(title: str, lines: list[str]) -> None:
    text = f"*{title}*\n" + "\n".join(f"• {l}" for l in lines)
    channel = SETTINGS["alerts"].get("channel", "slack")
    if channel == "slack" and env("SLACK_WEBHOOK_URL"):
        try:
            requests.post(env("SLACK_WEBHOOK_URL"), json={"text": text}, timeout=15)
            print("[alerts] slack 전송")
            return
        except Exception as e:
            print(f"[alerts] slack 실패: {e}")
    print("[alerts] (미전송) " + text.replace("\n", " | "))


def check_trends_spikes(rows: list[dict]) -> list[str]:
    a = SETTINGS["alerts"]
    hits = []
    for r in rows:
        wow = r.get("wow_pct")
        if wow is None:
            continue
        if wow >= a["trends_wow_spike_pct"]:
            hits.append(f"[{r['country']}] '{r['keyword']}' 검색량 +{wow:.0f}% WoW")
        elif wow <= a["trends_wow_drop_pct"]:
            hits.append(f"[{r['country']}] '{r['keyword']}' 검색량 {wow:.0f}% WoW")
    return hits


def check_llm_samsung_sentiment(rows: list[dict]) -> list[str]:
    a = SETTINGS["alerts"]
    neg = [r for r in rows if r.get("samsung_sentiment") == "negative"]
    total = [r for r in rows if r.get("samsung_mentioned")]
    if total and len(neg) / len(total) >= a["llm_samsung_negative_ratio"]:
        return [f"LLM 응답에서 삼성 부정 언급 {len(neg)}/{len(total)} ({len(neg)/len(total):.0%})"]
    return []
