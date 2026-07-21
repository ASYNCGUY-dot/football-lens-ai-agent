# -*- coding: utf-8 -*-
"""
llm_nodes.py
============
LLM 요약/분석 노드 3종

노드별 LLM 배정:
    summarize_korean_node  → Claude (Anthropic)   : 한국어 뉴스 요약
    summarize_english_node → GPT-4o-mini (OpenAI) : 영어 뉴스 요약
    analyze_match_node     → Gemini (Google)       : EPL 경기 데이터 분석

각 노드는:
    1. State에서 필요한 데이터를 꺼냅니다.
    2. 프롬프트를 구성합니다.
    3. LLM API를 호출합니다.
    4. 결과를 State 업데이트 딕셔너리로 반환합니다.

API 키 설정 (.env):
    ANTHROPIC_API_KEY       : Claude API 키
    OPENAI_API_KEY          : OpenAI API 키
    GOOGLE_API_KEY          : Gemini API 키

발급 링크:
    Claude  : https://console.anthropic.com
    OpenAI  : https://platform.openai.com/api-keys
    Gemini  : https://aistudio.google.com/app/apikey
"""

import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from state import FootballNewsState, SummaryResult, MatchAnalysisResult, SentimentResult, MatchPredictionResult

load_dotenv()
logger = logging.getLogger(__name__)


# =============================================
# 공통 유틸리티
# =============================================

def _format_articles_for_prompt(articles: list[dict], max_count: int = 15) -> str:
    """
    기사 목록을 LLM 프롬프트에 넣기 적합한 텍스트로 변환합니다.

    Parameters
    ----------
    articles : list[dict]
        기사 딕셔너리 목록
    max_count : int
        프롬프트에 포함할 최대 기사 수 (토큰 제한 고려)

    Returns
    -------
    str
        번호가 매겨진 기사 목록 텍스트
    """
    selected = articles[:max_count]
    lines = []
    for i, a in enumerate(selected, start=1):
        title = a.get("title", "")
        summary = a.get("summary", "")
        source = a.get("source_name", "")
        pub = ""
        if a.get("published_at"):
            try:
                pub = str(a["published_at"])[:10]  # YYYY-MM-DD만
            except Exception:
                pass
        lines.append(f"{i}. [{source}] {title}")
        if summary:
            lines.append(f"   요약: {summary[:150]}")
        if pub:
            lines.append(f"   날짜: {pub}")
        lines.append("")
    return "\n".join(lines)


def _format_matches_for_prompt(matches: list[dict]) -> str:
    """EPL 경기 결과를 프롬프트용 텍스트로 변환합니다."""
    lines = []
    for m in matches:
        date = str(m.get("utc_date", ""))[:10]
        home = m.get("home_team_name", "?")
        away = m.get("away_team_name", "?")
        hs = m.get("home_score")
        as_ = m.get("away_score")
        score = f"{hs}-{as_}" if hs is not None else "미정"
        winner = m.get("winner", "")
        winner_str = ""
        if winner == "HOME_TEAM":
            winner_str = f"({home} 승)"
        elif winner == "AWAY_TEAM":
            winner_str = f"({away} 승)"
        elif winner == "DRAW":
            winner_str = "(무승부)"
        lines.append(f"- {date} | {home} {score} {away} {winner_str}")
    return "\n".join(lines)


def _format_standings_for_prompt(standings: list[dict], top_n: int = 10) -> str:
    """순위표를 프롬프트용 텍스트로 변환합니다."""
    lines = ["순위 | 팀 | 경기 | 승 | 무 | 패 | 득실 | 승점"]
    lines.append("-" * 50)
    for row in standings[:top_n]:
        lines.append(
            f"{row.get('rank', '?'):2}위 | {row.get('team_name', '?'):25s} | "
            f"{row.get('played', 0):2}경기 | {row.get('won', 0)}승 {row.get('draw', 0)}무 {row.get('lost', 0)}패 | "
            f"{row.get('goal_diff', 0):+d} | {row.get('points', 0)}점"
        )
    return "\n".join(lines)


def _clean_api_key(key: str | None) -> str:
    """
    환경변수에서 읽은 API 키를 정제합니다.
    - 앞뒤 따옴표/공백 제거
    - 한국어 등 비ASCII 문자 포함 시 빈 문자열 반환 (플레이스홀더 감지)
    - 너무 짧은 값(<10자)은 빈 문자열 반환
    """
    if not key:
        return ""
    key = key.strip().strip('"').strip("'")
    try:
        key.encode("ascii")        # 한국어 플레이스홀더 감지
    except UnicodeEncodeError:
        return ""                  # 한글 포함 → 플레이스홀더로 간주
    if len(key) < 10:
        return ""
    return key


def _now_iso() -> str:
    """
    현재 UTC 시각을 ISO 8601 형식 문자열로 반환합니다.

    Returns
    -------
    str
        예: "2026-06-23T10:30:00.123456+00:00"
    """
    return datetime.now(timezone.utc).isoformat()


# =============================================
# 노드 ④: 국내 뉴스 요약 (Claude)
# =============================================

def summarize_korean_node(state: FootballNewsState) -> dict:
    """
    한국어 축구 뉴스를 Claude API로 요약합니다.

    사용 모델: claude-3-5-haiku-20241022 (빠르고 저렴, 한국어 우수)
    대안 모델: claude-opus-4-8 (더 정밀한 요약이 필요할 때)

    프롬프트 전략:
        - System: 역할 + 출력 형식 지정
        - User: 실제 기사 목록 전달
        - 출력: 3~5문단 요약 + 주요 토픽 키워드 목록

    State 업데이트:
        korean_summary : SummaryResult 딕셔너리
    """
    articles = state.get("korean_articles", [])
    logger.info(f"[summarize_korean_node] 시작 | 기사 {len(articles)}건")

    # ── 프롬프트 구성 (공통) ───────────────────────────────
    articles_text = _format_articles_for_prompt(articles, max_count=15)

    today_str = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일")

    system_prompt = f"""당신은 축구 전문 뉴스 에디터입니다.
오늘 날짜: {today_str}
제공된 국내 축구 뉴스 기사들을 분석하여 독자가 빠르게 핵심을 파악할 수 있도록 요약합니다.

출력 규칙:
1. 한국어로 작성하세요.
2. 3~5개 문단으로 요약하세요. 각 문단은 하나의 주요 주제를 다룹니다.
3. 중요한 선수 이름, 팀 이름, 경기 결과는 굵게(**) 표시하세요.
4. ★ 팩트 vs 루머 구분:
   - 경기 결과·공식 발표 등 확인된 사실 → 그대로 서술
   - 이적설·협상중·가능성 등 미확인 정보 → 반드시 "~설이 있다", "~가능성이 거론된다"처럼 서술
5. 마지막에 '주요 토픽:' 라벨 뒤에 쉼표로 구분된 키워드 5개를 나열하세요.
6. 광고성 내용이나 기사 메타데이터(날짜, 출처명)는 요약에 포함하지 마세요.
7. ★ 제공된 기사에 없는 내용을 절대 추가하지 마세요. 기사에 없으면 쓰지 마세요."""

    user_prompt = f"""다음은 {today_str} 기준 수집된 국내 축구 뉴스 기사 {len(articles)}건입니다.
팩트와 루머를 구분하여 핵심 내용을 요약해 주세요.

{'='*50}
{articles_text}
{'='*50}

위 기사들을 시스템 지시에 따라 요약해 주세요."""

    def _parse_topics(text: str) -> list:
        for line in text.split("\n"):
            if line.strip().startswith("주요 토픽:"):
                raw = line.split(":", 1)[-1].strip()
                return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    # ── ① Anthropic (Claude) 시도 ─────────────────────────
    anthropic_key = _clean_api_key(os.getenv("ANTHROPIC_API_KEY"))
    if anthropic_key:
        model_name = "claude-3-5-haiku-20241022"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model=model_name,
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            response_text = response.content[0].text
            key_topics = _parse_topics(response_text)
            logger.info(f"[summarize_korean_node] Claude 응답 완료 | 토픽: {key_topics}")
            return {
                "korean_summary": SummaryResult(
                    model_used=model_name,
                    articles_count=len(articles),
                    summary_text=response_text,
                    key_topics=key_topics,
                    generated_at=_now_iso(),
                    error=None,
                )
            }
        except Exception as e:
            logger.warning(f"[summarize_korean_node] Claude 실패, 폴백 시도: {e}")

    # ── ② OpenAI (GPT-4o-mini) 폴백 ──────────────────────
    openai_key = _clean_api_key(os.getenv("OPENAI_API_KEY"))
    if openai_key:
        model_name = "gpt-4o-mini"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=model_name,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            response_text = response.choices[0].message.content
            key_topics = _parse_topics(response_text)
            logger.info(f"[summarize_korean_node] OpenAI 폴백 응답 완료 | 토픽: {key_topics}")
            return {
                "korean_summary": SummaryResult(
                    model_used=f"{model_name}(폴백)",
                    articles_count=len(articles),
                    summary_text=response_text,
                    key_topics=key_topics,
                    generated_at=_now_iso(),
                    error=None,
                )
            }
        except Exception as e:
            logger.warning(f"[summarize_korean_node] OpenAI 폴백 실패: {e}")

    # ── ③ Google Gemini 폴백 ──────────────────────────────
    google_key = _clean_api_key(os.getenv("GOOGLE_API_KEY"))
    if google_key:
        model_name = "gemini-1.5-flash"
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
            response = model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(max_output_tokens=1500, temperature=0.3),
            )
            response_text = response.text
            key_topics = _parse_topics(response_text)
            logger.info(f"[summarize_korean_node] Gemini 폴백 응답 완료 | 토픽: {key_topics}")
            return {
                "korean_summary": SummaryResult(
                    model_used=f"{model_name}(폴백)",
                    articles_count=len(articles),
                    summary_text=response_text,
                    key_topics=key_topics,
                    generated_at=_now_iso(),
                    error=None,
                )
            }
        except Exception as e:
            logger.warning(f"[summarize_korean_node] Gemini 폴백 실패: {e}")

    # ── ④ 모든 API 키 없음 → Mock ─────────────────────────
    logger.warning("모든 LLM API 키 없음 → Mock 응답 반환")
    return {
        "korean_summary": SummaryResult(
            model_used="mock",
            articles_count=len(articles),
            summary_text=(
                "[API 키 미설정] 국내 뉴스 요약을 생성하려면 아래 중 하나의 API 키가 필요합니다.\n\n"
                "- `ANTHROPIC_API_KEY` → https://console.anthropic.com\n"
                "- `OPENAI_API_KEY` → https://platform.openai.com/api-keys\n"
                "- `GOOGLE_API_KEY` → https://aistudio.google.com/app/apikey\n\n"
                "`week2/.env` 파일에 입력하세요."
            ),
            key_topics=["API키필요"],
            generated_at=_now_iso(),
            error=None,
        )
    }


# =============================================
# 노드 ⑤: 해외 뉴스 요약 (GPT-4o-mini)
# =============================================

def summarize_english_node(state: FootballNewsState) -> dict:
    """
    영어 축구 뉴스를 GPT-4o-mini로 요약합니다.

    사용 모델: gpt-4o-mini (빠르고 저렴, 영어 요약 우수)
    대안 모델: gpt-4o (더 정밀한 분석이 필요할 때)

    프롬프트 전략:
        - 영어로 요약 후 한국어로도 핵심 1줄 제공 (이중 언어 출력)
        - Premier League 중심 토픽 강조
        - Key Topics는 영어 키워드로 추출

    State 업데이트:
        english_summary : SummaryResult 딕셔너리
    """
    articles = state.get("english_articles", [])
    logger.info(f"[summarize_english_node] 시작 | 기사 {len(articles)}건")

    api_key = _clean_api_key(os.getenv("OPENAI_API_KEY"))
    if not api_key:
        logger.warning("OPENAI_API_KEY 없음 또는 플레이스홀더 → Mock 응답 반환")
        return {
            "english_summary": SummaryResult(
                model_used="mock",
                articles_count=len(articles),
                summary_text="[Mock] OpenAI API 키가 설정되지 않았습니다.\n\n`week2/.env` 파일에 `OPENAI_API_KEY=sk-proj-...` 를 입력하세요.\n\n발급: https://platform.openai.com/api-keys",
                key_topics=["API key required"],
                generated_at=_now_iso(),
                error=None,
            )
        }

    articles_text = _format_articles_for_prompt(articles, max_count=15)

    # System 프롬프트
    system_prompt = """You are a professional football news editor specializing in the English Premier League and European football.
Analyze the provided English football news articles and create a concise summary for Korean football fans.

Output rules:
1. Write the main summary in ENGLISH (3-5 paragraphs).
2. After the English summary, add a section titled '## 한국어 핵심 요약' with a 2-3 sentence Korean summary of the most important points.
3. Bold (**) important player names, team names, and match results.
4. At the end, add 'Key Topics:' followed by 5 comma-separated English keywords.
   Example: Key Topics: Premier League, Erling Haaland, Manchester City, Champions League, injury
5. Do not fabricate information. Only use content from the provided articles."""

    # User 프롬프트
    user_prompt = f"""Here are {len(articles)} English football news articles collected today.
Please summarize the key highlights.

{'='*50}
{articles_text}
{'='*50}

Please summarize following the system instructions."""

    model_name = "gpt-4o-mini"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model_name,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        response_text = response.choices[0].message.content

        # 'Key Topics:' 파싱
        key_topics = []
        for line in response_text.split("\n"):
            if line.strip().startswith("Key Topics:"):
                topics_raw = line.split(":", 1)[-1].strip()
                key_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
                break

        logger.info(f"[summarize_english_node] GPT 응답 완료 | 토픽: {key_topics}")

        return {
            "english_summary": SummaryResult(
                model_used=model_name,
                articles_count=len(articles),
                summary_text=response_text,
                key_topics=key_topics,
                generated_at=_now_iso(),
                error=None,
            )
        }

    except Exception as e:
        logger.warning(f"[summarize_english_node] OpenAI 오류, Gemini 폴백 시도: {e}")

    # ── ② Google Gemini 폴백 ──────────────────────────────
    google_key = _clean_api_key(os.getenv("GOOGLE_API_KEY"))
    if google_key:
        gemini_model = "gemini-1.5-flash"
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel(
                model_name=gemini_model,
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1500, temperature=0.3
                ),
            )
            response_text = response.text
            key_topics = []
            for line in response_text.split("\n"):
                if line.strip().startswith("Key Topics:"):
                    key_topics = [t.strip() for t in line.split(":", 1)[-1].split(",") if t.strip()]
                    break
            logger.info(f"[summarize_english_node] Gemini 폴백 완료 | 토픽: {key_topics}")
            return {
                "english_summary": SummaryResult(
                    model_used=f"{gemini_model}(폴백)",
                    articles_count=len(articles),
                    summary_text=response_text,
                    key_topics=key_topics,
                    generated_at=_now_iso(),
                    error=None,
                )
            }
        except Exception as e2:
            logger.warning(f"[summarize_english_node] Gemini 폴백 실패: {e2}")

    # ── ③ 모든 API 실패 → Mock ────────────────────────────
    logger.warning("[summarize_english_node] 모든 LLM 실패 → Mock 응답")
    return {
        "english_summary": SummaryResult(
            model_used="mock",
            articles_count=len(articles),
            summary_text=(
                "[Mock] OpenAI API 오류 및 Gemini 폴백도 실패했습니다.\n\n"
                "API 키를 `week2/.env` 파일에서 확인하세요."
            ),
            key_topics=[],
            generated_at=_now_iso(),
            error="All LLM providers failed",
        ),
        "errors": ["summarize_english_node: All LLM providers failed"],
    }


# =============================================
# 노드 ⑥: 경기 데이터 분석 (Gemini)
# =============================================

def analyze_match_node(state: FootballNewsState) -> dict:
    """
    EPL 경기 결과와 순위표를 Gemini API로 분석합니다.

    사용 모델: gemini-1.5-flash (빠른 응답, 구조화 데이터 분석 우수)
    대안 모델: gemini-1.5-pro (더 심층적인 전술 분석이 필요할 때)

    프롬프트 전략:
        - 경기 결과 + 순위표를 구조화된 텍스트로 전달
        - 주목할 경기 선별 (대역전, 다득점, 무득점 등)
        - 순위 변동 분석
        - 다음 경기 전망 포함

    State 업데이트:
        match_analysis : MatchAnalysisResult 딕셔너리
    """
    matches = state.get("raw_matches", [])
    standings = state.get("raw_standings", [])
    league_code = state.get("config", {}).get("league", "PL")
    logger.info(f"[analyze_match_node] 시작 | 리그:{league_code} 경기 {len(matches)}건, 순위표 {len(standings)}팀")

    api_key = _clean_api_key(os.getenv("GOOGLE_API_KEY"))
    if not api_key:
        logger.warning("GOOGLE_API_KEY 없음 또는 플레이스홀더 → Mock 응답 반환")
        return {
            "match_analysis": MatchAnalysisResult(
                model_used="mock",
                matches_count=len(matches),
                analysis_text="[Mock] Google API 키가 설정되지 않았습니다.\n\n`week2/.env` 파일에 `GOOGLE_API_KEY=AIza...` 를 입력하세요.\n\n발급: https://aistudio.google.com/app/apikey",
                notable_results=["API 키 설정 필요"],
                standings_summary="순위표 조회 불가",
                generated_at=_now_iso(),
                error=None,
            )
        }

    # ── WC: 경기 데이터 없으면 뉴스 기반 분석 ─────────────────
    is_wc = (league_code == "WC")
    if is_wc and not matches:
        all_articles = state.get("korean_articles", []) + state.get("english_articles", [])
        WC_KW = ["월드컵", "worldcup", "world cup", "fifa", "조별", "16강", "8강", "4강", "결승"]
        wc_articles = [
            a for a in all_articles
            if any(kw in (a.get("title", "") + a.get("summary", "")).lower() for kw in WC_KW)
        ] or all_articles[:20]

        articles_text = _format_articles_for_prompt(wc_articles, max_count=20)
        today_str = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일")

        system_prompt = f"""당신은 2026 FIFA 월드컵 전문 분석가입니다.
오늘 날짜: {today_str}
제공된 뉴스 기사들을 바탕으로 한국 축구 팬들을 위한 월드컵 분석을 제공합니다.

출력 규칙:
1. 한국어로 작성하세요.
2. 다음 구조로 작성하세요:
   ### 월드컵 주요 경기 & 결과 분석
   (뉴스에서 파악된 경기 결과 및 주요 장면)

   ### 주목할 팀 & 선수 트렌드
   (조별리그 성적, 주목받는 팀·선수)

   ### 한국 대표팀 동향
   (한국팀 관련 뉴스가 있으면 별도 분석)

3. 굵게(**) 중요한 팀명·선수명·결과를 표시하세요.
4. 뉴스에 없는 내용은 추측하지 마세요."""

        user_prompt = f"""다음은 {today_str} 기준 수집된 2026 FIFA 월드컵 관련 뉴스 기사 {len(wc_articles)}건입니다.

{'='*50}
{articles_text}
{'='*50}

위 뉴스를 바탕으로 월드컵 경기 분석을 작성해 주세요."""

        model_name = "gemini-1.5-flash"
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            m = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
            resp = m.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(max_output_tokens=1500),
            )
            text = resp.text
            logger.info("[analyze_match_node] WC 뉴스 기반 Gemini 분석 완료")
            return {
                "match_analysis": MatchAnalysisResult(
                    model_used=model_name,
                    matches_count=len(wc_articles),
                    analysis_text=text,
                    notable_results=[],
                    standings_summary="뉴스 기반 분석 (API 경기 데이터 미제공)",
                    generated_at=_now_iso(),
                    error=None,
                )
            }
        except Exception as e:
            logger.warning(f"[analyze_match_node] WC 뉴스 분석 실패: {e}")
            return {
                "match_analysis": MatchAnalysisResult(
                    model_used="error",
                    matches_count=0,
                    analysis_text=f"월드컵 분석 실패: {e}",
                    notable_results=[],
                    standings_summary="",
                    generated_at=_now_iso(),
                    error=str(e),
                )
            }

    matches_text = _format_matches_for_prompt(matches)
    standings_text = _format_standings_for_prompt(standings, top_n=10)

    # ── 리그별 시스템 프롬프트 ─────────────────────────────────
    _LEAGUE_NAMES = {
        "PL": "EPL 프리미어리그", "PD": "라리가", "BL1": "분데스리가",
        "SA": "세리에A", "FL1": "리그앙", "KL1": "K리그1",
    }
    league_display = _LEAGUE_NAMES.get(league_code, "축구 리그")

    system_prompt = f"""당신은 {league_display} 전문 데이터 분석가입니다.
제공된 최근 경기 결과와 순위표를 분석하여 한국 축구 팬들을 위한 인사이트를 제공합니다.

출력 규칙:
1. 한국어로 작성하세요.
2. 분석 내용은 다음 구조를 따르세요:
   ### 이번 주 경기 하이라이트
   (주목할 경기 결과 3~5건 분석)

   ### 순위 변동 분석
   (현재 상위 5팀 상황, 강등권 팀 상황)

   ### 주목할 팀/선수 트렌드
   (최근 폼이 좋거나 나쁜 팀, 주목할 통계)

3. 굵게(**) 중요한 팀명과 결과를 표시하세요.
4. 마지막에 '주목 경기:' 라벨 뒤에 쉼표로 구분된 주목 경기 3건을 나열하세요.
5. 그 다음 줄에 '순위 요약:' 라벨 뒤에 한 줄로 현재 순위 상황을 요약하세요.
6. 데이터에 없는 정보는 추측하지 마세요."""

    # User 프롬프트
    user_prompt = f"""다음은 최근 {league_display} 경기 결과와 현재 순위표입니다.

=== 최근 경기 결과 ({len(matches)}건) ===
{matches_text if matches_text else "경기 결과 없음"}

=== 현재 {league_display} 순위표 (상위 10팀) ===
{standings_text if standings_text else "순위표 없음"}

위 데이터를 시스템 지시에 따라 분석해 주세요."""

    model_name = "gemini-1.5-flash"
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )

        response = model.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1500,
                temperature=0.3,     # 낮은 온도 = 더 사실 기반 응답
            ),
        )
        response_text = response.text

        # '주목 경기:' 파싱
        notable_results = []
        standings_summary = ""
        for line in response_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("주목 경기:"):
                raw = stripped.split(":", 1)[-1].strip()
                notable_results = [r.strip() for r in raw.split(",") if r.strip()]
            elif stripped.startswith("순위 요약:"):
                standings_summary = stripped.split(":", 1)[-1].strip()

        logger.info(f"[analyze_match_node] Gemini 응답 완료 | 주목경기: {notable_results}")

        return {
            "match_analysis": MatchAnalysisResult(
                model_used=model_name,
                matches_count=len(matches),
                analysis_text=response_text,
                notable_results=notable_results,
                standings_summary=standings_summary,
                generated_at=_now_iso(),
                error=None,
            )
        }

    except Exception as e:
        error_msg = f"Gemini API 오류: {e}"
        logger.error(error_msg)
        return {
            "match_analysis": MatchAnalysisResult(
                model_used=model_name,
                matches_count=len(matches),
                analysis_text="",
                notable_results=[],
                standings_summary="",
                generated_at=_now_iso(),
                error=error_msg,
            ),
            "errors": [error_msg],
        }


# =============================================
# 노드 ⑦: 감정 분석 + 이적 루머 분류
# =============================================

def sentiment_analysis_node(state: FootballNewsState) -> dict:
    """
    수집된 기사에 대해 감정 분석 + 이적 루머 분류를 수행합니다.

    - sentiment_score: -1.0(매우부정) ~ 1.0(매우긍정)
    - sentiment_label: "긍정" / "중립" / "부정"
    - is_transfer_rumor: 이적 루머 여부
    - rumor_players / rumor_clubs: 관련 선수/구단

    LLM을 배치 방식으로 호출해 기사 20건까지 한 번에 처리합니다.
    API 키가 없으면 키워드 기반 규칙으로 폴백합니다.
    """
    all_articles = (
        state.get("korean_articles", []) + state.get("english_articles", [])
    )
    logger.info(f"[sentiment_analysis_node] 시작 | 기사 {len(all_articles)}건")

    if not all_articles:
        return {"article_sentiments": [], "transfer_rumors": []}

    # ── 규칙 기반 폴백 (LLM 없을 때) ──────────────────────
    def _rule_based_sentiment(article: dict) -> SentimentResult:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        POSITIVE_KW = ["승리", "우승", "골", "해트트릭", "복귀", "활약", "완승", "최고", "win", "goal", "great", "victory"]
        NEGATIVE_KW = ["패배", "부진", "부상", "퇴장", "실점", "강등", "위기", "논란", "lose", "injury", "crisis", "poor"]
        RUMOR_KW   = ["이적설", "관심", "협상", "제안", "영입 목표", "transfer", "linked", "target", "bid", "move"]
        PLAYER_KW  = ["손흥민", "이강인", "황희찬", "김민재", "홀란드", "살라", "엠바페", "벨링엄",
                      "haaland", "salah", "mbappe", "bellingham", "yamal", "kane"]
        CLUB_KW    = ["맨시티", "리버풀", "아스날", "첼시", "토트넘", "맨유", "레알", "바르셀로나",
                      "city", "liverpool", "arsenal", "chelsea", "tottenham", "united", "real", "barcelona"]

        pos = sum(1 for k in POSITIVE_KW if k in text)
        neg = sum(1 for k in NEGATIVE_KW if k in text)
        score = round(min(max((pos - neg) / max(pos + neg, 1), -1.0), 1.0), 2)
        label = "긍정" if score > 0.1 else ("부정" if score < -0.1 else "중립")
        is_rumor = any(k in text for k in RUMOR_KW)
        players = [p for p in PLAYER_KW if p in text]
        clubs   = [c for c in CLUB_KW   if c in text]
        return SentimentResult(
            article_id=article.get("article_id", ""),
            title=article.get("title", ""),
            sentiment_score=score,
            sentiment_label=label,
            is_transfer_rumor=is_rumor,
            rumor_players=players[:3],
            rumor_clubs=clubs[:3],
        )

    # ── LLM 배치 분석 ──────────────────────────────────────
    def _llm_batch_sentiment(articles: list[dict], api_key_type: str) -> list[SentimentResult] | None:
        import json
        batch = articles[:20]
        lines = []
        for i, a in enumerate(batch):
            title = (a.get("title") or "")[:100]
            summary = (a.get("summary") or "")[:80]
            lines.append(f"{i}: [{a.get('article_id','')}] {title} | {summary}")
        articles_text = "\n".join(lines)

        system_prompt = """You are a football news sentiment analyzer. For each article (index: id | title | summary), return JSON array.
Each item: {"idx": <int>, "score": <float -1.0 to 1.0>, "label": "<긍정|중립|부정>", "is_rumor": <bool>, "players": [<str>], "clubs": [<str>]}
Rules:
- score: -1.0=very negative, 0=neutral, 1.0=very positive (team/player performance perspective)
- is_rumor: true if transfer speculation, linked, bid, negotiations mentioned
- players: player names mentioned in transfer context (max 3)
- clubs: club names mentioned in transfer context (max 3)
Return ONLY valid JSON array, no markdown."""

        user_prompt = f"Analyze these {len(batch)} football news articles:\n\n{articles_text}\n\nReturn JSON array:"

        try:
            if api_key_type == "anthropic":
                import anthropic
                key = _clean_api_key(os.getenv("ANTHROPIC_API_KEY"))
                client = anthropic.Anthropic(api_key=key)
                resp = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw = resp.content[0].text
            elif api_key_type == "openai":
                from openai import OpenAI
                key = _clean_api_key(os.getenv("OPENAI_API_KEY"))
                client = OpenAI(api_key=key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=2000,
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": user_prompt}],
                )
                raw = resp.choices[0].message.content
            else:
                return None

            # JSON 추출
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json").strip()
            parsed = json.loads(raw)

            results = []
            for item in parsed:
                idx = item.get("idx", 0)
                if idx >= len(batch):
                    continue
                a = batch[idx]
                results.append(SentimentResult(
                    article_id=a.get("article_id", ""),
                    title=a.get("title", ""),
                    sentiment_score=float(item.get("score", 0)),
                    sentiment_label=item.get("label", "중립"),
                    is_transfer_rumor=bool(item.get("is_rumor", False)),
                    rumor_players=item.get("players", [])[:3],
                    rumor_clubs=item.get("clubs", [])[:3],
                ))
            return results
        except Exception as e:
            logger.warning(f"[sentiment_analysis_node] LLM 배치 실패 ({api_key_type}): {e}")
            return None

    # API 키 우선순위로 시도
    sentiments = None
    for api_type in ["anthropic", "openai"]:
        key_env = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}[api_type]
        if _clean_api_key(os.getenv(key_env)):
            sentiments = _llm_batch_sentiment(all_articles, api_type)
            if sentiments:
                logger.info(f"[sentiment_analysis_node] {api_type} 분석 완료 {len(sentiments)}건")
                break

    # LLM 실패 시 규칙 기반
    if not sentiments:
        logger.info("[sentiment_analysis_node] 규칙 기반 감정 분석 사용")
        sentiments = [_rule_based_sentiment(a) for a in all_articles[:50]]

    # 이적 루머 기사 추출
    rumor_articles = []
    sentiment_by_id = {s["article_id"]: s for s in sentiments}
    for a in all_articles:
        sid = a.get("article_id", "")
        sent = sentiment_by_id.get(sid)
        if sent and sent.get("is_transfer_rumor"):
            rumor_articles.append({**a, "sentiment": sent})

    logger.info(f"[sentiment_analysis_node] 완료 | 감정: {len(sentiments)}건, 이적루머: {len(rumor_articles)}건")
    return {
        "article_sentiments": sentiments,
        "transfer_rumors": rumor_articles,
    }


# =============================================
# 노드 ⑧: 경기 예측
# =============================================

def match_prediction_node(state: FootballNewsState) -> dict:
    """
    다가오는 경기를 뉴스 감정 + 최근 경기 데이터 기반으로 예측합니다.

    - 뉴스 감정 트렌드 (팀별 긍정/부정 기사 비율)
    - 최근 경기 결과 (폼)
    - 순위표 데이터

    주의: 예측은 참고 목적이며 정확성을 보장하지 않습니다.
    """
    upcoming = state.get("upcoming_matches", [])
    sentiments = state.get("article_sentiments", [])
    standings = state.get("raw_standings", [])
    league_code = state.get("config", {}).get("league", "PL")

    logger.info(f"[match_prediction_node] 시작 | 예정경기 {len(upcoming)}건 | 리그 {league_code}")

    # 예정 경기 없을 때: WC이면 뉴스 기반 예측 시도, 아니면 skip
    if not upcoming:
        if league_code != "WC":
            return {"match_prediction": MatchPredictionResult(
                model_used="skip", prediction_text="예정 경기 데이터 없음",
                predictions=[], generated_at=_now_iso(), error=None,
            )}
        # WC: 뉴스 기사만으로 월드컵 전망 분석
        logger.info("[match_prediction_node] WC 뉴스 기반 분석 시작")
        all_articles = state.get("raw_articles", [])
        wc_titles = [
            f"- {a.get('title','')[:120]}"
            for a in all_articles[:30]
            if any(kw in f"{a.get('title','')} {a.get('summary','')}".lower()
                   for kw in ["월드컵", "world cup", "worldcup", "2026 fifa", "korea", "한국"])
        ]
        if not wc_titles:
            wc_titles = [f"- {a.get('title','')[:120]}" for a in all_articles[:15]]
        articles_text = "\n".join(wc_titles) or "수집된 기사 없음"

        wc_system = """당신은 2026 FIFA 월드컵 분석 전문가입니다.
제공된 뉴스 기사 제목을 바탕으로 주요 팀 동향과 경기 전망을 분석하세요.

출력 형식:
## 🌍 2026 FIFA 월드컵 주요 분석
(뉴스 기반 팀별 동향 3~5개 bullet)

## 🔮 주목할 경기 전망
(관련 팀 2~3경기 예측, 형식: **팀A vs 팀B** - 전망 1~2줄)

## ⭐ 핵심 선수 주목
(주요 선수 2~3명 간단 언급)

마지막에: "※ 예측은 뉴스 기반 참고 정보이며 실제 결과를 보장하지 않습니다."

한국어로 작성하세요."""

        wc_user = f"다음 2026 FIFA 월드컵 관련 뉴스 기사 제목을 분석해주세요:\n\n{articles_text}"

        for api_type, env_var, model_id in [
            ("anthropic", "ANTHROPIC_API_KEY", "claude-3-5-haiku-20241022"),
            ("openai",    "OPENAI_API_KEY",    "gpt-4o-mini"),
            ("google",    "GOOGLE_API_KEY",    "gemini-1.5-flash"),
        ]:
            key = _clean_api_key(os.getenv(env_var))
            if not key:
                continue
            try:
                if api_type == "anthropic":
                    import anthropic
                    client = anthropic.Anthropic(api_key=key)
                    resp = client.messages.create(
                        model=model_id, max_tokens=1200,
                        system=wc_system,
                        messages=[{"role": "user", "content": wc_user}],
                    )
                    text = resp.content[0].text
                elif api_type == "openai":
                    from openai import OpenAI
                    client = OpenAI(api_key=key)
                    resp = client.chat.completions.create(
                        model=model_id, max_tokens=1200,
                        messages=[{"role": "system", "content": wc_system},
                                  {"role": "user", "content": wc_user}],
                    )
                    text = resp.choices[0].message.content
                else:
                    import google.generativeai as genai
                    genai.configure(api_key=key)
                    m = genai.GenerativeModel(model_name=model_id, system_instruction=wc_system)
                    resp = m.generate_content(wc_user)
                    text = resp.text
                logger.info(f"[match_prediction_node] WC 뉴스 분석 완료 ({api_type})")
                return {"match_prediction": MatchPredictionResult(
                    model_used=model_id,
                    prediction_text=text,
                    predictions=[],
                    generated_at=_now_iso(),
                    error=None,
                )}
            except Exception as e:
                logger.warning(f"[match_prediction_node] WC 뉴스 분석 실패 ({api_type}): {e}")

        return {"match_prediction": MatchPredictionResult(
            model_used="skip",
            prediction_text="월드컵 예측을 생성하려면 LLM API 키가 필요합니다.",
            predictions=[], generated_at=_now_iso(), error=None,
        )}

    # 팀별 감정 집계
    team_sentiment: dict[str, list[float]] = {}
    for s in sentiments:
        title = (s.get("title") or "").lower()
        TEAMS_MAP = {
            "맨시티": ["맨시티", "manchester city", "man city"],
            "리버풀": ["리버풀", "liverpool"],
            "아스날": ["아스날", "arsenal"],
            "첼시":   ["첼시", "chelsea"],
            "토트넘": ["토트넘", "tottenham", "spurs"],
            "맨유":   ["맨유", "manchester united", "man utd"],
        }
        for team, aliases in TEAMS_MAP.items():
            if any(alias in title for alias in aliases):
                team_sentiment.setdefault(team, []).append(s.get("sentiment_score", 0))

    team_avg_sentiment = {
        t: round(sum(v) / len(v), 2) for t, v in team_sentiment.items() if v
    }

    # 순위표 상위 10팀
    standings_text = _format_standings_for_prompt(standings, top_n=10)

    # 예정 경기 텍스트
    upcoming_text = "\n".join(
        f"- {m.get('utc_date','')[:10]} | {m.get('home_team_name','?')} vs {m.get('away_team_name','?')}"
        for m in upcoming[:8]
    )

    # 감정 텍스트
    sentiment_text = "\n".join(
        f"- {t}: 평균 감정 {v:+.2f}" for t, v in team_avg_sentiment.items()
    ) or "감정 데이터 없음"

    system_prompt = (
        "당신은 EPL 데이터 분석가입니다.\n"
        "제공된 순위표, 팀별 뉴스 감정 점수를 바탕으로 다가오는 경기를 예측합니다.\n\n"
        "출력 형식 (반드시 준수):\n"
        "각 경기마다 다음 형식으로 작성:\n"
        "**[홈팀] vs [원정팀]**\n"
        "- 예측: [홈팀 승 / 무승부 / 원정팀 승]\n"
        "- 신뢰도: [높음 / 중간 / 낮음]\n"
        "- 근거: (2줄 이내, 순위/폼/뉴스 감정 기반)\n\n"
        "마지막에 면책문구: "
        "'※ 위 예측은 데이터 기반 참고 정보이며 실제 결과를 보장하지 않습니다.'\n\n"
        "제공된 데이터에 없는 정보는 추측하지 마세요."
    )

    user_prompt = (
        f"다음은 현재 리그 데이터와 예정 경기 목록입니다.\n\n"
        f"=== 현재 순위표 (상위 10팀) ===\n"
        f"{standings_text or '순위표 없음'}\n\n"
        f"=== 예정 경기 (향후 7일) ===\n"
        f"{upcoming_text or '예정 경기 없음'}\n\n"
        f"=== 팀별 뉴스 감정 지수 ===\n"
        f"{sentiment_text}\n\n"
        "위 데이터를 기반으로 예정 경기를 예측해 주세요."
    )

    for api_type, env_var, model_id in [
        ("anthropic", "ANTHROPIC_API_KEY", "claude-3-5-haiku-20241022"),
        ("openai",    "OPENAI_API_KEY",    "gpt-4o-mini"),
        ("google",    "GOOGLE_API_KEY",    "gemini-1.5-flash"),
    ]:
        key = _clean_api_key(os.getenv(env_var))
        if not key:
            continue
        try:
            if api_type == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                resp = client.messages.create(
                    model=model_id, max_tokens=1500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text = resp.content[0].text
            elif api_type == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=key)
                resp = client.chat.completions.create(
                    model=model_id, max_tokens=1500,
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": user_prompt}],
                )
                text = resp.choices[0].message.content
            else:
                import google.generativeai as genai
                genai.configure(api_key=key)
                m = genai.GenerativeModel(model_name=model_id, system_instruction=system_prompt)
                resp = m.generate_content(user_prompt,
                    generation_config=genai.types.GenerationConfig(max_output_tokens=1500))
                text = resp.text

            preds = []
            for ln in text.split("\n"):
                if "vs" in ln.lower() and "**" in ln:
                    match_str = ln.replace("**", "").strip(" -•")
                    preds.append({"match": match_str, "details": ""})

            logger.info(f"[match_prediction_node] {api_type} 완료 | 경기 {len(preds)}건 예측")
            return {"match_prediction": MatchPredictionResult(
                model_used=model_id,
                prediction_text=text,
                predictions=preds,
                generated_at=_now_iso(),
                error=None,
            )}
        except Exception as e:
            logger.warning(f"[match_prediction_node] {api_type} 실패: {e}")

    return {"match_prediction": MatchPredictionResult(
        model_used="mock",
        prediction_text="[API 키 없음] 경기 예측을 생성하려면 LLM API 키가 필요합니다.",
        predictions=[],
        generated_at=_now_iso(),
        error="API key not found",
    )}
