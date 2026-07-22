# -*- coding: utf-8 -*-
"""
test_players.py
================
week3/dashboard/tabs/players.py의 순수 함수 두 개에 대한 테스트.

compute_player_stats/spotlight_candidates는 이번 세션에서 하드코딩된
LEAGUE_SPOTLIGHT_PLAYERS 목록("선수가 다른 리그로 이적해도 계속
후보로 남는" 문제)을 실시간 top_scorers API 데이터 기반으로 갈아
끼운 부분이라, 데이터 형태가 바뀌어도 동작이 깨지지 않는지 고정해
둔다.
"""
from players import compute_player_stats, spotlight_candidates


def test_spotlight_candidates_dedupes_preserving_order():
    top_scorers = [
        {"player_name": "홀란드", "goals": 20},
        {"player_name": "살라", "goals": 18},
        {"player_name": "홀란드", "goals": 20},  # 중복 (동일 선수, 여러 대회 집계 등)
    ]
    result = spotlight_candidates(top_scorers)
    assert result == ["홀란드", "살라"]


def test_spotlight_candidates_skips_blank_names():
    top_scorers = [{"player_name": ""}, {"player_name": "  "}, {"player_name": "손흥민"}]
    result = spotlight_candidates(top_scorers)
    assert result == ["손흥민"]


def test_spotlight_candidates_caps_at_ten():
    top_scorers = [{"player_name": f"선수{i}"} for i in range(15)]
    result = spotlight_candidates(top_scorers)
    assert len(result) == 10


def test_spotlight_candidates_empty_for_unsupported_league():
    """K리그처럼 football-data.org 미지원 리그는 top_scorers가 아예 빈 리스트로 온다."""
    assert spotlight_candidates([]) == []


def test_compute_player_stats_matches_title_and_summary():
    articles = [
        {"article_id": "1", "title": "손흥민 멀티골 활약", "summary": ""},
        {"article_id": "2", "title": "토트넘 2연승", "summary": "손흥민 부상 복귀전"},
        {"article_id": "3", "title": "무관한 기사", "summary": "무관한 내용"},
    ]
    sentiments = {
        "1": {"sentiment_score": 0.8, "sentiment_label": "긍정"},
        "2": {"sentiment_score": -0.2, "sentiment_label": "부정"},
    }
    stats = compute_player_stats("손흥민", articles, sentiments)
    assert stats["article_count"] == 2
    assert stats["positive_count"] == 1
    assert stats["negative_count"] == 1
    assert stats["avg_sentiment"] == (0.8 + -0.2) / 2


def test_compute_player_stats_no_matches_returns_none_avg():
    stats = compute_player_stats("존재하지않는선수", [{"title": "다른 기사", "summary": ""}], {})
    assert stats["article_count"] == 0
    assert stats["avg_sentiment"] is None


def test_compute_player_stats_article_without_sentiment_excluded_from_average():
    """감정분석이 안 된(article_id가 sentiments_by_id에 없는) 기사는 평균 계산에서 빠져야 한다."""
    articles = [
        {"article_id": "1", "title": "손흥민 골", "summary": ""},
        {"article_id": "2", "title": "손흥민 인터뷰", "summary": ""},
    ]
    sentiments = {"1": {"sentiment_score": 1.0, "sentiment_label": "긍정"}}
    stats = compute_player_stats("손흥민", articles, sentiments)
    assert stats["article_count"] == 2
    assert stats["avg_sentiment"] == 1.0
