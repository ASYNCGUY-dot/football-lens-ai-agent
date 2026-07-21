# -*- coding: utf-8 -*-
"""
rag_node.py
===========
LangGraph StateGraph에 연결되는 RAG 검색 노드

동작:
    - state의 raw_articles / raw_matches를 기반으로 검색 쿼리를 자동 생성
    - ChromaDB에서 관련 기사를 검색
    - 검색 결과를 state의 rag_context에 저장

사용법:
    # week2/graph.py에서 노드로 등록
    from week3.rag.rag_node import rag_search_node

    graph.add_node("rag_search", rag_search_node)
    graph.add_edge("classify", "rag_search")
    graph.add_edge("rag_search", "summarize_korean")
"""

import sys
import os
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# week2 state 임포트
WEEK2_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "week2")
if WEEK2_PATH not in sys.path:
    sys.path.insert(0, WEEK2_PATH)

from state import FootballNewsState


def _build_queries(state: FootballNewsState) -> list[str]:
    """
    State의 기사와 경기 데이터에서 RAG 검색 쿼리를 생성합니다.

    전략:
        - 수집된 기사 제목에서 상위 5개 추출
        - 경기 데이터에서 팀명 기반 쿼리 추가
        - 기본 쿼리 2개 항상 포함 (EPL 전체, 한국 선수)

    Returns
    -------
    list[str]
        검색 쿼리 목록 (중복 제거)
    """
    queries = set()

    # 리그별 기본 쿼리
    league_code = state.get("config", {}).get("league", "PL")
    _LEAGUE_DEFAULT_QUERIES = {
        "WC":  ["2026 FIFA 월드컵 경기 결과", "월드컵 한국 대표팀 조별리그"],
        "PL":  ["EPL 프리미어리그 경기 결과", "한국 선수 손흥민 이강인 황희찬"],
        "KL1": ["K리그1 경기 결과", "한국 프로축구 순위"],
        "PD":  ["라리가 경기 결과", "레알마드리드 바르셀로나"],
        "BL1": ["분데스리가 경기 결과", "바이에른뮌헨 도르트문트"],
        "SA":  ["세리에A 경기 결과", "인테르밀란 유벤투스"],
        "FL1": ["리그앙 경기 결과", "PSG 파리생제르맹"],
    }
    for q in _LEAGUE_DEFAULT_QUERIES.get(league_code, ["축구 경기 결과", "한국 선수"]):
        queries.add(q)

    # 기사 제목 기반 쿼리
    articles = state.get("raw_articles", [])
    for a in articles[:5]:
        title = a.get("title", "")
        if title and len(title) > 5:
            # 제목을 그대로 쿼리로 사용 (30자 제한)
            queries.add(title[:30])

    # 경기 데이터 기반 쿼리
    matches = state.get("raw_matches", [])
    for m in matches[:3]:
        home = m.get("home_team_name", "")
        away = m.get("away_team_name", "")
        if home and away:
            queries.add(f"{home} vs {away}")

    return list(queries)


def rag_search_node(state: FootballNewsState) -> dict:
    """
    ChromaDB에서 관련 축구 기사를 RAG 검색합니다.

    실행 순서:
        1. State에서 검색 쿼리 자동 생성
        2. ArticleEmbedder로 ChromaDB 쿼리
        3. 중복 제거 후 rag_context에 저장

    인덱스가 비어 있으면 자동으로 build_index()를 호출합니다.

    State 업데이트 키:
        rag_context : 검색된 관련 기사 목록 (dict list)
        errors      : 오류 메시지 추가

    Parameters
    ----------
    state : FootballNewsState
        현재 그래프 상태

    Returns
    -------
    dict
        업데이트할 State 딕셔너리
    """
    logger.info("[rag_search_node] RAG 검색 시작")

    try:
        from week3.rag.embedder import ArticleEmbedder

        embedder = ArticleEmbedder()

        # 인덱스가 비어 있으면 자동 빌드
        stats = embedder.get_stats()
        if stats.get("total", 0) == 0:
            logger.info("[rag_search_node] 인덱스 없음 → 자동 빌드 시작")
            embedder.build_index()

        # 검색 쿼리 생성
        queries = _build_queries(state)
        logger.info(f"[rag_search_node] 검색 쿼리 {len(queries)}개: {queries[:3]}...")

        # 각 쿼리로 검색 후 결과 통합
        seen_ids = set()
        rag_results = []

        for query in queries:
            results = embedder.search(query, n_results=3)
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    rag_results.append(r)

        # 유사도 순 정렬 (distance 낮을수록 유사)
        rag_results.sort(key=lambda x: x.get("distance", 1.0))
        # 최대 20개 제한
        rag_results = rag_results[:20]

        logger.info(
            f"[rag_search_node] 완료 | 검색 결과 {len(rag_results)}건"
        )

        return {
            "rag_context": rag_results,
            "errors": [],
        }

    except ImportError as e:
        msg = f"[rag_search_node] 패키지 없음: {e}"
        logger.error(msg)
        return {"rag_context": [], "errors": [msg]}
    except (KeyError, TypeError) as e:
        msg = f"[rag_search_node] State 읽기 오류: {e}"
        logger.error(msg)
        return {"rag_context": [], "errors": [msg]}
    except Exception as e:
        msg = f"[rag_search_node] 예외 발생: {e}"
        logger.error(msg)
        return {"rag_context": [], "errors": [msg]}


# =============================================
# 직접 실행 시 노드 단독 테스트
# =============================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # week2 state 임포트
    sys.path.insert(0, WEEK2_PATH)
    from state import create_initial_state

    print("=== rag_search_node 단독 테스트 ===\n")
    state = create_initial_state()
    result = rag_search_node(state)

    contexts = result.get("rag_context", [])
    print(f"RAG 검색 결과: {len(contexts)}건")
    for ctx in contexts[:5]:
        print(f"  [{ctx['source']}][{ctx['language']}] {ctx['title'][:50]}  (거리: {ctx['distance']})")
