"""결과 저장 공통 유틸 (핸드오프 §10-4).

항상 data/<dataset>.jsonl 에 append.
GOOGLE_SHEETS_ID + GOOGLE_SERVICE_ACCOUNT_JSON 설정 시 해당 워크시트에도 append.
"""
from __future__ import annotations
import json, pathlib
from .config import ROOT, SETTINGS, env, iso_now

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
    _to_sheets(dataset, stamped)


def _to_sheets(dataset: str, rows: list[dict]) -> None:
    sheet_id = env("GOOGLE_SHEETS_ID") or SETTINGS["storage"].get("google_sheets_id")
    sa_json = env("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not (sheet_id and sa_json):
        return
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_info(
            json.loads(sa_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        try:
            ws = sh.worksheet(dataset)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=dataset, rows=1000, cols=26)
        # 헤더 없으면 union 키로 생성
        header = ws.row_values(1)
        if not header:
            header = sorted({k for r in rows for k in r})
            ws.append_row(header)
        ws.append_rows([[json_safe(r.get(h, "")) for h in header] for r in rows])
        print(f"[storage] sheets '{dataset}': +{len(rows)}")
    except Exception as e:  # 저장 실패가 수집을 막지 않도록
        print(f"[storage] sheets 저장 실패: {e}")


def json_safe(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
