# -*- coding: utf-8 -*-
"""
insight_node.py
===============
RAG 검색 결과 + LLM 요약 결과를 통합하여 최종 인사이트 보고서를 생성합니다.

이 노드는 merge_node 이후에 실행되며:
    - RAG로 찾은 관련 기사 컨텍스트
    - Claude/GPT/Gemini 요약 결과
    - EPL 순위 및 경기 데이터
를 하나의 구조화된 인사이트 보고서로 통합합니다.

사용법:
    # week2/graph.py에서 노드로 등록
    from week3.insight_node import insight_node

    graph.add_node("insight", insight_node)
    graph.add_edge("merge", "insight")
    graph.add_edge("insight", END)
"""

import os
import sys
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# week2 state 임포트
WEEK2_PATH = os.path.join(os.path.dirname(__file__), "..", "week2")
if WEEK2_PATH not in sys.path:
    sys.path.insert(0, WEEK2_PATH)

# week1 league_registry 임포트
WEEK1_PATH = os.path.join(os.path.dirname(__file__), "..", "week1")
if WEEK1_PATH not in sys.path:
    sys.path.insert(0, WEEK1_PATH)

from state import FootballNewsState
from token_tracker import make_usage_record, usage_from_anthropic, usage_from_openai
from league_registry import LEAGUES as _LEAGUES


def _clean_api_key(key: str | None) -> str:
    """
    환경변수에서 읽은 API 키를 정제합니다 (week2/llm_nodes.py와 동일 로직).
    - 앞뒤 따옴표/공백 제거
    - 한국어 등 비ASCII 문자 포함 시 빈 문자열 반환 (플레이스홀더 감지)
    - 너무 짧은 값(<10자)은 빈 문자열 반환

    이 검증 없이 httpx로 요청을 보내면, 플레이스홀더 값이 HTTP 헤더에 들어가면서
    'ascii' codec can't encode characters ... 예외가 발생해 매번 폴백 경로를
    타면서 트레이스백 로그만 남기게 된다.
    """
    if not key:
        return ""
    key = key.strip().strip('"').strip("'")
    try:
        key.encode("ascii")
    except UnicodeEncodeError:
        return ""
    if len(key) < 10:
        return ""
    return key


# =============================================
# 프롬프트 생성 헬퍼
# =============================================

def _format_rag_context(rag_results: list[dict], max_count: int = 8) -> str:
    """
    RAG 검색 결과를 프롬프트용 텍스트로 변환합니다.

    Parameters
    ----------
    rag_results : list[dict]
        embedder.search() 결과
    max_count : int
        최대 표시 건수 (기본 8)

    Returns
    -------
    str
        프롬프트에 삽입할 컨텍스트 텍스트
    """
    if not rag_results:
        return "관련 기사 없음"
    lines = []
    for i, r in enumerate(rag_results[:max_count], 1):
        source_tag = "[더미]" if r.get("source") == "dummy" else "[수집]"
        lang_tag = "[KO]" if r.get("language") == "ko" else "[EN]"
        lines.append(
            f"{i}. {source_tag}{lang_tag} {r.get('title', '')}\n"
            f"   요약: {r.get('summary', '')[:120]}..."
        )
    return "\n".join(lines)


def _format_standings_brief(standings: list[dict], top_n: int = 5) -> str:
    """
    EPL 순위표 상위 팀을 요약 텍스트로 변환합니다.

    Parameters
    ----------
    standings : list[dict]
        FootballDataCollector.get_standings() 결과
    top_n : int
        표시할 팀 수

    Returns
    -------
    str
        순위 요약 텍스트
    """
    if not standings:
        return "순위 데이터 없음"
    lines = []
    for team in standings[:top_n]:
        lines.append(
            f"{team.get('rank', '?')}위 {team.get('team_name', '?'):20s} "
            f"{team.get('points', 0)}pts  "
            f"({team.get('won', 0)}승 {team.get('draw', 0)}무 {team.get('lost', 0)}패)"
        )
    return "\n".join(lines)


# 리그별 프롬프트 메타는 week1/league_registry.py에서 가져온다.
# 예전엔 이 파일에 별도 딕셔너리를 직접 정의해서, insight_node()의
# OpenAI 시스템 메시지가 "당신은 EPL 애널리스트입니다"로 고정 출력되던
# 문제가 있었다 — 이제 레지스트리 하나만 고치면 여기도 같이 반영된다.
def _get_league_meta(state: FootballNewsState) -> dict:
    league_code = state.get("config", {}).get("league", "PL")
    meta = _LEAGUES.get(league_code, _LEAGUES["PL"])
    return {
        "name": meta["full_name"],
        "role": meta["prompt_role"],
        "standings_label": meta["standings_label"],
        "section3": meta["section3_label"],
    }


def _build_insight_prompt(state: FootballNewsState) -> str:
    """
    통합 인사이트 보고서 생성용 프롬프트를 구성합니다.
    선택된 리그/대회(config.league)에 맞춰 프롬프트를 동적으로 생성합니다.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일")

    meta = _get_league_meta(state)
    league_name     = meta["name"]
    analyst_role    = meta["role"]
    standings_label = meta["standings_label"]
    section3_name   = meta["section3"]

    # 리그 관련 기사만 사용한다. classify_node(week2/nodes.py)가 이미
    # korean_articles/english_articles를 선택 리그로 필터링해두므로, 여기서
    # raw_articles를 별도의(더 허술한) 키워드 목록으로 다시 거르지 않는다
    # — 예전엔 이 함수가 자체 필터를 또 갖고 있어서 두 필터가 어긋나면
    # 오히려 관련 기사가 새는 문제가 있었다.
    league_articles = state.get("korean_articles", []) + state.get("english_articles", [])
    if not league_articles:
        # classify_node 필터 결과가 비정상적으로 비었을 때의 안전판.
        league_articles = state.get("raw_articles", [])

    article_titles = "\n".join(
        f"- {a.get('title','')[:60]}"
        for a in league_articles[:8]
        if a.get("title")
    ) or "수집된 기사 없음"

    rag_text = _format_rag_context(state.get("rag_context", []))
    standings_text = _format_standings_brief(state.get("raw_standings", []))
    ko_summary = state.get("korean_summary", {}).get("summary_text", "데이터 없음")
    en_summary = state.get("english_summary", {}).get("summary_text", "No data")
    match_analysis_text = state.get("match_analysis", {}).get("analysis_text", "데이터 없음")
    total_articles = len(league_articles)
    errors = state.get("errors", [])

    prompt = f"""당신은 {analyst_role}입니다.
아래 데이터를 바탕으로 오늘({now_str})의 **{league_name}** Football Lens 인사이트 보고서를 작성해주세요.
반드시 {league_name} 관련 내용만 포함하고, 다른 리그 정보는 제외하세요.

## 입력 데이터

### 1. {league_name} 주요 기사 제목
{article_titles}

### 2. RAG 관련 기사 컨텍스트
{rag_text}

### 3. {standings_label}
{standings_text}

### 4. 국내 뉴스 요약
{ko_summary[:300]}

### 5. 해외 뉴스 요약
{en_summary[:300]}

### 6. 경기 분석
{match_analysis_text[:300]}

## 작성 지침 ({league_name} 전용)
1. **오늘의 핵심 인사이트** (3개, 각 2~3문장): {league_name}의 가장 중요한 뉴스/이슈
2. **주목 선수** (2명): {league_name}에서 오늘 가장 주목받는 선수와 이유
3. **{section3_name}**: 현재 순위/상황 기반 간략한 전망 (3~4문장)
4. **내일 주목 경기** (있는 경우): {league_name} 예정 경기 중 가장 중요한 매치업
5. **에디터 픽**: {league_name}에서 오늘 가장 흥미로운 스토리 하나 (2~3문장)

⚠️ 주의: {league_name} 외 다른 리그 내용은 절대 포함하지 마세요.
⚠️ "주목 선수"에는 위 기사 제목에서 실제 사람 이름임이 분명한 경우에만 쓰세요.
"GD"처럼 약어·별명·불확실한 표현을 실제 선수 이름으로 추측해 지어내지 마세요.
⚠️ 후보가 부족하다고 다른 리그의 유명 선수(예: 호날두, 메시처럼 세계적으로
유명하지만 {league_name}와 무관한 선수)를 "직접 연관은 없지만"이라는 식으로
끼워넣지 마세요 — {league_name} 소속이거나 이 리그 기사에 실제로 등장하는
선수가 아니면 아예 쓰지 마세요. 확실한 후보가 1명뿐이거나 없으면 그만큼만
쓰세요, 2명을 채우는 것보다 정확한 게 우선입니다.
응답 형식: 마크다운, 각 섹션은 ## 헤더 사용, 총 400~600자
수집된 {league_name} 기사 수: {total_articles}건{"  |  ⚠️ 오류 " + str(len(errors)) + "건" if errors else ""}
"""
    return prompt.strip()


# =============================================
# insight_node 함수
# =============================================

def insight_node(state: FootballNewsState) -> dict:
    """
    RAG 컨텍스트와 LLM 요약을 통합하여 최종 인사이트 보고서를 생성합니다.

    사용 LLM 우선순위:
        1. Claude (Anthropic) — ANTHROPIC_API_KEY 있을 때
        2. GPT-4o-mini (OpenAI) — OPENAI_API_KEY 있을 때
        3. 목업 보고서 — API 키 없을 때 (테스트용)

    State 업데이트 키:
        insight_report      : 생성된 인사이트 보고서 텍스트
        final_report        : insight_report로 최종 리포트 갱신
        report_generated_at : 생성 시각

    Parameters
    ----------
    state : FootballNewsState
        현재 그래프 상태

    Returns
    -------
    dict
        업데이트할 State 딕셔너리
    """
    logger.info("[insight_node] 통합 인사이트 보고서 생성 시작")

    try:
        prompt = _build_insight_prompt(state)
        meta = _get_league_meta(state)
        now_iso = datetime.now(timezone.utc).isoformat()

        # ── Claude API 시도 ────────────────────────────────
        anthropic_key = _clean_api_key(os.getenv("ANTHROPIC_API_KEY"))
        if anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                insight_text = message.content[0].text
                logger.info("[insight_node] Claude로 인사이트 생성 완료")
                in_tok, out_tok = usage_from_anthropic(message)
                return {
                    "insight_report": insight_text,
                    "final_report": _build_final_report(state, insight_text),
                    "report_generated_at": now_iso,
                    "errors": [],
                    "llm_usage": [make_usage_record("anthropic", "claude-3-5-haiku-20241022", in_tok, out_tok, "insight_node")],
                }
            except Exception as e:
                logger.warning(f"[insight_node] Claude 오류, OpenAI로 폴백: {e}")

        # ── GPT-4o-mini 폴백 ──────────────────────────────
        openai_key = _clean_api_key(os.getenv("OPENAI_API_KEY"))
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"당신은 {meta['role']}입니다."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1024,
                    temperature=0.5,
                )
                insight_text = response.choices[0].message.content
                logger.info("[insight_node] GPT-4o-mini로 인사이트 생성 완료")
                in_tok, out_tok = usage_from_openai(response)
                return {
                    "insight_report": insight_text,
                    "final_report": _build_final_report(state, insight_text),
                    "report_generated_at": now_iso,
                    "errors": [],
                    "llm_usage": [make_usage_record("openai", "gpt-4o-mini", in_tok, out_tok, "insight_node")],
                }
            except Exception as e:
                logger.warning(f"[insight_node] GPT-4o-mini 오류: {e}")

        # ── 목업 보고서 (API 키 없을 때) ──────────────────
        logger.info("[insight_node] API 키 없음 → 목업 인사이트 생성")
        rag_count = len(state.get("rag_context", []))
        league_name = meta["name"]
        mock_insight = f"""## 🔍 오늘의 핵심 인사이트
1. **{league_name} 순위 경쟁 지속**: 시즌 막판 치열한 순위 경쟁이 이어지고 있습니다.
2. **주요 이슈**: 이번 기간 수집된 뉴스를 기반으로 한 요약입니다.
3. **이적 시장 동향**: 이적 시장을 앞두고 각 구단의 움직임이 활발합니다.

## ⭐ 주목 선수
- 실제 선수명은 API 키 설정 후 AI 분석에서 확인할 수 있습니다.

## 🏆 {meta['section3']}
시즌 종반 치열한 경쟁이 예상됩니다. RAG 검색 {rag_count}건의 관련 기사에서
다양한 인사이트를 확인하였습니다.

## 📌 에디터 픽
이번 주 가장 주목할 경기는 상위권 팀들의 직접 대결입니다.

*⚠️ 목업 데이터: API 키를 .env에 설정하면 {league_name} 기준 실제 AI 분석이 생성됩니다.*"""

        return {
            "insight_report": mock_insight,
            "final_report": _build_final_report(state, mock_insight),
            "report_generated_at": now_iso,
            "errors": [],
        }

    except (KeyError, TypeError) as e:
        msg = f"[insight_node] State 읽기 오류: {e}"
        logger.error(msg)
        return {
            "insight_report": f"인사이트 생성 실패: {e}",
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "errors": [msg],
        }
    except Exception as e:
        msg = f"[insight_node] 예외 발생: {e}"
        logger.error(msg)
        return {
            "insight_report": f"인사이트 생성 실패: {e}",
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "errors": [msg],
        }


def _build_final_report(state: FootballNewsState, insight_text: str) -> str:
    """
    기존 merge_node 리포트에 인사이트 섹션을 추가하여 최종 리포트를 완성합니다.

    Parameters
    ----------
    state : FootballNewsState
        현재 그래프 상태
    insight_text : str
        insight_node에서 생성된 인사이트 텍스트

    Returns
    -------
    str
        완성된 최종 리포트 마크다운 텍스트
    """
    existing_report = state.get("final_report", "")
    now_str = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일 %H:%M UTC")

    insight_section = f"""
---
## 🔎 AI 통합 인사이트 (RAG + Multi-LLM)
*생성: {now_str}*

{insight_text}
"""
    if existing_report:
        return existing_report + insight_section
    else:
        return f"# ⚽ Football Lens 인사이트 보고서\n{insight_section}"


# =============================================
# 직접 실행 시 단독 테스트
# =============================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    sys.path.insert(0, WEEK2_PATH)
    from state import create_initial_state

    print("=== insight_node 단독 테스트 ===\n")
    state = create_initial_state()
    # 더미 RAG 컨텍스트 주입
    state["rag_context"] = [
        {"id": "dummy_001", "title": "손흥민 재계약", "summary": "토트넘과 협상 중",
         "language": "ko", "source": "dummy", "distance": 0.12},
    ]
    result = insight_node(state)
    print("인사이트 보고서 (처음 500자):")
    print(result.get("insight_report", "")[:500])
