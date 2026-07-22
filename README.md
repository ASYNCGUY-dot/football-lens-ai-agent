# ⚽ Football Lens AI Agent
- DONGA KDT AI AGENT 2nd persnal project

> 축구 뉴스 자동 수집 · AI 분석 · 경기 예측 대시보드

LangGraph 기반 멀티 에이전트 파이프라인으로 국내외 축구 뉴스를 수집하고,  
Claude · GPT · Gemini를 활용해 일간 리포트와 경기 예측을 자동 생성합니다.

---

## 주요 기능

- **뉴스 자동 수집** — 네이버 뉴스, RSS, Reddit, YouTube, football-data.org
- **AI 요약 · 분석** — 한국어(Claude), 영어(GPT-4o-mini), 경기 데이터(Gemini)
- **감정 분석 · 이적 루머 탐지** — 기사별 긍/부정 점수 및 이적 루머 자동 분류
- **경기 예측** — 순위표 + 뉴스 감정 기반 다음 경기 승패 예측
- **RAG 검색** — ChromaDB 벡터 검색으로 관련 과거 기사 연동
- **Streamlit 대시보드** — 일간 보고서, 경기 예측, 감정 분석, RAG 검색 탭 제공
- **리그 지원** — EPL, 2026 FIFA 월드컵, K리그1, 라리가, 분데스리가, 세리에A, 리그앙

---

## 프로젝트 구조

```
football-lens-ai-agent/
├── week1/                        # 데이터 수집 레이어
│   ├── collectors/
│   │   ├── naver_collector.py    # 네이버 뉴스 API
│   │   ├── rss_collector.py      # BBC, Guardian 등 RSS
│   │   ├── reddit_collector.py   # Reddit r/soccer
│   │   ├── youtube_collector.py  # YouTube 하이라이트
│   │   └── football_data_collector.py  # football-data.org API
│   ├── preprocessing/
│   │   └── preprocessor.py       # 중복 제거, 광고 필터
│   └── main.py
│
├── week2/                        # LangGraph 파이프라인
│   ├── state.py                  # FootballNewsState 정의
│   ├── nodes.py                  # collect / preprocess / classify / merge
│   ├── llm_nodes.py              # LLM 노드 (요약 · 분석 · 예측)
│   └── graph.py                  # StateGraph 빌드 및 조건부 라우팅
│
├── week3/                        # 대시보드 레이어
│   ├── dashboard/
│   │   └── app.py                # Streamlit 앱
│   ├── rag/
│   │   ├── embedder.py           # ChromaDB 임베딩
│   │   └── rag_node.py           # RAG 검색 노드
│   ├── insight_node.py           # 통합 인사이트 생성
│   └── mailer/
│       └── email_sender.py       # 리포트 이메일 발송
│
└── .env.example                  # API 키 설정 예시
```

---

## 파이프라인 구조

```
START
  │
  ▼
collect_node          ← 뉴스 + 경기 데이터 수집
  │
  ▼
preprocess_node       ← 전처리 (중복 제거, 언어 감지)
  │
  ▼
classify_node         ← 라우팅 플래그 설정
  │
  ├──► summarize_korean_node    (Claude)
  ├──► summarize_english_node   (GPT-4o-mini)
  ├──► analyze_match_node       (Gemini)
  └──► sentiment_analysis_node  → match_prediction_node
                │
                ▼
            merge_node
                │
               END
```

---

## 설치 및 실행

### 1. 환경 설정

```bash
git clone https://github.com/ASYNCGUY-dot/football-lens-ai-agent.git
cd football-lens-ai-agent

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r week3/requirements.txt
```

### 2. API 키 설정

프로젝트 루트에 `.env` 파일 생성:

```env
# LLM API (최소 하나 이상 필요)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# 뉴스 수집
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
FOOTBALL_DATA_API_KEY=...   # football-data.org (무료 플랜 가능)

# 선택사항
YOUTUBE_API_KEY=...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
```

### 3. 대시보드 실행

```bash
cd week3/dashboard
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 사용 방법

1. 사이드바에서 **리그** 선택 (EPL, 월드컵, K리그1 등)
2. **⚡ 분석 실행** 버튼 클릭
3. 탭별 결과 확인:
   - **일간 보고서** — 뉴스 요약 + 경기 분석
   - **경기 예측** — 다음 경기 AI 예측
   - **감정 분석** — 기사별 감정 점수 + 이적 루머
   - **RAG 검색** — 키워드로 관련 기사 검색

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| AI 파이프라인 | LangGraph, LangChain |
| LLM | Anthropic Claude, OpenAI GPT-4o-mini, Google Gemini |
| 벡터 DB | ChromaDB |
| 대시보드 | Streamlit |
| 데이터 수집 | football-data.org, Naver API, RSS, Reddit API, YouTube API |
| 언어 | Python 3.10+ |

---

## 주의사항

- `football-data.org` 무료 플랜은 월드컵(WC) 엔드포인트를 지원하지 않습니다. 월드컵 분석은 뉴스 기사 기반으로 동작합니다.
- `.env` 파일은 절대 커밋하지 마세요. `.gitignore`에 포함되어 있습니다.
- 분석 실행 후 파이프라인 코드 수정 시 Streamlit을 재시작해야 변경사항이 반영됩니다.

---

## License

MIT
