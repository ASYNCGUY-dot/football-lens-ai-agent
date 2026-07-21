# -*- coding: utf-8 -*-
"""tabs/youtube.py — YouTube 하이라이트 탭."""
import os as _os

import streamlit as st

from constants import _CODE_TO_LEAGUE_NAME
from components import _html, espn_section, render_news_card
from utils import _filter_articles_by_league
from season_info import render_off_season_notice


def _render_related_news(result: dict, league: str) -> None:
    """
    영상 대신 보여줄 대안 콘텐츠 — 이번 실행에서 수집된 관련 리그 뉴스.
    실시간 API를 새로 부르지 않고 이미 있는 result를 재사용한다.
    """
    league_name = _CODE_TO_LEAGUE_NAME.get(league)
    all_articles = result.get("korean_articles", []) + result.get("english_articles", [])
    related = _filter_articles_by_league(all_articles, league_name) if league_name else all_articles

    if not related:
        st.info("관련 뉴스도 아직 없습니다. 먼저 ⚡ 분석 실행으로 기사를 수집해주세요.")
        return

    espn_section("📰", "대신 최근 관련 소식을 확인하세요", len(related[:6]))
    col_l, col_r = st.columns(2)
    for i, a in enumerate(related[:6]):
        with col_l if i % 2 == 0 else col_r:
            render_news_card(a, show_image=True)


def render_youtube_tab(result: dict, league: str = None):
    """
    YouTube 하이라이트 탭을 렌더링합니다.

    실제 영상(YOUTUBE_API_KEY 설정 시)만 보여준다. 예전엔 키가 없을 때
    무관한 스톡사진을 붙인 Mock 영상 그리드를 보여줬는데, 사용자 피드백에
    따라 완전히 제거했다 — 비시즌이면 시즌 배너 + 관련 뉴스로, 시즌
    중인데 API 키가 없으면 안내 문구만 보여준다.
    """
    videos = result.get("youtube_videos", [])
    has_api_key = bool(_os.getenv("YOUTUBE_API_KEY"))
    is_mock = any(v.get("source") == "youtube_mock" for v in videos)

    if render_off_season_notice(league):
        # 비시즌: 영상 대신 관련 리그 뉴스를 대안으로 보여준다
        _render_related_news(result, league)
        return

    if has_api_key and videos and not is_mock:
        # 실제 YouTube API로 가져온 진짜 영상 — 정상 렌더링
        espn_section("▶️", "Football Highlights", len(videos))
        col_l, col_r = st.columns(2)
        for i, v in enumerate(videos[:12]):
            with col_l if i % 2 == 0 else col_r:
                thumb = v.get("thumbnail", "")
                title = v.get("title", "")[:70]
                channel = v.get("channel", "")
                url = v.get("url", "#")
                query = v.get("query", "")
                pub = str(v.get("published_at", ""))[:10]
                thumb_html = (
                    f'<img src="{thumb}" style="width:100%;height:140px;object-fit:cover;'
                    f'border-radius:4px 4px 0 0;" onerror="this.style.display=\'none\'">'
                    if thumb else ""
                )
                _html(f"""
<div style="background:#FFFFFF;border-radius:6px;overflow:hidden;
     box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:16px;">
  {thumb_html}
  <div style="padding:12px 14px;">
    <div style="font-size:11px;color:#CC0000;font-family:Oswald,sans-serif;
         font-weight:700;text-transform:uppercase;margin-bottom:4px;">{query}</div>
    <a href="{url}" target="_blank" style="font-size:13px;font-weight:600;
       color:#1A1A1A;text-decoration:none;line-height:1.4;">{title}</a>
    <div style="font-size:11px;color:#888;margin-top:6px;">{channel} &nbsp;·&nbsp; {pub}</div>
  </div>
</div>
""")
        return

    # 시즌 중인데 API 키가 없거나(Mock) 영상이 없는 경우 — 무관한 스톡사진을
    # 진짜 영상처럼 보여주는 대신, 정직하게 안내만 하고 관련 뉴스로 대체한다.
    if not has_api_key:
        _html("""
<div style="background:#FFF3E0;border-left:4px solid #FFA000;border-radius:0 6px 6px 0;
     padding:12px 16px;margin-bottom:16px;font-size:13px;color:#555;">
  📺 YouTube API 키가 설정되지 않아 실제 하이라이트 영상을 불러올 수 없습니다.
  <strong>YOUTUBE_API_KEY</strong>를 .env에 입력하면 여기에 실제 영상이 표시됩니다.<br>
  <span style="font-size:11px;color:#888;">발급: https://console.cloud.google.com → YouTube Data API v3</span>
</div>
""")
    else:
        st.info("영상 데이터가 없습니다. 파이프라인을 실행하세요.")

    _render_related_news(result, league)
