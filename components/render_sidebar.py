import streamlit as st

def render_sidebar(active=None):
    with st.sidebar:
        st.markdown("## 📂 メニュー")

        page = st.radio(
            "",
            ["🏠 ホーム", "🔐 ログイン", "👤 プロフィール", "🍽 食事", "🎮 RPG", "🏅 称号"],
            index=0,
            key="sidebar_nav"
        )

    # ページ遷移
    if page == "🏠 ホーム":
        st.switch_page("app.py")
    elif page == "🔐 ログイン":
        st.switch_page("pages/00_Login.py")
    elif page == "👤 プロフィール":
        st.switch_page("pages/01_Profile.py")
    elif page == "🍽 食事":
        st.switch_page("pages/02_MealInput.py")
    elif page == "🎮 RPG":
        st.switch_page("pages/03_RPG_and_Gacha.py")
    elif page == "🏅 称号":
        st.switch_page("pages/04_Badges.py")
