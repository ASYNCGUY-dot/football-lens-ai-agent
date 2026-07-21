# -*- coding: utf-8 -*-
"""tabs/youtube.py — YouTube 하이라이트 탭."""
import streamlit as st

from components import _html, espn_section


def render_youtube_tab(result: dict):
    """YouTube 하이라이트 탭을 렌더링합니다."""
    videos = result.get("youtube_videos", [])

    import os as _os
    if not _os.getenv("YOUTUBE_API_KEY"):
        _html("""
<div style="background:#FFF3E0;border-left:4px solid #FFA000;border-radius:0 6px 6px 0;
     padding:12px 16px;margin-bottom:16px;font-size:13px;color:#555;">
  📺 YouTube API 키가 설정되지 않았습니다. Mock 영상을 표시하거나 실제 영상을 보려면
  <strong>YOUTUBE_API_KEY</strong>를 .env에 입력하세요.<br>
  <span style="font-size:11px;color:#888;">발급: https://console.cloud.google.com → YouTube Data API v3</span>
</div>
""")

    if not videos:
        st.info("영상 데이터가 없습니다. 파이프라인을 실행하세요.")
        return

    espn_section("▶️", "Football Highlights", len(videos))
    col_l, col_r = st.columns(2)
    for i, v in enumerate(videos[:12]):
        with col_l if i % 2 == 0 else col_r:
            thumb = v.get("thumbnail", "")
            is_mock = v.get("source") == "youtube_mock"
            title = v.get("title", "")[:70]
            channel = v.get("channel", "")
            url = v.get("url", "#")
            query = v.get("query", "")
            pub = str(v.get("published_at", ""))[:10]
            if is_mock:
                # Mock 데이터는 실제 영상 썸네일이 없다. 관련 없는 스톡사진을
                # 진짜 썸네일처럼 보여주면 오해를 주므로, 재생 아이콘 +
                # "MOCK" 라벨이 명확한 플레이스홀더로 대체한다.
                thumb_html = (
                    '<div style="width:100%;height:140px;border-radius:4px 4px 0 0;'
                    'background:linear-gradient(135deg,#2A2A2A,#1A1A1A);'
                    'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;">'
                    '<span style="font-size:32px;opacity:0.6;">▶️</span>'
                    '<span style="font-size:10px;color:#FFF;background:#CC0000;padding:2px 8px;'
                    'border-radius:2px;font-family:Oswald,sans-serif;font-weight:700;'
                    'letter-spacing:0.5px;">MOCK — 실제 영상 아님</span>'
                    '</div>'
                )
            else:
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
