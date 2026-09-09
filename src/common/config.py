"""설정/키워드/프롬프트 로더 + 공통 유틸."""
from __future__ import annotations
import os, pathlib, datetime as dt
import yaml
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _load(name: str) -> dict:
    with open(ROOT / "config" / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


KEYWORDS = _load("keywords.yaml")
PROMPTS = _load("prompts.yaml")
SETTINGS = _load("settings.yaml")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def today() -> str:
    return dt.date.today().isoformat()


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def keywords_for(country: str, categories: list[str] | None = None) -> list[dict]:
    """[{keyword, category, country}] 평탄화 리스트."""
    sets = KEYWORDS["sets"][country]
    cats = categories or list(sets.keys())
    out = []
    for cat in cats:
        for kw in sets.get(cat, []):
            out.append({"keyword": kw, "category": cat, "country": country})
    return out
