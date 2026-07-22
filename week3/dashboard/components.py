# -*- coding: utf-8 -*-
"""
components.py
=============
app.py에서 분리한 공용 UI 조각. 여러 탭이 공유하는 렌더링 헬퍼만 담는다.
"""
import textwrap
from datetime import datetime

import streamlit as st

from constants import IMG_STADIUM, LOGO_COLOR
from utils import _filter_articles_by_league


def _html(markup: str) -> None:
    """
    들여쓰기를 제거하고 HTML을 렌더링합니다.
    CommonMark의 4칸-들여쓰기 코드블록 오인을 방지합니다.
    """
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


# =============================================
# ESPN CSS
# =============================================



def render_ticker(articles: list = None):
    """
    ESPN 스타일 속보 뉴스 티커를 렌더링합니다.

    Parameters
    ----------
    articles : list, optional
        기사 목록. 없으면 기본 더미 텍스트를 표시합니다.
    """
    if articles:
        items = " &nbsp;•&nbsp; ".join(
            f"⚽ {a.get('title','')[:60]}" for a in articles[:8]
        )
        # 무한 루프를 위해 두 번 반복
        ticker_text = items + " &nbsp;&nbsp;&nbsp; " + items
    else:
        ticker_text = (
            "⚽ Football Lens — AI 기반 축구 뉴스 분석 대시보드 &nbsp;•&nbsp; "
            "🏆 EPL · K리그1 · 라리가 · 분데스리가 &nbsp;•&nbsp; "
            "🤖 Claude + GPT-4o-mini + Gemini 멀티 LLM &nbsp;•&nbsp; "
            "🔍 ChromaDB RAG 벡터 검색 &nbsp;•&nbsp; "
            "📊 LangGraph 파이프라인 &nbsp;•&nbsp; "
            "⚽ Football Lens — AI 기반 축구 뉴스 분석 대시보드 &nbsp;•&nbsp; "
            "🏆 EPL · K리그1 · 라리가 · 분데스리가 &nbsp;•&nbsp; "
            "🤖 Claude + GPT-4o-mini + Gemini 멀티 LLM &nbsp;•&nbsp; "
            "🔍 ChromaDB RAG 벡터 검색 &nbsp;•&nbsp; "
            "📊 LangGraph 파이프라인"
        )

    _html(f"""
<div style="background:#CC0000;overflow:hidden;white-space:nowrap;padding:7px 0;margin-bottom:0;border-bottom:2px solid #AA0000;">
<div style="display:inline-flex;align-items:center;">
<span style="background:rgba(255,255,255,0.2);color:#FFFFFF;font-family:'Oswald',sans-serif;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:0 14px;margin-right:16px;white-space:nowrap;border-right:1px solid rgba(255,255,255,0.3);">⚡ LIVE</span>
<span style="display:inline-block;animation:espn-scroll 30s linear infinite;font-size:12px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:500;letter-spacing:0.3px;">
{ticker_text}
</span>
</div>
</div>
""")


# =============================================
# ESPN 히어로 헤더
# =============================================



def render_hero():
    """
    스타디움 배경 이미지 위에 ESPN 스타일 히어로 배너를 렌더링합니다.
    Unsplash 스타디움 사진 + 빨간 그라데이션 오버레이
    """
    _html(f"""
<div style="position:relative;background:url('{IMG_STADIUM}') center/cover no-repeat;min-height:220px;margin:0 0 0 0;overflow:hidden;">
<div style="position:absolute;inset:0;background:linear-gradient(100deg,rgba(204,0,0,0.92) 0%,rgba(26,26,26,0.88) 60%,rgba(0,0,0,0.6) 100%);"></div>
<div style="position:relative;padding:32px 40px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:20px;">
<div>
<div style="font-family:'Oswald',sans-serif;font-size:11px;font-weight:700;color:#FF9999;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">AI FOOTBALL NEWS DASHBOARD</div>
<div style="font-family:'Oswald',sans-serif;font-size:42px;font-weight:700;color:#FFFFFF;letter-spacing:-1px;line-height:1;text-transform:uppercase;text-shadow:0 2px 8px rgba(0,0,0,0.5);">Football Lens</div>
<div style="font-size:14px;color:rgba(255,255,255,0.75);margin-top:8px;font-family:'Source Sans 3',sans-serif;">LangGraph 파이프라인 · Claude · GPT-4o-mini · Gemini · ChromaDB RAG</div>
<div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;">
<span style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:2px;padding:4px 12px;font-size:11px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">⚡ LangGraph</span>
<span style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:2px;padding:4px 12px;font-size:11px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">🤖 Multi-LLM</span>
<span style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:2px;padding:4px 12px;font-size:11px;color:#FFFFFF;font-family:'Oswald',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">🔍 RAG</span>
</div>
</div>
<div style="display:flex;flex-direction:column;align-items:center;gap:12px;">
<img src="{LOGO_COLOR}" style="width:70px;height:70px;filter:drop-shadow(0 2px 10px rgba(0,0,0,0.6));" alt="Football Lens">
<div style="text-align:center;">
<div style="font-family:'Oswald',sans-serif;font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px;">{datetime.now().strftime('%Y.%m.%d')}</div>
<div style="font-family:'Oswald',sans-serif;font-size:13px;color:#FFFFFF;font-weight:600;">{datetime.now().strftime('%A').upper()}</div>
</div>
</div>
</div>
</div>
""")


# =============================================
# 카드 컴포넌트
# =============================================



def render_news_card(article: dict, show_image: bool = False):
    """
    ESPN 스타일 뉴스 카드를 렌더링합니다.

    Parameters
    ----------
    article : dict
        기사 딕셔너리
    show_image : bool
        True이면 섹션 이미지를 표시합니다 (주요 기사용)
    """
    lang = article.get("language", "ko")
    title = (article.get("title") or "제목 없음")[:120]
    summary = (article.get("summary") or "")[:160]
    url = article.get("url") or "#"
    source_name = article.get("source_name") or article.get("keyword") or ""
    category = article.get("category", "")

    tag = category or ("국내 축구" if lang == "ko" else "FOOTBALL")
    lang_cls = "eb-blue" if lang == "ko" else "eb-red"
    lang_txt = "🇰🇷 KO" if lang == "ko" else "🇬🇧 EN"
    title_html = (
        f'<a href="{url}" target="_blank" class="espn-card-title">{title}</a>'
        if url and url != "#"
        else f'<div class="espn-card-title">{title}</div>'
    )
    ellipsis = "..." if len(article.get("summary") or "") > 160 else ""

    img_html = ""
    article_img = article.get("image_url", "")
    if article_img:
        # 실제 기사 이미지가 있을 때만 보여준다 (RSS는 대부분 제공, 네이버
        # 뉴스 검색 API는 이미지 필드 자체가 없음 — 무관한 스톡사진을
        # 대신 넣으면 기사 내용과 안 맞는 사진이 반복 노출되는 문제가 있었음)
        img_html = (
            f'<img src="{article_img}" style="width:100%;height:110px;object-fit:cover;'
            f'border-radius:2px;margin-bottom:8px;" alt="article" '
            f'onerror="this.parentElement.querySelector(\'.espn-img-fallback\')?.style.removeProperty(\'display\');this.remove();">'
        )
    elif show_image:
        # 이미지가 없는데 큰 카드로 보여야 할 때는 출처만 담은 중립
        # 플레이스홀더로 대체 (스톡사진으로 오해 유발하지 않음)
        src_label = (article.get("source_name") or "기사")[:12]
        img_html = (
            f'<div class="espn-img-fallback" style="width:100%;height:110px;border-radius:2px;'
            f'margin-bottom:8px;background:#F0F0F0;display:flex;align-items:center;'
            f'justify-content:center;color:#AAA;font-family:Oswald,sans-serif;'
            f'font-size:12px;font-weight:600;">📰 {src_label}</div>'
        )

    _html(f"""
<div class="espn-card">
{img_html}
<div class="espn-card-tag">{tag}</div>
{title_html}
<div class="espn-card-summary">{summary}{ellipsis}</div>
<div class="espn-card-meta">
<span class="ebadge {lang_cls}">{lang_txt}</span>
{"<span>·</span><span>" + source_name + "</span>" if source_name else ""}
</div>
</div>
""")



def render_rag_card(r: dict):
    """
    ESPN 스타일 RAG 검색 결과 카드를 렌더링합니다.

    Parameters
    ----------
    r : dict
        embedder.search() 결과
    """
    source = r.get("source", "real")
    lang = r.get("language", "ko")
    title = (r.get("title") or "")[:120]
    summary = (r.get("summary") or "")[:160]
    url = r.get("url") or "#"
    similarity = round((1 - r.get("distance", 0)) * 100, 1)

    src_cls = "eb-green" if source == "real" else "eb-gray"
    src_txt = "🟢 REAL" if source == "real" else "⬜ DEMO"
    lang_cls = "eb-blue" if lang == "ko" else "eb-red"
    lang_txt = "🇰🇷 KO" if lang == "ko" else "🇬🇧 EN"
    title_html = (
        f'<a href="{url}" target="_blank" class="espn-card-title">{title}</a>'
        if url and url != "#"
        else f'<div class="espn-card-title">{title}</div>'
    )

    _html(f"""
<div class="espn-card">
<div class="espn-card-tag">유사도 {similarity}%</div>
{title_html}
<div class="espn-card-summary">{summary}{"..." if len(r.get("summary","")) > 160 else ""}</div>
<div class="espn-card-meta">
<span class="ebadge {src_cls}">{src_txt}</span>
<span class="ebadge {lang_cls}">{lang_txt}</span>
<span class="ebadge eb-gold">{similarity}%</span>
</div>
<div class="sim-bar-bg"><div class="sim-bar-fill" style="width:{int(similarity)}%;"></div></div>
</div>
""")



def render_hot_issues(result: dict, league: str = None):
    """
    핫이슈 섹션 — 선택 리그 관련 기사를 우선으로, 최신 이미지 카드 6개를 3열 그리드로 표시합니다.
    league가 지정되면 해당 리그 관련 기사가 상위에 배치됩니다.
    """
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    if not all_articles:
        return

    # 최신순 정렬
    def _sort_key(a):
        pt = a.get("published_at")
        return str(pt) if pt else ""

    sorted_articles = sorted(all_articles, key=_sort_key, reverse=True)

    # 리그 관련 기사 우선 배치 (그룹 내 날짜 순서 유지)
    if league:
        sorted_articles = _filter_articles_by_league(sorted_articles, league)

    # 제목 기반 중복 제거 (URL이 달라도 같은 기사 걸러냄)
    seen_titles: set = set()
    deduped = []
    for a in sorted_articles:
        title_key = (a.get("title") or "")[:40].strip()
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            deduped.append(a)

    top = deduped[:6]

    espn_section("🔥", "HOT ISSUES", len(all_articles))

    cols = st.columns(3)
    for i, article in enumerate(top):
        with cols[i % 3]:
            title = (article.get("title") or "")[:80]
            url   = article.get("url") or "#"
            src   = article.get("source_name") or article.get("keyword") or ""
            pub   = str(article.get("published_at", ""))[:10]
            lang  = article.get("language", "ko")
            flag  = "🇰🇷" if lang == "ko" else "🇬🇧"
            _html(f"""
<div class="espn-card" style="padding:14px 16px;margin-bottom:10px;border-left:4px solid #CC0000;">
<div style="margin-bottom:6px;">
<span style="background:#CC0000;color:#FFF;font-family:'Oswald',sans-serif;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;padding:2px 7px;border-radius:2px;">{flag} {src}</span>
<span style="font-size:10px;color:#888;margin-left:8px;">{pub}</span>
</div>
<a href="{url}" target="_blank" style="text-decoration:none;">
<div style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#1A1A1A;line-height:1.4;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{title}</div>
</a>
</div>
""")



def render_league_overview(result: dict, league: str = None):
    """
    리그 오버뷰 섹션 — 수집된 순위표 데이터로 상위 5팀을 리그별 카드로 표시합니다.

    league(API 코드)를 넘기지 않으면 예전처럼 "프리미어리그"로 고정
    표시되는 버그가 있었다 — 실제 standings는 선택된 리그(예: 브라질
    세리에A) 데이터인데 카드 제목만 항상 EPL로 나와서 혼란을 줬다.
    """
    standings = result.get("raw_standings", [])
    all_leagues = result.get("all_leagues_standings", {})

    if not standings and not all_leagues:
        return

    espn_section("🌍", "LEAGUE OVERVIEW")

    # 단일 리그 수집인 경우 — league 코드로 실제 이름/국기를 찾는다.
    if standings and not all_leagues:
        from constants import _CODE_TO_LEAGUE_NAME, _LEAGUE_DISPLAY
        display = _LEAGUE_DISPLAY.get(_CODE_TO_LEAGUE_NAME.get(league, ""), "")
        flag, _, name = display.partition(" ")
        if not name:
            name = _CODE_TO_LEAGUE_NAME.get(league, league or "리그")
            flag = "⚽"
        all_leagues = {(league or "LG"): {"meta": {"name": name, "flag": flag}, "standings": standings[:5]}}

    if not all_leagues:
        return

    league_cols = st.columns(min(len(all_leagues), 3))
    for col_i, (league_key, data) in enumerate(all_leagues.items()):
        meta      = data.get("meta", {})
        lg_stands = data.get("standings", [])[:5]
        flag      = meta.get("flag", "⚽")
        lg_name   = meta.get("name", league_key)

        with league_cols[col_i % len(league_cols)]:
            rows_html = ""
            for team in lg_stands:
                rank   = team.get("rank", "?")
                name   = (team.get("team_name") or "?")[:16]
                pts    = team.get("points", 0)
                won    = team.get("won", 0)
                draw   = team.get("draw", 0)
                lost   = team.get("lost", 0)
                rank_color = "#CC0000" if rank == 1 else ("#555" if rank <= 4 else "#888")
                rows_html += f"""
<div style="display:flex;align-items:center;padding:7px 12px;border-bottom:1px solid #F5F5F5;gap:8px;">
<span style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:{rank_color};min-width:20px;">{rank}</span>
<span style="flex:1;font-size:13px;font-weight:600;color:#1A1A1A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</span>
<span style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#CC0000;min-width:24px;text-align:right;">{pts}pt</span>
<span style="font-size:11px;color:#888;">({won}승{draw}무{lost}패)</span>
</div>"""
            _html(f"""
<div style="background:#FFFFFF;border-radius:6px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:12px;">
<div style="background:#CC0000;padding:10px 14px;display:flex;align-items:center;gap:8px;">
<span style="font-size:18px;">{flag}</span>
<span style="font-family:'Oswald',sans-serif;font-size:14px;font-weight:700;color:#FFF;text-transform:uppercase;">{lg_name}</span>
</div>
{rows_html}
</div>
""")



def espn_section(icon: str, title: str, count: int = None):
    """ESPN 스타일 섹션 헤더를 렌더링합니다."""
    count_html = (
        f'<span class="espn-sh-count">{count}건</span>'
        if count is not None else ""
    )
    _html(f"""
<div class="espn-sh">
<span style="font-size:20px;">{icon}</span>
<span class="espn-sh-title">{title}</span>
{count_html}
</div>
""")





def render_sentiment_badge(score: float, label: str) -> str:
    """감정 점수를 HTML 배지로 변환합니다."""
    if label == "긍정":
        color, bg = "#2E7D32", "#E8F5E9"
    elif label == "부정":
        color, bg = "#CC0000", "#FFEBEE"
    else:
        color, bg = "#555555", "#F5F5F5"
    bar_pct = int((score + 1) / 2 * 100)
    return (
        f'<span style="background:{bg};color:{color};border:1px solid {color}33;'
        f'border-radius:3px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:0.3px;">'
        f'{label} {score:+.2f}</span>'
    )
