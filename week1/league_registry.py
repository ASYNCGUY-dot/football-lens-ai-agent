# -*- coding: utf-8 -*-
"""
league_registry.py
===================
지원하는 모든 리그/대회의 메타데이터를 담는 단일 진실 공급원(single
source of truth).

왜 만들었나
-----------
이 프로젝트는 리그를 하나 추가할 때마다 naver_collector.py(검색
키워드), constants.py(표시명/필터 키워드), season_info.py(시즌 일정),
nodes.py(리포트 섹션 제목), llm_nodes.py(프롬프트용 영어/한국어 이름),
insight_node.py(AI 분석가 role), youtube_collector.py(영상 검색어),
rag_node.py(RAG 쿼리), sidebar.py(선택지), players.py(탭 헤더) 등
8개 이상의 파일을 일일이 손봐야 했다. 실제로 이번 세션에서만 "리그
하나를 어느 파일에 추가하는 걸 깜빡했다"는 버그가 4~5번 재발했다
(챔피언스리그/브라질세리에A/코파리베르타도레스가 llm_nodes.py의
analyze_match_node, rag_node.py, players.py에서 각각 따로 누락돼
있었던 사례 등, 2026-07-22).

이 파일 하나에 각 리그의 모든 속성을 몰아넣고, 나머지 파일들은
여기서 파생시키는 방식으로 통합했다 — 리그를 추가/수정할 땐 이제
이 파일 하나만 고치면 된다.

수집 키워드(keywords)에 대한 참고
----------------------------------
이 키워드 리스트는 두 가지 용도로 함께 쓰인다: (1) 네이버 뉴스 검색
API에 보낼 검색어, (2) week2/nodes.py의 classify_node가 리그와
무관한 기사를 걸러낼 때 쓰는 필터 키워드(제목만 검사, summary는
포함 문구로 오탐이 났던 전례가 있어 뺐음 — nodes.py 주석 참고).
두 용도가 같은 리스트를 공유해야 "수집할 때 쓴 키워드와 걸러낼 때
쓰는 키워드가 다르면 관련 기사까지 걸러지는" 예전 버그가 재발하지
않는다.

흔한 성씨(예: "산투스"/"Santos")나 지나치게 넓은 단어(예: 브라질
리그에서 "브라질"/"brazil" 단독)는 실제로 오탐을 낸 적이 있어
일부러 뺐다 — 각 리스트의 주석 참고.
"""

from datetime import date

# =============================================
# 리그별 키워드 (네이버 검색 + 필터 겸용)
# =============================================

_WC_KEYWORDS = [
    "2026 월드컵", "FIFA 월드컵", "북중미 월드컵", "월드컵 2026",
    "world cup", "fifa world cup", "2026 world cup",
    "월드컵 한국", "태극전사", "국가대표 월드컵",
    "월드컵 손흥민", "월드컵 이강인", "월드컵 황희찬",
    "월드컵 조규성", "월드컵 김민재", "월드컵 황인범",
    "월드컵 조별리그", "월드컵 16강", "월드컵 8강",
    "월드컵 4강", "월드컵 결승", "월드컵 경기결과",
    "월드컵 경기일정", "월드컵 득점",
    "월드컵 브라질", "월드컵 아르헨티나", "월드컵 프랑스",
    "월드컵 잉글랜드", "월드컵 독일", "월드컵 스페인",
    "월드컵 포르투갈", "월드컵 네덜란드",
    "월드컵 음바페", "월드컵 네이마르", "월드컵 메시",
    "월드컵 홀란드", "월드컵 살라",
]

_PL_KEYWORDS = [
    "EPL", "프리미어리그", "이적시장", "premier league",
    "맨체스터시티", "리버풀", "아스날", "첼시",
    "토트넘", "맨체스터유나이티드",
    "manchester city", "liverpool", "arsenal", "chelsea",
    "tottenham", "manchester united",
    "손흥민", "황희찬", "son heung-min",
    "홀란드", "살라", "벨링엄", "haaland", "salah", "bellingham",
]

_KL1_KEYWORDS = [
    "K리그", "K리그1", "한국 프로축구", "k league", "k-league",
    "전북현대", "울산HD", "FC서울", "수원삼성",
    "포항스틸러스", "대구FC", "광주FC",
    "jeonbuk", "ulsan hd", "fc seoul",
    "K리그 순위", "K리그 경기결과",
]

_PD_KEYWORDS = [
    "라리가", "스페인 축구", "la liga", "laliga",
    "레알마드리드", "바르셀로나", "아틀레티코마드리드",
    "real madrid", "barcelona", "atletico madrid",
    "야말", "비니시우스", "이강인", "yamal", "vinicius",
]

_BL1_KEYWORDS = [
    "분데스리가", "독일 축구", "bundesliga",
    "바이에른뮌헨", "도르트문트", "레버쿠젠",
    "bayern munich", "borussia dortmund", "bayer leverkusen",
    "케인", "무시알라", "어데예미", "kane", "musiala",
]

_SA_KEYWORDS = [
    "세리에A", "이탈리아 축구", "serie a",
    "인테르밀란", "유벤투스", "AC밀란", "나폴리",
    "inter milan", "juventus", "ac milan", "napoli",
    "루카쿠", "마르티네스", "lukaku",
]

_FL1_KEYWORDS = [
    "리그앙", "프랑스 축구", "ligue 1",
    "PSG", "파리생제르맹", "모나코", "마르세유",
    "paris saint-germain", "monaco", "marseille",
    "음바페", "mbappe",
]

_CL_KEYWORDS = [
    "챔피언스리그", "UCL", "UEFA챔피언스리그", "champions league",
    "맨체스터시티", "레알마드리드", "바이에른뮌헨", "PSG",
    "리버풀", "아스날", "인테르밀란", "바르셀로나",
    "manchester city", "real madrid", "bayern munich",
]

_BSA_KEYWORDS = [
    # "브라질"/"brazil" 단독은 일부러 뺐다 — 브라질 국가대표팀·월드컵
    # 뉴스처럼 리그와 무관한 내용까지 걸리는 오탐이 있었다(2026-07-22).
    "브라질세리에A", "브라질리안세리에A", "브라지레이랑", "브라질 축구",
    "brasileirao", "brazilian serie a",
    "팔메이라스", "플라멩구", "플루미넨시", "브라간치누",
    "파라나엔세", "코린치안스", "상파울루FC", "그레미우",
    "palmeiras", "flamengo", "fluminense", "bragantino",
]

_CLI_KEYWORDS = [
    # "산투스"/"santos"는 일부러 뺐다 — 흔한 선수 성씨(예: Andrey
    # Santos)와 겹쳐 무관한 이적 기사가 걸리는 오탐이 있었다(2026-07-22).
    "코파리베르타도레스", "리베르타도레스", "남미 클럽대항전", "copa libertadores",
    "보카주니어스", "리버플레이트", "플라멩구", "팔메이라스",
    "그레미우", "인테르나시오나우", "코린치안스",
    "boca juniors", "river plate", "gremio", "internacional", "corinthians",
]

_ELC_KEYWORDS = [
    "EFL챔피언십", "잉글랜드 2부", "championship",
    "리즈유나이티드", "셰필드유나이티드", "선덜랜드", "노리치시티", "웨스트브롬",
    "leeds united", "sheffield united", "sunderland", "norwich city", "west brom",
]

_DED_KEYWORDS = [
    "에레디비시", "네덜란드 리그", "eredivisie",
    "아약스", "PSV에인트호번", "페예노르트", "AZ알크마르",
    "ajax", "psv eindhoven", "feyenoord", "az alkmaar",
]

_PPL_KEYWORDS = [
    "프리메이라리가", "포르투갈 리그", "primeira liga",
    "벤피카", "포르투", "스포르팅CP", "브라가",
    "benfica", "porto", "sporting cp", "braga",
]


# =============================================
# 리그 레지스트리 — 리그 코드(football-data.org 기준) → 전체 메타데이터
# =============================================
LEAGUES: dict = {
    "WC": {
        "sidebar_name": "2026 FIFA 월드컵",
        "full_name": "2026 FIFA 월드컵",
        "short_name": "월드컵",
        "display_emoji": "🌍 2026 FIFA 월드컵",
        "en_name": "the 2026 FIFA World Cup",
        "prompt_role": "2026 FIFA 월드컵 전문 축구 애널리스트",
        "standings_label": "조별리그 순위",
        "section3_label": "월드컵 순위 및 토너먼트 전망",
        "keywords": _WC_KEYWORDS,
        "video_queries": ["2026 FIFA 월드컵 하이라이트", "World Cup 2026 highlights", "월드컵 한국 하이라이트"],
        "rag_queries": ["2026 FIFA 월드컵 경기 결과", "월드컵 한국 대표팀 조별리그"],
        # (시즌 시작, 시즌 종료, 다음 시즌 시작)
        "season": (date(2026, 6, 11), date(2026, 7, 19), None),
    },
    "PL": {
        "sidebar_name": "EPL (프리미어리그)",
        "full_name": "EPL 프리미어리그",
        "short_name": "EPL",
        "display_emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL",
        "en_name": "the English Premier League",
        "prompt_role": "EPL 및 한국 축구 전문 애널리스트",
        "standings_label": "EPL 순위 (상위 5팀)",
        "section3_label": "EPL 순위 전망",
        "keywords": _PL_KEYWORDS,
        "video_queries": ["EPL highlights this week", "Premier League goals", "손흥민 하이라이트"],
        "rag_queries": ["EPL 프리미어리그 경기 결과", "한국 선수 손흥민 이강인 황희찬"],
        "season": (date(2025, 8, 16), date(2026, 5, 24), date(2026, 8, 8)),
    },
    "KL1": {
        "sidebar_name": "K리그1",
        "full_name": "K리그1",
        "short_name": "K리그",
        "display_emoji": "🇰🇷 K리그1",
        "en_name": "the Korean K League 1",
        "prompt_role": "K리그 전문 축구 애널리스트",
        "standings_label": "K리그1 순위 (상위 5팀)",
        "section3_label": "K리그1 순위 전망",
        "keywords": _KL1_KEYWORDS,
        "video_queries": ["K리그 하이라이트", "K리그1 하이라이트", "K League highlights"],
        "rag_queries": ["K리그1 경기 결과", "한국 프로축구 순위"],
        "season": (date(2026, 2, 21), date(2026, 11, 30), None),
        # football-data.org가 K리그를 지원하지 않아 순위표/득점왕/경기
        # 데이터는 이 리그에서만 제공 안 됨 — 자세한 내용은
        # week1/collectors/football_data_collector.py의 AVAILABLE_LEAGUES 주석 참고.
        "unsupported_by_football_data": True,
    },
    "PD": {
        "sidebar_name": "라리가",
        "full_name": "라리가",
        "short_name": "라리가",
        "display_emoji": "🇪🇸 라리가",
        "en_name": "La Liga",
        "prompt_role": "라리가 전문 축구 애널리스트",
        "standings_label": "라리가 순위 (상위 5팀)",
        "section3_label": "라리가 순위 전망",
        "keywords": _PD_KEYWORDS,
        "video_queries": ["라리가 하이라이트", "La Liga highlights"],
        "rag_queries": ["라리가 경기 결과", "레알마드리드 바르셀로나"],
        "season": (date(2025, 8, 15), date(2026, 6, 1), date(2026, 8, 15)),
    },
    "BL1": {
        "sidebar_name": "분데스리가",
        "full_name": "분데스리가",
        "short_name": "분데스리가",
        "display_emoji": "🇩🇪 분데스리가",
        "en_name": "the Bundesliga",
        "prompt_role": "분데스리가 전문 축구 애널리스트",
        "standings_label": "분데스리가 순위 (상위 5팀)",
        "section3_label": "분데스리가 순위 전망",
        "keywords": _BL1_KEYWORDS,
        "video_queries": ["분데스리가 하이라이트", "Bundesliga highlights"],
        "rag_queries": ["분데스리가 경기 결과", "바이에른뮌헨 도르트문트"],
        "season": (date(2025, 8, 22), date(2026, 5, 23), date(2026, 8, 7)),
    },
    "SA": {
        "sidebar_name": "세리에A",
        "full_name": "세리에A",
        "short_name": "세리에A",
        "display_emoji": "🇮🇹 세리에A",
        "en_name": "Serie A",
        "prompt_role": "세리에A 전문 축구 애널리스트",
        "standings_label": "세리에A 순위 (상위 5팀)",
        "section3_label": "세리에A 순위 전망",
        "keywords": _SA_KEYWORDS,
        "video_queries": ["세리에A 하이라이트", "Serie A highlights"],
        "rag_queries": ["세리에A 경기 결과", "인테르밀란 유벤투스"],
        "season": (date(2025, 8, 23), date(2026, 5, 31), date(2026, 8, 21)),
    },
    "FL1": {
        "sidebar_name": "리그앙",
        "full_name": "리그앙",
        "short_name": "리그앙",
        "display_emoji": "🇫🇷 리그앙",
        "en_name": "Ligue 1",
        "prompt_role": "리그앙 전문 축구 애널리스트",
        "standings_label": "리그앙 순위 (상위 5팀)",
        "section3_label": "리그앙 순위 전망",
        "keywords": _FL1_KEYWORDS,
        "video_queries": ["리그앙 하이라이트", "Ligue 1 highlights"],
        "rag_queries": ["리그앙 경기 결과", "PSG 파리생제르맹"],
        "season": (date(2025, 8, 16), date(2026, 5, 24), date(2026, 8, 9)),
    },
    "CL": {
        "sidebar_name": "챔피언스리그",
        "full_name": "UEFA 챔피언스리그",
        "short_name": "챔피언스리그",
        "display_emoji": "⭐ UEFA 챔피언스리그",
        "en_name": "the UEFA Champions League",
        "prompt_role": "UEFA 챔피언스리그 전문 축구 애널리스트",
        "standings_label": "조별 순위",
        "section3_label": "토너먼트 전망",
        "keywords": _CL_KEYWORDS,
        "video_queries": ["챔피언스리그 하이라이트", "Champions League highlights"],
        "rag_queries": ["챔피언스리그 경기 결과", "챔피언스리그 8강"],
        "season": (date(2025, 9, 16), date(2026, 5, 30), date(2026, 9, 15)),
    },
    "BSA": {
        "sidebar_name": "브라질세리에A",
        "full_name": "브라질 세리에A",
        "short_name": "브라질 세리에A",
        "display_emoji": "🇧🇷 브라질 세리에A",
        "en_name": "the Brazilian Serie A",
        "prompt_role": "브라질 세리에A 전문 축구 애널리스트",
        "standings_label": "브라질 세리에A 순위 (상위 5팀)",
        "section3_label": "브라질 세리에A 순위 전망",
        "keywords": _BSA_KEYWORDS,
        "video_queries": ["브라질세리에A 하이라이트", "Brasileirao highlights"],
        "rag_queries": ["브라질세리에A 경기 결과", "팔메이라스 플라멩구"],
        "season": (date(2026, 1, 28), date(2026, 12, 2), date(2027, 1, 27)),
    },
    "CLI": {
        "sidebar_name": "코파리베르타도레스",
        "full_name": "코파 리베르타도레스",
        "short_name": "코파 리베르타도레스",
        "display_emoji": "🏆 코파 리베르타도레스",
        "en_name": "the Copa Libertadores",
        "prompt_role": "코파 리베르타도레스 전문 축구 애널리스트",
        "standings_label": "조별 순위",
        "section3_label": "토너먼트 전망",
        "keywords": _CLI_KEYWORDS,
        "video_queries": ["코파리베르타도레스 하이라이트", "Copa Libertadores highlights"],
        "rag_queries": ["코파리베르타도레스 경기 결과", "보카주니어스 리버플레이트"],
        "season": (date(2026, 2, 4), date(2026, 11, 28), date(2027, 2, 3)),
    },
    "ELC": {
        "sidebar_name": "EFL 챔피언십",
        "full_name": "EFL 챔피언십",
        "short_name": "EFL 챔피언십",
        "display_emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 EFL 챔피언십",
        "en_name": "the EFL Championship",
        "prompt_role": "EFL 챔피언십 전문 축구 애널리스트",
        "standings_label": "EFL 챔피언십 순위 (상위 5팀)",
        "section3_label": "EFL 챔피언십 순위 전망",
        "keywords": _ELC_KEYWORDS,
        "video_queries": ["EFL 챔피언십 하이라이트", "Championship highlights"],
        "rag_queries": ["EFL 챔피언십 경기 결과", "리즈유나이티드 선덜랜드"],
        # API currentSeason(다음 시즌) 확인(2026-07-22): 2026-08-14~2027-05-01
        "season": (date(2025, 8, 9), date(2026, 5, 3), date(2026, 8, 14)),
    },
    "DED": {
        "sidebar_name": "에레디비시",
        "full_name": "에레디비시",
        "short_name": "에레디비시",
        "display_emoji": "🇳🇱 에레디비시",
        "en_name": "the Dutch Eredivisie",
        "prompt_role": "에레디비시 전문 축구 애널리스트",
        "standings_label": "에레디비시 순위 (상위 5팀)",
        "section3_label": "에레디비시 순위 전망",
        "keywords": _DED_KEYWORDS,
        "video_queries": ["에레디비시 하이라이트", "Eredivisie highlights"],
        "rag_queries": ["에레디비시 경기 결과", "아약스 PSV에인트호번"],
        # API currentSeason(다음 시즌) 확인(2026-07-22): 2026-08-07~2027-05-23
        "season": (date(2025, 8, 8), date(2026, 5, 24), date(2026, 8, 7)),
    },
    "PPL": {
        "sidebar_name": "프리메이라리가",
        "full_name": "프리메이라리가",
        "short_name": "프리메이라리가",
        "display_emoji": "🇵🇹 프리메이라리가",
        "en_name": "the Portuguese Primeira Liga",
        "prompt_role": "프리메이라리가 전문 축구 애널리스트",
        "standings_label": "프리메이라리가 순위 (상위 5팀)",
        "section3_label": "프리메이라리가 순위 전망",
        "keywords": _PPL_KEYWORDS,
        "video_queries": ["프리메이라리가 하이라이트", "Primeira Liga highlights"],
        "rag_queries": ["프리메이라리가 경기 결과", "벤피카 포르투"],
        # API currentSeason(다음 시즌) 확인(2026-07-22): 2026-08-08~2027-05-16
        "season": (date(2025, 8, 15), date(2026, 5, 17), date(2026, 8, 8)),
    },
}

# 사이드바 selectbox 표시 순서(그대로 유지 — 기존 UI 순서와 동일하게)
SIDEBAR_ORDER = ["PL", "WC", "KL1", "PD", "BL1", "SA", "FL1", "CL", "BSA", "CLI", "ELC", "DED", "PPL"]

# 표시명(sidebar_name) → 코드 역매핑, 코드 → 표시명 매핑 (자주 쓰여서 미리 계산)
SIDEBAR_NAME_TO_CODE: dict = {v["sidebar_name"]: k for k, v in LEAGUES.items()}
CODE_TO_SIDEBAR_NAME: dict = {k: v["sidebar_name"] for k, v in LEAGUES.items()}


def get_league(code: str) -> dict:
    """리그 코드로 메타데이터 딕셔너리를 반환한다. 없으면 빈 딕셔너리."""
    return LEAGUES.get(code, {})
