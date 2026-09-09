"""LLM 언급 모니터링 (핸드오프 §5, §10-3).

Gemini / OpenAI / Anthropic 3사에 동일 프롬프트 세트(en + ko) 매일 호출.
응답에서 브랜드 언급 여부·첫 등장 순서·간이 감성 집계.
"""
from __future__ import annotations
from ..common.config import PROMPTS, SETTINGS, env
from ..common.storage import save_rows

L = SETTINGS["llm"]
NEG = ["fragile", "crease", "durability concern", "delay", "expensive", "overpriced",
       "부서", "주름", "내구성 우려", "비싸", "지연"]
POS = ["impressive", "best", "worth it", "durable", "innovative",
       "인상적", "최고", "값어치", "튼튼", "혁신"]


def _gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=env("GEMINI_API_KEY"))
    m = genai.GenerativeModel(L["gemini_model"])
    return m.generate_content(prompt).text or ""


def _openai(prompt: str) -> str:
    from openai import OpenAI
    c = OpenAI(api_key=env("OPENAI_API_KEY"))
    r = c.chat.completions.create(
        model=L["openai_model"], temperature=L["temperature"],
        max_tokens=L["max_tokens"], messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content or ""


def _anthropic(prompt: str) -> str:
    import anthropic
    c = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))
    r = c.messages.create(
        model=L["anthropic_model"], max_tokens=L["max_tokens"],
        temperature=L["temperature"], messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in r.content if b.type == "text")


PROVIDERS = {"gemini": _gemini, "openai": _openai, "anthropic": _anthropic}


def _analyze(text: str) -> dict:
    t = text.lower()
    ents = PROMPTS["entities"]
    first = {}
    for name, aliases in ents.items():
        pos = min((t.find(a.lower()) for a in aliases if a.lower() in t), default=-1)
        first[name] = pos
    apple_p, sams_p = first["apple"], first["samsung"]
    return {
        "apple_mentioned": apple_p >= 0,
        "samsung_mentioned": sams_p >= 0,
        "apple_first": apple_p >= 0 and (sams_p < 0 or apple_p < sams_p),
        "samsung_sentiment": _sent(text) if sams_p >= 0 else None,
        "response_chars": len(text),
        "response_snippet": text[:600],
    }


def _sent(text: str) -> str:
    t = text.lower()
    n = sum(w in t for w in NEG)
    p = sum(w in t for w in POS)
    return "negative" if n > p else "positive" if p > n else "neutral"


def collect() -> list[dict]:
    rows = []
    for ptype in PROMPTS["types"]:
        for lang in ("en", "ko"):
            prompt = ptype[lang]
            for prov, fn in PROVIDERS.items():
                try:
                    text = fn(prompt)
                except Exception as e:
                    print(f"[llm] {prov}/{ptype['id']}/{lang} 실패: {e}")
                    continue
                rows.append({
                    "provider": prov, "prompt_id": ptype["id"], "lang": lang,
                    "prompt": prompt, **_analyze(text),
                })
    save_rows("llm_mentions", rows)
    return rows


if __name__ == "__main__":
    collect()
