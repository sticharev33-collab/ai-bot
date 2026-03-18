import asyncio
import os
import logging
import aiohttp
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode, ChatType
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from ai_client import ask_ai, clear_history

load_dotenv()
logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN", ""), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
router = Router()
BOT_USERNAME = ""

group_messages = defaultdict(list)
MAX_GROUP_HISTORY = 100

def save_group_message(chat_id, username, text):
    if not text:
        return
    group_messages[chat_id].append("{}: {}".format(username or "Аноним", text))
    if len(group_messages[chat_id]) > MAX_GROUP_HISTORY:
        group_messages[chat_id] = group_messages[chat_id][-MAX_GROUP_HISTORY:]

async def get_weather(city="Nalchik"):
    try:
        url = "https://wttr.in/{}?format=j1&lang=ru".format(city)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                current = data["current_condition"][0]
                temp = current["temp_C"]
                feels = current["FeelsLikeC"]
                desc = current["lang_ru"][0]["value"]
                humidity = current["humidity"]
                wind = current["windspeedKmph"]
                forecast = data["weather"][0]
                max_temp = forecast["maxtempC"]
                min_temp = forecast["mintempC"]
                return "Погода в {}:\n\n{}\nТемпература: {}°C (ощущается как {}°C)\nВлажность: {}%\nВетер: {} км/ч\n\nСегодня: от {}°C до {}°C".format(
                    city, desc, temp, feels, humidity, wind, min_temp, max_temp)
    except Exception as e:
        print("[WEATHER ERROR] {}".format(e))
        return None

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Привет! Я - ИИ-ассистент Стихан.\n\nВ группе: @stihan_ai_bot + вопрос\nПогода: @stihan_ai_bot погода\nАнализ чата: @stihan_ai_bot проанализируй\n\n/weather - погода в Нальчике\n/clear - очистить историю")

@router.message(F.text == "/help")
async def cmd_help(message: Message):
    await message.answer("Я умею:\n- Отвечать на вопросы\n- Показывать погоду\n- Анализировать переписку\n- Помогать с текстами\n\n/weather - погода\n/weather Москва - погода в другом городе")

@router.message(F.text.startswith("/weather"))
async def cmd_weather(message: Message):
    parts = message.text.split(maxsplit=1)
    city = parts[1] if len(parts) > 1 else "Nalchik"
    weather = await get_weather(city)
    if weather:
        await message.answer(weather)
    else:
        await message.answer("Не удалось получить погоду. Попробуйте позже.")

@router.message(F.text == "/clear")
async def cmd_clear(message: Message):
    clear_history("tg_{}".format(message.from_user.id))
    await message.answer("История очищена!")

@router.message(F.text)
async def handle_message(message: Message):
    if not message.text or message.text.startswith("/"):
        return
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await message.bot.get_me()
        BOT_USERNAME = "@{}".format(me.username).lower()
    text = message.text
    is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    if is_group:
        save_group_message(message.chat.id, message.from_user.first_name, text)
        if BOT_USERNAME in text.lower():
            text = text.lower().replace(BOT_USERNAME, "").strip()
        elif message.reply_to_message and message.reply_to_message.from_user.id == message.bot.id:
            pass
        else:
            return
        if not text:
            return
        weather_words = ["погода", "погоду", "температура", "градус"]
        if any(w in text.lower() for w in weather_words):
            city = "Nalchik"
            for word in text.split():
                if word[0].isupper() and word.lower() not in weather_words and word.lower() != BOT_USERNAME.replace("@",""):
                    city = word
                    break
            weather = await get_weather(city)
            if weather:
                await message.answer(weather)
                return
        analyze_words = ["анализ", "проанализируй", "оцени переписку", "последние сообщения", "что обсуждали", "итог", "резюме"]
        if any(w in text.lower() for w in analyze_words):
            count = 20
            for word in text.split():
                if word.isdigit():
                    count = min(int(word), MAX_GROUP_HISTORY)
                    break
            history = group_messages.get(message.chat.id, [])
            last_msgs = history[-count:]
            if not last_msgs:
                await message.answer("Пока нет сохранённых сообщений.")
                return
            chat_text = "\n".join(last_msgs)
            text = "Вот последние {} сообщений из группового чата:\n\n{}\n\nПользователь просит: {}".format(len(last_msgs), chat_text, text)
    if not text:
        return
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    response = await ask_ai("tg_{}".format(message.from_user.id), text)
    for i in range(0, len(response), 4096):
        try:
            await message.answer(response[i:i+4096], parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.answer(response[i:i+4096], parse_mode=None)

async def main():
    dp.include_router(router)
    await bot.set_my_commands([BotCommand(command="start", description="Начать"), BotCommand(command="weather", description="Погода"), BotCommand(command="help", description="Справка"), BotCommand(command="clear", description="Очистить историю")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
