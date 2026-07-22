# -*- coding: utf-8 -*-
"""
test_weekly_highlights.py
==========================
week3/dashboard/tabs/weekly.py의 compute_weekly_highlights()에 대한
테스트. 주간 탭이 일간 탭과 완전히 같은 final_report만 보여주고
"주간"만의 콘텐츠가 없다는 문제(2026-07-22, 사용자 스크린샷)를 고치며
추가한 순수 함수라, 새 LLM/API 호출 없이 기존 파이프라인 데이터만으로
계산이 맞는지 고정해 둔다.
"""
from weekly import compute_weekly_highlights


def _base_result(**overrides):
    base = {
        "korean_articles": [],
        "english_articles": [],
        "article_sentiments": [],
        "korean_summary": {},
        "english_summary": {},
        "transfer_rumors": [],
    }
    base.update(overrides)
    return base


def test_empty_result_yields_zero_counts_and_no_crash():
    h = compute_weekly_highlights(_base_result())
    assert h["article_count"] == 0
    assert h["avg_sentiment"] is None
    assert h["hot_topics"] == []
    assert h["busiest_day"] is None


def test_article_and_language_counts():
    h = compute_weekly_highlights(_base_result(
        korean_articles=[{"title": "a"}, {"title": "b"}],
        english_articles=[{"title": "c"}],
    ))
    assert h["article_count"] == 3
    assert h["ko_count"] == 2
    assert h["en_count"] == 1


def test_positive_tone_label():
    h = compute_weekly_highlights(_base_result(
        article_sentiments=[
            {"sentiment_score": 0.8, "sentiment_label": "긍정"},
            {"sentiment_score": 0.5, "sentiment_label": "긍정"},
        ],
    ))
    assert h["avg_sentiment"] == (0.8 + 0.5) / 2
    assert h["positive_pct"] == 100
    assert h["negative_pct"] == 0
    assert "긍정적" in h["tone_label"]


def test_negative_tone_label():
    h = compute_weekly_highlights(_base_result(
        article_sentiments=[
            {"sentiment_score": -0.6, "sentiment_label": "부정"},
            {"sentiment_score": -0.4, "sentiment_label": "부정"},
        ],
    ))
    assert "무거운" in h["tone_label"]


def test_neutral_tone_label_when_no_sentiment_data():
    h = compute_weekly_highlights(_base_result())
    assert h["tone_label"] == "감정 분석 데이터 없음"


def test_hot_topics_merged_and_deduped_preserving_order():
    h = compute_weekly_highlights(_base_result(
        korean_summary={"key_topics": ["이적시장", "K리그"]},
        english_summary={"key_topics": ["K리그", "챔피언스리그"]},
    ))
    assert h["hot_topics"] == ["이적시장", "K리그", "챔피언스리그"]


def test_hot_topics_capped_at_eight():
    h = compute_weekly_highlights(_base_result(
        korean_summary={"key_topics": [f"토픽{i}" for i in range(12)]},
    ))
    assert len(h["hot_topics"]) == 8


def test_rumor_count_and_top_rumors_sorted_by_recency():
    rumors = [
        {"title": "오래된 루머", "published_at": "2026-07-01T00:00:00"},
        {"title": "최신 루머", "published_at": "2026-07-20T00:00:00"},
        {"title": "중간 루머", "published_at": "2026-07-10T00:00:00"},
    ]
    h = compute_weekly_highlights(_base_result(transfer_rumors=rumors))
    assert h["rumor_count"] == 3
    assert [r["title"] for r in h["top_rumors"]] == ["최신 루머", "중간 루머", "오래된 루머"]


def test_busiest_day_picks_max_count_date():
    articles = [
        {"published_at": "2026-07-20T09:00:00"},
        {"published_at": "2026-07-20T15:00:00"},
        {"published_at": "2026-07-21T09:00:00"},
    ]
    h = compute_weekly_highlights(_base_result(korean_articles=articles))
    assert h["busiest_day"] == "2026-07-20"
    assert h["busiest_day_count"] == 2
