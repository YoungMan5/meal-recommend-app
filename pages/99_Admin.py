import streamlit as st
import sqlite3
import pandas as pd
from components.render_sidebar import render_sidebar

ADMIN_PASSWORD = "admin123"

render_sidebar(is_admin=False)

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
# 管理者ページ（DB閲覧＋SQL実行）
# -----------------------------
st.title("管理者ダッシュボード")

conn = sqlite3.connect("nutrition.db")
cursor = conn.cursor()

# SQL入力欄
st.subheader("SQL実行")
sql_query = st.text_area("SQLを入力してください（例: SELECT * FROM users;）", height=100)

if st.button("実行"):
    try:
        # SQL実行
        df = pd.read_sql(sql_query, conn)
        st.success("SQL実行成功")
        st.dataframe(df)
    except Exception as e:
        st.error(f"SQL実行エラー: {e}")

# 1. DB内のテーブル一覧を取得
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]

st.write(f"テーブル一覧: {tables}")

# 2. 全テーブルのデータを表示＆ダウンロード
all_data = {}
for table in tables:
    st.subheader(f"{table} テーブル")
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    st.dataframe(df)
    all_data[table] = df