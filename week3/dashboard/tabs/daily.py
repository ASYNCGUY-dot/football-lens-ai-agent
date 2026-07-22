# -*- coding: utf-8 -*-
"""tabs/daily.py — 일간 보고서 탭."""
import streamlit as st

from constants import _LEAGUE_DISPLAY
from components import _html, espn_section, render_hot_issues, render_league_overview, render_news_card
from utils import _filter_articles_by_league
from season_info import render_off_season_notice


def render_daily_report(result: dict, language: str, league: str = None):
    """
    일간 보고서 탭을 렌더링합니다.
    league가 지정되면 해당 리그/대회 관련 뉴스가 상단에 우선 배치됩니다.
    """
    league_display = _LEAGUE_DISPLAY.get(league, league or "⚽ 축구")

    if render_off_season_notice(league):
        return

    if not result:
        _html(f"""
<div style="margin-top:20px;">
<div style="background:#FFFFFF;border-left:5px solid #CC0000;border-radius:0 6px 6px 0;padding:24px 28px;box-shadow:0 2px 8px rgba(0,0,0,0.07);display:flex;align-items:center;gap:20px;">
<div style="font-size:40px;line-height:1;">⚡</div>
<div>
<div style="font-family:'Oswald',sans-serif;font-size:18px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:4px;">분석 준비 완료 — 사이드바에서 시작하세요</div>
<div style="font-size:14px;color:#666;">{league_display} 선택됨 → 기간 설정 → <strong style="color:#CC0000;">⚡ 분석 실행</strong> 클릭</div>
</div>
</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;">
<div style="background:#FFFFFF;border-radius:6px;padding:20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #CC0000;">
<div style="font-size:28px;margin-bottom:8px;">📰</div>
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">일간 보고서</div>
<div style="font-size:12px;color:#888;margin-top:4px;">국내·해외 뉴스 AI 요약</div>
</div>
<div style="background:#FFFFFF;border-radius:6px;padding:20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #003399;">
<div style="font-size:28px;margin-bottom:8px;">🔍</div>
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">RAG 기사 검색</div>
<div style="font-size:12px;color:#888;margin-top:4px;">ChromaDB 벡터 유사도 검색</div>
</div>
<div style="background:#FFFFFF;border-radius:6px;padding:20px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #2E7D32;">
<div style="font-size:28px;margin-bottom:8px;">🏆</div>
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">{league_display}</div>
<div style="font-size:12px;color:#888;margin-top:4px;">리그/대회 최신 뉴스</div>
</div>
</div>
</div>
""")
        return

    # ── 스탯 메트릭 ────────────────────────────────────────
    stats = result.get("preprocessing_stats", {})
    ko_count = len(result.get("korean_articles", []))
    en_count = len(result.get("english_articles", []))
    match_count = len(result.get("raw_matches", []))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📥 수집 기사", f"{stats.get('total', 0)}건")
    with col2:
        st.metric("✅ 전처리 통과", f"{stats.get('passed', 0)}건")
    with col3:
        st.metric("🇰🇷 국내 / 🌍 해외", f"{ko_count} / {en_count}")
    with col4:
        st.metric("🏟️ 경기", f"{match_count}건")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 핫이슈 이미지 카드 그리드 (선택 리그 우선) ────────────
    render_hot_issues(result, league=league)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 리그 오버뷰 ─────────────────────────────────────────
    render_league_overview(result, league=league)

    # ── AI 인사이트 ─────────────────────────────────────────
    insight = result.get("insight_report", "")
    if insight:
        _html(f"""
<div style="background:#FFFFFF;border-left:5px solid #CC0000;border-radius:0 4px 4px 0;padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
<div style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#CC0000;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">🔎 AI 통합 인사이트 — RAG + Multi-LLM</div>
</div>
""")
        st.markdown(insight)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── 국내 뉴스 요약 ────────────────────────────────────
    if language in (None, "ko"):
        ko_summary = result.get("korean_summary", {})
        with st.expander("📺 국내 축구 뉴스 요약 (Claude)", expanded=True):
            if ko_summary.get("error"):
                st.warning(f"요약 실패: {ko_summary['error']}")
            elif ko_summary.get("summary_text"):
                st.markdown(ko_summary["summary_text"])
                if ko_summary.get("key_topics"):
                    topics = " ".join(
                        f'<span class="ebadge eb-dark">{t}</span>'
                        for t in ko_summary["key_topics"]
                    )
                    _html(f'<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;"><span style="font-size:12px;color:#888;align-self:center;">토픽:</span>{topics}</div>')
            else:
                st.info("국내 뉴스 데이터 없음")

    # ── 해외 뉴스 요약 ────────────────────────────────────
    if language in (None, "en"):
        en_summary = result.get("english_summary", {})
        with st.expander("🌍 해외 뉴스 요약 (GPT-4o-mini)", expanded=True):
            if en_summary.get("error"):
                st.warning(f"요약 실패: {en_summary['error']}")
            elif en_summary.get("summary_text"):
                st.markdown(en_summary["summary_text"])
            else:
                st.info("No English news data")

    # ── 경기 분석 ─────────────────────────────────────────
    match_analysis = result.get("match_analysis", {})
    with st.expander(f"🏟️ {league_display} 경기 분석 (Gemini)", expanded=True):
        if match_analysis.get("error"):
            st.warning(f"분석 실패: {match_analysis['error']}")
        elif match_analysis.get("analysis_text"):
            st.markdown(match_analysis["analysis_text"])
        else:
            # WC 폴백: 파이프라인 미반영 상태에서도 뉴스 목록 표시
            if league == "WC":
                all_arts = result.get("korean_articles", []) + result.get("english_articles", [])
                WC_KW = ["월드컵", "world cup", "worldcup", "fifa", "조별", "16강", "8강", "결승", "한국 대표"]
                wc_arts = [
                    a for a in all_arts
                    if any(kw in (a.get("title","") + a.get("summary","")).lower() for kw in WC_KW)
                ] or all_arts[:10]
                if wc_arts:
                    _html("""
<div style="background:#FFF8E1;border-left:4px solid #FFA000;border-radius:0 4px 4px 0;
     padding:10px 16px;margin-bottom:12px;font-size:12px;color:#666;">
  ℹ️ Gemini API로 심층 분석을 생성하려면 <code>.env</code>에 <code>GOOGLE_API_KEY</code>를 설정 후 Streamlit을 재시작하세요.
  현재는 수집된 뉴스 기사 목록을 표시합니다.
</div>
""")
                    for a in wc_arts[:12]:
                        title = (a.get("title") or "")[:90]
                        url   = a.get("url", "#")
                        src   = a.get("source_name", "")
                        pub   = str(a.get("published_at", ""))[:10]
                        _html(f"""
<div style="border-bottom:1px solid #F0F0F0;padding:8px 0;">
<a href="{url}" target="_blank"
   style="font-size:13px;font-weight:600;color:#1A1A1A;text-decoration:none;">{title}</a>
<div style="font-size:11px;color:#888;margin-top:2px;">{src} · {pub}</div>
</div>
""")
                else:
                    st.info("분석 실행 후 월드컵 경기 분석이 표시됩니다.")
            else:
                st.info("경기 데이터 없음 — 분석 실행 또는 football-data.org API 키 확인")

    # ── 기사 카드 그리드 (선택 리그 우선 정렬) ───────────────
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
        if language is None
        else result.get("korean_articles", []) if language == "ko"
        else result.get("english_articles", [])
    )
    # 선택 리그 관련 기사를 앞으로 배치
    if league and all_articles:
        all_articles = _filter_articles_by_league(all_articles, league)
    if all_articles:
        espn_section("🗞️", "Latest Articles", len(all_articles))
        # 상단 2개: 이미지 포함 featured
        feat_cols = st.columns(2)
        for i, article in enumerate(all_articles[:2]):
            with feat_cols[i]:
                render_news_card(article, show_image=True)
        # 나머지: 2열 그리드
        col_l, col_r = st.columns(2)
        for i, article in enumerate(all_articles[2:18]):
            with col_l if i % 2 == 0 else col_r:
                render_news_card(article)

    # Reddit 커뮤니티 섹션은 뺐다 — 수집기 자체를 제거했다(week2/nodes.py
    # 주석 참고: 고정 서브레딧이 리그 무관이었고 rate limit도 심했음).

    # ── 득점 순위 미니 테이블 ─────────────────────────────
    top_scorers = result.get("top_scorers", [])
    if top_scorers:
        st.markdown("<br>", unsafe_allow_html=True)
        espn_section("⚽", "Top Scorers")
        cols = st.columns(5)
        for i, s in enumerate(top_scorers[:5]):
            with cols[i]:
                _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:12px 10px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#CC0000;">{s.get('goals', 0)}</div>
<div style="font-family:'Oswald',sans-serif;font-size:11px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">{(s.get('player_name') or '')[:14]}</div>
<div style="font-size:10px;color:#888;">{(s.get('team_name') or '')[:16]}</div>
<div style="font-size:10px;color:#555;margin-top:2px;">{s.get('assists', 0)}A</div>
</div>
""")

    errors = result.get("errors", [])
    if errors:
        with st.expander(f"⚠️ 오류 {len(errors)}건", expanded=False):
            for err in errors:
                st.error(err)
