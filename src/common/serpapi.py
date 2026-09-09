"""SerpApi 공통 클라이언트 + 무료 쿼터(250회/월) 보호 가드.

이번 달 호출 수를 data/_serp_quota.json 에 누적. 예산 초과 시 QuotaExceeded.
"""
from __future__ import annotations
import json, datetime as dt, requests
from .config import ROOT, SETTINGS, env

_QUOTA_FILE = ROOT / SETTINGS["storage"]["local_dir"] / "_serp_quota.json"
_BUDGET = SETTINGS.get("serp", {}).get("monthly_call_budget", 230)


class QuotaExceeded(RuntimeError):
    pass


def remaining() -> int:
    month = dt.date.today().strftime("%Y-%m")
    try:
        used = json.loads(_QUOTA_FILE.read_text()).get(month, 0)
    except Exception:
        used = 0
    return max(0, _BUDGET - used)


def _inc() -> None:
    month = dt.date.today().strftime("%Y-%m")
    try:
        d = json.loads(_QUOTA_FILE.read_text())
    except Exception:
        d = {}
    if d.get(month, 0) >= _BUDGET:
        raise QuotaExceeded(f"{month} SerpApi {d.get(month, 0)}/{_BUDGET} 도달")
    _QUOTA_FILE.parent.mkdir(exist_ok=True)
    _QUOTA_FILE.write_text(json.dumps({month: d.get(month, 0) + 1}))


def get(params: dict) -> dict:
    _inc()
    params = {**params, "api_key": env("SERPAPI_KEY")}
    return requests.get("https://serpapi.com/search", params=params, timeout=40).json()
