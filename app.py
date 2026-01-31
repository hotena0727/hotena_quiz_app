from pathlib import Path
import random
import pandas as pd
import streamlit as st

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="JLPT Quiz", layout="centered")
st.title("い형용사 퀴즈")

# =====================
# CSV 경로 (GitHub/Streamlit Cloud 안전)
# =====================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "words_adj_300.csv"

# =====================
# CSV 불러오기 (콤마/탭 자동 대응)
# =====================
df = pd.read_csv(CSV_PATH)
if len(df.columns) == 1 and "\t" in df.columns[0]:
    df = pd.read_csv(CSV_PATH, sep="\t")

# BOM/공백 제거
df.columns = df.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()

# =====================
# 설정 (STEP1 생략: 고정값)
# =====================
LEVEL = "N4"
POS_LIST = ["i_adj", "na_adj"]
N = 10

pool = df[
    (df["level"] == LEVEL) &
    (df["pos"].isin(POS_LIST))
].copy()

if len(pool) < N:
    st.error(f"단어가 부족합니다: pool={len(pool)}")
    st.stop()

# =====================
# 출제 타입: reading / meaning 랜덤
# - reading: jp_word(문제) -> reading 고르기
# - meaning: jp_word(문제) -> meaning(한국어 뜻) 고르기
# =====================
QUESTION_TYPES = ["reading", "meaning"]

def make_question(row, pool_df):
    """
    row: 정답 단어 1개
    pool_df: 같은 풀에서 오답 추출
    return dict with: qtype, prompt, choices(list), correct_index(int), correct_text
    """
    qtype = random.choice(QUESTION_TYPES)

    if qtype == "reading":
        prompt = f"{row['jp_word']}의 발음은?"
        correct = row["reading"]

        wrongs = (
            pool_df[pool_df["reading"] != correct]["reading"]
            .dropna()
            .drop_duplicates()
            .sample(n=3, replace=False)
            .tolist()
        )

    else:  # meaning
        prompt = f"{row['jp_word']}의 뜻은?"
        correct = row["meaning"]

        wrongs = (
            pool_df[pool_df["meaning"] != correct]["meaning"]
            .dropna()
            .drop_duplicates()
            .sample(n=3, replace=False)
            .tolist()
        )

        wrongs = list(set(wrongs))
        
    choices = wrongs + [correct]
    random.shuffle(choices)
    correct_index = choices.index(correct)

    return {
        "qtype": qtype,
        "prompt": prompt,
        "choices": choices,
        "correct_index": correct_index,
        "correct_text": correct,
        "jp_word": row["jp_word"],
        "reading": row["reading"],
        "meaning": row["meaning"],
    }

def build_quiz():
    # 10개 랜덤 출제
    sampled = pool.sample(n=N).reset_index(drop=True)
    quiz = [make_question(sampled.iloc[i], pool) for i in range(N)]
    return quiz

# =====================
# 세션: 퀴즈 유지/재생성
# =====================
if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz()
    st.session_state.submitted = False
    st.session_state.answers = [None] * N

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 새 문제(랜덤 10문항)"):
        st.session_state.quiz = build_quiz()
        st.session_state.submitted = False
        st.session_state.answers = [None] * N

with col2:
    if st.button("🧹 선택 초기화"):
        st.session_state.submitted = False
        st.session_state.answers = [None] * N

st.divider()

# =====================
# 문제 표시
# =====================
for idx, q in enumerate(st.session_state.quiz):
    st.subheader(f"Q{idx+1}")
    st.write(q["prompt"])

    choice = st.radio(
        label="보기",
        options=q["choices"],
        index=None if st.session_state.answers[idx] is None else q["choices"].index(st.session_state.answers[idx]),
        key=f"q_{idx}",
        label_visibility="collapsed"
    )

    st.session_state.answers[idx] = choice
    st.divider()

# =====================
# 제출/채점
# =====================
all_answered = all(a is not None for a in st.session_state.answers)

if st.button("✅ 제출하고 채점하기", disabled=not all_answered):
    st.session_state.submitted = True

if not all_answered:
    st.info("모든 문제에 답을 선택하면 제출 버튼이 활성화됩니다.")

if st.session_state.submitted:
    score = 0
    wrong_list = []

    for idx, q in enumerate(st.session_state.quiz):
        picked = st.session_state.answers[idx]
        correct = q["correct_text"]

        if picked == correct:
            score += 1
        else:
            wrong_list.append({
                "No": idx+1,
                "문제": q["prompt"],
                "내 답": picked,
                "정답": correct,
                "단어": q["jp_word"],
                "읽기": q["reading"],
                "뜻": q["meaning"],
            })

    st.success(f"점수: {score} / {N}")
    
    ratio = score / N

    if ratio == 1:
        st.balloons()
        st.success("🎉 완벽해요! 전부 정답입니다. 정말 잘했어요!")
    elif ratio >= 0.7:
        st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
    else:
        st.warning("💪 괜찮아요! 틀린 문제는 성장의 재료예요. 다시 한 번 도전해봐요.")


    if wrong_list:
        st.subheader("❌ 오답 노트")

    for w in wrong_list:
        st.markdown(
            f"""
**Q{w['No']}**

- 문제: {w['문제']}
- ❌ 내 답: **{w['내 답']}**
- ✅ 정답: **{w['정답']}**

📌 단어 정리  
- 표기: **{w['단어']}**  
- 읽기: {w['읽기']}  
- 뜻: {w['뜻']}

---
"""
        )
    else:
        pass
