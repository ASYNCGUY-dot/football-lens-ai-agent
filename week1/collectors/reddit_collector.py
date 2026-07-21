# -*- coding: utf-8 -*-
"""
reddit_collector.py
===================
Reddit RSS 피드를 이용한 축구 커뮤니티 인기 포스트 수집 모듈

API 키 불필요 — Reddit의 공개 RSS 피드를 사용합니다.
주요 서브레딧:
    r/soccer          : 전 세계 축구 뉴스/토론
    r/PremierLeague   : EPL 특화 토론
    r/Ksoccer         : 한국 축구 (손흥민 등)
    r/reddevils       : 맨유
    r/LiverpoolFC     : 리버풀

RSS URL 형식:
    https://www.reddit.com/r/{subreddit}/.rss?limit=25

사용법:
    from collectors.reddit_collector import RedditCollector

    collector = RedditCollector()
    posts = collector.collect_all()
"""

import logging
import re
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)


# 수집 대상 서브레딧
FOOTBALL_SUBREDDITS = [
    "soccer",
    "PremierLeague",
    "Ksoccer",
    "footballhighlights",
    "reddevils",
    "LiverpoolFC",
]


class RedditCollector:
    """
    Reddit RSS 기반 축구 커뮤니티 포스트 수집기 (API 키 불필요)

    RSS 피드는 공개 데이터이므로 별도 인증 없이 수집 가능합니다.
    단, Reddit은 User-Agent 헤더를 요구합니다.

    주요 메서드:
        collect_subreddit(subreddit) : 서브레딧 RSS 수집
        collect_all()                : 전체 서브레딧 수집 + 중복 제거
    """

    HEADERS = {
        "User-Agent": "FootballLens/1.0 (educational project; contact: user@example.com)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }

    def __init__(self, subreddits: list[str] = None, max_per_sub: int = 10):
        """
        Parameters
        ----------
        subreddits : list[str], optional
            수집할 서브레딧 목록. 기본값: FOOTBALL_SUBREDDITS
        max_per_sub : int
            서브레딧당 최대 포스트 수 (기본 10)
        """
        self.subreddits = subreddits or FOOTBALL_SUBREDDITS
        self.max_per_sub = max_per_sub

    def collect_subreddit(self, subreddit: str) -> list[dict]:
        """
        Reddit 서브레딧의 RSS 피드를 수집합니다.

        Parameters
        ----------
        subreddit : str
            서브레딧 이름 (예: "soccer", "PremierLeague")

        Returns
        -------
        list[dict]
            포스트 메타데이터 목록. 각 항목:
            - post_id    : Reddit 포스트 고유 ID
            - title      : 포스트 제목
            - url        : 포스트 URL (reddit.com)
            - link_url   : 포스트에 링크된 외부 URL (있는 경우)
            - author     : 작성자
            - published_at: 게시일 (datetime, timezone-aware)
            - subreddit  : 서브레딧 이름
            - thumbnail  : 썸네일 URL (있는 경우)
            - source     : "reddit"
            - language   : "en"
            - category   : "reddit"
        """
        rss_url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit={self.max_per_sub}"
        logger.info(f"[Reddit] r/{subreddit} RSS 수집 시작")

        try:
            resp = requests.get(rss_url, headers=self.HEADERS, timeout=15)
            if resp.status_code == 429:
                logger.warning(f"[Reddit] r/{subreddit} rate limit → 건너뜀")
                return []
            resp.raise_for_status()
            return self._parse_rss(resp.text, subreddit)

        except requests.exceptions.RequestException as e:
            logger.error(f"[Reddit] r/{subreddit} 요청 오류: {e}")
            return []

    def _parse_rss(self, xml_text: str, subreddit: str) -> list[dict]:
        """RSS XML을 파싱하여 포스트 목록을 반환합니다."""
        posts = []
        try:
            import xml.etree.ElementTree as ET
            # Reddit RSS는 Atom 형식
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "media": "http://search.yahoo.com/mrss/",
            }
            root = ET.fromstring(xml_text)

            # Atom <entry> 태그 처리
            entries = root.findall("atom:entry", ns)
            if not entries:
                # RSS 2.0 형식 폴백
                entries = root.findall(".//item")

            for entry in entries:
                try:
                    post = self._parse_entry(entry, ns, subreddit)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.debug(f"[Reddit] 포스트 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"[Reddit] XML 파싱 오류: {e}")

        logger.info(f"[Reddit] r/{subreddit} 수집: {len(posts)}건")
        return posts

    def _parse_entry(self, entry, ns: dict, subreddit: str) -> dict | None:
        """Atom entry 또는 RSS item 하나를 파싱합니다."""
        def get_text(tag, default=""):
            elem = entry.find(tag, ns) or entry.find(tag)
            return (elem.text or default).strip() if elem is not None else default

        title = html.unescape(get_text("atom:title") or get_text("title"))
        url   = ""
        link_elem = entry.find("atom:link", ns) or entry.find("link")
        if link_elem is not None:
            url = link_elem.get("href", "") or link_elem.text or ""

        if not title or not url:
            return None

        # Reddit 포스트 ID 추출 (/t3_XXXXX/)
        post_id_match = re.search(r"/t3_([a-z0-9]+)", url)
        post_id = post_id_match.group(1) if post_id_match else url[-16:]

        # 작성자
        author = get_text("atom:author/atom:name") or get_text("author")
        author = author.replace("/u/", "").strip()

        # 날짜
        pub_str = get_text("atom:published") or get_text("atom:updated") or get_text("pubDate")
        try:
            if "T" in pub_str:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            else:
                pub_dt = parsedate_to_datetime(pub_str)
        except Exception:
            pub_dt = datetime.now(timezone.utc)

        # 내용에서 외부 링크 추출
        content = get_text("atom:content") or get_text("description")
        link_url = self._extract_external_link(content, url)

        # 썸네일
        thumbnail = ""
        media_thumb = entry.find("media:thumbnail", ns)
        if media_thumb is not None:
            thumbnail = media_thumb.get("url", "")

        return {
            "post_id": post_id,
            "title": title,
            "url": url,
            "link_url": link_url,
            "author": author,
            "published_at": pub_dt,
            "subreddit": subreddit,
            "thumbnail": thumbnail,
            "source": "reddit",
            "source_name": f"r/{subreddit}",
            "language": "en",
            "category": "reddit",
            "collected_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def _extract_external_link(content: str, reddit_url: str) -> str:
        """포스트 내용에서 외부 링크를 추출합니다."""
        if not content:
            return reddit_url
        # href= 속성에서 URL 추출
        matches = re.findall(r'href=["\']([^"\']+)["\']', content)
        for m in matches:
            if "reddit.com" not in m and m.startswith("http"):
                return m
        return reddit_url

    def collect_all(self) -> list[dict]:
        """
        전체 서브레딧을 수집하고 URL 기반 중복을 제거합니다.

        Returns
        -------
        list[dict]
            중복 제거된 포스트 목록 (최신순)
        """
        all_posts = []
        seen_ids = set()

        for sub in self.subreddits:
            posts = self.collect_subreddit(sub)
            for p in posts:
                if p["post_id"] not in seen_ids:
                    seen_ids.add(p["post_id"])
                    all_posts.append(p)

        # 최신순 정렬
        all_posts.sort(key=lambda p: str(p.get("published_at", "")), reverse=True)
        logger.info(f"[Reddit] 전체 수집 완료: {len(all_posts)}건 (서브레딧 {len(self.subreddits)}개)")
        return all_posts


# =============================================
# 직접 실행 시 테스트
# =============================================
if __name__ == "__main__":
    collector = RedditCollector(max_per_sub=5)
    posts = collector.collect_all()
    print(f"\n총 수집 포스트: {len(posts)}건\n")
    for p in posts[:5]:
        print(f"[r/{p['subreddit']}] {p['title'][:70]}")
        print(f"  URL: {p['url']}")
        print(f"  날짜: {p['published_at']}")
        print()
