# -*- coding: utf-8 -*-
"""
main.py
=======
Week 1 전체 파이프라인 실행 스크립트

실행 순서:
    1. RSS 뉴스 수집
    2. 네이버 뉴스 수집
    3. football-data.org EPL 데이터 수집
    4. 전처리 (중복 제거, 광고 필터링)
    5. PostgreSQL 저장

실행 방법:
    # week1 폴더에서:
    python main.py

    # 특정 단계만 실행:
    python main.py --step rss
    python main.py --step naver
    python main.py --step football
"""

import time
import logging
import argparse
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def run_rss_pipeline(db=None):
    """RSS 수집 → 전처리 → DB 저장"""
    from collectors.rss_collector import RSSCollector
    from preprocessing.preprocessor import ArticlePreprocessor

    start = time.time()
    logger.info("=== RSS 수집 시작 ===")

    collector = RSSCollector()
    raw = collector.collect_all()

    preprocessor = ArticlePreprocessor()
    clean = preprocessor.run(raw)
    stats = preprocessor.get_stats()

    saved = 0
    if db and clean:
        saved = db.insert_articles(clean)
        db.log_collect_job(
            job_name="rss_all_sources",
            source_type="rss",
            status="success",
            articles_fetched=stats["total"],
            articles_saved=saved,
            articles_skipped=stats["total"] - stats["passed"],
            duration_seconds=round(time.time() - start, 2),
        )

    logger.info(f"RSS 완료: 수집 {stats['total']}건 → 저장 {saved}건")
    return clean


def run_naver_pipeline(db=None):
    """네이버 수집 → 전처리 → DB 저장"""
    from collectors.naver_collector import NaverNewsCollector
    from preprocessing.preprocessor import ArticlePreprocessor

    start = time.time()
    logger.info("=== 네이버 뉴스 수집 시작 ===")

    try:
        collector = NaverNewsCollector(display=20)
        raw = collector.collect_keywords()
    except ValueError as e:
        logger.warning(f"네이버 API 키 없음, 건너뜁니다: {e}")
        return []

    preprocessor = ArticlePreprocessor()
    clean = preprocessor.run(raw)
    stats = preprocessor.get_stats()

    saved = 0
    if db and clean:
        saved = db.insert_articles(clean)
        db.log_collect_job(
            job_name="naver_football_keywords",
            source_type="naver",
            status="success",
            articles_fetched=stats["total"],
            articles_saved=saved,
            articles_skipped=stats["total"] - stats["passed"],
            duration_seconds=round(time.time() - start, 2),
        )

    logger.info(f"네이버 완료: 수집 {stats['total']}건 → 저장 {saved}건")
    return clean


def run_football_pipeline(db=None):
    """football-data.org EPL 데이터 수집 → DB 저장"""
    from collectors.football_data_collector import FootballDataCollector

    start = time.time()
    logger.info("=== EPL 데이터 수집 시작 ===")

    try:
        collector = FootballDataCollector()
    except ValueError as e:
        logger.warning(f"football-data API 키 없음, 건너뜁니다: {e}")
        return

    standings = collector.get_standings()
    matches = collector.get_recent_matches(days_back=7)

    if db:
        db.insert_standings(standings)
        db.insert_matches(matches)
        db.log_collect_job(
            job_name="football_data_epl",
            source_type="football_data",
            status="success",
            articles_fetched=len(matches),
            articles_saved=len(matches),
            duration_seconds=round(time.time() - start, 2),
        )

    logger.info(f"EPL 완료: 순위표 {len(standings)}팀, 경기 {len(matches)}건")


def main():
    parser = argparse.ArgumentParser(description="Football Lens 1주차 데이터 수집 파이프라인")
    parser.add_argument(
        "--step",
        choices=["rss", "naver", "football", "all"],
        default="all",
        help="실행할 단계 (기본: all)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="DB 저장 없이 수집만 실행 (테스트용)",
    )
    args = parser.parse_args()

    db = None
    if not args.no_db:
        try:
            from database.schema import DatabaseManager
            db = DatabaseManager()
            db.create_all_tables()
        except Exception as e:
            logger.warning(f"DB 연결 실패, DB 없이 실행: {e}")

    total_start = time.time()

    if args.step in ("rss", "all"):
        run_rss_pipeline(db)

    if args.step in ("naver", "all"):
        run_naver_pipeline(db)

    if args.step in ("football", "all"):
        run_football_pipeline(db)

    elapsed = round(time.time() - total_start, 2)
    logger.info(f"=== 전체 파이프라인 완료 ({elapsed}초) ===")


if __name__ == "__main__":
    main()
