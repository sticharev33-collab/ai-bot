import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("AI_API_KEY"),
    base_url=os.getenv("AI_BASE_URL", "https://openrouter.ai/api/v1"),
)
MODEL = os.getenv("AI_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "Ты - дружелюбный ИИ-ассистент. Отвечай на русском языке.")
conversations = {}
MAX_HISTORY = 20

async def ask_ai(user_id, user_message):
    if user_id not in conversations:
        conversations[user_id] = []
    history = conversations[user_id]
    history.append({"role": "user", "content": user_message})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        conversations[user_id] = history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    try:
        response = await client.chat.completions.create(model=MODEL, messages=messages, max_tokens=2000, temperature=0.7)
        assistant_message = response.choices[0].message.content or "Нет ответа."
        history.append({"role": "assistant", "content": assistant_message})
        conversations[user_id] = history
        return assistant_message
    except Exception as e:
        print("[AI ERROR] {}".format(e))
        return "Ошибка ИИ. Попробуйте позже."

def clear_history(user_id):
    conversations.pop(user_id, None)
