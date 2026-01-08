import streamlit as st
import os
import time
import random
import base64
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from utils import load_css, calc_nutrient_targets
import json

from db import load_meals, load_user_badges, save_user_badge, get_user_profile
from components.render_sidebar import render_sidebar

load_css("styles.css")
render_sidebar(is_admin=False)
st.set_page_config(page_title="実績", layout="wide")
st.title("📛 実績一覧")


# =========================================================
# 🎵 効果音（非表示で自動再生）
# =========================================================
def play_sound_hidden(sound_path):
    if not os.path.exists(sound_path):
        return

    with open(sound_path, "rb") as f:
        data = f.read()

    b64 = base64.b64encode(data).decode()
    st.markdown(
        f"""
        <audio autoplay style="display:none;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 🎉 紙吹雪エフェクト
# =========================================================
def confetti():
    unique_id = random.randint(0, 1_000_000)
    components.html(
        f"""
        <div id="confetti_{unique_id}"></div>
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
        <script>
        var duration = 1.5 * 1000;
        var end = Date.now() + duration;

        (function frame() {{
            confetti({{
                particleCount: 5,
                spread: 120,
                startVelocity: 25,
                origin: {{ x: Math.random(), y: Math.random() - 0.2 }}
            }});
            if (Date.now() < end) requestAnimationFrame(frame);
        }})();
        </script>
        """,
        height=0,
        width=0
    )


# =========================================================
# ✨ GIF → PNG 切り替え（アニメーション再生）
# =========================================================
def play_gif_once(placeholder, gif_path, png_path, width=120, duration=1.4):
    placeholder.empty()
    time.sleep(0.05)

    if os.path.exists(gif_path):
        placeholder.image(gif_path, width=width)
    time.sleep(duration)

    if os.path.exists(png_path):
        placeholder.image(png_path, width=width)


# =========================================================
# 🔥 バッジの条件判定ロジック
# =========================================================

def get_streak(user_id):
    """連続日数（食事登録）"""
    meals = load_meals(user_id)
    dates = sorted({m["date"] for m in meals}, reverse=True)

    if not dates:
        return 0

    streak = 1
    today = datetime.now().date()

    for i in range(1, len(dates)):
        d1 = datetime.fromisoformat(dates[i-1]).date()
        d2 = datetime.fromisoformat(dates[i]).date()
        if (d1 - d2).days == 1:
            streak += 1
        else:
            break

    return streak


def get_morning_streak(user_id):
    """朝食3日連続"""
    meals = load_meals(user_id)
    today = datetime.now().date()
    streak = 0

    for offset in range(3):
        day = today - timedelta(days=offset)
        exists = any(m["date"] == day.isoformat() and m["category"] == "朝食" for m in meals)
        if exists:
            streak += 1
        else:
            break

    return streak


from datetime import datetime, timedelta

def get_no_late_streak(user_id):
    """夜食（22〜3時）をしなかった日が何日連続しているか"""
    meals = load_meals(user_id)
    today = datetime.now().date()
    streak = 0

    for offset in range(7):
        day = today - timedelta(days=offset)

        day_meals = [
            m for m in meals
            if m["date"] == day.isoformat()
        ]

        # ❌ 食事記録が1件もない日は継続不可
        if not day_meals:
            break

        has_late = False
        for m in day_meals:
            hour = int(m["time"].split(":")[0])
            if hour >= 22 or hour < 3:
                has_late = True
                break

        # 夜食してたら終了
        if has_late:
            break

        streak += 1

    return streak

# =========================================================
# 🔐 ユーザーID 必須
# =========================================================
if "user_id" not in st.session_state:
    st.error("ログインしてください")
    st.stop()

user_id = st.session_state["user_id"]

earned = load_user_badges(user_id)

# =========================================================
# ⭐ 実績バッジリスト（このまま運用）
# =========================================================
BADGES = [
    {
        "id": "first",
        "req": 1,
        "title": "はじめの一歩",
        "desc": "初めて食事を記録する",
        "func": lambda uid: 1 if load_meals(uid) else 0,
    },
    {
        "id": "3days",
        "req": 3,
        "title": "三日坊主卒業",
        "desc": "食事記録を3日連続で続ける",
        "func": get_streak,
    },
    {
        "id": "7days",
        "req": 7,
        "title": "習慣化の兆し",
        "desc": "食事記録を7日連続で続ける",
        "func": get_streak,
    },
    {
        "id": "30days",
        "req": 30,
        "title": "日常茶飯事",
        "desc": "食事記録を30日連続で続ける",
        "func": get_streak,
    },
    {
        "id": "early_morning",
        "req": 3,
        "title": "1日の準備",
        "desc": "朝食を3日連続で続ける",
        "func": get_morning_streak,
    },
    {
        "id": "prohabit_late_night_snack",
        "req": 7,
        "title": "健康的習慣",
        "desc": "夜食を7日間しなかった",
        "func": get_no_late_streak,
    },
]

# =========================================================
# 🏆 バッジ表示
# =========================================================
cols = st.columns(5)

for i, badge in enumerate(BADGES):
    badge_id = badge["id"]
    req = badge["req"]
    title = badge["title"]
    desc = badge["desc"]
    func = badge["func"]

    col = cols[i % 5]

    # 進捗
    progress = func(user_id)
    ratio = min(progress / req, 1)
    is_earned = badge_id in earned

    # 素材
    base = f"assets/images/badges/{badge_id}"
    gray = base + "_gray.png"
    color = base + ".png"
    shine = base + "_shine.gif"
    sound = "assets/sounds/rappa.mp3"

    st.markdown("""
    <style>
    .badge-card {
        border-radius:14px;
        padding:12px;
        box-shadow:0 4px 12px rgba(0,0,0,0.15);
        text-align:center;
        width:200px;
        margin:0 auto;
    }
    .badge-title {
        font-weight:bold;
        margin-top:6px;
    }
    .badge-desc {
        font-size:12px;
        color:#666;
    }
    .progress-wrap {
        width:110px;
        margin:8px auto 4px;
    }
    </style>
    """, unsafe_allow_html=True)


    with col:
        # 画像位置を制御する columns
        left, center, right = st.columns([1, 3, 1])

        with center:
            img_ph = st.empty()   # ← ここが超重要

            if is_earned:
                img_ph.image(color, width=110)
            else:
                img_ph.image(color if progress >= req else gray, width=110)

        # まずカードHTMLを全部描画
        st.markdown(f"""
        <div class="badge-card">
        <div id="img-{badge_id}"></div>

        <div class="badge-title">{badge['title']}</div>
        <div class="badge-desc">{badge['desc']}</div>

        <div class="progress-wrap">
            <div style="height:8px;background:#eee;border-radius:4px;">
                <div style="
                    height:8px;
                    width:{ratio*100}%;
                    background:#6cc36c;
                    border-radius:4px;
                "></div>
            </div>
            <div style="font-size:11px;">{progress} / {req}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


        # 獲得ボタン
        if not is_earned and progress >= req:
            if st.button("🏆 獲得", key=badge_id):
                save_user_badge(user_id, badge_id)
                play_sound_hidden(sound)
                confetti()
                play_gif_once(img_ph, shine, color, width=110)
                st.rerun()



