import openai
import os
from dotenv import load_dotenv

# Load .env BEFORE reading any env vars
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Verify it loaded
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY not found — check your .env file")

# Create assistant
assistant = openai.beta.assistants.create(
    name="Bot Buddy Study Assistant",
    instructions="You are a helpful AI study assistant. Answer academic questions clearly and thoroughly.",
    model="gpt-4o-mini"
)

print(f"ASSISTANT_ID={assistant.id}")