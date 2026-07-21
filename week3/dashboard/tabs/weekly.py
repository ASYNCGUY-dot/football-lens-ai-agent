# -*- coding: utf-8 -*-
"""tabs/weekly.py — 주간 보고서 탭."""
from datetime import datetime

import streamlit as st

from constants import IMG_TROPHY, _LEAGUE_DISPLAY
from components import _html, espn_section


def render_weekly_report(result: dict, league: str = None):
    """
    주간 보고서 탭을 렌더링합니다.
    league가 지정되면 해당 리그/대회 이름이 섹션 헤더에 표시됩니다.
    """
    league_display = _LEAGUE_DISPLAY.get(league, league or "⚽ 축구")

    if not result:
        _html(f"""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<img src="{IMG_TROPHY}" style="width:100%;height:120px;object-fit:cover;border-radius:3px;margin-bottom:16px;opacity:0.5;" alt="trophy">
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">주간 보고서 없음</div>
<div style="font-size:14px;color:#888;">기간을 <strong style="color:#CC0000;">7일 이상</strong>으로 설정 후 분석을 실행하세요</div>
</div>
""")
        return

    espn_section("📊", f"Weekly Report — {league_display}")

    final_report = result.get("final_report", "")
    if final_report:
        _html('<div style="background:#FFFFFF;border:1px solid #E5E5E5;border-radius:4px;padding:28px 32px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">')
        st.markdown(final_report)
        _html('</div>')
        st.download_button(
            label="📥 보고서 다운로드 (.md)",
            data=final_report,
            file_name=f"football_lens_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )
    else:
        st.info("보고서 데이터가 없습니다.")
