import openai

# Set your API key
openai.api_key = "sk-proj-your-actual-key-here"

# Create assistant
assistant = openai.beta.assistants.create(
    name="Bot Buddy Study Assistant",
    instructions="You are a helpful AI study assistant. Answer academic questions clearly and thoroughly.",
    model="gpt-3.5-turbo"
)

print(f"ASSISTANT_ID={assistant.id}")