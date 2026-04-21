from flask import Flask, render_template, request
from openai import OpenAI

import psycopg2

conn = psycopg2.connect("postgresql://postgres.pzwyezklgdorszbleesz:[hitone27182818]@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres")
cur = conn.cursor()
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
import os
client = OpenAI(
api_key = os.getenv("OPENAI_API_KEY")
)

@app.route("/", methods=["GET", "POST"])
def index():
    reply = ""
    user_text = ""
    today_word = get_today_word()


    if request.method == "POST":
        user_text = request.form.get("user_text", "").strip()

        if not user_text:
            reply = ""
        else:
            count = load_count()
            count += 1
            save_count(count)
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
                            )
                        },
                        {
                            "role": "user",
                            "content": f"ユーザーの言葉：{user_text}"
                        }
                    ]
                )

                reply = response.output_text.strip()

                if not reply:
                    reply = "（返答が空でした）"

            except Exception as e:
                reply = f"（接続エラー）\n{e}"

    count = load_count()
    return render_template(
        "index.html",
        count=count,
        reply=reply,
        date_text=get_date_text(),
        user_text=user_text,
        today_word=today_word
    )

if __name__ == "__main__":
    app.run(debug=True)
