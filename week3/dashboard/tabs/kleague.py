# -*- coding: utf-8 -*-
"""tabs/kleague.py — K리그 전용 탭."""
import streamlit as st

from constants import IMG_CROWD, IMG_MATCH, IMG_STADIUM, IMG_TRAINING
from components import _html, espn_section, render_sentiment_badge


def render_kleague_tab(result: dict):
    """K리그 전용 탭을 렌더링합니다."""
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    sentiments_by_id = {
        s.get("article_id", ""): s
        for s in result.get("article_sentiments", [])
    }

    # "울산" 단독 키워드는 지명이라 K리그와 무관한 기사까지 잡아서 제외했다
    # (구단명은 "울산hd"로 매칭). 팀 목록은 K리그1 상위 노출 구단 위주이며
    # 전체 12개 구단을 다 커버하지는 않는다.
    K_LEAGUE_KEYWORDS = [
        "k리그", "k-리그", "전북현대", "울산hd", "fc서울", "포항스틸러스",
        "수원삼성", "인천유나이티드", "성남fc", "대구fc", "광주fc",
        "조규성", "오현규", "황인범",
    ]

    kleague_articles = [
        a for a in all_articles
        if any(kw in f"{a.get('title','')} {a.get('summary','')}".lower()
               for kw in K_LEAGUE_KEYWORDS)
    ]

    if not result:
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">🇰🇷</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">K리그 데이터 없음</div>
<div style="font-size:14px;color:#888;margin-top:8px;">분석 실행 후 K리그 뉴스가 표시됩니다</div>
</div>
""")
        return

    espn_section("🇰🇷", "K-League News", len(kleague_articles))
    st.caption(
        "⚠️ K리그 전용으로 수집한 기사가 아니라, 전체 축구 뉴스 중 K리그 키워드가 "
        "포함된 기사만 걸러낸 것입니다 — 완벽하지 않을 수 있습니다. "
        "또한 football-data.org는 K리그 경기 데이터를 지원하지 않아 순위표는 제공되지 않습니다."
    )

    if not kleague_articles:
        st.info("현재 수집된 K리그 기사가 없습니다. 검색 키워드에 'K리그', '전북현대', '울산HD' 등을 포함해주세요.")
        return

    # 팀별 기사 집계
    from collections import Counter
    TEAMS = ["전북현대", "울산hd", "fc서울", "포항스틸러스", "수원삼성"]
    team_cnt = Counter()
    for a in kleague_articles:
        text = f"{a.get('title','')} {a.get('summary','')}".lower()
        for t in TEAMS:
            if t in text:
                team_cnt[t] += 1

    if team_cnt:
        st.caption("📊 구단별 기사 언급 횟수 (많이 언급된 순)")
        c1, c2, c3 = st.columns(3)
        for i, (team, cnt) in enumerate(team_cnt.most_common(3)):
            with [c1, c2, c3][i]:
                _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#CC0000;">{cnt}<span style="font-size:11px;color:#999;font-weight:400;">건</span></div>
<div style="font-family:'Oswald',sans-serif;font-size:12px;font-weight:600;color:#1A1A1A;text-transform:uppercase;">{team.upper()}</div>
</div>
""")
        st.markdown("<br>", unsafe_allow_html=True)

    # K리그 기사 카드
    fallback_imgs = [IMG_MATCH, IMG_STADIUM, IMG_CROWD, IMG_TRAINING]
    for i, article in enumerate(kleague_articles[:12]):
        sent = sentiments_by_id.get(article.get("article_id", ""), {})
        score = sent.get("sentiment_score", 0)
        label = sent.get("sentiment_label", "중립")
        badge = render_sentiment_badge(score, label)
        title = (article.get("title") or "")[:80]
        url   = article.get("url", "#")
        src   = article.get("source_name", "")
        pub   = str(article.get("published_at", ""))[:10]
        summary = (article.get("summary") or "")[:100]

        img = fallback_imgs[i % len(fallback_imgs)]
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-left:4px solid #003399;padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="display:flex;align-items:flex-start;gap:14px;">
<img src="{img}" style="width:80px;height:60px;object-fit:cover;border-radius:3px;flex-shrink:0;" alt="">
<div style="flex:1;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
<a href="{url}" target="_blank" style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;text-decoration:none;line-height:1.35;flex:1;margin-right:8px;">{title}</a>
{badge}
</div>
<div style="font-size:11px;color:#888;">{src} · {pub}</div>
<div style="font-size:12px;color:#666;margin-top:4px;">{summary}</div>
</div>
</div>
</div>
""")
