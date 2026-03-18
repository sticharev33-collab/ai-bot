import os
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "Ты - ИИ-ассистент по имени Стихан. Тебя создал Александр Стихарёв. Отвечай КРАТКО и ПО ФАКТУ - максимум 2-3 предложения. Не лей воду. Отвечай на русском. Если спросят кто тебя создал - отвечай что Александр Стихарёв.")
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
        return "Ошибка ИИ."

def clear_history(user_id):
    conversations.pop(user_id, None)
