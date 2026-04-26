import os
import re
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# ==============================
# Load environment variables
# ==============================
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")  # optional security layer
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")

# ==============================
# DeepSeek client (OpenAI-compatible)
# ==============================
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==============================
# Initialize app
# ==============================
app = Flask(__name__)
CORS(app)  # Allow all origins (safe for Flutter mobile)

# ==============================
# In-memory session store
# { user_id: [ {role, content}, ... ] }
# NOTE: Replace with Redis/DB in production
# ==============================
session_histories = {}

# ==============================
# Reply formatter
# ==============================
def format_reply(text: str) -> str:
    """
    Cleans up bot replies:
    - Strips markdown asterisks (* and **)
    - Normalises bullet dashes into clean paragraph breaks
    - Collapses excess blank lines
    - Returns neatly spaced paragraphs
    """
    # Remove bold/italic markers (**, *)
    text = re.sub(r'\*{1,3}', '', text)

    # Replace markdown bullet lines (- item or • item) with a blank line + text
    text = re.sub(r'^\s*[-•]\s+', '\n', text, flags=re.MULTILINE)

    # Replace markdown numbered lists (1. item) similarly
    text = re.sub(r'^\s*\d+\.\s+', '\n', text, flags=re.MULTILINE)

    # Collapse 3+ consecutive newlines into exactly 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    return text.strip()

# ==============================
# Health check
# ==============================
@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

# ==============================
# Chat endpoint
# ==============================
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # --------------------------
        # Optional API key protection
        # --------------------------
        if APP_API_KEY:
            client_key = request.headers.get("x-api-key")
            if client_key != APP_API_KEY:
                return jsonify({"error": "Unauthorized"}), 401

        # --------------------------
        # Parse request
        # --------------------------
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        user_message = data.get('message')
        user_id = data.get('user_id')

        if not user_message or not user_id:
            return jsonify({"error": "Missing message or user_id"}), 400

        # --------------------------
        # Get or create conversation history
        # --------------------------
        if user_id not in session_histories:
            session_histories[user_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

        history = session_histories[user_id]
        history.append({"role": "user", "content": user_message})

        # --------------------------
        # Call DeepSeek
        # --------------------------
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=history,
            stream=False
        )

        bot_reply = format_reply(response.choices[0].message.content)

        # --------------------------
        # Save assistant reply to history
        # --------------------------
        history.append({"role": "assistant", "content": bot_reply})

        # --------------------------
        # Success response
        # --------------------------
        return jsonify({
            "reply": bot_reply,
            "user_id": user_id
        })

    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


# ==============================
# Clear session (optional utility)
# ==============================
@app.route('/api/reset', methods=['POST'])
def reset():
    data = request.get_json()
    user_id = data.get('user_id') if data else None
    if user_id and user_id in session_histories:
        del session_histories[user_id]
    return jsonify({"status": "reset"}), 200


# ==============================
# Run app
# ==============================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Railway compatibility
    app.run(host="0.0.0.0", port=port, debug=False)
