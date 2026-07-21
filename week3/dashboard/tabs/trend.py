# -*- coding: utf-8 -*-
"""tabs/trend.py — 키워드 트렌드 · 감정 분포 탭."""
import streamlit as st

from components import _html, espn_section


def _compute_stats(data: dict) -> dict:
    """비교에 쓸 요약 지표(기사 수, 평균 감정, 이적루머 건수)를 계산한다."""
    articles = data.get("korean_articles", []) + data.get("english_articles", [])
    sentiments = data.get("article_sentiments", [])
    avg_sentiment = (
        sum(s.get("sentiment_score", 0) for s in sentiments) / len(sentiments)
        if sentiments else None
    )
    return {
        "article_count": len(articles),
        "avg_sentiment": avg_sentiment,
        "rumor_count": len(data.get("transfer_rumors", [])),
        "saved_at": data.get("_saved_at"),
    }


def _render_history_comparison(result: dict, league: str) -> None:
    """
    지금 결과와 저장된 과거 결과를 비교한다. 같은 리그의 과거 실행이
    없으면 조용히 아무것도 그리지 않는다.
    """
    if not league:
        return

    from week3.storage.results_store import list_results, load_result

    past_entries = [
        e for e in list_results(limit=50)
        if e.get("league") == league and e.get("run_id") != result.get("run_id")
    ]
    if not past_entries:
        return

    espn_section("📊", "지난 분석과 비교")

    options = {
        f"{e['saved_at'][:16].replace('T', ' ')} 실행" if e.get("saved_at") else e["run_id"]: e["file"]
        for e in past_entries
    }
    choice = st.selectbox("비교할 과거 실행", options=list(options.keys()), key="history_compare_select")
    past_data = load_result(options[choice])
    if not past_data:
        st.info("과거 결과를 불러오지 못했습니다.")
        return

    now_stats = _compute_stats(result)
    past_stats = _compute_stats(past_data)

    def _delta_html(now_val, past_val, unit="", higher_is=None):
        if now_val is None or past_val is None:
            return '<span style="color:#AAA;font-size:11px;">비교 불가</span>'
        diff = now_val - past_val
        if abs(diff) < 0.001:
            return '<span style="color:#888;font-size:12px;">변화 없음</span>'
        arrow = "▲" if diff > 0 else "▼"
        color = "#888"
        if higher_is == "good":
            color = "#2E7D32" if diff > 0 else "#CC0000"
        elif higher_is == "bad":
            color = "#CC0000" if diff > 0 else "#2E7D32"
        sign = "+" if diff > 0 else ""
        return f'<span style="color:{color};font-size:12px;font-weight:700;">{arrow} {sign}{diff:.2f}{unit}</span>'

    col1, col2, col3 = st.columns(3)
    with col1:
        delta = _delta_html(now_stats["article_count"], past_stats["article_count"], unit="건")
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#1A1A1A;">{now_stats['article_count']}건</div>
<div style="font-size:11px;color:#888;margin-bottom:4px;">수집 기사 (이전 {past_stats['article_count']}건)</div>
{delta}
</div>
""")
    with col2:
        now_s, past_s = now_stats["avg_sentiment"], past_stats["avg_sentiment"]
        delta = _delta_html(now_s, past_s, higher_is="good")
        now_str = f"{now_s:+.2f}" if now_s is not None else "—"
        past_str = f"{past_s:+.2f}" if past_s is not None else "—"
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#1A1A1A;">{now_str}</div>
<div style="font-size:11px;color:#888;margin-bottom:4px;">평균 감정 (이전 {past_str})</div>
{delta}
</div>
""")
    with col3:
        delta = _delta_html(now_stats["rumor_count"], past_stats["rumor_count"], unit="건", higher_is=None)
        _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#1A1A1A;">{now_stats['rumor_count']}건</div>
<div style="font-size:11px;color:#888;margin-bottom:4px;">이적 루머 (이전 {past_stats['rumor_count']}건)</div>
{delta}
</div>
""")
    st.markdown("<br>", unsafe_allow_html=True)


def render_trend_tab(result: dict, league: str = None):
    """트렌드 차트 탭 — 키워드 언급 빈도 + 감정 분포 + 지난 분석과 비교."""
    all_articles = (
        result.get("korean_articles", []) + result.get("english_articles", [])
    )
    sentiments = result.get("article_sentiments", [])

    if not result:
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">📈</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">트렌드 데이터 없음</div>
<div style="font-size:14px;color:#888;margin-top:8px;">분석을 실행하면 키워드 트렌드 차트가 표시됩니다</div>
</div>
""")
        return

    _render_history_comparison(result, league)

    try:
        import pandas as pd
        import plotly.graph_objects as go
        import plotly.express as px
        from collections import Counter

        # ── 1. 키워드 빈도 차트 ──────────────────────────────
        espn_section("📊", "Keyword Frequency")
        st.caption(
            "오늘 수집된 기사 제목·요약에 아래 고정 키워드(선수명·클럽명 등)가 "
            "몇 번 등장했는지 센 것입니다. 실시간 트렌드가 아니라 미리 정해둔 "
            "키워드 목록 기준이라, 목록에 없는 이슈는 잡히지 않습니다."
        )
        TRACK_KEYWORDS = [
            "손흥민", "이강인", "황희찬", "김민재", "홀란드", "살라",
            "엠바페", "벨링엄", "야말", "케인", "이적", "챔피언스리그",
            "K리그", "EPL", "맨시티", "리버풀", "아스날",
        ]
        kw_counts = Counter()
        for a in all_articles:
            text = f"{a.get('title','')} {a.get('summary','')}".lower()
            for kw in TRACK_KEYWORDS:
                if kw.lower() in text:
                    kw_counts[kw] += 1

        if kw_counts:
            kw_df = pd.DataFrame(
                [(k, v) for k, v in kw_counts.most_common(15)],
                columns=["키워드", "언급 횟수"],
            )
            fig_kw = px.bar(
                kw_df, x="언급 횟수", y="키워드", orientation="h",
                color="언급 횟수",
                color_continuous_scale=[[0, "#FFCCCC"], [1, "#CC0000"]],
                text="언급 횟수",
            )
            fig_kw.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                font=dict(color="#1A1A1A", family="Oswald"),
                yaxis=dict(autorange="reversed", gridcolor="#EEEEEE", title=None),
                xaxis=dict(gridcolor="#EEEEEE", title="언급 횟수"),
                coloraxis_showscale=False,
                margin=dict(t=10, b=10, l=10, r=10), height=380,
            )
            fig_kw.update_traces(textposition="outside", textfont=dict(color="#CC0000"))
            st.plotly_chart(fig_kw, use_container_width=True)
        else:
            st.info("키워드 데이터 없음")

        # ── 2. 감정 분포 도넛 차트 ──────────────────────────
        if sentiments:
            espn_section("😊", "Sentiment Distribution")
            st.caption(
                "수집된 기사 전체를 AI가 긍정/중립/부정으로 분류한 비율입니다. "
                "'긍정'은 응원할 만한 좋은 소식(승리, 활약 등), '부정'은 안 좋은 "
                "소식(패배, 부상, 논란 등)에 가깝다는 뜻이며, 특정 팀 편향을 "
                "의미하지는 않습니다."
            )
            col1, col2 = st.columns([1, 2])

            label_counts = Counter(s.get("sentiment_label", "중립") for s in sentiments)
            labels  = list(label_counts.keys())
            values  = list(label_counts.values())
            colors  = {"긍정": "#2E7D32", "중립": "#888888", "부정": "#CC0000"}
            chart_colors = [colors.get(l, "#AAAAAA") for l in labels]

            with col1:
                fig_donut = go.Figure(go.Pie(
                    labels=labels, values=values,
                    hole=0.6,
                    marker=dict(colors=chart_colors, line=dict(color="#FFF", width=2)),
                    textinfo="label+percent",
                    textfont=dict(family="Oswald", size=12),
                ))
                fig_donut.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=260,
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            with col2:
                # 감정별 상위 기사
                for label in ["긍정", "중립", "부정"]:
                    top = [s for s in sentiments if s.get("sentiment_label") == label]
                    top = sorted(top, key=lambda x: abs(x.get("sentiment_score", 0)), reverse=True)
                    cnt = label_counts.get(label, 0)
                    color = colors.get(label, "#888")
                    _html(f'<div style="font-family:Oswald,sans-serif;font-size:12px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:0.5px;margin:8px 0 4px;">{label} ({cnt}건)</div>')
                    for s in top[:2]:
                        t = (s.get("title") or "")[:55]
                        sc = s.get("sentiment_score", 0)
                        _html(f'<div style="font-size:12px;color:#555;padding:3px 0;border-left:3px solid {color};padding-left:8px;margin-bottom:4px;">{t} <span style="color:{color};font-weight:700;">{sc:+.2f}</span></div>')

        # ── 3. 날짜별 기사 수 라인 차트 ──────────────────────
        if all_articles:
            espn_section("📅", "Daily Article Volume")
            st.caption(
                "기사 발행일(published_at) 기준 날짜별 기사 수입니다. 뉴스 수집이 "
                "최근 기사 위주라 보통 최근 날짜로 갈수록 급격히 늘어나는 모양이 "
                "정상입니다 — 오래된 날짜에 기사가 거의 없는 건 버그가 아니라 "
                "수집 방식(최신 뉴스 중심) 때문입니다."
            )
            date_counts = Counter()
            for a in all_articles:
                pub = a.get("published_at")
                if pub:
                    try:
                        date_counts[str(pub)[:10]] += 1
                    except Exception:
                        pass
            if date_counts:
                date_df = pd.DataFrame(
                    sorted(date_counts.items()),
                    columns=["날짜", "기사 수"],
                )
                fig_line = px.line(
                    date_df, x="날짜", y="기사 수",
                    markers=True,
                    color_discrete_sequence=["#CC0000"],
                )
                fig_line.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                    font=dict(color="#1A1A1A", family="Oswald"),
                    xaxis=dict(gridcolor="#EEEEEE", title=None),
                    yaxis=dict(gridcolor="#EEEEEE", title="기사 수"),
                    margin=dict(t=10, b=10, l=10, r=10), height=240,
                )
                fig_line.update_traces(
                    line=dict(width=2.5),
                    marker=dict(size=7, color="#CC0000"),
                )
                st.plotly_chart(fig_line, use_container_width=True)

    except ImportError:
        st.warning("트렌드 차트를 보려면 plotly와 pandas가 필요합니다: `pip install plotly pandas`")
    except Exception as e:
        st.error(f"트렌드 차트 오류: {e}")
