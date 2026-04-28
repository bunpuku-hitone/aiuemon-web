from flask import Flask, render_template, request, session
from openai import OpenAI

import psycopg2

import os
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

#cur.execute(
#    "INSERT INTO entries (app_name, user_key, input_text, output_text) VALUES (%s, %s, %s, %s)",
#    ("test_app", "test_user", "テスト入力", "テスト出力")
#)
#conn.commit()

def load_words():
    with open("words.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

words = load_words()
import datetime
def get_date_text():
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today = today.date()
    return f"{today.year}年{today.month}月{today.day}日"

BASE_DATE = datetime.date(2026, 1, 1)

def get_today_word():
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today = today.date()
    days_passed = (today - BASE_DATE).days
    index = days_passed % len(words)
    return words[index]

def is_english(text):
    if not text:
        return False
    eng = sum(1 for c in text if c.isascii() and c.isalpha())
    return (eng / len(text)) > 0.6

def load_enjoy_words():
    with open("enjoy.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
enjoy_words = load_enjoy_words()

def load_count():
    try:
        with open("counter.txt", "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_count(count):
    with open("counter.txt", "w") as f:
        f.write(str(count))

app = Flask(__name__)
app.secret_key = "hitone_beta07"
mode = "gift"
import os
client = OpenAI(
api_key = os.getenv("OPENAI_API_KEY")
)

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

@app.route("/", methods=["GET", "POST"])
def index():
    mode = session.get("mode", "gift")
    
    reply = ""
    user_text = ""
    tone = ""
    today_word = get_today_word()


    if request.method == "POST":

        user_text = request.form.get("user_text", "").strip()
        tone = request.form.get("tone", "")

        if not user_text:
            return render_template(
                "index.html",
                count=get_db_count(),
                reply="",
                date_text=get_date_text(),
                user_text="",
                today_word=today_word,
                tone=tone,
                enjoy_words=enjoy_words,
            )
        else:
            count = load_count()
            count += 1
            save_count(count)

            if is_english(user_text):
                system_prompt = "Respond ONLY in English. No Japanese."
            else:
                system_prompt = "日本語で、やさしく短いエッセイで返答してください。"
            if mode == "aiemon":
                system_prompt = "あい右衛門として会話調で返答する。"

            try:
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=[
                        {
                            "role": "system",
                            "content": (
                                "静かに、やわらかく、説明しすぎず、余白を残す語りで返答する。"
                                "出力は20秒程度で読める短い台本（ショートエッセイ）とする。"
                                "語り手の名前は出さない。"
                                "英語の場合は、中学レベルの単語だけで、短くやさしい文章にする。難しい単語は禁止する。"
                                + system_prompt
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"ユーザーの言葉：{user_text}"
                        }
                    ]
                )
                #  reply = response.output[0].content[0].text
                reply = response.output_text.strip()

                if not reply:
                    reply = "（返答が空でした）"

                db_conn = get_db_connection()
                db_cur = db_conn.cursor()
                try:
                    db_cur.execute(
                        "INSERT INTO entries (app_name, user_key, input_text, output_text) VALUES (%s, %s, %s, %s)",
                        ("aiuemon", "user1", user_text, reply)
                    )
                    db_conn.commit()
                except Exception as e:
                    print("insert error:", e)
                finally:
                    db_cur.close()
                    db_conn.close()

            except Exception as e:
                reply = f"（接続エラー）\n{e}"

        
    count = get_db_count()
    return render_template(
        "index.html",
        count=count,
        reply=reply,
        date_text=get_date_text(),
        user_text=user_text,
        today_word=today_word,
        tone=tone,
        enjoy_words=enjoy_words,
        mode=mode,
    )

    return render_template(
        "index.html",
        reply=reply,
        today_word=today_word,
        user_text=user_text,
        tone=tone,
        count=count,
        date_text=date_text,
        enjoy_words=enjoy_words
    )
    
@app.route("/toggle_mode", methods=["POST"])
def toggle_mode():
    current = session.get("mode", "gift")

    if current == "gift":
        session["mode"] = "aiemon"
    else:
        session["mode"] = "gift"

    return "", 204
    
if __name__ == "__main__":
    app.run(debug=True)
