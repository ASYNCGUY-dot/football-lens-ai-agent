# -*- coding: utf-8 -*-
"""
setup_wizard.py
================
첫 실행 시 API 키를 입력받아 week3/.env를 자동 생성/갱신하는 Setup 화면.

배경: app.py는 week3/.env, week2/.env 두 파일만 명시적 경로로 load_dotenv()
한다. 반면 week1의 collector들(naver_collector.py 등)은 인자 없는
load_dotenv()를 쓰는데, 이는 실행 시점 cwd에서 위로 탐색하는 방식이라
Streamlit 대시보드에서 실행될 때는 week1/.env(네이버·football-data 키가
있는 곳)를 찾지 못할 수 있다. 그래서 이 마법사는 모든 키를 week3/.env
하나로 모아서, app.py가 확정적으로 로드하는 경로에 저장한다.
"""

import os
from pathlib import Path

import streamlit as st

WEEK3_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# (환경변수명, 표시 라벨, 필수 여부, 비밀값 여부)
LLM_KEYS = [
    ("ANTHROPIC_API_KEY", "Claude (Anthropic)", False, True),
    ("OPENAI_API_KEY", "GPT-4o-mini (OpenAI)", False, True),
    ("GOOGLE_API_KEY", "Gemini (Google)", False, True),
]
NEWS_KEYS = [
    ("NAVER_CLIENT_ID", "네이버 Client ID", False, False),
    ("NAVER_CLIENT_SECRET", "네이버 Client Secret", False, True),
    ("FOOTBALL_DATA_API_KEY", "football-data.org API Key", False, True),
]


def _is_placeholder(value: str) -> bool:
    """
    'your_..._here'·'여기에_Anthropic_키' 같은 미입력 잔여 값인지 판별.

    week2/llm_nodes.py의 _clean_api_key()와 같은 기준(비ASCII 문자 포함 시
    플레이스홀더로 간주)을 추가했다 — 한글 placeholder는 실제 API 키로
    httpx에 전달되면 헤더 인코딩 오류(UnicodeEncodeError)를 일으킨다.
    """
    if not value:
        return True
    v = value.strip()
    if v == "" or v.lower().startswith("your_") or v.lower() in ("changeme", "xxx"):
        return True
    try:
        v.encode("ascii")
    except UnicodeEncodeError:
        return True
    return len(v) < 10


def is_setup_complete() -> bool:
    """LLM 키 중 하나라도 실제 값이 설정돼 있으면 설정 완료로 간주."""
    return any(
        not _is_placeholder(os.getenv(key, ""))
        for key, _, _, _ in LLM_KEYS
    )


def _read_env_lines() -> list[str]:
    if not WEEK3_ENV_PATH.exists():
        return []
    with open(WEEK3_ENV_PATH, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _upsert_env_file(updates: dict[str, str]) -> None:
    """
    기존 week3/.env 내용을 보존하면서 지정된 키만 갱신/추가한다.
    값이 빈 문자열인 항목은 건너뛴다 (사용자가 입력 안 한 키는 그대로 둠).
    """
    updates = {k: v for k, v in updates.items() if v}
    if not updates:
        return

    lines = _read_env_lines()
    seen = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        new_lines.append(line)

    remaining = [k for k in updates if k not in seen]
    if remaining:
        new_lines.append("")
        new_lines.append("# ── setup_wizard.py가 추가한 키 ──")
        for k in remaining:
            new_lines.append(f"{k}={updates[k]}")

    WEEK3_ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WEEK3_ENV_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(new_lines) + "\n")


def render_setup_wizard() -> None:
    """API 키 입력 마법사를 렌더링한다. 저장 성공 시 st.rerun()으로 대시보드로 전환."""
    st.markdown("## ⚙️ 초기 설정")
    st.markdown(
        "Football Lens를 시작하려면 최소 하나의 LLM API 키가 필요합니다. "
        "입력한 키는 이 프로젝트의 `week3/.env` 파일에 저장되며, 외부로 전송되지 않습니다."
    )

    with st.form("setup_wizard_form"):
        st.markdown("### 🤖 LLM API 키 (하나 이상 필수)")
        llm_values = {}
        for key, label, _required, is_secret in LLM_KEYS:
            llm_values[key] = st.text_input(
                label, type="password" if is_secret else "default", key=f"setup_{key}",
            )

        with st.expander("📰 뉴스 수집 API 키 (선택사항 — 없으면 일부 리그 데이터가 비어 보일 수 있음)"):
            news_values = {}
            for key, label, _required, is_secret in NEWS_KEYS:
                news_values[key] = st.text_input(
                    label, type="password" if is_secret else "default", key=f"setup_{key}",
                )

        col_save, col_skip = st.columns([1, 1])
        with col_save:
            submitted = st.form_submit_button("💾 저장하고 시작", type="primary", use_container_width=True)
        with col_skip:
            skipped = st.form_submit_button("건너뛰기 (키 없이 둘러보기)", use_container_width=True)

    if submitted:
        has_llm = any(v.strip() for v in llm_values.values())
        if not has_llm:
            st.error("LLM API 키를 최소 하나 이상 입력해주세요 (Claude / GPT / Gemini 중 하나).")
            return

        all_updates = {**llm_values, **news_values}
        for k, v in all_updates.items():
            if v.strip():
                os.environ[k] = v.strip()
        _upsert_env_file(all_updates)

        st.success("저장 완료! 대시보드로 이동합니다...")
        st.rerun()

    if skipped:
        st.session_state["_setup_skipped"] = True
        st.rerun()
