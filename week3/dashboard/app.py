# -*- coding: utf-8 -*-
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

구조 (2026-07 분리):
    이 파일은 사이드바/탭 조립과 실행 진입점만 담당한다.
    실제 렌더링 로직은 constants.py / styles.py / components.py /
    utils.py / sidebar.py / tabs/*.py 로 분리되어 있다.
    (PROJECT_EVALUATION_REPORT.html #07 로드맵 Critical 항목 대응)
"""

import sys
import os
import queue
import threading
import logging
from datetime import datetime

# ── 경로 설정 ──────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
WEEK1_PATH = os.path.join(ROOT, "week1")
WEEK2_PATH = os.path.join(ROOT, "week2")
WEEK3_PATH = os.path.join(ROOT, "week3")
DASHBOARD_PATH = os.path.dirname(__file__)

for p in [ROOT, WEEK1_PATH, WEEK2_PATH, WEEK3_PATH, DASHBOARD_PATH]:
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

from styles import inject_custom_css
from components import render_ticker, render_hero
from sidebar import render_sidebar
from utils import _run_pipeline_in_thread
from tabs.daily import render_daily_report
from tabs.weekly import render_weekly_report
from tabs.standings import render_standings_tab
from tabs.trend import render_trend_tab
from tabs.rumors import render_transfer_rumors_tab
from tabs.kleague import render_kleague_tab
from tabs.worldcup import render_worldcup_tab
from tabs.players import render_spotlight_players_tab
from tabs.prediction import render_prediction_tab
from tabs.youtube import render_youtube_tab
from tabs.rag_search import render_rag_search_tab
from tabs.email import render_email_tab


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
    (tab_daily, tab_weekly, tab_standings, tab_trend,
     tab_rumors, tab_kleague, tab_worldcup,
     tab_player, tab_predict, tab_youtube,
     tab_rag_search, tab_email) = st.tabs([
        "⚽  일간 보고서",
        "📊  주간 보고서",
        "🏆  순위표",
        "📈  트렌드",
        "🔄  이적 루머",
        "🇰🇷  K리그",
        "🌍  월드컵",
        "⭐  주목할 선수",
        "🎯  경기 예측",
        "▶️  YouTube",
        "🔍  RAG 검색",
        "📧  이메일 발송",
    ])

    with tab_daily:
        render_daily_report(result, settings["language"], _league)
    with tab_weekly:
        render_weekly_report(result, _league)
    with tab_standings:
        render_standings_tab(result)
    with tab_trend:
        render_trend_tab(result)
    with tab_rumors:
        render_transfer_rumors_tab(result)
    with tab_kleague:
        render_kleague_tab(result)
    with tab_worldcup:
        render_worldcup_tab(result)
    with tab_player:
        render_spotlight_players_tab(result, _league)
    with tab_predict:
        render_prediction_tab(result, _league)
    with tab_youtube:
        render_youtube_tab(result)
    with tab_rag_search:
        render_rag_search_tab(result)
    with tab_email:
        render_email_tab(result)


if __name__ == "__main__":
    main()
