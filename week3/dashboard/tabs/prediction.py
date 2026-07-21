# -*- coding: utf-8 -*-
"""tabs/prediction.py — 경기 예측 탭."""
import streamlit as st

from components import _html, espn_section


def render_prediction_tab(result: dict, league: str = "PL"):
    """경기 예측 탭 — 리그 시즌 여부 확인 후 예측 또는 개막일 표시."""
    from datetime import date as _date

    # ── 리그별 시즌 일정 ──────────────────────────────────────
    # (season_start, season_end, next_season_start, league_display)
    _LEAGUE_SEASON = {
        # WC 2026: 2026-06-11 ~ 2026-07-19
        "WC":  (_date(2026, 6, 11),  _date(2026, 7, 19),  None,                "2026 FIFA 월드컵"),
        # EPL 2025/26: ~2026-05-24 종료, 2026/27 개막 예정 2026-08-08
        "PL":  (_date(2025, 8, 16),  _date(2026, 5, 24),  _date(2026, 8, 8),   "EPL 프리미어리그"),
        # La Liga 2025/26
        "PD":  (_date(2025, 8, 15),  _date(2026, 6, 1),   _date(2026, 8, 15),  "라리가"),
        # Bundesliga 2025/26: 8월 개막, 5월 종료
        "BL1": (_date(2025, 8, 22),  _date(2026, 5, 23),  _date(2026, 8, 7),   "분데스리가"),
        # Serie A 2025/26
        "SA":  (_date(2025, 8, 23),  _date(2026, 5, 31),  _date(2026, 8, 21),  "세리에A"),
        # Ligue 1 2025/26
        "FL1": (_date(2025, 8, 16),  _date(2026, 5, 24),  _date(2026, 8, 9),   "리그앙"),
        # K리그1 2025: 2~11월
        "KL1": (_date(2026, 2, 21),  _date(2026, 11, 30), None,                "K리그1"),
    }

    today = _date.today()
    season_info = _LEAGUE_SEASON.get(league)

    # ── 비시즌 처리 ───────────────────────────────────────────
    if season_info:
        s_start, s_end, next_start, lg_name = season_info
        in_season = s_start <= today <= s_end

        if not in_season and league != "WC":
            # 비시즌 안내 카드
            if next_start:
                days_left = (next_start - today).days
                next_str = next_start.strftime("%Y년 %m월 %d일")
                countdown = f"{days_left}일 후" if days_left > 0 else "곧 개막"
            else:
                next_str = "미정"
                countdown = ""

            _html(f"""
<div style="background:#FFFFFF;border-radius:8px;border:2px solid #E0E0E0;padding:48px 32px;text-align:center;margin-top:16px;">
<div style="font-size:56px;margin-bottom:16px;">🏖️</div>
<div style="font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:#1A1A1A;text-transform:uppercase;margin-bottom:8px;">{lg_name} — 비시즌</div>
<div style="font-size:15px;color:#555;margin-bottom:20px;">현재 리그가 진행 중이지 않습니다.</div>
<div style="display:inline-block;background:#CC0000;color:#FFF;border-radius:6px;padding:14px 28px;">
  <div style="font-size:11px;font-family:'Oswald',sans-serif;text-transform:uppercase;letter-spacing:1px;opacity:0.85;margin-bottom:4px;">다음 시즌 개막</div>
  <div style="font-family:'Oswald',sans-serif;font-size:24px;font-weight:700;">{next_str}</div>
  <div style="font-size:13px;margin-top:4px;opacity:0.9;">{countdown}</div>
</div>
<div style="margin-top:24px;font-size:12px;color:#888;">개막 후 분석을 실행하면 경기 예측이 표시됩니다.</div>
</div>
""")
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
