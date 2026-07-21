markdown
# ⚽ Football Lens AI Agent

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

football-lens-ai-agent/
├── week1/ # 데이터 수집 레이어
│ ├── collectors/
│ │ ├── naver_collector.py # 네이버 뉴스 API
│ │ ├── rss_collector.py # BBC, Guardian 등 RSS
│ │ ├── reddit_collector.py # Reddit r/soccer
│ │ ├── youtube_collector.py # YouTube 하이라이트
│ │ └── football_data_collector.py # football-data.org API
│ ├── preprocessing/
│ │ └── preprocessor.py # 중복 제거, 광고 필터
│ └── main.py
│
├── week2/ # LangGraph 파이프라인
│ ├── state.py # FootballNewsState 정의
│ ├── nodes.py # collect / preprocess / classify / merge
│ ├── llm_nodes.py # LLM 노드 (요약 · 분석 · 예측)
│ └── graph.py # StateGraph 빌드 및 조건부 라우팅
│
└── week3/ # 대시보드 레이어
├── dashboard/app.py # Streamlit 앱
├── rag/ # ChromaDB RAG 검색
├── insight_node.py # 통합 인사이트 생성
└── mailer/ # 리포트 이메일 발송


---

## 파이프라인 구조

START → collect → preprocess → classify
│
┌───────────────────────┼───────────────────────┐
▼ ▼ ▼
summarize_korean(Claude) summarize_english(GPT) analyze_match(Gemini)
│ │ │
└───────────────────────┴───────────────────────┘
│
sentiment_analysis
│
match_prediction
│
merge → END


---

## 설치 및 실행

```bash
git clone https://github.com/ASYNCGUY-dot/football-lens-ai-agent.git
cd football-lens-ai-agent

python -m venv venv
venv\Scripts\activate

pip install -r week3/requirements.txt
```

`.env` 파일 생성:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
FOOTBALL_DATA_API_KEY=...
```

대시보드 실행:

```bash
cd week3/dashboard
streamlit run app.py
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| AI 파이프라인 | LangGraph, LangChain |
| LLM | Claude / GPT-4o-mini / Gemini |
| 벡터 DB | ChromaDB |
| 대시보드 | Streamlit |
| 데이터 수집 | football-data.org, Naver API, RSS, Reddit, YouTube |
| 언어 | Python 3.10+ |

---

## License

MIT
