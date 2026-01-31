from pathlib import Path
import random
import pandas as pd
import streamlit as st

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="JLPT Quiz", layout="centered")
st.title("형용사 퀴즈")
NAVER_TALK_URL = "https://talk.naver.com/W45141"  # ✅ 네 네이버톡 링크로 교체

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
N = 10

pool = df[df["level"] == LEVEL].copy()

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
    pool_df: (혼합) 단어 풀
    보기(오답)는 정답과 같은 pos(품사)에서만 뽑는다.
    """
    qtype = random.choice(QUESTION_TYPES)

    # ✅ 정답과 같은 품사(pos)만 후보로 제한
    target_pos = row["pos"]
    same_pos_pool = pool_df[pool_df["pos"] == target_pos]

    if qtype == "reading":
        prompt = f"{row['jp_word']}의 발음은?"
        correct = row["reading"]

        candidates = (
            same_pos_pool[same_pos_pool["reading"] != correct]["reading"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )

    else:  # meaning
        prompt = f"{row['jp_word']}의 뜻은?"
        correct = row["meaning"]

        candidates = (
            same_pos_pool[same_pos_pool["meaning"] != correct]["meaning"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )

    # ✅ 오답 후보가 부족하면 안내
    if len(candidates) < 3:
        st.error(f"오답 후보 부족: pos={target_pos}, 후보={len(candidates)}개")
        st.stop()

    wrongs = random.sample(candidates, 3)

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
        "pos": row["pos"],
    }


def build_quiz():
    """
    pos_mode에 따라 10문제를 만든다.
    - i_adj  : い형용사 10개
    - na_adj : な형용사 10개
    - mix    : い 5개 + な 5개 (5:5 고정)
    """
    mode = st.session_state.get("pos_mode", "mix")

    # ✅ 1) 혼합(5:5)인 경우: 여기서 바로 sampled를 만든 뒤 return으로 끝낸다
    if mode == "mix":
        i_pool = pool[pool["pos"] == "i_adj"].copy()
        na_pool = pool[pool["pos"] == "na_adj"].copy()

        if len(i_pool) < 5 or len(na_pool) < 5:
            st.error(f"혼합 모드 단어 부족: i={len(i_pool)}, na={len(na_pool)}")
            st.stop()

        sampled = pd.concat([
            i_pool.sample(n=5),
            na_pool.sample(n=5)
        ]).sample(frac=1).reset_index(drop=True)

        quiz = [make_question(sampled.iloc[i], sampled) for i in range(N)]
        return quiz

    # ✅ 2) 혼합이 아니라면: 해당 pos에서만 10개 뽑는다
    filtered = pool[pool["pos"] == mode].copy()

    if len(filtered) < N:
        st.error(f"단어가 부족합니다: mode={mode}, pool={len(filtered)}")
        st.stop()

    sampled = filtered.sample(n=N).reset_index(drop=True)
    quiz = [make_question(sampled.iloc[i], filtered) for i in range(N)]
    return quiz

# =====================
# 세션: 퀴즈 유지/재생성
# =====================
if "pos_mode" not in st.session_state:
    st.session_state.pos_mode = "mix"
if "quiz_version" not in st.session_state:
    st.session_state.quiz_version = 0
if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz()
    st.session_state.submitted = False
    st.session_state.answers = [None] * N

mode_label_map = {
    "i_adj": "い형용사",
    "na_adj": "な형용사",
    "mix": "MIX",
}

selected = st.radio(
    "출제 유형",
    options=["i_adj", "na_adj", "mix"],
    format_func=lambda x: mode_label_map[x],
    horizontal=True,
    index=["i_adj", "na_adj", "mix"].index(st.session_state.pos_mode),
)

if selected != st.session_state.pos_mode:
    st.session_state.pos_mode = selected
    st.session_state.quiz = build_quiz()
    st.session_state.answers = [None] * N
    st.session_state.submitted = False
    st.session_state.quiz_version += 1

st.caption(f"현재 선택: **{mode_label_map[st.session_state.pos_mode]}**")
st.divider()

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
        st.session_state.quiz_version += 1

st.divider()

# =====================
# 문제 표시
# =====================
# =====================
# 문제 표시
# =====================
for idx, q in enumerate(st.session_state.quiz):
    st.subheader(f"Q{idx+1}")
    st.write(q["prompt"])

    # ✅ 핵심: quiz_version을 key에 포함 -> 초기화 버튼 누르면 key가 바뀌어 선택이 싹 사라짐
    choice = st.radio(
        label="보기",
        options=q["choices"],
        index=None,
        key=f"q_{st.session_state.quiz_version}_{idx}",
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
    st.divider()
    st.markdown("### 💬 일본어 공부, 여기서 막히셨나요?")

    st.markdown(
    """
    <style>
    @keyframes floaty {
        0%   { transform: translateY(0); }
        50%  { transform: translateY(-6px); }
        100% { transform: translateY(0); }
    }

    @keyframes ping {
        0%   { transform: scale(1); opacity: 0.9; }
        70%  { transform: scale(2.2); opacity: 0; }
        100% { transform: scale(2.2); opacity: 0; }
    }

    .floating-naver-talk {
        position: fixed;
        right: 18px;
        bottom: 90px;   /* footer 위로 */
        z-index: 99999;
        text-decoration: none;
    }

    .floating-wrap {
        position: relative;
        animation: floaty 2.2s ease-in-out infinite;
    }

    .talk-btn {
        background: #03C75A;
        color: #fff;
        border: 0;
        border-radius: 999px;
        padding: 14px 18px;
        font-size: 15px;
        font-weight: 700;
        box-shadow: 0 12px 28px rgba(0,0,0,0.22);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        line-height: 1.1;
        text-decoration: none !important; /*
    }

    .talk-btn:hover { filter: brightness(0.95); }

    .talk-text small {
        display: block;
        font-size: 12px;
        font-weight: 600;
        opacity: 0.95;
        margin-top: 2px;
    }

    /* 🔴 빨간 알림 점 */
    .badge {
        position: absolute;
        top: -6px;
        right: -6px;
        width: 12px;
        height: 12px;
        background: #ff3b30;
        border-radius: 999px;
        box-shadow: 0 6px 14px rgba(0,0,0,0.25);
    }

    /* 🔴 빨간 점이 ‘펑펑’ 울리는 링 */
    .badge::after {
        content: "";
        position: absolute;
        left: 50%;
        top: 50%;
        width: 12px;
        height: 12px;
        transform: translate(-50%, -50%);
        border-radius: 999px;
        background: rgba(255,59,48,0.55);
        animation: ping 1.2s ease-out infinite;
    }

    /* 모바일에서 너무 아래면 살짝 올리기 */
    @media (max-width: 600px) {
        .floating-naver-talk,
        .floating-naver-talk:visited,
        .floating-naver-talk:hover,
        .floating-naver-talk:active {
            text-decoration: none !important;
            color: inherit !important;
    }

    .talk-btn {
        background: #03C75A;
        color: #fff;
        border: 0;
        border-radius: 999px;
        padding: 14px 18px;
        font-size: 15px;
        font-weight: 700;
        box-shadow: 0 12px 28px rgba(0,0,0,0.22);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        line-height: 1.1;
        text-decoration: none !important; /* ✅ 혹시 모를 밑줄 방지 */
    }
    </style>

    <a class="floating-naver-talk" href="https://talk.naver.com/W45141" target="_blank" rel="noopener noreferrer">
        <div class="floating-wrap">
            <span class="badge"></span>
            <button class="talk-btn">
                <span>💬</span>
                <span class="talk-text">
                    하테나쌤 1:1 톡톡 상담
                    <small>수강신청 질문하기</small>
                </span>
            </button>
        </div>
    </a>
    """,
    unsafe_allow_html=True
)
