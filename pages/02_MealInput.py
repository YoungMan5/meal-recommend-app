# pages/02_MealInput.py

import streamlit as st
from db import save_meal, get_user_profile, load_meals, add_exp, save_daily_advice, load_daily_advice, get_tomorrow_menu, save_tomorrow_menu, get_daily_advice, add_move_count
from utils import gemini_model, calc_nutrient_targets
import json
import datetime
import pandas as pd
from utils import load_css

load_css("styles.css")
st.set_page_config(page_title="食事入力", layout="wide")
st.title("🍱 食事入力")

# =========================
# 🔐 ログインチェック
# =========================
if "user_id" not in st.session_state:
    st.error("ログインしてください。")
    st.stop()

user_id = st.session_state["user_id"]
profile = get_user_profile(user_id)
NUTRIENT_TARGETS = calc_nutrient_targets(profile)

# -----------------------------------------
# 横棒プログレスバーを描画する関数
# -----------------------------------------
def nutrient_bar(name, value, target):
    ratio = min(value / target, 1.0)  # 1.0 を上限にする

    # 色設定
    color = "#53c26f"        # 通常：緑
    if value > target * 1.2: # 20%超過で赤
        color = "#e55656"
    elif value > target:     # 100%超過で黄色
        color = "#f0ad4e"

    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
            <div style="font-weight:600;">{name}</div>
            <div style="font-size:22px; font-weight:700;">
                {value:.1f} / {target}{'kcal' if name=='カロリー' else 'g'}
            </div>
            <div style="width:100%; background:#eee; height:12px; border-radius:6px;">
                <div style="width:{ratio*100}%; background:{color}; height:12px; border-radius:6px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================
# 🔽 日付の選択
# ============================
selected_date = st.date_input("日付を選択", value=datetime.date.today())
selected_date_str = selected_date.isoformat()

tab1, tab2 = st.tabs(["🍽 今日の食事入力", "🍱 明日の献立提案"])

with tab1:
    # ============================
    # 📊 選択日の栄養サマリー
    # ============================
    st.subheader("📊 栄養素グラフ")

    today_meals = load_meals(user_id, date=selected_date_str)

    nutri_total = {k: 0 for k in NUTRIENT_TARGETS.keys()}

    for meal in today_meals:
        arr = json.loads(meal["nutrients"])
        for item in arr:
            name = item.get("name")
            value = float(item.get("value", 0))
            if name in nutri_total:
                nutri_total[name] += value

    # 表示
    cols = st.columns(2)
    for i, (name, target) in enumerate(NUTRIENT_TARGETS.items()):
        value = nutri_total.get(name, 0)
        with cols[i % 2]:
            nutrient_bar(name, value, target)


    # =========================
    # 🍽 食事区分ごとの栄養素グラフ
    # =========================
    st.subheader("📊 食事ごとの栄養サマリー")

    categories = ["朝食", "昼食", "夕食", "間食"]

    for cat in categories:
        st.markdown(f"### 🟢 {cat}")

        # DB から取得
        meals = load_meals(user_id, date=selected_date_str, category=cat)


        if not meals:
            st.write("（記録なし）")
            continue

        # 食べ物ごとに表示
        for m in meals:
            food = m["food"]
            grams = m["grams"]
            nutrients = json.loads(m["nutrients"])

            # 栄養素を辞書に変換
            nutrient_dict = {x["name"]: x["value"] for x in nutrients}

            cal = nutrient_dict.get("カロリー", 0)
            protein = nutrient_dict.get("たんぱく質", 0)
            fat = nutrient_dict.get("脂質", 0)
            carbs = nutrient_dict.get("炭水化物", 0)
            fiber = nutrient_dict.get("食物繊維", 0)
            sugar = nutrient_dict.get("糖質", 0)
            salt = nutrient_dict.get("塩分", 0)

            st.markdown(
                f"""
                <div style="
                    padding:10px;
                    margin:5px 0;
                    border-radius:8px;
                    border:1px solid #ddd;
                    background:#fafafa;
                    display:flex;
                    flex-wrap:wrap;
                    gap:15px;
                    align-items:center;
                ">
                    <b>{food}</b>（{grams}g）  
                    <span>カロリー: {cal} kcal</span>
                    <span>たんぱく質: {protein} g</span>
                    <span>脂質: {fat} g</span>
                    <span>炭水化物: {carbs} g</span>
                    <span>食物繊維: {fiber} g</span>
                    <span>糖質: {sugar} g</span>
                    <span>塩分: {salt} g</span>
                </div>
                """,
                unsafe_allow_html=True
            )


    # =========================
    # 📝 食事入力フォーム
    # =========================
    st.subheader("🍽 食事を記録する")

    # --------------------------------------------------------
    # セッション初期化
    # --------------------------------------------------------
    if "foods" not in st.session_state:
        st.session_state.foods = [{"id": 1, "food": "", "grams": 100}]

    foods = st.session_state.foods
    remove_id = None

    # --------------------------------------------------------
    # 行の描画
    # --------------------------------------------------------
    for item in foods:
        row_id = item["id"]

        col1, col2, col3 = st.columns([4, 3, 1])

        with col1:
            item["food"] = st.text_input(
                "食品名",
                item["food"],
                key=f"food_{row_id}"
            )

        with col2:
            item["grams"] = st.number_input(
                "グラム数",
                value=item["grams"],
                min_value=1,
                key=f"grams_{row_id}"
            )

        with col3:
            if st.button("❌", key=f"del_{row_id}"):
                remove_id = row_id

    # --------------------------------------------------------
    # 行削除処理
    # --------------------------------------------------------
    if remove_id is not None:
        st.session_state.foods = [f for f in foods if f["id"] != remove_id]
        st.rerun()

    # --------------------------------------------------------
    # 行追加
    # --------------------------------------------------------
    if st.button("＋食品を追加"):
        new_id = max([f["id"] for f in st.session_state.foods]) + 1
        st.session_state.foods.append({"id": new_id, "food": "", "grams": 100})
        st.rerun()

    # 食事区分
    category = st.selectbox("食事区分", ["朝食", "昼食", "夕食", "間食"])

    # =======================================================
    # 🚀 AI解析して一括保存（APIは1回だけ）
    # =======================================================
    if st.button("AIで解析して保存"):

        loading = st.empty()

        # ===============================
        # 🔄 ローディング表示
        # ===============================
        with loading.container():
            col_img, col_text = st.columns([1, 3])

            with col_img:
                st.image("assets/images/loading_man.gif", width=120)

            with col_text:
                st.markdown(
                    """
                    <div style="
                        display:flex;
                        align-items:center;
                        height:100%;
                        font-size:26px;
                    ">
                        AIで解析中...
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        food_list = [
            {"food": f["food"].strip(), "grams": f["grams"]}
            for f in st.session_state.foods if f["food"].strip() != ""
        ]

        if not food_list:
            loading.empty()
            st.warning("食品を入力してください")
            st.stop()

        # ---------------------------------------
        # 🚀 API1回だけ呼び出す
        # ---------------------------------------
        result = gemini_model.analyze_food_multi(food_list, user_info=profile)

        items = result.get("items", [])
        total = result.get("total", [])
        advice = result.get("advice", "")

        # ---------------------------------------
        # DB保存
        # ---------------------------------------
        for item in items:
            save_meal(
                user_id,
                selected_date_str,
                category,
                item["food"],
                item["grams"],
                json.dumps(item["nutrients"], ensure_ascii=False),
                ""   # ← アドバイス保存しない
            )

        # ---------------------------------------
        # 経験値
        # ---------------------------------------
        exp_gain = 5  # 全食事共通ベース

        if category == "朝食":
            exp_gain += 3      # 生活リズム重視
        elif category == "昼食":
            exp_gain += 2      # 活動の中心
        elif category == "夕食":
            exp_gain += 1      # 締め
        elif category == "間食":
            exp_gain += 0      # おまけ枠
            
        add_exp(user_id, exp_gain)

        # ---------------------------------------
        # 結果表示
        # ---------------------------------------
        loading.empty()

        added = add_move_count(user_id, 1)
        if added:
            st.toast("🚶‍♂️ 冒険ポイント +1！")

        st.success(f"保存しました！経験値 +{exp_gain} 🎉")

        st.subheader("📊 全食品の解析結果")
        st.json(items)

        st.subheader("🔥 合計栄養素")
        st.json(total)

        st.info(advice)

        st.rerun()

with tab2:
    # =============================
    # 🍀 今日の食事アドバイス（総括）
    # =============================
    st.subheader("🍀 今日の食事アドバイス")

    # ① 保存済みアドバイスを読込
    saved_advice = load_daily_advice(user_id, selected_date_str)

    if saved_advice:
        st.write(saved_advice)
    else:
        st.info("この日はまだアドバイスが生成されていません。")

    # ② 生成ボタン
    if st.button("🌟 この日のアドバイスを生成"):
        loading = st.empty()

        # ===============================
        # 🔄 ローディング表示
        # ===============================
        with loading.container():
            col_img, col_text = st.columns([1, 3])

            with col_img:
                st.image("assets/images/loading_man.gif", width=120)

            with col_text:
                st.markdown(
                    """
                    <div style="
                        display:flex;
                        align-items:center;
                        height:100%;
                        font-size:26px;
                    ">
                        🌟 この日のアドバイスを生成中...
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        advice = gemini_model.generate_daily_advice(
            nutri_total,
            NUTRIENT_TARGETS
        )


        save_daily_advice(user_id, selected_date_str, advice)

        loading.empty()
        st.success("アドバイスを生成しました！")
        st.write(advice)
        st.rerun()

    # =============================
    # 🍱 明日の献立生成
    # =============================
    st.subheader("🍱 明日の献立を自動生成")

    menu_text = get_tomorrow_menu(user_id, selected_date_str)

    if menu_text:
        st.info(menu_text)
    else:
        st.warning("まだ明日の献立がありません。")
    
    if st.button("✨ 明日の献立を生成"):

        loading = st.empty()

        # ===============================
        # 🔄 ローディング表示
        # ===============================
        with loading.container():
            col_img, col_text = st.columns([1, 3])

            with col_img:
                st.image("assets/images/loading_man.gif", width=120)

            with col_text:
                st.markdown(
                    """
                    <div style="
                        display:flex;
                        align-items:center;
                        height:100%;
                        font-size:26px;
                    ">
                        🍳 明日の献立を作成中...
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ===============================
        # 処理開始
        # ===============================
        advice_text = get_daily_advice(user_id, selected_date_str)

        if not advice_text:
            loading.empty()
            st.error("先に『今日のアドバイス』を生成してください。")
            st.stop()

        menu = gemini_model.generate_tomorrow_menu(
            today_advice=advice_text,
            nutri_total=nutri_total,
            nutrient_targets=NUTRIENT_TARGETS
        )

        save_tomorrow_menu(user_id, selected_date_str, menu)

        # ===============================
        # ✅ 処理完了
        # ===============================
        loading.empty()
        st.success("明日の献立を保存しました！")
        st.rerun()





