# -*- coding: utf-8 -*-
"""
test_kleague_collector.py
==========================
week1/collectors/kleague_collector.py의 순수 파싱 로직에 대한 테스트.
네트워크 호출 없이 kleague.com이 실제로 반환한 형태의 raw dict를
직접 넣어서 검증한다.

_parse_schedule_row의 "완료 여부" 판정은 실제로 한 번 틀렸던 지점이라
(homeGoal이 예정 경기에도 null이 아니라 0으로 채워져 있어서, 이걸
기준으로 삼으면 예정 경기가 전부 "0-0 완료 경기"로 오분류됐다 —
2026-07-22, 실측으로 발견) 회귀 테스트로 고정해 둔다.
"""
from kleague_collector import KLeagueCollector


def _make_collector():
    return KLeagueCollector(league_id="1", year=2026)


def test_finished_match_uses_endYn_not_zero_goals():
    """endYn='Y'인 경기는 실제 스코어(0-0 포함)를 그대로 살려야 한다."""
    c = _make_collector()
    row = {
        "gameId": 1, "roundId": 12, "gameDate": "2026.07.12", "gameTime": "19:30",
        "homeTeam": "K22", "homeTeamName": "광주", "awayTeam": "K03", "awayTeamName": "포항",
        "homeGoal": 0, "awayGoal": 0, "endYn": "Y",
    }
    parsed = c._parse_schedule_row(row)
    assert parsed["status"] == "FINISHED"
    assert parsed["home_score"] == 0
    assert parsed["away_score"] == 0
    assert parsed["winner"] == "DRAW"


def test_unstarted_match_with_zero_goal_placeholder_is_not_finished():
    """
    핵심 회귀 케이스: endYn='N'인 예정 경기는 homeGoal/awayGoal이 0으로
    채워져 있어도 반드시 SCHEDULED로 분류돼야 하고, 점수는 None이어야
    한다(실제로 0-0 경기와 구분이 안 되면 안 됨).
    """
    c = _make_collector()
    row = {
        "gameId": 2, "roundId": 18, "gameDate": "2026.07.25", "gameTime": "19:30",
        "homeTeam": "K03", "homeTeamName": "포항", "awayTeam": "K05", "awayTeamName": "전북",
        "homeGoal": 0, "awayGoal": 0, "endYn": "N",
    }
    parsed = c._parse_schedule_row(row)
    assert parsed["status"] == "SCHEDULED"
    assert parsed["home_score"] is None
    assert parsed["away_score"] is None
    assert parsed["winner"] is None


def test_winner_determined_correctly_for_finished_match():
    c = _make_collector()
    row = {
        "gameId": 3, "roundId": 17, "gameDate": "2026.07.11", "gameTime": "19:30",
        "homeTeam": "K01", "homeTeamName": "울산", "awayTeam": "K05", "awayTeamName": "전북",
        "homeGoal": 1, "awayGoal": 3, "endYn": "Y",
    }
    parsed = c._parse_schedule_row(row)
    assert parsed["winner"] == "AWAY_TEAM"


def test_standings_field_mapping():
    """teamRank.do의 실제 필드명이 football_data_collector와 동일한 스키마로 변환되는지 확인."""
    c = _make_collector()
    row = {
        "teamId": "K09", "teamName": "서울", "rank": 1, "gainPoint": 39,
        "winCnt": 12, "tieCnt": 3, "lossCnt": 3,
        "gainGoal": 31, "lossGoal": 13, "gapCnt": 18, "gameCount": 18,
        "game01": "승", "game02": "무", "game03": "승", "game04": "승", "game05": "승", "game06": "패",
    }
    data = {"teamRank": [row]}
    import unittest.mock as mock
    with mock.patch.object(c, "_post", return_value=data):
        standings = c.get_standings()
    assert len(standings) == 1
    s = standings[0]
    assert s["team_name"] == "서울"
    assert s["played"] == 18
    assert s["won"] == 12
    assert s["draw"] == 3
    assert s["lost"] == 3
    assert s["goals_for"] == 31
    assert s["goals_against"] == 13
    assert s["goal_diff"] == 18
    assert s["points"] == 39
    assert s["form"] == "WDWWWL"


def test_top_scorers_field_mapping():
    c = _make_collector()
    row = {
        "rank": 1, "playerId": "20230315", "name": "야고", "teamId": "K01",
        "teamName": "울산", "goalQty": 8, "assistQty": 0,
    }
    data = {"list": [row]}
    import unittest.mock as mock
    with mock.patch.object(c, "_post", return_value=data):
        scorers = c.get_top_scorers(limit=10)
    assert len(scorers) == 1
    s = scorers[0]
    assert s["player_name"] == "야고"
    assert s["team_name"] == "울산"
    assert s["goals"] == 8
    assert s["assists"] == 0


def test_post_returns_none_on_non_200_result_code():
    """kleague.com이 정상 HTTP 200이면서도 resultCode로 실패를 알리는 경우를 처리한다."""
    c = _make_collector()
    import unittest.mock as mock
    fake_response = mock.MagicMock()
    fake_response.json.return_value = {"resultCode": "500", "resultMsg": "오류"}
    fake_response.raise_for_status.return_value = None
    with mock.patch("kleague_collector.requests.post", return_value=fake_response):
        result = c._post("/record/teamRank.do")
    assert result is None
