# -*- coding: utf-8 -*-
"""
test_football_data_standings.py
================================
week1/collectors/football_data_collector.py의 get_standings()에 대한
테스트. 조별리그(코파리베르타도레스처럼 Group A~H로 나뉜 대회)에서
첫 조 4팀만 반환하고 나머지 28팀을 버리던 버그를 고정해 둔다
(2026-07-24 발견 — get_standings()가 data["standings"][0]만 읽고
있었는데, 실제로는 조별리그 대회는 standings 배열에 조마다 항목이
따로 들어있었다).
"""
import unittest.mock as mock

from football_data_collector import FootballDataCollector


def _make_group(group_name, teams):
    """football-data.org API 응답의 한 그룹(standings 배열 원소) 형태를 만든다."""
    return {
        "group": group_name,
        "type": "TOTAL",
        "table": [
            {
                "position": i + 1,
                "team": {"id": t["id"], "name": t["name"]},
                "playedGames": 4, "won": 3, "draw": 0, "lost": 1,
                "goalsFor": 8, "goalsAgainst": 3, "goalDifference": 5,
                "points": 9, "form": "WWWL",
            }
            for i, t in enumerate(teams)
        ],
    }


def _collector():
    return FootballDataCollector(api_key="fake-key-for-test", competition="CLI")


def test_single_group_league_has_none_group_field():
    """대부분의 단일 리그(EPL 등)는 group이 None으로 채워져야 한다(기존 동작 유지)."""
    c = _collector()
    fake_data = {
        "standings": [_make_group(None, [{"id": 1, "name": "팀A"}, {"id": 2, "name": "팀B"}])],
    }
    with mock.patch.object(c, "_request", return_value=fake_data):
        standings = c.get_standings()
    assert len(standings) == 2
    assert all(s["group"] is None for s in standings)


def test_multi_group_competition_returns_all_teams_not_just_first_group():
    """
    핵심 회귀 케이스: 코파리베르타도레스처럼 8개 조(각 4팀)인 대회는
    32팀 전체가 나와야 한다 — 예전엔 data["standings"][0]["table"]만
    읽어서 4팀만 반환했다.
    """
    c = _collector()
    groups = [
        _make_group(f"Group {chr(65+i)}", [{"id": i * 4 + j, "name": f"팀{i}-{j}"} for j in range(4)])
        for i in range(8)
    ]
    fake_data = {"standings": groups}
    with mock.patch.object(c, "_request", return_value=fake_data):
        standings = c.get_standings()
    assert len(standings) == 32


def test_multi_group_teams_tagged_with_correct_group_name():
    c = _collector()
    groups = [
        _make_group("Group A", [{"id": 1, "name": "보카"}]),
        _make_group("Group B", [{"id": 2, "name": "리버"}]),
    ]
    fake_data = {"standings": groups}
    with mock.patch.object(c, "_request", return_value=fake_data):
        standings = c.get_standings()
    by_name = {s["team_name"]: s["group"] for s in standings}
    assert by_name["보카"] == "Group A"
    assert by_name["리버"] == "Group B"


def test_non_total_type_entries_are_skipped():
    """HOME/AWAY 같은 TOTAL이 아닌 서브테이블이 섞여 있어도 무시해야 한다."""
    c = _collector()
    home_away_entry = _make_group("Group A", [{"id": 1, "name": "팀A"}])
    home_away_entry["type"] = "HOME"
    total_entry = _make_group("Group A", [{"id": 1, "name": "팀A"}, {"id": 2, "name": "팀B"}])
    fake_data = {"standings": [home_away_entry, total_entry]}
    with mock.patch.object(c, "_request", return_value=fake_data):
        standings = c.get_standings()
    assert len(standings) == 2


def test_empty_response_returns_empty_list():
    c = _collector()
    with mock.patch.object(c, "_request", return_value=None):
        assert c.get_standings() == []
