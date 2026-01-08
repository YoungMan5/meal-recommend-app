# db.py
import sqlite3
import json
from datetime import datetime, date
import os

DB_NAME = "nutrition.db"

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # profiles
    c.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER UNIQUE NOT NULL,
        name TEXT,
        age INTEGER,
        gender TEXT,
        height REAL,
        weight REAL,
        goal TEXT,
        activity_level INTEGER,
        favorite_food TEXT,
        current_chara TEXT,
        current_title TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # meals
    c.execute("""
    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        category TEXT,
        food TEXT,
        grams REAL,
        nutrients TEXT,
        advice TEXT,
        time TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # user_badges
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_badges (
        user_id INTEGER,
        badge_id TEXT,
        achieved_at TEXT,
        PRIMARY KEY (user_id, badge_id)
    )
    """)

    # --- user_progress: レベル・経験値を保持 ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        user_id INTEGER PRIMARY KEY,
        exp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        last_exp_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # --- 冒険マップ進行 ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_map_progress (
        user_id INTEGER PRIMARY KEY,
        map_pos INTEGER DEFAULT 0,
        current_chara TEXT DEFAULT '',
        move_count INTEGER DEFAULT 0,
        last_move_date TEXT,
        updated_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )

    """)

    # --- daily_advice: 日ごとの総括アドバイスとを保存 ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_advice (
    user_id TEXT,
    date TEXT,
    advice TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, date)
    )
    """)

        # 明日の献立保存テーブル
    c.execute("""
    CREATE TABLE IF NOT EXISTS tomorrow_menu (
        user_id INTEGER,
        date TEXT,          -- 今日の日付（=アドバイスを元に作った日）
        menu_text TEXT,     -- 生成した献立
        PRIMARY KEY (user_id, date)
    )
    """)

    # --- ガチャ用（コイン管理） ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_gacha (
        user_id INTEGER PRIMARY KEY,
        coins INTEGER DEFAULT 0,
        updated_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # --- ユーザ所持キャラ ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        char_name TEXT,
        rarity TEXT,
        obtained_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # --- マップコイン ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_node_coins (
        user_id INTEGER NOT NULL,
        map_key TEXT NOT NULL,
        node_index INTEGER NOT NULL,
        collected_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, map_key, node_index)
    )
    """)

    # --- ユーザ称号 ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_titles (
        user_id INTEGER NOT NULL,
        level INTEGER NOT NULL,
        title TEXT NOT NULL,
        obtained_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, level),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)




    conn.commit()
    conn.close()

# 初期化を自動実行
init_db()

# -------------------------
# ユーザ管理
# -------------------------
def create_user(userid, password):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (userid, password) VALUES (?, ?)", (userid, password))
        conn.commit()

        # 直前に挿入した行の PRIMARY KEY を返す
        user_pk = c.lastrowid
        return user_pk

    except Exception:
        return None

    finally:
        conn.close()

def login(userid, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE userid=? AND password=?", (userid, password))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# -------------------------------
# プロフィール保存 / 取得
# -------------------------------
def save_user_profile(user_id, profile):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO profiles (user_id, name, age, gender, height, weight, goal, activity_level, favorite_food)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        name=excluded.name,
        age=excluded.age,
        gender=excluded.gender,
        height=excluded.height,
        weight=excluded.weight,
        goal=excluded.goal,
        activity_level=excluded.activity_level,
        favorite_food=excluded.favorite_food
    """, (
        user_id, profile["name"], profile["age"], profile["gender"],
        profile["height"], profile["weight"], profile["goal"],
        profile["activity_level"], profile["favorite_food"]
    ))
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, name, age, gender, height, weight, goal, activity_level, favorite_food FROM profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "name": row[1],
        "age": row[2],
        "gender": row[3],
        "height": row[4],
        "weight": row[5],
        "goal": row[6],
        "activity_level": row[7],
        "favorite_food": row[8],
    }

def load_username(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name FROM profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else "名無し"

# -------------------------
# 食事記録
# -------------------------
def save_meal(user_id, date, category, food, grams, nutrients_json, advice):
    conn = get_conn()
    c = conn.cursor()
    time_str = datetime.now().strftime("%H:%M:%S")
    c.execute("""
        INSERT INTO meals (user_id, date, category, food, grams, nutrients, advice, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, date, category, food, grams, nutrients_json, advice, time_str))
    conn.commit()
    conn.close()

def load_meals(user_id, date=None, category=None):
    conn = get_conn()
    c = conn.cursor()
    query = "SELECT date, category, food, grams, nutrients, advice, time FROM meals WHERE user_id=?"
    params = [user_id]
    if date is not None:
        query += " AND date=?"
        params.append(date)
    if category is not None:
        query += " AND category=?"
        params.append(category)
    query += " ORDER BY date DESC, time DESC"
    rows = c.execute(query, tuple(params)).fetchall()
    conn.close()
    return [
        {
            "date": r[0],
            "category": r[1],
            "food": r[2],
            "grams": r[3],
            "nutrients": r[4],
            "advice": r[5],
            "time": r[6],
        }
        for r in rows
    ]

# -------------------------
# 日次レポート保存 / 取得
# -------------------------
def save_daily_advice(user_id: str, date_str: str, advice: str):
    """日付ごとのアドバイスをSQLiteに保存（上書き）"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_advice (
            user_id TEXT,
            date TEXT,
            advice TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, date)
        )
    """)
    cur.execute("""
        INSERT INTO daily_advice (user_id, date, advice)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET advice=excluded.advice
    """, (user_id, date_str, advice))
    conn.commit()
    conn.close()


def load_daily_advice(user_id: str, date_str: str):
    """指定した日付のアドバイスを取得（なければ None）"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT advice FROM daily_advice
        WHERE user_id = ? AND date = ?
    """, (user_id, date_str))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return row[0]
    return None

def get_daily_advice(user_id, date_str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT advice FROM daily_advice
        WHERE user_id = ? AND date = ?
    """, (user_id, date_str))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# -------------------------
# 明日の献立保存 / 取得
# -------------------------
def save_tomorrow_menu(user_id: int, date_str: str, menu_text: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO tomorrow_menu (user_id, date, menu_text)
        VALUES (?, ?, ?)
    """, (user_id, date_str, menu_text))
    conn.commit()
    conn.close()

def get_tomorrow_menu(user_id: int, date_str: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT menu_text FROM tomorrow_menu
        WHERE user_id = ? AND date = ?
    """, (user_id, date_str))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


# -------------------------
# バッジ保存・取得
# -------------------------
def save_user_badge(user_id, badge_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO user_badges (user_id, badge_id, achieved_at) VALUES (?, ?, datetime('now'))",
        (user_id, badge_id)
    )
    conn.commit()
    conn.close()

def load_user_badges(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT badge_id FROM user_badges WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return {r[0] for r in rows}

# -------------------------
# 進捗（経験値/レベル）操作
# -------------------------
LEVEL_EXP = {1: 0}

for lv in range(2, 100):
    LEVEL_EXP[lv] = int(10 + (lv - 2) * 12 + (lv ** 2) * 0.5)
MAX_LEVEL = 99

TITLE_BY_LEVEL = {
    5:  "はじまりの冒険者",
    10: "若き探究者",
    15: "栄養の見習い",
    20: "継続の戦士",
    25: "健康の守り手",
    30: "食事管理士",
    35: "習慣化マスター",
    40: "知識の探求者",
    45: "バランス調整者",
    50: "自己管理の達人",
    55: "栄養戦略家",
    60: "生活改善の賢者",
    65: "ヘルスロード覇者",
    70: "完全管理者",
    75: "鉄壁の意志",
    80: "レジェンド候補",
    85: "超越者",
    90: "不屈の王",
    95: "神域の挑戦者",
    99: "🍀 栄養管理の神 🍀"
}


def get_progress(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT exp, level FROM user_progress WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"exp": 0, "level": 1}
    return {"exp": row[0], "level": row[1]}

def add_exp(user_id, exp_gain):
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT exp, level FROM user_progress WHERE user_id=?",
        (user_id,)
    )
    row = c.fetchone()

    if row is None:
        exp = exp_gain
        level = 1
        c.execute(
            "INSERT INTO user_progress (user_id, exp, level, last_exp_at) VALUES (?, ?, ?, datetime('now'))",
            (user_id, exp, level)
        )
    else:
        exp, level = row
        exp += exp_gain

        new_level = level
        for lv in sorted(LEVEL_EXP.keys()):
            if exp >= LEVEL_EXP[lv]:
                new_level = lv

        if new_level > MAX_LEVEL:
            new_level = MAX_LEVEL

        if new_level > level:
            for lv in range(level + 1, new_level + 1):
                grant_title_if_needed(user_id, lv)

        level = new_level

        c.execute(
            "UPDATE user_progress SET exp=?, level=?, last_exp_at=datetime('now') WHERE user_id=?",
            (exp, level, user_id)
        )

    conn.commit()
    conn.close()
    return get_progress(user_id)


def grant_title_if_needed(user_id, level):
    if level not in TITLE_BY_LEVEL:
        return

    title = TITLE_BY_LEVEL[level]

    conn = get_conn()
    c = conn.cursor()

    # すでに持っているか？
    c.execute(
        "SELECT 1 FROM user_titles WHERE user_id=? AND title=?",
        (user_id, title)
    )
    exists = c.fetchone()

    if not exists:
        # 追加
        c.execute(
            "INSERT INTO user_titles (user_id, title, level) VALUES (?, ?, ?)",
            (user_id, title, level)
        )

        # 初回称号なら自動セット
        c.execute(
            "SELECT current_title FROM profiles WHERE user_id=?",
            (user_id,)
        )
        row = c.fetchone()
        if not row or not row[0]:
            c.execute(
                "UPDATE profiles SET current_title=? WHERE user_id=?",
                (title, user_id)
            )

    conn.commit()
    conn.close()

def get_user_titles(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT title FROM user_titles WHERE user_id=? ORDER BY level",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]




# -------------------------
# ヘルパー：連続日数取得
# -------------------------
def get_consecutive_days(user_id):
    """ユーザが何日連続で記録しているか（今日含む）"""
    meals = load_meals(user_id)
    dates = sorted({m["date"] for m in meals}, reverse=True)
    if not dates:
        return 0
    streak = 1
    for i in range(1, len(dates)):
        d1 = datetime.fromisoformat(dates[i-1]).date()
        d2 = datetime.fromisoformat(dates[i]).date()
        if (d1 - d2).days == 1:
            streak += 1
        else:
            break
    return streak

# -------------------------
# 冒険マップ進行
# -------------------------
def get_map_progress(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT map_pos, current_chara FROM user_map_progress WHERE user_id=?",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()

    if row:
        return {
            "map_pos": row[0],
            "current_chara": row[1] or "star1_1.png"
        }

    # 未登録ユーザは初期化
    return {
        "map_pos": 0,
        "current_chara": "star1_1.png"
    }


def save_map_progress(user_id, map_pos, current_chara):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_map_progress (user_id, map_pos, current_chara, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            map_pos=excluded.map_pos,
            current_chara=excluded.current_chara,
            updated_at=datetime('now')
    """, (user_id, map_pos, current_chara))
    conn.commit()
    conn.close()

def get_move_count(user_id):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT move_count
        FROM user_map_progress
        WHERE user_id = ?
    """, (user_id,))

    row = c.fetchone()
    conn.close()

    return row[0] if row else 0

def add_move_count(user_id, n):
    today = date.today().isoformat()

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT last_move_date
        FROM user_map_progress
        WHERE user_id = ?
    """, (user_id,))
    row = c.fetchone()

    # 今日すでに付与済みなら何もしない
    if row and row[0] == today:
        conn.close()
        return False

    # move_count 加算 & 日付更新
    c.execute("""
        UPDATE user_map_progress
        SET move_count = move_count + ?,
            last_move_date = ?,
            updated_at = ?
        WHERE user_id = ?
    """, (
        n,
        today,
        today,
        user_id
    ))

    conn.commit()
    conn.close()
    return True

def consume_move_count(user_id, n):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        UPDATE user_map_progress
        SET move_count = MAX(move_count - ?, 0),
            updated_at = ?
        WHERE user_id = ?
    """, (
        n,
        datetime.now().isoformat(),
        user_id
    ))

    conn.commit()
    conn.close()


# -------------------------
# ガチャコイン管理
# -------------------------
def get_gacha_coins(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT coins FROM user_gacha WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


def add_gacha_coins(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_gacha (user_id, coins, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            coins = coins + excluded.coins,
            updated_at = datetime('now')
    """, (user_id, amount))
    conn.commit()
    conn.close()


def consume_gacha_coin(user_id, amount=1):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT coins FROM user_gacha WHERE user_id=?", (user_id,))
    row = c.fetchone()

    if not row or row[0] < amount:
        conn.close()
        return False

    c.execute("""
        UPDATE user_gacha
        SET coins = coins - ?, updated_at=datetime('now')
        WHERE user_id=?
    """, (amount, user_id))

    conn.commit()
    conn.close()
    return True

# -------------------------
# キャラ所持管理
# -------------------------
def add_user_character(user_id, char_name, rarity):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_characters (user_id, char_name, rarity, obtained_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (user_id, char_name, rarity))
    conn.commit()
    conn.close()


def load_user_characters(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT char_name, rarity FROM user_characters
        WHERE user_id=?
        ORDER BY obtained_at
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "rarity": r[1]} for r in rows]

# -------------------------
# マップコイン管理
# -------------------------
def has_node_coin(user_id, map_key, node_index):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM user_node_coins
        WHERE user_id=? AND map_key=? AND node_index=?
    """, (user_id, map_key, node_index))
    r = c.fetchone()
    conn.close()
    return r is not None


def collect_node_coin(user_id, map_key, node_index):
    conn = get_conn()
    c = conn.cursor()

    # 取得済み防止
    c.execute("""
        INSERT OR IGNORE INTO user_node_coins
        (user_id, map_key, node_index)
        VALUES (?, ?, ?)
    """, (user_id, map_key, node_index))

    conn.commit()
    conn.close()

    # ガチャコイン加算
    add_gacha_coins(user_id, 1)


# -------------------------
# 初期キャラをもたせる
# -------------------------
def ensure_initial_character(user_id):
    chars = load_user_characters(user_id)
    owned = {c["name"] for c in chars}

    if "star1_1.png" not in owned:
        add_user_character(
            user_id=user_id,
            char_name="star1_1.png",
            rarity="N"
        )

        # 初期キャラを使用中に設定
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "UPDATE profiles SET current_chara=? WHERE user_id=?",
            ("star1_1.png", user_id)
        )
        conn.commit()
        conn.close()

# -------------------------
# 現在のキャラを変更
# -------------------------
def set_current_chara(user_id, char_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE profiles SET current_chara=? WHERE user_id=?",
        (char_name, user_id)
    )
    conn.commit()
    conn.close()

def get_current_chara(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT current_chara FROM profiles WHERE user_id=?",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else "star1_1.png"

