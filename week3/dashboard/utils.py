# -*- coding: utf-8 -*-
"""
utils.py
========
app.py에서 분리한 비-UI 로직: 파이프라인 실행, RAG 검색, 이메일 발송,
리그 필터링 등.
"""
import logging
import queue
from datetime import datetime

import streamlit as st

from constants import _LEAGUE_KEYWORDS

logger = logging.getLogger(__name__)


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



def run_pipeline_and_save(days_back: int, league: str) -> dict:
    """
    파이프라인(수집~LLM 분석) + RAG/인사이트 노드를 실행하고 결과를 저장한다.

    Streamlit 세션(스레드)뿐 아니라 week3/scheduler.py의 헤드리스 실행에서도
    그대로 재사용하기 위해 _run_pipeline_in_thread에서 분리했다.
    저장 실패는 파이프라인 자체를 막지 않고 경고 로그만 남긴다.
    """
    from week2.graph import run_pipeline
    result = run_pipeline(
        config={"days_back": days_back, "max_articles_per_source": 20, "league": league},
        verbose=False,
    ) or {}

    try:
        from week3.rag.rag_node import rag_search_node
        from week3.insight_node import insight_node
        result.update(rag_search_node(result))
        result.update(insight_node(result))
    except Exception as e:
        result.setdefault("errors", []).append(f"RAG/인사이트 오류: {e}")

    try:
        from week3.storage.results_store import save_result
        save_result(result)
    except Exception as e:
        logger.warning(f"결과 저장 실패: {e}")

    return result


def _run_pipeline_in_thread(days_back: int, league: str, result_queue: queue.Queue):
    """
    백그라운드 스레드에서 run_pipeline_and_save()를 실행합니다.
    완료되면 result_queue에 결과를 넣습니다.
    메인 스레드를 블록하지 않아 Streamlit WebSocket이 유지됩니다.
    """
    try:
        result = run_pipeline_and_save(days_back, league)
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
