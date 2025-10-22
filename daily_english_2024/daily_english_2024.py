# -*- coding: utf-8 -*-
import streamlit as st
st.set_page_config(page_title="왕초보 영어 2024 하편", layout="centered")

import os, json, random, re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ------------ 경로 설정 ------------
DATA_PATH = "data_dialog_only.json"   # ✅ JSON 파일명
BASE_AUDIO_PATH = "audio"

# ------------ 한글 폰트 등록 ------------
pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

# ------------ JSON 데이터 불러오기 ------------
if not os.path.exists(DATA_PATH):
    st.error(f"❌ 데이터 파일이 없습니다: {os.path.abspath(DATA_PATH)}")
    st.stop()

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    st.warning("⚠️ JSON 데이터가 비어 있습니다.")
    st.stop()

day_list = sorted(data.keys())

# ------------ 함수 정의 ------------
def find_audio_file(day_number):
    """audio 폴더에서 mp3 파일 탐색"""
    if not os.path.isdir(BASE_AUDIO_PATH):
        return None
    prefix = f"{int(day_number):03d}."
    for f in os.listdir(BASE_AUDIO_PATH):
        if f.startswith(prefix) and f.endswith(".mp3"):
            return os.path.join(BASE_AUDIO_PATH, f)
    return None

def make_pdf(day_key, lesson):
    """PDF 생성"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Title'], fontName="HYSMyeongJo-Medium",
                                 fontSize=22, alignment=1, leading=28, spaceAfter=20)
    style_heading = ParagraphStyle('Heading', parent=styles['Heading2'], fontName="HYSMyeongJo-Medium",
                                   fontSize=15, leading=22, spaceAfter=14)
    style_body = ParagraphStyle('Body', parent=styles['BodyText'], fontName="HYSMyeongJo-Medium",
                                fontSize=12, leading=20, spaceAfter=20)

    def safe(t): 
        return t.decode() if isinstance(t, bytes) else str(t or "")

    content = []
    content.append(Paragraph(safe(f"왕초보 영어 {day_key}"), style_title))
    content.append(Spacer(1, 20))
    content.append(Paragraph(safe(lesson.get("title", "")), style_heading))
    content.append(Spacer(1, 16))

    # Dialogue
    dlg = lesson.get("dialogue", [])
    if isinstance(dlg, list):
        dlg_text = "".join([f"<b>{d.get('speaker')}</b>: {d.get('en')}<br/>{d.get('ko')}<br/><br/>" for d in dlg])
    else:
        dlg_text = dlg
    content.append(Paragraph(safe(dlg_text), style_body))
    content.append(Spacer(1, 14))

    doc.build(content)
    buffer.seek(0)
    return buffer

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

# ------------ UI ------------
st.title("📘 왕초보 영어 2024 하편 학습 뷰어")
st.markdown("🔹 DAY 번호를 입력하거나 ⏮⏭ 버튼으로 이동하세요.")

# 현재 DAY 상태 관리
if "current_day" not in st.session_state:
    st.session_state.current_day = day_list[0]

# 입력창 (Enter로 바로 이동)
query = st.text_input("DAY 번호 입력 (예: 5 또는 005)", value=st.session_state.current_day)

norm = normalize_day(query)
if norm and norm in data and norm != st.session_state.current_day:
    st.session_state.current_day = norm
    st.rerun()

# 이전 / 다음 버튼 한 줄 배치
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

# ------------ 현재 DAY 내용 표시 ------------
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

# 🎧 오디오 자동 연결
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
