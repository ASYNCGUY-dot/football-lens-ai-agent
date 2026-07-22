# -*- coding: utf-8 -*-
"""
test_youtube_key_redaction.py
==============================
week1/collectors/youtube_collector.py의 _redact_key()에 대한 테스트.

실제로 429 Too Many Requests 에러가 나면 requests가 던지는 예외
메시지에 요청 URL 전체(쿼리스트링의 API 키 포함)가 그대로 들어있는데,
이걸 logger.error에 그대로 넘기면 로그 파일에 평문 키가 영구히
남는다 — 실제로 이 로그가 노출된 사고가 있었다(2026-07-22). 로그에
찍기 전에 반드시 마스킹되는지 고정해 둔다.
"""
from youtube_collector import _redact_key


def test_redacts_key_in_middle_of_query_string():
    msg = (
        "429 Client Error: Too Many Requests for url: "
        "https://www.googleapis.com/youtube/v3/search?key=AIzaSyChzLfwp6cwEHGXaWh0KM_jnESfiOvymbw"
        "&q=K%EB%A6%AC%EA%B7%B8&part=snippet"
    )
    redacted = _redact_key(msg)
    assert "AIzaSyChzLfwp6cwEHGXaWh0KM_jnESfiOvymbw" not in redacted
    assert "key=***REDACTED***" in redacted
    # 다른 쿼리 파라미터는 그대로 남아야 진단에 쓸모가 있다
    assert "q=K%EB%A6%AC%EA%B7%B8" in redacted


def test_redacts_key_as_first_query_param():
    msg = "https://api.example.com/x?key=SECRET123&foo=bar"
    redacted = _redact_key(msg)
    assert "SECRET123" not in redacted
    assert "foo=bar" in redacted


def test_no_key_param_left_unchanged():
    msg = "404 Client Error: Not Found for url: https://example.com/rss.xml"
    assert _redact_key(msg) == msg


def test_accepts_exception_object_not_just_string():
    """logger.error(f"...: {e}")처럼 예외 객체를 바로 넘겨도 동작해야 한다."""
    err = ValueError("Too Many Requests for url: https://api.example.com/x?key=AIzaTestKeyValue123&q=test")
    redacted = _redact_key(err)
    assert "AIzaTestKeyValue123" not in redacted
    assert "key=***REDACTED***" in redacted
