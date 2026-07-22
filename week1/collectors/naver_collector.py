# -*- coding: utf-8 -*-
"""
naver_collector.py
==================
네이버 뉴스 검색 API를 이용한 축구 뉴스 수집 모듈

네이버 API 발급:
    1. https://developers.naver.com/apps 접속
    2. 애플리케이션 등록 → "검색" API 선택
    3. Client ID / Client Secret 발급
    4. .env 파일에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 입력

공식 문서:
    https://developers.naver.com/docs/serviceapi/search/news/news.md

사용법:
    from collectors.naver_collector import NaverNewsCollector

    collector = NaverNewsCollector()
    articles = collector.collect_keywords(["EPL", "손흥민", "프리미어리그"])
"""

import os
import hashlib
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv

# .env 파일 로드 (week1 폴더 기준)
load_dotenv()

logger = logging.getLogger(__name__)


# =============================================
# 기본 검색 키워드 목록 (축구 관련)
# =============================================
DEFAULT_KEYWORDS = [
    # ── EPL / 해외 리그 ───────────────────────────────────────
    "EPL",
    "프리미어리그",
    "라리가",
    "분데스리가",
    "세리에A",
    "챔피언스리그",
    "유로파리그",
    "이적시장",
    # ── 해외 구단 ─────────────────────────────────────────────
    "맨체스터시티",
    "리버풀",
    "아스날",
    "첼시",
    "토트넘",
    "맨체스터유나이티드",
    "레알마드리드",
    "바르셀로나",
    "바이에른뮌헨",
    "PSG",
    # ── 한국 선수 ─────────────────────────────────────────────
    "손흥민",
    "이강인",
    "황희찬",
    "김민재",
    "조규성",
    "오현규",
    "황인범",
    # ── 해외 스타 플레이어 ───────────────────────────────────
    "홀란드",
    "살라",
    "엠바페",
    "벨링엄",
    "야말",
    "케인",
    # ── K리그 ─────────────────────────────────────────────────
    "K리그",
    "전북현대",
    "울산HD",
    "FC서울",
    # ── 2026 FIFA 월드컵 ──────────────────────────────────────
    "2026 월드컵",
    "월드컵 한국",
    "월드컵 조별리그",
    "월드컵 16강",
    "태극전사",
    "국가대표 월드컵",
    "월드컵 손흥민",
    "월드컵 이강인",
    "월드컵 경기결과",
    "FIFA 월드컵",
]

# 리그별 키워드 및 LEAGUE_KEYWORD_MAP은 week1/league_registry.py로
# 이전했다 — 예전엔 이 파일에 직접 정의돼 있었는데, constants.py의
# 화면 필터 키워드와 따로 관리되다 보니 두 목록이 어긋나는 버그가
# 반복됐다(예: 브라질세리에A의 "브라질" 단독 키워드가 한쪽에만 남아있던
# 사례, 2026-07-22). 이제 league_registry.py 하나만 고치면 수집·필터·
# 화면 표시가 전부 같이 반영된다.
import sys as _sys
import os as _os
_WEEK1_PATH = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _WEEK1_PATH not in _sys.path:
    _sys.path.insert(0, _WEEK1_PATH)
from league_registry import LEAGUES as _LEAGUES

LEAGUE_KEYWORD_MAP: dict = {code: meta["keywords"] for code, meta in _LEAGUES.items()}


# 네이버 뉴스 검색 API 엔드포인트
NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"


def _parse_naver_date(pub_date_str: str) -> datetime:
    """
    네이버 API 날짜 형식(RFC 2822) → timezone-aware datetime 변환
    예: "Tue, 23 Jun 2026 10:30:00 +0900"
    """
    try:
        return parsedate_to_datetime(pub_date_str)
    except Exception:
        return datetime.now(timezone.utc)


def _clean_naver_html(text: str) -> str:
    """
    네이버 API 응답의 HTML 엔티티 및 태그 제거
    예: &lt;b&gt;손흥민&lt;/b&gt; → 손흥민
    """
    import re
    import html
    text = html.unescape(text)                   # HTML 엔티티 디코딩
    text = re.sub(r"<[^>]+>", "", text)          # HTML 태그 제거
    return text.strip()


def _generate_article_id(url: str, title: str) -> str:
    """URL + 제목 기반 고유 ID 생성"""
    content = f"{url}|{title}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


class NaverNewsCollector:
    """
    네이버 뉴스 검색 API 수집기

    환경변수 필요:
        NAVER_CLIENT_ID     : 네이버 API Client ID
        NAVER_CLIENT_SECRET : 네이버 API Client Secret

    예시:
        collector = NaverNewsCollector()

        # 단일 키워드 검색
        articles = collector.collect_keyword("EPL")

        # 여러 키워드 검색 (중복 제거 포함)
        articles = collector.collect_keywords(["EPL", "손흥민", "프리미어리그"])
    """

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        display: int = 20,
        sort: str = "date",
    ):
        """
        Parameters
        ----------
        client_id : str, optional
            네이버 API Client ID. 미입력 시 환경변수 NAVER_CLIENT_ID 사용.
        client_secret : str, optional
            네이버 API Client Secret. 미입력 시 환경변수 NAVER_CLIENT_SECRET 사용.
        display : int
            한 번에 가져올 기사 수 (최대 100, 기본 20)
        sort : str
            정렬 기준 - "date"(최신순) 또는 "sim"(정확도순)
        """
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")
        self.display = min(display, 100)  # 최대 100
        self.sort = sort

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "네이버 API 키가 없습니다.\n"
                ".env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 입력하세요.\n"
                "발급: https://developers.naver.com/apps"
            )

    def _build_headers(self) -> dict:
        """API 요청 헤더 생성"""
        return {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

    def collect_keyword(self, keyword: str, start: int = 1) -> list[dict]:
        """
        단일 키워드로 네이버 뉴스를 검색합니다.

        Parameters
        ----------
        keyword : str
            검색 키워드 (예: "EPL", "손흥민")
        start : int
            검색 시작 위치 (1~1000, 기본 1)

        Returns
        -------
        list[dict]
            수집된 기사 목록. 각 항목:
            - article_id  : 고유 ID
            - title       : 기사 제목 (HTML 태그 제거됨)
            - url         : 네이버 뉴스 링크
            - original_url: 원본 기사 링크
            - summary     : 요약 (description)
            - published_at: 발행일시 (datetime, timezone-aware)
            - source_name : "네이버뉴스"
            - keyword     : 검색에 사용된 키워드
            - language    : "ko"
            - category    : "naver_news"
            - collected_at: 수집 시각
        """
        params = {
            "query": keyword,
            "display": self.display,
            "start": start,
            "sort": self.sort,
        }

        logger.info(f"[네이버뉴스] '{keyword}' 검색 시작 (display={self.display})")

        try:
            response = requests.get(
                NAVER_NEWS_API_URL,
                headers=self._build_headers(),
                params=params,
                timeout=10,
            )

            # 인증 오류 처리
            if response.status_code == 401:
                logger.error("네이버 API 인증 실패. Client ID/Secret을 확인하세요.")
                return []

            # 할당량 초과 처리
            if response.status_code == 429:
                logger.warning("네이버 API 호출 한도 초과. 잠시 후 재시도하세요.")
                return []

            response.raise_for_status()
            data = response.json()

        except requests.exceptions.Timeout:
            logger.error(f"[네이버뉴스] '{keyword}' 요청 타임아웃")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[네이버뉴스] '{keyword}' 요청 오류: {e}")
            return []

        articles = []
        for item in data.get("items", []):
            try:
                title = _clean_naver_html(item.get("title", ""))
                url = item.get("link", "").strip()
                original_url = item.get("originallink", "").strip()
                summary = _clean_naver_html(item.get("description", ""))[:500]
                pub_date = _parse_naver_date(item.get("pubDate", ""))

                if not title or not url:
                    continue

                article = {
                    "article_id": _generate_article_id(url, title),
                    "title": title,
                    "url": url,
                    "original_url": original_url,
                    "summary": summary,
                    "published_at": pub_date,
                    "source_name": "네이버뉴스",
                    "keyword": keyword,
                    "language": "ko",
                    "category": "naver_news",
                    "collected_at": datetime.now(timezone.utc),
                }
                articles.append(article)

            except Exception as e:
                logger.warning(f"[네이버뉴스] 기사 파싱 오류: {e}")
                continue

        logger.info(f"[네이버뉴스] '{keyword}' 수집 완료: {len(articles)}건")
        return articles
    def collect_keywords(self, keywords: list[str] = None, max_workers: int = 5) -> list[dict]:
        """
        여러 키워드로 병렬 수집합니다.

        Parameters
        ----------
        keywords : list[str], optional
            검색 키워드 목록. None이면 DEFAULT_KEYWORDS 사용.
        max_workers : int
            동시 요청 스레드 수 (기본 5)

        Returns
        -------
        list[dict]
            중복 제거된 기사 목록
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

        if keywords is None:
            keywords = DEFAULT_KEYWORDS

        all_articles: list[dict] = []
        seen_urls: set[str] = set()

        def _safe_collect(kw):
            try:
                return self.collect_keyword(kw)
            except Exception as e:
                logger.warning(f"[네이버뉴스] '{kw}' 수집 실패: {e}")
                return []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_safe_collect, kw): kw for kw in keywords}
            for future in _as_completed(futures):
                for article in future.result():
                    url = article.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_articles.append(article)

        logger.info(f"[네이버뉴스] 키워드 {len(keywords)}개 수집 완료: {len(all_articles)}건")
        return all_articles

    def collect_league_keywords(self, league_code: str, max_workers: int = 5) -> list[dict]:
        """
        리그/대회별 전용 키워드로 집중 수집합니다.

        Parameters
        ----------
        league_code : str
            리그 코드 (예: "WC", "PL", "KL1", "PD", "BL1", "SA", "FL1")
        max_workers : int
            동시 요청 스레드 수 (기본 5)

        Returns
        -------
        list[dict]
            해당 리그/대회 관련 기사 목록
        """
        keywords = LEAGUE_KEYWORD_MAP.get(league_code, DEFAULT_KEYWORDS)
        logger.info(
            f"[네이버뉴스] 리그별 집중 수집 시작 — "
            f"league={league_code}, 키워드 {len(keywords)}개"
        )
        return self.collect_keywords(keywords=keywords, max_workers=max_workers)


# =============================================
# 직접 실행 시 테스트
# =============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = NaverNewsCollector(display=10)
    articles = collector.collect_keywords(keywords=["EPL", "손흥민"], max_workers=2)
    print(f"\n총 수집 기사 수: {len(articles)}건")
    for a in articles[:3]:
        print(f"  {a.get('title','(제목없음)')[:60]}")
