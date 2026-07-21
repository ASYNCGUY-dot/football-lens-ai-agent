# -*- coding: utf-8 -*-
"""tabs/worldcup.py — 2026 FIFA 월드컵 탭."""
from datetime import datetime

import streamlit as st

from components import _html, espn_section, render_news_card


def render_worldcup_tab(result: dict):
    """2026 FIFA 월드컵 탭 — 그룹 순위 · 경기 일정 · 득점 순위 · 관련 뉴스"""

    # ── 헤더 배너 ─────────────────────────────────────────────
    _html("""
<div style="background:linear-gradient(135deg,#003399 0%,#CC0000 100%);
     border-radius:8px;padding:24px 28px;margin-bottom:20px;color:#FFF;
     display:flex;align-items:center;gap:20px;">
  <div style="font-size:52px;line-height:1;">🌍</div>
  <div>
    <div style="font-family:'Oswald',sans-serif;font-size:26px;font-weight:700;
         text-transform:uppercase;letter-spacing:1px;">2026 FIFA World Cup</div>
    <div style="font-size:13px;opacity:0.85;margin-top:4px;">
      🇺🇸 미국 · 🇨🇦 캐나다 · 🇲🇽 멕시코 &nbsp;|&nbsp; 48개국 · 12조 · 104경기
    </div>
  </div>
</div>
""")

    groups   = result.get("worldcup_groups", [])
    matches  = result.get("worldcup_matches", [])
    scorers  = result.get("worldcup_scorers", [])

    # 파이프라인 미실행 안내
    if not groups and not matches and not scorers:
        _html("""
<div style="background:#FFF8E1;border-left:4px solid #FFA000;border-radius:0 6px 6px 0;
     padding:16px 20px;font-size:13px;color:#555;">
  ⚡ <strong>분석 실행</strong> 후 월드컵 데이터가 표시됩니다.<br>
  <span style="font-size:12px;color:#888;">football-data.org API 키가 필요합니다 (무료 플랜 지원).</span>
</div>
""")
        # 월드컵 관련 뉴스 (API 없어도 표시)
        _render_worldcup_news(result)
        return

    # ── 탭 내 서브 섹션 ──────────────────────────────────────
    sec_groups, sec_scenarios, sec_matches, sec_scorers, sec_news = st.tabs(
        ["🗂️ 그룹 순위", "🎲 경우의 수", "📅 경기 일정·결과", "⚽ 득점 순위", "📰 관련 뉴스"]
    )

    # ── 그룹 순위 ─────────────────────────────────────────────
    with sec_groups:
        if not groups:
            st.info("그룹 순위 데이터를 불러오지 못했습니다.")
        else:
            espn_section("🗂️", "Group Stage Standings", len(groups))
            # 3열 그리드로 표시
            COLS = 3
            for row_start in range(0, len(groups), COLS):
                cols = st.columns(COLS)
                for col_idx, grp in enumerate(groups[row_start:row_start + COLS]):
                    with cols[col_idx]:
                        label = grp.get("group_label", grp.get("group", ""))
                        _html(f'<div style="font-family:Oswald,sans-serif;font-size:14px;font-weight:700;'
                              f'color:#CC0000;text-transform:uppercase;letter-spacing:0.5px;'
                              f'margin-bottom:6px;border-bottom:2px solid #CC0000;padding-bottom:4px;">'
                              f'{label}</div>')
                        table_rows = ""
                        for t in grp.get("standings", []):
                            pos   = t["position"]
                            name  = t.get("team_short", t.get("team_name", ""))[:18]
                            pts   = t.get("points", 0)
                            played = t.get("played", 0)
                            won   = t.get("won", 0)
                            draw  = t.get("draw", 0)
                            lost  = t.get("lost", 0)
                            gd    = t.get("gd", 0)
                            gd_str = f"+{gd}" if gd > 0 else str(gd)
                            # 1·2위: 진출권 (파란 배경)
                            bg = "#E3F2FD" if pos <= 2 else "#FFFFFF"
                            fw = "700" if pos <= 2 else "400"
                            table_rows += (
                                f'<tr style="background:{bg};">'
                                f'<td style="font-weight:{fw};color:#CC0000;width:20px;">{pos}</td>'
                                f'<td style="font-weight:{fw};max-width:120px;overflow:hidden;'
                                f'text-overflow:ellipsis;white-space:nowrap;">{name}</td>'
                                f'<td style="text-align:center;">{played}</td>'
                                f'<td style="text-align:center;">{won}</td>'
                                f'<td style="text-align:center;">{draw}</td>'
                                f'<td style="text-align:center;">{lost}</td>'
                                f'<td style="text-align:center;">{gd_str}</td>'
                                f'<td style="text-align:center;font-weight:700;">{pts}</td>'
                                f'</tr>'
                            )
                        _html(f"""
<table style="width:100%;font-size:11px;border-collapse:collapse;font-family:sans-serif;">
  <thead>
    <tr style="background:#F5F5F5;color:#888;">
      <th style="padding:4px 3px;text-align:left;">#</th>
      <th style="padding:4px 3px;text-align:left;">팀</th>
      <th style="padding:4px 2px;text-align:center;">경</th>
      <th style="padding:4px 2px;text-align:center;">승</th>
      <th style="padding:4px 2px;text-align:center;">무</th>
      <th style="padding:4px 2px;text-align:center;">패</th>
      <th style="padding:4px 2px;text-align:center;">득실</th>
      <th style="padding:4px 2px;text-align:center;">승점</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>
<div style="font-size:10px;color:#AAA;margin-top:4px;">🔵 16강 진출권</div>
""")
                        st.markdown("")

    # ── 경기 일정·결과 ────────────────────────────────────────
    with sec_matches:
        if not matches:
            st.info("최근/예정 경기 데이터가 없습니다.")
        else:
            finished  = [m for m in matches if m.get("status") == "FINISHED"]
            scheduled = [m for m in matches if m.get("status") in ("SCHEDULED", "TIMED")]
            live      = [m for m in matches if m.get("status") == "IN_PLAY"]

            if live:
                espn_section("🔴", "LIVE — 진행 중", len(live))
                for m in live:
                    _render_wc_match_card(m, live=True)

            if finished:
                espn_section("✅", "최근 경기 결과", len(finished))
                for m in sorted(finished, key=lambda x: x.get("utc_date",""), reverse=True)[:10]:
                    _render_wc_match_card(m)

            if scheduled:
                espn_section("📅", "예정 경기", len(scheduled))
                for m in sorted(scheduled, key=lambda x: x.get("utc_date",""))[:10]:
                    _render_wc_match_card(m)

    # ── 경우의 수 ─────────────────────────────────────────────
    with sec_scenarios:
        if not groups:
            st.info("분석 실행 후 경우의 수가 계산됩니다.")
        else:
            espn_section("🎲", "16강 진출 경우의 수", None)
            _html("""
<div style="background:#E3F2FD;border-left:4px solid #1565C0;border-radius:0 6px 6px 0;
     padding:10px 16px;margin-bottom:16px;font-size:12px;color:#1A1A1A;">
  📌 <strong>계산 기준</strong> — 그룹당 3경기, 1·2위 자동 진출 + 각 조 최하위 성적 3위 8팀 추가 진출 (2026 WC 기준)
</div>
""")
            for grp in groups:
                label = grp.get("group_label", grp.get("group", ""))
                standings = grp.get("standings", [])
                if not standings:
                    continue
                scenarios = _calc_wc_scenarios(standings)

                _html(f'<div style="font-family:Oswald,sans-serif;font-size:14px;font-weight:700;'
                      f'color:#003399;text-transform:uppercase;letter-spacing:0.5px;'
                      f'margin:16px 0 8px;border-bottom:2px solid #003399;padding-bottom:4px;">'
                      f'🌍 {label}</div>')

                rows_html = ""
                for sc in scenarios:
                    s_color = sc["color"]
                    s_bg    = sc["bg"]
                    rows_html += f"""
<div style="display:flex;align-items:center;gap:12px;padding:8px 14px;
     background:{s_bg};border-radius:4px;margin-bottom:4px;">
  <div style="font-family:Oswald,sans-serif;font-size:13px;font-weight:700;
       width:28px;color:{s_color};text-align:center;">{sc['pos']}</div>
  <div style="flex:1;font-family:Oswald,sans-serif;font-size:13px;font-weight:600;">
    {sc['team']}</div>
  <div style="font-size:12px;color:#555;min-width:80px;text-align:center;">
    {sc['pts']}점 (잔여{sc['remaining']}경기)</div>
  <div style="min-width:180px;">
    <span style="background:{s_color};color:#FFF;border-radius:3px;
         padding:3px 10px;font-size:11px;font-family:Oswald,sans-serif;font-weight:700;">
      {sc['status']}</span>
    <div style="font-size:11px;color:#666;margin-top:3px;">{sc['detail']}</div>
  </div>
</div>"""
                _html(rows_html)

    # ── 득점 순위 ─────────────────────────────────────────────
    with sec_scorers:
        if not scorers:
            st.info("득점 순위 데이터가 없습니다.")
        else:
            espn_section("⚽", "Top Scorers — 2026 World Cup", len(scorers))
            rows = ""
            for s in scorers:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(s["rank"], f'{s["rank"]}위')
                rows += (
                    f'<tr>'
                    f'<td style="font-size:16px;text-align:center;">{medal}</td>'
                    f'<td><strong>{s.get("player_name","")}</strong>'
                    f'<div style="font-size:11px;color:#888;">{s.get("nationality","")}</div></td>'
                    f'<td style="color:#888;font-size:12px;">{s.get("team_short", s.get("team_name",""))}</td>'
                    f'<td style="text-align:center;font-weight:700;font-size:18px;color:#CC0000;">'
                    f'{s.get("goals",0)}</td>'
                    f'<td style="text-align:center;color:#555;">{s.get("assists",0)}</td>'
                    f'</tr>'
                )
            _html(f"""
<table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:13px;">
  <thead>
    <tr style="background:#CC0000;color:#FFF;">
      <th style="padding:8px 6px;width:40px;">#</th>
      <th style="padding:8px 6px;text-align:left;">선수</th>
      <th style="padding:8px 6px;text-align:left;">국가대표팀</th>
      <th style="padding:8px 6px;text-align:center;">골</th>
      <th style="padding:8px 6px;text-align:center;">어시</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
""")

    # ── 관련 뉴스 ─────────────────────────────────────────────
    with sec_news:
        _render_worldcup_news(result)



def _calc_wc_scenarios(standings: list[dict]) -> list[dict]:
    """
    그룹 순위표를 받아 팀별 16강 진출 경우의 수를 계산합니다.

    2026 WC 규정:
        - 그룹당 4팀, 각 팀 3경기
        - 조 1·2위 자동 진출
        - 각 조 3위 중 상위 8팀도 진출 (wild card)

    Returns
    -------
    list[dict]
        team, pos, pts, remaining, max_pts, status, detail, color, bg
    """
    TOTAL_GAMES = 3  # 4팀 조별리그, 팀당 총 3경기

    # 현재 점수 내림차순 정렬
    sorted_teams = sorted(standings, key=lambda t: (
        -t.get("points", 0), -t.get("gd", 0), -t.get("gf", 0)
    ))

    result = []
    for team in sorted_teams:
        played    = team.get("played", 0)
        remaining = max(0, TOTAL_GAMES - played)
        pts       = team.get("points", 0)
        max_pts   = pts + remaining * 3
        pos       = team.get("position", 0)
        name      = team.get("team_short", team.get("team_name", ""))

        # 다른 팀들의 최대 가능 점수
        others = [t for t in sorted_teams if t is not team]
        others_max = sorted(
            [t.get("points", 0) + max(0, TOTAL_GAMES - t.get("played", 0)) * 3
             for t in others],
            reverse=True,
        )
        # 현재 2위 팀의 최대 가능 점수 (나를 제외한 1위)
        top2_threshold = others_max[1] if len(others_max) >= 2 else 0

        if remaining == 0:
            # 경기 완료 — 최종 순위
            if pos <= 2:
                status = "진출 확정"
                detail = "16강 진출 확정 🎉"
                color, bg = "#2E7D32", "#E8F5E9"
            elif pos == 3:
                status = "3위 대기"
                detail = "타 그룹 3위 성적 비교 후 확정"
                color, bg = "#E65100", "#FFF3E0"
            else:
                status = "탈락 확정"
                detail = "4위 탈락 확정"
                color, bg = "#CC0000", "#FFEBEE"
        else:
            rival_max = [
                t.get("points", 0) + max(0, TOTAL_GAMES - t.get("played", 0)) * 3
                for t in others
            ]
            rival_max_sorted = sorted(rival_max, reverse=True)
            second_rival_max = rival_max_sorted[1] if len(rival_max_sorted) >= 2 else 0

            if pts > second_rival_max:
                status = "진출 확정"
                detail = "수학적 진출 확정 ✅"
                color, bg = "#2E7D32", "#E8F5E9"
            elif max_pts < top2_threshold:
                status = "탈락 확정"
                detail = f"최대 {max_pts}점으로 진출 불가 ❌"
                color, bg = "#CC0000", "#FFEBEE"
            else:
                others_pts_sorted = sorted([t.get("points", 0) for t in others], reverse=True)
                second_pts = others_pts_sorted[1] if len(others_pts_sorted) >= 2 else 0
                pts_needed = max(0, second_pts + 1 - pts)
                wins_needed = (pts_needed + 2) // 3

                if wins_needed == 0:
                    status = "유리한 위치"
                    detail = f"현재 {pos}위, 잔여 {remaining}경기 소화 필요"
                    color, bg = "#1565C0", "#E3F2FD"
                elif wins_needed <= remaining:
                    status = "진출 가능"
                    detail = f"잔여 {remaining}경기 중 {wins_needed}승 이상 필요"
                    color, bg = "#1565C0", "#E3F2FD"
                else:
                    status = "탈락 위기"
                    detail = f"잔여 {remaining}경기 전승해도 불확실"
                    color, bg = "#E65100", "#FFF3E0"

        result.append({
            "team":      name,
            "pos":       pos,
            "pts":       pts,
            "remaining": remaining,
            "max_pts":   max_pts,
            "status":    status,
            "detail":    detail,
            "color":     color,
            "bg":        bg,
        })

    return result



def _render_wc_match_card(m: dict, live: bool = False):
    """월드컵 경기 카드 한 장을 렌더링합니다."""
    status   = m.get("status", "")
    utc_str  = m.get("utc_date", "")
    grp_raw  = m.get("group", "")
    grp      = (grp_raw.replace("GROUP_", "") + "조") if grp_raw else m.get("stage", "")
    home     = m.get("home_short", m.get("home_team", ""))
    away     = m.get("away_short", m.get("away_team", ""))
    h_score  = m.get("home_score")
    a_score  = m.get("away_score")

    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        date_str = dt.strftime("%m/%d %H:%M") + " (UTC)"
    except Exception:
        date_str = utc_str[:16]

    if status == "FINISHED":
        score_html = (
            f'<span style="font-size:22px;font-weight:700;color:#1A1A1A;">'
            f'{h_score} &nbsp;-&nbsp; {a_score}</span>'
        )
        status_badge = '<span style="background:#E8F5E9;color:#2E7D32;border-radius:3px;padding:2px 8px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;">FT</span>'
    elif live:
        score_html = (
            f'<span style="font-size:22px;font-weight:700;color:#CC0000;">'
            f'{h_score or 0} &nbsp;-&nbsp; {a_score or 0}</span>'
        )
        status_badge = '<span style="background:#CC0000;color:#FFF;border-radius:3px;padding:2px 8px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;">LIVE</span>'
    else:
        score_html = f'<span style="font-size:14px;color:#888;">{date_str}</span>'
        status_badge = '<span style="background:#E3F2FD;color:#1565C0;border-radius:3px;padding:2px 8px;font-size:10px;font-family:Oswald,sans-serif;font-weight:700;">예정</span>'

    _html(f"""
<div style="background:#FFFFFF;border-radius:6px;padding:14px 20px;margin-bottom:8px;
     box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:16px;">
  <div style="font-size:11px;min-width:36px;text-align:center;
       font-family:Oswald,sans-serif;font-weight:700;color:#CC0000;">{grp}</div>
  <div style="flex:1;display:flex;align-items:center;justify-content:space-between;gap:12px;">
    <div style="flex:1;text-align:right;font-family:Oswald,sans-serif;font-size:15px;font-weight:700;">{home}</div>
    <div style="text-align:center;min-width:100px;">{score_html}</div>
    <div style="flex:1;text-align:left;font-family:Oswald,sans-serif;font-size:15px;font-weight:700;">{away}</div>
  </div>
  <div style="min-width:52px;text-align:right;">{status_badge}</div>
</div>
""")



def _render_worldcup_news(result: dict):
    """월드컵 관련 기사를 필터링해서 보여줍니다."""
    WC_KEYWORDS = ["월드컵", "world cup", "worldcup", "fifa", "국가대표", "태극전사"]
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    wc_articles = [
        a for a in all_articles
        if any(kw in (a.get("title", "") + a.get("summary", "")).lower() for kw in WC_KEYWORDS)
    ]
    if not wc_articles:
        st.info("월드컵 관련 기사가 없습니다. 분석 실행 후 확인하세요.")
        return
    espn_section("📰", "World Cup News", len(wc_articles))
    col_l, col_r = st.columns(2)
    for i, a in enumerate(wc_articles[:16]):
        with col_l if i % 2 == 0 else col_r:
            render_news_card(a)
