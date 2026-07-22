# -*- coding: utf-8 -*-
"""
test_merge_node_report_title.py
================================
week2/nodes.py의 merge_node()가 만드는 final_report 제목이 수집
기간(days_back)에 맞춰 "일간"/"주간"으로 바뀌는지 검증한다.

예전엔 days_back과 무관하게 항상 "일간 리포트"로 고정돼 있어서, 주간
보고서 탭(기간 7일 이상)에서도 본문 제목만 "일간"이라고 나오는
불일치가 있었다(2026-07-22, 사용자가 스크린샷으로 지적).
"""
from nodes import merge_node


def _minimal_state(days_back: int) -> dict:
    return {
        "config": {"days_back": days_back, "league": "PL"},
        "run_id": "test_run",
        "korean_summary": {},
        "english_summary": {},
        "match_analysis": {},
        "preprocessing_stats": {},
        "errors": [],
    }


def test_short_period_labeled_daily():
    result = merge_node(_minimal_state(days_back=1))
    assert "일간 리포트" in result["final_report"]
    assert "주간 리포트" not in result["final_report"]


def test_week_or_longer_labeled_weekly():
    result = merge_node(_minimal_state(days_back=7))
    assert "주간 리포트" in result["final_report"]


def test_longer_than_week_still_labeled_weekly():
    result = merge_node(_minimal_state(days_back=30))
    assert "주간 리포트" in result["final_report"]
