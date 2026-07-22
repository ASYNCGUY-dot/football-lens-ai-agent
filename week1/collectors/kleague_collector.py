# -*- coding: utf-8 -*-
"""
kleague_collector.py
====================
K리그 연맹 공식 사이트(kleague.com)의 내부 API를 이용한 순위표/득점왕/
경기결과 수집 모듈.

왜 만들었나
-----------
football-data.org 무료 플랜은 K리그를 아예 지원하지 않는다(자세한 내용은
football_data_collector.py의 AVAILABLE_LEAGUES 주석 참고). K리그 연맹이
공개 API를 제공하지 않아서, kleague.com이 자기 홈페이지 렌더링에 내부적
으로 쓰는 엔드포인트를 브라우저 개발자도구 네트워크 탭으로 직접 관찰해
찾아냈다(2026-07-22). 참고로 GitHub의 성남FC 일정 스크립트
(garudanish/sfc-google-calendar)도 이 중 getScheduleList.do를 똑같은
방식으로 쓰고 있는 걸 확인했다 — 커뮤니티에서도 이미 쓰이는 방식이다.

⚠️ 주의: 공식 문서가 없는 비공개(미문서화) 내부 API다. football-data.org
처럼 계약된 안정성이 없어서 예고 없이 응답 형식이 바뀌거나 막힐 수 있다.
모든 메서드가 실패 시 예외를 던지지 않고 빈 리스트를 반환하도록 만들어서,
이 API가 언젠가 깨지더라도 파이프라인 전체가 죽지 않게 했다.

확인된 엔드포인트 (전부 POST, 2026-07-22 curl로 직접 검증):
    GET  (site)  https://www.kleague.com/record/team.do   — 순위표 페이지
    POST         https://www.kleague.com/record/teamRank.do
                     ?leagueId=1&year=2026&stadium=all&recordType=rank
                 → 팀 순위표 (쿼리 파라미터만 필요, body 없음)
    POST         https://www.kleague.com/record/rankSort.do
                 body(JSON): {"leagueId": "1", "year": "2026", "recordType": "GOAL"}
                 → 선수 개인기록 (recordType: GOAL/ASSIST/AP/CONCEDED/CK/FC/ST/
                   OS/WARN/OUT/CLEAN/GAMECNT 중 선택)
    POST         https://www.kleague.com/getScheduleList.do
                 body(JSON): {"leagueId": "1", "teamId": "", "year": "2026", "month": "07"}
                 → 월별 경기 일정 + 종료된 경기는 실제 스코어(homeGoal/awayGoal) 포함

리그 ID: K리그1="1", K리그2="2"

반환 형식은 football_data_collector.FootballDataCollector의
get_standings()/get_top_scorers()/get_recent_matches()/
get_upcoming_matches()와 동일한 dict 스키마를 쓴다 — 그래야 nodes.py나
대시보드 탭들을 K리그 전용으로 따로 안 고쳐도 그대로 재사용할 수 있다.

사용법:
    from collectors.kleague_collector import KLeagueCollector

    collector = KLeagueCollector()
    standings = collector.get_standings()
    scorers   = collector.get_top_scorers(limit=10)
    matches   = collector.get_recent_matches(days_back=7)
"""

import logging
import requests
from datetime import datetime, timezone, timedelta, date as _date

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kleague.com"
K1_LEAGUE_ID = "1"  # K리그1
REQUEST_TIMEOUT = 10

# kleague.com game01~game06 결과 표기 → football-data.org 스타일 약어
_FORM_MAP = {"승": "W", "무": "D", "패": "L"}


class KLeagueCollector:
    """
    K리그 연맹 공식 사이트(kleague.com) 내부 API 수집기.

    주요 메서드:
        get_standings()       : K리그1 순위표
        get_top_scorers()     : 득점 순위
        get_recent_matches()  : 최근 완료된 경기 결과
        get_upcoming_matches(): 예정된 경기 일정
    """

    def __init__(self, league_id: str = K1_LEAGUE_ID, year: int = None):
        self.league_id = league_id
        self.year = year or datetime.now().year

    def _post(self, path: str, params: dict = None, json_body: dict = None) -> dict | None:
        """
        공통 POST 요청. 실패해도 예외를 던지지 않고 None을 반환한다 —
        비공식 API라 언제든 형식이 바뀌거나 막힐 수 있어서, 호출부가
        try/except 없이도 안전하게 빈 결과로 처리할 수 있게 했다.
        """
        url = f"{BASE_URL}{path}"
        try:
            resp = requests.post(
                url, params=params, json=json_body, timeout=REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("resultCode") != "200":
                logger.warning(f"[KLeague] {path} 응답 코드 이상: {data.get('resultCode')} {data.get('resultMsg')}")
                return None
            return data.get("data")
        except requests.exceptions.RequestException as e:
            logger.error(f"[KLeague] {path} 요청 오류: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"[KLeague] {path} 응답 파싱 오류: {e}")
            return None

    # =============================================
    # 순위표
    # =============================================
    def get_standings(self) -> list[dict]:
        """
        K리그1 순위표를 가져온다. football_data_collector.get_standings()와
        동일한 스키마로 반환한다.
        """
        data = self._post(
            "/record/teamRank.do",
            params={
                "leagueId": self.league_id, "year": self.year,
                "stadium": "all", "recordType": "rank",
            },
        )
        if not data:
            return []

        standings = []
        for row in data.get("teamRank", []):
            try:
                games = [row.get(f"game0{i}") for i in range(1, 7)]
                form = "".join(_FORM_MAP.get(g, "") for g in games if g)
                standings.append({
                    "rank": row.get("rank"),
                    "team_id": row.get("teamId"),
                    "team_name": row.get("teamName"),
                    "played": row.get("gameCount"),
                    "won": row.get("winCnt"),
                    "draw": row.get("tieCnt"),
                    "lost": row.get("lossCnt"),
                    "goals_for": row.get("gainGoal"),
                    "goals_against": row.get("lossGoal"),
                    "goal_diff": row.get("gapCnt"),
                    "points": row.get("gainPoint"),
                    "form": form,
                    "collected_at": datetime.now(timezone.utc),
                })
            except Exception as e:
                logger.warning(f"[KLeague] 순위 파싱 오류 (건너뜀): {e}")

        logger.info(f"[KLeague] 순위표 수집 완료: {len(standings)}팀")
        return standings

    # =============================================
    # 득점 순위
    # =============================================
    def get_top_scorers(self, limit: int = 10) -> list[dict]:
        """
        K리그1 득점 순위를 가져온다. football_data_collector.get_top_scorers()와
        동일한 스키마로 반환한다(nationality/penalties는 kleague.com이 안 줘서
        빈 값으로 채운다).
        """
        data = self._post(
            "/record/rankSort.do",
            json_body={"leagueId": self.league_id, "year": str(self.year), "recordType": "GOAL"},
        )
        if not data:
            return []

        scorers = []
        for row in data.get("list", [])[:limit]:
            try:
                scorers.append({
                    "rank": row.get("rank"),
                    "player_id": row.get("playerId"),
                    "player_name": row.get("name"),
                    "nationality": "",
                    "team_id": row.get("teamId"),
                    "team_name": row.get("teamName"),
                    "goals": row.get("goalQty", 0),
                    "assists": row.get("assistQty", 0),
                    "penalties": 0,
                    "collected_at": datetime.now(timezone.utc),
                })
            except Exception as e:
                logger.warning(f"[KLeague] 득점 순위 파싱 오류 (건너뜀): {e}")

        logger.info(f"[KLeague] 득점 순위 수집 완료: {len(scorers)}명")
        return scorers

    # =============================================
    # 경기 일정 / 결과
    # =============================================
    def _get_month_schedule(self, year: int, month: int) -> list[dict]:
        data = self._post(
            "/getScheduleList.do",
            json_body={
                "leagueId": self.league_id, "teamId": "",
                "year": str(year), "month": f"{month:02d}",
            },
        )
        if not data:
            return []
        return data.get("scheduleList", [])

    def _parse_schedule_row(self, row: dict) -> dict | None:
        """kleague.com의 경기 한 건을 football-data.org 스타일 dict로 변환한다."""
        try:
            game_date = row.get("gameDate", "")  # "2026.05.02"
            game_time = row.get("gameTime", "00:00")  # "19:30"
            y, m, d = (game_date.split(".") + ["01", "01", "01"])[:3]
            # kleague.com 시각은 한국 현지시각(KST) 기준이라, football-data.org
            # 처럼 진짜 UTC로 변환하지 않고 그대로 ISO 문자열에 담는다 — 대시보드
            # 코드가 대부분 날짜 앞 10자리(YYYY-MM-DD)만 잘라 쓰기 때문에
            # 실사용에는 문제가 없다.
            iso_date = f"{y}-{m}-{d}T{game_time}:00"

            # 완료 여부는 반드시 endYn으로 판정해야 한다 — homeGoal/awayGoal은
            # 아직 안 열린 경기에도 null이 아니라 0으로 채워져 있어서, 이걸
            # 기준으로 삼으면 예정 경기가 전부 "0-0으로 끝난 경기"로 잘못
            # 분류된다(2026-07-22, 실측으로 확인: 7/25~8/2 예정 경기 전부
            # homeGoal=0, endYn=N). gameStatus도 같은 정보를 "FE"/""로 준다.
            is_finished = row.get("endYn") == "Y"
            home_goal = row.get("homeGoal") if is_finished else None
            away_goal = row.get("awayGoal") if is_finished else None
            status = "FINISHED" if is_finished else "SCHEDULED"

            winner = None
            if is_finished:
                if home_goal > away_goal:
                    winner = "HOME_TEAM"
                elif away_goal > home_goal:
                    winner = "AWAY_TEAM"
                else:
                    winner = "DRAW"

            return {
                "match_id": row.get("gameId"),
                "matchday": row.get("roundId"),
                "utc_date": iso_date,
                "status": status,
                "home_team_id": row.get("homeTeam"),
                "home_team_name": row.get("homeTeamName"),
                "away_team_id": row.get("awayTeam"),
                "away_team_name": row.get("awayTeamName"),
                "home_score": home_goal,
                "away_score": away_goal,
                "home_ht_score": None,
                "away_ht_score": None,
                "winner": winner,
                "competition": "KL1",
                "season": str(y),
                "collected_at": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.warning(f"[KLeague] 경기 파싱 오류 (건너뜀): {e}")
            return None

    def get_recent_matches(self, days_back: int = 7) -> list[dict]:
        """
        최근 완료된 K리그1 경기 결과를 가져온다. getScheduleList.do가 '월' 단위
        조회만 지원해서, days_back이 걸치는 월(최대 2개월)을 모두 조회한 뒤
        날짜로 다시 걸러낸다.
        """
        today = _date.today()
        start = today - timedelta(days=days_back)
        months = {(start.year, start.month), (today.year, today.month)}

        rows = []
        for y, m in months:
            rows.extend(self._get_month_schedule(y, m))

        matches = []
        for row in rows:
            parsed = self._parse_schedule_row(row)
            if not parsed or parsed["status"] != "FINISHED":
                continue
            try:
                match_date = datetime.fromisoformat(parsed["utc_date"]).date()
            except ValueError:
                continue
            if start <= match_date <= today:
                matches.append(parsed)

        logger.info(f"[KLeague] 최근 경기 결과 수집 완료: {len(matches)}건")
        return matches

    def get_upcoming_matches(self, days_ahead: int = 7) -> list[dict]:
        """예정된 K리그1 경기 일정을 가져온다."""
        today = _date.today()
        end = today + timedelta(days=days_ahead)
        months = {(today.year, today.month), (end.year, end.month)}

        rows = []
        for y, m in months:
            rows.extend(self._get_month_schedule(y, m))

        matches = []
        for row in rows:
            parsed = self._parse_schedule_row(row)
            if not parsed or parsed["status"] != "SCHEDULED":
                continue
            try:
                match_date = datetime.fromisoformat(parsed["utc_date"]).date()
            except ValueError:
                continue
            if today <= match_date <= end:
                matches.append(parsed)

        logger.info(f"[KLeague] 예정 경기 수집 완료: {len(matches)}건")
        return matches


# =============================================
# 직접 실행 시 테스트
# =============================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = KLeagueCollector()

    print("=== K리그1 순위표 ===")
    for team in collector.get_standings()[:5]:
        print(f"{team['rank']}위 {team['team_name']:6s} {team['points']}점")

    print("\n=== K리그1 득점 순위 ===")
    for s in collector.get_top_scorers(limit=5):
        print(f"{s['rank']}위 {s['player_name']:6s} ({s['team_name']}) {s['goals']}골")

    print("\n=== 최근 경기 결과 ===")
    for m in collector.get_recent_matches(days_back=14)[:5]:
        print(f"{m['utc_date'][:10]} {m['home_team_name']} {m['home_score']}-{m['away_score']} {m['away_team_name']}")
