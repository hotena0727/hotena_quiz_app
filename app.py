from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="JLPT Adjective Quiz", layout="centered")
st.title("JLPT い形容詞クイズ (N4) - 10問")

# ✅ GitHub/Streamlit Cloud에서 안전한 경로
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "words_adj_300.csv"

# ✅ (디버그) 파일 존재 여부 확인
st.caption(f"CSV 경로: {CSV_PATH}")
st.caption(f"CSV 존재: {CSV_PATH.exists()}")

# ✅ CSV 불러오기
df = pd.read_csv(CSV_PATH)

# ✅ STEP1 없이: 기본값을 코드에 고정
LEVEL = "N4"
POS = "i_adj"
N = 10

pool = df[(df["level"] == LEVEL) & (df["pos"] == POS)].copy()

if len(pool) < N:
    st.error(f"단어가 부족합니다: pool={len(pool)}")
    st.stop()

# ✅ 랜덤 10개 뽑기
questions = pool.sample(n=N, random_state=None).reset_index(drop=True)

st.caption("일단은 랜덤 10개가 정상 출력되는지 확인합니다 (보기/채점은 다음 단계).")

for i, row in questions.iterrows():
    st.write(f"Q{i+1}. {row['jp_word']}  /  {row['reading']}  /  {row['meaning']}")
