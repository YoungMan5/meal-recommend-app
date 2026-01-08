import streamlit as st
import sqlite3
import pandas as pd

ADMIN_PASSWORD = "admin123"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.title("管理者ログイン")

if not st.session_state.is_admin:
    pw = st.text_input("管理者パスワード", type="password")

    if st.button("ログイン"):
        if pw == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.success("ログイン成功")
            st.rerun()
        else:
            st.error("パスワードが違います")

    st.stop()

# -----------------------------
# 管理者ページ（DB閲覧）
# -----------------------------
st.title("管理者ダッシュボード")

conn = sqlite3.connect("nutrition.db")

st.subheader("ユーザ一覧")
users_df = pd.read_sql("SELECT * FROM users", conn)
st.dataframe(users_df)

st.subheader("食事履歴")
meals_df = pd.read_sql("SELECT * FROM meals", conn)
st.dataframe(meals_df)

st.subheader("CSVエクスポート")
st.download_button(
    "食事履歴をCSVでダウンロード",
    meals_df.to_csv(index=False),
    file_name="meals.csv",
    mime="text/csv"
)