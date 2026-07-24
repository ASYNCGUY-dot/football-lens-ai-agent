# -*- coding: utf-8 -*-
"""tabs/standings.py — 순위표 탭."""
import streamlit as st

from constants import IMG_TROPHY
from components import _html, espn_section
from league_registry import LEAGUES as _LEAGUES


def render_standings_tab(result: dict, league: str = "PL"):
    """
    리그 순위표 탭을 렌더링합니다.

    예전엔 "EPL Standings"로 제목이 고정돼 있었는데, K리그도 이제
    실제 순위표 데이터가 채워지면서(kleague_collector.py, 2026-07-22)
    다른 리그를 봐도 항상 EPL이라고 나오는 게 어색해져서 리그별로
    바뀌도록 고쳤다.
    """
    league_meta = _LEAGUES.get(league, {})
    league_name = league_meta.get("full_name", league)

    standings = result.get("raw_standings", [])
    if not standings:
        _html(f"""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<img src="{IMG_TROPHY}" style="width:100%;height:100px;object-fit:cover;border-radius:3px;margin-bottom:16px;opacity:0.5;" alt="trophy">
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">순위 데이터 없음</div>
<div style="font-size:14px;color:#888;">{league_name} 분석을 먼저 실행해주세요</div>
</div>
""")
        return

    # 코파리베르타도레스처럼 조별리그(Group A~H)로 진행되는 대회는 팀마다
    # group 필드가 채워져 있다(2026-07-24, football_data_collector.py의
    # get_standings() 참고 — 예전엔 이 필드 자체가 없어서 A조 4팀만 반환
    # 하고 나머지 28팀을 통째로 버렸었다). group이 하나라도 있으면 조별로
    # 나눠서 보여주고, 없으면(대부분의 단일 리그) 기존처럼 표 하나로
    # 합쳐서 보여준다.
    groups_present = sorted({s["group"] for s in standings if s.get("group")})

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

        if groups_present:
            espn_section("📋", f"{league_name} Standings — {len(groups_present)}개 조")
            # 2열로 배치 (조가 많아도 화면을 세로로 너무 길게 만들지 않도록)
            for i in range(0, len(groups_present), 2):
                cols = st.columns(2)
                for col, group_name in zip(cols, groups_present[i:i + 2]):
                    with col:
                        st.caption(f"**{group_name}**")
                        group_df = df[df["group"] == group_name].sort_values("rank")
                        st.dataframe(
                            group_df[available_cols].rename(columns=col_labels),
                            use_container_width=True, hide_index=True,
                        )
        else:
            espn_section("📋", f"{league_name} Standings")
            df_display = df[available_cols].rename(columns=col_labels)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        if "team_name" in df.columns and "points" in df.columns:
            espn_section("📊", "Top 10 Points")
            # head(10)은 리스트 순서(=조 순서) 그대로 앞 10개를 뽑아서,
            # 조별리그에서는 실제 승점 상위 10팀이 아니라 앞쪽 조 몇 개만
            # 나올 수 있었다. points 기준으로 명시 정렬해서 group 유무와
            # 무관하게 항상 진짜 승점 top10이 나오도록 했다.
            top10 = df.sort_values("points", ascending=False).head(10)
            fig = px.bar(
                top10,
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
            tag = f"{league_name} · {team['group']}" if team.get("group") else league_name
            _html(f"""
<div class="espn-card">
<div class="espn-card-tag">{tag} Standings</div>
<div class="espn-card-title"><span style="color:#CC0000;margin-right:10px;">{team.get('rank','?')}위</span>{team.get('team_name','?')}</div>
<div class="espn-card-meta"><span class="ebadge eb-red">{team.get('points',0)}pts</span><span class="ebadge eb-dark">{team.get('won',0)}W</span><span class="ebadge eb-gray">{team.get('draw',0)}D</span><span>{team.get('lost',0)}L</span></div>
</div>
""")
    except Exception as e:
        st.error(f"순위표 오류: {e}")
