import streamlit as st
import pandas as pd
import random

st.title("JLPT 형용사 퀴즈 (10문항)")

# 데이터 불러오기
df = pd.read_csv("data/words_adj.csv")

st.subheader("테마 선택")
theme = st.radio("선택", ["い형용사", "な형용사", "형용사 MIX"])

if st.button("10문제 생성"):
    if theme == "い형용사":
        pool = df[df["pos"] == "i_adj"]
    elif theme == "な형용사":
        pool = df[df["pos"] == "na_adj"]
    else:
        pool = df[df["pos"].isin(["i_adj", "na_adj"])]

    questions = pool.sample(n=10, replace=False)
    st.session_state["today_set"] = questions

if "today_set" in st.session_state:
    st.subheader("오늘의 10문제")
    for i, row in enumerate(st.session_state["today_set"].iterrows(), start=1):
        r = row[1]
        st.write(f"{i}. {r['jp_word']}  ({r['pos']})")
