# -*- coding: utf-8 -*-
"""tabs/email.py — 이메일 발송 탭."""
import streamlit as st

from components import _html, espn_section
from utils import send_report_email


def render_email_tab(result: dict):
    """이메일 발송 탭을 렌더링합니다."""
    espn_section("📧", "Email Report")

    final_report = result.get("final_report", "")
    if not final_report:
        st.info("분석 실행 후 이메일 발송이 가능합니다.")
        return

    col_form, col_side = st.columns([1, 1])

    with col_form:
        recipients_input = st.text_input(
            "수신자 이메일 (쉼표로 구분)",
            placeholder="example@email.com, another@email.com",
        )

        import os as _os
        smtp_ok = bool(_os.getenv("SMTP_USER") and _os.getenv("SMTP_PASSWORD"))
        if smtp_ok:
            _html(f'<div style="background:#E8F5E9;border:1px solid #A5D6A7;border-radius:3px;'
                  f'padding:10px 14px;margin:8px 0;font-size:12px;color:#2E7D32;'
                  f'font-family:Oswald,sans-serif;font-weight:600;text-transform:uppercase;">'
                  f'SMTP 설정 완료 — {_os.getenv("SMTP_HOST","")}</div>')
        else:
            _html('<div style="background:#FFF3E0;border:1px solid #FFCC80;border-radius:3px;'
                  'padding:10px 14px;margin:8px 0;font-size:12px;color:#E65100;'
                  'font-family:Oswald,sans-serif;font-weight:600;text-transform:uppercase;">'
                  'SMTP 미설정 — .env에 SMTP_USER / SMTP_PASSWORD 입력</div>')

        send_btn = st.button("📤 이메일 발송", type="primary", use_container_width=True, disabled=not smtp_ok)
        if send_btn:
            recipients = [r.strip() for r in recipients_input.split(",") if r.strip()]
            if not recipients:
                st.error("수신자 이메일을 입력해주세요.")
                return
            with st.spinner(f"{len(recipients)}명에게 발송 중..."):
                success = send_report_email(final_report, recipients)
            if success:
                st.success(f"✅ {len(recipients)}명에게 발송 완료!")
                st.balloons()

    with col_side:
        espn_section("👁️", "Preview")
        with st.expander("보고서 내용", expanded=True):
            st.markdown(final_report[:1200] + ("..." if len(final_report) > 1200 else ""))
