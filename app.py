import streamlit as st
import pandas as pd

st.set_page_config(page_title="구글 시트 연결 테스트", layout="centered")

st.title("🔍 구글 시트 연결 X-레이 테스트")

try:
    SHEET_ID = st.secrets["SHEET_ID"].strip() # 혹시 모를 공백 제거
    SHEET_GID = st.secrets["SHEET_GID"].strip()
except Exception as e:
    st.error(f"Secrets 파일에 문제가 있습니다: {e}")
    st.stop()

# 1. 값이 제대로 들어왔는지 확인
st.write("### 1️⃣ Secrets 값 확인")
st.write(f"- **ID**: `{SHEET_ID}` (길이: {len(SHEET_ID)})")
st.write(f"- **GID**: `{SHEET_GID}` (길이: {len(SHEET_GID)})")

# 2. 완성된 주소 확인
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
st.write("### 2️⃣ 데이터 요청 주소")
st.code(url)

# 3. 데이터 로드 시도 및 실제 에러 메시지 출력
st.write("### 3️⃣ 결과")
try:
    df = pd.read_csv(url)
    st.success("✅ 구글 시트 데이터 로드 성공!")
    st.dataframe(df)
except Exception as e:
    st.error("❌ 연결 실패! 아래의 에러 메시지를 확인하세요.")
    st.code(str(e)) # 진짜 에러 원인을 보여줍니다.
