# -*- coding: utf-8 -*-
import streamlit as st
import os, json, re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from config import DATA_PATH, AUDIO_DIR

# ------------ 기본 설정 ------------
st.set_page_config(page_title="왕초보 영어 2024 하편", layout="centered")
pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

# ------------ JSON 불러오기 ------------
if not os.path.exists(DATA_PATH):
    st.error(f"❌ 데이터 파일이 없습니다: {os.path.abspath(DATA_PATH)}")
    st.stop()

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    st.warning("⚠️ JSON 데이터가 비어 있습니다.")
    st.stop()

day_list = sorted(data.keys())

# ------------ 유틸 함수 ------------
def find_audio_file(day_number):
    """audio 폴더에서 mp3 파일 탐색"""
    if not os.path.isdir(AUDIO_DIR):
        return None
    prefix = f"{int(day_number):03d}."
    for f in os.listdir(AUDIO_DIR):
        if f.startswith(prefix) and f.endswith(".mp3"):
            return os.path.join(AUDIO_DIR, f)
    return None


def normalize_day(q: str):
    """입력값을 DAY 포맷으로 변환"""
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


def make_pdf(day_key, lesson):
    """PDF 생성 (대화 + 핵심 표현 + 손영작 연습 포함)"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('Title', parent=styles['Title'],
        fontName="HYSMyeongJo-Medium", fontSize=22, alignment=1, leading=28, spaceAfter=20)
    style_heading = ParagraphStyle('Heading', parent=styles['Heading2'],
        fontName="HYSMyeongJo-Medium", fontSize=15, leading=22, spaceAfter=10)
    style_body = ParagraphStyle('Body', parent=styles['BodyText'],
        fontName="HYSMyeongJo-Medium", fontSize=12, leading=20, spaceAfter=8)

    def safe(x): return x.decode() if isinstance(x, bytes) else str(x or "")

    content = []
    content.append(Paragraph(safe(f"왕초보 영어 {day_key}"), style_title))
    content.append(Paragraph(safe(lesson.get("title","")), style_heading))

    # 💬 Dialogue
    content.append(Spacer(1, 6))
    content.append(Paragraph("💬 Dialogue", style_heading))
    dlg = lesson.get("dialogue", [])
    if isinstance(dlg, list) and dlg:
        dlg_text = "".join([f"<b>{d.get('speaker')}</b>: {d.get('en')}<br/>{d.get('ko')}<br/><br/>" for d in dlg])
    else:
        dlg_text = "내용 없음"
    content.append(Paragraph(safe(dlg_text), style_body))

    # 📘 핵심 표현
    content.append(Spacer(1, 6))
    content.append(Paragraph("📘 핵심 표현", style_heading))
    patterns = lesson.get("patterns", [])
    patt_text = "<br/>".join([f"• {p}" for p in patterns]) if patterns else "없음"
    content.append(Paragraph(safe(patt_text), style_body))

    # ✍️ 손영작 연습
    content.append(Spacer(1, 6))
    content.append(Paragraph("✍️ 손영작 연습", style_heading))
    practice = lesson.get("practice", [])
    prac_text = "<br/>".join([f"□ {p}" for p in practice]) if practice else "없음"
    content.append(Paragraph(safe(prac_text), style_body))

    doc.build(content)
    buffer.seek(0)
    return buffer

# ------------ UI ------------

st.title("📘 왕초보 영어 2024 하편 학습 뷰어")
st.markdown("🔹 DAY 번호를 입력하거나 ⏮⏭ 버튼으로 이동하세요.")

# 현재 DAY 상태 관리
if "current_day" not in st.session_state:
    st.session_state.current_day = day_list[0]

query = st.text_input("DAY 번호 입력 (예: 5 또는 005)", value=st.session_state.current_day)
norm = normalize_day(query)
if norm and norm in data and norm != st.session_state.current_day:
    st.session_state.current_day = norm
    st.rerun()

col1, col2, col3 = st.columns([1, 1, 6])
with col1:
    if st.button("⏮ 이전"):
        idx = day_list.index(st.session_state.current_day)
        if idx > 0:
            st.session_state.current_day = day_list[idx - 1]
            st.rerun()
with col2:
    if st.button("⏭ 다음"):
        idx = day_list.index(st.session_state.current_day)
        if idx < len(day_list) - 1:
            st.session_state.current_day = day_list[idx + 1]
            st.rerun()
with col3:
    st.markdown(
        f"<div style='text-align:right;font-weight:600'>현재 DAY: {st.session_state.current_day}</div>",
        unsafe_allow_html=True
    )

# ------------ 현재 DAY 표시 ------------
day = st.session_state.current_day
lesson = data.get(day, {})
st.header(f"{day} — {lesson.get('title', '')}")

# 💬 Dialogue
if lesson.get("dialogue"):
    st.subheader("💬 Dialogue")
    for line in lesson["dialogue"]:
        st.markdown(f"**{line.get('speaker','')}:** {line.get('en','')}")
        st.markdown(f"👉 {line.get('ko','')}")
        st.markdown("---")
else:
    st.info("대화 내용이 없습니다.")

# 📘 핵심 표현
if lesson.get("patterns"):
    st.subheader("📘 핵심 표현")
    for p in lesson["patterns"]:
        st.markdown(f"- {p}")
else:
    st.info("핵심 표현이 없습니다.")

# ✍️ 손영작 연습
if lesson.get("practice"):
    st.subheader("✍️ 손영작 연습")
    for p in lesson["practice"]:
        st.markdown(f"□ {p}")
else:
    st.info("손영작 연습이 없습니다.")

# 🎧 오디오
num = day.split()[1]
audio = find_audio_file(num)
if audio:
    st.audio(audio)
else:
    st.info("🔇 오디오 파일이 없습니다.")

# 📘 PDF 다운로드
pdf = make_pdf(day, lesson)
st.download_button(
    label=f"📘 {day} 학습지 PDF 다운로드",
    data=pdf,
    file_name=f"{day}_학습지.pdf",
    mime="application/pdf"
)
