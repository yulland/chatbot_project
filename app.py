from flask import Flask, request, jsonify
import openai
import sqlite3
import difflib
import os

app = Flask(__name__)

openai.api_key = os.environ.get("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")  # 환경 변수 키 이름도 수정!

def init_db():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_reply TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_chat(user_message, bot_reply):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat (user_message, bot_reply) VALUES (?, ?)", (user_message, bot_reply))
    conn.commit()
    conn.close()

def get_recent_chats(limit=5):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, bot_reply FROM chat ORDER BY id DESC LIMIT ?", (limit,))
    chats = cursor.fetchall()
    conn.close()
    return [
        {"role": "user", "content": chat[0]} if i % 2 == 0 else {"role": "assistant", "content": chat[1]}
        for i, chat in enumerate(reversed(chats))
    ]

def find_similar_response(user_input):
    conn = sqlite3.connect("chat_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, bot_reply FROM chat")
    data = cursor.fetchall()
    conn.close()

    best_match = None
    highest_ratio = 0
    for user_msg, bot_reply in data:
        ratio = difflib.SequenceMatcher(None, user_input, user_msg).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = bot_reply

    return best_match if highest_ratio > 0.6 else None

# ✅ DB 초기화용 라우트 (최초 1회만 호출!)
@app.route("/init", methods=["GET"])
def init():
    init_db()
    return "DB initialized!", 200

# ✅ 본격 대화 라우트
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        if not data or "message" not in data:
            return jsonify({"error": "'message' 키가 필요해요."}), 400

        user_message = data["message"].strip()

        db_response = find_similar_response(user_message)
        if db_response:
            save_chat(user_message, db_response)
            return jsonify({"reply": db_response})

        recent_chats = get_recent_chats()
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 다정하고 귀여운 남편 '종떠'야. 대화할 때 '이쁘니', '율띠', '다듀디' 같은 애칭을 자주 쓰고, 장난스럽고 위로도 잘 해줘. 웃긴 말, 장난, 애교 넘치는 표현도 자주 써줘."}
            ] + recent_chats + [{"role": "user", "content": user_message}]
        )

        bot_reply = response.choices[0].message.content
        save_chat(user_message, bot_reply)
        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
