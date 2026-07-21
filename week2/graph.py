"""
graph.py
========
LangGraph StateGraph 노드 연결 및 조건부 엣지 분기 구현

그래프 구조:
                         ┌──────────────────────────────────────────────────┐
                         │                                                  │
    START                │   fan-out (병렬 실행 가능)                        │
      │                  │                                                  │
      ▼                  │  ┌─────────────────────────────────────────────┐ │
  collect_node           │  │  has_korean=True  → summarize_korean_node  │ │
      │                  │  │  has_english=True → summarize_english_node │─┘
      ▼                  │  │  has_match_data=True → analyze_match_node  │
  preprocess_node        │  └─────────────────────────────────────────────┘
      │                  │               │  (모두 완료 후)
      ▼                  │               ▼
  classify_node ─────────┘          merge_node
                                         │
                                         ▼
                                        END

조건부 엣지 (route_after_classify):
    classify_node 실행 후 has_korean / has_english / has_match_data 플래그를
    검사하여 실행할 노드 목록을 반환합니다.
    해당 데이터가 없으면 노드를 건너뜁니다.

    반환값 형식: list[str] — LangGraph가 반환된 노드들을 동시에 실행 시작
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END, START

from state import FootballNewsState, create_initial_state
from nodes import collect_node, preprocess_node, classify_node, merge_node
from llm_nodes import (
    summarize_korean_node, summarize_english_node, analyze_match_node,
    sentiment_analysis_node, match_prediction_node,
)

logger = logging.getLogger(__name__)


# =============================================
# 조건부 엣지 라우팅 함수
# =============================================

def route_after_classify(state: FootballNewsState) -> list[str]:
    """
    classify_node 실행 후 다음에 실행할 노드들을 결정합니다.

    LangGraph의 add_conditional_edges에서 사용되는 라우팅 함수입니다.
    리스트로 여러 노드를 반환하면 LangGraph가 해당 노드들을 팬아웃(fan-out)하여
    병렬로 실행합니다.

    반환 규칙:
        - has_korean=True  → "summarize_korean" 포함
        - has_english=True → "summarize_english" 포함
        - has_match_data=True → "analyze_match" 포함
        - 아무것도 없으면 → 바로 "merge" 로 이동

    Parameters
    ----------
    state : FootballNewsState
        classify_node가 업데이트한 State

    Returns
    -------
    list[str]
        실행할 노드 이름 목록
    """
    try:
        next_nodes = []

        if state.get("has_korean"):
            next_nodes.append("summarize_korean")
            logger.debug("라우팅: summarize_korean 추가")

        if state.get("has_english"):
            next_nodes.append("summarize_english")
            logger.debug("라우팅: summarize_english 추가")

        if state.get("has_match_data"):
            next_nodes.append("analyze_match")
            logger.debug("라우팅: analyze_match 추가")

        # 기사가 있으면 감정 분석 항상 실행
        if state.get("has_korean") or state.get("has_english"):
            next_nodes.append("sentiment_analysis")
            logger.debug("라우팅: sentiment_analysis 추가")

        # 데이터가 전혀 없으면 바로 merge로
        if not next_nodes:
            logger.warning("수집된 데이터 없음 → merge로 바로 이동")
            next_nodes.append("merge")

        logger.info(f"[route_after_classify] 다음 노드: {next_nodes}")
        return next_nodes

    except (KeyError, TypeError) as e:
        logger.error(f"[route_after_classify] State 읽기 오류: {e} → merge로 폴백")
        return ["merge"]
    except Exception as e:
        logger.error(f"[route_after_classify] 예외 발생: {e} → merge로 폴백")
        return ["merge"]


# =============================================
# 그래프 빌드 함수
# =============================================

def build_graph() -> StateGraph:
    """
    FootballNewsState를 사용하는 전체 파이프라인 그래프를 생성합니다.

    Returns
    -------
    langgraph.graph.CompiledGraph
        invoke() / stream()을 호출할 수 있는 컴파일된 그래프

    노드 등록 순서:
        1. collect         : 뉴스 + EPL 데이터 수집
        2. preprocess      : 전처리 (중복 제거, 광고 필터)
        3. classify        : 언어 분류 + 라우팅 플래그
        4. summarize_korean: 국내 뉴스 요약 (Claude)
        5. summarize_english: 해외 뉴스 요약 (GPT-4o-mini)
        6. analyze_match   : EPL 경기 분석 (Gemini)
        7. merge           : 최종 리포트 통합

    엣지 구조:
        START → collect → preprocess → classify
        classify ──(조건부)──→ [summarize_korean, summarize_english, analyze_match]
        summarize_korean  → merge
        summarize_english → merge
        analyze_match     → merge
        merge → END
    """
    try:
        # ── 그래프 초기화 ──────────────────────────────────────
        graph = StateGraph(FootballNewsState)

        # ── 노드 등록 ──────────────────────────────────────────
        graph.add_node("collect",            collect_node)
        graph.add_node("preprocess",         preprocess_node)
        graph.add_node("classify",           classify_node)
        graph.add_node("summarize_korean",   summarize_korean_node)
        graph.add_node("summarize_english",  summarize_english_node)
        graph.add_node("analyze_match",      analyze_match_node)
        graph.add_node("sentiment_analysis", sentiment_analysis_node)
        graph.add_node("run_prediction",     match_prediction_node)
        graph.add_node("merge",              merge_node)

        # ── 일반 엣지 (순차 실행) ──────────────────────────────
        graph.add_edge(START,        "collect")
        graph.add_edge("collect",    "preprocess")
        graph.add_edge("preprocess", "classify")

        # ── 조건부 엣지 (classify 이후 분기) ─────────────────
        graph.add_conditional_edges(
            "classify",
            route_after_classify,
            {
                "summarize_korean":   "summarize_korean",
                "summarize_english":  "summarize_english",
                "analyze_match":      "analyze_match",
                "sentiment_analysis": "sentiment_analysis",
                "merge":              "merge",
            },
        )

        # ── fan-in 엣지 (LLM 노드들 → merge or prediction) ────
        graph.add_edge("summarize_korean",   "merge")
        graph.add_edge("summarize_english",  "merge")
        graph.add_edge("analyze_match",      "merge")
        # 감정 분석 완료 후 → 경기 예측 → merge
        graph.add_edge("sentiment_analysis", "run_prediction")
        graph.add_edge("run_prediction",     "merge")

        # ── 종료 엣지 ─────────────────────────────────────────
        graph.add_edge("merge", END)

        return graph

    except Exception as e:
        logger.error(f"[build_graph] 그래프 빌드 중 예외 발생: {e}")
        raise


def compile_graph():
    """
    그래프를 컴파일하여 실행 가능한 객체를 반환합니다.

    Returns
    -------
    CompiledGraph
        graph.invoke(state) 또는 graph.stream(state)로 실행 가능
    """
    try:
        graph = build_graph()
        compiled = graph.compile()
        logger.info("그래프 컴파일 완료")
        return compiled
    except Exception as e:
        logger.error(f"[compile_graph] 그래프 컴파일 중 예외 발생: {e}")
        raise


# =============================================
# 그래프 실행 헬퍼 함수
# =============================================

def run_pipeline(config: dict = None, verbose: bool = True) -> FootballNewsState:
    """
    전체 파이프라인을 실행하고 최종 State를 반환합니다.

    Parameters
    ----------
    config : dict, optional
        실행 설정. 예: {"days_back": 7, "max_articles_per_source": 20}
    verbose : bool
        True이면 실행 중 각 노드의 진행 상황을 출력합니다.

    Returns
    -------
    FootballNewsState
        모든 노드 실행 후의 최종 State

    예시:
        from graph import run_pipeline

        result = run_pipeline(config={"days_back": 3})
        print(result["final_report"])
    """
    try:
        initial_state = create_initial_state(config=config)
        app = compile_graph()

        if verbose:
            print(f"\n{'='*60}")
            print(f"⚽ Football Lens 파이프라인 시작")
            print(f"   run_id: {initial_state['run_id']}")
            print(f"   config: {initial_state['config']}")
            print(f"{'='*60}\n")

            # stream 모드: 노드별 실행 상황을 실시간 출력
            final_state = None
            try:
                for step in app.stream(initial_state):
                    node_name = list(step.keys())[0]
                    print(f"  ✓ {node_name} 완료")
                    final_state = step[node_name]
            except Exception as e:
                logger.error(f"[run_pipeline] 스트리밍 중 오류: {e}")
                # 스트리밍 실패 시 invoke로 폴백
                logger.info("[run_pipeline] invoke 모드로 재시도")
                final_state = app.invoke(initial_state)

        else:
            final_state = app.invoke(initial_state)

        if verbose and final_state:
            print(f"\n{'='*60}")
            print("파이프라인 완료!")
            errors = final_state.get("errors", [])
            if errors:
                print(f"⚠️  오류 {len(errors)}건 발생:")
                for e in errors:
                    print(f"   - {e}")
            print(f"{'='*60}\n")

        return final_state

    except Exception as e:
        logger.error(f"[run_pipeline] 파이프라인 실행 중 예외 발생: {e}")
        return {
            "errors": [f"파이프라인 오류: {e}"],
            "final_report": f"파이프라인 실행 실패: {e}",
            "raw_articles": [],
            "korean_articles": [],
            "english_articles": [],
        }


# =============================================
# 그래프 시각화 (선택사항)
# =============================================

def print_graph_structure():
    """
    그래프 구조를 텍스트로 출력합니다.
    Mermaid 다이어그램 코드도 함께 출력합니다 (LangGraph 기능).
    """
    app = compile_graph()
    try:
        # LangGraph가 Mermaid 다이어그램 코드를 생성
        mermaid_code = app.get_graph().draw_mermaid()
        print("=== Mermaid 다이어그램 코드 ===")
        print(mermaid_code)
        print("https://mermaid.live 에 붙여넣어 시각화할 수 있습니다.")
    except Exception as e:
        print(f"시각화 코드 생성 실패: {e}")


# =============================================
# 직접 실행 시 파이프라인 테스트
# =============================================
if __name__ == "__main__":
    import sys

    if "--viz" in sys.argv:
        print_graph_structure()
    else:
        result = run_pipeline(
            config={"days_back": 3, "max_articles_per_source": 10},
            verbose=True,
        )

        if result and result.get("final_report"):
            print("\n=== 최종 리포트 미리보기 (처음 500자) ===")
            print(result["final_report"][:500])
            print("...")
