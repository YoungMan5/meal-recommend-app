# login.py
import streamlit as st
from db import login, create_user, init_db
from utils import load_css


load_css("styles.css")
init_db()

st.title("ログイン / 新規登録")

tab1, tab2 = st.tabs(["ログイン", "新規登録"])

with tab1:
    user_id = st.text_input("ユーザID")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        uid = login(user_id, password)
        if uid:
            st.session_state["user_id"] = uid
            st.success("ログイン成功！")
            st.switch_page("pages/02_MealInput.py")
        else:
            st.error("IDまたはパスワードが違います")

with tab2:
    new_user = st.text_input("新しいユーザID")
    new_pass = st.text_input("パスワード（登録用）", type="password")

    if st.button("登録"):
        if not new_user or not new_pass:
            st.error("ユーザーIDとパスワードを入力してください")
        else:
            new_uid = create_user(new_user, new_pass)
            if new_uid:  # 数字が返る
                st.session_state["user_id"] = new_uid
                st.success("登録完了しました。")
                st.switch_page("pages/01_Profile.py")
            else:
                st.error("そのユーザーIDは既に存在します。")
