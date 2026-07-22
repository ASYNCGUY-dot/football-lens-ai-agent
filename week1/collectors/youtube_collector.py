# -*- coding: utf-8 -*-
"""
youtube_collector.py
====================
YouTube Data API v3를 이용한 축구 하이라이트 영상 메타데이터 수집 모듈

API 키 발급:
    1. https://console.cloud.google.com 접속
    2. 프로젝트 생성 → YouTube Data API v3 활성화
    3. API 키 발급
    4. .env 파일에 YOUTUBE_API_KEY 입력

무료 할당량: 10,000 units/day
    - search.list: 100 units/회
    - videos.list: 1 unit/회

사용법:
    from collectors.youtube_collector import YouTubeCollector

    collector = YouTubeCollector()
    videos = collector.search_football_videos(["EPL highlights", "손흥민 골"])
"""

import os
import logging
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# 기본 검색 키워드 (축구 하이라이트 위주) — league_code를 안 넘겼을 때만 쓴다.
DEFAULT_QUERIES = [
    "EPL highlights this week",
    "Premier League goals",
    "손흥민 골 하이라이트",
    "이강인 하이라이트",
    "K리그 하이라이트",
    "Champions League highlights",
]

# 리그별 영상 검색 쿼리 — 예전엔 리그 선택과 무관하게 항상 위 DEFAULT_QUERIES를
# 그대로 써서, K리그를 선택해도 EPL/챔피언스리그 하이라이트가 섞여 나왔다
# (Naver 뉴스 수집기의 LEAGUE_KEYWORD_MAP과 동일한 종류의 버그였다). 같은
# LEAGUE_KEYWORD_MAP을 재사용해 리그별 쿼리를 만든다.
_LEAGUE_VIDEO_QUERIES: dict[str, list[str]] = {
    "WC":  ["2026 FIFA 월드컵 하이라이트", "World Cup 2026 highlights", "월드컵 한국 하이라이트"],
    "PL":  ["EPL highlights this week", "Premier League goals", "손흥민 하이라이트"],
    "KL1": ["K리그 하이라이트", "K리그1 하이라이트", "K League highlights"],
    "PD":  ["라리가 하이라이트", "La Liga highlights"],
    "BL1": ["분데스리가 하이라이트", "Bundesliga highlights"],
    "SA":  ["세리에A 하이라이트", "Serie A highlights"],
    "FL1": ["리그앙 하이라이트", "Ligue 1 highlights"],
    "CL":  ["챔피언스리그 하이라이트", "Champions League highlights"],
    "BSA": ["브라질세리에A 하이라이트", "Brasileirao highlights"],
    "CLI": ["코파리베르타도레스 하이라이트", "Copa Libertadores highlights"],
}


def get_league_video_queries(league_code: str) -> list[str]:
    """리그 코드에 맞는 YouTube 검색 쿼리를 반환한다. 없으면 DEFAULT_QUERIES."""
    return _LEAGUE_VIDEO_QUERIES.get(league_code, DEFAULT_QUERIES)


class YouTubeCollector:
    """
    YouTube Data API v3 기반 축구 영상 수집기

    환경변수:
        YOUTUBE_API_KEY : YouTube Data API v3 키

    주요 메서드:
        search_football_videos(queries) : 키워드별 영상 검색
        get_video_details(video_ids)    : 영상 상세 정보 (조회수 등)
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            logger.warning(
                "YOUTUBE_API_KEY 없음. Mock 데이터를 반환합니다.\n"
                "발급: https://console.cloud.google.com → YouTube Data API v3"
            )

    def _is_available(self) -> bool:
        return bool(self.api_key)

    def search_videos(self, query: str, max_results: int = 5) -> list[dict]:
        """
        단일 키워드로 YouTube 영상을 검색합니다.

        Parameters
        ----------
        query : str
            검색 키워드
        max_results : int
            최대 결과 수 (기본 5, 최대 50)

        Returns
        -------
        list[dict]
            영상 메타데이터 목록. 각 항목:
            - video_id   : YouTube 영상 ID
            - title      : 영상 제목
            - channel    : 채널 이름
            - published_at: 게시일 (datetime)
            - thumbnail  : 썸네일 URL
            - url        : YouTube 영상 URL
            - query      : 사용된 검색어
        """
        if not self._is_available():
            return self._mock_videos(query, max_results)

        try:
            params = {
                "key": self.api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": min(max_results, 50),
                "order": "relevance",
                "publishedAfter": self._days_ago_iso(14),  # 최근 2주
                "relevanceLanguage": "ko",
                "videoCategoryId": "17",  # Sports
            }
            resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            videos = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId", "")
                if not vid_id:
                    continue
                pub_str = snippet.get("publishedAt", "")
                try:
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    pub_dt = datetime.now(timezone.utc)

                videos.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published_at": pub_dt,
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "query": query,
                    "source": "youtube",
                    "collected_at": datetime.now(timezone.utc),
                })

            logger.info(f"[YouTube] '{query}' 검색: {len(videos)}건")
            return videos

        except requests.exceptions.RequestException as e:
            logger.error(f"[YouTube] '{query}' 요청 오류: {e}")
            return []

    def search_football_videos(
        self,
        queries: list[str] = None,
        max_per_query: int = 3,
        league_code: str = None,
    ) -> list[dict]:
        """
        여러 키워드로 YouTube 영상을 검색하고 중복을 제거합니다.

        Parameters
        ----------
        queries : list[str], optional
            검색 키워드 목록을 직접 지정하고 싶을 때만 쓴다. 지정하면
            league_code는 무시된다.
        max_per_query : int
            키워드당 최대 영상 수
        league_code : str, optional
            선택된 리그 코드(예: "KL1"). queries를 안 넘기면 이 리그에
            맞는 쿼리(get_league_video_queries)를 자동으로 쓴다 — 예전엔
            리그와 무관하게 항상 DEFAULT_QUERIES(EPL 위주)를 써서 K리그를
            선택해도 EPL/챔피언스리그 영상이 섞여 나왔다.

        Returns
        -------
        list[dict]
            중복 제거된 영상 메타데이터 목록
        """
        queries = queries or get_league_video_queries(league_code)
        all_videos = []
        seen_ids = set()

        for query in queries:
            videos = self.search_videos(query, max_results=max_per_query)
            for v in videos:
                if v["video_id"] not in seen_ids:
                    seen_ids.add(v["video_id"])
                    all_videos.append(v)

        # 최신순 정렬
        all_videos.sort(key=lambda v: str(v.get("published_at", "")), reverse=True)
        logger.info(f"[YouTube] 전체 수집 완료: {len(all_videos)}건")
        return all_videos

    def get_video_details(self, video_ids: list[str]) -> dict[str, dict]:
        """
        영상 ID 목록으로 조회수, 좋아요 수 등 상세 정보를 가져옵니다.

        Parameters
        ----------
        video_ids : list[str]
            YouTube 영상 ID 목록 (최대 50개)

        Returns
        -------
        dict[str, dict]
            {video_id: {"view_count": int, "like_count": int, "duration": str}}
        """
        if not self._is_available() or not video_ids:
            return {}

        try:
            params = {
                "key": self.api_key,
                "id": ",".join(video_ids[:50]),
                "part": "statistics,contentDetails",
            }
            resp = requests.get(YOUTUBE_VIDEOS_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            details = {}
            for item in data.get("items", []):
                vid_id = item.get("id", "")
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})
                details[vid_id] = {
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "duration": content.get("duration", ""),  # ISO 8601 (PT5M30S)
                }
            return details

        except Exception as e:
            logger.error(f"[YouTube] 영상 상세 조회 오류: {e}")
            return {}

    @staticmethod
    def _days_ago_iso(days: int) -> str:
        """n일 전 시각을 ISO 8601 UTC 문자열로 반환"""
        from datetime import timedelta
        dt = datetime.now(timezone.utc) - timedelta(days=days)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _mock_videos(query: str, count: int) -> list[dict]:
        """API 키 없을 때 반환하는 Mock 데이터"""
        mock_data = [
            {
                "video_id": f"mock_{query[:5]}_{i}",
                "title": f"[Mock] {query} - Highlights #{i+1}",
                "channel": "Football Highlights",
                "published_at": datetime.now(timezone.utc),
                "thumbnail": "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=320&h=180&fit=crop",
                "url": "https://www.youtube.com/results?search_query=" + query.replace(" ", "+"),
                "query": query,
                "source": "youtube_mock",
                "collected_at": datetime.now(timezone.utc),
            }
            for i in range(count)
        ]
        return mock_data


# =============================================
# 직접 실행 시 테스트
# =============================================
if __name__ == "__main__":
    collector = YouTubeCollector()
    videos = collector.search_football_videos(
        queries=["EPL highlights", "손흥민 골"],
        max_per_query=3,
    )
    print(f"\n총 수집 영상: {len(videos)}건\n")
    for v in videos[:5]:
        print(f"[{v['channel']}] {v['title']}")
        print(f"  URL: {v['url']}")
        print(f"  Thumbnail: {v['thumbnail']}")
        print()
