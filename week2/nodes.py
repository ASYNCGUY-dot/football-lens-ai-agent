# -*- coding: utf-8 -*-
"""
nodes.py
========
LangGraph 그래프의 각 노드(node) 함수 뼈대

노드란?
    그래프에서 실제 작업을 수행하는 함수입니다.
    각 노드는 현재 State를 입력으로 받고,
    업데이트할 State 키-값 딕셔너리를 반환합니다.
    LangGraph가 반환값을 현재 State에 자동으로 병합합니다.

노드 목록:
    1. collect_node       - 뉴스 + 경기 데이터 수집
    2. preprocess_node    - 전처리 (중복 제거, 광고 필터링)
    3. classify_node      - 언어 분류 + 라우팅 플래그 설정
    4. merge_node         - LLM 결과들을 하나의 리포트로 통합

    (LLM 노드 3종은 llm_nodes.py에 별도 정의)
"""

import sys
import os
import logging
from datetime import datetime, timezone

# week1 모듈을 import할 수 있도록 경로 추가
# 실행 위치: week2/ 기준 → ../week1/ 을 sys.path에 추가
WEEK1_PATH = os.path.join(os.path.dirname(__file__), "..", "week1")
if WEEK1_PATH not in sys.path:
    sys.path.insert(0, WEEK1_PATH)

from state import FootballNewsState
from league_registry import LEAGUES as _LEAGUES

logger = logging.getLogger(__name__)

# merge_node에서 리포트 섹션 제목에 쓰는 짧은 리그 표기.
# 예전엔 "EPL 경기 분석"이 리그와 무관하게 하드코딩돼 있어서, K리그·
# 브라질세리에A 등을 선택해도 리포트 본문에 계속 "EPL"이 찍혔다.
# 이제 week1/league_registry.py의 short_name을 그대로 쓴다.
_LEAGUE_SHORT_NAME: dict = {code: meta["short_name"] for code, meta in _LEAGUES.items()}


def _filter_by_league(
    korean_articles: list[dict], english_articles: list[dict], league_code: str,
) -> tuple[list[dict], list[dict]]:
    """
    선택 리그/대회와 무관한 기사를 제외한다.

    RSS(6개 소스, 리그 인식 없음)와 네이버 수집 결과에는 선택 리그와 무관한
    기사가 섞여 있다 — 화면 표시 단계에서만 걸러내면 LLM 요약·감정분석·
    RAG 인덱싱은 이미 오염된 뒤라 소용없어서, 분류 직후 이 시점에서 한 번에
    걸러낸다. 키워드는 week1/naver_collector.py의 LEAGUE_KEYWORD_MAP을
    그대로 재사용한다 — 수집할 때 쓴 키워드와 걸러낼 때 쓰는 키워드가
    다르면(예전 버그가 이랬다) 정작 수집된 관련 기사까지 걸러지는 역효과가
    나므로 반드시 같은 소스를 써야 한다.

    필터 결과가 0건이면 그냥 0건으로 둔다 — 예전엔 "0건이면 필터 없이
    원본을 반환"하는 안전장치가 있었는데, 실제로는 이게 필터를 통째로
    무력화하는 구멍이었다. 예를 들어 브라질세리에A 헤드라인은 실제로
    "브라질세리에A"라는 표현을 잘 안 쓰고 팀명만 쓰는 경우가 많아서
    제목 매칭이 0건이 되기 쉬운데, 그 순간 안전장치가 발동해 완전히
    무관한 기사(브라질 국가대표 월드컵 뉴스 등)까지 전부 통과됐다.
    다운스트림(summarize_*_node 등)은 이미 빈 리스트를 "관련 기사 없음"
    으로 안전하게 처리하도록 만들어뒀으니, 0건이면 정직하게 0건으로
    두는 게 낫다.
    """
    try:
        from collectors.naver_collector import LEAGUE_KEYWORD_MAP
    except ImportError:
        return korean_articles, english_articles

    keywords = LEAGUE_KEYWORD_MAP.get(league_code)
    if not keywords:
        return korean_articles, english_articles
    # 공백 유무 표기 차이("전북현대" 키워드 vs 기사의 "전북 현대")로 매칭이
    # 새는 걸 막기 위해 공백을 제거한 버전도 함께 비교한다.
    keywords_norm = [kw.lower().replace(" ", "") for kw in keywords]

    def _matches(a: dict) -> bool:
        # 제목만 본다 — 요약(summary)까지 포함하면, 실제로는 다른 리그
        # 이야기인데 본문 어딘가에 K리그 club명이 스치듯 언급된 기사까지
        # "K리그 기사"로 잘못 걸러졌다. 예: "황인범, 포르투 입단" 이적
        # 기사가 프로필 설명에 "K리그 FC서울에서 잠시 뛴 뒤..."라는 문장을
        # 포함한다는 이유로 K리그 이적 소식에 뜬 사례. 제목은 기사가 실제로
        # 무엇에 관한 것인지를 훨씬 정확히 반영한다. 수집 키워드(a["keyword"])
        # 도 마찬가지 이유로 애초에 안 본다.
        text = (a.get("title") or "").lower().replace(" ", "")
        return any(kw in text for kw in keywords_norm)

    ko_filtered = [a for a in korean_articles if _matches(a)]
    en_filtered = [a for a in english_articles if _matches(a)]

    logger.info(
        f"[classify_node] 리그 필터({league_code}) | "
        f"국내 {len(korean_articles)}→{len(ko_filtered)}건, 영어 {len(english_articles)}→{len(en_filtered)}건"
    )
    return ko_filtered, en_filtered


# =============================================
# 노드 1: 수집 노드 (collect_node)
# =============================================

def collect_node(state: FootballNewsState) -> dict:
    """
    뉴스 기사와 EPL 경기 데이터를 수집합니다.

    실행 순서:
        1. RSS 피드 수집 (6개 소스)
        2. 네이버 뉴스 API 수집
        3. football-data.org EPL 경기 결과 수집

    State 업데이트 키:
        raw_articles  : 수집된 전체 기사 목록
        raw_matches   : EPL 경기 결과
        raw_standings : EPL 순위표
        errors        : 오류 발생 시 메시지 추가

    Parameters
    ----------
    state : FootballNewsState
        현재 그래프 상태. config에서 설정값을 읽습니다.
        - config["days_back"]              : 수집 기간 (기본 7일)
        - config["max_articles_per_source"]: 소스당 최대 기사 수 (기본 20)

    Returns
    -------
    dict
        업데이트할 State 키-값 딕셔너리
    """
    logger.info(f"[collect_node] 시작 | run_id={state.get('run_id')}")
    config = state.get("config", {})
    days_back = config.get("days_back", 7)

    raw_articles = []
    raw_matches = []
    raw_standings = []
    youtube_videos = []
    reddit_posts = []
    top_scorers = []
    upcoming_matches = []
    worldcup_groups = []
    worldcup_matches = []
    worldcup_scorers = []
    errors = []

    league_code = config.get("league", "PL")
    is_worldcup = (league_code == "WC")

    # ── RSS 수집 ──────────────────────────────────────────
    try:
        from collectors.rss_collector import RSSCollector
        rss_collector = RSSCollector()
        if is_worldcup:
            # 월드컵 전용 RSS 피드 사용
            rss_articles = rss_collector.collect_worldcup_news()
            logger.info(f"[collect_node] 월드컵 RSS 수집: {len(rss_articles)}건")
        else:
            rss_articles = rss_collector.collect_all()
            logger.info(f"[collect_node] RSS 수집: {len(rss_articles)}건")
        raw_articles.extend(rss_articles)
    except Exception as e:
        msg = f"RSS 수집 오류: {e}"
        logger.error(msg)
        errors.append(msg)

    # ── 네이버 뉴스 수집 ──────────────────────────────────
    try:
        from collectors.naver_collector import NaverNewsCollector
        naver_collector = NaverNewsCollector(display=20)
        # 선택된 리그/대회 전용 키워드로 집중 수집한다. 예전엔 월드컵만 이
        # 방식을 쓰고 나머지 리그는 전부 EPL/K리그/월드컵 위주의 고정
        # DEFAULT_KEYWORDS로 검색해서, 예를 들어 브라질세리에A를 선택해도
        # 뉴스는 항상 EPL/월드컵 기사만 나오는 문제가 있었다.
        # collect_league_keywords()는 LEAGUE_KEYWORD_MAP에 없는 리그 코드는
        # 자동으로 DEFAULT_KEYWORDS로 폴백하므로 안전하다.
        naver_articles = naver_collector.collect_league_keywords(league_code)
        logger.info(f"[collect_node] 네이버 수집({league_code}): {len(naver_articles)}건")
        raw_articles.extend(naver_articles)
    except ValueError:
        logger.warning("[collect_node] 네이버 API 키 없음, 건너뜀")
    except Exception as e:
        msg = f"네이버 수집 오류: {e}"
        logger.error(msg)
        errors.append(msg)

    # Reddit 수집기는 제거했다(2026-07-22) — 고정 6개 서브레딧(r/soccer,
    # r/PremierLeague 등)이 항상 EPL/K리그 위주라 다른 리그를 선택해도
    # 무관한 콘텐츠만 나왔고, 화면에도 리그 필터 없이 그대로 노출됐다.
    # 게다가 실제로는 거의 항상 429(rate limit)에 걸려 신뢰할 수 없는
    # 소스였다. reddit_posts는 항상 빈 리스트로 유지한다(state 키
    # 자체는 다른 곳에서 .get()으로 안전하게 참조하므로 스키마는 유지).

    # ── YouTube 영상 수집 ────────────────────────────────
    try:
        from collectors.youtube_collector import YouTubeCollector
        yt_collector = YouTubeCollector()
        youtube_videos = yt_collector.search_football_videos(max_per_query=3, league_code=league_code)
        logger.info(f"[collect_node] YouTube 수집: {len(youtube_videos)}건")
    except Exception as e:
        msg = f"YouTube 수집 오류: {e}"
        logger.warning(msg)

    # ── 리그/대회별 경기 데이터 ──────────────────────────
    if is_worldcup:
        # 2026 FIFA 월드컵 — WC 전용 API 메서드 사용
        try:
            from collectors.football_data_collector import FootballDataCollector
            wc_collector = FootballDataCollector(competition="WC")
            worldcup_groups  = wc_collector.get_worldcup_groups()
            worldcup_matches = wc_collector.get_worldcup_matches(days_back=3, days_ahead=4)
            worldcup_scorers = wc_collector.get_worldcup_scorers(limit=10)
            # raw_matches/raw_standings에도 WC 데이터 매핑 (대시보드 공통 렌더링 지원)
            raw_matches   = worldcup_matches
            raw_standings = worldcup_groups
            top_scorers   = worldcup_scorers
            if not worldcup_matches and not worldcup_groups:
                logger.warning(
                    "[collect_node] 월드컵 API 데이터 없음 — football-data.org 무료 플랜은 "
                    "WC 엔드포인트(403)를 지원하지 않습니다. 뉴스 기반으로만 운영됩니다."
                )
            else:
                logger.info(
                    f"[collect_node] 월드컵 — 그룹:{len(worldcup_groups)}개, "
                    f"경기:{len(worldcup_matches)}건, 득점순위:{len(worldcup_scorers)}명"
                )
        except ValueError:
            logger.warning("[collect_node] 월드컵: football-data API 키 없음, 건너뜀")
        except Exception as e:
            logger.warning(f"[collect_node] 월드컵 데이터 수집 실패 (비중요): {e}")
    else:
        # 일반 리그 (EPL, 라리가, K리그 등)
        try:
            from collectors.football_data_collector import FootballDataCollector
            fd_collector = FootballDataCollector(competition=league_code)
            raw_matches      = fd_collector.get_recent_matches(days_back=days_back)
            raw_standings    = fd_collector.get_standings()
            top_scorers      = fd_collector.get_top_scorers(limit=10)
            upcoming_matches = fd_collector.get_upcoming_matches(days_ahead=7)
            logger.info(
                f"[collect_node] 경기: {len(raw_matches)}건, 순위: {len(raw_standings)}팀, "
                f"득점왕: {len(top_scorers)}명, 예정경기: {len(upcoming_matches)}건"
            )
        except ValueError:
            logger.warning("[collect_node] football-data API 키 없음, 건너뜀")
        except Exception as e:
            msg = f"리그 데이터 수집 오류: {e}"
            logger.error(msg)
            errors.append(msg)

    logger.info(f"[collect_node] 완료 | 총 기사 {len(raw_articles)}건")

    return {
        "raw_articles": raw_articles,
        "raw_matches": raw_matches,
        "raw_standings": raw_standings,
        "youtube_videos": youtube_videos,
        "reddit_posts": reddit_posts,
        "top_scorers": top_scorers,
        "upcoming_matches": upcoming_matches,
        "worldcup_groups":  worldcup_groups,
        "worldcup_matches": worldcup_matches,
        "worldcup_scorers": worldcup_scorers,
        "errors": errors,
    }


# =============================================
# 노드 2: 전처리 노드 (preprocess_node)
# =============================================

def preprocess_node(state: FootballNewsState) -> dict:
    """
    수집된 원시 기사를 전처리합니다.

    수행 작업:
        - 중복 제거 (URL 기반 + Simhash 유사 중복)
        - 광고/스팸 필터링
        - 오래된 기사 제거
        - 언어 감지

    State 업데이트 키:
        raw_articles        : 전처리된 기사로 교체 (덮어쓰기)
        preprocessing_stats : 전처리 통계 딕셔너리

    Parameters
    ----------
    state : FootballNewsState
        raw_articles에서 원시 기사를 읽습니다.
    """
    logger.info(f"[preprocess_node] 시작 | 입력 {len(state.get('raw_articles', []))}건")
    errors = []

    try:
        from preprocessing.preprocessor import ArticlePreprocessor
        config = state.get("config", {})

        preprocessor = ArticlePreprocessor(
            allowed_languages=["ko", "en", "unknown"],
            max_age_days=config.get("max_age_days", 30),
            use_simhash=True,
        )
        clean_articles = preprocessor.run(state.get("raw_articles", []))
        stats = preprocessor.get_stats()

        logger.info(
            f"[preprocess_node] 완료 | "
            f"{stats['total']}건 → {stats['passed']}건 "
            f"(광고:{stats['ad_filtered']}, 중복:{stats['url_duplicate'] + stats['simhash_duplicate']})"
        )

        return {
            "raw_articles": clean_articles,     # 전처리된 기사로 교체
            "preprocessing_stats": stats,
            "errors": errors,
        }

    except Exception as e:
        msg = f"전처리 오류: {e}"
        logger.error(msg)
        return {
            "preprocessing_stats": {},
            "errors": [msg],
        }


# =============================================
# 노드 3: 분류 노드 (classify_node)
# =============================================

def classify_node(state: FootballNewsState) -> dict:
    """
    전처리된 기사를 언어별로 분류하고 라우팅 플래그를 설정합니다.

    이 노드의 결과가 조건부 엣지(conditional edge)의 입력이 됩니다.
    has_korean / has_english / has_match_data 플래그를 보고
    graph.py의 route_after_classify() 함수가 다음 노드를 결정합니다.

    State 업데이트 키:
        korean_articles  : 한국어 기사 목록
        english_articles : 영어 기사 목록
        has_korean       : 한국어 기사 1건 이상 존재 여부
        has_english      : 영어 기사 1건 이상 존재 여부
        has_match_data   : EPL 경기 결과 1건 이상 존재 여부
    """
    try:
        articles = state.get("raw_articles", [])
        matches = state.get("raw_matches", [])
        league_code = state.get("config", {}).get("league", "PL")

        korean_articles = [a for a in articles if a.get("language") == "ko"]
        english_articles = [a for a in articles if a.get("language") == "en"]

        # 선택 리그와 무관한 기사를 여기서 걸러낸다. 예전엔 RSS(6개 소스,
        # 리그 인식 없음)와 네이버 수집 결과가 그대로 요약/감정분석/RAG
        # 인덱싱까지 흘러들어가서, 예를 들어 K리그를 선택해도 일간 보고서
        # "주요 토픽"에 월드컵·EPL 기사가 섞여 나오는 문제가 있었다. 화면
        # 표시 단계에서만 걸러서는 요약 자체가 이미 오염된 뒤라 해결이 안 됐다.
        korean_articles, english_articles = _filter_by_league(
            korean_articles, english_articles, league_code
        )

        has_korean = len(korean_articles) > 0
        has_english = len(english_articles) > 0
        # WC: 무료 API 제한으로 경기 데이터가 없어도 뉴스 기반 분석 실행
        if league_code == "WC" and (has_korean or has_english):
            has_match_data = True
        else:
            has_match_data = len(matches) > 0

        logger.info(
            f"[classify_node] 완료 | "
            f"국내:{len(korean_articles)}건 영어:{len(english_articles)}건 "
            f"경기:{len(matches)}건"
        )

        return {
            "korean_articles": korean_articles,
            "english_articles": english_articles,
            "has_korean": has_korean,
            "has_english": has_english,
            "has_match_data": has_match_data,
            "errors": [],
        }

    except (KeyError, TypeError) as e:
        logger.error(f"[classify_node] State 읽기 오류: {e}")
        return {
            "korean_articles": [], "english_articles": [],
            "has_korean": False, "has_english": False, "has_match_data": False,
            "errors": [f"classify_node 오류: {e}"],
        }
    except Exception as e:
        logger.error(f"[classify_node] 예외 발생: {e}")
        return {
            "korean_articles": [], "english_articles": [],
            "has_korean": False, "has_english": False, "has_match_data": False,
            "errors": [f"classify_node 예외: {e}"],
        }


# =============================================
# 노드 4: 병합/최종 리포트 노드 (merge_node)
# =============================================

def merge_node(state: FootballNewsState) -> dict:
    """
    LLM 노드 3종의 결과를 하나의 최종 리포트로 통합합니다.

    통합 구조:
        ┌─────────────────────────────────────┐
        │         ⚽ Football Lens 일간 리포트  │
        ├─────────────────────────────────────┤
        │ 1. 국내 축구 뉴스 요약 (Claude)       │
        │ 2. 해외 축구 뉴스 요약 (GPT-4o-mini) │
        │ 3. 경기 분석 (Gemini, 선택 리그 기준)  │
        │ 4. 수집 통계                          │
        └─────────────────────────────────────┘

    State 업데이트 키:
        final_report        : 통합된 마크다운 리포트 텍스트
        report_generated_at : 리포트 생성 시각 (ISO 문자열)
    """
    logger.info("[merge_node] 최종 리포트 생성 시작")

    try:
        korean_summary = state.get("korean_summary", {})
        english_summary = state.get("english_summary", {})
        match_analysis = state.get("match_analysis", {})
        stats = state.get("preprocessing_stats", {})
        run_id = state.get("run_id", "unknown")
        league_code = state.get("config", {}).get("league", "PL")
        league_label = _LEAGUE_SHORT_NAME.get(league_code, league_code)
        now_str = datetime.now(timezone.utc).strftime("%Y년 %m월 %d일 %H:%M UTC")

        # ── 섹션별 텍스트 조립 ─────────────────────────────────
        sections = []

        # 헤더
        sections.append(f"# ⚽ Football Lens 일간 리포트")
        sections.append(f"**생성일시**: {now_str} | **run_id**: {run_id}")
        sections.append("")

        # 1. 국내 뉴스 요약
        sections.append("---")
        sections.append("## 📰 국내 축구 뉴스 요약")
        if korean_summary.get("error"):
            sections.append(f"> ⚠️ 요약 생성 실패: {korean_summary['error']}")
        elif korean_summary.get("summary_text"):
            sections.append(f"*모델: {korean_summary.get('model_used', '-')} | 기사 {korean_summary.get('articles_count', 0)}건 기반*")
            sections.append("")
            sections.append(korean_summary["summary_text"])
            if korean_summary.get("key_topics"):
                topics = ", ".join(f"`{t}`" for t in korean_summary["key_topics"])
                sections.append(f"\n**주요 토픽**: {topics}")
        else:
            sections.append("> 국내 뉴스 없음")

        sections.append("")

        # 2. 해외 뉴스 요약
        sections.append("---")
        sections.append("## 🌍 해외 축구 뉴스 요약")
        if english_summary.get("error"):
            sections.append(f"> ⚠️ 요약 생성 실패: {english_summary['error']}")
        elif english_summary.get("summary_text"):
            sections.append(f"*모델: {english_summary.get('model_used', '-')} | 기사 {english_summary.get('articles_count', 0)}건 기반*")
            sections.append("")
            sections.append(english_summary["summary_text"])
            if english_summary.get("key_topics"):
                topics = ", ".join(f"`{t}`" for t in english_summary["key_topics"])
                sections.append(f"\n**Key Topics**: {topics}")
        else:
            sections.append("> No English news available")

        sections.append("")

        # 3. 경기 분석
        sections.append("---")
        sections.append(f"## 🏆 {league_label} 경기 분석")
        if match_analysis.get("error"):
            sections.append(f"> ⚠️ 분석 생성 실패: {match_analysis['error']}")
        elif match_analysis.get("analysis_text"):
            sections.append(f"*모델: {match_analysis.get('model_used', '-')} | 경기 {match_analysis.get('matches_count', 0)}건 분석*")
            sections.append("")
            sections.append(match_analysis["analysis_text"])
            if match_analysis.get("notable_results"):
                sections.append("\n**주목 경기**:")
                for r in match_analysis["notable_results"]:
                    sections.append(f"- {r}")
            if match_analysis.get("standings_summary"):
                sections.append(f"\n**순위표 요약**: {match_analysis['standings_summary']}")
        else:
            sections.append(f"> {league_label} 경기 데이터 없음")

        sections.append("")

        # 4. 수집 통계
        sections.append("---")
        sections.append("## 📊 수집 통계")
        if stats:
            sections.append(f"- 전체 수집: **{stats.get('total', 0)}건**")
            sections.append(f"- 최종 통과: **{stats.get('passed', 0)}건**")
            sections.append(f"- 광고 필터: {stats.get('ad_filtered', 0)}건")
            sections.append(f"- 중복 제거: {stats.get('url_duplicate', 0) + stats.get('simhash_duplicate', 0)}건")

        # 오류 목록 (있을 경우)
        errors = state.get("errors", [])
        if errors:
            sections.append("")
            sections.append("---")
            sections.append("## ⚠️ 실행 오류 목록")
            for err in errors:
                sections.append(f"- {err}")


        final_report = "\n".join(sections)
        generated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[merge_node] 최종 리포트 생성 완료 | "
            f"길이 {len(final_report)}자 | generated_at={generated_at}"
        )

        return {
            "final_report": final_report,
            "generated_at": generated_at,
            "errors": [],
        }

    except Exception as e:
        logger.error(f"[merge_node] 예외 발생: {e}", exc_info=True)
        return {
            "final_report": f"리포트 생성 실패: {e}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "errors": [f"merge_node 예외: {e}"],
        }
