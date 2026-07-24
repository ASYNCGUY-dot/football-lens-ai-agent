# -*- coding: utf-8 -*-
"""
football_data_collector.py
==========================
football-data.org API v4를 이용한 EPL 경기 데이터 수집 모듈

API 키 발급:
    1. https://www.football-data.org/client/register 접속
    2. 무료 플랜 가입 (무료: 10 요청/분, EPL 포함)
    3. 발급된 API Key를 .env 파일의 FOOTBALL_DATA_API_KEY에 입력

공식 문서:
    https://www.football-data.org/documentation/quickstart

EPL 리그 코드: PL (Premier League)

사용법:
    from collectors.football_data_collector import FootballDataCollector

    collector = FootballDataCollector()

    # 현재 시즌 순위
    standings = collector.get_standings()

    # 최근 경기 결과
    matches = collector.get_recent_matches(matchday_range=5)

    # 특정 경기 상세 정보
    match = collector.get_match(match_id=12345)
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================
# 상수 정의
# =============================================
BASE_URL = "https://api.football-data.org/v4"
EPL_COMPETITION_CODE = "PL"         # Premier League
RATE_LIMIT_DELAY = 6.1              # 무료 플랜: 10req/min → 6초 간격

# ── 무료 플랜에서 수집 가능한 전체 리그 ──────────────────────
AVAILABLE_LEAGUES = {
    "EPL":          {"code": "PL",  "name": "프리미어리그",       "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "라리가":       {"code": "PD",  "name": "라리가",             "flag": "🇪🇸"},
    "분데스리가":   {"code": "BL1", "name": "분데스리가",         "flag": "🇩🇪"},
    "세리에A":      {"code": "SA",  "name": "세리에A",            "flag": "🇮🇹"},
    "리그앙":       {"code": "FL1", "name": "리그앙",             "flag": "🇫🇷"},
    "챔피언스리그": {"code": "CL",  "name": "UEFA 챔피언스리그", "flag": "⭐"},
    "브라질세리에A": {"code": "BSA", "name": "브라질 세리에A",    "flag": "🇧🇷"},
    "코파리베르타도레스": {"code": "CLI", "name": "코파 리베르타도레스", "flag": "🏆"},
    "EFL챔피언십":  {"code": "ELC", "name": "EFL 챔피언십",       "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "에레디비시":   {"code": "DED", "name": "에레디비시",         "flag": "🇳🇱"},
    "프리메이라리가": {"code": "PPL", "name": "프리메이라리가",     "flag": "🇵🇹"},
    # 주의: UEFA 유러피언 챔피언십(EC)은 API가 지원은 하지만 4년 주기
    # 대회라 currentSeason이 2024-06~2024-07로 고정돼 있다(다음 대회
    # 2028년, 2026-07-22 확인) — 지금 추가해봐야 계속 비시즌만 뜨므로
    # 뺐다. 2028년 유로 개막 전에 다시 검토할 것.
    #
    # 주의: "유로파리그"(EL)는 이 API의 무료 플랜에서 지원하지 않아 제거했다
    # (2026-07-21 /v4/competitions 목록 직접 확인 — 404).
    #
    # K리그(KL1)도 이 목록에 없다 — football-data.org가 애초에 K리그를
    # 지원하지 않는다(/v4/competitions에 없음). 대안으로 API-Football을
    # 검토해 실제 키까지 발급받아 테스트했으나(2026-07-22), 무료 플랜이
    # 2022~2024 시즌 데이터만 제공하고 현재 시즌은 전부 막혀 있어
    # ("Free plans do not have access to this season, try from 2022 to
    # 2024" — standings/topscorers/fixtures 세 엔드포인트 모두 동일)
    # "이번 시즌 순위/득점왕"에는 쓸 수 없다고 확인됨. 유료 Pro 플랜
    # ($19/월, 7,500req/일)부터 현재 시즌이 열리는데, 리그 하나 때문에
    # 매달 비용을 낼 정도는 아니라고 판단해 보류하기로 함(사용자 결정,
    # 2026-07-22). K리그는 순위표/득점왕 없이 뉴스 기반으로만 운영한다
    # — players.py의 KL1 분기 참고(예측 탭 자체는 이후 완전히 제거함).
    # API_FOOTBALL_KEY는 .env에 남아있지만 실제로 쓰는 코드는
    # 없다(나중에 유료 전환하면 그때 collector를 새로 만들면 됨).
}

# 2026 FIFA 월드컵 설정
WORLDCUP_CODE  = "WC"
WORLDCUP_YEAR  = 2026
# 2026 WC: 48개국, 12그룹 (A~L)
WORLDCUP_GROUPS = [f"GROUP_{chr(65+i)}" for i in range(12)]  # GROUP_A ~ GROUP_L


class FootballDataCollector:
    """
    football-data.org API v4 수집기

    주요 메서드:
        get_standings()         : 현재 시즌 EPL 순위표
        get_recent_matches()    : 최근 완료된 경기 결과
        get_upcoming_matches()  : 예정된 경기 일정
        get_match(match_id)     : 특정 경기 상세 정보
        get_top_scorers()       : 득점 순위

    환경변수:
        FOOTBALL_DATA_API_KEY : football-data.org API 키
    """

    def __init__(self, api_key: str = None, competition: str = EPL_COMPETITION_CODE):
        """
        Parameters
        ----------
        api_key : str, optional
            API 키. 미입력 시 환경변수 FOOTBALL_DATA_API_KEY 사용.
        competition : str
            리그 코드. 기본값: "PL" (EPL)
            다른 리그: "PD"(라리가), "BL1"(분데스리가), "SA"(세리에A), "FL1"(리그앙)
        """
        self.api_key = api_key or os.getenv("FOOTBALL_DATA_API_KEY")
        self.competition = competition
        self._last_request_time = 0  # rate limiting 용

        if not self.api_key:
            raise ValueError(
                "FOOTBALL_DATA_API_KEY가 없습니다.\n"
                ".env 파일에 API 키를 입력하거나 인자로 전달하세요.\n"
                "발급: https://www.football-data.org/client/register"
            )

    def _get_headers(self) -> dict:
        """
        API 요청에 필요한 인증 헤더를 반환합니다.

        Returns
        -------
        dict
            X-Auth-Token 키를 포함한 헤더 딕셔너리
        """
        return {"X-Auth-Token": self.api_key}

    def _request(self, endpoint: str, params: dict = None) -> dict | None:
        """
        API 요청 공통 메서드 (rate limit, 오류 처리 포함)

        Parameters
        ----------
        endpoint : str
            API 경로 (예: "/competitions/PL/standings")
        params : dict, optional
            쿼리 파라미터

        Returns
        -------
        dict or None
            응답 JSON. 실패 시 None.
        """
        # Rate limiting: 마지막 요청으로부터 최소 6.1초 대기
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)

        url = f"{BASE_URL}{endpoint}"
        logger.info(f"API 요청: {url} params={params}")

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=15,
            )
            self._last_request_time = time.time()

            if response.status_code == 401:
                logger.error("API 인증 실패. API 키를 확인하세요.")
                return None
            if response.status_code == 403:
                logger.error("접근 권한 없음. 해당 리그는 유료 플랜이 필요할 수 있습니다.")
                return None
            if response.status_code == 429:
                logger.warning("Rate limit 초과. 60초 대기 후 재시도...")
                time.sleep(60)
                return self._request(endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"요청 타임아웃: {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"요청 오류: {e}")

        return None

    # =============================================
    # 순위표 (Standings)
    # =============================================
    def get_standings(self, season: int = None) -> list[dict]:
        """
        순위표를 가져옵니다.

        코파리베르타도레스처럼 조별리그(8개 조)로 진행되는 대회는 API가
        standings 배열에 조(Group A~H)별로 항목을 따로 준다. 예전엔
        standings[0]만 가져와서 첫 조 4팀만 반환하고 나머지 28팀을 통째로
        버렸다(2026-07-24 발견 — 라리가/분데스리가/세리에A/리그앙/
        브라질세리에A/EFL챔피언십/에레디비시/프리메이라리가/챔피언스리그는
        전부 단일 그룹이라 문제없었고, CLI만 걸림). 이제 모든 그룹을
        순회해서 각 팀에 group 필드를 붙여 전부 반환한다 — 단일 리그는
        group이 None으로 채워지고 동작이 예전과 동일하다.

        Parameters
        ----------
        season : int, optional
            시즌 연도 (예: 2024 → 2024/25 시즌). 기본값: 현재 시즌.

        Returns
        -------
        list[dict]
            각 팀의 순위 정보. 각 항목:
            - rank        : 조 내 순위 (조별리그면 조 안에서의 순위)
            - team_id     : 팀 고유 ID
            - team_name   : 팀 이름
            - played      : 경기 수
            - won         : 승
            - draw        : 무
            - lost        : 패
            - goals_for   : 득점
            - goals_against: 실점
            - goal_diff   : 득실차
            - points      : 승점
            - form        : 최근 5경기 결과 (예: "WWDLW")
            - group       : 조 이름 (예: "Group A") — 단일 리그면 None
        """
        params = {"season": season} if season else {}
        data = self._request(f"/competitions/{self.competition}/standings", params)

        if not data:
            return []

        standings = []
        try:
            for group_entry in data.get("standings", []):
                if group_entry.get("type") != "TOTAL":
                    continue
                group_name = group_entry.get("group")  # 조별리그가 아니면 None
                for row in group_entry.get("table", []):
                    team = row.get("team", {})
                    standings.append({
                        "rank": row.get("position"),
                        "team_id": team.get("id"),
                        "team_name": team.get("name"),
                        "played": row.get("playedGames"),
                        "won": row.get("won"),
                        "draw": row.get("draw"),
                        "lost": row.get("lost"),
                        "goals_for": row.get("goalsFor"),
                        "goals_against": row.get("goalsAgainst"),
                        "goal_diff": row.get("goalDifference"),
                        "points": row.get("points"),
                        "form": row.get("form", ""),
                        "group": group_name,
                        "collected_at": datetime.now(timezone.utc),
                    })
        except (KeyError, IndexError) as e:
            logger.error(f"순위표 파싱 오류: {e}")

        logger.info(f"순위표 수집 완료: {len(standings)}팀")
        return standings

    # =============================================
    # 경기 결과 (Matches)
    # =============================================
    def get_recent_matches(self, days_back: int = 7) -> list[dict]:
        """
        최근 완료된 EPL 경기 결과를 가져옵니다.

        Parameters
        ----------
        days_back : int
            며칠 전까지의 경기를 가져올지 (기본 7일)

        Returns
        -------
        list[dict]
            완료된 경기 목록. 각 항목:
            - match_id      : 경기 고유 ID
            - matchday      : 라운드
            - utc_date      : 경기 일시 (UTC)
            - status        : 경기 상태 ("FINISHED")
            - home_team_id  : 홈팀 ID
            - home_team_name: 홈팀 이름
            - away_team_id  : 원정팀 ID
            - away_team_name: 원정팀 이름
            - home_score    : 홈팀 최종 스코어
            - away_score    : 원정팀 최종 스코어
            - home_ht_score : 홈팀 전반전 스코어
            - away_ht_score : 원정팀 전반전 스코어
            - winner        : 승자 ("HOME_TEAM" / "AWAY_TEAM" / "DRAW")
            - collected_at  : 수집 시각
        """
        try:
            date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
            params = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED"}
            data = self._request(f"/competitions/{self.competition}/matches", params)
            if not data:
                return []
            return self._parse_matches(data.get("matches", []))
        except (ValueError, KeyError) as e:
            logger.error(f"[get_recent_matches] 파싱 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"[get_recent_matches] 예외 발생: {e}")
            return []

    def get_upcoming_matches(self, days_ahead: int = 7) -> list[dict]:
        """
        예정된 EPL 경기 일정을 가져옵니다.

        Parameters
        ----------
        days_ahead : int
            며칠 후까지의 경기를 가져올지 (기본 7일)

        Returns
        -------
        list[dict]
            예정 경기 목록. 오류 발생 시 빈 리스트 반환.
        """
        try:
            date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            date_to = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            params = {"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED"}
            data = self._request(f"/competitions/{self.competition}/matches", params)
            if not data:
                return []
            return self._parse_matches(data.get("matches", []))
        except (ValueError, KeyError) as e:
            logger.error(f"[get_upcoming_matches] 파싱 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"[get_upcoming_matches] 예외 발생: {e}")
            return []

    def get_match(self, match_id: int) -> dict | None:
        """
        특정 경기의 상세 정보를 가져옵니다.

        Parameters
        ----------
        match_id : int
            경기 고유 ID (API에서 반환된 값)

        Returns
        -------
        dict or None
            경기 정보 딕셔너리. 찾지 못하거나 오류 발생 시 None 반환.
        """
        try:
            data = self._request(f"/matches/{match_id}")
            if not data:
                return None
            matches = self._parse_matches([data])
            return matches[0] if matches else None
        except (ValueError, KeyError) as e:
            logger.error(f"[get_match] 파싱 오류 (match_id={match_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"[get_match] 예외 발생 (match_id={match_id}): {e}")
            return None

    def _parse_matches(self, raw_matches: list) -> list[dict]:
        """
        API 응답의 경기 목록을 표준 딕셔너리 형식으로 변환합니다.
        """
        matches = []
        for m in raw_matches:
            try:
                home_team = m.get("homeTeam", {})
                away_team = m.get("awayTeam", {})
                score = m.get("score", {})
                full_time = score.get("fullTime", {})
                half_time = score.get("halfTime", {})

                match = {
                    "match_id": m.get("id"),
                    "matchday": m.get("matchday"),
                    "utc_date": m.get("utcDate"),
                    "status": m.get("status"),
                    "home_team_id": home_team.get("id"),
                    "home_team_name": home_team.get("name"),
                    "away_team_id": away_team.get("id"),
                    "away_team_name": away_team.get("name"),
                    "home_score": full_time.get("home"),
                    "away_score": full_time.get("away"),
                    "home_ht_score": half_time.get("home"),
                    "away_ht_score": half_time.get("away"),
                    "winner": score.get("winner"),  # HOME_TEAM / AWAY_TEAM / DRAW
                    "competition": self.competition,
                    "season": m.get("season", {}).get("startDate", "")[:4],
                    "collected_at": datetime.now(timezone.utc),
                }
                matches.append(match)

            except Exception as e:
                logger.warning(f"경기 파싱 오류: {e}")
                continue

        return matches

    # =============================================
    # 득점 순위 (Top Scorers)
    # =============================================
    def get_top_scorers(self, limit: int = 10) -> list[dict]:
        """
        EPL 득점 순위를 가져옵니다.

        Parameters
        ----------
        limit : int
            가져올 선수 수 (기본 10명)

        Returns
        -------
        list[dict]
            각 선수 정보:
            - rank          : 순위
            - player_id     : 선수 ID
            - player_name   : 선수 이름
            - nationality   : 국적
            - team_id       : 소속팀 ID
            - team_name     : 소속팀 이름
            - goals         : 득점
            - assists        : 어시스트
            - penalties     : 패널티 득점
        """
        try:
            params = {"limit": limit}
            data = self._request(f"/competitions/{self.competition}/scorers", params)

            if not data:
                return []

            scorers = []
            for i, s in enumerate(data.get("scorers", []), start=1):
                try:
                    player = s.get("player", {})
                    team = s.get("team", {})
                    scorers.append({
                        "rank": i,
                        "player_id": player.get("id"),
                        "player_name": player.get("name"),
                        "nationality": player.get("nationality"),
                        "team_id": team.get("id"),
                        "team_name": team.get("name"),
                        "goals": s.get("goals", 0),
                        "assists": s.get("assists", 0),
                          "penalties": s.get("penalties", 0),
                        "collected_at": datetime.now(timezone.utc),
                    })
                except (KeyError, ValueError) as e:
                    logger.warning(f"[get_top_scorers] 선수 파싱 오류 (건너뜀): {e}")
                    continue

            logger.info(f"득점 순위 수집 완료: {len(scorers)}명")
            return scorers

        except (KeyError, ValueError) as e:
            logger.error(f"[get_top_scorers] 파싱 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"[get_top_scorers] 예외 발생: {e}")
            return []


    # =============================================
    # 전 리그 일괄 수집
    # =============================================
    def get_all_leagues_standings(self, leagues: list[str] = None, top_n: int = 5) -> dict:
        """
        여러 리그의 순위표 상위 N팀을 수집합니다.

        Parameters
        ----------
        leagues : list[str], optional
            수집할 리그 키 목록. 기본값: AVAILABLE_LEAGUES 전체.
            예: ["EPL", "라리가", "분데스리가"]
        top_n : int
            리그별 상위 팀 수 (기본 5)

        Returns
        -------
        dict
            {리그키: {"meta": {...}, "standings": [...]}} 형태
            예: {"EPL": {"meta": {"name":"프리미어리그","flag":"🏴"}, "standings": [...]}}
        """
        target = leagues or list(AVAILABLE_LEAGUES.keys())
        result = {}
        original_competition = self.competition

        for league_key in target:
            league_info = AVAILABLE_LEAGUES.get(league_key)
            if not league_info:
                logger.warning(f"알 수 없는 리그 키: {league_key}")
                continue
            try:
                self.competition = league_info["code"]
                standings = self.get_standings()
                if standings:
                    result[league_key] = {
                        "meta": league_info,
                        "standings": standings[:top_n],
                    }
                    logger.info(f"[{league_key}] 순위 {len(standings[:top_n])}팀 수집")
            except Exception as e:
                logger.error(f"[{league_key}] 수집 오류: {e}")

        self.competition = original_competition
        return result

    def get_all_leagues_top_scorers(self, leagues: list[str] = None, limit: int = 5) -> dict:
        """
        여러 리그의 득점 순위 상위 N명을 수집합니다.

        Parameters
        ----------
        leagues : list[str], optional
            수집할 리그 키 목록. 기본값: ["EPL", "라리가", "분데스리가"]
        limit : int
            리그별 선수 수 (기본 5)

        Returns
        -------
        dict
            {리그키: {"meta": {...}, "scorers": [...]}} 형태
        """
        target = leagues or ["EPL", "라리가", "분데스리가"]
        result = {}
        original_competition = self.competition

        for league_key in target:
            league_info = AVAILABLE_LEAGUES.get(league_key)
            if not league_info:
                continue
            try:
                self.competition = league_info["code"]
                scorers = self.get_top_scorers(limit=limit)
                if scorers:
                    result[league_key] = {
                        "meta": league_info,
                        "scorers": scorers,
                    }
            except Exception as e:
                logger.error(f"[{league_key}] 득점 순위 오류: {e}")

        self.competition = original_competition
        return result

    # =========================================================
    # 2026 FIFA 월드컵 전용 메서드
    # =========================================================

    def get_worldcup_groups(self) -> list[dict]:
        """
        2026 FIFA 월드컵 그룹 순위표를 반환합니다.

        Returns
        -------
        list[dict]
            그룹별 순위 목록. 각 항목:
            - group       : 그룹명 (예: "GROUP_A")
            - group_label : 표시용 라벨 (예: "A조")
            - standings   : 팀 순위 리스트 (position, team_name, flag, played, won, draw, lost, gf, ga, gd, points)
        """
        original = self.competition
        self.competition = WORLDCUP_CODE
        try:
            data = self._request(f"/competitions/{WORLDCUP_CODE}/standings",
                                 {"season": WORLDCUP_YEAR})
            if not data:
                logger.warning("[WorldCup] 그룹 순위 데이터 없음")
                return []

            groups = []
            for standing in data.get("standings", []):
                grp_raw = standing.get("group", "")
                if not grp_raw or standing.get("type") != "TOTAL":
                    continue
                # GROUP_A → A조
                letter = grp_raw.replace("GROUP_", "")
                table = []
                for row in standing.get("table", []):
                    team = row.get("team", {})
                    table.append({
                        "position":  row.get("position", 0),
                        "team_id":   team.get("id"),
                        "team_name": team.get("name", ""),
                        "team_short": team.get("shortName", team.get("name", "")),
                        "crest_url": team.get("crest", ""),
                        "played":    row.get("playedGames", 0),
                        "won":       row.get("won", 0),
                        "draw":      row.get("draw", 0),
                        "lost":      row.get("lost", 0),
                        "gf":        row.get("goalsFor", 0),
                        "ga":        row.get("goalsAgainst", 0),
                        "gd":        row.get("goalDifference", 0),
      
                        "points":    row.get("points", 0),
                        "form":      row.get("form", ""),
                    })
                groups.append({
                    "group":       grp_raw,
                    "group_label": f"{letter}조",
                    "standings":   table,
                })
            logger.info(f"[WorldCup] 그룹 순위 수집: {len(groups)}개 그룹")
            return groups

        except Exception as e:
            logger.error(f"[WorldCup] 그룹 순위 오류: {e}")
            return []
        finally:
            self.competition = original

    def get_worldcup_matches(
        self,
        status: str = None,
        days_back: int = 3,
        days_ahead: int = 5,
    ) -> list[dict]:
        """2026 FIFA 월드컵 경기 일정 및 결과를 반환합니다."""
        try:
            if status:
                params = {"status": status}
            else:
                now = datetime.now(timezone.utc)
                date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
                date_to   = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                params = {"dateFrom": date_from, "dateTo": date_to}

            data = self._request(f"/competitions/{WORLDCUP_CODE}/matches", params)
            if not data:
                return []

            matches = []
            for m in data.get("matches", []):
                home  = m.get("homeTeam", {})
                away  = m.get("awayTeam", {})
                score = m.get("score", {})
                full  = score.get("fullTime", {})
                matches.append({
                    "match_id":   m.get("id"),
                    "utc_date":   m.get("utcDate", ""),
                    "status":     m.get("status", ""),
                    "stage":      m.get("stage", ""),
                    "group":      m.get("group", ""),
                    "matchday":   m.get("matchday"),
                    "home_team":  home.get("name", ""),
                    "home_short": home.get("shortName", home.get("name", "")),
                    "home_crest": home.get("crest", ""),
                    "away_team":  away.get("name", ""),
                    "away_short": away.get("shortName", away.get("name", "")),
                    "away_crest": away.get("crest", ""),
                    "home_score": full.get("home"),
                    "away_score": full.get("away"),
                    "winner":     score.get("winner", ""),
                })
            logger.info(f"[WorldCup] 경기 수집: {len(matches)}건")
            return matches

        except Exception as e:
            logger.error(f"[WorldCup] 경기 수집 오류: {e}")
            return []

    def get_worldcup_scorers(self, limit: int = 10) -> list[dict]:
        """2026 FIFA 월드컵 득점 순위 상위 N명을 반환합니다."""
        try:
            data = self._request(
                f"/competitions/{WORLDCUP_CODE}/scorers",
                {"limit": limit, "season": WORLDCUP_YEAR},
            )
            if not data:
                return []

            scorers = []
            for i, s in enumerate(data.get("scorers", [])[:limit], 1):
                player = s.get("player", {})
                team   = s.get("team", {})
                scorers.append({
                    "rank":        i,
                    "player_id":   player.get("id"),
                    "player_name": player.get("name", ""),
                    "nationality": player.get("nationality", ""),
                    "team_name":   team.get("name", ""),
                    "team_short":  team.get("shortName", team.get("name", "")),
                    "goals":       s.get("goals", 0),
                    "assists":     s.get("assists", 0),
                    "penalties":   s.get("penalties", 0),
                })
            logger.info(f"[WorldCup] 득점 순위 수집: {len(scorers)}명")
            return scorers

        except Exception as e:
            logger.error(f"[WorldCup] 득점 순위 오류: {e}")
            return []

    def get_squad(self, team_id: int) -> list[dict]:
        """특정 팀의 선수단 정보를 가져옵니다."""
        data = self._request(f"/teams/{team_id}")
        if not data:
            return []

        squad = []
        for p in data.get("squad", []):
            try:
                squad.append({
                    "player_id":     p.get("id"),
                    "player_name":   p.get("name"),
                    "position":      p.get("position", ""),
                    "nationality":   p.get("nationality", ""),
                    "date_of_birth": p.get("dateOfBirth", "")[:10],
                    "shirt_number":  p.get("shirtNumber"),
                })
            except Exception as e:
                logger.warning(f"선수 파싱 오류: {e}")

        logger.info(f"선수단 수집 완료 (team_id={team_id}): {len(squad)}명")
        return squad


# =============================================
# 직접 실행 시 테스트
# =============================================
if __name__ == "__main__":
    try:
        collector = FootballDataCollector()

        print("=== EPL 순위표 ===")
        standings = collector.get_standings()
        for team in standings[:5]:
            print(f"{team['rank']}위 {team['team_name']:30s} {team['points']}점")

        print("\n=== 2026 월드컵 그룹 순위 ===")
        wc = FootballDataCollector(competition="WC")
        groups = wc.get_worldcup_groups()
        for g in groups[:2]:
            print(f"\n[{g['group_label']}]")
            for t in g["standings"]:
                print(f"  {t['position']}위 {t['team_name']} {t['points']}점")

    except ValueError as e:
        print(f"오류: {e}")
