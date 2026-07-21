# -*- coding: utf-8 -*-
"""tabs/players.py — 주목할 선수 탭."""
import streamlit as st

from components import _html, espn_section, render_sentiment_badge


def render_spotlight_players_tab(result: dict, league: str = "PL"):
    """⭐ 주목할 선수 탭 — 리그별 주요 선수 + 관련 뉴스 + 감정 통계."""

    # 리그별 주목할 선수 목록
    _LEAGUE_SPOTLIGHT = {
        "WC":  ["손흥민", "이강인", "김민재", "메시", "음바페", "홀란드", "비니시우스", "벨링엄", "야말", "로드리"],
        "PL":  ["홀란드", "살라", "손흥민", "황희찬", "팔머", "아르테타", "벨링엄", "워트킨스", "이사크", "자카"],
        "PD":  ["비니시우스", "야말", "음바페", "벨링엄", "레반도프스키", "페드리", "모드리치", "크로스"],
        "BL1": ["케인", "무시알라", "그리말도", "비르츠", "그나브리", "킴미히", "사네"],
        "SA":  ["마르티네스", "루카쿠", "디마리아", "바레야", "오시멘", "초크", "라우타로"],
        "FL1": ["음바페", "뎀벨레", "음파페", "파리", "아카이오지", "테아테", "루베르트"],
        "KL1": ["조규성", "오현규", "황인범", "황의조", "이동경", "제르소", "마테우스"],
    }

    league_players = _LEAGUE_SPOTLIGHT.get(league, _LEAGUE_SPOTLIGHT["PL"])

    # 리그 이름 매핑
    _LEAGUE_NAME = {
        "WC": "2026 FIFA 월드컵", "PL": "EPL 프리미어리그",
        "PD": "라리가", "BL1": "분데스리가",
        "SA": "세리에A", "FL1": "리그앙", "KL1": "K리그1",
    }
    league_name = _LEAGUE_NAME.get(league, league)

    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    sentiments_by_id = {
        s.get("article_id", ""): s
        for s in result.get("article_sentiments", [])
    }
    top_scorers = result.get("top_scorers", [])

    espn_section("⭐", f"Spotlight Players — {league_name}")

    # 주목할 선수 chip 목록
    _html(f'<div style="font-size:11px;color:#CC0000;font-family:Oswald,sans-serif;font-weight:700;text-transform:uppercase;margin-bottom:8px;">⚡ {league_name} 주목 선수</div>')
    chip_cols = st.columns(min(len(league_players), 5))
    for i, p in enumerate(league_players[:5]):
        with chip_cols[i]:
            if st.button(p, key=f"spotlight_chip_{i}", use_container_width=True):
                st.session_state["spotlight_query"] = p

    # 두 번째 줄 chip (나머지)
    if len(league_players) > 5:
        chip_cols2 = st.columns(min(len(league_players) - 5, 5))
        for i, p in enumerate(league_players[5:10]):
            with chip_cols2[i]:
                if st.button(p, key=f"spotlight_chip2_{i}", use_container_width=True):
                    st.session_state["spotlight_query"] = p

    # 검색창
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        player_query = st.text_input(
            "선수 검색",
            placeholder=f"예: {league_players[0]}, {league_players[1]}...",
            label_visibility="collapsed",
            key="spotlight_search_input",
        )
    with col2:
        if st.button("🔍 검색", key="spotlight_search_btn", type="primary", use_container_width=True):
            if player_query:
                st.session_state["spotlight_query"] = player_query

    if player_query:
        st.session_state["spotlight_query"] = player_query
    query = st.session_state.get("spotlight_query", "")

    if not query:
        # 기본: 득점 순위 표시
        if top_scorers:
            st.markdown("<br>", unsafe_allow_html=True)
            espn_section("⚽", "Top Scorers")
            try:
                import pandas as pd
                df = pd.DataFrame(top_scorers[:10])
                cols_show = [c for c in ["rank", "player_name", "team_name", "goals", "assists", "penalties"] if c in df.columns]
                col_labels = {"rank": "순위", "player_name": "선수", "team_name": "팀",
                              "goals": "득점", "assists": "어시스트", "penalties": "PK"}
                st.dataframe(df[cols_show].rename(columns=col_labels), use_container_width=True, hide_index=True)
            except Exception:
                for s in top_scorers[:10]:
                    _html(f'<div style="padding:6px 0;border-bottom:1px solid #EEE;">'
                          f'<strong style="color:#CC0000;">{s.get("rank","?")}위</strong> '
                          f'{s.get("player_name","?")} <span style="color:#888;font-size:12px;">({s.get("team_name","?")})</span> '
                          f'— <strong>{s.get("goals",0)}</strong>골 {s.get("assists",0)}A</div>')
        else:
            st.info("위에서 선수 이름을 클릭하거나 검색하세요.")
        return

    if not all_articles:
        st.info("먼저 ⚡ 분석 실행으로 데이터를 수집하세요.")
        return

    # 선수 관련 기사 필터
    q_lower = query.lower()
    matched = [
        a for a in all_articles
        if q_lower in f"{a.get('title','')} {a.get('summary','')}".lower()
    ]

    if not matched:
        st.warning(f"'{query}' 관련 기사가 없습니다. 분석 실행 후 다시 시도하세요.")
        return

    # 감정 통계
    player_sentiments = [
        sentiments_by_id[a["article_id"]]
        for a in matched
        if a.get("article_id") in sentiments_by_id
    ]

    if player_sentiments:
        from collections import Counter
        avg_score = sum(s.get("sentiment_score", 0) for s in player_sentiments) / len(player_sentiments)
        label_cnt = Counter(s.get("sentiment_label", "중립") for s in player_sentiments)

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:#CC0000;">{len(matched)}</div>
<div style="font-size:12px;color:#888;">관련 기사</div>
</div>
""")
        with col_b:
            sc_color = "#2E7D32" if avg_score > 0.1 else ("#CC0000" if avg_score < -0.1 else "#888")
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid {sc_color};padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:{sc_color};">{avg_score:+.2f}</div>
<div style="font-size:12px;color:#888;">평균 감정 점수</div>
</div>
""")
        with col_c:
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #2E7D32;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:#2E7D32;">{label_cnt.get('긍정', 0)}</div>
<div style="font-size:12px;color:#888;">긍정 기사</div>
</div>
""")
        with col_d:
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #888;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:28px;font-weight:700;color:#888;">{label_cnt.get('부정', 0)}</div>
<div style="font-size:12px;color:#888;">부정 기사</div>
</div>
""")
        st.markdown("<br>", unsafe_allow_html=True)

    # 관련 기사 목록
    espn_section("📰", f"'{query}' Related Articles", len(matched))
    for a in matched[:15]:
        sent = sentiments_by_id.get(a.get("article_id", ""), {})
        score = sent.get("sentiment_score", 0)
        label = sent.get("sentiment_label", "중립")
        badge = render_sentiment_badge(score, label)
        is_rumor = sent.get("is_transfer_rumor", False)
        rumor_chip = '<span style="background:#E65C00;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;margin-left:4px;">🔄 이적설</span>' if is_rumor else ""
        title = (a.get("title") or "")[:80]
        url   = a.get("url", "#")
        src   = a.get("source_name", "")
        pub   = str(a.get("published_at", ""))[:10]
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:12px 16px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);display:flex;justify-content:space-between;align-items:center;">
<div style="flex:1;margin-right:12px;">
<a href="{url}" target="_blank" style="font-size:14px;font-weight:600;color:#1A1A1A;text-decoration:none;">{title}</a>
<div style="font-size:11px;color:#888;margin-top:3px;">{src} · {pub}</div>
</div>
<div style="display:flex;gap:4px;flex-shrink:0;">{badge}{rumor_chip}</div>
</div>
""")
