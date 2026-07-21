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
from token_tracker import summarize_usage


@st.cache_data(ttl=60, show_spinner=False)
def _get_cumulative_cost() -> float:
    """results/ 에 저장된 모든 실행의 API 비용 합산 (60초 캐시)."""
    from week3.storage.results_store import list_results
    entries = list_results(limit=1000)
    return round(sum(e.get("cost_usd", 0.0) for e in entries), 6)


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

        # ── API 비용 추적 ─────────────────────────────────────
        usage_summary = summarize_usage((result or {}).get("llm_usage", []))
        if usage_summary["call_count"] > 0:
            cumulative_cost = _get_cumulative_cost()
            est_mark = "~" if usage_summary["has_estimate"] else ""
            _html(f"""
<div style="background:#FFF8E1;border-radius:6px;padding:10px 14px;margin-top:8px;font-size:12px;color:#555;line-height:1.8;">
  <div style="font-weight:700;color:#1A1A1A;margin-bottom:4px;">💰 API 비용</div>
  <div>이번 실행 <strong style="color:#CC0000;float:right;">{est_mark}${usage_summary['total_cost_usd']:.4f}</strong></div>
  <div>누적(저장분) <strong style="color:#1A1A1A;float:right;">~${cumulative_cost:.4f}</strong></div>
  <div style="font-size:10px;color:#999;margin-top:2px;">LLM 호출 {usage_summary['call_count']}건 · 토큰 {usage_summary['total_input_tokens']+usage_summary['total_output_tokens']:,}개</div>
</div>
""")
            if usage_summary["has_estimate"]:
                _html('<div style="font-size:10px;color:#AAA;margin-top:2px;">~ 표시는 Gemini 별칭 모델 단가 추정치 포함</div>')

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
