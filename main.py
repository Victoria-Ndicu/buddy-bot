import uuid
import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import openai

# ==============================
# Load environment variables
# ==============================
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")  # optional security layer

# ==============================
# Initialize app
# ==============================
app = Flask(__name__)

# Allow all origins (safe for Flutter mobile)
CORS(app)

# ==============================
# In-memory session store
# ==============================
# NOTE: Replace with Redis/DB in production
session_threads = {}

# ==============================
# Health check
# ==============================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "ok",
        "message": "Bot server is running 🚀"
    })


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
        # Get or create thread
        # --------------------------
        thread_id = session_threads.get(user_id)

        if not thread_id:
            thread = openai.beta.threads.create()
            thread_id = thread.id
            session_threads[user_id] = thread_id

        # --------------------------
        # Add user message
        # --------------------------
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # --------------------------
        # Run assistant
        # --------------------------
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=os.getenv("ASSISTANT_ID")
        )

        # --------------------------
        # Wait for completion (safe polling)
        # --------------------------
        max_retries = 20
        for _ in range(max_retries):
            status = openai.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

            if status.status == "completed":
                break
            elif status.status in ["failed", "cancelled", "expired"]:
                return jsonify({"error": f"Run {status.status}"}), 500

            time.sleep(0.5)
        else:
            return jsonify({"error": "Timeout waiting for response"}), 504

        # --------------------------
        # Get latest assistant reply
        # --------------------------
        messages = openai.beta.threads.messages.list(thread_id=thread_id)

        bot_reply = None
        for msg in messages.data:
            if msg.role == "assistant":
                bot_reply = msg.content[0].text.value
                break

        if not bot_reply:
            return jsonify({"error": "No response from assistant"}), 500

        # --------------------------
        # Success response
        # --------------------------
        return jsonify({
            "reply": bot_reply,
            "thread_id": thread_id
        })

    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


# ==============================
# Run app
# ==============================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Railway compatibility
    app.run(host="0.0.0.0", port=port, debug=True)