"""수집 결과(data/*.jsonl)를 Excel 워크북으로 묶어 이메일 발송.

- 데이터셋별로 시트 1개 (trends, serp, llm_mentions, news_volume, ...)
- 'summary' 시트에 최신 핵심 지표 요약
- SMTP(기본 Gmail)로 첨부 발송
"""
from __future__ import annotations
import json, io, smtplib, datetime as dt
from email.message import EmailMessage
from pathlib import Path
from .config import ROOT, SETTINGS, env, today

DATA_DIR = ROOT / SETTINGS["storage"]["local_dir"]


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_workbook() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from . import interpret

    wb = Workbook()
    wb.remove(wb.active)
    paths = [p for p in sorted(DATA_DIR.glob("*.jsonl")) if not p.stem.startswith("_")]
    data = {p.stem: _read_jsonl(p) for p in paths}

    # 1) 해석 시트 (맨 앞)
    hs = wb.create_sheet("해석")
    for r in interpret.build_rows(data):
        hs.append(r)
    for row in hs.iter_rows():
        if row[0].value in ("구분", "종합") or str(row[0].value).startswith("※"):
            for c in row:
                c.font = Font(bold=True)
    widths = {"A": 16, "B": 30, "C": 26, "D": 60, "E": 8}
    for col, w in widths.items():
        hs.column_dimensions[col].width = w
    for row in hs.iter_rows():
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)

    # 2) summary 시트
    summary = wb.create_sheet("summary")
    summary.append(["dataset", "총 행수", "마지막 수집(UTC)"])

    # 3) 데이터셋별 원본 시트
    for name, rows in data.items():
        if not rows:
            continue
        ws = wb.create_sheet(name[:31])
        header = list(dict.fromkeys(k for r in rows for k in r))
        ws.append(header)
        for r in rows:
            ws.append([_cell(r.get(h, "")) for h in header])
        summary.append([name, len(rows),
                        max((r.get("_ingested_at", "") for r in rows), default="")])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cell(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return v


def email_report(subject: str | None = None, body: str = "") -> None:
    to = env("REPORT_EMAIL_TO")
    user = env("SMTP_USER")
    pw = env("SMTP_PASS")
    if not (to and user and pw):
        print("[report] SMTP_USER/SMTP_PASS/REPORT_EMAIL_TO 미설정 → 발송 생략")
        return

    xlsx = build_workbook()
    msg = EmailMessage()
    msg["Subject"] = subject or f"[애플 폴더블 모니터링] {today()} 리포트"
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body or "첨부된 Excel 워크북에 최신 수집 데이터가 담겨 있습니다.")
    msg.add_attachment(
        xlsx, maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"apple_foldable_monitor_{today()}.xlsx",
    )

    host = env("SMTP_HOST", "smtp.gmail.com")
    port = int(env("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"[report] 발송 완료 → {to}")


if __name__ == "__main__":
    email_report()
