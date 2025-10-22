# -*- coding: utf-8 -*-
import streamlit as st
import json
import os
import re

# ---------------- 기본 설정 ----------------
st.set_page_config(page_title="왕초보 영어 JSON 편집기", layout="centered")
st.title("📝 왕초보 영어 2024 JSON 편집기")

DATA_PATH = "data_dialog_only.json"

# ---------------- JSON 불러오기 ----------------
if not os.path.exists(DATA_PATH):
    st.error(f"❌ JSON 파일이 없습니다: {os.path.abspath(DATA_PATH)}")
    st.stop()

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

if not isinstance(data, dict) or not data:
    st.warning("⚠️ JSON 데이터가 비어 있거나 잘못되었습니다.")
    st.stop()

day_keys = sorted(data.keys())

# ---------------- DAY 인식 함수 ----------------
def normalize_day(q: str):
    if not q:
        return None
    q = str(q).strip()
    if q.isdigit():
        n = int(q)
        if 1 <= n <= 130:
            return f"DAY {n:03}"
    m = re.search(r"(?i)\bday\D*([0-9]{1,3})\b", q)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 130:
            return f"DAY {n:03}"
    return None

# ---------------- 세션 상태 초기화 ----------------
if "selected_day" not in st.session_state:
    st.session_state.selected_day = "DAY 001"
if "query_buffer" not in st.session_state:
    st.session_state.query_buffer = ""

# ---------------- 입력 후 이동 콜백 ----------------
def handle_day_change():
    """입력창에 Enter 시 DAY 이동 + 입력창 초기화"""
    query = st.session_state.query_buffer
    norm = normalize_day(query)
    if norm and norm in data:
        st.session_state.selected_day = norm
    # ✅ 입력 후 항상 비움 (자동 초기화)
    st.session_state.query_buffer = ""

# ---------------- 입력창 (Enter 후 자동 초기화) ----------------
st.text_input(
    "DAY 번호 입력 (예: 5 또는 005)",
    key="query_buffer",
    on_change=handle_day_change,
)

selected_day = st.session_state.selected_day
lesson = data[selected_day]
st.header(f"{selected_day} — {lesson.get('title', '')}")

# ---------------- 제목 ----------------
new_title = st.text_input("제목 (Title)", value=lesson.get("title", ""))

# ---------------- Dialogue 편집 ----------------
st.subheader("💬 Dialogue (A/B 대화)")
dialogues = lesson.get("dialogue", [])
new_dialogues = []

for i, d in enumerate(dialogues):
    col1, col2, col3 = st.columns([1, 3, 3])
    with col1:
        sp = st.selectbox(f"화자 {i+1}", ["A", "B"], index=0 if d.get("speaker") == "A" else 1)
    with col2:
        en = st.text_input(f"EN {i+1}", value=d.get("en", ""))
    with col3:
        ko = st.text_input(f"KO {i+1}", value=d.get("ko", ""))
    new_dialogues.append({"speaker": sp, "en": en.strip(), "ko": ko.strip()})

# ➕ 대화 줄 추가
if st.button("➕ 대화 줄 추가"):
    new_dialogues.append({"speaker": "A", "en": "", "ko": ""})
    lesson["dialogue"] = new_dialogues
    data[selected_day] = lesson
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    st.success("✅ 빈 대화 줄이 추가되었습니다.")
    st.experimental_rerun()

# 🗑️ 공백 줄 자동 삭제
if st.button("🗑️ 공백 줄 삭제"):
    before = len(new_dialogues)
    new_dialogues = [d for d in new_dialogues if d["en"].strip() or d["ko"].strip()]
    after = len(new_dialogues)
    lesson["dialogue"] = new_dialogues
    data[selected_day] = lesson
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    st.success(f"✅ 공백 줄 {before - after}개 삭제 완료!")
    st.experimental_rerun()

# ---------------- 패턴 / 연습 ----------------
st.subheader("📘 핵심 패턴")
patterns_text = "\n".join(lesson.get("patterns", []))
patterns_new = st.text_area("패턴 목록 (줄바꿈으로 구분)", value=patterns_text, height=120)

st.subheader("✍️ 손영작 연습")
practice_text = "\n".join(lesson.get("practice", []))
practice_new = st.text_area("연습 문장 (줄바꿈으로 구분)", value=practice_text, height=120)

# ---------------- 저장 ----------------
if st.button("💾 JSON 저장"):
    lesson["title"] = new_title
    lesson["dialogue"] = [d for d in new_dialogues if d["en"].strip() or d["ko"].strip()]
    lesson["patterns"] = [x.strip() for x in patterns_new.splitlines() if x.strip()]
    lesson["practice"] = [x.strip() for x in practice_new.splitlines() if x.strip()]
    data[selected_day] = lesson

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    st.success(f"✅ {selected_day} 수정 내용이 저장되었습니다.")
