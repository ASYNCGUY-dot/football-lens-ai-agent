# -*- coding: utf-8 -*-
"""
schema.py
=========
PostgreSQL 테이블 스키마 설계 및 생성 코드

테이블 목록:
    1. articles          - 수집된 뉴스 기사 (RSS + 네이버)
    2. epl_matches       - EPL 경기 결과
    3. epl_standings     - EPL 순위표 스냅샷
    4. collect_logs      - 수집 작업 실행 로그

사용법:
    from database.schema import DatabaseManager

    db = DatabaseManager()
    db.create_all_tables()   # 테이블 전체 생성
    db.drop_all_tables()     # 테이블 전체 삭제 (주의!)
"""

import os
import logging
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================
# DB 연결 설정
# =============================================

def get_db_connection():
    """
    .env 파일의 환경변수로 PostgreSQL 연결을 생성합니다.

    필요한 환경변수:
        DB_HOST     : DB 서버 주소 (기본 localhost)
        DB_PORT     : 포트 (기본 5432)
        DB_NAME     : 데이터베이스 이름
        DB_USER     : 사용자 이름
        DB_PASSWORD : 비밀번호

    Returns
    -------
    psycopg2.connection
        PostgreSQL 연결 객체

    Raises
    ------
    psycopg2.OperationalError
        DB 서버에 연결할 수 없을 때 발생
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname=os.getenv("DB_NAME", "football_lens"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"[get_db_connection] PostgreSQL 연결 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"[get_db_connection] 예외 발생: {e}")
        raise


# =============================================
# DDL: 테이블 생성 SQL
# =============================================

# 1. 뉴스 기사 테이블
CREATE_ARTICLES_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    id              SERIAL PRIMARY KEY,
    article_id      VARCHAR(16)  NOT NULL UNIQUE,  -- SHA256 기반 고유 ID
    title           TEXT         NOT NULL,
    url             TEXT         NOT NULL,
    original_url    TEXT,                           -- 네이버 뉴스 원본 URL
    summary         TEXT,
    published_at    TIMESTAMPTZ,                    -- 기사 발행일시 (timezone 포함)
    source_name     VARCHAR(100) NOT NULL,          -- 수집 소스 이름
    language        VARCHAR(10)  NOT NULL DEFAULT 'ko',
    category        VARCHAR(50),
    keyword         VARCHAR(100),                   -- 네이버 검색 키워드
    detected_language VARCHAR(10),
    processed_at    TIMESTAMPTZ,
    text_hash       VARCHAR(32),                    -- SHA256 앞 32자 (제목+요약 중복 감지)
    simhash         VARCHAR(32),                    -- Simhash 근사 중복 감지
    collected_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_published_at  ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source_name   ON articles (source_name);
CREATE INDEX IF NOT EXISTS idx_articles_language      ON articles (language);
CREATE INDEX IF NOT EXISTS idx_articles_collected_at  ON articles (collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_title_gin     ON articles USING GIN (to_tsvector('simple', title));
"""

# 2. EPL 경기 결과 테이블
CREATE_EPL_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS epl_matches (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER      NOT NULL UNIQUE,
    matchday        INTEGER,
    utc_date        TIMESTAMPTZ,
    status          VARCHAR(20),
    home_team_id    INTEGER,
    home_team_name  VARCHAR(100),
    away_team_id    INTEGER,
    away_team_name  VARCHAR(100),
    home_score      INTEGER,
    away_score      INTEGER,
    home_ht_score   INTEGER,
    away_ht_score   INTEGER,
    winner          VARCHAR(20),
    competition     VARCHAR(10) NOT NULL DEFAULT 'PL',
    season          VARCHAR(4),
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_epl_matches_utc_date    ON epl_matches (utc_date DESC);
CREATE INDEX IF NOT EXISTS idx_epl_matches_matchday    ON epl_matches (matchday);
CREATE INDEX IF NOT EXISTS idx_epl_matches_home_team   ON epl_matches (home_team_id);
CREATE INDEX IF NOT EXISTS idx_epl_matches_away_team   ON epl_matches (away_team_id);
CREATE INDEX IF NOT EXISTS idx_epl_matches_status      ON epl_matches (status);
"""

# 3. EPL 순위표 스냅샷 테이블
CREATE_EPL_STANDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS epl_standings (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE         NOT NULL,
    rank            INTEGER      NOT NULL,
    team_id         INTEGER      NOT NULL,
    team_name       VARCHAR(100) NOT NULL,
    played          INTEGER DEFAULT 0,
    won             INTEGER DEFAULT 0,
    draw            INTEGER DEFAULT 0,
    lost            INTEGER DEFAULT 0,
    goals_for       INTEGER DEFAULT 0,
    goals_against   INTEGER DEFAULT 0,
    goal_diff       INTEGER DEFAULT 0,
    points          INTEGER DEFAULT 0,
    form            VARCHAR(20),
    season          VARCHAR(4),
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (snapshot_date, team_id)
);

CREATE INDEX IF NOT EXISTS idx_epl_standings_snapshot_date ON epl_standings (snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_epl_standings_team_id       ON epl_standings (team_id);
CREATE INDEX IF NOT EXISTS idx_epl_standings_rank          ON epl_standings (rank);
"""

# 4. 수집 작업 로그 테이블
CREATE_COLLECT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS collect_logs (
    id               SERIAL PRIMARY KEY,
    job_name         VARCHAR(100) NOT NULL,
    source_type      VARCHAR(50)  NOT NULL,
    status           VARCHAR(20)  NOT NULL,
    articles_fetched INTEGER DEFAULT 0,
    articles_saved   INTEGER DEFAULT 0,
    articles_skipped INTEGER DEFAULT 0,
    error_message    TEXT,
    duration_seconds FLOAT,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_collect_logs_started_at  ON collect_logs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_collect_logs_job_name    ON collect_logs (job_name);
CREATE INDEX IF NOT EXISTS idx_collect_logs_status      ON collect_logs (status);
"""


# =============================================
# DatabaseManager 클래스
# =============================================

class DatabaseManager:
    """
    PostgreSQL 데이터베이스 관리 클래스

    주요 기능:
        create_all_tables()  : 모든 테이블 생성
        drop_all_tables()    : 모든 테이블 삭제 (주의!)
        check_tables()       : 테이블 존재 여부 확인
        insert_articles()    : 기사 목록 일괄 저장 (중복 무시)
        insert_matches()     : 경기 결과 일괄 저장 (중복 시 업데이트)
        insert_standings()   : 순위표 스냅샷 저장
        log_collect_job()    : 수집 작업 로그 기록

    예시:
        db = DatabaseManager()
        db.create_all_tables()

        articles = [...]
        saved = db.insert_articles(articles)
        print(f"{saved}건 저장 완료")
    """

    TABLE_NAMES = ["articles", "epl_matches", "epl_standings", "collect_logs"]

    def __init__(self):
        """
        DatabaseManager를 초기화합니다.

        초기화 시 PostgreSQL 연결 테스트를 수행합니다.
        연결 실패 시 예외를 발생시켜 잘못된 설정으로 진행되는 것을 방지합니다.

        Raises
        ------
        Exception
            .env의 DB 접속 정보가 잘못되었거나 PostgreSQL 서버가 실행 중이지 않은 경우
        """
        self._test_connection()

    def _test_connection(self):
        """
        DB 연결 가능 여부를 테스트합니다.

        Raises
        ------
        psycopg2.OperationalError
            연결 실패 시 예외를 그대로 전파하여 초기화를 중단시킵니다.
        """
        try:
            conn = get_db_connection()
            conn.close()
            logger.info("PostgreSQL 연결 성공")
        except psycopg2.OperationalError as e:
            logger.error(f"[_test_connection] DB 연결 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"[_test_connection] 예외 발생: {e}")
            raise

    # =============================================
    # 테이블 생성 / 삭제
    # =============================================

    def create_all_tables(self):
        """
        4개 테이블을 모두 생성합니다.
        이미 존재하는 테이블은 건너뜁니다 (IF NOT EXISTS).

        Raises
        ------
        psycopg2.Error
            SQL 실행 중 DB 오류 발생 시
        """
        logger.info("테이블 생성 시작...")
        all_ddl = [
            CREATE_ARTICLES_TABLE,
            CREATE_EPL_MATCHES_TABLE,
            CREATE_EPL_STANDINGS_TABLE,
            CREATE_COLLECT_LOGS_TABLE,
        ]
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for ddl in all_ddl:
                    for stmt in ddl.split(";"):
                        stmt = stmt.strip()
                        if stmt:
                            cur.execute(stmt)
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"[create_all_tables] DB 오류: {e}")
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"[create_all_tables] 예외 발생: {e}")
            raise
        finally:
            conn.close()
        logger.info("테이블 생성 완료")

    def drop_all_tables(self, confirm: bool = False):
        """
        4개 테이블을 모두 삭제합니다.

        Parameters
        ----------
        confirm : bool
            True로 설정해야 실제로 삭제됩니다. 실수 방지용 안전장치.
        """
        if not confirm:
            logger.warning("[drop_all_tables] confirm=True 필요. 삭제 취소됨.")
            return
        tables = ["collect_logs", "epl_standings", "epl_matches", "articles"]
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for table in tables:
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            conn.commit()
            logger.info("테이블 삭제 완료")
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"[drop_all_tables] DB 오류: {e}")
            raise
        finally:
            conn.close()

    def check_tables(self) -> dict:
        """
        4개 테이블의 존재 여부와 행 수를 반환합니다.

        Returns
        -------
        dict
            {테이블명: {"exists": bool, "row_count": int}} 형식
        """
        result = {}
        tables = ["articles", "epl_matches", "epl_standings", "collect_logs"]
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for table in tables:
                    cur.execute(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = %s);",
                        (table,),
                    )
                    exists = cur.fetchone()[0]
                    count = 0
                    if exists:
                        cur.execute(f"SELECT COUNT(*) FROM {table};")
                        count = cur.fetchone()[0]
                    result[table] = {"exists": exists, "row_count": count}
        except psycopg2.Error as e:
            logger.error(f"[check_tables] DB 오류: {e}")
        finally:
            conn.close()
        return result

    # =============================================
    # 데이터 삽입
    # =============================================

    def insert_articles(self, articles: list) -> int:
        """
        기사 목록을 articles 테이블에 삽입합니다.

        중복된 article_id는 무시합니다 (ON CONFLICT DO NOTHING).

        Parameters
        ----------
        articles : list
            ArticlePreprocessor.run() 결과 기사 딕셔너리 목록

        Returns
        -------
        int
            실제 삽입된 행 수
        """
        if not articles:
            return 0
        conn = get_db_connection()
        inserted = 0
        try:
            with conn.cursor() as cur:
                for a in articles:
                    try:
                        cur.execute(
                            """
                            INSERT INTO articles
                                (article_id, source_name, category,
                                 title, url, summary, published_at, language,
                                 text_hash, simhash)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (article_id) DO NOTHING;
                            """,
                            (
                                a.get("article_id"), a.get("source_name"),
                                a.get("category"),
                                a.get("title"), a.get("url"),
                                a.get("summary"), a.get("published_at"),
                                a.get("language"), a.get("text_hash"),
                                str(a.get("simhash", "")),
                            ),
                        )
                        inserted += cur.rowcount
                    except psycopg2.Error as e:
                        logger.warning(f"[insert_articles] 행 삽입 오류 (건너뜀): {e}")
                        continue
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"[insert_articles] DB 오류: {e}")
        finally:
            conn.close()
        logger.info(f"기사 삽입: {inserted}/{len(articles)}건")
        return inserted

    def insert_matches(self, matches: list) -> int:
        """
        EPL 경기 결과를 epl_matches 테이블에 삽입합니다.

        기존 match_id가 있으면 status와 스코어를 업데이트합니다.

        Parameters
        ----------
        matches : list
            FootballDataCollector.get_recent_matches() 결과 딕셔너리 목록

        Returns
        -------
        int
            삽입 또는 업데이트된 행 수
        """
        if not matches:
            return 0
        conn = get_db_connection()
        upserted = 0
        try:
            with conn.cursor() as cur:
                for m in matches:
                    try:
                        cur.execute(
                            """
                            INSERT INTO epl_matches
                                (match_id, competition, season, matchday,
                                 utc_date, status,
                                 home_team_id, home_team_name,
                                 away_team_id, away_team_name,
                                 home_score, away_score,
                                 home_ht_score, away_ht_score,
                                 winner, collected_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (match_id) DO UPDATE SET
                                status = EXCLUDED.status,
                                home_score = EXCLUDED.home_score,
                                away_score = EXCLUDED.away_score,
                                home_ht_score = EXCLUDED.home_ht_score,
                                away_ht_score = EXCLUDED.away_ht_score,
                                winner = EXCLUDED.winner;
                            """,
                            (
                                m.get("match_id"), m.get("competition"),
                                m.get("season"), m.get("matchday"),
                                m.get("utc_date"), m.get("status"),
                                m.get("home_team_id"), m.get("home_team_name"),
                                m.get("away_team_id"), m.get("away_team_name"),
                                m.get("home_score"), m.get("away_score"),
                                m.get("home_ht_score"), m.get("away_ht_score"),
                                m.get("winner"), m.get("collected_at"),
                            ),
                        )
                        upserted += 1
                    except psycopg2.Error as e:
                        logger.warning(f"[insert_matches] 행 삽입 오류 (건너뜀): {e}")
                        continue
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"[insert_matches] DB 오류: {e}")
        finally:
            conn.close()
        logger.info(f"경기 결과 삽입: {upserted}/{len(matches)}건")
        return upserted

    def insert_standings(self, standings: list, snapshot_date: str = None) -> int:
        """
        EPL 순위표를 epl_standings 테이블에 삽입합니다.

        같은 날짜의 같은 팀 데이터는 업데이트합니다.

        Parameters
        ----------
        standings : list
            FootballDataCollector.get_standings() 결과 딕셔너리 목록
        snapshot_date : str, optional
            스냅샷 날짜 (YYYY-MM-DD). 기본값: 오늘

        Returns
        -------
        int
            삽입 또는 업데이트된 행 수
        """
        if not standings:
            return 0
        if snapshot_date is None:
            from datetime import date
            snapshot_date = date.today().isoformat()
        conn = get_db_connection()
        upserted = 0
        try:
            with conn.cursor() as cur:
                for row in standings:
                    try:
                        cur.execute(
                            """
                            INSERT INTO epl_standings
                                (snapshot_date, team_id, team_name, rank,
                                 played, won, draw, lost,
                                 goals_for, goals_against, goal_diff, points, form)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (snapshot_date, team_id) DO UPDATE SET
                                rank = EXCLUDED.rank,
                                played = EXCLUDED.played,
                                won = EXCLUDED.won,
                                draw = EXCLUDED.draw,
                                lost = EXCLUDED.lost,
                                goals_for = EXCLUDED.goals_for,
                                goals_against = EXCLUDED.goals_against,
                                goal_diff = EXCLUDED.goal_diff,
                                points = EXCLUDED.points,
                                form = EXCLUDED.form;
                            """,
                            (
                                snapshot_date,
                                row.get("team_id"), row.get("team_name"),
                                row.get("rank"), row.get("played"),
                                row.get("won"), row.get("draw"), row.get("lost"),
                                row.get("goals_for"), row.get("goals_against"),
                                row.get("goal_diff"), row.get("points"),
                                row.get("form", ""),
                            ),
                        )
                        upserted += 1
                    except psycopg2.Error as e:
                        logger.warning(f"[insert_standings] 행 삽입 오류 (건너뜀): {e}")
                        continue
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"[insert_standings] DB 오류: {e}")
        finally:
            conn.close()
        logger.info(f"순위표 삽입: {upserted}/{len(standings)}팀")
        return upserted

    def log_collect_job(self, job_name: str, source_type: str, status: str = "success",
                        articles_fetched: int = 0, articles_saved: int = 0,
                        articles_skipped: int = 0, error_message: str = None,
                        duration_seconds: float = None) -> int:
        """
        수집 작업 로그를 collect_logs 테이블에 기록합니다.

        Parameters
        ----------
        job_name : str
            수집 작업 이름 (예: "rss_all_sources", "naver_football_keywords")
        source_type : str
            수집 소스 종류 (예: "rss", "naver", "football_data")
        status : str
            작업 결과 ("success" / "partial" / "failed")
        articles_fetched : int
            수집된 총 기사 수
        articles_saved : int
            DB에 저장된 기사 수
        articles_skipped : int
            중복/필터링으로 건너뛴 기사 수
        error_message : str, optional
            오류 발생 시 메시지
        duration_seconds : float, optional
            작업 수행 시간(초)

        Returns
        -------
        int
            생성된 로그 레코드 ID. 오류 시 -1 반환.
        """
        insert_sql = """
            INSERT INTO collect_logs
                (job_name, source_type, status, articles_fetched, articles_saved, articles_skipped,
                error_message, duration_seconds, finished_at
            ) VALUES (
                %(job_name)s, %(source_type)s, %(status)s,
                %(articles_fetched)s, %(articles_saved)s, %(articles_skipped)s,
                %(error_message)s, %(duration_seconds)s, NOW()
            )
            RETURNING id;
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(insert_sql, {
                    "job_name": job_name,
                    "source_type": source_type,
                    "status": status,
                    "articles_fetched": articles_fetched,
                    "articles_saved": articles_saved,
                    "articles_skipped": articles_skipped,
                    "error_message": error_message,
                    "duration_seconds": duration_seconds,
                })
                log_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"수집 로그 기록: {job_name} ({status}) → log_id={log_id}")
            return log_id
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"[log_collect_job] DB 오류: {e}")
            return -1
        finally:
            conn.close()


# =============================================
# 직접 실행 시 테이블 생성 테스트
# =============================================
if __name__ == "__main__":
    print("=== PostgreSQL 테이블 생성 테스트 ===\n")
    try:
        db = DatabaseManager()
        db.create_all_tables()
        status = db.check_tables()
        for table, info in status.items():
            mark = "✅" if info["exists"] else "❌"
            print(f"  {mark} {table:20s} ({info['row_count']}행)")
    except Exception as e:
        print(f"오류: {e}")
        print("PostgreSQL 연결 정보를 .env 파일에서 확인하세요.")
