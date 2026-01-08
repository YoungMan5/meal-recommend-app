import streamlit as st

def render_sidebar(is_admin=False):
    with st.sidebar:
        st.markdown("## Menu")

        if not is_admin:
            st.page_link("pages/00_Login.py", label="🔐 ログイン")
            st.page_link("pages/01_Profile.py", label="👤 プロフィール")
            st.page_link("pages/02_MealInput.py", label="🍱 食事登録")
            st.page_link("pages/03_RPG_and_Gacha.py", label="🎮 RPG")
            st.page_link("pages/04_Badges.py", label="🏅 実績")
        else:
            st.page_link("pages/_hidden_Admin.py", label="🛠 Admin")