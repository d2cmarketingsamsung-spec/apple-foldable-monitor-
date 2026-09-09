"""결과 저장 (핸드오프 §10-4).

data/<dataset>.jsonl 에 append. 리포트(Excel)는 report.py 가 이 파일들을 읽어 생성.
"""
from __future__ import annotations
import json
from .config import ROOT, SETTINGS, iso_now

DATA_DIR = ROOT / SETTINGS["storage"]["local_dir"]
DATA_DIR.mkdir(exist_ok=True)


def save_rows(dataset: str, rows: list[dict]) -> None:
    if not rows:
        return
    stamped = [{"_ingested_at": iso_now(), **r} for r in rows]
    path = DATA_DIR / f"{dataset}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        for r in stamped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[storage] {dataset}: +{len(rows)} rows -> {path.name}")
