# -*- coding: utf-8 -*-
"""
test_league_filter.py
======================
week2/nodes.py의 _filter_by_league()에 대한 회귀 테스트.

이 함수는 이번 세션에서 실제로 여러 번 버그가 났던 지점이라(황인범
Porto 이적 기사가 K리그로 잘못 분류된 사례, "전북현대"/"전북 현대"
공백 불일치, Santos FC 키워드가 선수 성씨와 충돌한 사례, "필터 결과
0건이면 원본 반환"하던 안전장치가 실제로는 필터를 무력화한 사례 등),
같은 버그가 재발하면 바로 잡아내도록 각 사례를 그대로 테스트로
고정했다.
"""
from nodes import _filter_by_league


def test_title_only_excludes_summary_mentions():
    """
    요약(summary)에만 다른 리그 club명이 스치듯 언급된 기사는 제외돼야
    한다 — 실제 사례: 황인범의 포르투 이적 기사(제목엔 K리그 언급 없음)가
    요약에 "K리그 FC서울에서 잠시 뛴 뒤..."라는 문구 때문에 K리그
    이적 소식으로 잘못 분류됐었다.
    """
    ko = [{
        "title": "월드컵 끝나자 빅클럽 도약! 황인범, 포르투 입단 확정...이적료 최대 8...",
        "summary": "러시아의 우크라이나 침공 이후 K리그 FC서울에서 잠시 뛴 뒤 올림피아코스와...",
    }]
    filtered_ko, filtered_en = _filter_by_league(ko, [], "KL1")
    assert filtered_ko == []


def test_title_match_is_kept():
    """제목에 실제로 리그 키워드가 있는 기사는 정상적으로 통과해야 한다."""
    ko = [{"title": "전북 현대, 대전과 0-0 무승부", "summary": ""}]
    filtered_ko, _ = _filter_by_league(ko, [], "KL1")
    assert len(filtered_ko) == 1


def test_whitespace_insensitive_matching():
    """
    키워드가 "전북현대"(붙여쓰기)인데 기사 제목은 "전북 현대"(띄어쓰기)인
    경우도 매칭돼야 한다 — 실제 확인된 표기 불일치 사례.
    """
    ko = [{"title": "전북 현대, 대전과 0-0 무승부", "summary": ""}]
    filtered_ko, _ = _filter_by_league(ko, [], "KL1")
    assert len(filtered_ko) == 1


def test_search_keyword_field_ignored():
    """
    '이 기사를 찾아낸 검색어'(a["keyword"])는 매칭에 안 써야 한다 —
    네이버 검색이 본문 어딘가에 스치듯 언급된 무관한 기사를 돌려줄 수
    있어서, keyword 필드만 보고 관련 기사로 오판하면 안 된다.
    """
    ko = [{
        "title": "월드컵 아름 떨어낸 손흥민, 2경기 연속골 도전...LAFC 상승세 이끌다",
        "summary": "",
        "keyword": "K리그",  # 이 기사를 찾아낸 검색어가 K리그였다고 해도
    }]
    filtered_ko, _ = _filter_by_league(ko, [], "KL1")
    assert filtered_ko == []


def test_common_surname_false_positive_excluded():
    """
    "Santos"처럼 클럽명이면서 흔한 선수 성씨이기도 한 키워드로 인한
    오탐 — 실제 사례: 코파리베르타도레스 필터에서 "산투스" 키워드가
    Andrey Santos(맨유 이적 기사)의 성씨와 겹쳐 오탐이 났다. 지금은
    이 키워드 자체를 뺐으니, 무관한 맨유 이적 기사는 계속 제외돼야
    한다.
    """
    en = [{
        "title": "Manchester United start new signing Andrey Santos in pre-season loss to Wrexham",
        "summary": "",
    }]
    ko = [{"title": "보카주니어스, 코파리베르타도레스 8강 진출", "summary": ""}]
    filtered_ko, filtered_en = _filter_by_league(ko, en, "CLI")
    assert filtered_en == []
    assert len(filtered_ko) == 1


def test_bare_country_name_excluded_for_brasileirao():
    """
    "브라질"/"brazil" 단독 키워드로 인한 오탐 — 실제 사례: 브라질세리에A
    필터에서 이 키워드 때문에 월드컵 브라질 국가대표팀 뉴스, 개별 선수
    해외 이적 뉴스가 걸렸다. 지금은 이 단독 키워드를 뺐으니, 국가대표/
    월드컵 관련 기사는 브라질세리에A 필터를 통과하면 안 된다.
    """
    ko = [
        {"title": "브라질 대표팀도 폭발했다...\"차라리 로봇 영입해라\" 월드컵에서 우승할...", "summary": ""},
        {"title": "[월드컵 아스트로] 브라질의 '정신적 지주'...카세미루가 증명한 클래...", "summary": ""},
        {"title": "팔메이라스, 코린치안스 꺾고 브라질세리에A 선두 굳혀", "summary": ""},
    ]
    filtered_ko, _ = _filter_by_league(ko, [], "BSA")
    titles = [a["title"] for a in filtered_ko]
    assert titles == ["팔메이라스, 코린치안스 꺾고 브라질세리에A 선두 굳혀"]


def test_zero_matches_stays_empty_no_unfiltered_fallback():
    """
    필터 결과가 0건이면 그냥 0건이어야 한다 — 예전엔 "0건이면 원본을
    그대로 반환"하는 안전장치가 있었는데, 이게 실제로는 필터를 통째로
    무력화하는 구멍이었다(브라질세리에A 헤드라인이 실제로는 "브라질
    세리에A"라는 표현을 잘 안 써서 매칭이 0건이 되면, 완전히 무관한
    기사까지 전부 통과되던 사례). 리그와 전혀 무관한 기사만 주면
    빈 리스트가 나와야 한다.
    """
    ko = [{"title": "오늘 날씨 맑음, 야외 활동하기 좋은 날", "summary": ""}]
    filtered_ko, filtered_en = _filter_by_league(ko, [], "KL1")
    assert filtered_ko == []
    assert filtered_en == []


def test_unmapped_league_code_returns_unfiltered():
    """레지스트리에 없는 리그 코드는 필터 없이 원본 그대로 반환해야 한다."""
    ko = [{"title": "아무 기사", "summary": ""}]
    filtered_ko, _ = _filter_by_league(ko, [], "NOT_A_REAL_LEAGUE")
    assert filtered_ko == ko


def test_bilingual_matching_for_english_articles():
    """
    키워드 목록이 한글만 있으면 영어 기사가 전부 걸러지는 문제가
    있었다 — 영어 클럽명으로도 매칭돼야 한다.
    """
    en = [{"title": "Chelsea sign Rogers in record £117m deal", "summary": ""}]
    filtered_ko, filtered_en = _filter_by_league([], en, "PL")
    assert len(filtered_en) == 1
