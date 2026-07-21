# -*- coding: utf-8 -*-
"""
pdf_report.py — Football Lens 주간 PDF 리포트 생성.

디자인은 Artifact로 미리 보여준 C안(모던 매거진, 다크+오렌지 포인트)을
fpdf2로 구현한 것이다. 목업의 CSS 그라디언트/블러/반투명은 fpdf2가
지원하지 않아 단색 카드로 근사했다 — 레이아웃과 섹션 구성은 동일하다.

SECTIONS 리스트는 각 섹션에 min_tier를 붙여 데이터 기반으로 정의했다.
지금은 프로토타입이라 PROTOTYPE_TIER로 전부 노출하지만, 나중에 구독
등급을 실제로 나누게 되면 generate_pdf_report(..., user_tier=N) 호출로
일부 섹션만 건너뛰게 만들면 된다.

모든 섹션은 실제 result dict에 데이터가 없으면 조용히 채워 넣지 않고
"데이터 없음" 계열의 문구로 대체한다 — 이 프로젝트에서 가짜/목업 데이터를
그대로 보여줬다가 여러 번 지적받은 적이 있어서, PDF도 같은 원칙을 따른다.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime

from fpdf import FPDF

FONT_DIR = "C:/Windows/Fonts"
FONT_REGULAR = os.path.join(FONT_DIR, "malgun.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "malgunbd.ttf")

# ── 색상 팔레트 (목업 C안 근사, RGB 0-255) ────────────────────────
BG = (16, 19, 28)
CARD = (28, 32, 45)
CARD_LINE = (48, 52, 66)
INK = (242, 241, 238)
MUTED = (154, 158, 176)
MUTED2 = (109, 113, 130)
ACCENT = (255, 138, 61)
ACCENT2 = (255, 77, 109)
POS = (126, 211, 137)
NEG = (255, 92, 114)

PAGE_W, PAGE_H = 210, 297
MARGIN = 15
CONTENT_W = PAGE_W - 2 * MARGIN

# ── 섹션 정의 (데이터 기반, 등급 게이팅 대비) ─────────────────────
SECTIONS = [
    {"id": "hero_summary", "title": "핵심 요약", "min_tier": 0},
    {"id": "headlines", "title": "헤드라인 뉴스", "min_tier": 0},
    {"id": "standings", "title": "순위표", "min_tier": 0},
    {"id": "top_scorers", "title": "득점왕", "min_tier": 0},
    {"id": "predictions", "title": "경기 예측", "min_tier": 1},
    {"id": "transfer_rumors", "title": "이적 루머 상세", "min_tier": 1},
    {"id": "spotlight_players", "title": "주목할 선수", "min_tier": 1},
]
PROTOTYPE_TIER = 99  # 지금은 모든 섹션 노출(최고 등급 프로토타입)


def _enabled(section_id: str, user_tier: int) -> bool:
    sec = next((s for s in SECTIONS if s["id"] == section_id), None)
    return bool(sec) and user_tier >= sec["min_tier"]


# ── 데이터 가공 헬퍼 ────────────────────────────────────────────

def _all_articles(result: dict) -> list:
    return result.get("korean_articles", []) + result.get("english_articles", [])


def _sentiments_by_id(result: dict) -> dict:
    return {s.get("article_id", ""): s for s in result.get("article_sentiments", [])}


def _avg_sentiment(sentiments: list) -> float | None:
    if not sentiments:
        return None
    return sum(s.get("sentiment_score", 0) for s in sentiments) / len(sentiments)


def _daily_sentiment_trend(articles: list, sentiments_by_id: dict, days: int = 7) -> list[tuple[str, float]]:
    """기사 published_at + article_sentiments를 article_id로 조인해 날짜별 평균 감정을 계산한다."""
    buckets: dict[str, list[float]] = defaultdict(list)
    for a in articles:
        aid = a.get("article_id")
        pub = a.get("published_at")
        if not pub or aid not in sentiments_by_id:
            continue
        buckets[str(pub)[:10]].append(sentiments_by_id[aid].get("sentiment_score", 0))
    dates = sorted(buckets.keys())[-days:]
    return [(d, sum(buckets[d]) / len(buckets[d])) for d in dates]


def _top_headlines(articles: list, sentiments_by_id: dict, n: int = 9) -> list[dict]:
    def _pub_key(a):
        return str(a.get("published_at") or "")

    ranked = sorted(articles, key=_pub_key, reverse=True)
    out = []
    for a in ranked[:n]:
        sent = sentiments_by_id.get(a.get("article_id", ""), {})
        out.append({
            "title": a.get("title", ""),
            "source": a.get("source_name", ""),
            "date": str(a.get("published_at", ""))[:10],
            "score": sent.get("sentiment_score", 0.0),
            "label": sent.get("sentiment_label", "중립"),
        })
    return out


def _rumor_tag(published_at: str) -> str:
    try:
        pub = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
        age_days = (datetime.now(pub.tzinfo) - pub).days
    except Exception:
        return "RUMOR"
    if age_days <= 1:
        return "HOT"
    if age_days <= 4:
        return "UPDATE"
    return "RUMOR"


def _sent_color(label: str):
    return POS if label == "긍정" else (NEG if label == "부정" else MUTED)


def _build_headline(standings: list, league_name: str) -> str:
    """순위표 1·2위 승점차를 기준으로 표지 헤드라인을 만든다. 데이터 없으면 일반 문구로 대체."""
    if len(standings) >= 2:
        top1, top2 = standings[0], standings[1]
        gap = abs((top1.get("points") or 0) - (top2.get("points") or 0))
        if gap <= 5:
            return f"{top1.get('team_name','1위')} vs {top2.get('team_name','2위')},\n승점 {gap}점 차 접전"
        return f"{top1.get('team_name','1위')} 독주,\n2위와 승점 {gap}점 차"
    return f"{league_name}\n위클리 리포트"


class _ReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.add_font("Malgun", "", FONT_REGULAR)
        self.add_font("Malgun", "B", FONT_BOLD)

    def bg(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, style="F")

    def pagehead(self, page_no: int):
        self.set_xy(MARGIN, 12)
        self.set_font("Malgun", "", 7.5)
        self.set_text_color(*MUTED2)
        self.cell(CONTENT_W / 2, 5, "FOOTBALL LENS  ·  WEEKLY REPORT", align="L")
        self.set_xy(PAGE_W - MARGIN - CONTENT_W / 2, 12)
        self.cell(CONTENT_W / 2, 5, f"{page_no:02d} / 03", align="R")
        self.set_y(20)

    def section_h(self, text: str):
        y = self.get_y() + 2
        self.set_xy(MARGIN, y)
        self.set_font("Malgun", "B", 9)
        self.set_text_color(*ACCENT)
        w = self.get_string_width(text) + 2
        self.cell(w, 5, text.upper())
        self.set_draw_color(*CARD_LINE)
        self.line(MARGIN + w + 2, y + 2.5, PAGE_W - MARGIN, y + 2.5)
        self.set_y(y + 7)

    def body_text(self, text: str, size=8, color=(199, 202, 214), line_h=3.9):
        self.set_x(MARGIN)
        self.set_font("Malgun", "", size)
        self.set_text_color(*color)
        self.multi_cell(CONTENT_W, line_h, text)
        self.ln(2)

    def foot(self, text: str):
        self.set_xy(MARGIN, PAGE_H - 16)
        self.set_draw_color(*CARD_LINE)
        self.line(MARGIN, PAGE_H - 18, PAGE_W - MARGIN, PAGE_H - 18)
        self.set_font("Malgun", "", 6.3)
        self.set_text_color(*MUTED2)
        self.multi_cell(CONTENT_W, 3.2, text, align="C")

    def card(self, x, y, w, h, radius=2.5):
        self.set_fill_color(*CARD)
        self.set_draw_color(*CARD_LINE)
        try:
            self.rect(x, y, w, h, style="FD", round_corners=True, corner_radius=radius)
        except TypeError:
            self.rect(x, y, w, h, style="FD")

    def draw_table(self, headers, rows, col_widths, aligns=None, header_size=6.3, body_size=7.3):
        aligns = aligns or ["L"] * len(headers)
        x0, y = MARGIN, self.get_y()
        self.set_xy(x0, y)
        self.set_font("Malgun", "B", header_size)
        self.set_text_color(*MUTED)
        for w, h, a in zip(col_widths, headers, aligns):
            self.cell(w, 5, h, align=a)
        self.ln(5)
        self.set_draw_color(*CARD_LINE)
        self.line(x0, self.get_y(), x0 + sum(col_widths), self.get_y())
        self.ln(0.8)
        self.set_font("Malgun", "", body_size)
        self.set_text_color(*(215, 217, 226))
        for row in rows:
            self.set_x(x0)
            for w, val, a in zip(col_widths, row, aligns):
                self.cell(w, 5.2, str(val), align=a)
            self.ln(5.2)
            self.set_draw_color(*(46, 49, 62))
            self.line(x0, self.get_y(), x0 + sum(col_widths), self.get_y())
            self.ln(0.6)
        self.ln(3)


# ── 페이지별 렌더러 ─────────────────────────────────────────────

def _page1(pdf: _ReportPDF, result: dict, league_name: str, articles: list,
           sentiments_by_id: dict, standings: list, transfer_rumors: list):
    pdf.add_page()
    pdf.bg()
    pdf.pagehead(1)

    pdf.set_xy(MARGIN, pdf.get_y())
    pdf.set_font("Malgun", "B", 8)
    pdf.set_text_color(*ACCENT)
    date_range = f"{datetime.now().strftime('%Y.%m.%d')} 기준"
    pdf.cell(0, 4, f"WEEKLY DROP  ·  {league_name.upper()}")
    pdf.ln(6)

    headline = _build_headline(standings, league_name)
    pdf.set_x(MARGIN)
    pdf.set_font("Malgun", "B", 22)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W, 8.5, headline)
    pdf.ln(1)

    n_ko = len(result.get("korean_articles", []))
    n_en = len(result.get("english_articles", []))
    n_sent = len(result.get("article_sentiments", []))
    pdf.body_text(
        f"{date_range}  ·  기사 {n_ko + n_en}건 분석  ·  감정분석 완료 {n_sent}건",
        size=8, color=MUTED,
    )

    avg = _avg_sentiment(list(sentiments_by_id.values()))
    pdf.set_x(MARGIN)
    pdf.set_font("Malgun", "B", 34)
    pdf.set_text_color(*ACCENT)
    pdf.cell(38, 14, (f"{avg:+.2f}" if avg is not None else "N/A"))
    pdf.set_xy(MARGIN + 40, pdf.get_y() + 2)
    pdf.set_font("Malgun", "", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(60, 3.6, "뉴스 감정지수\n(수집 기간 평균)")
    pdf.set_y(pdf.get_y() + 4)

    box_y = pdf.get_y()
    box_h = 20
    pdf.card(MARGIN, box_y, CONTENT_W, box_h)
    pdf.set_xy(MARGIN + 4, box_y + 3)
    pdf.set_font("Malgun", "B", 7.6)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 4, "뉴스 감정지수란?")
    pdf.set_xy(MARGIN + 4, box_y + 7.2)
    pdf.set_font("Malgun", "", 7.3)
    pdf.set_text_color(*(217, 212, 200))
    pdf.multi_cell(CONTENT_W - 8, 3.5,
        "AI가 수집된 기사 하나하나의 논조를 -1.0(매우 부정)부터 +1.0(매우 긍정) 사이로 채점해 "
        "평균 낸 값입니다. 승리·활약처럼 긍정적으로 보도된 기사가 많을수록 올라가고, 부상·패배·"
        "논란이 많을수록 내려갑니다. 팀 전력이나 실제 성적을 직접 의미하지는 않으며, 이번 기간 "
        "여론 분위기에 가깝습니다.")
    pdf.set_y(box_y + box_h + 5)

    # 통계 타일 3개
    tile_y = pdf.get_y()
    tile_h = 16
    gap = 4
    tile_w = (CONTENT_W - 2 * gap) / 3
    from prediction_tracker import get_accuracy_summary
    acc = get_accuracy_summary()
    acc_txt = f"{acc['accuracy_pct']}%" if acc["total"] > 0 else "N/A"
    gap_txt = "N/A"
    if len(standings) >= 2:
        gap_txt = f"{abs((standings[0].get('points') or 0) - (standings[1].get('points') or 0))}pt"
    tiles = [
        (str(len(transfer_rumors)), "이적 루머"),
        (acc_txt, "예측 적중률"),
        (gap_txt, "1·2위 격차"),
    ]
    for i, (val, cap) in enumerate(tiles):
        x = MARGIN + i * (tile_w + gap)
        pdf.card(x, tile_y, tile_w, tile_h)
        pdf.set_xy(x + 3, tile_y + 2.5)
        pdf.set_font("Malgun", "B", 13)
        pdf.set_text_color(*INK)
        pdf.cell(tile_w - 6, 6, val)
        pdf.set_xy(x + 3, tile_y + 9.5)
        pdf.set_font("Malgun", "", 6.2)
        pdf.set_text_color(*MUTED)
        pdf.cell(tile_w - 6, 4, cap)
    pdf.set_y(tile_y + tile_h + 6)

    # 일별 감정 추세
    pdf.section_h("일별 감정 추세")
    trend = _daily_sentiment_trend(articles, sentiments_by_id)
    if trend:
        chart_y = pdf.get_y()
        chart_h = 16
        bw = CONTENT_W / len(trend)
        for i, (d, score) in enumerate(trend):
            bh = max(2, (score + 1) / 2 * chart_h)
            bx = MARGIN + i * bw
            color = POS if score >= 0.15 else (NEG if score <= -0.15 else ACCENT)
            pdf.set_fill_color(*color)
            pdf.rect(bx + bw * 0.15, chart_y + chart_h - bh, bw * 0.7, bh, style="F")
            pdf.set_xy(bx, chart_y + chart_h + 1.5)
            pdf.set_font("Malgun", "", 5.6)
            pdf.set_text_color(*MUTED2)
            pdf.cell(bw, 3, d[5:], align="C")
        pdf.set_y(chart_y + chart_h + 6)
    else:
        pdf.body_text("날짜별 감정 데이터가 아직 충분하지 않습니다.", size=7.5, color=MUTED2)

    # Executive Summary
    pdf.section_h("Executive Summary")
    summary_text = (result.get("insight_report") or "").strip()
    if not summary_text:
        summary_text = (result.get("final_report") or "").strip()
    if summary_text:
        summary_text = summary_text[:420] + ("..." if len(summary_text) > 420 else "")
    else:
        summary_text = (
            f"이번 기간 {league_name} 관련 기사 {n_ko + n_en}건을 수집해 분석했습니다. "
            f"AI 요약 리포트가 아직 생성되지 않아 통계 기반 요약만 제공합니다."
        )
    pdf.body_text(summary_text, size=8, color=(199, 202, 214), line_h=4.0)

    pdf.foot("Football Lens AI Agent  ·  LangGraph + Multi-LLM  ·  본 리포트는 뉴스 감정분석 기반 참고 정보이며 정확성을 보장하지 않습니다")


def _page2(pdf: _ReportPDF, articles: list, sentiments_by_id: dict, standings: list):
    pdf.add_page()
    pdf.bg()
    pdf.pagehead(2)

    pdf.section_h("Headline News")
    pdf.set_x(MARGIN)
    pdf.set_font("Malgun", "", 6)
    pdf.set_text_color(*MUTED)
    pdf.cell(20, 4, "");
    for label, color in [("긍정", POS), ("중립", MUTED), ("부정", NEG)]:
        pdf.set_fill_color(*color)
        pdf.circle(pdf.get_x() + 1, pdf.get_y() + 2, 0.8, style="F")
        pdf.set_x(pdf.get_x() + 3)
        pdf.set_text_color(*MUTED)
        pdf.cell(14, 4, label)
    pdf.ln(6)

    headlines = _top_headlines(articles, sentiments_by_id, n=9)
    if headlines:
        for h in headlines:
            row_y = pdf.get_y()
            pdf.set_fill_color(*_sent_color(h["label"]))
            pdf.circle(MARGIN + 1, row_y + 2, 0.9, style="F")
            pdf.set_xy(MARGIN + 4, row_y)
            pdf.set_font("Malgun", "B", 7.8)
            pdf.set_text_color(*INK)
            title = h["title"][:58] + ("..." if len(h["title"]) > 58 else "")
            pdf.cell(CONTENT_W - 26, 4, title)
            pdf.set_xy(PAGE_W - MARGIN - 18, row_y)
            pdf.set_font("Malgun", "B", 6.6)
            pdf.set_text_color(*_sent_color(h["label"]))
            pdf.cell(18, 4, f"{h['score']:+.2f}", align="R")
            pdf.set_xy(MARGIN + 4, row_y + 4)
            pdf.set_font("Malgun", "", 6.2)
            pdf.set_text_color(*MUTED2)
            pdf.cell(CONTENT_W - 4, 3.5, f"{h['source']}  ·  {h['date']}")
            pdf.set_y(row_y + 8.5)
            pdf.set_draw_color(*(40, 43, 56))
            pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
            pdf.ln(1.5)
    else:
        pdf.body_text("수집된 기사가 없습니다.", size=7.5, color=MUTED2)

    pdf.ln(2)
    pdf.section_h(f"Standings — Top {min(10, len(standings)) or 0}")
    if standings:
        headers = ["#", "Club", "P", "W", "D", "L", "GD", "Pts"]
        col_widths = [8, 62, 14, 14, 14, 14, 18, 16]
        aligns = ["L", "L", "R", "R", "R", "R", "R", "R"]
        rows = []
        for row in sorted(standings, key=lambda r: r.get("rank", 999))[:10]:
            gd = row.get("goal_diff")
            gd_txt = f"+{gd}" if isinstance(gd, (int, float)) and gd > 0 else str(gd)
            rows.append([
                row.get("rank", "?"), row.get("team_name", "?"), row.get("played", "-"),
                row.get("won", "-"), row.get("draw", "-"), row.get("lost", "-"),
                gd_txt, row.get("points", "-"),
            ])
        pdf.draw_table(headers, rows, col_widths, aligns)
    else:
        pdf.body_text("순위표 데이터가 없습니다(대회 특성상 미제공일 수 있습니다).", size=7.5, color=MUTED2)

    pdf.foot("Football Lens AI Agent  ·  감정 점수는 -1.0(매우 부정) ~ +1.0(매우 긍정) 범위입니다")


def _page3(pdf: _ReportPDF, result: dict, league: str, league_name: str,
           articles: list, sentiments_by_id: dict, transfer_rumors: list, user_tier: int):
    pdf.add_page()
    pdf.bg()
    pdf.pagehead(3)

    if _enabled("predictions", user_tier):
        pdf.section_h("Match Prediction")
        mp = result.get("match_prediction") or {}
        preds = mp.get("predictions") or []
        if preds:
            for p in preds[:3]:
                card_y = pdf.get_y()
                card_h = 14
                pdf.card(MARGIN, card_y, CONTENT_W, card_h)
                pdf.set_xy(MARGIN + 4, card_y + 2.5)
                pdf.set_font("Malgun", "B", 8.5)
                pdf.set_text_color(*INK)
                vs_txt = f"{p.get('home_team','?')}   vs   {p.get('away_team','?')}"
                pdf.cell(CONTENT_W - 8, 4.5, vs_txt)
                pdf.set_xy(MARGIN + 4, card_y + 8)
                pdf.set_font("Malgun", "", 6.6)
                conf = (p.get("confidence") or "").strip()
                conf_color = POS if "높" in conf else (NEG if "낮" in conf else ACCENT)
                pdf.set_text_color(*conf_color)
                conf_label = conf if conf else "신뢰도 정보 없음"
                pdf.cell(28, 3.6, conf_label)
                pdf.set_text_color(*MUTED)
                reason = (p.get("reason") or "").strip()[:44]
                pdf.cell(CONTENT_W - 36, 3.6, reason)
                pdf.set_y(card_y + card_h + 3)
            acc_note = ""
            from prediction_tracker import get_accuracy_summary
            acc = get_accuracy_summary()
            if acc["total"] > 0:
                acc_note = f" 지난 {acc['total']}건 예측 중 적중률은 {acc['accuracy_pct']}%입니다."
            pdf.body_text(
                "예측은 뉴스 감정 지수와 순위·최근 경기 데이터를 종합한 참고 정보이며 실제 결과를 "
                "보장하지 않습니다." + acc_note,
                size=7.3, color=MUTED,
            )
        else:
            err = mp.get("error")
            model_used = mp.get("model_used", "")
            if err:
                note = f"예측을 생성하지 못했습니다: {err}"
            elif model_used == "skip":
                note = "예정된 경기가 없어 이번 기간에는 경기 예측을 제공하지 않습니다."
            else:
                note = "LLM API 키가 설정되지 않아 경기 예측을 생성하지 못했습니다."
            pdf.body_text(note, size=7.5, color=MUTED2)

    top_scorers = result.get("top_scorers") or []
    if top_scorers:
        pdf.section_h("Top Scorers")
        headers = ["#", "Player", "Club", "G", "A"]
        col_widths = [8, 55, 60, 12, 12]
        rows = [
            [s.get("rank", "?"), s.get("player_name", "?"), s.get("team_name", "?"),
             s.get("goals", 0), s.get("assists", 0)]
            for s in top_scorers[:5]
        ]
        pdf.draw_table(headers, rows, col_widths, header_size=6.3, body_size=7.3)
    else:
        pdf.section_h("Top Scorers")
        pdf.body_text("득점왕 데이터가 없습니다(대회 특성상 미제공일 수 있습니다).", size=7.5, color=MUTED2)

    if _enabled("transfer_rumors", user_tier):
        pdf.section_h("Transfer Watch — 상세")
        if transfer_rumors:
            for r in transfer_rumors[:5]:
                row_y = pdf.get_y()
                title = (r.get("title") or "")[:52]
                tag = _rumor_tag(r.get("published_at", ""))
                tag_color = ACCENT2 if tag == "HOT" else (ACCENT if tag == "UPDATE" else MUTED)
                pdf.set_xy(MARGIN, row_y)
                pdf.set_font("Malgun", "", 7.6)
                pdf.set_text_color(*INK)
                pdf.cell(CONTENT_W - 20, 5, title)
                pdf.set_xy(PAGE_W - MARGIN - 18, row_y)
                pdf.set_font("Malgun", "B", 6.4)
                pdf.set_text_color(*tag_color)
                pdf.cell(18, 5, tag, align="R")
                pdf.set_y(row_y + 5)
                pdf.set_draw_color(*(40, 43, 56))
                pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
                pdf.ln(1.2)
            pdf.ln(2)
        else:
            pdf.body_text("이 기간 수집된 이적 루머가 없습니다.", size=7.5, color=MUTED2)

    if _enabled("spotlight_players", user_tier):
        pdf.section_h("Spotlight Players")
        from tabs.players import LEAGUE_SPOTLIGHT_PLAYERS, compute_player_stats
        candidates = LEAGUE_SPOTLIGHT_PLAYERS.get(league, LEAGUE_SPOTLIGHT_PLAYERS["PL"])
        stats_list = []
        for name in candidates:
            st_ = compute_player_stats(name, articles, sentiments_by_id)
            if st_["article_count"] > 0:
                stats_list.append(st_)
        stats_list.sort(key=lambda s: s["article_count"], reverse=True)
        top_players = stats_list[:5]
        if top_players:
            chip_y = pdf.get_y()
            chip_h = 14
            gap = 3
            chip_w = (CONTENT_W - gap * (len(top_players) - 1)) / len(top_players)
            for i, s in enumerate(top_players):
                x = MARGIN + i * (chip_w + gap)
                pdf.card(x, chip_y, chip_w, chip_h)
                pdf.set_xy(x + 1, chip_y + 3)
                pdf.set_font("Malgun", "B", 7.4)
                pdf.set_text_color(*INK)
                pdf.cell(chip_w - 2, 4, s["query"], align="C")
                pdf.set_xy(x + 1, chip_y + 8)
                pdf.set_font("Malgun", "", 5.8)
                pdf.set_text_color(*MUTED)
                avg = s["avg_sentiment"]
                avg_txt = f"{avg:+.2f}" if avg is not None else "-"
                pdf.cell(chip_w - 2, 3.5, f"기사 {s['article_count']}건 · {avg_txt}", align="C")
            pdf.set_y(chip_y + chip_h + 4)
        else:
            pdf.body_text("주목 선수 관련 기사가 이번 기간에는 없습니다.", size=7.5, color=MUTED2)

    pdf.foot(f"Football Lens AI Agent  ·  LangGraph + Claude/GPT/Gemini  ·  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def generate_pdf_report(result: dict, league: str, user_tier: int = PROTOTYPE_TIER) -> bytes:
    """result(파이프라인 실행 결과)를 받아 3페이지 PDF 리포트 바이트를 반환한다."""
    from constants import _CODE_TO_LEAGUE_NAME  # dashboard 폴더가 sys.path에 있을 때만 임포트 가능

    league_name = _CODE_TO_LEAGUE_NAME.get(league, league)
    articles = _all_articles(result)
    sentiments_by_id = _sentiments_by_id(result)
    standings = sorted(result.get("raw_standings", []), key=lambda r: r.get("rank", 999))
    transfer_rumors = result.get("transfer_rumors", [])

    pdf = _ReportPDF()
    _page1(pdf, result, league_name, articles, sentiments_by_id, standings, transfer_rumors)
    _page2(pdf, articles, sentiments_by_id, standings)
    _page3(pdf, result, league, league_name, articles, sentiments_by_id, transfer_rumors, user_tier)

    return bytes(pdf.output())
