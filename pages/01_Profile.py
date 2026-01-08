# pages/01_Profile.py
import streamlit as st
from db import get_user_profile, save_user_profile
from utils import load_css
import datetime

load_css("styles.css")
st.set_page_config(page_title="プロフィール", layout="wide")
st.title("👤 プロフィール")

if "user_id" not in st.session_state:
    st.error("ログインしてください（トップページ）。")
    st.stop()

user_id = st.session_state["user_id"]

#既存プロフィール読み込み
profile = get_user_profile(user_id) or {}

name = st.text_input("名前", profile.get("name", ""))
age = st.number_input("年齢", 1, 120, profile.get("age", 20))
gender = st.selectbox("性別", ["男性", "女性", "その他"], index=["男性","女性","その他"].index(profile.get("gender","男性")))
height = st.number_input("身長 (cm)", 80.0, 250.0, profile.get("height", 170.0))
weight = st.number_input("体重 (kg)", 20.0, 200.0, profile.get("weight", 60.0))
goal = st.selectbox("目標", ["体重維持", "ダイエット", "筋増量"], index=["体重維持","ダイエット","筋増量"].index(profile.get("goal","体重維持")))
activity_level = st.slider("運動頻度（週あたり）", 0, 7, profile.get("activity_level", 0))
favorite_food = st.text_input("好きな食べ物", profile.get("favorite_food", ""))

if st.button("プロフィール保存"):
    save_user_profile(user_id, {
        "name": name,
        "age": age,
        "gender": gender,
        "height": height,
        "weight": weight,
        "goal": goal,
        "activity_level": activity_level,
        "favorite_food": favorite_food
    })
    st.success("プロフィールを保存しました！")
    st.switch_page("pages/02_MealInput.py")
