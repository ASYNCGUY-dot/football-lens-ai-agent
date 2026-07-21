"""
app.py
======
Football Lens Streamlit 대시보드 (v3 — ESPN 테마)

실행 방법:
    cd week3
    streamlit run dashboard/app.py

디자인 레퍼런스:
    ESPN.com — 빨강(#CC0000) + 다크(#1A1A1A) + 화이트
    폰트: Oswald (헤드라인) + Source Sans 3 (본문)
    이미지: Unsplash 스타디움/축구 사진

주의:
    _html() 헬퍼가 textwrap.dedent()로 들여쓰기를 제거합니다.
    → Markdown 4칸-들여쓰기 코드블록 오인 방지
"""

import sys
import os
import time
import queue
import base64
import threading
import textwrap
import logging
from datetime import datetime

# ── 경로 설정 ────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
WEEK1_PATH = os.path.join(ROOT, "week1")
WEEK2_PATH = os.path.join(ROOT, "week2")
WEEK3_PATH = os.path.join(ROOT, "week3")

for p in [ROOT, WEEK1_PATH, WEEK2_PATH, WEEK3_PATH]:
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, "week3", ".env"))
load_dotenv(os.path.join(ROOT, "week2", ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Football Lens",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 이미지 URL 상수 ───────────────────────────────────────────
IMG_STADIUM   = "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?auto=format&fit=crop&w=1400&q=80"
IMG_BALL      = "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&w=400&q=80"
IMG_MATCH     = "https://images.unsplash.com/photo-1553778263-73a83bab9b0c?auto=format&fit=crop&w=800&q=80"
IMG_CROWD     = "https://images.unsplash.com/photo-1562552476-8ac59b2a2e46?auto=format&fit=crop&w=800&q=80"
# ── Football Lens 커스텀 SVG 로고 (저작권 없는 독자 디자인) ──────────────
# 축구공(오각형 패턴) + 렌즈 링 조합 — 흰색 버전 (사이드바·히어로 공용)
_FL_LOGO_SVG_WHITE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
  <circle cx="30" cy="30" r="27" fill="none" stroke="white" stroke-width="2.5"/>
  <circle cx="30" cy="27" r="12.5" fill="none" stroke="white" stroke-width="1.8"/>
  <polygon points="30,20 36.3,24.2 33.8,31.4 26.2,31.4 23.7,24.2" fill="white"/>
  <line x1="30" y1="14.5" x2="30" y2="20" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="41.8" y1="22.3" x2="36.3" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="38.2" y1="37.2" x2="33.8" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="21.8" y1="37.2" x2="26.2" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="18.2" y1="22.3" x2="23.7" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <text x="30" y="53" font-family="Arial,sans-serif" font-size="6.2" font-weight="900"
        text-anchor="middle" fill="white" letter-spacing="2.5">LENS</text>
</svg>"""

# 컬러 버전 (어두운 배경용 — 빨강 링 + 흰 볼)
_FL_LOGO_SVG_COLOR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
  <circle cx="30" cy="30" r="27" fill="none" stroke="#CC0000" stroke-width="3"/>
  <circle cx="30" cy="30" r="23" fill="#CC0000"/>
  <circle cx="30" cy="27" r="12.5" fill="none" stroke="white" stroke-width="1.8"/>
  <polygon points="30,20 36.3,24.2 33.8,31.4 26.2,31.4 23.7,24.2" fill="white"/>
  <line x1="30" y1="14.5" x2="30" y2="20" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="41.8" y1="22.3" x2="36.3" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="38.2" y1="37.2" x2="33.8" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="21.8" y1="37.2" x2="26.2" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="18.2" y1="22.3" x2="23.7" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <text x="30" y="53" font-family="Arial,sans-serif" font-size="6.2" font-weight="900"
        text-anchor="middle" fill="white" letter-spacing="2.5">LENS</text>
</svg>"""

# data URI 변환 (img src 속성에 직접 사용 가능)
LOGO_WHITE = "data:image/svg+xml;base64," + base64.b64encode(_FL_LOGO_SVG_WHITE.encode()).decode()
LOGO_COLOR = "data:image/svg+xml;base64," + base64.b64encode(_FL_LOGO_SVG_COLOR.encode()).decode()

IMG_EPL       = LOGO_WHITE   # 하위 호환 — 기존 IMG_EPL 참조 코드도 자동 대체
IMG_TROPHY    = "https://images.unsplash.com/photo-1594736797933-d0501ba2fe65?auto=format&fit=crop&w=400&q=80"
IMG_TRAINING  = "https://images.unsplash.com/photo-1526232761682-d26e03ac148e?auto=format&fit=crop&w=800&q=80"

# ── 추가 축구 사진 ────────────────────────────────────────────
IMG_KICK       = "https://images.unsplash.com/photo-1543326727-cf6c39e8f84c?auto=format&fit=crop&w=800&q=80"
IMG_GOALKEEPER = "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?auto=format&fit=crop&w=800&q=80"
IMG_CELEBRATE  = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=800&q=80"
IMG_STADIUM2   = "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=800&q=80"
IMG_BOOTS      = "https://images.unsplash.com/photo-1560272564-c83b66b1ad12?auto=format&fit=crop&w=800&q=80"
IMG_AERIAL     = "https://images.unsplash.com/photo-1587329310686-91414b8e3cb7?auto=format&fit=crop&w=800&q=80"

# 포토 스트립 (이모지 라벨 + URL + 배지 색상)
PHOTO_STRIP = [
    ("⚽ 경기 액션",    IMG_MATCH,      "#CC0000"),
    ("🏟️ 스타디움",    IMG_STADIUM2,   "#1A1A1A"),
    ("🧤 골키퍼",      IMG_GOALKEEPER, "#003399"),
    ("🎉 골 세리머니",  IMG_CELEBRATE,  "#CC0000"),
    ("🏆 트로피",      IMG_TROPHY,     "#E65C00"),
    ("🦵 훈련",        IMG_TRAINING,   "#2E7D32"),
    ("👟 클리트",      IMG_BOOTS,      "#555555"),
    ("🎟️ 관중석",     IMG_CROWD,      "#1A1A1A"),
]


# =============================================
# HTML 헬퍼
# =============================================

def _html(markup: str) -> None:
    """
    들여쓰기를 제거하고 HTML을 렌더링합니다.
    CommonMark의 4칸-들여쓰기 코드블록 오인을 방지합니다.
    """
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


# =============================================
# ESPN CSS
# =============================================

def inject_custom_css():
    """ESPN 스타일 전역 CSS를 삽입합니다."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');

/* ── Streamlit 기본 UI 숨김 ── */
header[data-testid="stHeader"] { display:none !important; }
#MainMenu { visibility:hidden !important; display:none !important; }
.stDeployButton { display:none !important; }
[data-testid="stToolbar"] { display:none !important; }
footer { display:none !important; }

/* ── 전역 ── */
html, body, .stApp {
    font-family: 'Source Sans 3', -apple-system, sans-serif !important;
    background-color: #F0F2F4 !important;
}
.main .block-container { padding-top: 0 !important; padding-bottom: 3rem; max-width: 1300px; }

/* ── 텍스트 ── */
p, li, .stMarkdown { color: #1A1A1A !important; line-height: 1.65; }
h1 { font-family:'Oswald',sans-serif !important; color:#1A1A1A !important; font-weight:700 !important; text-transform:uppercase !important; letter-spacing:0.5px !important; }
h2 { font-family:'Oswald',sans-serif !important; color:#1A1A1A !important; font-weight:600 !important; text-transform:uppercase !important; }
h3 { font-family:'Oswald',sans-serif !important; color:#CC0000 !important; font-weight:600 !important; text-transform:uppercase !important; }
.stCaption, small { color:#888 !important; }

/* ── 사이드바 ── */
section[data-testid="stSidebar"] { background-color:#FFFFFF !important; border-right:3px solid #CC0000 !important; }
section[data-testid="stSidebar"] * { color:#333333 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color:#1A1A1A !important; }

/* ── 탭 ── */
.stTabs {
    position: relative;
    z-index: 10;
}
.stTabs [data-baseweb="tab-list"] {
    background-color:#FFFFFF; gap:0; border-radius:0;
    border-bottom:3px solid #E8E8E8; box-shadow:0 2px 6px rgba(0,0,0,0.05);
    position: relative; z-index: 10;
    pointer-events: auto !important;
    overflow-x: auto !important;   /* 탭 많아도 가로 스크롤 */
    overflow-y: visible !important;
    flex-wrap: nowrap !important;
    scrollbar-width: thin;
    scrollbar-color: #CC0000 #F0F0F0;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { height: 3px; }
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb { background: #CC0000; border-radius: 2px; }
.stTabs [data-baseweb="tab"] {
    background-color:transparent; color:#777777 !important;
    font-family:'Oswald',sans-serif !important; font-weight:600;
    font-size:11px; text-transform:uppercase; letter-spacing:0.3px;
    padding:10px 14px; border-radius:0; border-bottom:3px solid transparent;
    margin-bottom:-3px; white-space: nowrap; flex-shrink: 0;
    cursor: pointer !important;
    pointer-events: auto !important;
}
.stTabs [data-baseweb="tab"]:hover { color:#CC0000 !important; }
.stTabs [aria-selected="true"] {
    background-color:transparent !important; color:#CC0000 !important;
    font-weight:700 !important; border-bottom:3px solid #CC0000 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display:none !important; pointer-events:none !important; }
.stTabs [data-baseweb="tab-border"] { display:none !important; pointer-events:none !important; }
.stTabs [data-baseweb="tab-panel"] { pointer-events: auto !important; }

/* ── 버튼 ── */
.stButton > button {
    border-radius:3px !important; font-family:'Oswald',sans-serif !important;
    font-weight:600 !important; text-transform:uppercase !important; letter-spacing:0.5px !important;
    transition:all 0.15s !important;
}
.stButton > button[kind="primary"] {
    background:#CC0000 !important; color:#FFFFFF !important; border:none !important;
}
.stButton > button[kind="primary"]:hover { background:#AA0000 !important; }
/* 일반(secondary) 버튼 — 전체 */
[data-testid="baseButton-secondary"],
.stButton button[kind="secondary"],
.stButton button:not([kind="primary"]) {
    background:#FFFFFF !important; color:#1A1A1A !important;
    border:2px solid #CCCCCC !important;
}
[data-testid="baseButton-secondary"]:hover,
.stButton button[kind="secondary"]:hover,
.stButton button:not([kind="primary"]):hover {
    border-color:#CC0000 !important; color:#CC0000 !important; background:#FFF5F5 !important;
}
/* 사이드바 secondary 버튼 — 밝은 회색 */
[data-testid="stSidebar"] [data-testid="baseButton-secondary"],
[data-testid="stSidebar"] .stButton button[kind="secondary"],
[data-testid="stSidebar"] .stButton button:not([kind="primary"]) {
    background:#F5F5F5 !important; color:#444444 !important;
    border:1px solid #DDDDDD !important; font-size:13px !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover,
[data-testid="stSidebar"] .stButton button:not([kind="primary"]):hover {
    background:#FFE8E8 !important; border-color:#CC0000 !important; color:#CC0000 !important;
}
[data-testid="stDownloadButton"] button {
    background:#FFFFFF !important; color:#CC0000 !important;
    border:2px solid #CC0000 !important; border-radius:3px !important;
    font-family:'Oswald',sans-serif !important; font-weight:600 !important; text-transform:uppercase !important;
}

/* ── 메트릭 ── */
[data-testid="stMetric"] {
    background:#FFFFFF !important; border-radius:4px !important;
    padding:14px 16px !important; border-top:3px solid #CC0000 !important;
    box-shadow:0 1px 4px rgba(0,0,0,0.08) !important;
}
[data-testid="stMetricValue"] { color:#1A1A1A !important; font-family:'Oswald',sans-serif !important; font-size:2rem !important; font-weight:700 !important; }
[data-testid="stMetricLabel"] { color:#888888 !important; font-size:0.7rem !important; text-transform:uppercase !important; letter-spacing:1px !important; }
[data-testid="stMetricDelta"] { color:#2E7D32 !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background:#FFFFFF !important; border:1px solid #E5E5E5 !important;
    border-left:4px solid #CC0000 !important; border-radius:0 4px 4px 0 !important;
    box-shadow:0 1px 4px rgba(0,0,0,0.06) !important;
}
[data-testid="stExpander"] summary { color:#1A1A1A !important; font-family:'Oswald',sans-serif !important; font-weight:600 !important; text-transform:uppercase !important; letter-spacing:0.3px; }
[data-testid="stExpander"] summary:hover { color:#CC0000 !important; }

/* ── 입력창 ── */
.stTextInput input, .stTextArea textarea {
    background:#FFFFFF !important; border:2px solid #DDDDDD !important;
    color:#1A1A1A !important; border-radius:3px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color:#CC0000 !important; box-shadow:none !important; }

/* ── 셀렉트박스 ── */
.stSelectbox > div > div { background:#FFFFFF !important; border:1.5px solid #DDDDDD !important; color:#1A1A1A !important; border-radius:4px !important; }
.stSelectbox > div > div:focus-within { border-color:#CC0000 !important; }
/* 드롭다운 팝업 패널 */
[data-baseweb="popover"] { background:#FFFFFF !important; box-shadow:0 4px 16px rgba(0,0,0,0.15) !important; }
[data-baseweb="popover"] * { background:#FFFFFF !important; color:#1A1A1A !important; }
[data-baseweb="menu"] { background:#FFFFFF !important; }
[role="option"] { background:#FFFFFF !important; color:#1A1A1A !important; padding:10px 14px !important; }
[role="option"]:hover { background:#FFF0F0 !important; color:#CC0000 !important; }
[aria-selected="true"][role="option"] { background:#FFEAEA !important; color:#CC0000 !important; font-weight:700 !important; }
li[role="option"] { background:#FFFFFF !important; color:#1A1A1A !important; }
li[role="option"]:hover { background:#FFF0F0 !important; color:#CC0000 !important; }

/* ── 라디오 ── */
.stRadio label { color:#333333 !important; font-size:13px !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color:#333333 !important; }

/* ── 데이터프레임 ── */
[data-testid="stDataFrame"] { border-radius:0 !important; border:1px solid #E5E5E5 !important; }

/* ── 구분선 ── */
hr { border-color:#E0E0E0 !important; }

/* ── 알림 ── */
[data-testid="stAlertContainer"] { border-radius:3px !important; }
.stSuccess { background:rgba(76,175,80,0.1) !important; border-color:#4CAF50 !important; color:#2E7D32 !important; }
.stWarning { background:rgba(255,152,0,0.1) !important; }
.stError { background:rgba(204,0,0,0.08) !important; border-color:#CC0000 !important; }
.stSpinner > div { border-top-color:#CC0000 !important; }

/* ── 스크롤바 ── */
::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-track { background:#F0F0F0; }
::-webkit-scrollbar-thumb { background:#CC0000; border-radius:0; }

/* ── ESPN 뉴스 카드 ── */
.espn-card {
    background:#FFFFFF; border-left:4px solid #CC0000;
    border-radius:0 4px 4px 0; padding:14px 16px; margin-bottom:8px;
    border-bottom:1px solid #F0F0F0; box-shadow:0 1px 3px rgba(0,0,0,0.06);
    transition:box-shadow 0.15s, border-left-color 0.15s;
}
.espn-card:hover { box-shadow:0 3px 10px rgba(0,0,0,0.12); border-left-color:#AA0000; }
.espn-card-tag { font-family:'Oswald',sans-serif; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:#CC0000; margin-bottom:4px; }
.espn-card-title { font-family:'Oswald',sans-serif; font-size:15px; font-weight:600; color:#1A1A1A; line-height:1.35; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; margin-bottom:6px; text-decoration:none; }
a.espn-card-title:hover { color:#CC0000 !important; text-decoration:none; }
.espn-card-summary { font-size:13px; color:#555; line-height:1.5; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; margin-bottom:8px; }
.espn-card-meta { display:flex; gap:8px; align-items:center; flex-wrap:wrap; font-size:11px; color:#888; }

/* ── ESPN 배지 ── */
.ebadge { display:inline-block; padding:2px 7px; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.3px; border-radius:2px; }
.eb-red  { background:#CC0000; color:#FFF; }
.eb-dark { background:#1A1A1A; color:#FFF; }
.eb-blue { background:#003399; color:#FFF; }
.eb-green{ background:#2E7D32; color:#FFF; }
.eb-gray { background:#555; color:#FFF; }
.eb-gold { background:#FF6B00; color:#FFF; }

/* ── ESPN 섹션 헤더 ── */
.espn-sh { display:flex; align-items:center; gap:10px; margin:20px 0 12px; padding-bottom:8px; border-bottom:3px solid #CC0000; }
.espn-sh-title { font-family:'Oswald',sans-serif; font-size:18px; font-weight:700; color:#1A1A1A; text-transform:uppercase; letter-spacing:0.5px; }
.espn-sh-count { background:#CC0000; color:#FFF; padding:2px 8px; border-radius:2px; font-size:11px; font-weight:700; font-family:'Oswald',sans-serif; }

/* ── 티커 애니메이션 ── */
@keyframes espn-scroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* ── RAG 유사도 바 ── */
.sim-bar-bg { height:3px; background:#E5E5E5; border-radius:0; margin-top:6px; }
.sim-bar-fill { height:100%; background:#CC0000; border-radius:0; }
</style>
""", unsafe_allow_html=True)




# =============================================
# ESPN 티커 (속보 스크롤)
# =============================================

def render_ticker(articles: list = None):
    """
    ESPN 스타일 속보 뉴스 티커를 렌더링합니다.

    Parameters
    ----------
    articles : list, optional
        기사 목록. 없으면 기본 더미 텍스트를 표시합니다.
    """
    if articles:
        items = " &nbsp;•&nbsp; ".join(
            f"⚽ {a.get('title','')[:60]}" for a in articles[:8]
        )
        # 무한 루프를 위해 두 번 반복
        ticker_text = items + " &nbsp;&nbsp;&nbsp; " + items
    else:
        ticker_text = (
            "⚽ Football Lens — AI 기반 축구 뉴스 분석 대시보드 &nbsp;•&nbsp; "
            "🏆 EPL · K리그1 · 라리가 · 분데스리가 &nbsp;•&nbsp; "
            "🤖 Claude + GPT-4o-mini + Gemini 멀티 LLM &nbsp;•&nbsp; "
            "🔍 ChromaDB RAG 벡터 검색 &nbsp;•&nbsp; "
            "📊 LangGraph 파이프라인 &nbsp;•&nbsp; "
            "⚽ Football Lens — AI 기반 축구 뉴스 분석 대시보드 &nbsp;•&nbsp; "
            "🏆 EPL · K리그1 · 라리가 · 분데스리가 &nbsp;•&nbsp; "
            "🤖 Claude + GPT-4o-mini + Gemini 멀티 LLM &nbsp;•&nbsp; "
            "🔍 ChromaDB RAG 벡터 검색 &nbsp;•&nbsp; "
            "📊 LangGraph 파이프라인"
        )

    _html(f"""
<div style="background:#CC0000;overflow:hidden;white-space:nowrap;padding:7px 0;margin-bottom:0;border-bottom:2px solid #AA0000;">
<div style="display:inline-flex;align-items:center;">
<span style="background:rgba(255,255,255,0.2);color:#FFFFFF;font-family:'Oswald',sans-serif;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:0 14px;margin-right:16px;white-space:nowrap;border-right:1px solid rgba(255,255,255,0.3);">⚡ LIVE</span>
<span style="display:inline-block;animation:espn-scroll 30s linear infinite;font-size:12px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:500;letter-spacing:0.3px;">
{ticker_text}
</span>
</div>
</div>
""")


# =============================================
# ESPN 히어로 헤더
# =============================================

def render_hero():
    """
    스타디움 배경 이미지 위에 ESPN 스타일 히어로 배너를 렌더링합니다.
    Unsplash 스타디움 사진 + 빨간 그라데이션 오버레이
    """
    _html(f"""
<div style="position:relative;background:url('{IMG_STADIUM}') center/cover no-repeat;min-height:220px;margin:0 0 0 0;overflow:hidden;">
<div style="position:absolute;inset:0;background:linear-gradient(100deg,rgba(204,0,0,0.92) 0%,rgba(26,26,26,0.88) 60%,rgba(0,0,0,0.6) 100%);"></div>
<div style="position:relative;padding:32px 40px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:20px;">
<div>
<div style="font-family:'Oswald',sans-serif;font-size:11px;font-weight:700;color:#FF9999;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">AI FOOTBALL NEWS DASHBOARD</div>
<div style="font-family:'Oswald',sans-serif;font-size:42px;font-weight:700;color:#FFFFFF;letter-spacing:-1px;line-height:1;text-transform:uppercase;text-shadow:0 2px 8px rgba(0,0,0,0.5);">Football Lens</div>
<div style="font-size:14px;color:rgba(255,255,255,0.75);margin-top:8px;font-family:'Source Sans 3',sans-serif;">LangGraph 파이프라인 · Claude · GPT-4o-mini · Gemini · ChromaDB RAG</div>
<div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;">
<span style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:2px;padding:4px 12px;font-size:11px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">⚡ LangGraph</span>
<span style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:2px;padding:4px 12px;font-size:11px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">🤖 Multi-LLM</span>
<span style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:2px;padding:4px 12px;font-size:11px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">🔍 RAG</span>
</div>
</div>
<div style="display:flex;flex-direction:column;align-items:center;gap:12px;">
<img src="{LOGO_COLOR}" style="width:70px;height:70px;filter:drop-shadow(0 2px 10px rgba(0,0,0,0.6));" alt="Football Lens">
<div style="text-align:center;">
<div style="font-family:'Oswald',sans-serif;font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;">{datetime.now().strftime('%Y.%m.%d')}</div>
<div style="font-family:'Oswald',sans-serif;font-size:13px;color:#FFFFFF;font-weight:600;">{datetime.now().strftime('%A').upper()}</div>
</div>
</div>
</div>
</div>
""")


# =============================================
# 카드 컴포넌트
# =============================================

def render_news_card(article: dict, show_image: bool = False):
    """
    ESPN 스타일 뉴스 카드를 렌더링합니다.

    Parameters
    ----------
    article : dict
        기사 딕셔너리
    show_image : bool
        True이면 섹션 이미지를 표시합니다 (주요 기사용)
    """
    lang = article.get("language", "ko")
    title = (article.get("title") or "제목 없음")[:120]
    summary = (article.get("summary") or "")[:160]
    url = article.get("url") or "#"
    source_name = article.get("source_name") or article.get("keyword") or ""
    category = article.get("category", "")

    tag = category or ("국내 축구" if lang == "ko" else "FOOTBALL")
    lang_cls = "eb-blue" if lang == "ko" else "eb-red"
    lang_txt = "🇰🇷 KO" if lang == "ko" else "🇬🇧 EN"
    title_html = (
        f'<a href="{url}" target="_blank" class="espn-card-title">{title}</a>'
        if url and url != "#"
        else f'<div class="espn-card-title">{title}</div>'
    )
    ellipsis = "..." if len(article.get("summary") or "") > 160 else ""

    img_html = ""
    article_img = article.get("image_url", "")
    if show_image or article_img:
        src = article_img or IMG_MATCH
        img_html = f'<img src="{src}" style="width:100%;height:110px;object-fit:cover;border-radius:2px;margin-bottom:8px;" alt="article" onerror="this.src=\'{IMG_MATCH}\'">'

    _html(f"""
<div class="espn-card">
{img_html}
<div class="espn-card-tag">{tag}</div>
{title_html}
<div class="espn-card-summary">{summary}{ellipsis}</div>
<div class="espn-card-meta">
<span class="ebadge {lang_cls}">{lang_txt}</span>
{"<span>·</span><span>" + source_name + "</span>" if source_name else ""}
</div>
</div>
""")


def render_rag_card(r: dict):
    """
    ESPN 스타일 RAG 검색 결과 카드를 렌더링합니다.

    Parameters
    ----------
    r : dict
        embedder.search() 결과
    """
    source = r.get("source", "real")
    lang = r.get("language", "ko")
    title = (r.get("title") or "")[:120]
    summary = (r.get("summary") or "")[:160]
    url = r.get("url") or "#"
    similarity = round((1 - r.get("distance", 0)) * 100, 1)

    src_cls = "eb-green" if source == "real" else "eb-gray"
    src_txt = "🟢 REAL" if source == "real" else "⬜ DEMO"
    lang_cls = "eb-blue" if lang == "ko" else "eb-red"
    lang_txt = "🇰🇷 KO" if lang == "ko" else "🇬🇧 EN"
    title_html = (
        f'<a href="{url}" target="_blank" class="espn-card-title">{title}</a>'
        if url and url != "#"
        else f'<div class="espn-card-title">{title}</div>'
    )

    _html(f"""
<div class="espn-card">
<div class="espn-card-tag">유사도 {similarity}%</div>
{title_html}
<div class="espn-card-summary">{summary}{"..." if len(r.get("summary","")) > 160 else ""}</div>
<div class="espn-card-meta">
<span class="ebadge {src_cls}">{src_txt}</span>
<span class="ebadge {lang_cls}">{lang_txt}</span>
<span class="ebadge eb-gold">{similarity}%</span>
</div>
<div class="sim-bar-bg"><div class="sim-bar-fill" style="width:{int(similarity)}%;"></div></div>
</div>
""")


def render_hot_issues(result: dict, league: str = None):
    """
    핫이슈 섹션 — 선택 리그 관련 기사를 우선으로, 최신 이미지 카드 6개를 3열 그리드로 표시합니다.
    league가 지정되면 해당 리그 관련 기사가 상위에 배치됩니다.
    """
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    if not all_articles:
        return

    # 최신순 정렬
    def _sort_key(a):
        pt = a.get("published_at")
        return str(pt) if pt else ""

    sorted_articles = sorted(all_articles, key=_sort_key, reverse=True)

    # 리그 관련 기사 우선 배치 (그룹 내 날짜 순서 유지)
    if league:
        sorted_articles = _filter_articles_by_league(sorted_articles, league)

    # 제목 기반 중복 제거 (URL이 달라도 같은 기사 걸러냄)
    seen_titles: set = set()
    deduped = []
    for a in sorted_articles:
        title_key = (a.get("title") or "")[:40].strip()
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            deduped.append(a)

    top = deduped[:6]

    espn_section("🔥", "HOT ISSUES", len(all_articles))

    cols = st.columns(3)
    for i, article in enumerate(top):
        with cols[i % 3]:
            title = (article.get("title") or "")[:80]
            url   = article.get("url") or "#"
            src   = article.get("source_name") or article.get("keyword") or ""
            pub   = str(article.get("published_at", ""))[:10]
            lang  = article.get("language", "ko")
            flag  = "🇰🇷" if lang == "ko" else "🇬🇧"
            _html(f"""
<div class="espn-card" style="padding:14px 16px;margin-bottom:10px;border-left:4px solid #CC0000;">
<div style="margin-bottom:6px;">
<span style="background:#CC0000;color:#FFF;font-family:'Oswald',sans-serif;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;padding:2px 7px;border-radius:2px;">{flag} {src}</span>
<span style="font-size:10px;color:#888;margin-left:8px;">{pub}</span>
</div>
<a href="{url}" target="_blank" style="text-decoration:none;">
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;line-height:1.4;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{title}</div>
</a>
</div>
""")


def render_league_overview(result: dict):
    """
    리그 오버뷰 섹션 — 수집된 순위표 데이터로 상위 5팀을 리그별 카드로 표시합니다.
    """
    standings = result.get("raw_standings", [])
    all_leagues = result.get("all_leagues_standings", {})

    if not standings and not all_leagues:
        return

    espn_section("🌍", "LEAGUE OVERVIEW")

    # EPL 단독 수집인 경우
    if standings and not all_leagues:
        all_leagues = {"EPL": {"meta": {"name": "프리미어리그", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"}, "standings": standings[:5]}}

    if not all_leagues:
        return

    league_cols = st.columns(min(len(all_leagues), 3))
    for col_i, (league_key, data) in enumerate(all_leagues.items()):
        meta      = data.get("meta", {})
        lg_stands = data.get("standings", [])[:5]
        flag      = meta.get("flag", "⚽")
        lg_name   = meta.get("name", league_key)

        with league_cols[col_i % len(league_cols)]:
            rows_html = ""
            for team in lg_stands:
                rank   = team.get("rank", "?")
                name   = (team.get("team_name") or "?")[:16]
                pts    = team.get("points", 0)
                won    = team.get("won", 0)
                draw   = team.get("draw", 0)
                lost   = team.get("lost", 0)
                rank_color = "#CC0000" if rank == 1 else ("#555" if rank <= 4 else "#888")
                rows_html += f"""
<div style="display:flex;align-items:center;padding:7px 12px;border-bottom:1px solid #F5F5F5;gap:8px;">
<span style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:{rank_color};min-width:20px;">{rank}</span>
<span style="flex:1;font-size:13px;font-weight:600;color:#1A1A1A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</span>
<span style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#CC0000;min-width:24px;text-align:right;">{pts}pt</span>
<span style="font-size:11px;color:#888;">({won}승{draw}무{lost}패)</span>
</div>"""
            _html(f"""
<div style="background:#FFFFFF;border-radius:6px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:12px;">
<div style="background:#CC0000;padding:10px 14px;display:flex;align-items:center;gap:8px;">
<span style="font-size:18px;">{flag}</span>
<span style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#FFF;text-transform:uppercase;">{lg_name}</span>
</div>
{rows_html}
</div>
""")


def espn_section(icon: str, title: str, count: int = None):
    """ESPN 스타일 섹션 헤더를 렌더링합니다."""
    count_html = (
        f'<span class="espn-sh-count">{count}건</span>'
        if count is not None else ""
    )
    _html(f"""
<div class="espn-sh">
<span style="font-size:20px;">{icon}</span>
<span class="espn-sh-title">{title}</span>
{count_html}
</div>
""")


# =============================================
# 리그별 기사 우선 필터
# =============================================

# 리그명 → 관련 키워드 매핑 (소문자로 비교)
_LEAGUE_KEYWORDS: dict = {
    "2026 FIFA 월드컵": ["월드컵", "world cup", "fifa 2026", "wc 2026", "2026 wc",
                        "월드컵 2026", "북중미 월드컵"],
    "EPL (프리미어리그)": ["epl", "프리미어리그", "premier league", "잉글랜드"],
    "K리그1":            ["k리그", "k-league", "kl1", "한국 프로축구", "k league"],
    "라리가":            ["라리가", "laliga", "la liga", "스페인 리그"],
    "분데스리가":         ["분데스리가", "bundesliga", "독일 리그"],
    "세리에A":           ["세리에", "serie a", "이탈리아 리그"],
    "리그앙":            ["리그앙", "ligue 1", "프랑스 리그"],
}

# 리그명 → 표시용 이름 + 이모지
_LEAGUE_DISPLAY: dict = {
    "2026 FIFA 월드컵": "🌍 2026 FIFA 월드컵",
    "EPL (프리미어리그)": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL",
    "K리그1":            "🇰🇷 K리그1",
    "라리가":            "🇪🇸 라리가",
    "분데스리가":         "🇩🇪 분데스리가",
    "세리에A":           "🇮🇹 세리에A",
    "리그앙":            "🇫🇷 리그앙",
}


def _filter_articles_by_league(articles: list, league: str) -> list:
    """
    선택 리그/대회 관련 기사를 상위로 올립니다.
    입력 articles의 원래 순서(최신순 등)를 각 그룹 내에서 유지합니다.

    Parameters
    ----------
    articles : list
        원본 기사 리스트 (이미 정렬된 상태여도 무방)
    league : str
        사이드바에서 선택된 리그명 (예: "EPL (프리미어리그)")

    Returns
    -------
    list
        [리그 관련 기사(입력 순서 유지)] + [기타 기사(입력 순서 유지)]
    """
    keywords = _LEAGUE_KEYWORDS.get(league, [])
    if not keywords or not articles:
        return articles

    relevant, others = [], []
    for a in articles:
        text = " ".join([
            (a.get("title")       or ""),
            (a.get("summary")     or ""),
            (a.get("source_name") or ""),
            (a.get("category")    or ""),
            (a.get("keyword")     or ""),
        ]).lower()
        if any(kw in text for kw in keywords):
            relevant.append(a)
        else:
            others.append(a)
    return relevant + others


# =============================================
# 유틸 함수
# =============================================

@st.cache_data(ttl=300, show_spinner=False)
def load_pipeline_result(days_back: int, league: str) -> dict:
    """
    LangGraph 파이프라인을 실행하고 결과를 반환합니다.
    5분간 캐시됩니다.
    """
    try:
        from week2.graph import run_pipeline
        result = run_pipeline(
            config={"days_back": days_back, "max_articles_per_source": 20, "league": league},
            verbose=False,
        )
        return result or {}
    except Exception as e:
        logger.error(f"파이프라인 오류: {e}")
        return {"errors": [str(e)], "final_report": f"파이프라인 오류: {e}"}


def _run_pipeline_in_thread(days_back: int, league: str, result_queue: queue.Queue):
    """
    백그라운드 스레드에서 파이프라인 전체를 실행합니다.
    완료되면 result_queue에 결과를 넣습니다.
    메인 스레드를 블록하지 않아 Streamlit WebSocket이 유지됩니다.
    """
    try:
        from week2.graph import run_pipeline
        result = run_pipeline(
            config={"days_back": days_back, "max_articles_per_source": 20, "league": league},
            verbose=False,
        ) or {}
        # RAG + 인사이트 노드도 스레드 안에서 실행
        try:
            from week3.rag.rag_node import rag_search_node
            from week3.insight_node import insight_node
            result.update(rag_search_node(result))
            result.update(insight_node(result))
        except Exception as e:
            result.setdefault("errors", []).append(f"RAG/인사이트 오류: {e}")
        result_queue.put(("ok", result))
    except Exception as e:
        logger.error(f"[백그라운드 파이프라인] 오류: {e}")
        result_queue.put(("error", str(e)))


@st.cache_data(ttl=600, show_spinner=False)
def _check_rag_packages() -> tuple[bool, str]:
    """chromadb + sentence-transformers 설치 여부를 확인합니다."""
    missing = []
    try:
        import chromadb  # noqa
    except ImportError:
        missing.append("chromadb")
    try:
        import sentence_transformers  # noqa
    except ImportError:
        missing.append("sentence-transformers")
    if missing:
        cmd = "pip install " + " ".join(missing)
        return False, cmd
    return True, ""


def _keyword_fallback_search(query: str, language: str = None) -> list:
    """
    ChromaDB 없을 때 session_state 기사에서 키워드 검색 (폴백).
    query의 각 단어가 제목 또는 요약에 포함된 기사를 반환합니다.
    """
    result = st.session_state.get("pipeline_result") or {}
    articles = result.get("raw_articles", [])
    if not articles:
        return []

    q_lower = query.lower()
    keywords = [w for w in q_lower.split() if len(w) >= 2]

    matched = []
    for a in articles:
        title   = (a.get("title", "") or "").lower()
        summary = (a.get("summary", "") or "").lower()
        text    = title + " " + summary
        score   = sum(1 for kw in keywords if kw in text)
        if score == 0:
            continue
        lang = a.get("language", "")
        if language and lang != language:
            continue
        matched.append({
            "id":          a.get("article_id", ""),
            "title":       a.get("title", ""),
            "summary":     a.get("summary", "")[:200],
            "url":         a.get("url", ""),
            "language":    lang,
            "source":      "real",
            "source_name": a.get("source_name", a.get("source", "")),
            "category":    a.get("category", ""),
            "distance":    round(1.0 - score / max(len(keywords), 1), 4),
        })

    # 매칭 점수 내림차순
    matched.sort(key=lambda x: x["distance"])
    return matched[:10]


def get_rag_search_results(query: str, language: str = None) -> tuple[list, str | None]:
    """
    ChromaDB RAG 검색을 실행합니다.

    Returns
    -------
    (results, error_msg)
        results   : 검색 결과 목록
        error_msg : None이면 정상, 문자열이면 표시할 에러 메시지
    """
    ok, missing_cmd = _check_rag_packages()
    if not ok:
        # 패키지 미설치 → 키워드 폴백
        fallback = _keyword_fallback_search(query, language)
        return fallback, missing_cmd

    try:
        from week3.rag.embedder import ArticleEmbedder
        embedder = ArticleEmbedder()
        if embedder.get_stats().get("total", 0) == 0:
            embedder.build_index()
        return embedder.search(query, n_results=10, language_filter=language or None), None
    except Exception as e:
        logger.error(f"RAG 검색 오류: {e}")
        fallback = _keyword_fallback_search(query, language)
        return fallback, str(e)


def send_report_email(report_text: str, recipients: list[str]) -> bool:
    """보고서를 이메일로 발송합니다."""
    try:
        from week3.mailer.email_sender import EmailSender
        EmailSender().send_report(
            report_markdown=report_text,
            recipients=recipients,
            subject=f"⚽ Football Lens 보고서 - {datetime.now().strftime('%Y-%m-%d')}",
        )
        return True
    except Exception as e:
        logger.error(f"이메일 오류: {e}")
        st.error(f"이메일 발송 실패: {e}")
        return False


# =============================================
# 사이드바
# =============================================

def render_sidebar() -> dict:
    """사이드바 — 설정 컨트롤 + 실행 버튼"""
    with st.sidebar:
        # ── 로고 헤더 ─────────────────────────────────────────
        _html(f"""
<div style="background:#CC0000;padding:14px 16px;margin:-1rem -1rem 20px;display:flex;align-items:center;gap:10px;">
  <img src="{LOGO_WHITE}" style="width:36px;height:36px;flex-shrink:0;" alt="FL">
  <div>
    <div style="font-family:'Oswald',sans-serif;font-size:16px;font-weight:700;color:#FFF;letter-spacing:0.5px;text-transform:uppercase;line-height:1.1;">Football Lens</div>
    <div style="font-size:10px;color:rgba(255,255,255,0.65);letter-spacing:1.5px;text-transform:uppercase;">AI Dashboard</div>
  </div>
</div>
""")

        # ── 설정 컨트롤 ───────────────────────────────────────
        st.caption("🏆 리그 / 대회")
        league = st.selectbox(
            "리그",
            options=["EPL (프리미어리그)", "2026 FIFA 월드컵", "K리그1", "라리가", "분데스리가", "세리에A", "리그앙"],
            index=0,
            label_visibility="collapsed",
        )

        st.caption(f"📅 수집 기간 — 최근 N일")
        days_back = st.slider("기간", min_value=1, max_value=30, value=7, step=1, label_visibility="collapsed")

        st.caption("🌐 언어")
        lang_options = {"전체": None, "한국어만": "ko", "영어만": "en"}
        lang_label = st.radio("언어", options=list(lang_options.keys()), index=0,
                              horizontal=True, label_visibility="collapsed")
        language = lang_options[lang_label]

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 실행 버튼 ─────────────────────────────────────────
        run_pipeline_btn = st.button(
            "⚡ 분석 실행",
            use_container_width=True,
            type="primary",
            help="LangGraph 파이프라인 실행 (1~3분)",
        )
        if st.button("↺ 캐시 초기화", use_container_width=True, help="수집 데이터 캐시를 지웁니다"):
            st.cache_data.clear()
            st.toast("캐시 초기화 완료", icon="✅")
            st.rerun()

        st.divider()

        # ── 파이프라인 상태 ───────────────────────────────────
        result = st.session_state.get("pipeline_result")
        if result:
            arts = len(result.get("raw_articles", []))
            ko   = len(result.get("korean_articles", []))
            en   = len(result.get("english_articles", []))
            _html(f"""
<div style="background:#F8F8F8;border-radius:6px;padding:10px 14px;font-size:12px;color:#555;line-height:1.8;">
  <div>📰 수집 기사 <strong style="color:#1A1A1A;float:right;">{arts}건</strong></div>
  <div>🇰🇷 국내 <strong style="color:#1A1A1A;float:right;">{ko}건</strong></div>
  <div>🌍 해외 <strong style="color:#1A1A1A;float:right;">{en}건</strong></div>
</div>
""")
        else:
            _html('<div style="font-size:12px;color:#AAA;text-align:center;padding:8px 0;">분석 실행 전</div>')

        _html(f'<div style="font-size:11px;color:#BBB;text-align:center;margin-top:6px;">🕐 {datetime.now().strftime("%Y.%m.%d %H:%M")}</div>')

    return {
        "league": league,
        "days_back": days_back,
        "language": language,
        "run_pipeline": run_pipeline_btn,
    }


# =============================================
# 탭 렌더러
# =============================================

def render_daily_report(result: dict, language: str, league: str = None):
    """
    일간 보고서 탭을 렌더링합니다.
    league가 지정되면 해당 리그/대회 관련 뉴스가 상단에 우선 배치됩니다.
    """
    league_display = _LEAGUE_DISPLAY.get(league, league or "⚽ 축구")

    if not result:
        _html(f"""
<div style="margin-top:20px;">
<div style="background:#FFFFFF;border-left:5px solid #CC0000;border-radius:0 6px 6px 0;padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,0.07);display:flex;align-items:center;gap:20px;">
<div style="font-size:40px;line-height:1;">⚡</div>
<div>
<div style="font-family:'Oswald',sans-serif;font-size:18px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:4px;">분석 준비 완료 — 사이드바에서 시작하세요</div>
<div style="font-size:14px;color:#666;">{league_display} 선택됨 → 기간 설정 → <strong style="color:#CC0000;">⚡ 분석 실행</strong> 클릭</div>
</div>
</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;">
<div style="background:#FFFFFF;border-radius:6px;padding:20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #CC0000;">
<div style="font-size:28px;margin-bottom:8px;">📰</div>
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">일간 보고서</div>
<div style="font-size:12px;color:#888;margin-top:4px;">국내·해외 뉴스 AI 요약</div>
</div>
<div style="background:#FFFFFF;border-radius:6px;padding:20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #003399;">
<div style="font-size:28px;margin-bottom:8px;">🔍</div>
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">RAG 기사 검색</div>
<div style="font-size:12px;color:#888;margin-top:4px;">ChromaDB 벡터 유사도 검색</div>
</div>
<div style="background:#FFFFFF;border-radius:6px;padding:20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #2E7D32;">
<div style="font-size:28px;margin-bottom:8px;">🏆</div>
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">{league_display}</div>
<div style="font-size:12px;color:#888;margin-top:4px;">리그/대회 최신 뉴스</div>
</div>
</div>
</div>
""")
        return

    # ── 스탯 메트릭 ────────────────────────────────────────
    stats = result.get("preprocessing_stats", {})
    ko_count = len(result.get("korean_articles", []))
    en_count = len(result.get("english_articles", []))
    match_count = len(result.get("raw_matches", []))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📥 수집 기사", f"{stats.get('total', 0)}건")
    with col2:
        st.metric("✅ 전처리 통과", f"{stats.get('passed', 0)}건")
    with col3:
        st.metric("🇰🇷 국내 / 🌍 해외", f"{ko_count} / {en_count}")
    with col4:
        st.metric("🏟️ 경기", f"{match_count}건")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 핫이슈 이미지 카드 그리드 (선택 리그 우선) ────────────
    render_hot_issues(result, league=league)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 리그 오버뷰 ─────────────────────────────────────────
    render_league_overview(result)

    # ── AI 인사이트 ─────────────────────────────────────────
    insight = result.get("insight_report", "")
    if insight:
        _html(f"""
<div style="background:#FFFFFF;border-left:5px solid #CC0000;border-radius:0 4px 4px 0;padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
<div style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#CC0000;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">🔎 AI 통합 인사이트 — RAG + Multi-LLM</div>
</div>
""")
        st.markdown(insight)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── 국내 뉴스 요약 ────────────────────────────────────
    if language in (None, "ko"):
        ko_summary = result.get("korean_summary", {})
        with st.expander("📺 국내 축구 뉴스 요약 (Claude)", expanded=True):
            if ko_summary.get("error"):
                st.warning(f"요약 실패: {ko_summary['error']}")
            elif ko_summary.get("summary_text"):
                st.markdown(ko_summary["summary_text"])
                if ko_summary.get("key_topics"):
                    topics = " ".join(
                        f'<span class="ebadge eb-dark">{t}</span>'
                        for t in ko_summary["key_topics"]
                    )
                    _html(f'<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;"><span style="font-size:12px;color:#888;align-self:center;">토픽:</span>{topics}</div>')
            else:
                st.info("국내 뉴스 데이터 없음")

    # ── 해외 뉴스 요약 ────────────────────────────────────
    if language in (None, "en"):
        en_summary = result.get("english_summary", {})
        with st.expander("🌍 해외 뉴스 요약 (GPT-4o-mini)", expanded=True):
            if en_summary.get("error"):
                st.warning(f"요약 실패: {en_summary['error']}")
            elif en_summary.get("summary_text"):
                st.markdown(en_summary["summary_text"])
            else:
                st.info("No English news data")

    # ── 경기 분석 ─────────────────────────────────────────
    match_analysis = result.get("match_analysis", {})
    with st.expander(f"🏟️ {league_display} 경기 분석 (Gemini)", expanded=True):
        if match_analysis.get("error"):
            st.warning(f"분석 실패: {match_analysis['error']}")
        elif match_analysis.get("analysis_text"):
            st.markdown(match_analysis["analysis_text"])
        else:
            # WC 폴백: 파이프라인 미반영 상태에서도 뉴스 목록 표시
            if league == "WC":
                all_arts = result.get("korean_articles", []) + result.get("english_articles", [])
                WC_KW = ["월드컵", "world cup", "worldcup", "fifa", "조별", "16강", "8강", "결승", "한국 대표"]
                wc_arts = [
                    a for a in all_arts
                    if any(kw in (a.get("title","") + a.get("summary","")).lower() for kw in WC_KW)
                ] or all_arts[:10]
                if wc_arts:
                    _html("""
<div style="background:#FFF8E1;border-left:4px solid #FFA000;border-radius:0 4px 4px 0;
     padding:10px 16px;margin-bottom:12px;font-size:12px;color:#666;">
  ℹ️ Gemini API로 심층 분석을 생성하려면 <code>.env</code>에 <code>GOOGLE_API_KEY</code>를 설정 후 Streamlit을 재시작하세요.
  현재는 수집된 뉴스 기사 목록을 표시합니다.
</div>
""")
                    for a in wc_arts[:12]:
                        title = (a.get("title") or "")[:90]
                        url   = a.get("url", "#")
                        src   = a.get("source_name", "")
                        pub   = str(a.get("published_at", ""))[:10]
                        _html(f"""
<div style="border-bottom:1px solid #F0F0F0;padding:8px 0;">
<a href="{url}" target="_blank"
   style="font-size:13px;font-weight:600;color:#1A1A1A;text-decoration:none;">{title}</a>
<div style="font-size:11px;color:#888;margin-top:2px;">{src} · {pub}</div>
</div>
""")
                else:
                    st.info("분석 실행 후 월드컵 경기 분석이 표시됩니다.")
            else:
                st.info("경기 데이터 없음 — 분석 실행 또는 football-data.org API 키 확인")

    # ── 기사 카드 그리드 (선택 리그 우선 정렬) ───────────────
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
        if language is None
        else result.get("korean_articles", []) if language == "ko"
        else result.get("english_articles", [])
    )
    # 선택 리그 관련 기사를 앞으로 배치
    if league and all_articles:
        all_articles = _filter_articles_by_league(all_articles, league)
    if all_articles:
        espn_section("🗞️", "Latest Articles", len(all_articles))
        # 상단 2개: 이미지 포함 featured
        feat_cols = st.columns(2)
        for i, article in enumerate(all_articles[:2]):
            with feat_cols[i]:
                render_news_card(article, show_image=True)
        # 나머지: 2열 그리드
        col_l, col_r = st.columns(2)
        for i, article in enumerate(all_articles[2:18]):
            with col_l if i % 2 == 0 else col_r:
                render_news_card(article)

    # ── Reddit 커뮤니티 포스트 ────────────────────────────
    reddit_posts = result.get("reddit_posts", [])
    if reddit_posts:
        st.markdown("<br>", unsafe_allow_html=True)
        espn_section("💬", "Reddit Football Community", len(reddit_posts))
        for post in reddit_posts[:6]:
            sub = post.get("subreddit", "")
            title = (post.get("title") or "")[:70]
            url   = post.get("url", "#")
            pub   = str(post.get("published_at", ""))[:10]
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:10px 16px;margin-bottom:6px;box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;gap:12px;">
<span style="background:#FF4500;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;flex-shrink:0;">r/{sub}</span>
<a href="{url}" target="_blank" style="font-size:13px;color:#1A1A1A;text-decoration:none;flex:1;">{title}</a>
<span style="font-size:11px;color:#888;flex-shrink:0;">{pub}</span>
</div>
""")

    # ── 득점 순위 미니 테이블 ─────────────────────────────
    top_scorers = result.get("top_scorers", [])
    if top_scorers:
        st.markdown("<br>", unsafe_allow_html=True)
        espn_section("⚽", "Top Scorers")
        cols = st.columns(5)
        for i, s in enumerate(top_scorers[:5]):
            with cols[i]:
                _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:12px 10px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#CC0000;">{s.get('goals', 0)}</div>
<div style="font-family:'Oswald',sans-serif;font-size:11px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">{(s.get('player_name') or '')[:14]}</div>
<div style="font-size:10px;color:#888;">{(s.get('team_name') or '')[:16]}</div>
<div style="font-size:10px;color:#555;margin-top:2px;">{s.get('assists', 0)}A</div>
</div>
""")

    errors = result.get("errors", [])
    if errors:
        with st.expander(f"⚠️ 오류 {len(errors)}건", expanded=False):
            for err in errors:
                st.error(err)


def render_weekly_report(result: dict, league: str = None):
    """
    주간 보고서 탭을 렌더링합니다.
    league가 지정되면 해당 리그/대회 이름이 섹션 헤더에 표시됩니다.
    """
    league_display = _LEAGUE_DISPLAY.get(league, league or "⚽ 축구")

    if not result:
        _html(f"""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<img src="{IMG_TROPHY}" style="width:100%;height:120px;object-fit:cover;border-radius:3px;margin-bottom:16px;opacity:0.5;" alt="trophy">
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">주간 보고서 없음</div>
<div style="font-size:14px;color:#888;">기간을 <strong style="color:#CC0000;">7일 이상</strong>으로 설정 후 분석을 실행하세요</div>
</div>
""")
        return

    espn_section("📊", f"Weekly Report — {league_display}")

    final_report = result.get("final_report", "")
    if final_report:
        _html('<div style="background:#FFFFFF;border:1px solid #E5E5E5;border-radius:4px;padding:28px 32px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">')
        st.markdown(final_report)
        _html('</div>')
        st.download_button(
            label="📥 보고서 다운로드 (.md)",
            data=final_report,
            file_name=f"football_lens_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )
    else:
        st.info("보고서 데이터가 없습니다.")


def render_standings_tab(result: dict):
    """EPL 순위표 탭을 렌더링합니다."""
    standings = result.get("raw_standings", [])
    if not standings:
        _html(f"""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<img src="{IMG_TROPHY}" style="width:100%;height:100px;object-fit:cover;border-radius:3px;margin-bottom:16px;opacity:0.5;" alt="trophy">
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">순위 데이터 없음</div>
<div style="font-size:14px;color:#888;">EPL 분석을 먼저 실행해주세요</div>
</div>
""")
        return

    try:
        import pandas as pd
        import plotly.express as px

        df = pd.DataFrame(standings)
        display_cols = ["rank", "team_name", "played", "won", "draw", "lost",
                        "goals_for", "goals_against", "goal_diff", "points", "form"]
        col_labels = {
            "rank": "순위", "team_name": "팀", "played": "경기",
            "won": "승", "draw": "무", "lost": "패",
            "goals_for": "득점", "goals_against": "실점",
            "goal_diff": "득실차", "points": "승점", "form": "최근 5경기",
        }
        available_cols = [c for c in display_cols if c in df.columns]
        df_display = df[available_cols].rename(columns=col_labels)

        espn_section("📋", "EPL Standings")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        if "team_name" in df.columns and "points" in df.columns:
            espn_section("📊", "Top 10 Points")
            fig = px.bar(
                df.head(10),
                x="team_name", y="points",
                color="points",
                color_continuous_scale=[[0, "#F5C6C6"], [0.5, "#FF4444"], [1, "#CC0000"]],
                text="points",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                font=dict(color="#1A1A1A", family="Oswald"),
                xaxis=dict(tickangle=-30, gridcolor="#EEEEEE", linecolor="#DDDDDD", title=None, tickfont=dict(family="Oswald", size=11)),
                yaxis=dict(gridcolor="#EEEEEE", linecolor="#DDDDDD", title="승점"),
                coloraxis_showscale=False, showlegend=False,
                margin=dict(t=20, b=40, l=20, r=20), height=320,
            )
            fig.update_traces(
                textposition="outside",
                textfont=dict(color="#CC0000", size=12, family="Oswald"),
                marker_line_color="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        for team in standings[:10]:
            _html(f"""
<div class="espn-card">
<div class="espn-card-tag">EPL Standings</div>
<div class="espn-card-title"><span style="color:#CC0000;margin-right:10px;">{team.get('rank','?')}위</span>{team.get('team_name','?')}</div>
<div class="espn-card-meta"><span class="ebadge eb-red">{team.get('points',0)}pts</span><span class="ebadge eb-dark">{team.get('won',0)}W</span><span class="ebadge eb-gray">{team.get('draw',0)}D</span><span>{team.get('lost',0)}L</span></div>
</div>
""")
    except Exception as e:
        st.error(f"순위표 오류: {e}")


def render_sentiment_badge(score: float, label: str) -> str:
    """감정 점수를 HTML 배지로 변환합니다."""
    if label == "긍정":
        color, bg = "#2E7D32", "#E8F5E9"
    elif label == "부정":
        color, bg = "#CC0000", "#FFEBEE"
    else:
        color, bg = "#555555", "#F5F5F5"
    bar_pct = int((score + 1) / 2 * 100)
    return (
        f'<span style="background:{bg};color:{color};border:1px solid {color}33;'
        f'border-radius:3px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:0.3px;">'
        f'{label} {score:+.2f}</span>'
    )


def render_transfer_rumors_tab(result: dict):
    """이적 루머 트래커 탭 — 리그 무관 최신 이적 소식을 모두 표시합니다."""

    # ── 이적 관련 키워드 (한/영) ──────────────────────────────
    TRANSFER_KW_KO = [
        "이적", "영입", "이적설", "영입설", "계약", "재계약", "협상", "제안", "입단",
        "방출", "임대", "이적료", "관심", "타진", "영입 목표", "FA",
    ]
    TRANSFER_KW_EN = [
        "transfer", "signing", "sign", "linked", "target", "bid", "deal",
        "contract", "loan", "fee", "move", "departure", "arrival", "negotiate",
        "reported", "interest", "offer",
    ]

    # 1) 파이프라인이 제공한 루머 기사 우선 사용
    rumors = list(result.get("transfer_rumors", []))

    # 2) 파이프라인 루머가 비어 있으면 모든 기사에서 직접 키워드 필터
    if not rumors:
        all_articles = (
            result.get("korean_articles", []) + result.get("english_articles", [])
        )
        sentiments_by_id = {
            s.get("article_id", ""): s
            for s in result.get("article_sentiments", [])
        }
        for a in all_articles:
            text = f"{a.get('title', '')} {a.get('summary', '')}".lower()
            ko_hit = any(kw in text for kw in TRANSFER_KW_KO)
            en_hit = any(kw in text for kw in TRANSFER_KW_EN)
            if ko_hit or en_hit:
                merged = dict(a)
                merged["sentiment"] = sentiments_by_id.get(a.get("article_id", ""), {})
                rumors.append(merged)

    # 최신순 정렬
    rumors.sort(key=lambda x: str(x.get("published_at", "")), reverse=True)

    if not rumors:
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">🔄</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">이적 소식 없음</div>
<div style="font-size:14px;color:#888;">먼저 <strong style="color:#CC0000;">⚡ 분석 실행</strong>으로 데이터를 수집하세요</div>
</div>
""")
        return

    espn_section("🔄", "Transfer Rumors — 최신 이적 소식", len(rumors))

    # 선수별 그룹화
    player_rumors: dict[str, list] = {}
    for r in rumors:
        sent = r.get("sentiment", {})
        players = sent.get("rumor_players", [])
        if players:
            for p in players:
                player_rumors.setdefault(p, []).append(r)
        else:
            player_rumors.setdefault("기타", []).append(r)

    # 선수 필터
    all_players = list(player_rumors.keys())
    if all_players:
        selected_player = st.selectbox(
            "선수 필터",
            options=["전체"] + all_players,
            label_visibility="collapsed",
        )
        if selected_player != "전체":
            filtered_rumors = player_rumors.get(selected_player, [])
        else:
            filtered_rumors = rumors
    else:
        filtered_rumors = rumors

    # 루머 카드
    for r in filtered_rumors[:20]:
        sent = r.get("sentiment", {})
        score = sent.get("sentiment_score", 0)
        label = sent.get("sentiment_label", "중립")
        players = sent.get("rumor_players", [])
        clubs   = sent.get("rumor_clubs", [])

        badge_html = render_sentiment_badge(score, label)
        player_chips = " ".join(
            f'<span style="background:#1A1A1A;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;margin-right:3px;">👤 {p}</span>'
            for p in players[:3]
        )
        club_chips = " ".join(
            f'<span style="background:#003399;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;margin-right:3px;">🏟️ {c}</span>'
            for c in clubs[:3]
        )
        pub = r.get("published_at", "")
        pub_str = str(pub)[:10] if pub else ""
        src = r.get("source_name", "")
        title = (r.get("title") or "")[:90]
        url   = r.get("url", "#")
        summary = (r.get("summary") or "")[:120]

        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-left:4px solid #CC0000;padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
<a href="{url}" target="_blank" style="font-family:'Oswald',sans-serif;font-size:15px;font-weight:700;color:#1A1A1A;text-decoration:none;flex:1;margin-right:12px;line-height:1.35;">{title}</a>
{badge_html}
</div>
<div style="font-size:11px;color:#888;margin-bottom:8px;">{src} · {pub_str}</div>
<div style="font-size:13px;color:#555;margin-bottom:8px;">{summary}</div>
<div style="display:flex;flex-wrap:wrap;gap:4px;">{player_chips}{club_chips}</div>
</div>
""")


def render_trend_tab(result: dict):
    """트렌드 차트 탭 — 키워드 언급 빈도 + 감정 분포."""
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    sentiments = result.get("article_sentiments", [])

    if not result:
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">📈</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">트렌드 데이터 없음</div>
<div style="font-size:14px;color:#888;margin-top:8px;">분석을 실행하면 키워드 트렌드 차트가 표시됩니다</div>
</div>
""")
        return

    try:
        import pandas as pd
        import plotly.graph_objects as go
        import plotly.express as px
        from collections import Counter

        # ── 1. 키워드 빈도 차트 ──────────────────────────────
        espn_section("📊", "Keyword Frequency")
        TRACK_KEYWORDS = [
            "손흥민", "이강인", "황희찬", "김민재", "홀란드", "살라",
            "엠바페", "벨링엄", "야말", "케인", "이적", "챔피언스리그",
            "K리그", "EPL", "맨시티", "리버풀", "아스날",
        ]
        kw_counts = Counter()
        for a in all_articles:
            text = f"{a.get('title','')} {a.get('summary','')}".lower()
            for kw in TRACK_KEYWORDS:
                if kw.lower() in text:
                    kw_counts[kw] += 1

        if kw_counts:
            kw_df = pd.DataFrame(
                [(k, v) for k, v in kw_counts.most_common(15)],
                columns=["키워드", "언급 횟수"],
            )
            fig_kw = px.bar(
                kw_df, x="언급 횟수", y="키워드", orientation="h",
                color="언급 횟수",
                color_continuous_scale=[[0, "#FFCCCC"], [1, "#CC0000"]],
                text="언급 횟수",
            )
            fig_kw.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                font=dict(color="#1A1A1A", family="Oswald"),
                yaxis=dict(autorange="reversed", gridcolor="#EEEEEE", title=None),
                xaxis=dict(gridcolor="#EEEEEE", title="언급 횟수"),
                coloraxis_showscale=False,
                margin=dict(t=10, b=10, l=10, r=10), height=380,
            )
            fig_kw.update_traces(textposition="outside", textfont=dict(color="#CC0000"))
            st.plotly_chart(fig_kw, use_container_width=True)
        else:
            st.info("키워드 데이터 없음")

        # ── 2. 감정 분포 도넛 차트 ──────────────────────────
        if sentiments:
            espn_section("😊", "Sentiment Distribution")
            col1, col2 = st.columns([1, 2])

            label_counts = Counter(s.get("sentiment_label", "중립") for s in sentiments)
            labels  = list(label_counts.keys())
            values  = list(label_counts.values())
            colors  = {"긍정": "#2E7D32", "중립": "#888888", "부정": "#CC0000"}
            chart_colors = [colors.get(l, "#AAAAAA") for l in labels]

            with col1:
                fig_donut = go.Figure(go.Pie(
                    labels=labels, values=values,
                    hole=0.6,
                    marker=dict(colors=chart_colors, line=dict(color="#FFF", width=2)),
                    textinfo="label+percent",
                    textfont=dict(family="Oswald", size=12),
                ))
                fig_donut.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=260,
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            with col2:
                # 감정별 상위 기사
                for label in ["긍정", "중립", "부정"]:
                    top = [s for s in sentiments if s.get("sentiment_label") == label]
                    top = sorted(top, key=lambda x: abs(x.get("sentiment_score", 0)), reverse=True)
                    cnt = label_counts.get(label, 0)
                    color = colors.get(label, "#888")
                    _html(f'<div style="font-family:Oswald,sans-serif;font-size:12px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:0.5px;margin:8px 0 4px;">{label} ({cnt}건)</div>')
                    for s in top[:2]:
                        t = (s.get("title") or "")[:55]
                        sc = s.get("sentiment_score", 0)
                        _html(f'<div style="font-size:12px;color:#555;padding:3px 0;border-left:3px solid {color};padding-left:8px;margin-bottom:4px;">{t} <span style="color:{color};font-weight:700;">{sc:+.2f}</span></div>')

        # ── 3. 날짜별 기사 수 라인 차트 ──────────────────────
        if all_articles:
            espn_section("📅", "Daily Article Volume")
            date_counts = Counter()
            for a in all_articles:
                pub = a.get("published_at")
                if pub:
                    try:
                        date_counts[str(pub)[:10]] += 1
                    except Exception:
                        pass
            if date_counts:
                date_df = pd.DataFrame(
                    sorted(date_counts.items()),
                    columns=["날짜", "기사 수"],
                )
                fig_line = px.line(
                    date_df, x="날짜", y="기사 수",
                    markers=True,
                    color_discrete_sequence=["#CC0000"],
                )
                fig_line.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                    font=dict(color="#1A1A1A", family="Oswald"),
                    xaxis=dict(gridcolor="#EEEEEE", title=None),
                    yaxis=dict(gridcolor="#EEEEEE", title="기사 수"),
                    margin=dict(t=10, b=10, l=10, r=10), height=240,
                )
                fig_line.update_traces(
                    line=dict(width=2.5),
                    marker=dict(size=7, color="#CC0000"),
                )
                st.plotly_chart(fig_line, use_container_width=True)

    except ImportError:
        st.warning("트렌드 차트를 보려면 plotly와 pandas가 필요합니다: `pip install plotly pandas`")
    except Exception as e:
        st.error(f"트렌드 차트 오류: {e}")


def render_kleague_tab(result: dict):
    """K리그 전용 탭을 렌더링합니다."""
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    sentiments_by_id = {
        s.get("article_id", ""): s
        for s in result.get("article_sentiments", [])
    }

    K_LEAGUE_KEYWORDS = [
        "k리그", "k-리그", "전북현대", "울산hd", "울산", "fc서울", "포항스틸러스",
        "수원삼성", "인천유나이티드", "성남fc", "대구fc", "광주fc",
        "조규성", "오현규", "황인범",
    ]

    kleague_articles = [
        a for a in all_articles
        if any(kw in f"{a.get('title','')} {a.get('summary','')}".lower()
               for kw in K_LEAGUE_KEYWORDS)
    ]

    if not result:
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">🇰🇷</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">K리그 데이터 없음</div>
<div style="font-size:14px;color:#888;margin-top:8px;">분석 실행 후 K리그 뉴스가 표시됩니다</div>
</div>
""")
        return

    espn_section("🇰🇷", "K-League News", len(kleague_articles))

    if not kleague_articles:
        st.info("현재 수집된 K리그 기사가 없습니다. 검색 키워드에 'K리그', '전북현대', '울산HD' 등을 포함해주세요.")
        return

    # 팀별 기사 집계
    from collections import Counter
    TEAMS = ["전북현대", "울산hd", "fc서울", "포항스틸러스", "수원삼성"]
    team_cnt = Counter()
    for a in kleague_articles:
        text = f"{a.get('title','')} {a.get('summary','')}".lower()
        for t in TEAMS:
            if t in text:
                team_cnt[t] += 1

    if team_cnt:
        c1, c2, c3 = st.columns(3)
        for i, (team, cnt) in enumerate(team_cnt.most_common(3)):
            with [c1, c2, c3][i]:
                _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#CC0000;">{cnt}</div>
<div style="font-family:'Oswald',sans-serif;font-size:12px;font-weight:600;color:#1A1A1A;text-transform:uppercase;">{team.upper()}</div>
</div>
""")
        st.markdown("<br>", unsafe_allow_html=True)

    # K리그 기사 카드
    fallback_imgs = [IMG_MATCH, IMG_STADIUM, IMG_CROWD, IMG_TRAINING]
    for i, article in enumerate(kleague_articles[:12]):
        sent = sentiments_by_id.get(article.get("article_id", ""), {})
        score = sent.get("sentiment_score", 0)
        label = sent.get("sentiment_label", "중립")
        badge = render_sentiment_badge(score, label)
        title = (article.get("title") or "")[:80]
        url   = article.get("url", "#")
        src   = article.get("source_name", "")
        pub   = str(article.get("published_at", ""))[:10]
        summary = (article.get("summary") or "")[:100]

        img = fallback_imgs[i % len(fallback_imgs)]
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-left:4px solid #003399;padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="display:flex;align-items:flex-start;gap:14px;">
<img src="{img}" style="width:80px;height:60px;object-fit:cover;border-radius:3px;flex-shrink:0;" alt="">
<div style="flex:1;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
<a href="{url}" target="_blank" style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-decoration:none;line-height:1.35;flex:1;margin-right:8px;">{title}</a>
{badge}
</div>
<div style="font-size:11px;color:#888;">{src} · {pub}</div>
<div style="font-size:12px;color:#666;margin-top:4px;">{summary}</div>
</div>
</div>
</div>
""")


def render_spotlight_players_tab(result: dict, league: str = "PL"):
    """⭐ 주목할 선수 탭 — 리그별 주요 선수 + 관련 뉴스 + 감정 통계."""

    # 리그별 주목할 선수 목록
    _LEAGUE_SPOTLIGHT = {
        "WC":  ["손흥민", "이강인", "김민재", "메시", "음바페", "홀란드", "비니시우스", "벨링엄", "야말", "로드리"],
        "PL":  ["홀란드", "살라", "손흥민", "황희찬", "팔머", "아르테타", "벨링엄", "워트킨스", "이사크", "자카"],
        "PD":  ["비니시우스", "야말", "음바페", "벨링엄", "레반도프스키", "페드리", "모드리치", "크로스"],
        "BL1": ["케인", "무시알라", "그리말도", "비르츠", "그나브리", "킴미히", "사네"],
        "SA":  ["마르티네스", "루카쿠", "디마리아", "바레야", "오시멘", "초크", "라우타로"],
        "FL1": ["음바페", "뎀벨레", "음파페", "파리", "아카이오지", "테아테", "루베르트"],
        "KL1": ["조규성", "오현규", "황인범", "황의조", "이동경", "제르소", "마테우스"],
    }

    league_players = _LEAGUE_SPOTLIGHT.get(league, _LEAGUE_SPOTLIGHT["PL"])

    # 리그 이름 매핑
    _LEAGUE_NAME = {
        "WC": "2026 FIFA 월드컵", "PL": "EPL 프리미어리그",
        "PD": "라리가", "BL1": "분데스리가",
        "SA": "세리에A", "FL1": "리그앙", "KL1": "K리그1",
    }
    league_name = _LEAGUE_NAME.get(league, league)

    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    sentiments_by_id = {
        s.get("article_id", ""): s
        for s in result.get("article_sentiments", [])
    }
    top_scorers = result.get("top_scorers", [])

    espn_section("⭐", f"Spotlight Players — {league_name}")

    # 주목할 선수 chip 목록
    _html(f'<div style="font-size:11px;color:#CC0000;font-family:Oswald,sans-serif;font-weight:700;text-transform:uppercase;margin-bottom:8px;">⚡ {league_name} 주목 선수</div>')
    chip_cols = st.columns(min(len(league_players), 5))
    for i, p in enumerate(league_players[:5]):
        with chip_cols[i]:
            if st.button(p, key=f"spotlight_chip_{i}", use_container_width=True):
                st.session_state["spotlight_query"] = p

    # 두 번째 줄 chip (나머지)
    if len(league_players) > 5:
        chip_cols2 = st.columns(min(len(league_players) - 5, 5))
        for i, p in enumerate(league_players[5:10]):
            with chip_cols2[i]:
                if st.button(p, key=f"spotlight_chip2_{i}", use_container_width=True):
                    st.session_state["spotlight_query"] = p

    # 검색창
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        player_query = st.text_input(
            "선수 검색",
            placeholder=f"예: {league_players[0]}, {league_players[1]}...",
            label_visibility="collapsed",
            key="spotlight_search_input",
        )
    with col2:
        if st.button("🔍 검색", key="spotlight_search_btn", type="primary", use_container_width=True):
            if player_query:
                st.session_state["spotlight_query"] = player_query

    if player_query:
        st.session_state["spotlight_query"] = player_query
    query = st.session_state.get("spotlight_query", "")

    if not query:
        # 기본: 득점 순위 표시
        if top_scorers:
            st.markdown("<br>", unsafe_allow_html=True)
            espn_section("⚽", "Top Scorers")
            try:
                import pandas as pd
                df = pd.DataFrame(top_scorers[:10])
                cols_show = [c for c in ["rank", "player_name", "team_name", "goals", "assists", "penalties"] if c in df.columns]
                col_labels = {"rank": "순위", "player_name": "선수", "team_name": "팀",
                              "goals": "득점", "assists": "어시스트", "penalties": "PK"}
                st.dataframe(df[cols_show].rename(columns=col_labels), use_container_width=True, hide_index=True)
            except Exception:
                for s in top_scorers[:10]:
                    _html(f'<div style="padding:6px 0;border-bottom:1px solid #EEE;">'
                          f'<strong style="color:#CC0000;">{s.get("rank","?")}위</strong> '
                          f'{s.get("player_name","?")} <span style="color:#888;font-size:12px;">({s.get("team_name","?")})</span> '
                          f'— <strong>{s.get("goals",0)}</strong>골 {s.get("assists",0)}A</div>')
        else:
            st.info("위에서 선수 이름을 클릭하거나 검색하세요.")
        return

    if not all_articles:
        st.info("먼저 ⚡ 분석 실행으로 데이터를 수집하세요.")
        return

    # 선수 관련 기사 필터
    q_lower = query.lower()
    matched = [
        a for a in all_articles
        if q_lower in f"{a.get('title','')} {a.get('summary','')}".lower()
    ]

    if not matched:
        st.warning(f"'{query}' 관련 기사가 없습니다. 분석 실행 후 다시 시도하세요.")
        return

    # 감정 통계
    player_sentiments = [
        sentiments_by_id[a["article_id"]]
        for a in matched
        if a.get("article_id") in sentiments_by_id
    ]

    if player_sentiments:
        from collections import Counter
        avg_score = sum(s.get("sentiment_score", 0) for s in player_sentiments) / len(player_sentiments)
        label_cnt = Counter(s.get("sentiment_label", "중립") for s in player_sentiments)

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:#CC0000;">{len(matched)}</div>
<div style="font-size:12px;color:#888;">관련 기사</div>
</div>
""")
        with col_b:
            sc_color = "#2E7D32" if avg_score > 0.1 else ("#CC0000" if avg_score < -0.1 else "#888")
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid {sc_color};padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:{sc_color};">{avg_score:+.2f}</div>
<div style="font-size:12px;color:#888;">평균 감정 점수</div>
</div>
""")
        with col_c:
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #2E7D32;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:#2E7D32;">{label_cnt.get('긍정', 0)}</div>
<div style="font-size:12px;color:#888;">긍정 기사</div>
</div>
""")
        with col_d:
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #888;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:#888;">{label_cnt.get('부정', 0)}</div>
<div style="font-size:12px;color:#888;">부정 기사</div>
</div>
""")
        st.markdown("<br>", unsafe_allow_html=True)

    # 관련 기사 목록
    espn_section("📰", f"'{query}' Related Articles", len(matched))
    for a in matched[:15]:
        sent = sentiments_by_id.get(a.get("article_id", ""), {})
        score = sent.get("sentiment_score", 0)
        label = sent.get("sentiment_label", "중립")
        badge = render_sentiment_badge(score, label)
        is_rumor = sent.get("is_transfer_rumor", False)
        rumor_chip = '<span style="background:#E65C00;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;margin-left:4px;">🔄 이적설</span>' if is_rumor else ""
        title = (a.get("title") or "")[:80]
        url   = a.get("url", "#")
        src   = a.get("source_name", "")
        pub   = str(a.get("published_at", ""))[:10]
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:12px 16px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);display:flex;justify-content:space-between;align-items:center;">
<div style="flex:1;margin-right:12px;">
<a href="{url}" target="_blank" style="font-size:14px;font-weight:600;color:#1A1A1A;text-decoration:none;">{title}</a>
<div style="font-size:11px;color:#888;margin-top:3px;">{src} · {pub}</div>
</div>
<div style="display:flex;gap:4px;flex-shrink:0;">{badge}{rumor_chip}</div>
</div>
""")


def render_prediction_tab(result: dict, league: str = "PL"):
    """경기 예측 탭 — 리그 시즌 여부 확인 후 예측 또는 개막일 표시."""
    from datetime import date as _date

    # ── 리그별 시즌 일정 ──────────────────────────────────────
    # (season_start, season_end, next_season_start, league_display)
    _LEAGUE_SEASON = {
        # WC 2026: 2026-06-11 ~ 2026-07-19
        "WC":  (_date(2026, 6, 11),  _date(2026, 7, 19),  None,                "2026 FIFA 월드컵"),
        # EPL 2025/26: ~2026-05-24 종료, 2026/27 개막 예정 2026-08-08
        "PL":  (_date(2025, 8, 16),  _date(2026, 5, 24),  _date(2026, 8, 8),   "EPL 프리미어리그"),
        # La Liga 2025/26
        "PD":  (_date(2025, 8, 15),  _date(2026, 6, 1),   _date(2026, 8, 15),  "라리가"),
        # Bundesliga 2025/26: 8월 개막, 5월 종료
        "BL1": (_date(2025, 8, 22),  _date(2026, 5, 23),  _date(2026, 8, 7),   "분데스리가"),
        # Serie A 2025/26
        "SA":  (_date(2025, 8, 23),  _date(2026, 5, 31),  _date(2026, 8, 21),  "세리에A"),
        # Ligue 1 2025/26
        "FL1": (_date(2025, 8, 16),  _date(2026, 5, 24),  _date(2026, 8, 9),   "리그앙"),
        # K리그1 2025: 2~11월
        "KL1": (_date(2026, 2, 21),  _date(2026, 11, 30), None,                "K리그1"),
    }

    today = _date.today()
    season_info = _LEAGUE_SEASON.get(league)

    # ── 비시즌 처리 ───────────────────────────────────────────
    if season_info:
        s_start, s_end, next_start, lg_name = season_info
        in_season = s_start <= today <= s_end

        if not in_season and league != "WC":
            # 비시즌 안내 카드
            if next_start:
                days_left = (next_start - today).days
                next_str = next_start.strftime("%Y년 %m월 %d일")
                countdown = f"{days_left}일 후" if days_left > 0 else "곧 개막"
            else:
                next_str = "미정"
                countdown = ""

            _html(f"""
<div style="background:#FFFFFF;border-radius:8px;border:2px solid #E0E0E0;padding:48px 32px;text-align:center;margin-top:16px;">
<div style="font-size:56px;margin-bottom:16px;">🏖️</div>
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">{lg_name} — 비시즌</div>
<div style="font-size:15px;color:#555;margin-bottom:20px;">현재 리그가 진행 중이지 않습니다.</div>
<div style="display:inline-block;background:#CC0000;color:#FFF;border-radius:6px;padding:14px 28px;">
  <div style="font-size:11px;font-family:'Oswald',sans-serif;text-transform:uppercase;letter-spacing:1px;opacity:0.85;margin-bottom:4px;">다음 시즌 개막</div>
  <div style="font-family:'Oswald',sans-serif;font-size:24px;font-weight:700;">{next_str}</div>
  <div style="font-size:13px;margin-top:4px;opacity:0.9;">{countdown}</div>
</div>
<div style="margin-top:24px;font-size:12px;color:#888;">개막 후 분석을 실행하면 경기 예측이 표시됩니다.</div>
</div>
""")
            return

    # ── 분석 미실행 상태 ──────────────────────────────────────
    prediction = result.get("match_prediction", {})
    upcoming = result.get("upcoming_matches", [])

    if not result or (not prediction and not upcoming):
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">🎯</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">예측 데이터 없음</div>
<div style="font-size:14px;color:#888;margin-top:8px;">⚡ 분석 실행 후 경기 예측이 표시됩니다</div>
</div>
""")
        return

    espn_section("🎯", "Match Prediction")
    _html("""
<div style="background:#FFF3E0;border:1px solid #FFCC80;border-radius:3px;padding:10px 14px;margin-bottom:16px;font-size:12px;color:#E65100;">
⚠️ <strong>면책사항</strong>: 예측은 뉴스 감정 + 순위 데이터 기반의 참고 정보이며, 실제 결과를 보장하지 않습니다.
</div>
""")

    # 예정 경기 일정
    if upcoming:
        espn_section("📅", "Upcoming Fixtures", len(upcoming))
        for m in upcoming[:8]:
            date = str(m.get("utc_date", ""))[:10]
            home = m.get("home_team_name", "?")
            away = m.get("away_team_name", "?")
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:12px 18px;margin-bottom:6px;box-shadow:0 1px 3px rgba(0,0,0,0.06);display:flex;justify-content:space-between;align-items:center;">
<div style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#1A1A1A;">{home}</div>
<div style="font-family:'Oswald',sans-serif;font-size:11px;font-weight:600;color:#CC0000;text-align:center;padding:0 12px;">VS<br><span style="font-size:9px;color:#888;">{date}</span></div>
<div style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#1A1A1A;text-align:right;">{away}</div>
</div>
""")
        st.markdown("<br>", unsafe_allow_html=True)

    # AI 예측 텍스트
    pred_text = prediction.get("prediction_text", "")
    model = prediction.get("model_used", "")
    skip_keywords = ["없음", "API 키", "skip", "데이터 없음"]
    if pred_text and not any(kw in pred_text for kw in skip_keywords):
        espn_section("🤖", f"AI Prediction — {model}")
        _html('<div style="background:#FFFFFF;border:1px solid #E5E5E5;border-radius:4px;padding:24px 28px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">')
        st.markdown(pred_text)
        _html('</div>')
    elif upcoming:
        # 경기 일정은 있지만 LLM 예측 실패
        st.info("LLM API 키를 설정하면 AI 경기 예측이 생성됩니다. (.env의 ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY)")
    else:
        # WC이지만 예정 경기 API 데이터 없음 → 뉴스 기반 안내
        if league == "WC":
            all_articles = result.get("korean_articles", []) + result.get("english_articles", [])
            wc_articles = [a for a in all_articles if any(
                kw in f"{a.get('title','')} {a.get('summary','')}".lower()
                for kw in ["월드컵", "world cup", "worldcup", "2026 fifa"]
            )]
            if wc_articles:
                espn_section("📰", "월드컵 관련 뉴스 (경기 일정 API 대체)")
                for a in wc_articles[:6]:
                    title = (a.get("title") or "")[:80]
                    url = a.get("url", "#")
                    src = a.get("source_name", "")
                    pub = str(a.get("published_at", ""))[:10]
                    _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:12px 16px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
<a href="{url}" target="_blank" style="font-size:14px;font-weight:600;color:#1A1A1A;text-decoration:none;">{title}</a>
<div style="font-size:11px;color:#888;margin-top:3px;">{src} · {pub}</div>
</div>
""")
            else:
                st.info("월드컵 경기 일정 API 데이터를 가져오지 못했습니다. 분석 실행 후 다시 시도하세요.")


def render_worldcup_tab(result: dict):
    """2026 FIFA 월드컵 탭 — 그룹 순위 · 경기 일정 · 득점 순위 · 관련 뉴스"""

    # ── 헤더 배너 ─────────────────────────────────────────────
    _html("""
<div style="background:linear-gradient(135deg,#003399 0%,#CC0000 100%);
     border-radius:8px;padding:24px 28px;margin-bottom:20px;color:#FFF;
     display:flex;align-items:center;gap:20px;">
  <div style="font-size:52px;line-height:1;">🌍</div>
  <div>
    <div style="font-family:'Oswald',sans-serif;font-size:26px;font-weight:700;
         text-transform:uppercase;letter-spacing:1px;">2026 FIFA World Cup</div>
    <div style="font-size:13px;opacity:0.85;margin-top:4px;">
      🇺🇸 미국 · 🇨🇦 캐나다 · 🇲🇽 멕시코 &nbsp;|&nbsp; 48개국 · 12조 · 104경기
    </div>
  </div>
</div>
""")

    groups   = result.get("worldcup_groups", [])
    matches  = result.get("worldcup_matches", [])
    scorers  = result.get("worldcup_scorers", [])

    # 파이프라인 미실행 안내
    if not groups and not matches and not scorers:
        _html("""
<div style="background:#FFF8E1;border-left:4px solid #FFA000;border-radius:0 6px 6px 0;
     padding:16px 20px;font-size:13px;color:#555;">
  ⚡ <strong>분석 실행</strong> 후 월드컵 데이터가 표시됩니다.<br>
  <span style="font-size:12px;color:#888;">football-data.org API 키가 필요합니다 (무료 플랜 지원).</span>
</div>
""")
        # 월드컵 관련 뉴스 (API 없어도 표시)
        _render_worldcup_news(result)
        return

    # ── 탭 내 서브 섹션 ──────────────────────────────────────
    sec_groups, sec_scenarios, sec_matches, sec_scorers, sec_news = st.tabs(
        ["🗂️ 그룹 순위", "🎲 경우의 수", "📅 경기 일정·결과", "⚽ 득점 순위", "📰 관련 뉴스"]
    )

    # ── 그룹 순위 ─────────────────────────────────────────────
    with sec_groups:
        if not groups:
            st.info("그룹 순위 데이터를 불러오지 못했습니다.")
        else:
            espn_section("🗂️", "Group Stage Standings", len(groups))
            # 3열 그리드로 표시
            COLS = 3
            for row_start in range(0, len(groups), COLS):
                cols = st.columns(COLS)
                for col_idx, grp in enumerate(groups[row_start:row_start + COLS]):
                    with cols[col_idx]:
                        label = grp.get("group_label", grp.get("group", ""))
                        _html(f'<div style="font-family:Oswald,sans-serif;font-size:14px;font-weight:700;'
                              f'color:#CC0000;text-transform:uppercase;letter-spacing:0.5px;'
                              f'margin-bottom:6px;border-bottom:2px solid #CC0000;padding-bottom:4px;">'
                              f'{label}</div>')
                        table_rows = ""
                        for t in grp.get("standings", []):
                            pos   = t["position"]
                            name  = t.get("team_short", t.get("team_name", ""))[:18]
                            pts   = t.get("points", 0)
                            played = t.get("played", 0)
                            won   = t.get("won", 0)
                            draw  = t.get("draw", 0)
                            lost  = t.get("lost", 0)
                            gd    = t.get("gd", 0)
                            gd_str = f"+{gd}" if gd > 0 else str(gd)
                            # 1·2위: 진출권 (파란 배경)
                            bg = "#E3F2FD" if pos <= 2 else "#FFFFFF"
                            fw = "700" if pos <= 2 else "400"
                            table_rows += (
                                f'<tr style="background:{bg};">'
                                f'<td style="font-weight:{fw};color:#CC0000;width:20px;">{pos}</td>'
                                f'<td style="font-weight:{fw};max-width:120px;overflow:hidden;'
                                f'text-overflow:ellipsis;white-space:nowrap;">{name}</td>'
                                f'<td style="text-align:center;">{played}</td>'
                                f'<td style="text-align:center;">{won}</td>'
                                f'<td style="text-align:center;">{draw}</td>'
                                f'<td style="text-align:center;">{lost}</td>'
                                f'<td style="text-align:center;">{gd_str}</td>'
                                f'<td style="text-align:center;font-weight:700;">{pts}</td>'
                                f'</tr>'
                            )
                        _html(f"""
<table style="width:100%;font-size:11px;border-collapse:collapse;font-family:sans-serif;">
  <thead>
    <tr style="background:#F5F5F5;color:#888;">
      <th style="padding:4px 3px;text-align:left;">#</th>
      <th style="padding:4px 3px;text-align:left;">팀</th>
      <th style="padding:4px 2px;text-align:center;">경</th>
      <th style="padding:4px 2px;text-align:center;">승</th>
      <th style="padding:4px 2px;text-align:center;">무</th>
      <th style="padding:4px 2px;text-align:center;">패</th>
      <th style="padding:4px 2px;text-align:center;">득실</th>
      <th style="padding:4px 2px;text-align:center;">승점</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>
<div style="font-size:10px;color:#AAA;margin-top:4px;">🔵 16강 진출권</div>
""")
                        st.markdown("")

    # ── 경기 일정·결과 ────────────────────────────────────────
    with sec_matches:
        if not matches:
            st.info("최근/예정 경기 데이터가 없습니다.")
        else:
            finished  = [m for m in matches if m.get("status") == "FINISHED"]
            scheduled = [m for m in matches if m.get("status") in ("SCHEDULED", "TIMED")]
            live      = [m for m in matches if m.get("status") == "IN_PLAY"]

            if live:
                espn_section("🔴", "LIVE — 진행 중", len(live))
                for m in live:
                    _render_wc_match_card(m, live=True)

            if finished:
                espn_section("✅", "최근 경기 결과", len(finished))
                for m in sorted(finished, key=lambda x: x.get("utc_date",""), reverse=True)[:10]:
                    _render_wc_match_card(m)

            if scheduled:
                espn_section("📅", "예정 경기", len(scheduled))
                for m in sorted(scheduled, key=lambda x: x.get("utc_date",""))[:10]:
                    _render_wc_match_card(m)

    # ── 경우의 수 ─────────────────────────────────────────────
    with sec_scenarios:
        if not groups:
            st.info("분석 실행 후 경우의 수가 계산됩니다.")
        else:
            espn_section("🎲", "16강 진출 경우의 수", None)
            _html("""
<div style="background:#E3F2FD;border-left:4px solid #1565C0;border-radius:0 6px 6px 0;
     padding:10px 16px;margin-bottom:16px;font-size:12px;color:#1A1A1A;">
  📌 <strong>계산 기준</strong> — 그룹당 3경기, 1·2위 자동 진출 + 각 조 최하위 성적 3위 8팀 추가 진출 (2026 WC 기준)
</div>
""")
            for grp in groups:
                label = grp.get("group_label", grp.get("group", ""))
                standings = grp.get("standings", [])
                if not standings:
                    continue
                scenarios = _calc_wc_scenarios(standings)

                _html(f'<div style="font-family:Oswald,sans-serif;font-size:14px;font-weight:700;'
                      f'color:#003399;text-transform:uppercase;letter-spacing:0.5px;'
                      f'margin:16px 0 8px;border-bottom:2px solid #003399;padding-bottom:4px;">'
                      f'🌍 {label}</div>')

                rows_html = ""
                for sc in scenarios:
                    s_color = sc["color"]
                    s_bg    = sc["bg"]
                    rows_html += f"""
<div style="display:flex;align-items:center;gap:12px;padding:8px 14px;
     background:{s_bg};border-radius:4px;margin-bottom:4px;">
  <div style="font-family:Oswald,sans-serif;font-size:13px;font-weight:700;
       width:28px;color:{s_color};text-align:center;">{sc['pos']}</div>
  <div style="flex:1;font-family:Oswald,sans-serif;font-size:13px;font-weight:600;">
    {sc['team']}</div>
  <div style="font-size:12px;color:#555;min-width:80px;text-align:center;">
    {sc['pts']}점 (잔여{sc['remaining']}경기)</div>
  <div style="min-width:180px;">
    <span style="background:{s_color};color:#FFF;border-radius:3px;
         padding:3px 10px;font-size:11px;font-family:Oswald,sans-serif;font-weight:700;">
      {sc['status']}</span>
    <div style="font-size:11px;color:#666;margin-top:3px;">{sc['detail']}</div>
  </div>
</div>"""
                _html(rows_html)

    # ── 득점 순위 ─────────────────────────────────────────────
    with sec_scorers:
        if not scorers:
            st.info("득점 순위 데이터가 없습니다.")
        else:
            espn_section("⚽", "Top Scorers — 2026 World Cup", len(scorers))
            rows = ""
            for s in scorers:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(s["rank"], f'{s["rank"]}위')
                rows += (
                    f'<tr>'
                    f'<td style="font-size:16px;text-align:center;">{medal}</td>'
                    f'<td><strong>{s.get("player_name","")}</strong>'
                    f'<div style="font-size:11px;color:#888;">{s.get("nationality","")}</div></td>'
                    f'<td style="color:#888;font-size:12px;">{s.get("team_short", s.get("team_name",""))}</td>'
                    f'<td style="text-align:center;font-weight:700;font-size:18px;color:#CC0000;">'
                    f'{s.get("goals",0)}</td>'
                    f'<td style="text-align:center;color:#555;">{s.get("assists",0)}</td>'
                    f'</tr>'
                )
            _html(f"""
<table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:13px;">
  <thead>
    <tr style="background:#CC0000;color:#FFF;">
      <th style="padding:8px 6px;width:40px;">#</th>
      <th style="padding:8px 6px;text-align:left;">선수</th>
      <th style="padding:8px 6px;text-align:left;">국가대표팀</th>
      <th style="padding:8px 6px;text-align:center;">골</th>
      <th style="padding:8px 6px;text-align:center;">어시</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
""")

    # ── 관련 뉴스 ─────────────────────────────────────────────
    with sec_news:
        _render_worldcup_news(result)


def _calc_wc_scenarios(standings: list[dict]) -> list[dict]:
    """
    그룹 순위표를 받아 팀별 16강 진출 경우의 수를 계산합니다.

    2026 WC 규정:
        - 그룹당 4팀, 각 팀 3경기
        - 조 1·2위 자동 진출
        - 각 조 3위 중 상위 8팀도 진출 (wild card)

    Returns
    -------
    list[dict]
        team, pos, pts, remaining, max_pts, status, detail, color, bg
    """
    TOTAL_GAMES = 3  # 4팀 조별리그, 팀당 총 3경기

    # 현재 점수 내림차순 정렬
    sorted_teams = sorted(standings, key=lambda t: (
        -t.get("points", 0), -t.get("gd", 0), -t.get("gf", 0)
    ))

    result = []
    for team in sorted_teams:
        played    = team.get("played", 0)
        remaining = max(0, TOTAL_GAMES - played)
        pts       = team.get("points", 0)
        max_pts   = pts + remaining * 3
        pos       = team.get("position", 0)
        name      = team.get("team_short", team.get("team_name", ""))

        # 다른 팀들의 최대 가능 점수
        others = [t for t in sorted_teams if t is not team]
        others_max = sorted(
            [t.get("points", 0) + max(0, TOTAL_GAMES - t.get("played", 0)) * 3
             for t in others],
            reverse=True,
        )
        # 현재 2위 팀의 최대 가능 점수 (나를 제외한 1위)
        top2_threshold = others_max[1] if len(others_max) >= 2 else 0

        if remaining == 0:
            # 경기 완료 — 최종 순위
            if pos <= 2:
                status = "진출 확정"
                detail = "16강 진출 확정 🎉"
                color, bg = "#2E7D32", "#E8F5E9"
            elif pos == 3:
                status = "3위 대기"
                detail = "타 그룹 3위 성적 비교 후 확정"
                color, bg = "#E65100", "#FFF3E0"
            else:
                status = "탈락 확정"
                detail = "4위 탈락 확정"
                color, bg = "#CC0000", "#FFEBEE"
        else:
            rival_max = [
                t.get("points", 0) + max(0, TOTAL_GAMES - t.get("played", 0)) * 3
                for t in others
            ]
            rival_max_sorted = sorted(rival_max, reverse=True)
            second_rival_max = rival_max_sorted[1] if len(rival_max_sorted) >= 2 else 0

            if pts > second_rival_max:
                status = "진출 확정"
                detail = "수학적 진출 확정 ✅"
                color, bg = "#2E7D32", "#E8F5E9"
            elif max_pts < top2_threshold:
                status = "탈락 확정"
                detail = f"최대 {max_pts}점으로 진출 불가 ❌"
                color, bg = "#CC0000", "#FFEBEE"
            else:
                others_pts_sorted = sorted([t.get("points", 0) for t in others], reverse=True)
                second_pts = others_pts_sorted[1] if len(others_pts_sorted) >= 2 else 0
                pts_needed = max(0, second_pts + 1 - pts)
                wins_needed = (pts_needed + 2) // 3

                if wins_needed == 0:
                    status = "유리한 위치"
                    detail = f"현재 {pos}위, 잔여 {remaining}경기 소화 필요"
                    color, bg = "#1565C0", "#E3F2FD"
                elif wins_needed <= remaining:
                    status = "진출 가능"
                    detail = f"잔여 {remaining}경기 중 {wins_needed}승 이상 필요"
                    color, bg = "#1565C0", "#E3F2FD"
                else:
                    status = "탈락 위기"
                    detail = f"잔여 {remaining}경기 전승해도 불확실"
                    color, bg = "#E65100", "#FFF3E0"

        result.append({
            "team":      name,
            "pos":       pos,
            "pts":       pts,
            "remaining": remaining,
            "max_pts":   max_pts,
            "status":    status,
            "detail":    detail,
            "color":     color,
            "bg":        bg,
        })

    return result


def _render_wc_match_card(m: dict, live: bool = False):
    """월드컵 경기 카드 한 장을 렌더링합니다."""
    status   = m.get("status", "")
    utc_str  = m.get("utc_date", "")
    grp_raw  = m.get("group", "")
    grp      = (grp_raw.replace("GROUP_", "") + "조") if grp_raw else m.get("stage", "")
    home     = m.get("home_short", m.get("home_team", ""))
    away     = m.get("away_short", m.get("away_team", ""))
    h_score  = m.get("home_score")
    a_score  = m.get("away_score")

    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        date_str = dt.strftime("%m/%d %H:%M") + " (UTC)"
    except Exception:
        date_str = utc_str[:16]

    if status == "FINISHED":
        score_html = (
            f'<span style="font-size:22px;font-weight:700;color:#1A1A1A;">'
            f'{h_score} &nbsp;-&nbsp; {a_score}</span>'
        )
        status_badge = '<span style="background:#E8F5E9;color:#2E7D32;border-radius:3px;padding:2px 8px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;">FT</span>'
    elif live:
        score_html = (
            f'<span style="font-size:22px;font-weight:700;color:#CC0000;">'
            f'{h_score or 0} &nbsp;-&nbsp; {a_score or 0}</span>'
        )
        status_badge = '<span style="background:#CC0000;color:#FFF;border-radius:3px;padding:2px 8px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;">LIVE</span>'
    else:
        score_html = f'<span style="font-size:14px;color:#888;">{date_str}</span>'
        status_badge = '<span style="background:#E3F2FD;color:#1565C0;border-radius:3px;padding:2px 8px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;">예정</span>'

    _html(f"""
<div style="background:#FFFFFF;border-radius:6px;padding:14px 20px;margin-bottom:8px;
     box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:16px;">
  <div style="font-size:11px;min-width:36px;text-align:center;
       font-family:Oswald,sans-serif;font-weight:700;color:#CC0000;">{grp}</div>
  <div style="flex:1;display:flex;align-items:center;justify-content:space-between;gap:12px;">
    <div style="flex:1;text-align:right;font-family:Oswald,sans-serif;font-size:15px;font-weight:700;">{home}</div>
    <div style="text-align:center;min-width:100px;">{score_html}</div>
    <div style="flex:1;text-align:left;font-family:Oswald,sans-serif;font-size:15px;font-weight:700;">{away}</div>
  </div>
  <div style="min-width:52px;text-align:right;">{status_badge}</div>
</div>
""")


def _render_worldcup_news(result: dict):
    """월드컵 관련 기사를 필터링해서 보여줍니다."""
    WC_KEYWORDS = ["월드컵", "world cup", "worldcup", "fifa", "국가대표", "태극전사"]
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    wc_articles = [
        a for a in all_articles
        if any(kw in (a.get("title", "") + a.get("summary", "")).lower() for kw in WC_KEYWORDS)
    ]
    if not wc_articles:
        st.info("월드컵 관련 기사가 없습니다. 분석 실행 후 확인하세요.")
        return
    espn_section("📰", "World Cup News", len(wc_articles))
    col_l, col_r = st.columns(2)
    for i, a in enumerate(wc_articles[:16]):
        with col_l if i % 2 == 0 else col_r:
            render_news_card(a)


def render_youtube_tab(result: dict):
    """YouTube 하이라이트 탭을 렌더링합니다."""
    videos = result.get("youtube_videos", [])

    import os as _os
    if not _os.getenv("YOUTUBE_API_KEY"):
        _html("""
<div style="background:#FFF3E0;border-left:4px solid #FFA000;border-radius:0 6px 6px 0;
     padding:12px 16px;margin-bottom:16px;font-size:13px;color:#555;">
  📺 YouTube API 키가 설정되지 않았습니다. Mock 영상을 표시하거나 실제 영상을 보려면
  <strong>YOUTUBE_API_KEY</strong>를 .env에 입력하세요.<br>
  <span style="font-size:11px;color:#888;">발급: https://console.cloud.google.com → YouTube Data API v3</span>
</div>
""")

    if not videos:
        st.info("영상 데이터가 없습니다. 파이프라인을 실행하세요.")
        return

    espn_section("▶️", "Football Highlights", len(videos))
    col_l, col_r = st.columns(2)
    for i, v in enumerate(videos[:12]):
        with col_l if i % 2 == 0 else col_r:
            thumb = v.get("thumbnail", "")
            title = v.get("title", "")[:70]
            channel = v.get("channel", "")
            url = v.get("url", "#")
            query = v.get("query", "")
            pub = str(v.get("published_at", ""))[:10]
            thumb_html = f'<img src="{thumb}" style="width:100%;height:140px;object-fit:cover;border-radius:4px 4px 0 0;" onerror="this.style.display=\'none\'">' if thumb else ""
            _html(f"""
<div style="background:#FFFFFF;border-radius:6px;overflow:hidden;
     box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:16px;">
  {thumb_html}
  <div style="padding:12px 14px;">
    <div style="font-size:11px;color:#CC0000;font-family:Oswald,sans-serif;
         font-weight:700;text-transform:uppercase;margin-bottom:4px;">{query}</div>
    <a href="{url}" target="_blank" style="font-size:13px;font-weight:600;
       color:#1A1A1A;text-decoration:none;line-height:1.4;">{title}</a>
    <div style="font-size:11px;color:#888;margin-top:6px;">{channel} &nbsp;·&nbsp; {pub}</div>
  </div>
</div>
""")


def render_email_tab(result: dict):
    """이메일 발송 탭을 렌더링합니다."""
    espn_section("📧", "Email Report")

    final_report = result.get("final_report", "")
    if not final_report:
        st.info("분석 실행 후 이메일 발송이 가능합니다.")
        return

    col_form, col_side = st.columns([1, 1])

    with col_form:
        recipients_input = st.text_input(
            "수신자 이메일 (쉼표로 구분)",
            placeholder="example@email.com, another@email.com",
        )

        import os as _os
        smtp_ok = bool(_os.getenv("SMTP_USER") and _os.getenv("SMTP_PASSWORD"))
        if smtp_ok:
            _html(f'<div style="background:#E8F5E9;border:1px solid #A5D6A7;border-radius:3px;'
                  f'padding:10px 14px;margin:8px 0;font-size:12px;color:#2E7D32;'
                  f'font-family:Oswald,sans-serif;font-weight:600;text-transform:uppercase;">'
                  f'SMTP 설정 완료 — {_os.getenv("SMTP_HOST","")}</div>')
        else:
            _html('<div style="background:#FFF3E0;border:1px solid #FFCC80;border-radius:3px;'
                  'padding:10px 14px;margin:8px 0;font-size:12px;color:#E65100;'
                  'font-family:Oswald,sans-serif;font-weight:600;text-transform:uppercase;">'
                  'SMTP 미설정 — .env에 SMTP_USER / SMTP_PASSWORD 입력</div>')

        send_btn = st.button("📤 이메일 발송", type="primary", use_container_width=True, disabled=not smtp_ok)
        if send_btn:
            recipients = [r.strip() for r in recipients_input.split(",") if r.strip()]
            if not recipients:
                st.error("수신자 이메일을 입력해주세요.")
                return
            with st.spinner(f"{len(recipients)}명에게 발송 중..."):
                success = send_report_email(final_report, recipients)
            if success:
                st.success(f"✅ {len(recipients)}명에게 발송 완료!")
                st.balloons()

    with col_side:
        espn_section("👁️", "Preview")
        with st.expander("보고서 내용", expanded=True):
            st.markdown(final_report[:1200] + ("..." if len(final_report) > 1200 else ""))


# =============================================
# 메인 진입점
# =============================================


# =============================================
# 메인
# =============================================

def main():
    """대시보드 메인 함수."""
    inject_custom_css()

    settings = render_sidebar()

    # 속보 티커
    articles_for_ticker = []
    if "pipeline_result" in st.session_state:
        r = st.session_state.pipeline_result
        articles_for_ticker = r.get("korean_articles", []) + r.get("english_articles", [])
    render_ticker(articles_for_ticker or None)

    # 히어로
    render_hero()

    # 세션 초기화
    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = {}

    result = st.session_state.get("pipeline_result") or {}

    # 자정 캐시 자동 초기화
    current_hour = datetime.now().hour
    last_clear_hour = st.session_state.get("_last_cache_clear_hour", -1)
    if current_hour == 0 and last_clear_hour != 0:
        st.cache_data.clear()
        st.session_state["_last_cache_clear_hour"] = 0
    elif current_hour != 0:
        st.session_state["_last_cache_clear_hour"] = current_hour

    LOADING_HTML = """
<style>
@keyframes ball-spin {
    0%   { transform: rotate(0deg)   scale(1);    }
    25%  { transform: rotate(90deg)  scale(1.08); }
    50%  { transform: rotate(180deg) scale(1);    }
    75%  { transform: rotate(270deg) scale(1.08); }
    100% { transform: rotate(360deg) scale(1);    }
}
@keyframes pulse-ring {
    0%   { transform: scale(0.9); opacity: 0.6; }
    50%  { transform: scale(1.1); opacity: 0.2; }
    100% { transform: scale(0.9); opacity: 0.6; }
}
@keyframes dot-bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
    40%            { transform: translateY(-8px); opacity: 1; }
}
.fl-loading-wrap {
    background: #FFFFFF; border-radius: 12px;
    padding: 56px 40px 48px; text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    margin: 24px 0; border-top: 4px solid #CC0000;
}
.fl-ball-outer { position: relative; display: inline-block; width: 90px; height: 90px; margin-bottom: 24px; }
.fl-ring { position: absolute; inset: -10px; border-radius: 50%; background: rgba(204,0,0,0.08); animation: pulse-ring 1.6s ease-in-out infinite; }
.fl-ball { font-size: 72px; line-height: 90px; display: block; animation: ball-spin 1.4s linear infinite; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.18)); }
.fl-loading-title { font-family: 'Oswald', sans-serif; font-size: 22px; font-weight: 700; color: #1A1A1A; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.fl-loading-sub { font-size: 14px; color: #888; margin-bottom: 28px; }
.fl-dots-wrap { display: flex; justify-content: center; gap: 8px; }
.fl-dot { width: 10px; height: 10px; border-radius: 50%; background: #CC0000; animation: dot-bounce 1.2s ease-in-out infinite; }
.fl-dot:nth-child(2) { animation-delay: 0.2s; background: #E65C00; }
.fl-dot:nth-child(3) { animation-delay: 0.4s; background: #003399; }
</style>
<div class="fl-loading-wrap">
  <div class="fl-ball-outer">
    <div class="fl-ring"></div>
    <span class="fl-ball">⚽</span>
  </div>
  <div class="fl-loading-title">분석 진행 중</div>
  <div class="fl-loading-sub">뉴스 수집 → 전처리 → AI 분석 중입니다. 잠시 기다려주세요.</div>
  <div class="fl-dots-wrap"><div class="fl-dot"></div><div class="fl-dot"></div><div class="fl-dot"></div></div>
</div>
"""

    pipeline_btn = settings.get("run_pipeline", False)
    if pipeline_btn:
        league_code = (
            settings["league"]
            .replace("EPL (프리미어리그)", "PL")
            .replace("2026 FIFA 월드컵", "WC")
            .replace("K리그1", "KL1")
            .replace("라리가", "PD")
            .replace("분데스리가", "BL1")
            .replace("세리에A", "SA")
            .replace("리그앙", "FL1")
            .split("(")[0].strip()
        )
        rq = queue.Queue()
        st.session_state["_pipeline_queue"] = rq
        st.session_state["_pipeline_running"] = True
        t = threading.Thread(
            target=_run_pipeline_in_thread,
            args=(settings["days_back"], league_code, rq),
            daemon=True,
        )
        t.start()
        st.rerun()

    # 파이프라인 에러 표시
    if st.session_state.get("_pipeline_error"):
        err_msg = st.session_state.pop("_pipeline_error")
        st.error(f"⚠️ 파이프라인 오류: {err_msg}")
        st.info("사이드바에서 설정을 확인 후 다시 **⚡ 분석 실행**을 클릭하세요.")
    if st.session_state.get("_pipeline_running"):
        loading_ph = st.empty()
        loading_ph.markdown(LOADING_HTML, unsafe_allow_html=True)

        rq = st.session_state.get("_pipeline_queue")
        if rq:
            try:
                status, payload = rq.get(timeout=0.5)
                st.session_state["_pipeline_running"] = False
                st.session_state["_pipeline_queue"] = None
                if status == "ok":
                    st.session_state.pipeline_result = payload or {}
                    loading_ph.empty()
                    st.rerun()
                else:
                    st.session_state["_pipeline_running"] = False
                    st.session_state["_pipeline_error"] = payload
                    loading_ph.empty()
                    st.rerun()
            except queue.Empty:
                st.rerun()
        return

    # 탭 — 리그 표시명을 API 코드로 변환
    _league = (
        settings["league"]
        .replace("EPL (프리미어리그)", "PL")
        .replace("2026 FIFA 월드컵", "WC")
        .replace("K리그1", "KL1")
        .replace("라리가", "PD")
        .replace("분데스리가", "BL1")
        .replace("세리에A", "SA")
        .replace("리그앙", "FL1")
        .split("(")[0].strip()
    )
    (tab_daily, tab_weekly,
     tab_rumors,
     tab_player, tab_predict, tab_youtube,
     tab_email) = st.tabs([
        "⚽  일간 보고서",
        "📊  주간 보고서",
        "🔄  이적 루머",
        "⭐  주목할 선수",
        "🎯  경기 예측",
        "▶️  YouTube",
        "📧  이메일 발송",
    ])

    with tab_daily:
        render_daily_report(result, settings["language"], _league)
    with tab_weekly:
        render_weekly_report(result, _league)
    with tab_rumors:
        render_transfer_rumors_tab(result)
    with tab_player:
        render_spotlight_players_tab(result, _league)
    with tab_predict:
        render_prediction_tab(result, _league)
    with tab_youtube:
        render_youtube_tab(result)
    with tab_email:
        render_email_tab(result)


if __name__ == "__main__":
    main()
