# -*- coding: utf-8 -*-
"""
state.py
========
LangGraph StateGraph에서 사용하는 공유 상태(State) 정의

FootballNewsState는 그래프의 모든 노드가 읽고 쓰는 공용 데이터 컨테이너입니다.
LangGraph는 각 노드 실행 후 반환된 딕셔너리를 현재 State에 병합(merge)합니다.

State 흐름 요약:
    [수집] → raw_articles
    [전처리] → korean_articles, english_articles
    [분류] → routing_flags (어떤 노드로 갈지 결정)
    [LLM 노드들] → korean_summary, english_summary, match_analysis
    [병합] → final_report
"""

from __future__ import annotations

from typing import Annotated, Any
from typing_extensions import TypedDict

# LangGraph의 add_messages처럼 리스트를 append 방식으로 병합하는 리듀서
# 여기서는 간단히 "덮어쓰기" 방식을 기본으로 사용하고,
# 필요한 필드만 operator.add 리듀서를 적용합니다.
import operator


# =============================================
# 기사 단건 타입 (타입 힌트용)
# =============================================

class Article(TypedDict, total=False):
    """수집된 기사 한 건의 구조 (week1 전처리 출력과 동일)"""
    article_id: str
    title: str
    url: str
    summary: str
    published_at: Any          # datetime 또는 str
    source_name: str
    language: str              # "ko" 또는 "en"
    category: str
    keyword: str
    collected_at: Any


class MatchData(TypedDict, total=False):
    """EPL 경기 한 건의 구조"""
    match_id: int
    matchday: int
    utc_date: str
    status: str
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    winner: str                # "HOME_TEAM" / "AWAY_TEAM" / "DRAW"


class StandingRow(TypedDict, total=False):
    """EPL 순위표 한 팀의 구조"""
    rank: int
    team_name: str
    played: int
    won: int
    draw: int
    lost: int
    points: int
    goal_diff: int
    form: str


# =============================================
# LLM 결과 타입
# =============================================

class SummaryResult(TypedDict, total=False):
    """LLM 요약 노드의 출력 구조"""
    model_used: str            # 사용된 모델 이름 (예: "claude-3-5-haiku-20241022")
    articles_count: int        # 요약에 사용된 기사 수
    summary_text: str          # LLM이 생성한 요약 텍스트
    key_topics: list[str]      # 주요 토픽 키워드 목록
    generated_at: str          # 생성 시각 (ISO 문자열)
    error: str | None          # 오류 발생 시 메시지


class MatchAnalysisResult(TypedDict, total=False):
    """경기 데이터 분석 노드의 출력 구조"""
    model_used: str
    matches_count: int
    analysis_text: str         # 경기 결과 분석 텍스트
    notable_results: list[str] # 주목할 경기 결과 목록
    standings_summary: str     # 순위표 요약
    generated_at: str
    error: str | None


class SentimentResult(TypedDict, total=False):
    """감정 분석 노드의 출력 구조"""
    article_id: str
    title: str
    sentiment_score: float     # -1.0(매우부정) ~ 1.0(매우긍정)
    sentiment_label: str       # "긍정" / "중립" / "부정"
    is_transfer_rumor: bool    # 이적 루머 여부
    rumor_players: list[str]   # 이적 루머 관련 선수 이름
    rumor_clubs: list[str]     # 이적 루머 관련 구단 이름


class MatchPredictionResult(TypedDict, total=False):
    """경기 예측 노드의 출력 구조"""
    model_used: str
    prediction_text: str       # 예측 내용 전문
    predictions: list[dict]    # [{"match": "A vs B", "prediction": "A 승", "confidence": "높음", "reason": "..."}]
    generated_at: str
    error: str | None


# =============================================
# 메인 State: FootballNewsState
# =============================================

class FootballNewsState(TypedDict, total=False):
    """
    LangGraph StateGraph의 공유 상태 컨테이너

    total=False : 모든 키가 선택적(Optional)
                  노드가 관련 키만 반환하면 나머지는 이전 값 유지

    필드 그룹:
        [입력/설정]
            run_id          : 이번 실행의 고유 ID (로깅/추적용)
            config          : 실행 설정 딕셔너리 (날짜 범위 등)

        [수집 단계]
            raw_articles    : 전체 수집된 기사 목록 (전처리 전)
            raw_matches     : 수집된 EPL 경기 결과 목록
            raw_standings   : 수집된 EPL 순위표

        [전처리/분류 단계]
            korean_articles : 전처리 후 한국어 기사 목록
            english_articles: 전처리 후 영어 기사 목록
            preprocessing_stats : 전처리 통계 딕셔너리

        [라우팅 플래그] — 조건부 엣지에서 사용
            has_korean      : 한국어 기사 존재 여부
            has_english     : 영어 기사 존재 여부
            has_match_data  : 경기 데이터 존재 여부

        [LLM 출력 단계]
            korean_summary  : 국내 뉴스 요약 결과 (Claude)
            english_summary : 해외 뉴스 요약 결과 (GPT-4o-mini)
            match_analysis  : 경기 데이터 분석 결과 (Gemini)

        [최종 출력]
            final_report    : 통합된 최종 리포트 텍스트
            report_generated_at : 리포트 생성 시각

        [오류 추적]
            errors          : 각 노드에서 발생한 오류 목록
                              Annotated + operator.add → 노드가 반환할 때마다 append
    """

    # ── 입력/설정 ──────────────────────────────────────────
    run_id: str
    config: dict[str, Any]

    # ── 수집 단계 ──────────────────────────────────────────
    raw_articles: list[Article]
    raw_matches: list[MatchData]
    raw_standings: list[StandingRow]

    # ── 전처리/분류 단계 ───────────────────────────────────
    korean_articles: list[Article]
    english_articles: list[Article]
    preprocessing_stats: dict[str, int]

    # ── 라우팅 플래그 (조건부 엣지용) ─────────────────────
    has_korean: bool
    has_english: bool
    has_match_data: bool

    # ── RAG 검색 결과 (week3 추가) ────────────────────────
    rag_context: list[dict]          # ChromaDB 검색 결과 (관련 기사 목록)

    # ── 추가 수집 데이터 ───────────────────────────────────
    youtube_videos: list[dict]       # YouTube 하이라이트 영상 메타데이터
    reddit_posts: list[dict]         # Reddit 축구 커뮤니티 인기 포스트
    top_scorers: list[dict]          # 득점 순위 (football-data.org)
    upcoming_matches: list[dict]     # 예정 경기 일정

    # ── 2026 FIFA 월드컵 ──────────────────────────────────────
    worldcup_groups: list[dict]      # 그룹별 순위표 (A조~L조)
    worldcup_matches: list[dict]     # 최근/예정 경기 일정+결과
    worldcup_scorers: list[dict]     # 월드컵 득점 순위

    # ── LLM 출력 ──────────────────────────────────────────
    korean_summary: SummaryResult
    english_summary: SummaryResult
    match_analysis: MatchAnalysisResult
    insight_report: str              # 통합 인사이트 보고서 (week3 추가)
    article_sentiments: list[SentimentResult]  # 기사별 감정 분석
    transfer_rumors: list[dict]      # 이적 루머 기사 목록
    match_prediction: MatchPredictionResult    # 경기 예측

    # ── 최종 출력 ─────────────────────────────────────────
    final_report: str
    report_generated_at: str

    # ── 오류 추적 (리스트 append 방식 병합) ────────────────
    # Annotated[list, operator.add] 덕분에 여러 노드가 에러를 추가해도 누락 없이 합산됨
    errors: Annotated[list[str], operator.add]

    # ── API 비용 추적 (리스트 append 방식 병합, errors와 동일 패턴) ─────
    # 각 LLM 호출 노드가 자신의 사용량 1건을 담아 반환하면 여기 누적됨
    llm_usage: Annotated[list[dict], operator.add]


# =============================================
# 초기 State 생성 헬퍼
# =============================================

def create_initial_state(run_id: str = None, config: dict = None) -> FootballNewsState:
    """
    그래프 실행 시작 시 빈 State를 생성합니다.

    Parameters
    ----------
    run_id : str, optional
        실행 ID. 미입력 시 현재 시각 기반으로 자동 생성.
    config : dict, optional
        실행 설정. 예: {"days_back": 7, "max_articles": 50}

    Returns
    -------
    FootballNewsState
        초기화된 State 딕셔너리

    예시:
        state = create_initial_state(run_id="run_001")
        graph.invoke(state)
    """
    from datetime import datetime, timezone

    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")

    return FootballNewsState(
        run_id=run_id,
        config=config or {"days_back": 7, "max_articles_per_source": 20},
        raw_articles=[],
        raw_matches=[],
        raw_standings=[],
        korean_articles=[],
        english_articles=[],
        preprocessing_stats={},
        has_korean=False,
        has_english=False,
        has_match_data=False,
        youtube_videos=[],
        reddit_posts=[],
        top_scorers=[],
        upcoming_matches=[],
        worldcup_groups=[],
        worldcup_matches=[],
        worldcup_scorers=[],
        article_sentiments=[],
        transfer_rumors=[],
        errors=[],
        llm_usage=[],
    )


# =============================================
# 직접 실행 시 State 구조 출력
# =============================================
if __name__ == "__main__":
    import json

    state = create_initial_state()
    print("=== FootballNewsState 구조 ===\n")
    print(f"run_id: {state['run_id']}")
    print(f"config: {state['config']}")
    print(f"errors: {state['errors']}")
    print(f"\n필드 목록:")
    for key in FootballNewsState.__annotations__:
        print(f"  {key}")
