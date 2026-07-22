# -*- coding: utf-8 -*-
"""
test_league_registry.py
========================
week1/league_registry.py 자체의 구조적 무결성 테스트.

이 파일은 "리그 하나를 추가할 때 특정 필드 채우는 걸 깜빡한다"는
패턴이 이번 세션에서만 4~5번 재발했던 지점이라(챔피언스리그/
브라질세리에A/코파리베르타도레스가 여러 파일에서 각각 따로 누락됐던
사례), 새 리그를 추가할 때 필수 필드가 하나라도 비면 즉시 실패하도록
고정했다. 앞으로 리그를 추가하면서 이 테스트가 깨지면, "또 어떤
소비 파일에 반영이 안 됐나"가 아니라 "레지스트리 자체에 뭘 빠뜨렸나"
로 바로 좁혀진다.
"""
from league_registry import LEAGUES, SIDEBAR_ORDER, SIDEBAR_NAME_TO_CODE, CODE_TO_SIDEBAR_NAME, get_league

REQUIRED_FIELDS = [
    "sidebar_name", "full_name", "short_name", "display_emoji", "en_name",
    "prompt_role", "standings_label", "section3_label", "keywords",
    "video_queries", "rag_queries", "season",
]


def test_every_league_has_all_required_fields():
    for code, meta in LEAGUES.items():
        for field in REQUIRED_FIELDS:
            assert field in meta, f"{code} 리그에 '{field}' 필드가 없다"
            assert meta[field] not in (None, "", []), f"{code} 리그의 '{field}' 필드가 비어 있다"


def test_every_league_has_nonempty_keywords():
    """
    키워드가 비어 있으면 네이버 검색도, week2/nodes.py의 필터도 전부
    무력화된다 — 가장 치명적인 누락이라 별도로 강조 검사한다.
    """
    for code, meta in LEAGUES.items():
        assert len(meta["keywords"]) >= 3, f"{code} 리그의 키워드가 너무 적다({len(meta['keywords'])}개)"


def test_sidebar_order_matches_registry_keys():
    """SIDEBAR_ORDER에 등록되지 않은 리그, 혹은 존재하지 않는 코드가 섞이면 사이드바가 깨진다."""
    assert set(SIDEBAR_ORDER) == set(LEAGUES.keys())


def test_sidebar_name_mappings_are_consistent_bijection():
    """표시명 <-> 코드 매핑이 서로 역함수 관계여야 한다(중복 표시명 없이 1:1)."""
    assert len(SIDEBAR_NAME_TO_CODE) == len(LEAGUES)
    for code, meta in LEAGUES.items():
        assert SIDEBAR_NAME_TO_CODE[meta["sidebar_name"]] == code
        assert CODE_TO_SIDEBAR_NAME[code] == meta["sidebar_name"]


def test_season_tuple_shape():
    """season은 (시작일, 종료일, 다음 시즌 시작일 or None) 3-tuple이어야 한다."""
    for code, meta in LEAGUES.items():
        season = meta["season"]
        assert len(season) == 3, f"{code} 리그의 season 튜플 길이가 3이 아니다"
        start, end, _next_start = season
        assert start < end, f"{code} 리그의 시즌 시작일이 종료일보다 앞서지 않는다"


def test_get_league_returns_empty_dict_for_unknown_code():
    assert get_league("NOT_A_REAL_CODE") == {}


def test_get_league_returns_metadata_for_known_code():
    assert get_league("PL")["short_name"] == "EPL"


def test_bare_country_or_surname_keywords_deliberately_excluded():
    """
    이번 세션에서 실제로 오탐을 냈던 위험 키워드들이 재발하지 않았는지
    확인한다 — 브라질세리에A의 단독 "브라질"/"brazil", 코파리베르타
    도레스의 단독 "산투스"/"santos".
    """
    bsa_keywords = [kw.lower() for kw in LEAGUES["BSA"]["keywords"]]
    assert "브라질" not in bsa_keywords
    assert "brazil" not in bsa_keywords

    cli_keywords = [kw.lower() for kw in LEAGUES["CLI"]["keywords"]]
    assert "산투스" not in cli_keywords
    assert "santos" not in cli_keywords
