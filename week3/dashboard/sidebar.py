# -*- coding: utf-8 -*-
"""
sidebar.py
==========
app.py에서 분리한 사이드바(리그·기간·언어 설정) 렌더링.
"""
from datetime import datetime

import streamlit as st

from constants import LOGO_WHITE
from components import _html


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
