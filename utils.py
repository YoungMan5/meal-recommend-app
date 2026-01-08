import os
import re
import json
from typing import Dict, Any
import streamlit as st

# Google GenAI SDK
try:
    from google import genai
except Exception as e:
    raise RuntimeError("google-genai が必要です。pip install google-genai") from e

API_KEY = os.getenv("GENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("環境変数 GENAI_API_KEY を設定してください")

client = genai.Client(api_key=API_KEY)

# -----------------------------
# Geminiモデルクラス
# -----------------------------
class GeminiModel:
    def __init__(self, model="gemini-2.0-flash"):
        self.model = model

    # AI呼び出し
    def generate_content(self, prompt: str) -> Any:
        chat = client.chats.create(model=self.model)
        return chat.send_message(prompt)

    # AI返答からJSON抽出
    def extract_json(self, text: str) -> dict:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {}

    # 食品判定
    def is_food_item(self, name: str) -> bool:
        prompt = f"""
        次の単語 "{name}" は食品または飲み物ですか？
        JSON形式で返してください: {{ "is_food": true }} または {{ "is_food": false }}
        """
        chat = client.chats.create(model=self.model)
        res = chat.send_message(prompt)
        reply = res.text.strip()
        m = re.search(r"\{[\s\S]*\}", reply)
        if m:
            try:
                data = json.loads(m.group(0))
                return bool(data.get("is_food", False))
            except Exception:
                return "true" in reply.lower()
        return "true" in reply.lower()

    # 栄養分析
    def analyze_food(self, food_name: str, grams: float, user_info: Dict[str, Any]=None) -> Dict[str, Any]:
        ui = ""
        if user_info:
            ui = "\n".join(f"{k}: {v}" for k, v in user_info.items())

        prompt = f"""
        あなたは専門の栄養士です。
        食品「{food_name}」の、**{grams}gあたり** の主要栄養素（カロリー・たんぱく質・炭水化物・脂質・食物繊維・糖質・塩分）を推定してください。
        出力は厳格にJSONのみとしてください。

        出力形式:
        {{
            "nutrients": [
                {{ "name": "カロリー", "value": 数値, "unit": "kcal" }},
                {{ "name": "たんぱく質", "value": 数値, "unit": "g" }},
                {{ "name": "炭水化物", "value": 数値, "unit": "g" }},
                {{ "name": "脂質", "value": 数値, "unit": "g" }},
                {{ "name": "食物繊維", "value": 数値, "unit": "g" }},
                {{ "name": "糖質", "value": 数値, "unit": "g" }},
                {{ "name": "塩分", "value": 数値, "unit": "g" }}
            ],
            "advice": "日本語で1〜2文の食事アドバイス"
        }}
        ユーザー情報:
        {ui}
        """
        chat = client.chats.create(model=self.model)
        res = chat.send_message(prompt)
        reply = res.text.strip()
        m = re.search(r"\{[\s\S]*\}", reply)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {"nutrients": [], "advice": reply}
    
        # 今日のアドバイス生成
    def generate_daily_advice(self, nutri_total: dict, nutrient_targets: dict) -> str:
        """
        栄養データと目標値から、Gemini による総括アドバイスを生成するメソッド
        """

        advice_prompt = f"""
        あなたは管理栄養士です。

        ユーザーが今日摂取した栄養素の合計:
        {json.dumps(nutri_total, ensure_ascii=False, indent=2)}

        栄養目標値:
        {json.dumps(nutrient_targets, ensure_ascii=False, indent=2)}

        以下を簡潔に日本語で回答してください：

        1. 今日の良かった点（栄養バランス・食事量）
        2. 改善ポイント（不足 or 過剰）
        3. 明日の行動アドバイス
        """

        res = self.generate_content(advice_prompt)
        return res.text

        #明日の献立
    def generate_tomorrow_menu(self, today_advice: str, nutri_total: dict, nutrient_targets: dict) -> str:
        """
        今日のアドバイスを基に材料込みの明日の献立（朝・昼・夜）を生成する
        """

        menu_prompt = f"""
        あなたは管理栄養士です。

        --- 今日の総括アドバイス ---
        {today_advice}

        --- 今日の摂取栄養素合計 ---
        {json.dumps(nutri_total, ensure_ascii=False, indent=2)}

        --- 栄養目標値 ---
        {json.dumps(nutrient_targets, ensure_ascii=False, indent=2)}

        上記をもとに、明日の1日の献立案（朝・昼・夜）を日本語で作成してください。

        【必須条件】
        1. 1食につきメイン1品＋副菜1–2品を提案する
        2. 料理名＋材料（分量付き）を必ず提示する
        3. 材料は「1人前」で書く
        4. 今日のアドバイスで指摘された不足・過剰を補う構成にする
        5. 簡単に作れる家庭料理にする
        6. 箇条書きで読みやすく

        【出力形式の例】
        朝食:
        ● 料理名
            - 材料:
                ・食材A：○g
                ・食材B：○個
            - 理由: ○○の改善に役立つため

        昼食:
        ● 料理名
            - 材料:
            …

        夕食:
        ● 料理名
            - 材料:
            …

        """

        res = self.generate_content(menu_prompt)
        return res.text
    
        # 複数食品まとめて解析
    def analyze_food_multi(self, food_list, user_info=None):

        ui = ""
        if user_info:
            ui = "\n".join(f"{k}: {v}" for k, v in user_info.items())

        foods_text = "\n".join(
            f"- {f['food']} {f['grams']}g" for f in food_list
        )

        prompt = f"""
        あなたは栄養士です。
        次の食品の栄養素（カロリー, たんぱく質, 脂質, 炭水化物, 食物繊維, 糖質, 塩分）を推定し、
        食品ごとの栄養素リストと合計を返してください。

        食品:
        {foods_text}

        出力は JSON のみ。形式は必ず以下に従う:

        {{
        "items":[
        {{
            "food":"食品名",
            "grams":数値,
            "nutrients":[
            {{"name":"カロリー","value":数値,"unit":"kcal"}},
            {{"name":"たんぱく質","value":数値,"unit":"g"}},
            {{"name":"炭水化物","value":数値,"unit":"g"}},
            {{"name":"脂質","value":数値,"unit":"g"}},
            {{"name":"食物繊維","value":数値,"unit":"g"}},
            {{"name":"糖質","value":数値,"unit":"g"}},
            {{"name":"塩分","value":数値,"unit":"g"}}
            ]
        }}
        ],
        "total":[ ... ]
        }}

        ユーザー情報：
        {ui}

        アドバイスは不要。JSON のみ返す。
        """

        chat = client.chats.create(model=self.model)
        res = chat.send_message(prompt)
        reply = res.text.strip()
        # JSON Extraction
        m = re.search(r"\{[\s\S]*\}", reply)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
        return {"items": [], "total": []}





#目標栄養値設定
def calc_nutrient_targets(profile):
    gender = profile["gender"]
    age = profile["age"]
    height = profile["height"]
    weight = profile["weight"]
    goal = profile["goal"]
    act = profile["activity_level"]

    # -------- BMR（基礎代謝） Mifflin-St Jeor --------
    if gender == "男性":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # ---- Activity Factor ----
    if act == 0:
        af = 1.2
    elif act <= 3:
        af = 1.375
    elif act <= 5:
        af = 1.55
    elif act == 6:
        af = 1.725
    else:
        af = 1.9

    tdee = bmr * af  # 1日の消費カロリー

    # ---- 目標に応じて調整 ----
    if goal == "ダイエット":
        tdee *= 0.85   # −15%
    elif goal == "筋増量":
        tdee *= 1.15   # ＋15%

    # ---- 栄養素バランス ----
    protein = weight * 1.6    # g
    fat = tdee * 0.25 / 9     # g
    carbs = (tdee - (protein*4 + fat*9)) / 4  # g

    return {
        "カロリー": round(tdee),
        "たんぱく質": round(protein),
        "脂質": round(fat),
        "炭水化物": round(carbs),
        "糖質": round(carbs * 0.9),
        "食物繊維": 18,
        "塩分": 6.5
    }

# -----------------------------
# インスタンス化
# -----------------------------
gemini_model = GeminiModel()

def load_css(file_name: str):
    with open(file_name, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
