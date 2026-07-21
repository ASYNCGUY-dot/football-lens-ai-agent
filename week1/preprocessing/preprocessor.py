# -*- coding: utf-8 -*-
"""
preprocessor.py
===============
수집된 기사 데이터 전처리 모듈

기능:
    1. 중복 제거 - URL 기반 정확 중복, Simhash 기반 유사 중복
    2. 언어 감지 - langdetect 라이브러리 활용
    3. 광고/스팸 필터링 - 키워드 + 규칙 기반

사용법:
    from preprocessing.preprocessor import ArticlePreprocessor

    preprocessor = ArticlePreprocessor()
    raw_articles = [...]  # 수집된 기사 목록

    clean_articles = preprocessor.run(raw_articles)
"""

import re
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================
# 광고/스팸 필터링 키워드 (한국어 + 영어)
# =============================================
AD_KEYWORDS_KO = [
    "광고", "협찬", "홍보", "이벤트 참여", "클릭하세요",
    "구독하기", "팔로우", "할인 쿠폰", "무료 체험",
    "지금 신청", "바로 구매", "한정 수량", "특가",
    "PR ", "[PR]", "[광고]", "[협찬]",
]

AD_KEYWORDS_EN = [
    "sponsored", "advertisement", "promo", "affiliate",
    "click here", "subscribe now", "buy now", "limited offer",
    "free trial", "discount code", "coupon", "[ad]", "[sponsored]",
    "terms and conditions apply",
]

# 최소 기사 길이 (너무 짧은 텍스트는 광고/단신으로 처리)
MIN_TITLE_LENGTH = 5        # 제목 최소 5자
MIN_SUMMARY_LENGTH = 10     # 요약 최소 10자

# =============================================
# 축구 관련성 필터링 키워드
# =============================================
# 아래 키워드 중 하나라도 제목·요약에 포함되면 축구 기사로 간주합니다.
FOOTBALL_KEYWORDS_KO = [
    # 종목 명칭 (단독으로도 강력한 신호)
    "축구", "풋볼",
    # 리그 (오해 없는 고유명사)
    "EPL", "프리미어리그", "라리가", "분데스리가", "세리에A", "세리에 A",
    "리그앙", "챔피언스리그", "UCL", "유로파리그", "UEL", "K리그", "K-리그",
    "FA컵", "카라바오컵", "수페르코파", "코파델레이", "월드컵", "유로",
    # 구단 (고유명사 — 오해 없음)
    "맨체스터", "리버풀", "아스날", "첼시", "토트넘", "맨유", "맨시티",
    "레알마드리드", "바르셀로나", "아틀레티코", "바이에른", "도르트문트",
    "PSG", "유벤투스", "인테르", "AC밀란", "나폴리", "포르투", "벤피카",
    "전북현대", "울산HD", "FC서울", "포항스틸러스",
    # 포지션 (명확한 축구 전용어)
    "골키퍼", "공격수", "미드필더", "수비수", "스트라이커", "윙어",
    # 경기 전용어
    "어시스트", "해트트릭", "페널티킥", "VAR", "오프사이드",
    "이적료", "이적시장", "임대이적",
    # 선수 이름 (한국)
    "손흥민", "이강인", "황희찬", "김민재", "조규성", "오현규", "황인범",
    # 선수 이름 (해외)
    "홀란드", "살라", "엠바페", "벨링엄", "야말", "케인", "비니시우스",
    "호날두", "메시", "네이마르",
]

# ※ 제거한 모호한 키워드:
#   "부상" → "부상하다(rise/emerge)"와 중복 → HD현대일렉트릭 오탐 원인
#   "골"   → "골든타임", "골프" 등 오탐 가능
#   "감독" → 영화 감독 등 오탐 가능
#   "계약" → 일반 비즈니스 계약 오탐
#   "교체", "출전", "선발", "임대", "방출", "영입" → 단독 사용 시 오탐 위험

FOOTBALL_KEYWORDS_EN = [
    "football", "soccer", "premier league", "la liga", "bundesliga",
    "serie a", "ligue 1", "champions league", "europa league", "world cup",
    "arsenal", "chelsea", "liverpool", "manchester", "tottenham",
    "real madrid", "barcelona", "bayern", "juventus", "inter milan",
    "haaland", "salah", "mbappe", "bellingham", "yamal", "kane",
    "midfielder", "defender", "striker", "goalkeeper",
    "hat-trick", "offside", "var", "transfer fee",
    "epl", "ucl", "uel", "fifa",
]


def is_football_related(title: str, summary: str = "", language: str = "ko") -> bool:
    """
    기사가 축구 관련 내용인지 확인합니다.

    제목에서 키워드를 우선 확인하고, 없으면 요약에서도 확인합니다.
    모호한 단어(부상, 감독 등)는 키워드 목록에서 제외해 오탐을 방지합니다.

    Parameters
    ----------
    title : str
        기사 제목
    summary : str
        기사 요약
    language : str
        언어 코드 ("ko", "en", "unknown")

    Returns
    -------
    bool
        True이면 축구 관련 기사
    """
    # 제목을 대소문자 무시해서 확인 (요약보다 신뢰도 높음)
    title_lower = title.lower()
    summary_lower = summary.lower()

    if language == "en":
        keywords = FOOTBALL_KEYWORDS_EN
    elif language == "ko":
        keywords = FOOTBALL_KEYWORDS_KO
    else:
        keywords = FOOTBALL_KEYWORDS_KO + FOOTBALL_KEYWORDS_EN

    for kw in keywords:
        kw_lower = kw.lower()
        # 제목에서 먼저 확인 (신뢰도 높음)
        if kw_lower in title_lower:
            return True

    # 한국어 기사: 제목에서만 판별 (요약은 Naver가 무관한 내용 포함 가능)
    if language == "ko":
        return False

    # 영어/기타 기사: 요약에서도 확인
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in summary_lower:
            return True
    return False

# 너무 오래된 기사 필터링 (기본 30일)
MAX_AGE_DAYS = 30

# Simhash 유사도 임계값 (비트 차이가 이 값 이하이면 중복 간주)
SIMHASH_THRESHOLD = 3


# =============================================
# 유틸리티 함수
# =============================================

def detect_language(text: str) -> str:
    """
    텍스트의 언어를 감지합니다.

    langdetect가 설치된 경우 사용하고,
    없으면 한글 문자 비율로 간단히 판별합니다.

    Parameters
    ----------
    text : str
        언어를 감지할 텍스트

    Returns
    -------
    str
        언어 코드 (예: "ko", "en", "unknown")
    """
    if not text or len(text.strip()) < 10:
        return "unknown"

    try:
        from langdetect import detect, LangDetectException
        return detect(text)
    except ImportError:
        pass
    except Exception:
        pass

    # 폴백: 한글 문자 비율로 판별
    korean_chars = len(re.findall(r"[가-힣]", text))
    ratio = korean_chars / max(len(text), 1)
    if ratio > 0.2:
        return "ko"
    elif ratio < 0.05:
        return "en"
    return "unknown"


def compute_text_hash(text: str) -> str:
    """
    텍스트의 SHA256 해시를 계산합니다. (정확한 중복 감지용)

    Parameters
    ----------
    text : str
        해시를 계산할 텍스트

    Returns
    -------
    str
        SHA256 해시 앞 32자리. 오류 발생 시 빈 문자열 반환.
    """
    try:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    except (TypeError, ValueError) as e:
        logger.error(f"[compute_text_hash] 해시 계산 오류: {e}")
        return ""


def compute_simhash(text: str, num_bits: int = 64) -> int:
    """
    텍스트의 Simhash 값을 계산합니다. (유사 중복 감지용)

    Simhash는 텍스트가 조금 다르더라도 유사도를 비교할 수 있는
    지문(fingerprint) 방식입니다.

    Parameters
    ----------
    text : str
        Simhash를 계산할 텍스트
    num_bits : int
        비트 수 (기본 64)

    Returns
    -------
    int
        Simhash 값 (정수)
    """
    try:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return 0

        bit_vector = [0] * num_bits
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            for i in range(num_bits):
                bit = (token_hash >> i) & 1
                bit_vector[i] += 1 if bit else -1

        simhash = 0
        for i in range(num_bits):
            if bit_vector[i] > 0:
                simhash |= (1 << i)

        return simhash
    except (TypeError, ValueError) as e:
        logger.error(f"[compute_simhash] 계산 오류: {e}")
        return 0


def hamming_distance(hash1: int, hash2: int) -> int:
    """
    두 Simhash 값 사이의 해밍 거리(다른 비트 수)를 계산합니다.

    해밍 거리가 작을수록 두 텍스트가 유사합니다.
    SIMHASH_THRESHOLD(3) 이하이면 중복으로 간주합니다.

    Parameters
    ----------
    hash1, hash2 : int
        비교할 두 Simhash 값

    Returns
    -------
    int
        다른 비트의 수
    """
    try:
        xor = hash1 ^ hash2
        return bin(xor).count("1")
    except TypeError as e:
        logger.error(f"[hamming_distance] 타입 오류: {e}")
        return 64  # 최대 거리 반환 → 중복 아님으로 처리


def is_ad_content(title: str, summary: str = "", language: str = "ko") -> bool:
    """
    광고/스팸 여부를 판별합니다.

    판별 기준:
    - 광고 키워드 포함 여부
    - 제목/요약 최소 길이 미달
    - URL만 있는 요약 (내용 없음)

    Parameters
    ----------
    title : str
        기사 제목
    summary : str
        기사 요약
    language : str
        언어 코드 ("ko" 또는 "en")

    Returns
    -------
    bool
        True이면 광고/스팸으로 판별됨
    """
    try:
        full_text = f"{title} {summary}".lower()

        ad_keywords = AD_KEYWORDS_KO if language == "ko" else AD_KEYWORDS_EN
        for keyword in ad_keywords:
            if keyword.lower() in full_text:
                logger.debug(f"광고 키워드 감지: '{keyword}' in '{title[:50]}'")
                return True

        if len(title.strip()) < MIN_TITLE_LENGTH:
            return True

        url_pattern = r"^https?://\S+$"
        if summary and re.match(url_pattern, summary.strip()):
            return True

        return False
    except (TypeError, AttributeError) as e:
        logger.error(f"[is_ad_content] 광고 판별 오류: {e}")
        return False  # 오류 시 광고 아님으로 처리 (기사 보존 우선)


def is_too_old(published_at, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """
    기사가 너무 오래됐는지 확인합니다.

    Parameters
    ----------
    published_at : datetime or str
        기사 발행일시
    max_age_days : int
        최대 허용 일수 (기본 30일)

    Returns
    -------
    bool
        True이면 너무 오래된 기사
    """
    if published_at is None:
        return False

    now = datetime.now(timezone.utc)

    # 문자열이면 datetime으로 변환
    if isinstance(published_at, str):
        try:
            from dateutil.parser import parse
            published_at = parse(published_at)
        except Exception:
            return False

    # timezone이 없는 경우 UTC로 간주
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age = now - published_at
    return age > timedelta(days=max_age_days)


# =============================================
# 전처리 파이프라인 클래스
# =============================================

class ArticlePreprocessor:
    """
    기사 전처리 파이프라인

    처리 순서:
        1. 필수 필드 검증 (title, url)
        2. 오래된 기사 필터링
        3. 광고/스팸 필터링
        4. 언어 감지 및 검증
        5. URL 기반 정확한 중복 제거
        6. Simhash 기반 유사 중복 제거

    예시:
        preprocessor = ArticlePreprocessor(
            allowed_languages=["ko", "en"],
            max_age_days=14,
            use_simhash=True,
        )
        clean = preprocessor.run(raw_articles)
        print(f"정제 후: {len(clean)}건")
    """

    def __init__(
        self,
        allowed_languages: list[str] = None,
        max_age_days: int = MAX_AGE_DAYS,
        use_simhash: bool = True,
        simhash_threshold: int = SIMHASH_THRESHOLD,
    ):
        """
        Parameters
        ----------
        allowed_languages : list[str], optional
            허용할 언어 목록. 기본값: ["ko", "en", "unknown"]
        max_age_days : int
            기사 최대 허용 일수 (기본 30일)
        use_simhash : bool
            Simhash 기반 유사 중복 제거 활성화 여부
        simhash_threshold : int
            유사 중복 판별 해밍 거리 임계값 (기본 3)
        """
        self.allowed_languages = allowed_languages or ["ko", "en", "unknown"]
        self.max_age_days = max_age_days
        self.use_simhash = use_simhash
        self.simhash_threshold = simhash_threshold

        # 통계 추적
        self.stats = {
            "total": 0,
            "missing_fields": 0,
            "too_old": 0,
            "ad_filtered": 0,
            "not_football": 0,
            "language_filtered": 0,
            "url_duplicate": 0,
            "simhash_duplicate": 0,
            "passed": 0,
        }

    def _reset_stats(self):
        """통계 카운터를 모두 0으로 초기화합니다. run() 호출 시 자동 실행됩니다."""
        for key in self.stats:
            self.stats[key] = 0

    def run(self, articles: list[dict]) -> list[dict]:
        """
        전처리 파이프라인을 실행합니다.

        Parameters
        ----------
        articles : list[dict]
            수집된 기사 딕셔너리 목록

        Returns
        -------
        list[dict]
            전처리 완료된 기사 목록 (각 기사에 processed_at, detected_language 필드 추가).
            예외 발생 시 빈 리스트 반환.
        """
        try:
            self._reset_stats()
            self.stats["total"] = len(articles)
            logger.info(f"전처리 시작: 총 {len(articles)}건")

            clean_articles = []
            seen_urls = set()
            seen_simhashes = []

            for article in articles:
                try:
                    # ── 1. 필수 필드 검증 ──────────────────────────────────
                    title = article.get("title", "").strip()
                    url = article.get("url", "").strip()

                    if not title or not url:
                        self.stats["missing_fields"] += 1
                        continue

                    # ── 2. 오래된 기사 필터링 ───────────────────────────────
                    if is_too_old(article.get("published_at"), self.max_age_days):
                        self.stats["too_old"] += 1
                        logger.debug(f"오래된 기사 필터링: {title[:50]}")
                        continue

                    # ── 3. 광고/스팸 필터링 ────────────────────────────────
                    lang_hint = article.get("language", "ko")
                    summary = article.get("summary", "")
                    if is_ad_content(title, summary, lang_hint):
                        self.stats["ad_filtered"] += 1
                        logger.debug(f"광고 필터링: {title[:50]}")
                        continue

                    # ── 3-1. 축구 관련성 필터링 ────────────────────────────
                    if not is_football_related(title, summary, lang_hint):
                        self.stats["not_football"] += 1
                        logger.debug(f"비축구 기사 제거: {title[:50]}")
                        continue

                    # ── 4. 언어 감지 ───────────────────────────────────────
                    detected_lang = detect_language(f"{title} {summary}")
                    final_lang = article.get("language") or detected_lang

                    if final_lang not in self.allowed_languages:
                        self.stats["language_filtered"] += 1
                        logger.debug(f"언어 필터링 ({final_lang}): {title[:50]}")
                        continue

                    # ── 5. URL 기반 정확한 중복 제거 ─────────────────────
                    normalized_url = url.rstrip("/").lower().split("?")[0]
                    if normalized_url in seen_urls:
                        self.stats["url_duplicate"] += 1
                        continue
                    seen_urls.add(normalized_url)

                    # ── 6. Simhash 기반 유사 중복 제거 ───────────────────
                    if self.use_simhash:
                        try:
                            title_hash = compute_simhash(title)
                            is_similar = any(
                                hamming_distance(title_hash, h) <= self.simhash_threshold
                                for h in seen_simhashes
                            )
                            if is_similar:
                                self.stats["simhash_duplicate"] += 1
                                logger.debug(f"유사 중복 제거: {title[:50]}")
                                continue
                            seen_simhashes.append(title_hash)
                        except Exception as e:
                            logger.warning(f"Simhash 계산 오류 (건너뜀): {e}")

                    # ── 통과 ─────────────────────────────────────────────
                    processed_article = {
                        **article,
                        "detected_language": detected_lang,
                        "language": final_lang,
                        "processed_at": datetime.now(timezone.utc),
                    }
                    clean_articles.append(processed_article)

                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"기사 전처리 중 파싱 오류 (건너뜀): {e}")
                    continue

            self.stats["passed"] = len(clean_articles)
            self._log_stats()
            return clean_articles

        except Exception as e:
            logger.error(f"[run] 전처리 파이프라인 예외 발생: {e}")
            return []

    def _log_stats(self):
        """전처리 통계를 로그로 출력합니다."""
        s = self.stats
        logger.info(
            f"전처리 완료 | "
            f"입력: {s['total']}건 → 출력: {s['passed']}건 | "
            f"필드누락: {s['missing_fields']}, "
            f"오래됨: {s['too_old']}, "
            f"광고: {s['ad_filtered']}, "
            f"비축구: {s['not_football']}, "
            f"언어: {s['language_filtered']}, "
            f"URL중복: {s['url_duplicate']}, "
            f"유사중복: {s['simhash_duplicate']}"
        )

    def get_stats(self) -> dict:
        """
        마지막 run() 실행의 전처리 통계를 반환합니다.

        Returns
        -------
        dict
            통계 딕셔너리 복사본. 키: total, passed, missing_fields,
            too_old, ad_filtered, language_filtered, url_duplicate, simhash_duplicate
        """
        try:
            return dict(self.stats)
        except Exception as e:
            logger.error(f"[get_stats] 통계 반환 오류: {e}")
            return {}


# =============================================
# 직접 실행 시 테스트

# =============================================
# 직접 실행 시 전처리 테스트
# =============================================
if __name__ == "__main__":
    from datetime import timezone

    test_articles = [
        {
            "article_id": "abc001",
            "title": "손흥민, 챔피언스리그 골 폭발",
            "url": "https://sports.example.com/news/1",
            "summary": "손흥민이 챔피언스리그에서 2골을 넣으며 팀 승리를 이끌었다.",
            "published_at": datetime.now(timezone.utc),
            "language": "ko",
        },
        {
            "article_id": "abc002",
            "title": "손흥민, 챔피언스리그에서 2골 활약",  # 유사 중복
            "url": "https://other.example.com/news/2",
            "summary": "손흥민이 챔피언스리그에서 멀티골을 기록하며 팀을 승리로 이끌었다.",
            "published_at": datetime.now(timezone.utc),
            "language": "ko",
        },
        {
            "article_id": "abc003",
            "title": "[광고] 스포츠 용품 특가 이벤트",
            "url": "https://ad.example.com/promo",
            "summary": "지금 바로 구매하세요! 한정 수량",
            "published_at": datetime.now(timezone.utc),
            "language": "ko",
        },
        {
            "article_id": "abc004",
            "title": "Man City win Premier League title",
            "url": "https://bbc.co.uk/sport/football/12345",
            "summary": "Manchester City clinched the Premier League title.",
            "published_at": datetime.now(timezone.utc),
            "language": "en",
        },
    ]

    preprocessor = ArticlePreprocessor()
    results = preprocessor.run(test_articles)
    stats = preprocessor.get_stats()

    print(f"=== 전처리 결과 ===")
    print(f"입력: {stats['total']}건 → 통과: {stats['passed']}건")
    print(f"광고 필터: {stats['ad_filtered']}건 | 중복 제거: {stats['url_duplicate'] + stats['simhash_duplicate']}건")
    print()
    for a in results:
        print(f"  [{a.get('language')}] {a.get('title')}")
