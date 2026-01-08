# app.py
import streamlit as st
import time
import base64
from utils import load_css

st.set_page_config(page_title="Nutrition App", layout="wide", initial_sidebar_state="collapsed")

load_css("styles.css")
load_css("assets/css/mobile.css")


def load_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

if "show_splash" not in st.session_state:
    st.session_state.show_splash = True

if st.session_state.show_splash:

    img_base64 = load_image_base64("assets/images/title.png")

    st.markdown(
        f"""
        <style>
        .splash-bg {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;

            /* ⭐ 背景を黒に設定 ⭐ */
            background: #000;

            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;

            z-index: 9999;
            transition: opacity 1s ease-out;
        }}

        .splash-image {{
            width: 80%;
            max-width: 300px;
            opacity: 0;
            animation: fadeInImage 2.2s forwards;
        }}

        @keyframes fadeInImage {{
            0% {{ opacity: 0; transform: scale(0.95); }}
            100% {{ opacity: 1; transform: scale(1.0); }}
        }}

        .splash-sub {{
            color: white;
            margin-top: 16px;
            font-size: 20px;
            opacity: 0;
            animation: fadeInSub 2.4s forwards;
            text-shadow: 0 0 8px rgba(0,0,0,0.5);
        }}

        @keyframes fadeInSub {{
            0% {{ opacity: 0; transform: translateY(10px); }}
            100% {{ opacity: 1; transform: translateY(0); }}
        }}

        .fade-out {{
            opacity: 0 !important;
        }}
        </style>

        <div id="splash" class="splash-bg">
            <img src="data:image/png;base64,{img_base64}" class="splash-image" />
            <div class="splash-sub">AIがあなたの健康をサポートします</div>
        </div>

        <script>
        setTimeout(() => {{
            document.getElementById("splash").classList.add("fade-out");
        }}, 2800);
        </script>
        """,
        unsafe_allow_html=True,
    )


    time.sleep(3)
    st.session_state.show_splash = False
    st.switch_page("pages/00_Login.py")
