# -*- coding: utf-8 -*-
"""tabs/standings.py — EPL 순위표 탭."""
import streamlit as st

from constants import IMG_TROPHY
from components import _html, espn_section


def render_standings_tab(result: dict):
    """EPL 순위표 탭을 렌더링합니다."""
    standings = result.get("raw_standings", [])
    if not standings:
        _html(f"""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<img src="{IMG_TROPHY}" style="width:100%;height:100px;object-fit:cover;border-radius:3px;margin-bottom:16px;opacity:0.5;" alt="trophy">
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">순위 데이터 없음</div>
<div style="font-size:14px;color:#888;">EPL 분석을 먼저 실행해주세요</div>
</div>
""")
        return

    try:
        import pandas as pd
        import plotly.express as px

        df = pd.DataFrame(standings)
        display_cols = ["rank", "team_name", "played", "won", "draw", "lost",
                        "goals_for", "goals_against", "goal_diff", "points", "form"]
        col_labels = {
            "rank": "순위", "team_name": "팀", "played": "경기",
            "won": "승", "draw": "무", "lost": "패",
            "goals_for": "득점", "goals_against": "실점",
            "goal_diff": "득실차", "points": "승점", "form": "최근 5경기",
        }
        available_cols = [c for c in display_cols if c in df.columns]
        df_display = df[available_cols].rename(columns=col_labels)

        espn_section("📋", "EPL Standings")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        if "team_name" in df.columns and "points" in df.columns:
            espn_section("📊", "Top 10 Points")
            fig = px.bar(
                df.head(10),
                x="team_name", y="points",
                color="points",
                color_continuous_scale=[[0, "#F5C6C6"], [0.5, "#FF4444"], [1, "#CC0000"]],
                text="points",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                font=dict(color="#1A1A1A", family="Oswald"),
                xaxis=dict(tickangle=-30, gridcolor="#EEEEEE", linecolor="#DDDDDD", title=None, tickfont=dict(family="Oswald", size=11)),
                yaxis=dict(gridcolor="#EEEEEE", linecolor="#DDDDDD", title="승점"),
                coloraxis_showscale=False, showlegend=False,
                margin=dict(t=20, b=40, l=20, r=20), height=320,
            )
            fig.update_traces(
                textposition="outside",
                textfont=dict(color="#CC0000", size=12, family="Oswald"),
                marker_line_color="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        for team in standings[:10]:
            _html(f"""
<div class="espn-card">
<div class="espn-card-tag">EPL Standings</div>
<div class="espn-card-title"><span style="color:#CC0000;margin-right:10px;">{team.get('rank','?')}위</span>{team.get('team_name','?')}</div>
<div class="espn-card-meta"><span class="ebadge eb-red">{team.get('points',0)}pts</span><span class="ebadge eb-dark">{team.get('won',0)}W</span><span class="ebadge eb-gray">{team.get('draw',0)}D</span><span>{team.get('lost',0)}L</span></div>
</div>
""")
    except Exception as e:
        st.error(f"순위표 오류: {e}")
