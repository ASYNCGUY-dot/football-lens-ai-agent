# -*- coding: utf-8 -*-
"""
token_tracker.py
=================
LLM 호출별 토큰 사용량을 비용으로 환산하는 헬퍼.
각 llm_nodes.py / insight_node.py의 API 호출 성공 지점에서
make_usage_record()를 한 번씩 호출해 state["llm_usage"]에 담는다.

가격 출처 (2026-07-21 확인, 1M 토큰당 USD):
    - claude-3-5-haiku-20241022: $0.80 입력 / $4.00 출력
      https://platform.claude.com/docs/en/about-claude/pricing
    - gpt-4o-mini: $0.15 입력 / $0.60 출력
      https://developers.openai.com/api/docs/pricing
    - gemini-flash-latest: 확정 단가 없음(버전이 시간에 따라 바뀌는 별칭).
      gemini-1.5-flash가 완전히 retired(404)되고, gemini-2.0-flash 계열은
      이 프로젝트의 무료 티어 키에서 429(할당량 0)라 실제로 호출 가능한
      건 이 별칭뿐이었다. 가장 최근 확인된 동급 Flash 최저가
      (gemini-2.5-flash-lite $0.10/$0.40, CloudZero 2026-07 기준)를
      근사치로 사용 — is_estimate=True로 표시해 UI에서 구분한다.

주의: 가격은 자주 바뀐다. 실제 청구 금액과 다를 수 있으므로 참고용이다.
"""

from __future__ import annotations

from datetime import datetime, timezone

# 모델명 -> (input_$/1M, output_$/1M, is_estimate)
PRICING: dict[str, tuple[float, float, bool]] = {
    "claude-3-5-haiku-20241022": (0.80, 4.00, False),
    "gpt-4o-mini": (0.15, 0.60, False),
    "gemini-flash-latest": (0.10, 0.40, True),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> tuple[float, bool]:
    """
    (예상 비용 USD, 추정치 여부)를 반환한다.
    가격표에 없는 모델(예: mock)은 비용 0, is_estimate=True로 처리한다.
    """
    pricing = PRICING.get(model)
    if pricing is None:
        return 0.0, True
    in_price, out_price, is_estimate = pricing
    cost = (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price
    return round(cost, 6), is_estimate


def usage_from_anthropic(response) -> tuple[int, int]:
    """anthropic Message 응답에서 (input_tokens, output_tokens)를 뽑는다."""
    u = getattr(response, "usage", None)
    if u is None:
        return 0, 0
    return getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0


def usage_from_openai(response) -> tuple[int, int]:
    """openai ChatCompletion 응답에서 (prompt_tokens, completion_tokens)를 뽑는다."""
    u = getattr(response, "usage", None)
    if u is None:
        return 0, 0
    return getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0


def usage_from_gemini(response) -> tuple[int, int]:
    """google-generativeai 응답에서 (prompt_token_count, candidates_token_count)를 뽑는다."""
    u = getattr(response, "usage_metadata", None)
    if u is None:
        return 0, 0
    return getattr(u, "prompt_token_count", 0) or 0, getattr(u, "candidates_token_count", 0) or 0


def make_usage_record(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    node: str = "",
) -> dict:
    """
    state["llm_usage"]에 append할 사용량 1건을 만든다.

    Parameters
    ----------
    provider : str
        "anthropic" / "openai" / "google"
    model : str
        실제 호출한 모델명
    input_tokens, output_tokens : int
        API 응답의 usage 필드에서 뽑아온 값
    node : str
        어느 노드에서 호출했는지 (로그/디버깅용, 예: "summarize_korean_node")
    """
    cost_usd, is_estimate = estimate_cost(model, input_tokens, output_tokens)
    return {
        "provider": provider,
        "model": model,
        "node": node,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "is_estimate": is_estimate,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def summarize_usage(usage_list: list[dict]) -> dict:
    """
    llm_usage 리스트를 요약한다 (사이드바 표시용).

    Returns
    -------
    dict
        {"total_cost_usd", "total_input_tokens", "total_output_tokens",
         "call_count", "has_estimate", "by_provider": {provider: cost}}
    """
    total_cost = 0.0
    total_in = 0
    total_out = 0
    has_estimate = False
    by_provider: dict[str, float] = {}

    for u in usage_list or []:
        cost = u.get("cost_usd", 0.0)
        total_cost += cost
        total_in += u.get("input_tokens", 0)
        total_out += u.get("output_tokens", 0)
        has_estimate = has_estimate or u.get("is_estimate", False)
        provider = u.get("provider", "unknown")
        by_provider[provider] = by_provider.get(provider, 0.0) + cost

    return {
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "call_count": len(usage_list or []),
        "has_estimate": has_estimate,
        "by_provider": {k: round(v, 6) for k, v in by_provider.items()},
    }
