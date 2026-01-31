from pathlib import Path
import random
import pandas as pd
import streamlit as st
from supabase import create_client

if "SUPABASE_URL" not in st.secrets or "SUPABASE_ANON_KEY" not in st.secrets:
    st.error("Supabase Secrets가 설정되지 않았습니다. (SUPABASE_URL / SUPABASE_ANON_KEY)")
    st.stop()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def auth_box():
    st.subheader("로그인")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        email = st.text_input("이메일", key="login_email")
        pw = st.text_input("비밀번호", type="password", key="login_pw")
        
        if st.button("로그인", use_container_width=True):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
        
            else:            
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                st.success("로그인 완료!")
                st.rerun()

    with tab2:
        email = st.text_input("이메일", key="signup_email")
        pw = st.text_input("비밀번호", type="password", key="signup_pw")
        
        if st.button("회원가입", use_container_width=True):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
            
            else:
            sb.auth.sign_up({"email": email, "password": pw})
            st.success("회원가입 요청 완료! 이메일 인증이 필요할 수 있어요.")
            # Supabase 설정에 따라 이메일 인증 on/off

def require_login():
    if "user" not in st.session_state or st.session_state.user is None:
        auth_box()
        st.stop()

require_login()
user_id = st.session_state.user.id

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="JLPT Quiz", layout="centered")
st.title("하테나일본어 형용사 퀴즈")

NAVER_TALK_URL = "https://talk.naver.com/W45141"
LEVEL = "N4"
N = 10
QUESTION_TYPES = ["reading", "meaning"]

# =====================
# CSV 로드
# =====================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "words_adj_300.csv"

df = pd.read_csv(CSV_PATH)
if len(df.columns) == 1 and "\t" in df.columns[0]:
    df = pd.read_csv(CSV_PATH, sep="\t")

df.columns = df.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()

pool = df[df["level"] == LEVEL].copy()
if len(pool) < N:
    st.error(f"단어가 부족합니다: pool={len(pool)}")
    st.stop()

# =====================
# 유틸 함수들
# =====================
def get_base_pool_for_mode(mode: str) -> pd.DataFrame:
    """현재 모드에 맞는 '출제/보기' 기준 풀"""
    if mode == "i_adj":
        return pool[pool["pos"] == "i_adj"].copy()
    if mode == "na_adj":
        return pool[pool["pos"] == "na_adj"].copy()
    return pool[pool["pos"].isin(["i_adj", "na_adj"])].copy()


def make_question(row: pd.Series, base_pool: pd.DataFrame) -> dict:
    """
    보기(오답)는 정답과 같은 pos에서만 뽑는다.
    base_pool: 현재 모드에 맞는 풀(혼합이면 i+na 전체)
    """
    qtype = random.choice(QUESTION_TYPES)

    target_pos = row["pos"]
    same_pos_pool = base_pool[base_pool["pos"] == target_pos]

    if qtype == "reading":
        prompt = f"{row['jp_word']}의 발음은?"
        correct = row["reading"]
        candidates = (
            same_pos_pool[same_pos_pool["reading"] != correct]["reading"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )
    else:
        prompt = f"{row['jp_word']}의 뜻은?"
        correct = row["meaning"]
        candidates = (
            same_pos_pool[same_pos_pool["meaning"] != correct]["meaning"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )

    if len(candidates) < 3:
        st.error(f"오답 후보 부족: pos={target_pos}, 후보={len(candidates)}개")
        st.stop()

    wrongs = random.sample(candidates, 3)
    choices = wrongs + [correct]
    random.shuffle(choices)

    return {
        "prompt": prompt,
        "choices": choices,
        "correct_text": correct,
        "jp_word": row["jp_word"],
        "reading": row["reading"],
        "meaning": row["meaning"],
        "pos": row["pos"],
    }


def build_quiz(mode: str) -> list:
    """
    - i_adj  : 10문항
    - na_adj : 10문항
    - mix    : い 5 + な 5 (5:5 고정)
    """
    base_pool = get_base_pool_for_mode(mode)

    if mode == "mix":
        i_pool = base_pool[base_pool["pos"] == "i_adj"].copy()
        na_pool = base_pool[base_pool["pos"] == "na_adj"].copy()

        if len(i_pool) < 5 or len(na_pool) < 5:
            st.error(f"혼합 모드 단어 부족: i={len(i_pool)}, na={len(na_pool)}")
            st.stop()

        sampled = pd.concat(
            [i_pool.sample(n=5), na_pool.sample(n=5)],
            ignore_index=True
        ).sample(frac=1).reset_index(drop=True)
    else:
        filtered = base_pool[base_pool["pos"] == mode].copy()
        if len(filtered) < N:
            st.error(f"단어가 부족합니다: mode={mode}, pool={len(filtered)}")
            st.stop()
        sampled = filtered.sample(n=N).reset_index(drop=True)

    quiz = [make_question(sampled.iloc[i], base_pool) for i in range(len(sampled))]
    return quiz


def build_quiz_from_wrongs(wrong_list: list, mode: str) -> list:
    """
    틀린 문제만 다시 풀기용 퀴즈 생성
    - wrong_list: 채점에서 만든 리스트
    - mode: 현재 모드(i_adj/na_adj/mix)
    """
    base_pool = get_base_pool_for_mode(mode)
    wrong_words = list({w["단어"] for w in wrong_list})

    retry_df = base_pool[base_pool["jp_word"].isin(wrong_words)].copy()
    if len(retry_df) == 0:
        st.error("오답 단어를 풀에서 찾지 못했습니다. (jp_word 매칭 확인 필요)")
        st.stop()

    retry_df = retry_df.sample(frac=1).reset_index(drop=True)
    retry_quiz = [make_question(retry_df.iloc[i], base_pool) for i in range(len(retry_df))]
    return retry_quiz


def render_naver_talk():
    """제출 후에만 보여줄 상담 배너"""
    st.divider()
    st.markdown(
        f"""
<style>
@keyframes floaty {{
  0% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-6px); }}
  100% {{ transform: translateY(0); }}
}}
@keyframes ping {{
  0% {{ transform: scale(1); opacity: 0.9; }}
  70% {{ transform: scale(2.2); opacity: 0; }}
  100% {{ transform: scale(2.2); opacity: 0; }}
}}

.floating-naver-talk,
.floating-naver-talk:visited,
.floating-naver-talk:hover,
.floating-naver-talk:active {{
  position: fixed;
  right: 18px;
  bottom: 90px;
  z-index: 99999;
  text-decoration: none !important;
  color: inherit !important;
}}

.floating-wrap {{
  position: relative;
  animation: floaty 2.2s ease-in-out infinite;
}}

.talk-btn {{
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
  text-decoration: none !important;
}}

.talk-btn:hover {{ filter: brightness(0.95); }}

.talk-text small {{
  display: block;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.95;
  margin-top: 2px;
}}

.badge {{
  position: absolute;
  top: -6px;
  right: -6px;
  width: 12px;
  height: 12px;
  background: #ff3b30;
  border-radius: 999px;
  box-shadow: 0 6px 14px rgba(0,0,0,0.25);
}}

.badge::after {{
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
}}

@media (max-width: 600px) {{
  .floating-naver-talk {{ bottom: 110px; right: 14px; }}
  .talk-btn {{ padding: 13px 16px; font-size: 14px; }}
  .talk-text small {{ font-size: 11px; }}
}}
</style>

<a class="floating-naver-talk" href="{NAVER_TALK_URL}" target="_blank" rel="noopener noreferrer">
  <div class="floating-wrap">
    <span class="badge"></span>
    <button class="talk-btn" type="button">
      <span>💬</span>
      <span class="talk-text">
        1:1 하테나쌤 상담
        <small>수강신청 문의하기</small>
      </span>
    </button>
  </div>
</a>
""",
        unsafe_allow_html=True
    )

# =====================
# 세션 초기화
# =====================
if "history" not in st.session_state:
    st.session_state.history = []   # 매 회차 기록(점수, 문항수 등)
if "wrong_counter" not in st.session_state:
    st.session_state.wrong_counter = {}  # 틀린 단어 누적 카운트
if "total_counter" not in st.session_state:
    st.session_state.total_counter = {}  # 나온 단어(출제) 누적 카운트

if "pos_mode" not in st.session_state:
    st.session_state.pos_mode = "mix"
if "quiz_version" not in st.session_state:
    st.session_state.quiz_version = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []

if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz(st.session_state.pos_mode)

# =====================
# 상단 UI (출제 유형/새문제/초기화)
# =====================
mode_label_map = {"i_adj": "い형용사", "na_adj": "な형용사", "mix": "형용사 혼합"}

selected = st.radio(
    "출제 유형",
    options=["i_adj", "na_adj", "mix"],
    format_func=lambda x: mode_label_map[x],
    horizontal=True,
    index=["i_adj", "na_adj", "mix"].index(st.session_state.pos_mode),
)

if selected != st.session_state.pos_mode:
    st.session_state.pos_mode = selected
    st.session_state.quiz = build_quiz(selected)
    st.session_state.submitted = False
    st.session_state.wrong_list = []
    st.session_state.quiz_version += 1
    st.rerun()

st.caption(f"현재 선택: **{mode_label_map[st.session_state.pos_mode]}**")
st.divider()

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 새 문제(랜덤 10문항)", use_container_width=True):
        st.session_state.quiz = build_quiz(st.session_state.pos_mode)
        st.session_state.submitted = False
        st.session_state.wrong_list = []
        st.session_state.quiz_version += 1
        st.rerun()

with col2:
    if st.button("🧹 선택 초기화", use_container_width=True):
        st.session_state.submitted = False
        st.session_state.quiz_version += 1
        st.rerun()

st.divider()

# =====================
# answers 길이 자동 맞춤 (오답 다시풀기 대비)
# =====================
quiz_len = len(st.session_state.quiz)
if "answers" not in st.session_state or len(st.session_state.answers) != quiz_len:
    st.session_state.answers = [None] * quiz_len

# =====================
# 문제 표시
# =====================
for idx, q in enumerate(st.session_state.quiz):
    st.subheader(f"Q{idx+1}")
    st.write(q["prompt"])

    choice = st.radio(
        label="보기",
        options=q["choices"],
        index=None,
        key=f"q_{st.session_state.quiz_version}_{idx}",
        label_visibility="collapsed",
    )

    st.session_state.answers[idx] = choice
    st.divider()

# =====================
# 제출/채점
# =====================
all_answered = all(a is not None for a in st.session_state.answers)
if st.button("✅ 제출하고 채점하기", disabled=not all_answered, type="primary", use_container_width=True):
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
                "No": idx + 1,
                "문제": q["prompt"],
                "내 답": picked,
                "정답": correct,
                "단어": q["jp_word"],
                "읽기": q["reading"],
                "뜻": q["meaning"],
            })

    st.session_state.wrong_list = wrong_list

    st.success(f"점수: {score} / {quiz_len}")
    ratio = score / quiz_len if quiz_len else 0
    # --- 누적 기록 저장(세션) ---
    st.session_state.history.append({
        "mode": st.session_state.pos_mode,
        "score": score,
        "total": quiz_len,
    })

    # --- 출제/오답 카운트 누적 ---
    for idx, q in enumerate(st.session_state.quiz):
        word = q["jp_word"]
        st.session_state.total_counter[word] = st.session_state.total_counter.get(word, 0) + 1

        picked = st.session_state.answers[idx]
        if picked != q["correct_text"]:
            st.session_state.wrong_counter[word] = st.session_state.wrong_counter.get(word, 0) + 1
    
    if ratio == 1:
        st.balloons()
        st.success("🎉 완벽해요! 전부 정답입니다. 정말 잘했어요!")
    elif ratio >= 0.7:
        st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
    else:
        st.warning("💪 괜찮아요! 틀린 문제는 성장의 재료예요. 다시 한 번 도전해봐요.")

    # ✅ 오답 있을 때만: 버튼 1번만!
    if len(st.session_state.wrong_list) > 0:
        st.subheader("❌ 오답 노트")

        if st.button("❌ 틀린 문제만 다시 풀기", type="primary", use_container_width=True, key="retry_wrong"):
            st.session_state.quiz = build_quiz_from_wrongs(st.session_state.wrong_list, st.session_state.pos_mode)
            st.session_state.submitted = False
            st.session_state.quiz_version += 1
            st.rerun()

        for w in st.session_state.wrong_list:
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
    st.divider()
    st.subheader("📊 누적 학습 현황 (이번 세션)")

    # 누적 점수/문항
    total_attempts = sum(x["total"] for x in st.session_state.history) if st.session_state.history else 0
    total_score = sum(x["score"] for x in st.session_state.history) if st.session_state.history else 0
    acc = (total_score / total_attempts) if total_attempts else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("누적 회차", len(st.session_state.history))
    c2.metric("누적 점수", f"{total_score} / {total_attempts}")
    c3.metric("누적 정답률", f"{acc*100:.0f}%")

    # 자주 틀리는 단어 TOP5
    if st.session_state.wrong_counter:
        st.markdown("#### ❌ 자주 틀리는 단어 TOP 5")
        top5 = sorted(st.session_state.wrong_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        for rank, (w, cnt) in enumerate(top5, start=1):
            total_seen = st.session_state.total_counter.get(w, 0)
            st.write(f"{rank}. **{w}**  —  {cnt}회 오답 / {total_seen}회 출제")
    else:
        st.info("아직 오답 누적 데이터가 없습니다.")
    if st.button("🗑️ 누적 기록 초기화", use_container_width=True):
        st.session_state.history = []
        st.session_state.wrong_counter = {}
        st.session_state.total_counter = {}
        st.rerun()

    # ✅ 제출 후에만 상담 배너 노출
    render_naver_talk()
