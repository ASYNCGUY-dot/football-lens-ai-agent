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


# 리그명 -> 관련 키워드 매핑 (소문자로 비교)
# 리그 라벨만 있으면 "전북현대"·"울산HD"처럼 팀명만 언급된 K리그 기사가
# 걸러지지 않고 다른 리그로 새는 문제가 있어서, week1/naver_collector.py의
# 수집 키워드(LEAGUE_KEYWORD_MAP)와 맞춰 팀/선수명까지 포함시켰다.
_LEAGUE_KEYWORDS: dict = {
    "2026 FIFA 월드컵": ["월드컵", "world cup", "fifa 2026", "wc 2026", "2026 wc",
                        "월드컵 2026", "북중미 월드컵"],
    "EPL (프리미어리그)": ["epl", "프리미어리그", "premier league", "잉글랜드",
                        "맨체스터시티", "리버풀", "아스날", "첼시", "토트넘",
                        "맨체스터유나이티드", "손흥민", "황희찬", "홀란드", "살라", "벨링엄",
                        "manchester city", "liverpool", "arsenal", "chelsea", "tottenham",
                        "manchester united", "haaland", "salah", "bellingham"],
    "K리그1":            ["k리그", "k-league", "kl1", "한국 프로축구", "k league",
                        "전북현대", "울산hd", "울산현대", "fc서울", "수원삼성",
                        "포항스틸러스", "대구fc", "광주fc",
                        "jeonbuk", "ulsan hd", "fc seoul"],
    "라리가":            ["라리가", "laliga", "la liga", "스페인 리그",
                        "레알마드리드", "바르셀로나", "아틀레티코마드리드", "야말", "비니시우스",
                        "real madrid", "barcelona", "atletico madrid", "yamal", "vinicius"],
    "분데스리가":         ["분데스리가", "bundesliga", "독일 리그",
                        "바이에른뮌헨", "도르트문트", "레버쿠젠", "케인", "무시알라",
                        "bayern munich", "borussia dortmund", "bayer leverkusen", "kane", "musiala"],
    "세리에A":           ["세리에", "serie a", "이탈리아 리그",
                        "인테르밀란", "유벤투스", "ac밀란", "나폴리", "루카쿠",
                        "inter milan", "juventus", "ac milan", "napoli", "lukaku"],
    "리그앙":            ["리그앙", "ligue 1", "프랑스 리그",
                        "psg", "파리생제르맹", "모나코", "마르세유", "음바페",
                        "paris saint-germain", "monaco", "marseille", "mbappe"],
    "챔피언스리그":       ["챔피언스리그", "champions league", "ucl",
                        "맨체스터시티", "레알마드리드", "바이에른뮌헨",
                        "manchester city", "real madrid", "bayern munich"],
    # "브라질"/"brazil" 단독 키워드는 뺐다 — 브라질 국가대표팀·월드컵
    # 뉴스 등 브라질세리에A와 무관한 내용까지 다 걸려서(2026-07-22,
    # 카세미루 월드컵 기사가 뜬 사례) week1/naver_collector.py의
    # BRASILEIRAO_KEYWORDS와 맞췄다 — 수집 키워드와 필터 키워드가
    # 다르면 또 같은 문제가 재발한다.
    "브라질세리에A":      ["브라질세리에A", "브라질리안세리에A", "브라지레이랑", "브라질 축구",
                        "brasileirao", "brazilian serie a",
                        "팔메이라스", "플라멩구", "플루미넨시", "브라간치누", "파라나엔세", "코린치안스",
                        "palmeiras", "flamengo", "fluminense", "bragantino"],
    # "산투스"/"santos"는 일부러 뺐다 — 흔한 선수 성씨와 겹쳐 오탐 발생
    # (week1/naver_collector.py의 LIBERTADORES_KEYWORDS 주석 참고).
    "코파리베르타도레스":  ["코파 리베르타도레스", "리베르타도레스", "copa libertadores", "libertadores",
                        "보카주니어스", "리버플레이트", "그레미우", "인테르나시오나우", "코린치안스",
                        "boca juniors", "river plate", "gremio", "internacional", "corinthians"],
    "EFL 챔피언십":      ["efl챔피언십", "잉글랜드 2부", "championship",
                        "리즈유나이티드", "셰필드유나이티드", "선덜랜드", "노리치시티", "웨스트브롬",
                        "leeds united", "sheffield united", "sunderland", "norwich city", "west brom"],
    "에레디비시":        ["에레디비시", "네덜란드 리그", "eredivisie",
                        "아약스", "psv에인트호번", "페예노르트", "az알크마르",
                        "ajax", "psv eindhoven", "feyenoord", "az alkmaar"],
    "프리메이라리가":     ["프리메이라리가", "포르투갈 리그", "primeira liga",
                        "벤피카", "포르투", "스포르팅cp", "브라가",
                        "benfica", "porto", "sporting cp", "braga"],
}

# 리그명 → 표시용 이름 + 이모지
_LEAGUE_DISPLAY: dict = {
    "2026 FIFA 월드컵": "🌍 2026 FIFA 월드컵",
    "EPL (프리미어리그)": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL",
    "K리그1":            "🇰🇷 K리그1",
    "라리가":            "🇪🇸 라리가",
    "분데스리가":         "🇩🇪 분데스리가",
    "세리에A":           "🇮🇹 세리에A",
    "리그앙":            "🇫🇷 리그앙",
    "챔피언스리그":       "⭐ UEFA 챔피언스리그",
    "브라질세리에A":      "🇧🇷 브라질 세리에A",
    "코파리베르타도레스":  "🏆 코파 리베르타도레스",
    "EFL 챔피언십":      "🏴󠁧󠁢󠁥󠁮󠁧󠁿 EFL 챔피언십",
    "에레디비시":        "🇳🇱 에레디비시",
    "프리메이라리가":     "🇵🇹 프리메이라리가",
}

# 리그명(사이드바 표시용) → football-data.org API 코드
# 예전엔 app.py에서 .replace() 체인 2곳이 같은 매핑을 중복 구현했는데,
# "세리에A"가 "브라질세리에A"의 부분 문자열이라 replace 순서에 따라
# 오작동할 위험이 있어서 딕셔너리 조회로 통일했다.
_LEAGUE_API_CODE: dict = {
    "EPL (프리미어리그)": "PL",
    "2026 FIFA 월드컵": "WC",
    "K리그1": "KL1",
    "라리가": "PD",
    "분데스리가": "BL1",
    "세리에A": "SA",
    "리그앙": "FL1",
    "챔피언스리그": "CL",
    "브라질세리에A": "BSA",
    "코파리베르타도레스": "CLI",
    "EFL 챔피언십": "ELC",
    "에레디비시": "DED",
    "프리메이라리가": "PPL",
}

# API 코드 → 리그명 (역매핑, _LEAGUE_KEYWORDS 등 표시명 기준 딕셔너리를
# 코드값만 갖고 있을 때 조회하기 위함)
_CODE_TO_LEAGUE_NAME: dict = {v: k for k, v in _LEAGUE_API_CODE.items()}
