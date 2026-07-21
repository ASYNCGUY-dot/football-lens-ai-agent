"""
rss_collector.py
================
RSS 피드를 통한 축구 뉴스 수집 모듈

지원 소스 (국내):
  - 스포츠조선, MBC스포츠, OSEN, 네이버스포츠, 풋볼리스트

지원 소스 (해외):
  - BBC Sport Football, ESPN Soccer, The Guardian Football
  - Goal.com, Sky Sports Football, UEFA, 90min

사용법:
    from collectors.rss_collector import RSSCollector

    collector = RSSCollector()
    articles = collector.collect_all()
    for article in articles:
        print(article['title'], article['source'], article['image_url'])
"""

import feedparser
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from email.utils import parsedate_to_datetime

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================
# RSS 피드 소스 목록
# =============================================
RSS_SOURCES = [
    # ── 국내 ───────────────────────────────────────────────────
    {
        "name": "스포츠조선",
        "url": "https://sports.chosun.com/rss/football.xml",
        "language": "ko",
        "category": "korean_media",
    },
    {
        "name": "MBC스포츠",
        "url": "https://imnews.imbc.com/rss/sports/index.xml",
        "language": "ko",
        "category": "korean_media",
    },
    {
        "name": "OSEN",
        "url": "https://osen.mt.co.kr/rss/sport.xml",
        "language": "ko",
        "category": "korean_media",
    },
    {
        "name": "스포츠서울",
        "url": "https://www.sportsseoul.com/rss/allArticle.xml",
        "language": "ko",
        "category": "korean_media",
    },
    {
        "name": "풋볼리스트",
        "url": "https://www.footballist.co.kr/rss/allArticle.xml",
        "language": "ko",
        "category": "korean_media",
    },
    # ── 해외 ───────────────────────────────────────────────────
    {
        "name": "BBC Sport Football",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "language": "en",
        "category": "international_media",
    },
    {
        "name": "ESPN Soccer",
        "url": "https://www.espn.com/espn/rss/soccer/news",
        "language": "en",
        "category": "international_media",
    },
    {
        "name": "The Guardian Football",
        "url": "https://www.theguardian.com/football/rss",
        "language": "en",
        "category": "international_media",
    },
    {
        "name": "Goal.com",
        "url": "https://www.goal.com/feeds/en/news",
        "language": "en",
        "category": "international_media",
    },
    {
        "name": "Sky Sports Football",
        "url": "https://www.skysports.com/rss/12040",
        "language": "en",
        "category": "international_media",
    },
    {
        "name": "90min",
        "url": "https://www.90min.com/feed",
        "language": "en",
        "category": "international_media",
    },
    {
        "name": "UEFA News",
        "url": "https://www.uefa.com/rssfeed/rss-news-en.xml",
        "language": "en",
        "category": "official",
    },
]

# ── 2026 FIFA 월드컵 전용 RSS ────────────────────────────────
WC_RSS_SOURCES = [
    # 국내 — 기존 피드에서 WC 뉴스도 커버되지만 명시적 WC 피드 추가
    {
        "name": "스포츠조선 (WC)",
        "url": "https://sports.chosun.com/rss/football.xml",
        "language": "ko",
        "category": "worldcup",
    },
    {
        "name": "OSEN (WC)",
        "url": "https://osen.mt.co.kr/rss/sport.xml",
        "language": "ko",
        "category": "worldcup",
    },
    {
        "name": "풋볼리스트 (WC)",
        "url": "https://www.footballist.co.kr/rss/allArticle.xml",
        "language": "ko",
        "category": "worldcup",
    },
    # 해외 — WC 특화 또는 종합 축구 피드
    {
        "name": "BBC Sport WC",
        "url": "https://feeds.bbci.co.uk/sport/football/world-cup/rss.xml",
        "language": "en",
        "category": "worldcup",
    },
    {
        "name": "The Guardian WC",
        "url": "https://www.theguardian.com/football/world-cup-2026/rss",
        "language": "en",
        "category": "worldcup",
    },
    {
        "name": "ESPN Soccer (WC)",
        "url": "https://www.espn.com/espn/rss/soccer/news",
        "language": "en",
        "category": "worldcup",
    },
    {
        "name": "Sky Sports WC",
        "url": "https://www.skysports.com/rss/12040",
        "language": "en",
        "category": "worldcup",
    },
    {
        "name": "Goal.com (WC)",
        "url": "https://www.goal.com/feeds/en/news",
        "language": "en",
        "category": "worldcup",
    },
    {
        "name": "90min (WC)",
        "url": "https://www.90min.com/feed",
        "language": "en",
        "category": "worldcup",
    },
]


def _parse_published_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """
    feedparser entry에서 발행일시를 파싱해 timezone-aware datetime으로 반환합니다.
    파싱 실패 시 현재 UTC 시각을 반환합니다.
    """
    # feedparser가 time_struct로 파싱한 경우
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    # 원본 문자열로 파싱 시도 (RFC 2822 형식: "Tue, 23 Jun 2026 10:00:00 +0900")
    if hasattr(entry, "published") and entry.published:
        try:
            return parsedate_to_datetime(entry.published)
        except Exception:
            pass

    # 파싱 실패 시 현재 시각
    return datetime.now(timezone.utc)


def _generate_article_id(url: str, title: str) -> str:
    """
    URL + 제목을 기반으로 고유 기사 ID(SHA256 앞 16자리)를 생성합니다.
    동일 기사가 여러 소스에서 수집될 때 중복 감지에 활용됩니다.
    """
    content = f"{url}|{title}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _extract_image(entry) -> str:
    """
    RSS entry에서 이미지 URL을 추출합니다.
    우선순위: media:thumbnail → media:content → enclosure → summary img 태그

    Parameters
    ----------
    entry : feedparser.FeedParserDict
        RSS 피드의 개별 항목

    Returns
    -------
    str
        이미지 URL 문자열. 찾지 못하면 빈 문자열.
    """
    # 1. media:thumbnail (BBC, Guardian 등)
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url", "")
        if url:
            return url

    # 2. media:content (ESPN 등)
    if hasattr(entry, "media_content") and entry.media_content:
        for mc in entry.media_content:
            if mc.get("type", "").startswith("image") or mc.get("url", ""):
                url = mc.get("url", "")
                if url:
                    return url

    # 3. enclosure (팟캐스트 스타일 피드)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                url = enc.get("href", enc.get("url", ""))
                if url:
                    return url

    # 4. summary/content 내 첫 번째 <img src="...">
    raw = ""
    if hasattr(entry, "summary"):
        raw = entry.summary
    elif hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    if raw:
        import re
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
        if match:
            return match.group(1)

    return ""


def _clean_html(raw: str) -> str:
    """
    HTML 태그를 제거하고 순수 텍스트만 반환합니다.
    BeautifulSoup이 없어도 동작하는 단순 버전입니다.
    """
    if not raw:
        return ""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(raw, "lxml").get_text(separator=" ", strip=True)
    except ImportError:
        import re
        return re.sub(r"<[^>]+>", "", raw).strip()


def fetch_rss_source(source: dict) -> list[dict]:
    """
    단일 RSS 소스에서 기사를 수집합니다.

    Parameters
    ----------
    source : dict
        RSS_SOURCES 목록의 항목 하나 (name, url, language, category 포함)

    Returns
    -------
    list[dict]
        수집된 기사 딕셔너리 목록. 각 항목은 아래 키를 가집니다:
        - article_id  : SHA256 기반 고유 ID
        - title       : 기사 제목
        - url         : 기사 원문 URL
        - summary     : 요약 / 본문 일부
        - published_at: 발행일시 (datetime, UTC)
        - source_name : 소스 이름 (예: "BBC Sport Football")
        - language    : 언어 코드 (예: "ko", "en")
        - category    : 소스 분류 (예: "international_media")
        - collected_at: 수집 시각 (datetime, UTC)
    """
    articles = []
    logger.info(f"[{source['name']}] RSS 수집 시작: {source['url']}")

    try:
        # feedparser로 RSS 파싱 (timeout 미지원 → requests로 직접 가져온 후 파싱)
        import requests
        response = requests.get(source["url"], timeout=10, headers={
            "User-Agent": "FootballLensBot/1.0 (educational project)"
        })
        response.raise_for_status()
        feed = feedparser.parse(response.content)

    except Exception as e:
        logger.error(f"[{source['name']}] 수집 실패: {e}")
        return []

    for entry in feed.entries:
        try:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()

            if not title or not url:
                continue  # 제목/URL 없으면 스킵

            # 요약 텍스트 추출 (summary → content → 빈 문자열)
            raw_summary = ""
            if hasattr(entry, "summary"):
                raw_summary = entry.summary
            elif hasattr(entry, "content") and entry.content:
                raw_summary = entry.content[0].get("value", "")
            summary = _clean_html(raw_summary)[:1000]  # 최대 1000자

            article = {
                "article_id": _generate_article_id(url, title),
                "title": title,
                "url": url,
                "summary": summary,
                "image_url": _extract_image(entry),
                "published_at": _parse_published_date(entry),
                "source_name": source["name"],
                "language": source["language"],
                "category": source["category"],
                "collected_at": datetime.now(timezone.utc),
            }
            articles.append(article)

        except Exception as e:
            logger.warning(f"[{source['name']}] 기사 파싱 오류: {e}")
            continue

    logger.info(f"[{source['name']}] 수집 완료: {len(articles)}건")
    return articles


class RSSCollector:
    """
    여러 RSS 소스를 병렬로 수집하는 메인 수집기 클래스.

    예시:
        collector = RSSCollector()

        # 전체 소스 수집 (병렬)
        all_articles = collector.collect_all()

        # 특정 소스만 수집 (이름 필터)
        kor_articles = collector.collect_by_language("ko")
    """

    def __init__(self, sources: list[dict] = None, max_workers: int = 6):
        """
        Parameters
        ----------
        sources : list[dict], optional
            커스텀 소스 목록. 기본값은 RSS_SOURCES 전체.
        max_workers : int
            병렬 수집 스레드 수 (기본 6)
        """
        self.sources = sources or RSS_SOURCES
        self.max_workers = max_workers

    def collect_all(self) -> list[dict]:
        """
        모든 RSS 소스에서 기사를 병렬로 수집하고 합친 결과를 반환합니다.

        ThreadPoolExecutor를 사용해 소스를 동시에 요청하므로
        순차 수집 대비 속도가 크게 향상됩니다.

        Returns
        -------
        list[dict]
            전체 소스 기사 목록. 개별 소스 오류 발생 시 해당 소스를 건너뛰고 계속 진행합니다.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        all_articles = []

        def _safe_fetch(source):
            try:
                return fetch_rss_source(source)
            except Exception as e:
                logger.error(f"[collect_all] '{source['name']}' 수집 중 예외: {e}")
                return []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_safe_fetch, src): src for src in self.sources}
            for future in as_completed(futures):
                articles = future.result()
                all_articles.extend(articles)

        logger.info(f"전체 수집 완료: 총 {len(all_articles)}건")
        return all_articles

    def collect_by_language(self, lang: str) -> list[dict]:
        """
        특정 언어 소스만 수집합니다.

        Parameters
        ----------
        lang : str
            언어 코드 ("ko" 또는 "en")

        Returns
        -------
        list[dict]
            해당 언어 기사 목록. 오류 발생 소스는 건너뜁니다.
        """
        try:
            filtered_sources = [s for s in self.sources if s["language"] == lang]
            if not filtered_sources:
                logger.warning(f"[collect_by_language] 언어 '{lang}'에 해당하는 소스 없음")
                return []
            for source in filtered_sources:
                try:
                    articles = fetch_rss_source(source)
                    all_articles.extend(articles)
                except Exception as e:
                    logger.warning(f"[collect_by_language] '{source['name']}' 오류: {e}")
            logger.info(f"[collect_by_language] 언어='{lang}' 수집 완료: {len(all_articles)}건")
            return all_articles
        except Exception as e:
            logger.error(f"[collect_by_language] 예외 발생: {e}")
            return []

    def collect_by_name(self, name: str) -> list[dict]:
        """
        특정 소스 이름으로 수집합니다.

        Parameters
        ----------
        name : str
            소스 이름 (예: "BBC Sport Football")

        Returns
        -------
        list[dict]
            해당 소스 기사 목록. 소스를 찾지 못하거나 오류 발생 시 빈 리스트 반환.
        """
        try:
            for source in self.sources:
                if source["name"] == name:
                    return fetch_rss_source(source)
            logger.warning(f"[collect_by_name] 소스를 찾을 수 없습니다: {name}")
            return []
        except Exception as e:
            logger.error(f"[collect_by_name] '{name}' 수집 중 예외: {e}")
            return []

    def collect_worldcup_news(self) -> list[dict]:
        """
        2026 FIFA 월드컵 뉴스를 수집합니다.

        전략:
            1) WC_RSS_SOURCES (WC 특화 피드) 병렬 수집
            2) 결과가 10건 미만이면 RSS_SOURCES (일반 피드)에서 추가 수집 후 WC 키워드 필터링

        Returns
        -------
        list[dict]
            월드컵 관련 기사 목록
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

        WC_FILTER = [
            "월드컵", "world cup", "worldcup", "wc 2026", "2026 wc",
            "fifa 2026", "mondial", "world cup 2026", "월드컵 2026",
            "북중미 월드컵", "2026 fifa", "태극전사",
        ]

        def _safe_fetch(source):
            try:
                return fetch_rss_source(source)
            except Exception as e:
                logger.warning(f"[WC RSS] '{source['name']}' 수집 실패: {e}")
                return []

        def _wc_filter(articles: list[dict]) -> list[dict]:
            result = []
            for a in articles:
                text = ((a.get("title") or "") + " " + (a.get("summary") or "")).lower()
                if a.get("category") == "worldcup" or any(kw in text for kw in WC_FILTER):
                    a["category"] = "worldcup"
                    result.append(a)
            return result

        # 1단계: WC 전용 피드 수집
        all_articles: list[dict] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_safe_fetch, src): src for src in WC_RSS_SOURCES}
            for future in _as_completed(futures):
                all_articles.extend(future.result())

        filtered = _wc_filter(all_articles)
        logger.info(f"[WC RSS] WC 전용 피드 수집: {len(filtered)}건 (전체 {len(all_articles)}건)")


        # 2단계: 폴백 — 일반 RSS_SOURCES에서도 WC 키워드 매칭 기사 추가 수집
        if len(filtered) < 10:
            logger.info("[WC RSS] 수집량 부족 → 일반 RSS 피드에서 WC 키워드 필터링 병행")
            seen_urls = {a.get("url", "") for a in filtered}
            general_articles: list[dict] = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures2 = {executor.submit(_safe_fetch, src): src for src in RSS_SOURCES}
                for future in _as_completed(futures2):
                    general_articles.extend(future.result())

            for a in _wc_filter(general_articles):
                url = a.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    filtered.append(a)

        logger.info(f"[WC RSS] 최종 월드컵 뉴스: {len(filtered)}건")
        return filtered


# =============================================
# 직접 실행 시 테스트
# =============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = RSSCollector()
    articles = collector.collect_all()
    print(f"\n총 수집 기사 수: {len(articles)}건")
    for a in articles[:3]:
        print(f"  [{a.get('language','?')}] {a.get('title','(제목없음)')[:60]}")
