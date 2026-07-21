# -*- coding: utf-8 -*-
"""tabs/rag_search.py — RAG 키워드 검색 탭."""
import streamlit as st

from components import espn_section, render_rag_card
from utils import get_rag_search_results


def render_rag_search_tab(result: dict):
    """
    RAG 검색 탭 — 키워드로 관련 기사를 검색합니다.

    get_rag_search_results()가 이미 ChromaDB 검색 → 키워드 폴백까지
    처리하므로, 이 함수는 검색 입력창과 결과 카드 렌더링만 담당한다.
    """
    espn_section("🔍", "RAG 기사 검색")

    query = st.text_input(
        "검색어를 입력하세요",
        placeholder="예: 손흥민 이적, 챔피언스리그 결과",
        key="rag_search_query",
    )
    lang_choice = st.radio(
        "언어", ["전체", "한국어", "영어"], horizontal=True, key="rag_search_lang",
    )
    lang_map = {"전체": None, "한국어": "ko", "영어": "en"}

    if not query:
        st.info("검색어를 입력하면 관련 기사를 찾아드립니다.")
        return

    with st.spinner("검색 중..."):
        results, error_msg = get_rag_search_results(query, lang_map[lang_choice])

    if error_msg:
        st.warning(f"⚠️ {error_msg} — 키워드 기반 폴백 검색 결과를 표시합니다.")

    if not results:
        st.info("검색 결과가 없습니다. 먼저 ⚡ 분석 실행으로 기사를 수집해주세요.")
        return

    for r in results:
        render_rag_card(r)
