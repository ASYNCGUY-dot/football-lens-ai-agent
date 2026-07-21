# ⚽ Football Lens — VS Code 실행 가이드

> 작성일: 2026-06-23  
> 대상: VS Code 사용 초보 개발자  
> Python 3.10+ / Windows 기준

---

## 📁 프로젝트 폴더 구조

```
DONGA KDT AI AGENT 2nd PROJECT/
├── week1/                  ← 데이터 수집 파이프라인
│   ├── main.py             ← week1 실행 진입점
│   ├── collectors/         ← RSS, 네이버, football-data 수집기
│   ├── preprocessing/      ← 전처리 (중복 제거, 광고 필터)
│   ├── database/           ← PostgreSQL 스키마/저장
│   └── requirements.txt
├── week2/                  ← LangGraph AI 파이프라인
│   ├── graph.py            ← week2 실행 진입점
│   ├── nodes.py            ← 수집/전처리/분류/병합 노드
│   ├── llm_nodes.py        ← Claude/GPT/Gemini LLM 노드
│   ├── state.py            ← 공유 State 정의
│   └── requirements.txt
└── week3/                  ← RAG + 대시보드 + 이메일
    ├── dashboard/app.py    ← Streamlit 대시보드 (메인 UI)
    ├── rag/                ← ChromaDB + 임베딩
    ├── insight_node.py     ← 통합 인사이트 노드
    ├── mailer/             ← 이메일 발송 (SMTP)
    ├── tests/              ← 통합 테스트
    └── requirements.txt
```

---

## 🔧 STEP 0 — VS Code에서 폴더 열기

1. VS Code 실행
2. `파일` → `폴더 열기` → `DONGA KDT AI AGENT 2nd PROJECT` 폴더 선택
3. 상단 메뉴 `터미널` → `새 터미널` 클릭
   - 또는 단축키: **Ctrl + `** (백틱)
4. 터미널이 아래쪽에 열리면 준비 완료

---

## 🐍 STEP 1 — Python 가상환경 생성 (최초 1회만)

터미널에서 아래 명령어를 순서대로 입력합니다.

```bash
# 1. 프로젝트 루트 폴더 이동 확인
cd "DONGA KDT AI AGENT 2nd PROJECT"

# 2. 가상환경 생성
python -m venv venv

# 3. 가상환경 활성화 (Windows)
venv\Scripts\activate
```

> ✅ 활성화 성공 시 터미널 앞에 `(venv)` 표시됨  
> ❗ "이 시스템에서 스크립트 실행이 비활성화" 오류 시:
> ```
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> 입력 후 다시 활성화

---

## 📦 STEP 2 — 패키지 설치

```bash
# week1 패키지
pip install -r week1/requirements.txt

# week2 패키지 (week1 위에 추가 설치)
pip install -r week2/requirements.txt

# week3 패키지 (RAG + 대시보드 + 이메일)
pip install -r week3/requirements.txt
```

> ⏱️ 처음 설치 시 `sentence-transformers`가 AI 모델을 다운로드해서  
> **5~10분** 걸릴 수 있습니다. 기다리세요!

---

## 🔑 STEP 3 — API 키 설정 (.env 파일)

### week1 폴더에 `.env` 파일 생성

VS Code 왼쪽 파일 탐색기에서 `week1` 폴더 우클릭 → `새 파일` → `.env`

```env
# ── 네이버 뉴스 API (선택사항) ─────────────────────────────
# https://developers.naver.com 에서 발급
NAVER_CLIENT_ID=여기에_클라이언트_ID
NAVER_CLIENT_SECRET=여기에_클라이언트_시크릿

# ── football-data.org API (선택사항) ───────────────────────
# https://www.football-data.org/client/register 에서 발급 (무료)
FOOTBALL_DATA_API_KEY=여기에_API_키

# ── PostgreSQL DB (선택사항) ───────────────────────────────
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_lens
DB_USER=postgres
DB_PASSWORD=여기에_DB_비밀번호
```

### week2 폴더에 `.env` 파일 생성

```env
# ── Claude API (선택사항, 하나만 있어도 됨) ────────────────
ANTHROPIC_API_KEY=여기에_Anthropic_키

# ── OpenAI API (선택사항) ──────────────────────────────────
OPENAI_API_KEY=여기에_OpenAI_키

# ── Google Gemini API (선택사항) ───────────────────────────
GOOGLE_API_KEY=여기에_Google_키
```

### week3 폴더에 `.env` 파일 생성

```env
# ── ChromaDB 저장 위치 ─────────────────────────────────────
CHROMA_PERSIST_DIR=./chroma_db

# ── 임베딩 모델 ────────────────────────────────────────────
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ── 이메일 SMTP 설정 (선택사항) ────────────────────────────
# Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_SSL=false
SMTP_USER=여기에_Gmail_주소
SMTP_PASSWORD=여기에_앱_비밀번호

# 네이버 메일 사용 시 아래로 변경:
# SMTP_HOST=smtp.naver.com
# SMTP_PORT=587
# SMTP_USE_SSL=false

EMAIL_RECIPIENTS=받는사람@email.com
EMAIL_SENDER_NAME=Football Lens
```

> 💡 **API 키 없어도 실행 가능!**  
> 모든 LLM 노드는 API 키가 없으면 자동으로 **목업(더미) 데이터**로 동작합니다.  
> 개발/테스트 시에는 키 없이 먼저 실행해보세요.

---

## ▶️ STEP 4 — Week1 실행 (데이터 수집)

### 4-1. DB 없이 수집만 테스트 (추천 — 첫 실행 시)

```bash
cd week1
python main.py --no-db
```

출력 예시:
```
2026-06-23 10:00:01 [INFO] main - === RSS 수집 시작 ===
2026-06-23 10:00:03 [INFO] main - RSS 완료: 수집 15건 → 저장 0건
2026-06-23 10:00:03 [INFO] main - === 네이버 뉴스 수집 시작 ===
2026-06-23 10:00:03 [WARNING] main - 네이버 API 키 없음, 건너뜁니다
2026-06-23 10:00:03 [INFO] main - === EPL 데이터 수집 시작 ===
2026-06-23 10:00:03 [WARNING] main - football-data API 키 없음, 건너뜁니다
2026-06-23 10:00:03 [INFO] main - === 전체 파이프라인 완료 (2.1초) ===
```

### 4-2. RSS만 수집

```bash
python main.py --step rss --no-db
```

### 4-3. 전체 실행 (DB 포함, PostgreSQL 필요)

```bash
python main.py
```

### 4-4. 각 수집기 단독 테스트

```bash
# RSS 수집기 직접 실행
python collectors/rss_collector.py

# 전처리기 직접 실행
python preprocessing/preprocessor.py

# DB 스키마 확인
python database/schema.py
```

---

## ▶️ STEP 5 — Week2 실행 (LangGraph AI 파이프라인)

```bash
# week2 폴더로 이동
cd ../week2
# (이미 week2에 있다면 cd week2)

# 전체 파이프라인 실행
python graph.py
```

출력 예시:
```
============================================================
⚽ Football Lens 파이프라인 시작
   run_id: run_20260623_100001
   config: {'days_back': 3, 'max_articles_per_source': 10}
============================================================

  ✓ collect 완료
  ✓ preprocess 완료
  ✓ classify 완료
  ✓ summarize_korean 완료
  ✓ summarize_english 완료
  ✓ analyze_match 완료
  ✓ merge 완료

============================================================
파이프라인 완료!
============================================================

=== 최종 리포트 미리보기 (처음 500자) ===
# ⚽ Football Lens 일간 보고서
...
```

### 그래프 구조 시각화

```bash
python graph.py --viz
```

출력된 Mermaid 코드를 복사 후 [mermaid.live](https://mermaid.live) 에 붙여넣으면 노드 다이어그램을 볼 수 있습니다.

### 개별 노드 테스트

```bash
# LLM 노드 단독 테스트
python llm_nodes.py

# State 구조 확인
python state.py
```

---

## ▶️ STEP 6 — Week3 실행 (대시보드 + RAG + 이메일)

### 6-1. Streamlit 대시보드 실행 ⭐ (메인)

```bash
# week3 폴더로 이동
cd ../week3

# 대시보드 실행
streamlit run dashboard/app.py
```

> 브라우저에 `http://localhost:8501` 이 자동으로 열립니다.  
> 안 열리면 직접 주소창에 입력하세요.

**대시보드 사용법:**
1. 왼쪽 사이드바에서 리그 선택 (기본: EPL)
2. 수집 기간 슬라이더 조정 (기본: 7일)
3. **🚀 분석 실행** 버튼 클릭
4. 탭별 결과 확인:
   - `📰 일간 보고서` — 오늘의 뉴스 요약
   - `📊 주간 보고서` — 주간 트렌드
   - `🏆 EPL 순위` — 팀 순위표
   - `🔍 RAG 검색` — 키워드로 기사 검색
   - `📧 이메일 발송` — 보고서 이메일 발송

### 6-2. RAG 임베더 단독 테스트

```bash
cd week3
python rag/embedder.py
```

### 6-3. 인사이트 노드 단독 테스트

```bash
python insight_node.py
```

### 6-4. 통합 테스트 실행

```bash
# pytest 방식
python -m pytest tests/test_integration.py -v

# 또는 직접 실행
python tests/test_integration.py
```

---

## 🚨 자주 발생하는 오류 해결

### ❌ `ModuleNotFoundError: No module named 'XXX'`
```bash
# 가상환경 활성화 확인
venv\Scripts\activate

# 패키지 재설치
pip install -r week3/requirements.txt
```

### ❌ `chromadb 미설치`
```bash
pip install chromadb==0.5.3
```

### ❌ `sentence-transformers 미설치`
```bash
pip install sentence-transformers==3.0.1
```

### ❌ `streamlit: command not found`
```bash
pip install streamlit==1.37.0
```

### ❌ VS Code 터미널에서 `python`이 아닌 `python3`로 실행됨
VS Code 우하단 Python 버전 클릭 → `venv` 선택

### ❌ `psycopg2` 오류 (PostgreSQL 없는 환경)
DB 없이 실행 가능합니다:
```bash
# week1
python main.py --no-db

# week2/week3는 DB 연결 실패 시 자동으로 무시하고 계속 실행됨
```

### ❌ `.env` 파일이 인식 안 됨
```bash
# .env 파일이 각 주차 폴더 안에 있는지 확인
# week1/.env, week2/.env, week3/.env 각각 존재해야 함
```

---

## 📋 전체 실행 순서 요약

```
① VS Code에서 폴더 열기
② 터미널 열기 (Ctrl + `)
③ 가상환경 생성 및 활성화
④ 패키지 설치 (week1 → week2 → week3 순서)
⑤ .env 파일 생성 (각 주차 폴더)
⑥ week1 테스트: cd week1 && python main.py --no-db
⑦ week2 테스트: cd ../week2 && python graph.py
⑧ week3 대시보드: cd ../week3 && streamlit run dashboard/app.py
```

---

## 💡 VS Code 유용한 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl + `` ` | 터미널 열기/닫기 |
| `Ctrl + Shift + P` | 명령 팔레트 |
| `F5` | 현재 파일 디버그 실행 |
| `Ctrl + F5` | 현재 파일 실행 (디버그 없이) |
| `Ctrl + Shift + E` | 파일 탐색기 열기 |
| `Ctrl + \`` | 터미널 새로 분할 |

---

*Football Lens Project — AI Agent 2nd 과정*
