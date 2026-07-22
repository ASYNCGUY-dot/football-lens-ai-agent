# -*- coding: utf-8 -*-
"""tabs/rumors.py — 이적 루머 탭."""
import streamlit as st

from components import _html, espn_section, render_sentiment_badge
from utils import _filter_articles_by_league


def render_transfer_rumors_tab(result: dict, league: str = None):
    """
    이적 루머 트래커 탭 — 선택 리그 관련 이적 소식만 표시합니다.

    예전엔 리그 무관하게 전체를 다 보여줬는데, K리그1을 선택해도 EPL/MLS
    이적설이 계속 섞여 나와 혼란을 준다는 피드백에 따라 다른 탭들과
    동일하게 리그 필터를 적용했다.
    """

    # ── 이적 관련 키워드 (한/영) ──────────────────────────────
    TRANSFER_KW_KO = [
        "이적", "영입", "이적설", "영입설", "계약", "재계약", "협상", "제안", "입단",
        "방출", "임대", "이적료", "관심", "타진", "영입 목표", "FA",
    ]
    TRANSFER_KW_EN = [
        "transfer", "signing", "sign", "linked", "target", "bid", "deal",
        "contract", "loan", "fee", "move", "departure", "arrival", "negotiate",
        "reported", "interest", "offer",
    ]

    # 1) 파이프라인이 제공한 루머 기사 우선 사용
    rumors = list(result.get("transfer_rumors", []))

    # 2) 파이프라인 루머가 비어 있으면 모든 기사에서 직접 키워드 필터
    if not rumors:
        all_articles = (
            result.get("korean_articles", []) + result.get("english_articles", [])
        )
        sentiments_by_id = {
            s.get("article_id", ""): s
            for s in result.get("article_sentiments", [])
        }
        for a in all_articles:
            text = f"{a.get('title', '')} {a.get('summary', '')}".lower()
            ko_hit = any(kw in text for kw in TRANSFER_KW_KO)
            en_hit = any(kw in text for kw in TRANSFER_KW_EN)
            if ko_hit or en_hit:
                merged = dict(a)
                merged["sentiment"] = sentiments_by_id.get(a.get("article_id", ""), {})
                rumors.append(merged)

    # 최신순 정렬
    rumors.sort(key=lambda x: str(x.get("published_at", "")), reverse=True)

    # 선택 리그 관련 이적 소식만 남긴다.
    if league:
        rumors = _filter_articles_by_league(rumors, league)

    if not rumors:
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">🔄</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">이적 소식 없음</div>
<div style="font-size:14px;color:#888;">먼저 <strong style="color:#CC0000;">⚡ 분석 실행</strong>으로 데이터를 수집하세요</div>
</div>
""")
        return

    espn_section("🔄", "Transfer Rumors — 최신 이적 소식", len(rumors))
    st.caption(
        "카드 우측 상단 점수는 '이적 성사 가능성'이 아니라 기사 전체의 AI 감정 "
        "분석 점수(-1.0 매우 부정 ~ +1.0 매우 긍정)를 그대로 가져온 것입니다. "
        "이적설 자체의 신빙성과는 무관하며, 단지 기사가 어떤 톤으로 쓰였는지를 나타냅니다."
    )

    # 선수별 그룹화
    player_rumors: dict[str, list] = {}
    for r in rumors:
        sent = r.get("sentiment", {})
        players = sent.get("rumor_players", [])
        if players:
            for p in players:
                player_rumors.setdefault(p, []).append(r)
        else:
            player_rumors.setdefault("기타", []).append(r)

    # 선수 필터
    all_players = list(player_rumors.keys())
    if all_players:
        selected_player = st.selectbox(
            "선수 필터",
            options=["전체"] + all_players,
            label_visibility="collapsed",
        )
        if selected_player != "전체":
            filtered_rumors = player_rumors.get(selected_player, [])
        else:
            filtered_rumors = rumors
    else:
        filtered_rumors = rumors

    # 루머 카드
    for r in filtered_rumors[:20]:
        sent = r.get("sentiment", {})
        score = sent.get("sentiment_score", 0)
        label = sent.get("sentiment_label", "중립")
        players = sent.get("rumor_players", [])
        clubs   = sent.get("rumor_clubs", [])

        badge_html = render_sentiment_badge(score, label)
        player_chips = " ".join(
            f'<span style="background:#1A1A1A;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;margin-right:3px;">👤 {p}</span>'
            for p in players[:3]
        )
        club_chips = " ".join(
            f'<span style="background:#003399;color:#FFF;border-radius:2px;padding:2px 7px;font-size:10px;font-family:Oswald,sans-serif;margin-right:3px;">🏟️ {c}</span>'
            for c in clubs[:3]
        )
        pub = r.get("published_at", "")
        pub_str = str(pub)[:10] if pub else ""
        src = r.get("source_name", "")
        title = (r.get("title") or "")[:90]
        url   = r.get("url", "#")
        summary = (r.get("summary") or "")[:120]

        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-left:4px solid #CC0000;padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
<a href="{url}" target="_blank" style="font-family:'Oswald',sans-serif;font-size:15px;font-weight:700;color:#1A1A1A;text-decoration:none;flex:1;margin-right:12px;line-height:1.35;">{title}</a>
{badge_html}
</div>
<div style="font-size:11px;color:#888;margin-bottom:8px;">{src} · {pub_str}</div>
<div style="font-size:13px;color:#555;margin-bottom:8px;">{summary}</div>
<div style="display:flex;flex-wrap:wrap;gap:4px;">{player_chips}{club_chips}</div>
</div>
""")
