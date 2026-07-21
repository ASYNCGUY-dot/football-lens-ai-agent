# -*- coding: utf-8 -*-
"""
prediction_tracker.py
======================
저장된 경기 예측을 실제 결과와 대조해 적중 여부를 기록한다.

동작:
    1. results_store에 저장된 모든 실행 결과에서 match_id가 붙은 예측을 모은다
       (week2/llm_nodes.py의 _parse_structured_predictions()가 채워둔 값)
    2. 이미 판정된 예측(prediction_accuracy.json에 기록됨)은 건너뛴다
    3. 경기 날짜가 지난 예측만 football-data.org로 실제 상태를 조회한다.
       아직 FINISHED가 아니면(연기 등) 이번엔 건너뛰고 다음에 다시 시도
    4. 예측한 결과(HOME_TEAM/DRAW/AWAY_TEAM)와 실제 승부를 비교해 기록

기록 파일: results/prediction_accuracy.json (results/ 는 .gitignore 대상)
    {match_id: {home_team, away_team, predicted_outcome, actual_outcome,
                correct, confidence, league, run_id, utc_date, judged_at}}

사용법:
    python week3/prediction_tracker.py          # 1회 판정 실행 + 요약 출력
    from week3.prediction_tracker import check_predictions, get_accuracy_summary
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

WEEK1_PATH = os.path.join(os.path.dirname(__file__), "..", "week1")
if WEEK1_PATH not in sys.path:
    sys.path.insert(0, WEEK1_PATH)

JUDGED_PATH = Path(__file__).resolve().parents[1] / "results" / "prediction_accuracy.json"

# football-data.org 무료 플랜 rate limit(6.1초/요청) 때문에 한 번 실행에서
# 조회할 경기 수를 제한한다. 스케줄러가 매일 돌면서 조금씩 처리하면 된다.
DEFAULT_MAX_CHECKS = 20


def _load_judged() -> dict:
    if not JUDGED_PATH.exists():
        return {}
    try:
        with open(JUDGED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"판정 기록 파일 읽기 실패: {e}")
        return {}


def _save_judged(records: dict) -> None:
    JUDGED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JUDGED_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _collect_pending_predictions(max_candidates: int = 200) -> list[dict]:
    """
    results/*.json을 훑어서 match_id가 있는 예측을 전부 모은다.
    (같은 경기를 여러 번 예측했을 수 있으므로 match_id 기준 최신 것만 남긴다)
    """
    from week3.storage.results_store import list_results, load_result

    by_match_id: dict[int, dict] = {}
    for entry in list_results(limit=max_candidates):
        data = load_result(entry["file"])
        if not data:
            continue
        run_id = data.get("run_id", entry["file"])
        league = (data.get("config") or {}).get("league")
        preds = (data.get("match_prediction") or {}).get("predictions", [])
        for p in preds:
            match_id = p.get("match_id")
            if not match_id or not p.get("predicted_outcome"):
                continue
            by_match_id[match_id] = {
                "match_id": match_id,
                "home_team": p.get("home_team"),
                "away_team": p.get("away_team"),
                "predicted_outcome": p.get("predicted_outcome"),
                "confidence": p.get("confidence"),
                "utc_date": p.get("utc_date"),
                "league": league,
                "run_id": run_id,
            }
    return list(by_match_id.values())


def check_predictions(max_checks: int = DEFAULT_MAX_CHECKS) -> dict:
    """
    아직 판정 안 된 예측 중 경기 날짜가 지난 것들을 실제 결과와 대조한다.

    Returns
    -------
    dict
        {"candidates": N, "checked": N, "judged": N, "still_pending": N}
    """
    from collectors.football_data_collector import FootballDataCollector

    judged = _load_judged()
    candidates = _collect_pending_predictions()

    now = datetime.now(timezone.utc)
    to_check = []
    for c in candidates:
        if str(c["match_id"]) in judged:
            continue
        utc_date = c.get("utc_date")
        if not utc_date:
            continue
        try:
            match_dt = datetime.fromisoformat(str(utc_date).replace("Z", "+00:00"))
        except ValueError:
            continue
        if match_dt < now:  # 경기 예정 시각이 지났으면 판정 후보
            to_check.append(c)

    checked = 0
    newly_judged = 0
    collectors_cache: dict[str, FootballDataCollector] = {}

    for c in to_check[:max_checks]:
        league = c.get("league") or "PL"
        collector = collectors_cache.get(league)
        if collector is None:
            try:
                collector = FootballDataCollector(competition=league)
                collectors_cache[league] = collector
            except ValueError as e:
                logger.warning(f"[check_predictions] {league} 컬렉터 생성 실패: {e}")
                continue

        checked += 1
        match_info = collector.get_match(c["match_id"])
        if not match_info or match_info.get("status") != "FINISHED":
            continue  # 아직 안 끝났거나 조회 실패 — 다음 실행 때 재시도

        actual = match_info.get("winner")
        correct = actual is not None and actual == c["predicted_outcome"]
        judged[str(c["match_id"])] = {
            **c,
            "actual_outcome": actual,
            "home_score": match_info.get("home_score"),
            "away_score": match_info.get("away_score"),
            "correct": correct,
            "judged_at": datetime.now(timezone.utc).isoformat(),
        }
        newly_judged += 1
        time.sleep(6.1)  # football-data.org 무료 플랜 rate limit

    if newly_judged:
        _save_judged(judged)

    return {
        "candidates": len(candidates),
        "checked": checked,
        "judged": newly_judged,
        "still_pending": len(to_check) - checked,
    }


def get_accuracy_summary() -> dict:
    """
    지금까지 판정된 예측의 적중률을 집계한다.

    Returns
    -------
    dict
        {"total": N, "correct": N, "accuracy_pct": float,
         "by_confidence": {...}, "by_league": {...}, "recent": [...]}
    """
    judged = _load_judged()
    records = list(judged.values())
    total = len(records)
    correct = sum(1 for r in records if r.get("correct"))

    by_confidence: dict[str, dict] = {}
    by_league: dict[str, dict] = {}
    for r in records:
        conf = r.get("confidence") or "미상"
        by_confidence.setdefault(conf, {"total": 0, "correct": 0})
        by_confidence[conf]["total"] += 1
        by_confidence[conf]["correct"] += 1 if r.get("correct") else 0

        lg = r.get("league") or "미상"
        by_league.setdefault(lg, {"total": 0, "correct": 0})
        by_league[lg]["total"] += 1
        by_league[lg]["correct"] += 1 if r.get("correct") else 0

    recent = sorted(records, key=lambda r: r.get("judged_at", ""), reverse=True)[:20]

    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": round(correct / total * 100, 1) if total else None,
        "by_confidence": by_confidence,
        "by_league": by_league,
        "recent": recent,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = check_predictions()
    print("판정 실행 결과:", result)
    print("적중률 요약:", get_accuracy_summary())
