# 애플 폴더블 아이폰 시장 반응 모니터링

애플 첫 폴더블 아이폰(iPhone Fold / iPhone Ultra, 2026-09-09 발표)의 시장 반응과
삼성닷컴에 미칠 영향을 모니터링한다. 핸드오프 문서 `apple_foldable_monitoring_handoff.md` 기준.

## 구조

```
config/        keywords.yaml (§4) · prompts.yaml (§5) · settings.yaml (임계치/모델/로케일)
src/common/    config(로더) · storage(jsonl+Sheets) · alerts(Slack)
src/collectors/
  trends.py        검색량 — pytrends, 실패 시 SerpApi google_trends 폴백 + rising queries
  serp.py          SERP 순위 + AI Overview/AI Mode — SerpApi
  llm_mentions.py  Gemini/OpenAI/Anthropic 3사 동일 프롬프트 언급·감성 집계
  news.py          GDELT + Google Alerts RSS (2차)
src/run_daily.py   1차: trends + serp + llm  (+임계치 알림)
src/run_weekly.py  rising queries 확장 + news
.github/workflows/ daily.yml (01:00 UTC) · weekly.yml (월 02:00 UTC)
```

1차 우선순위: 검색량 · SERP · AI Overview · LLM 3사
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

레포 Settings → Secrets 에 `.env.example` 의 키를 동일 이름으로 등록.
워크플로는 `data/` 를 아티팩트로 업로드한다. (Sheets 미사용 시 이력 확인용)

## 데이터셋

| dataset | 주기 | 핵심 필드 |
|---|---|---|
| trends | 일 | keyword, country, value_last, wow_pct, source |
| trends_rising | 주 | seed, rising_query, value |
| serp | 일 | keyword, apple_rank, samsung_rank, ai_overview_present, ai_overview_mentions_* |
| llm_mentions | 일 | provider, prompt_id, lang, apple_first, samsung_sentiment |
| news_volume / news_articles | 주 | query, gdelt_volume_* / title, link |

## 미결 (핸드오프 §9) — 사용자 확인 필요

- Anthropic API 키 신규 발급 여부
- 저장소: Google Sheets vs BigQuery
- 알림 채널: Slack vs 이메일
- GA4 접근권한 (현재 GSC로 자사 트래픽 대체)
- 나머지 8개 법인 2차 추가 여부

## 보고 시 유의 (§6)

정성적 반응 지표(관심도 변화)와 정량적 전환 지표(매출/체류)를 구분해 명시.
GSC 단독으로는 관심도 변화만 확인 가능, 실제 전환은 GA4 필요.
