# 애플 폴더블 아이폰 시장 반응 모니터링

애플 첫 폴더블 아이폰(iPhone Fold / iPhone Ultra, 2026-09-09 발표)의 시장 반응과
삼성닷컴에 미칠 영향을 모니터링한다. 핸드오프 문서 `apple_foldable_monitoring_handoff.md` 기준.

## 구조

```
config/        keywords.yaml (§4) · prompts.yaml (§5) · settings.yaml (임계치/모델/로케일)
src/common/    config(로더) · storage(jsonl) · report(Excel 메일) · alerts(email/Slack)
src/collectors/
  trends.py        검색량 — pytrends, 실패 시 SerpApi google_trends 폴백 + rising queries
  serp.py          SERP 순위 + AI Overview/AI Mode — SerpApi
  llm_mentions.py  LLM 언급·감성 — 무료(Gemini)만. openai/anthropic은 유료라 비활성
  news.py          GDELT + Google Alerts RSS (2차)
src/run_frequent.py 매시간: trends + llm  (+임계치 알림)
src/run_daily.py    매시간: serp(예산 가드) + rising + news + Excel 리포트(하루 1회)
.github/workflows/  frequent.yml · heavy.yml — 둘 다 매시간 (cron 0 * * * *)
```

1차 우선순위: 검색량 · SERP · AI Overview · LLM 언급(Gemini)
2차: 뉴스 · 커뮤니티 · 자사 트래픽(GSC) · 가격 감시

## 로컬 실행

```bash
python -m venv .venv && .venv/Scripts/activate    # Windows
pip install -r requirements.txt
cp .env.example .env      # 키 채우기
python -m src.collectors.trends          # 개별 수집기 단독 실행
python -m src.run_daily                  # 전체 일간 파이프라인
```

키가 없어도 각 수집기는 해당 소스를 건너뛰고 나머지를 진행한다.
결과는 항상 `data/<dataset>.jsonl`. `GOOGLE_SHEETS_ID` + 서비스계정 JSON 설정 시
같은 이름의 워크시트에도 append 된다.

## GitHub Actions 배포

1. **레포를 public 으로 생성** (Actions 분(minutes) 무제한). 예:
   ```bash
   # GitHub에서 빈 public 레포 생성 후
   git remote add origin https://github.com/<계정>/apple-foldable-monitor.git
   git push -u origin main
   ```
   이미 private 으로 만들었다면: Settings → General → Danger Zone → Change visibility → Public
2. Settings → Secrets and variables → Actions 에 `.env.example` 의 키를 동일 이름으로 등록
3. Settings → Actions → General → Workflow permissions → **Read and write** (CI가 data/ 커밋)
4. 스케줄
   - `frequent.yml` 매시간: 검색량 + LLM 언급(Gemini)
   - `heavy.yml` 매시간: SERP + AI Overview + 뉴스. SerpApi는 `monthly_call_budget`(230)
     초과 시 자동 중단. Excel 리포트 메일은 `email_hour_utc`(17=KST 02:00) 실행에서만 1회
5. CI가 `data/*.jsonl` 을 레포에 커밋해 히스토리 축적

> LLM: 무료 Gemini만 사용. OpenAI·Anthropic은 유료라 제외(`config/settings.yaml` `llm.providers`).
> ChatGPT/Claude 응답 모니터링이 필요해지면 유료 키 발급 후 providers 에 추가.

## 데이터셋

| dataset | 주기 | 핵심 필드 |
|---|---|---|
| trends | 매시간 | keyword, country, value_last, wow_pct, source |
| trends_rising | 일 | seed, rising_query, value |
| serp | 일 | keyword, apple_rank, samsung_rank, ai_overview_present, ai_overview_mentions_* |
| llm_mentions | 매시간 | provider, prompt_id, lang, apple_first, samsung_sentiment |
| news_volume / news_articles | 일 | query, gdelt_volume_* / title, link |

리포트: daily 실행이 위 전체를 시트별로 나눈 `.xlsx` 를 `REPORT_EMAIL_TO` 로 발송.

## 미결 (핸드오프 §9) — 사용자 확인 필요

- ChatGPT/Claude 언급 모니터링: 무료 API 없음 → 현재 제외 (Gemini만)
- GA4 접근권한 (현재 GSC로 자사 트래픽 대체)
- 나머지 8개 법인 2차 추가 여부

## 보고 시 유의 (§6)

정성적 반응 지표(관심도 변화)와 정량적 전환 지표(매출/체류)를 구분해 명시.
GSC 단독으로는 관심도 변화만 확인 가능, 실제 전환은 GA4 필요.
