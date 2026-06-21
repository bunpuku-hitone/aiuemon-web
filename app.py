from flask import Flask, render_template, session, redirect, url_for
from flask import request, jsonify
from datetime import datetime, timedelta
import os
import psycopg2
DATABASE_URL = os.getenv("DATABASE_URL")
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)
    
app = Flask(__name__)
app.secret_key = "present-web-secret-key"

from openai import OpenAI
client = OpenAI()

def is_english(text):
    return sum(1 for c in text if ord(c) < 128) / max(len(text), 1) > 0.6
def load_prompt(filename):
    try:
        with open(filename, encoding="utf-8") as f:
            text = f.read().strip()
            if text:
                return text
            else:
                return ""
    except:
        return ""
def generate_response(user_input, mode, history):

    with open("words.txt", encoding="utf-8") as f:
        text = f.read()

    if mode == "aiemon":
        prompt = load_prompt("aiuemon.txt")

    elif mode == "concierge":
        prompt = load_prompt("concierge.txt")

    else:
        if is_english(user_input):
            prompt = load_prompt("gift_en.txt")
        else:
            prompt = load_prompt("gift_ja.txt")

    history = session.get("aiuemon_history", [])
    if mode != "aiemon":
        history = []
            
    messages = [{"role": "system", "content": prompt}]
    if mode == "aiemon":
        for h in history:
            messages.append(h)
    messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )
    increment_count()
    reply = response.choices[0].message.content
    
    if mode == "aiemon":
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        session["aiuemon_history"] = history[-10:]
    return reply
    
    return response.choices[0].message.content
    
def get_db_count():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM entries")
        result = cur.fetchone()
        return result[0] if result else 0

    except Exception as e:
        print("get_db_count error:", e)
        return 0

    finally:
        cur.close()
        conn.close()

def increment_count():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO entries (app_name, user_key, input_text, output_text) VALUES (%s, %s, %s, %s)",
            ("present_web", "happy_count", "count", "count")
        )
        conn.commit()

    except Exception as e:
        print("increment_count error:", e)

    finally:
        cur.close()
        conn.close()

@app.route("/")
def index():
    mode = session.get("mode", "gift")
    date_text = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y年%m月%d日")
    
    with open("enjoy.txt", encoding="utf-8") as f:
        enjoy_words = [line.strip() for line in f if line.strip()]
    with open("words.txt", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    if words:
        index = (datetime.utcnow() + timedelta(hours=9)).day % len(words)
        today_word = words[index]
    else:
        today_word = "（言葉がありません）"

    return render_template(
        "index.html",
        mode=mode,
        count=get_db_count(),
        date_text=date_text,
        tone="",
        user_text="こんにちは",
        reply="",
        today_word=today_word,
        enjoy_words=enjoy_words
    )

@app.route("/toggle_mode", methods=["POST"])
def toggle_mode():
    current = session.get("mode", "gift")

    if current == "gift":
        session["mode"] = "aiemon"
    elif current == "aiemon":
        session["mode"] = "concierge"
    else:
        session["mode"] = "gift"

    return "OK"

@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    user_text = data.get("user_text", "")
    mode = session.get("mode", "gift")
    history = session.get("history", [])

    # words.txt 読み込み
    with open("words.txt", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    # 空入力 → 今日の言葉
    if user_text.strip() == "":
        if words:
            index = (datetime.utcnow() + timedelta(hours=9)).day % len(words)
            reply = words[index]
        else:
            reply = "（言葉がありません）"
        return jsonify({
            "reply": reply,
            "count": get_db_count()
        })
    # 通常入力（モード別）
    reply = generate_response(user_text, mode, history)

    return jsonify({
        "reply": reply,
        "count": get_db_count()
    })
    
if __name__ == "__main__":
    app.run(debug=True)
