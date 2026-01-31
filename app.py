from pathlib import Path
import pandas as pd
import streamlit as st

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="JLPT Adjective Quiz", layout="centered")
st.title("JLPT い形容詞クイズ (N4) - 10問")

# =====================
# CSV 경로 (GitHub / Streamlit Cloud 안전)
# =====================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "words_adj_300.csv"

st.caption(f"CSV 경로: {CSV_PATH}")
st.caption(f"CSV 존재: {CSV_PATH.exists()}")

# =====================
# CSV 불러오기 (콤마 / 탭 자동 대응)
# =====================
df = pd.read_csv(CSV_PATH)

# 컬럼이 1개 + 탭이 있으면 TSV로 다시 읽기
if len(df.columns) == 1 and "\t" in df.columns[0]:
    df = pd.read_csv(CSV_PATH, sep="\t")

# BOM / 공백 제거
df.columns = (
    df.columns
    .astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
)

# 확인용 (지금 단계에서만 사용, 나중에 지워도 됨)
st.write("컬럼들:", list(df.columns))
st.dataframe(df.head(3))

# =====================
# STEP1 없이 고정값
# =====================
LEVEL = "N4"
POS = "i_adj"
N = 10

pool = df[(df["level"] == LEVEL) & (df["pos"] == POS)].copy()

if len(pool) < N:
    st.error(f"단어가 부족합니다: pool={len(pool)}")
    st.stop()

# =====================
# 랜덤 10문제
# =====================
questions = pool.sample(n=N).reset_index(drop=True)

st.caption("일단은 랜덤 10개가 정상 출력되는지 확인합니다 (보기/채점은 다음 단계).")

for i, row in questions.iterrows():
    st.write(
        f"Q{i+1}. {row['jp_word']} / {row['reading']} / {row['meaning']}"
    )
