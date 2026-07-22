# -*- coding: utf-8 -*-
"""
season_info.py
===============
리그별 시즌 진행 여부를 판별하고, 비시즌일 때 공통으로 쓰는 안내 카드를
렌더링한다. 원래 tabs/prediction.py에만 있던 로직을 공용화해서
일간/주간 보고서 탭에도 같은 방식으로 적용한다.

날짜 값은 2025/26 시즌 기준으로 하드코딩돼 있다 — 시즌이 바뀌면 갱신 필요.
"""

from datetime import date as _date

from components import _html

# (season_start, season_end, next_season_start, league_display)
LEAGUE_SEASON = {
    # WC 2026: 2026-06-11 ~ 2026-07-19
    "WC":  (_date(2026, 6, 11),  _date(2026, 7, 19),  None,                "2026 FIFA 월드컵"),
    # EPL 2025/26: ~2026-05-24 종료, 2026/27 개막 예정 2026-08-08
    "PL":  (_date(2025, 8, 16),  _date(2026, 5, 24),  _date(2026, 8, 8),   "EPL 프리미어리그"),
    # La Liga 2025/26
    "PD":  (_date(2025, 8, 15),  _date(2026, 6, 1),   _date(2026, 8, 15),  "라리가"),
    # Bundesliga 2025/26: 8월 개막, 5월 종료
    "BL1": (_date(2025, 8, 22),  _date(2026, 5, 23),  _date(2026, 8, 7),   "분데스리가"),
    # Serie A 2025/26
    "SA":  (_date(2025, 8, 23),  _date(2026, 5, 31),  _date(2026, 8, 21),  "세리에A"),
    # Ligue 1 2025/26
    "FL1": (_date(2025, 8, 16),  _date(2026, 5, 24),  _date(2026, 8, 9),   "리그앙"),
    # K리그1 2025: 2~11월
    "KL1": (_date(2026, 2, 21),  _date(2026, 11, 30), None,                "K리그1"),
    # UEFA 챔피언스리그 — football-data.org API currentSeason 값으로 확인(2026-07-21)
    "CL":  (_date(2025, 9, 16),  _date(2026, 5, 30),  _date(2026, 9, 15),  "UEFA 챔피언스리그"),
    # 브라질 세리에A — API currentSeason 확인(2026-07-21): 2026-01-28~12-02
    "BSA": (_date(2026, 1, 28),  _date(2026, 12, 2),  _date(2027, 1, 27),  "브라질 세리에A"),
    # 코파 리베르타도레스 — API currentSeason 확인(2026-07-21): 2026-02-04~11-28
    "CLI": (_date(2026, 2, 4),   _date(2026, 11, 28), _date(2027, 2, 3),   "코파 리베르타도레스"),
    # EFL 챔피언십 — API currentSeason(다음 시즌) 확인(2026-07-22): 2026-08-14~2027-05-01
    "ELC": (_date(2025, 8, 9),   _date(2026, 5, 3),   _date(2026, 8, 14),  "EFL 챔피언십"),
    # 에레디비시 — API currentSeason(다음 시즌) 확인(2026-07-22): 2026-08-07~2027-05-23
    "DED": (_date(2025, 8, 8),   _date(2026, 5, 24),  _date(2026, 8, 7),   "에레디비시"),
    # 프리메이라리가 — API currentSeason(다음 시즌) 확인(2026-07-22): 2026-08-08~2027-05-16
    "PPL": (_date(2025, 8, 15),  _date(2026, 5, 17),  _date(2026, 8, 8),   "프리메이라리가"),
}


def get_season_status(league: str) -> dict | None:
    """
    리그의 시즌 진행 여부를 반환한다. 시즌 정보가 없는 리그면 None.

    Returns
    -------
    dict | None
        {"in_season": bool, "league_display": str, "next_start": date|None,
         "days_left": int|None}
    """
    info = LEAGUE_SEASON.get(league)
    if not info:
        return None
    s_start, s_end, next_start, lg_name = info
    today = _date.today()
    in_season = s_start <= today <= s_end
    days_left = (next_start - today).days if next_start else None
    return {
        "in_season": in_season,
        "league_display": lg_name,
        "next_start": next_start,
        "days_left": days_left,
    }


def render_off_season_notice(league: str, context: str = "") -> bool:
    """
    비시즌이면 안내 카드를 렌더링하고 True를 반환한다 (호출부는 이때 return
    하면 됨). 시즌 중이거나 시즌 정보가 없는 리그(WC 등)면 아무것도 하지
    않고 False를 반환한다.

    Parameters
    ----------
    league : str
        현재 선택된 리그 코드
    context : str
        탭마다 다른 안내 문구 (예: "일간 보고서를 보려면", "예측을 보려면")
    """
    status = get_season_status(league)
    if not status or status["in_season"] or league == "WC":
        return False

    lg_name = status["league_display"]
    next_start = status["next_start"]
    days_left = status["days_left"]
    if next_start:
        next_str = next_start.strftime("%Y년 %m월 %d일")
        countdown = f"{days_left}일 후" if days_left and days_left > 0 else "곧 개막"
    else:
        next_str = "미정"
        countdown = ""

    context_line = f"<div style=\"font-size:13px;color:#888;margin-top:8px;\">{context}</div>" if context else ""

    _html(f"""
<div style="background:#FFFFFF;border-radius:8px;border:2px solid #E0E0E0;padding:48px 32px;text-align:center;margin-top:16px;">
<div style="font-size:56px;margin-bottom:16px;">🏖️</div>
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">{lg_name} — 비시즌</div>
<div style="font-size:15px;color:#555;margin-bottom:20px;">현재 시즌 중이 아닙니다. 다른 리그를 찾아볼까요?</div>
<div style="display:inline-block;background:#CC0000;color:#FFF;border-radius:6px;padding:14px 28px;">
  <div style="font-size:11px;font-family:'Oswald',sans-serif;text-transform:uppercase;letter-spacing:1px;opacity:0.85;margin-bottom:4px;">다음 시즌 개막</div>
  <div style="font-family:'Oswald',sans-serif;font-size:24px;font-weight:700;">{next_str}</div>
  <div style="font-size:13px;margin-top:4px;opacity:0.9;">{countdown}</div>
</div>
{context_line}
</div>
""")
    return True
