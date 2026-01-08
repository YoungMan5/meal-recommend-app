# pages/03_RPG_and_Gacha.py
import streamlit as st
import os, random, time
from db import load_username, get_progress, add_exp, LEVEL_EXP, get_consecutive_days, get_map_progress, save_map_progress, consume_gacha_coin, get_gacha_coins, add_user_character, load_user_characters, get_conn, has_node_coin, collect_node_coin, ensure_initial_character, set_current_chara, get_current_chara, get_user_titles, get_move_count, consume_move_count, add_move_count
from utils import load_css
from dataclasses import dataclass
from datetime import datetime

load_css("styles.css")
st.set_page_config(page_title="育成＆ガチャ", layout="wide")

if "user_id" not in st.session_state:
    st.error("ログインしてください。")
    st.stop()
user_id = st.session_state["user_id"]
if "username" not in st.session_state:
    st.session_state["username"] = load_username(user_id)

ensure_initial_character(user_id)


# ==========================
# タブ作成
# ==========================
tab_rpg, tab_gacha, tab_chara, tab_map = st.tabs(["🛡️ RPG育成", "🎰 ガチャ", "📘 キャラ図鑑", "📍 冒険マップ"])

# ==========================
# RPGタブ
# ==========================
with tab_rpg:
    st.title("🛡️ 育成画面 (RPG)")

    prog = get_progress(user_id)
    exp = prog["exp"]
    level = prog["level"]

    next_level = min(level + 1, 99)
    next_req = LEVEL_EXP.get(next_level, LEVEL_EXP[level])

    # 使用中称号取得
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT current_title FROM profiles WHERE user_id=?",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()
    current_title = row[0] if row and row[0] else "無名"

    st.markdown(
        f"### 🏷️ 称号：**{current_title}**"
        f"<br>{st.session_state.get('username', '')} さんの状態",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 2])

    # --------------------------
    # 使用中キャラを取得（完全安定版）
    # --------------------------
    if "current_chara" not in st.session_state:
        conn = get_conn()
        c = conn.cursor()

        c.execute(
            "SELECT current_chara FROM profiles WHERE user_id=?",
            (user_id,)
        )
        row = c.fetchone()

        # DBに値がある場合
        if row and row[0]:
            current = row[0]
        else:
            # 初期キャラ
            current = "star1_1.png"
            # ★ DBにも保存しておく（超重要）
            c.execute("""
                INSERT INTO profiles (user_id, current_chara)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                current_chara=excluded.current_chara
                """, (user_id, current))
            conn.commit()

        conn.close()

        st.session_state["current_chara"] = current

    # キャラ画像
    with col1:
        char_file = st.session_state["current_chara"]
        img_path = f"assets/images/characters/{char_file}"
        if os.path.exists(img_path):
            st.image(img_path, width=240)
        else:
            st.markdown(
                "<div style='width:240px;height:240px;background:#333;color:white;"
                "border-radius:12px;display:flex;align-items:center;justify-content:center;'>"
                "NO IMAGE</div>",
                unsafe_allow_html=True
            )

    # レベル情報
    with col2:
        st.markdown(f"#### レベル: {level}")
        st.markdown(f"#### 経験値: {exp} / {next_req}")
        st.progress(exp / next_req if next_req > 0 else 1.0)

        st.markdown("""
        この画面では、あなたの生活習慣が **キャラクターの成長** につながります。

        🍚 **食事を入力すると経験値を獲得**  
        ⭐ 経験値が貯まるとレベルアップ  
        🏅 **レベル5ごとに称号を獲得**し、成長の証が増えていきます

        コツコツ続けて、最強の称号を目指そう！
        """)

        # if st.button("テスト: +10 exp"):
        #     old = level
        #     add_exp(user_id, 10)
        #     new = get_progress(user_id)["level"]
        #     if new > old:
        #         st.balloons()
        #         st.success(f"レベルアップ！ {old} → {new}")
        #     st.rerun()

    # --------------------------
    # 称号一覧
    # --------------------------
    st.subheader("🏷️ 称号一覧")

    titles = get_user_titles(user_id)

    for title in titles:
        cols = st.columns([3, 1])
        cols[0].write(
            f"**{title}**" + (" ← 使用中" if title == current_title else "")
        )

        if cols[1].button(
            "使用する",
            key=f"title_{title}",
            disabled=(title == current_title)
        ):
            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "UPDATE profiles SET current_title=? WHERE user_id=?",
                (title, user_id)
            )
            conn.commit()
            conn.close()
            st.rerun()


# ==========================
# ガチャタブ（修正版）
# ==========================
with tab_gacha:
    import random
    import os
    import time
    from PIL import Image

    st.title("🎰 ガチャガチャ")

    st.markdown("""
    冒険で集めた **ガチャコイン** を使って、新しい報酬を手に入れよう！

    🪙 コインは冒険マップを進めると獲得  
    🎁 様々なキャラクターが手に入る  
    ✨ レアな報酬ほど低確率！

    たくさんのキャラクターをゲットしよう！
    """)
    
    BASE = "assets/images"
    EGG_PATH = f"{BASE}/eggs"
    CHAR_PATH = f"{BASE}/characters"

    # レアリティ（番号→表示ラベル）
    RARITY_LABELS = {1: "N", 2: "R", 3: "SR", 4: "UR", 5: "LEGEND"}

    # 画像関連は番号キーで保持（壊れにくい）
    RARITY_EGG = {1: "egg_n.png", 2: "egg_r.png", 3: "egg_sr.png", 4: "egg_ur.png", 5: "egg_lr.png"}
    RARITY_BREAK = {1: "egg_break_n.png", 2: "egg_break_r.png", 3: "egg_break_sr.png", 4: "egg_break_ur.png", 5: "egg_break_lr.png"}
    RARITY_PROBS = {1: 0.60, 2: 0.20, 3: 0.12, 4: 0.06, 5: 0.02}

    # 初期化
    if "result" not in st.session_state:
        st.session_state.result = None
    if "mode" not in st.session_state:
        st.session_state.mode = "normal"  # normal / anim / result

    # --------------------------
    # Utility
    # --------------------------
    def pick_rarity():
        ids = list(RARITY_PROBS.keys())
        weights = list(RARITY_PROBS.values())
        return random.choices(ids, weights=weights, k=1)[0]

    def load_characters():
        # return dict: rarity_num -> [files]
        data = {k: [] for k in RARITY_LABELS.keys()}
        try:
            for file in os.listdir(CHAR_PATH):
                if not (file.lower().endswith(".png") or file.lower().endswith(".jpg") or file.lower().endswith(".jpeg")):
                    continue
                # try to extract rarity digit from filename (convention dependent)
                # fallback: place into a pool (e.g., N)
                try:
                    rar_num = int(file[4])
                except Exception:
                    # If filename pattern not match, put into '1' (N) bucket to avoid empty lists
                    rar_num = 1
                if rar_num in data:
                    data[rar_num].append(file)
        except FileNotFoundError:
            # folder missing -> keep empty lists
            pass
        return data

    def get_character(rarity_num, chars):
        lst = chars.get(rarity_num, [])
        if not lst:
            # fallback to any available character
            all_files = sum(chars.values(), [])
            if not all_files:
                return None
            return random.choice(all_files)
        return random.choice(lst)

    # --------------------------
    # 合成アニメ（マシンを背景にPILで合成）
    # --------------------------
    def play_machine_roll(egg_path, break_path, char_path):
        placeholder = st.empty()
        try:
            machine = Image.open(f"{BASE}/gacha_machine.png").convert("RGBA")
        except Exception:
            # fallback: create blank canvas
            machine = Image.new("RGBA", (480, 360), (240, 240, 240, 255))

        # load assets safely
        try:
            egg = Image.open(egg_path).convert("RGBA")
        except Exception:
            egg = Image.new("RGBA", (140, 140), (255, 200, 200, 255))
        try:
            break_img = Image.open(break_path).convert("RGBA")
        except Exception:
            break_img = Image.new("RGBA", (200, 200), (255, 220, 220, 255))
        try:
            char = Image.open(char_path).convert("RGBA")
        except Exception:
            char = Image.new("RGBA", (240, 240), (200, 255, 200, 255))

        egg = egg.resize((140, 140))
        break_img = break_img.resize((200, 200))

        # 1) 転がり
        for x in range(-140, 100, 20):
            frame = machine.copy()
            angle = (x * 5) % 360
            egg_rot = egg.rotate(angle, expand=True)
            # position might go out of bounds; that's okay
            frame.paste(egg_rot, (x, 260), egg_rot)
            placeholder.image(frame)
            time.sleep(0.05)

        # 2) 止まる
        frame = machine.copy()
        frame.paste(egg, (80, 260), egg)
        placeholder.image(frame)
        time.sleep(0.25)

        # 3) 割れる
        frame = machine.copy()
        frame.paste(break_img, (50, 240), break_img)
        placeholder.image(frame)
        time.sleep(0.35)

        # 4) キャラ登場（拡大）
        for scale in [0.3, 0.5, 0.7, 0.85, 1.0]:
            frame = machine.copy()
            w = max(1, int(char.width * scale))
            h = max(1, int(char.height * scale))
            resized = char.resize((w, h))
            # center-ish position
            frame.paste(resized, (80, max(0, 200 - int(50 * scale))), resized)
            placeholder.image(frame)
            time.sleep(0.05)

        time.sleep(0.2)
        placeholder.empty()

    # --------------------------
    # ガチャ実行（mode -> 'anim' にして rerun）
    # --------------------------
    def do_gacha():
        # guard
        if not consume_gacha_coin(user_id, 1):
            st.warning("コインがありません！")
            return

        chars = load_characters()
        rarity_num = pick_rarity()
        rarity_name = RARITY_LABELS[rarity_num]

        char_file = get_character(rarity_num, chars)
        # if no char found, abort gracefully
        if char_file is None:
            st.error("キャラクターが見つかりません。")
            return

        egg_file = RARITY_EGG[rarity_num]
        break_file = RARITY_BREAK[rarity_num]

        st.session_state.result = {
            "rarity_num": rarity_num,
            "rarity_name": rarity_name,
            "egg": egg_file,
            "break": break_file,
            "char": char_file,
        }

        st.session_state.mode = "anim"
        # rerun to enter animation branch
        st.rerun()

    # --------------------------
    # main_gacha（モードで描画を切替）
    # --------------------------
    def main_gacha():
        # safety: if mode anim but no result, reset
        if st.session_state.mode == "anim" and not st.session_state.result:
            st.session_state.mode = "normal"

        # ANIMATION MODE
        if st.session_state.mode == "anim":
            data = st.session_state.result
            # double-check
            if not data:
                st.warning("演出データが見つかりません。")
                st.session_state.mode = "normal"
                st.rerun()
                return

            egg_img = f"{EGG_PATH}/{data['egg']}"
            break_img = f"{EGG_PATH}/{data['break']}"
            char_img = f"{CHAR_PATH}/{data['char']}"

            st.markdown("## 🎉 ガチャ結果！")
            # play animation (blocking until done)
            play_machine_roll(egg_img, break_img, char_img)

            # after animation, switch to result display
            st.session_state.mode = "result"
            st.rerun()
            return

        # RESULT MODE
        if st.session_state.mode == "result":
            data = st.session_state.result
            if not data:
                st.session_state.mode = "normal"
                st.rerun()
                return
            
            # ガチャ結果確定後
            add_user_character(
                user_id=user_id,
                char_name=data["char"],
                rarity=data["rarity_name"]
            )

            st.markdown(f"## 【{data['rarity_name']}】")
            # show char image (fallback safe)
            char_path = f"{CHAR_PATH}/{data['char']}"
            if os.path.exists(char_path):
                st.image(char_path, width=300)
            else:
                st.write(f"(画像が見つかりません：{data['char']})")
            st.markdown(f"**{data['char']}**")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("戻る"):
                    st.session_state.result = None
                    st.session_state.mode = "normal"
                    st.rerun()
            with col2:
                if st.button("もう一回ガチャる"):
                    if get_gacha_coins(user_id) > 0:
                        do_gacha()
                    else:
                        st.warning("コインがありません！")
            return

        # NORMAL MODE (default)
        # show machine + rates on the right
        rarity_order = [1, 2, 3, 4, 5]
        rarity_colors = {1: "#CCCCCC", 2: "#55AAFF", 3: "#AA55FF", 4: "#FFD700", 5: "#FF5500"}
        rarity_eggs = RARITY_EGG
        rarity_prob = {1: 0.55, 2: 0.25, 3: 0.12, 4: 0.06, 5: 0.02}

        machine_col, right_col = st.columns([2, 1])
        with machine_col:
            if os.path.exists(f"{BASE}/gacha_machine.png"):
                st.image(f"{BASE}/gacha_machine.png", width="stretch")
            else:
                st.write("（ガチャマシーン画像がありません）")

        with right_col:
            st.markdown("### 📊 提供割合 (排出率)")
            for r in rarity_order:
                egg_file = f"{EGG_PATH}/{rarity_eggs[r]}"
                label = RARITY_LABELS[r]
                prob = rarity_prob[r] * 100
                color = rarity_colors[r]

                egg_col, text_col = st.columns([1, 2])
                with egg_col:
                    if os.path.exists(egg_file):
                        st.image(egg_file, width=60)
                    else:
                        st.write("（画像なし）")
                with text_col:
                    st.markdown(
                        f"""
                        <div style="padding:6px;">
                            <span style="color:{color}; font-size:18px; font-weight:bold;">
                                {label}
                            </span>
                            : {prob:.1f}%
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # buttons
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("ガチャる", width="stretch"):
                do_gacha()
        with col2:
            coins = get_gacha_coins(user_id)
            st.markdown(f"### 🪙 コイン: {coins}")

    # --------------------------
    # run
    # --------------------------
    main_gacha()

# ==========================
# キャラ図鑑タブ（完全安定版）
# ==========================
with tab_chara:

    import os
    import base64
    import streamlit as st

    current_chara = st.session_state.get("current_chara")

    # --------------------------
    # 見出し
    # --------------------------
    st.markdown("""
        <h2 style="text-align:center; color:#F4E99B;
        text-shadow:2px 2px 4px #000;">📘 キャラ図鑑</h2>
        <p style="text-align:center; color:#DDD;">
            入手したキャラをコレクションできます！
        </p>
        <hr style="border:1px solid #665;">
    """, unsafe_allow_html=True)

    # --------------------------
    # Base64変換
    # --------------------------
    def img_to_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    # --------------------------
    # キャラ一覧（フォルダ基準）
    # --------------------------
    if not os.path.exists(CHAR_PATH):
        st.error("キャラ画像フォルダが存在しません")
        st.stop()

    all_characters = sorted([
        f for f in os.listdir(CHAR_PATH)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ])

    if not all_characters:
        st.warning("キャラ画像がありません")
        st.stop()

    # --------------------------
    # ユーザ所持キャラ（DB）
    # --------------------------
    user_chars = load_user_characters(user_id)
    owned_set = {c["name"] for c in user_chars}

    # --------------------------
    # 所持率計算
    # --------------------------
    total_chars = len(all_characters)
    owned_count = len(owned_set)
    owned_rate = int((owned_count / total_chars) * 100) if total_chars > 0 else 0

    st.markdown(
        f"""
        <div style="
            width:100%;
            max-width:600px;
            margin:20px auto 30px auto;
            padding:12px 16px;
            background:#1A1A1A;
            border-radius:14px;
            box-shadow:0 0 10px #000;
        ">
            <div style="
                color:#F4E99B;
                font-weight:bold;
                margin-bottom:8px;
                text-align:center;
                text-shadow:1px 1px 2px #000;
            ">
                図鑑達成率：{owned_count} / {total_chars}（{owned_rate}%）
            </div>

        <div style="
            width:100%;
            height:18px;
            background:#333;
            border-radius:10px;
            overflow:hidden;
        ">
                <div style="
                    width:{owned_rate}%;
                    height:100%;
                    background:linear-gradient(
                        90deg,
                        #6EE7B7,
                        #F4E99B,
                        #FFD700
                    );
                    box-shadow:0 0 8px #FFD700;
                    transition:width 0.6s ease;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )



    # --------------------------
    # レアリティ判定
    # --------------------------
    def get_rarity_from_filename(filename):
        try:
            num = int(filename[4])  # starX_
        except:
            return "N"
        return {1: "N", 2: "R", 3: "SR", 4: "UR", 5: "LEGEND"}.get(num, "N")

    # --------------------------
    # レアリティ別デザイン
    # --------------------------
    RARITY_STYLE = {
        "N": {
            "border": "#8B6F47",
            "bg": "#2A2418",
            "shadow": "0 0 6px #000",
            "color": "#C8B48A",
        },
        "R": {
            "border": "#B87333",
            "bg": "#2A1E14",
            "shadow": "0 0 8px #B87333",
            "color": "#FFB070",
        },
        "SR": {
            "border": "#C0C0C0",
            "bg": "#1E1E2F",
            "shadow": "0 0 10px #C0C0C0",
            "color": "#E0E0E0",
        },
        "UR": {
            "border": "#FFD700",
            "bg": "#2F240E",
            "shadow": "0 0 14px #FFD700",
            "color": "#FFE066",
        },
        "LEGEND": {
            "border": "linear-gradient(45deg, red, orange, yellow, green, cyan, blue, violet)",
            "bg": "#1B0F2D",
            "shadow": "0 0 18px #FF66FF",
            "color": "#FFCCFF",
        },
    }

    # --------------------------
    # 5列グリッド
    # --------------------------
    cols = st.columns(5)

    for idx, filename in enumerate(all_characters):
        col = cols[idx % 5]

        with col:
            img_path = f"{CHAR_PATH}/{filename}"
            b64 = img_to_base64(img_path)

            rarity = get_rarity_from_filename(filename)
            style = RARITY_STYLE[rarity]
            is_owned = filename in owned_set
            is_current = (filename == current_chara)

            # 未所持は黒シルエット
            filter_css = "filter: brightness(0);" if not is_owned else ""
            bg_color = "#2A2A2A" if not is_owned else "#0F0F0F"

            with st.form(key=f"use_char_{filename}", clear_on_submit=True):

                st.markdown(
                    f"""
                    <div style="
                        background:{style['bg']};
                        border:4px solid {style['border']};
                        border-radius:14px;
                        padding:10px;
                        margin-bottom:18px;
                        box-shadow:{style['shadow']};
                        text-align:center;
                        color:{style['color']};
                    ">

                    {"<div style='position:absolute; top:6px; left:6px; "
                    "background:#FFD700; color:#000; padding:4px 8px; "
                    "font-size:12px; font-weight:bold; border-radius:8px; "
                    "box-shadow:0 0 6px #000;'>使用中</div>"
                    if is_current else ""}

                    <!-- 画像枠 -->
                    <div style="
                        width:140px;
                        height:140px;
                        margin:0 auto;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        background:{bg_color};
                        border-radius:10px;
                    ">
                    <img src="data:image/png;base64,{b64}"
                        style="
                            max-width:100%;
                            max-height:100%;
                            object-fit:contain;
                            {filter_css}">
                    </div>

                    <div style="
                            margin-top:8px;
                            font-weight:bold;
                            font-size:14px;
                            text-shadow:1px 1px 2px #000;
                        ">
                            レア度: {rarity}
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # 👇 画像の下に透明ボタン（実質「画像クリック」）
                submitted = st.form_submit_button(
                    "使用する" if is_owned else "未所持",
                    disabled=not is_owned
                )

                if submitted:
                    set_current_chara(user_id, filename)
                    st.session_state["current_chara"] = filename
                    st.success(f"{filename} を使用キャラに設定しました")
                    st.rerun()





# ==========================
# 冒険マップ tab（完全版）
# ==========================
with tab_map:

    import base64
    import streamlit as st

    def img_to_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    
    def ensure_map_progress(user_id):
        conn = get_conn()
        c = conn.cursor()

        c.execute("""
            INSERT OR IGNORE INTO user_map_progress (
                user_id, map_pos, current_chara, move_count, updated_at
            ) VALUES (?, 0, '', 0, ?)
        """, (user_id, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    ensure_map_progress(user_id)

    st.title("🚶‍♂️ 冒険")

    st.markdown("""
    🗺️ **冒険マップへようこそ！**

    食事を記録すると「移動可能マス」が増え、
    キャラクターがマップを進んでいきます。

    道中では **ガチャコイン🪙** を拾ったり、
    新しいエリアが解放されます。
    """)

    # --------------------------
    # マップ定義
    # --------------------------
    MAPS = {
        "grass": {
            "name": "🌱 草原",
            "img": "grass.png",
            "nodes": [(12,35),(28,32),(43,30),(63,32),(77,35),(60,52),(50,65)]
        },
        "desert": {
            "name": "🏜️ 砂漠",
            "img": "desert.png",
            "nodes": [(12,35),(28,32),(43,30),(63,32),(77,35),(60,52),(50,65)]
        },
        "snow": {
            "name": "❄️ 雪原",
            "img": "snow.png",
            "nodes": [(12,35),(28,32),(43,30),(63,32),(77,35),(60,52),(50,65)]
        }
    }

    MAP_ORDER = ["grass", "desert", "snow"]

    def get_next_map_key(current_key):
        if current_key not in MAP_ORDER:
            return None
        idx = MAP_ORDER.index(current_key)
        if idx + 1 < len(MAP_ORDER):
            return MAP_ORDER[idx + 1]
        return None  # 最終マップ


    # ★ コイン配置ノード（重要）
    NODE_COINS = {
        "grass":  [2, 4, 6],
        "desert": [1, 3],
        "snow":   [2, 5],
    }

    COIN_PATH = "assets/images/coin.png"
    coin64 = img_to_base64(COIN_PATH)

    if "current_map" not in st.session_state:
        st.session_state.current_map = "grass"

    map_key = st.session_state.current_map
    current_map = MAPS[map_key]
    node_positions = current_map["nodes"]
    coin_nodes = NODE_COINS.get(map_key, [])

    # --------------------------
    # 進行状況
    # --------------------------
    map_data = get_map_progress(user_id)
    map_pos = map_data["map_pos"]
    current_chara = get_current_chara(user_id)

    move_count = get_move_count(user_id)

    bg64 = img_to_base64(f"assets/images/maps/{current_map['img']}")
    char64 = img_to_base64(f"assets/images/characters/{current_chara}")

    # --------------------------
    # HTML生成
    # --------------------------
    nodes_html = "".join([
        f"""
        <div class="node {'active' if i == map_pos else ''}"
            style="left:{x}%; top:{y}%;"></div>
        """
        for i, (x, y) in enumerate(node_positions)
    ])

    coins_html = "".join([
        f"""
        <img src="data:image/png;base64,{coin64}"
            class="coin"
            style="
                left:{node_positions[i][0]}%;
                top:{node_positions[i][1] - 6}%;
            ">
        """
        for i in coin_nodes
        if not has_node_coin(user_id, map_key, i)
    ])

    char_x, char_y = node_positions[map_pos]

    # --------------------------
    # マップ描画（markdown 1回）
    # --------------------------
    st.markdown(
        f"""
        <style>
        #map-area {{
            position:relative;
            width:100%;
            max-width:1400px;
            height:720px;
            margin:auto;
            background-image:url('data:image/png;base64,{bg64}');
            background-size:cover;
            background-position:center;
            border:4px solid #3a2f1b;
            border-radius:16px;
            overflow:hidden;
        }}

        .node {{
            position:absolute;
            width:56px;
            height:56px;
            border-radius:50%;
            background:rgba(120,170,180,0.9);
            border:3px solid #222;
            transform:translate(-50%, -50%);
            box-shadow:0 0 6px #333;
            z-index:20;
        }}

        .node.active {{
            box-shadow:0 0 18px 6px gold;
        }}

        .coin {{
            position:absolute;
            width:36px;
            transform:translate(-50%, -50%);
            z-index:40;
            animation:coinFloat 2s ease-in-out infinite;
        }}

        @keyframes coinFloat {{
            0%   {{ transform:translate(-50%, -55%); }}
            50%  {{ transform:translate(-50%, -65%); }}
            100% {{ transform:translate(-50%, -55%); }}
        }}

        @keyframes charaFloat {{
            0%   {{ transform:translate(-50%, -55%); }}
            50%  {{ transform:translate(-50%, -65%); }}
            100% {{ transform:translate(-50%, -55%); }}
        }}

        .chara {{
            position:absolute;
            width:84px;
            transform:translate(-50%, -100%);
            z-index:50;
            animation:charaFloat 2s ease-in-out infinite;
        }}
        </style>

        <div id="map-area">
            {nodes_html}
            {coins_html}
        <img src="data:image/png;base64,{char64}"
            class="chara"
            style="left:{char_x}%; top:{char_y - 6}%;">
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------
    # 移動UI（ここが新設）
    # --------------------------
    st.metric(
        label="移動可能マス",
        value=move_count,
        help="食事入力で一日一回増えます"
    )


    LAST_NODE_INDEX = len(node_positions) - 1

    can_move = move_count > 0 and map_pos < LAST_NODE_INDEX

    if st.button("▶ 1マス進む", disabled=not can_move):
        next_pos = map_pos + 1

        save_map_progress(user_id, next_pos, current_chara)
        consume_move_count(user_id, 1)

        if next_pos in coin_nodes and not has_node_coin(user_id, map_key, next_pos):
            collect_node_coin(user_id, map_key, next_pos)
            st.toast("🪙 ガチャコイン +1！")

        st.rerun()

    if not can_move:
        st.info("🍚 食事を入力すると移動ポイントが貯まります")


    # --------------------------
    # 次のマップ
    # --------------------------
    if map_pos == LAST_NODE_INDEX:
        next_map = get_next_map_key(map_key)
        if next_map:
            if st.button("▶ 次のマップへ"):
                st.session_state.current_map = next_map
                save_map_progress(user_id, 0, current_chara)
                st.rerun()
        else:
            st.success("🎉 すべてのマップをクリアしました！")
