# -*- coding: utf-8 -*-
"""tabs/trend.py — 키워드 트렌드 · 감정 분포 탭."""
import streamlit as st

from components import _html, espn_section


def render_trend_tab(result: dict):
    """트렌드 차트 탭 — 키워드 언급 빈도 + 감정 분포."""
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

    try:
        import pandas as pd
        import plotly.graph_objects as go
        import plotly.express as px
        from collections import Counter

        # ── 1. 키워드 빈도 차트 ──────────────────────────────
        espn_section("📊", "Keyword Frequency")
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
