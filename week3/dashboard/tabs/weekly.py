# -*- coding: utf-8 -*-
"""tabs/weekly.py — 주간 보고서 탭."""
from collections import Counter
from datetime import datetime

import streamlit as st

from constants import IMG_TROPHY, _LEAGUE_DISPLAY
from components import _html, espn_section
from season_info import render_off_season_notice


def compute_weekly_highlights(result: dict) -> dict:
    """
    주간 보고서 전용 요약 지표를 계산한다 — 이미 파이프라인이 만들어둔
    데이터(article_sentiments, korean_summary/english_summary의
    key_topics, transfer_rumors)만 재활용하므로 추가 LLM/API 호출이
    없다.

    예전엔 일간 탭과 주간 탭이 완전히 같은 final_report 텍스트만
    보여줘서, 주간 탭에 들어가도 "주간"만의 콘텐츠가 하나도 없었다
    (2026-07-22, 사용자가 주간 탭 스크린샷으로 지적).

    Returns
    -------
    dict
        {article_count, ko_count, en_count, avg_sentiment, tone_label,
         positive_pct, negative_pct, hot_topics, rumor_count,
         top_rumors, busiest_day, busiest_day_count}
    """
    ko_articles = result.get("korean_articles", [])
    en_articles = result.get("english_articles", [])
    all_articles = ko_articles + en_articles
    sentiments = result.get("article_sentiments", [])

    avg_sentiment = (
        sum(s.get("sentiment_score", 0) for s in sentiments) / len(sentiments)
        if sentiments else None
    )
    label_counts = Counter(s.get("sentiment_label", "중립") for s in sentiments)
    total_sent = len(sentiments) or 1  # 0 나눗셈 방지
    positive_pct = round(label_counts.get("긍정", 0) / total_sent * 100)
    negative_pct = round(label_counts.get("부정", 0) / total_sent * 100)

    if avg_sentiment is None:
        tone_label = "감정 분석 데이터 없음"
    elif avg_sentiment > 0.15:
        tone_label = "전반적으로 긍정적인 한 주였습니다"
    elif avg_sentiment < -0.15:
        tone_label = "다소 무거운 소식이 많았던 한 주입니다"
    else:
        tone_label = "특별히 치우치지 않은 무난한 한 주였습니다"

    # 핫토픽 — 국내/해외 요약이 이미 뽑아둔 key_topics를 합쳐 중복 제거
    ko_topics = result.get("korean_summary", {}).get("key_topics", []) or []
    en_topics = result.get("english_summary", {}).get("key_topics", []) or []
    seen, hot_topics = set(), []
    for t in ko_topics + en_topics:
        if t and t not in seen:
            seen.add(t)
            hot_topics.append(t)

    rumors = result.get("transfer_rumors", [])
    top_rumors = sorted(
        rumors, key=lambda r: str(r.get("published_at", "")), reverse=True
    )[:3]

    # 날짜별 기사량 — 가장 기사가 많았던 날 하루만 짚어준다(전체 추이
    # 그래프는 📈 트렌드 탭에 이미 있어서 중복하지 않음).
    date_counts = Counter()
    for a in all_articles:
        pub = a.get("published_at")
        if pub:
            date_counts[str(pub)[:10]] += 1
    busiest_day, busiest_day_count = (None, 0)
    if date_counts:
        busiest_day, busiest_day_count = date_counts.most_common(1)[0]

    return {
        "article_count": len(all_articles),
        "ko_count": len(ko_articles),
        "en_count": len(en_articles),
        "avg_sentiment": avg_sentiment,
        "tone_label": tone_label,
        "positive_pct": positive_pct,
        "negative_pct": negative_pct,
        "hot_topics": hot_topics[:8],
        "rumor_count": len(rumors),
        "top_rumors": top_rumors,
        "busiest_day": busiest_day,
        "busiest_day_count": busiest_day_count,
    }


def _render_weekly_highlights(result: dict) -> None:
    """이번 기간 하이라이트 카드 — final_report 본문보다 위에 렌더링한다."""
    h = compute_weekly_highlights(result)
    if h["article_count"] == 0:
        return

    espn_section("📌", "이번 기간 하이라이트")

    col1, col2, col3 = st.columns(3)
    with col1:
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #CC0000;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:26px;font-weight:700;color:#CC0000;">{h['article_count']}건</div>
<div style="font-size:12px;color:#888;">수집 기사 (국내 {h['ko_count']} · 해외 {h['en_count']})</div>
</div>
""")
    with col2:
        sc = h["avg_sentiment"]
        sc_str = f"{sc:+.2f}" if sc is not None else "—"
        sc_color = "#2E7D32" if (sc or 0) > 0.1 else ("#CC0000" if (sc or 0) < -0.1 else "#888")
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid {sc_color};padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:26px;font-weight:700;color:{sc_color};">{sc_str}</div>
<div style="font-size:12px;color:#888;">평균 감정 (긍정 {h['positive_pct']}% · 부정 {h['negative_pct']}%)</div>
</div>
""")
    with col3:
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;border-top:3px solid #E65C00;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:26px;font-weight:700;color:#E65C00;">{h['rumor_count']}건</div>
<div style="font-size:12px;color:#888;">이적 소식</div>
</div>
""")

    _html(f'<div style="font-size:13px;color:#555;margin:12px 0 4px;">💬 {h["tone_label"]}</div>')

    if h["hot_topics"]:
        chips = " ".join(
            f'<span style="background:#1A1A1A;color:#FFF;border-radius:2px;padding:3px 9px;font-size:11px;font-family:Oswald,sans-serif;margin-right:4px;">#{t}</span>'
            for t in h["hot_topics"]
        )
        _html(f'<div style="margin:8px 0;">{chips}</div>')

    if h["busiest_day"]:
        _html(f'<div style="font-size:12px;color:#888;margin-bottom:8px;">📅 가장 기사가 많았던 날: {h["busiest_day"]} ({h["busiest_day_count"]}건)</div>')

    if h["top_rumors"]:
        st.caption("🔄 최신 이적 소식")
        for r in h["top_rumors"]:
            title = (r.get("title") or "")[:70]
            url = r.get("url", "#")
            _html(f'<div style="font-size:13px;padding:4px 0;"><a href="{url}" target="_blank" style="color:#1A1A1A;text-decoration:none;">▸ {title}</a></div>')

    st.markdown("<br>", unsafe_allow_html=True)


def render_weekly_report(result: dict, league: str = None):
    """
    주간 보고서 탭을 렌더링합니다.
    league가 지정되면 해당 리그/대회 이름이 섹션 헤더에 표시됩니다.
    """
    league_display = _LEAGUE_DISPLAY.get(league, league or "⚽ 축구")

    if render_off_season_notice(league):
        return

    if not result:
        _html(f"""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<img src="{IMG_TROPHY}" style="width:100%;height:120px;object-fit:cover;border-radius:3px;margin-bottom:16px;opacity:0.5;" alt="trophy">
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">주간 보고서 없음</div>
<div style="font-size:14px;color:#888;">기간을 <strong style="color:#CC0000;">7일 이상</strong>으로 설정 후 분석을 실행하세요</div>
</div>
""")
        return

    espn_section("📊", f"Weekly Report — {league_display}")

    _render_weekly_highlights(result)

    final_report = result.get("final_report", "")
    if final_report:
        _html('<div style="background:#FFFFFF;border:1px solid #E5E5E5;border-radius:4px;padding:28px 32px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">')
        st.markdown(final_report)
        _html('</div>')
        st.download_button(
            label="📥 보고서 다운로드 (.md)",
            data=final_report,
            file_name=f"football_lens_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )
    else:
        st.info("보고서 데이터가 없습니다.")
