# -*- coding: utf-8 -*-
"""
constants.py
============
app.py에서 분리한 이미지 URL·로고 SVG·색상 상수.
"""
import base64


# ── 이미지 URL 상수 ───────────────────────────────────────────
IMG_STADIUM   = "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?auto=format&fit=crop&w=1400&q=80"
IMG_BALL      = "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&w=400&q=80"
IMG_MATCH     = "https://images.unsplash.com/photo-1553778263-73a83bab9b0c?auto=format&fit=crop&w=800&q=80"
IMG_CROWD     = "https://images.unsplash.com/photo-1562552476-8ac59b2a2e46?auto=format&fit=crop&w=800&q=80"
# ── Football Lens 커스텀 SVG 로고 (저작권 없는 독자 디자인) ──────────────
# 축구공(오각형 패턴) + 렌즈 링 조합 — 흰색 버전 (사이드바·히어로 공용)
_FL_LOGO_SVG_WHITE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
  <circle cx="30" cy="30" r="27" fill="none" stroke="white" stroke-width="2.5"/>
  <circle cx="30" cy="27" r="12.5" fill="none" stroke="white" stroke-width="1.8"/>
  <polygon points="30,20 36.3,24.2 33.8,31.4 26.2,31.4 23.7,24.2" fill="white"/>
  <line x1="30" y1="14.5" x2="30" y2="20" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="41.8" y1="22.3" x2="36.3" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="38.2" y1="37.2" x2="33.8" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="21.8" y1="37.2" x2="26.2" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="18.2" y1="22.3" x2="23.7" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <text x="30" y="53" font-family="Arial,sans-serif" font-size="6.2" font-weight="900"
        text-anchor="middle" fill="white" letter-spacing="2.5">LENS</text>
</svg>"""

# 컬러 버전 (어두운 배경용 — 빨강 링 + 흰 볼)
_FL_LOGO_SVG_COLOR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
  <circle cx="30" cy="30" r="27" fill="none" stroke="#CC0000" stroke-width="3"/>
  <circle cx="30" cy="30" r="23" fill="#CC0000"/>
  <circle cx="30" cy="27" r="12.5" fill="none" stroke="white" stroke-width="1.8"/>
  <polygon points="30,20 36.3,24.2 33.8,31.4 26.2,31.4 23.7,24.2" fill="white"/>
  <line x1="30" y1="14.5" x2="30" y2="20" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="41.8" y1="22.3" x2="36.3" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="38.2" y1="37.2" x2="33.8" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="21.8" y1="37.2" x2="26.2" y2="31.4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="18.2" y1="22.3" x2="23.7" y2="24.2" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
  <text x="30" y="53" font-family="Arial,sans-serif" font-size="6.2" font-weight="900"
        text-anchor="middle" fill="white" letter-spacing="2.5">LENS</text>
</svg>"""

# data URI 변환 (img src 속성에 직접 사용 가능)
LOGO_WHITE = "data:image/svg+xml;base64," + base64.b64encode(_FL_LOGO_SVG_WHITE.encode()).decode()
LOGO_COLOR = "data:image/svg+xml;base64," + base64.b64encode(_FL_LOGO_SVG_COLOR.encode()).decode()

IMG_EPL       = LOGO_WHITE   # 하위 호환 — 기존 IMG_EPL 참조 코드도 자동 대체
IMG_TROPHY    = "https://images.unsplash.com/photo-1594736797933-d0501ba2fe65?auto=format&fit=crop&w=400&q=80"
IMG_TRAINING  = "https://images.unsplash.com/photo-1526232761682-d26e03ac148e?auto=format&fit=crop&w=800&q=80"

# ── 추가 축구 사진 ────────────────────────────────────────────
IMG_KICK       = "https://images.unsplash.com/photo-1543326727-cf6c39e8f84c?auto=format&fit=crop&w=800&q=80"
IMG_GOALKEEPER = "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?auto=format&fit=crop&w=800&q=80"
IMG_CELEBRATE  = "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=800&q=80"
IMG_STADIUM2   = "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=800&q=80"
IMG_BOOTS      = "https://images.unsplash.com/photo-1560272564-c83b66b1ad12?auto=format&fit=crop&w=800&q=80"
IMG_AERIAL     = "https://images.unsplash.com/photo-1587329310686-91414b8e3cb7?auto=format&fit=crop&w=800&q=80"

# 포토 스트립 (이모지 라벨 + URL + 배지 색상)
PHOTO_STRIP = [
    ("⚽ 경기 액션",    IMG_MATCH,      "#CC0000"),
    ("🏟️ 스타디움",    IMG_STADIUM2,   "#1A1A1A"),
    ("🧤 골키퍼",      IMG_GOALKEEPER, "#003399"),
    ("🎉 골 세리머니",  IMG_CELEBRATE,  "#CC0000"),
    ("🏆 트로피",      IMG_TROPHY,     "#E65C00"),
    ("🦵 훈련",        IMG_TRAINING,   "#2E7D32"),
    ("👟 클리트",      IMG_BOOTS,      "#555555"),
    ("🎟️ 관중석",     IMG_CROWD,      "#1A1A1A"),
]


# 리그명 -> 관련 키워드 매핑, 표시용 이름+이모지, API 코드 매핑은
# 전부 week1/league_registry.py에서 파생시킨다(코드 기준 → 표시명
# 기준으로 변환). 예전엔 이 파일에 직접 정의돼 있어서, 화면 필터
# 키워드와 week1/naver_collector.py의 수집 키워드가 따로 관리되다
# 어긋나는 버그가 반복됐다(예: 브라질세리에A의 "브라질" 단독 키워드가
# 한쪽에서만 빠져있던 사례, 2026-07-22). 이제 레지스트리 하나만
# 고치면 여기도 자동으로 반영된다.
from league_registry import LEAGUES as _LEAGUES

_LEAGUE_KEYWORDS: dict = {
    meta["sidebar_name"]: [kw.lower() for kw in meta["keywords"]]
    for meta in _LEAGUES.values()
}

_LEAGUE_DISPLAY: dict = {
    meta["sidebar_name"]: meta["display_emoji"] for meta in _LEAGUES.values()
}

# 리그명(사이드바 표시용) → football-data.org API 코드
# 예전엔 app.py에서 .replace() 체인 2곳이 같은 매핑을 중복 구현했는데,
# "세리에A"가 "브라질세리에A"의 부분 문자열이라 replace 순서에 따라
# 오작동할 위험이 있어서 딕셔너리 조회로 통일했다.
_LEAGUE_API_CODE: dict = {
    meta["sidebar_name"]: code for code, meta in _LEAGUES.items()
}

# API 코드 → 리그명 (역매핑, _LEAGUE_KEYWORDS 등 표시명 기준 딕셔너리를
# 코드값만 갖고 있을 때 조회하기 위함)
_CODE_TO_LEAGUE_NAME: dict = {v: k for k, v in _LEAGUE_API_CODE.items()}
