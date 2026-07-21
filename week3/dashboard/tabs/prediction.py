# -*- coding: utf-8 -*-
"""tabs/prediction.py — 경기 예측 탭."""
import streamlit as st

from components import _html, espn_section
from season_info import render_off_season_notice


def _render_accuracy_section() -> None:
    """
    지금까지 판정된 과거 예측의 적중률을 보여준다. 판정 기록이 하나도
    없으면 조용히 아무것도 그리지 않는다(예측 데이터 유무와 무관하게
    항상 먼저 표시 — 리그가 비시즌이어도 과거 적중률은 볼 수 있어야 함).
    """
    from prediction_tracker import get_accuracy_summary, check_predictions

    summary = get_accuracy_summary()

    col_title, col_btn = st.columns([3, 1])
    with col_btn:
        if st.button("🔄 적중 판정 실행", help="지난 예측 중 경기가 끝난 것들을 실제 결과와 대조합니다 (최대 5건, API 제한으로 다소 걸릴 수 있음)"):
            with st.spinner("실제 결과와 대조 중..."):
                run_result = check_predictions(max_checks=5)
            st.toast(
                f"판정 완료: {run_result['judged']}건 새로 판정, {run_result['still_pending']}건 대기 중",
                icon="✅",
            )
            st.rerun()

    if summary["total"] == 0:
        return

    with col_title:
        espn_section("📊", "예측 적중률", summary["total"])

    acc = summary["accuracy_pct"]
    acc_color = "#2E7D32" if acc >= 55 else ("#E65100" if acc >= 45 else "#CC0000")
    _html(f"""
<div style="background:#FFFFFF;border-radius:6px;padding:16px 20px;margin-bottom:12px;
     box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:20px;">
  <div style="font-family:'Oswald',sans-serif;font-size:32px;font-weight:800;color:{acc_color};">{acc}%</div>
  <div style="font-size:13px;color:#666;">
    총 {summary['total']}건 판정 · 적중 {summary['correct']}건<br>
    <span style="font-size:11px;color:#999;">경기가 끝난 예측만 판정되며, 아직 안 끝난 경기는 다음 판정 때 확인됩니다.</span>
  </div>
</div>
""")

    if summary["by_league"]:
        league_rows = "".join(
            f'<tr><td>{lg}</td><td style="text-align:center;">{v["total"]}건</td>'
            f'<td style="text-align:center;">{round(v["correct"]/v["total"]*100,1) if v["total"] else 0}%</td></tr>'
            for lg, v in summary["by_league"].items()
        )
        _html(f"""
<details style="margin-bottom:16px;">
<summary style="cursor:pointer;font-size:12px;color:#888;">리그별 적중률 보기</summary>
<table style="width:100%;font-size:12px;margin-top:8px;border-collapse:collapse;">
<thead><tr style="color:#888;"><th style="text-align:left;">리그</th><th>판정 수</th><th>적중률</th></tr></thead>
<tbody>{league_rows}</tbody>
</table>
</details>
""")


def render_prediction_tab(result: dict, league: str = "PL"):
    """경기 예측 탭 — 리그 시즌 여부 확인 후 예측 또는 개막일 표시."""
    _render_accuracy_section()

    if render_off_season_notice(league, context="개막 후 분석을 실행하면 경기 예측이 표시됩니다."):
        return

    # ── 분석 미실행 상태 ──────────────────────────────────────
    prediction = result.get("match_prediction", {})
    upcoming = result.get("upcoming_matches", [])

    if not result or (not prediction and not upcoming):
        _html("""
<div style="background:#FFFFFF;border:2px dashed #E0E0E0;border-radius:4px;padding:48px;text-align:center;margin-top:16px;">
<div style="font-size:48px;margin-bottom:12px;">🎯</div>
<div style="font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;color:#1A1A1A;text-transform:uppercase;">예측 데이터 없음</div>
<div style="font-size:14px;color:#888;margin-top:8px;">⚡ 분석 실행 후 경기 예측이 표시됩니다</div>
</div>
""")
        return

    espn_section("🎯", "Match Prediction")
    _html("""
<div style="background:#FFF3E0;border:1px solid #FFCC80;border-radius:3px;padding:10px 14px;margin-bottom:16px;font-size:12px;color:#E65100;">
⚠️ <strong>면책사항</strong>: 예측은 뉴스 감정 + 순위 데이터 기반의 참고 정보이며, 실제 결과를 보장하지 않습니다.
</div>
""")

    # 예정 경기 일정
    if upcoming:
        espn_section("📅", "Upcoming Fixtures", len(upcoming))
        for m in upcoming[:8]:
            date = str(m.get("utc_date", ""))[:10]
            home = m.get("home_team_name", "?")
            away = m.get("away_team_name", "?")
            _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:12px 18px;margin-bottom:6px;box-shadow:0 1px 3px rgba(0,0,0,0.06);display:flex;justify-content:space-between;align-items:center;">
<div style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#1A1A1A;">{home}</div>
<div style="font-family:'Oswald',sans-serif;font-size:11px;font-weight:600;color:#CC0000;text-align:center;padding:0 12px;">VS<br><span style="font-size:9px;color:#888;">{date}</span></div>
<div style="font-family:'Oswald',sans-serif;font-size:13px;font-weight:700;color:#1A1A1A;text-align:right;">{away}</div>
</div>
""")
        st.markdown("<br>", unsafe_allow_html=True)

    # AI 예측 텍스트
    pred_text = prediction.get("prediction_text", "")
    model = prediction.get("model_used", "")
    skip_keywords = ["없음", "API 키", "skip", "데이터 없음"]
    if pred_text and not any(kw in pred_text for kw in skip_keywords):
        espn_section("🤖", f"AI Prediction — {model}")
        _html('<div style="background:#FFFFFF;border:1px solid #E5E5E5;border-radius:4px;padding:24px 28px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">')
        st.markdown(pred_text)
        _html('</div>')
    elif upcoming:
        # 경기 일정은 있지만 LLM 예측 실패
        st.info("LLM API 키를 설정하면 AI 경기 예측이 생성됩니다. (.env의 ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY)")
    else:
        # WC이지만 예정 경기 API 데이터 없음 → 뉴스 기반 안내
        if league == "WC":
            all_articles = result.get("korean_articles", []) + result.get("english_articles", [])
            wc_articles = [a for a in all_articles if any(
                kw in f"{a.get('title','')} {a.get('summary','')}".lower()
                for kw in ["월드컵", "world cup", "worldcup", "2026 fifa"]
            )]
            if wc_articles:
                espn_section("📰", "월드컵 관련 뉴스 (경기 일정 API 대체)")
                for a in wc_articles[:6]:
                    title = (a.get("title") or "")[:80]
                    url = a.get("url", "#")
                    src = a.get("source_name", "")
                    pub = str(a.get("published_at", ""))[:10]
                    _html(f"""
<div style="background:#FFFFFF;border-radius:4px;padding:12px 16px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
<a href="{url}" target="_blank" style="font-size:14px;font-weight:600;color:#1A1A1A;text-decoration:none;">{title}</a>
<div style="font-size:11px;color:#888;margin-top:3px;">{src} · {pub}</div>
</div>
""")
            else:
                st.info("월드컵 경기 일정 API 데이터를 가져오지 못했습니다. 분석 실행 후 다시 시도하세요.")
