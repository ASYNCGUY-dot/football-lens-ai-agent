# -*- coding: utf-8 -*-
r"""
scheduler.py
============
파이프라인 자동 실행 스케줄러. Streamlit 없이 헤드리스로 동작한다.
week3/dashboard/utils.py의 run_pipeline_and_save()를 그대로 재사용해
대시보드에서 "⚡ 분석 실행" 버튼을 누른 것과 동일한 결과를 저장한다.
(PROJECT_EVALUATION_REPORT.html #07 로드맵 High Priority — 자동 스케줄링)

사용법
----
1) 즉시 1회 실행 (Windows 작업 스케줄러 / cron에 등록하는 용도):

    python week3/scheduler.py --once --league PL --days-back 7

2) 매일 지정 시각에 자동 실행하는 상시 데몬 (터미널을 계속 열어두거나
   백그라운드로 띄워두는 방식, Ctrl+C로 종료):

    python week3/scheduler.py --time 07:00 --league PL --days-back 7

Windows 작업 스케줄러 등록 예시 (참고용 — 이 스크립트가 직접 등록하지는
않는다. 시스템 설정 변경이라 사용자가 직접 실행해야 한다):

    schtasks /create /tn "FootballLensDailyRun" ^
        /tr "\"<repo>\venv\Scripts\python.exe\" \"<repo>\week3\scheduler.py\" --once" ^
        /sc daily /st 07:00
"""

import argparse
import logging
import os
import sys
import time

# ── 경로 설정 (app.py와 동일한 패턴) ──────────────────────────
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WEEK1_PATH = os.path.join(ROOT, "week1")
WEEK2_PATH = os.path.join(ROOT, "week2")
WEEK3_PATH = os.path.join(ROOT, "week3")
DASHBOARD_PATH = os.path.join(WEEK3_PATH, "dashboard")

for p in [ROOT, WEEK1_PATH, WEEK2_PATH, WEEK3_PATH, DASHBOARD_PATH]:
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv

load_dotenv(os.path.join(WEEK3_PATH, ".env"))
load_dotenv(os.path.join(WEEK2_PATH, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("scheduler")


def run_once(league: str, days_back: int) -> bool:
    """파이프라인을 1회 실행하고 결과를 저장한다. 성공 여부를 반환."""
    from utils import run_pipeline_and_save  # week3/dashboard/utils.py

    logger.info(f"파이프라인 실행 시작 (league={league}, days_back={days_back})")
    start = time.monotonic()
    try:
        result = run_pipeline_and_save(days_back=days_back, league=league)
        elapsed = time.monotonic() - start
        errors = result.get("errors") or []
        run_id = result.get("run_id", "?")
        if errors:
            logger.warning(
                f"완료(경고 {len(errors)}건, {elapsed:.1f}초) run_id={run_id} — {errors}"
            )
        else:
            logger.info(f"완료 ({elapsed:.1f}초) run_id={run_id}")
        return True
    except Exception as e:
        logger.error(f"파이프라인 실행 실패: {e}")
        return False


def run_daemon(league: str, days_back: int, at_time: str) -> None:
    """매일 지정 시각에 run_once()를 실행하는 상시 루프."""
    import schedule

    schedule.every().day.at(at_time).do(run_once, league=league, days_back=days_back)
    logger.info(f"데몬 모드 시작 — 매일 {at_time}에 자동 실행. 종료: Ctrl+C")
    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="Football Lens 파이프라인 자동 실행 스케줄러")
    parser.add_argument("--league", default="PL", help="리그 코드 (기본값: PL)")
    parser.add_argument("--days-back", type=int, default=7, help="수집 기간 — 최근 N일 (기본값: 7)")
    parser.add_argument("--once", action="store_true", help="즉시 1회 실행 후 종료")
    parser.add_argument("--time", default="07:00", help="데몬 모드 실행 시각 HH:MM (기본값: 07:00)")
    args = parser.parse_args()

    if args.once:
        ok = run_once(args.league, args.days_back)
        sys.exit(0 if ok else 1)
    else:
        run_daemon(args.league, args.days_back, args.time)


if __name__ == "__main__":
    main()
