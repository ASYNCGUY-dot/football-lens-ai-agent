# -*- coding: utf-8 -*-
"""
season_info.py
===============
리그별 시즌 진행 여부를 판별하고, 비시즌일 때 공통으로 쓰는 안내 카드를
렌더링한다. 원래 경기 예측 탭에만 있던 로직을 공용화해서 일간/주간
보고서 탭에도 같은 방식으로 적용한다(예측 탭 자체는 이후 제거됨).

시즌 날짜 값은 week1/league_registry.py에 있다(2025/26 시즌 기준) —
시즌이 바뀌면 그 파일에서 갱신하면 된다.
"""

from components import _html
from league_registry import LEAGUES as _LEAGUES

# (season_start, season_end, next_season_start, league_display)
# week1/league_registry.py의 season/full_name 필드에서 파생한다 — 예전엔
# 이 파일에 직접 정의돼 있어서 리그를 추가할 때마다 여기도 따로 고쳐야
# 했다.
LEAGUE_SEASON = {
    code: (*meta["season"], meta["full_name"])
    for code, meta in _LEAGUES.items()
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
