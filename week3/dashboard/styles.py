# -*- coding: utf-8 -*-
"""
styles.py
=========
app.py에서 분리한 ESPN 스타일 전역 CSS 주입 함수.
"""
import streamlit as st


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
