# -*- coding: utf-8 -*-
"""
results_store.py
=================
파이프라인 실행 결과(FootballNewsState 최종 병합본)를 JSON으로 저장/조회하는 모듈.

app.py나 week2/graph.py는 건드리지 않고 "결과 영속성"만 담당한다.
호출 지점: week3/dashboard/app.py의 _run_pipeline_in_thread() —
RAG/인사이트 노드까지 병합이 끝난 직후.

app.py를 나중에 tabs/components/utils로 쪼갤 때도 이 모듈은
경로만 그대로 옮기면 되도록 독립적으로 설계했다
(PROJECT_EVALUATION_REPORT.html #07 로드맵 Critical 항목).

저장 위치: <프로젝트 루트>/results/{run_id}.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# week3/storage/results_store.py -> week3 -> 프로젝트 루트
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"

# 실행마다 결과가 계속 쌓이기만 하고 정리되는 곳이 없어서(2026-07-22
# 확인 시점 21건·12MB), 최근 N건만 남기는 보관 정책을 둔다. 평균
# 파일 크기(~600KB) 기준으로 이 정도면 디스크 부담 없이 충분한 이력을
# 유지한다.
MAX_RESULTS = 50


def _json_default(obj: Any) -> str:
    """json.dump가 기본으로 처리 못 하는 타입(datetime 등)을 문자열로 변환"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _safe_run_id(run_id: str) -> str:
    """run_id를 파일명으로 써도 안전하게 정리 (경로 이탈 문자 제거)"""
    cleaned = "".join(c for c in run_id if c.isalnum() or c in ("_", "-"))
    return cleaned or "run_unknown"


def save_result(result: dict, run_id: Optional[str] = None) -> Path:
    """
    파이프라인 실행 결과를 JSON 파일로 저장한다.

    Parameters
    ----------
    result : dict
        run_pipeline() + RAG/인사이트 노드까지 병합된 최종 state
    run_id : str, optional
        미입력 시 result["run_id"] 또는 현재 시각 기반으로 생성

    Returns
    -------
    Path
        저장된 파일 경로

    Notes
    -----
    실패해도 파이프라인 자체를 멈추면 안 되므로, 호출하는 쪽(app.py)에서
    반드시 try/except로 감싸고 저장 실패는 경고 로그로만 남기도록 한다.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rid = run_id or result.get("run_id") or datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    safe_rid = _safe_run_id(str(rid))

    payload = dict(result)
    payload["_saved_at"] = datetime.now(timezone.utc).isoformat()

    path = RESULTS_DIR / f"{safe_rid}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default)

    logger.info(f"파이프라인 결과 저장: {path}")
    _prune_old_results()
    return path


def _prune_old_results() -> int:
    """
    MAX_RESULTS건을 초과하는 오래된 결과 파일을 정리한다.

    Returns
    -------
    int
        삭제한 파일 수
    """
    if not RESULTS_DIR.exists():
        return 0
    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    to_delete = files[MAX_RESULTS:]
    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            deleted += 1
        except OSError as e:
            logger.warning(f"오래된 결과 삭제 실패 ({f}): {e}")
    if deleted:
        logger.info(f"오래된 결과 {deleted}건 정리 (최근 {MAX_RESULTS}건만 유지)")
    return deleted


def list_results(limit: int = 20) -> list[dict]:
    """
    저장된 결과 목록을 최신순으로 반환한다 (요약 메타데이터만, 본문 제외).

    Returns
    -------
    list[dict]
        [{"run_id", "saved_at", "league", "file", "has_errors", "cost_usd"}, ...]
    """
    if not RESULTS_DIR.exists():
        return []

    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    summaries = []
    for f in files[:limit]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"결과 파일 읽기 실패 ({f}): {e}")
            continue
        cost_usd = sum(u.get("cost_usd", 0.0) for u in data.get("llm_usage", []) or [])
        summaries.append({
            "run_id": data.get("run_id", f.stem),
            "saved_at": data.get("_saved_at"),
            "league": (data.get("config") or {}).get("league"),
            "file": f.name,
            "has_errors": bool(data.get("errors")),
            "cost_usd": round(cost_usd, 6),
        })
    return summaries


def load_result(run_id_or_file: str) -> Optional[dict]:
    """run_id 또는 파일명으로 저장된 결과 하나를 불러온다. 없으면 None."""
    stem = run_id_or_file[:-5] if run_id_or_file.endswith(".json") else run_id_or_file
    path = RESULTS_DIR / f"{_safe_run_id(stem)}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # 간단한 자체 동작 확인 (pytest 대체용 스모크 테스트)
    sample = {
        "run_id": "run_selftest",
        "final_report": "테스트 리포트",
        "config": {"league": "PL", "days_back": 3},
        "errors": [],
    }
    saved_path = save_result(sample)
    print(f"저장됨: {saved_path}")

    listed = list_results()
    print(f"목록 ({len(listed)}건): {listed[:1]}")

    loaded = load_result("run_selftest")
    print(f"불러오기 성공: {loaded is not None and loaded.get('final_report') == '테스트 리포트'}")

    saved_path.unlink()
    print("스모크 테스트 정리 완료")
