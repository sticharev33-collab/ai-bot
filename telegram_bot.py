import asyncio, os, logging, aiohttp
from collections import deque
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode, ChatType
from aiogram.client.default import DefaultBotProperties
from ai_client import ask_ai, clear_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
bot = Bot(token="8728640848:AAHhv5residcU5YbVZVnVdo1nbVMDXw-tkY", default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
router = Router()
group_messages = {}
MAX_GROUP_MESSAGES = 100
BOT_USERNAME = "stihan_ai_bot"

def save_group_message(chat_id, user_name, text):
    if chat_id not in group_messages:
        group_messages[chat_id] = deque(maxlen=MAX_GROUP_MESSAGES)
    group_messages[chat_id].append({"user": user_name, "text": text})

def get_group_context(chat_id):
    if chat_id not in group_messages or not group_messages[chat_id]:
        return ""
    return "\n".join([f"{m['user']}: {m['text']}" for m in group_messages[chat_id]])

def is_bot_mentioned(message):
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.username == BOT_USERNAME:
            return True
    if message.text and f"@{BOT_USERNAME}" in message.text:
        return True
    return False

async def get_weather(city=""):
    if not city:
        city = "Nalchik"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=ru", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return f"Погода в {city}: {(await resp.text()).strip()}"
    except Exception:
        pass
    return "Не удалось получить погоду."

@router.message(F.text.startswith("/start"))
async def cmd_start(message):
    await message.answer("Привет! Я Стихан. Напиши вопрос.\n/help - справка\n/weather - погода\n/clear - очистить историю")

@router.message(F.text.startswith("/help"))
async def cmd_help(message):
    await message.answer("Я умею отвечать на вопросы, переводить, показывать погоду.\nВ группе - только по @stihan_ai_bot или реплаю.\n/weather Москва - погода в городе")

@router.message(F.text.startswith("/clear"))
async def cmd_clear(message):
    clear_history(f"tg_{message.from_user.id}")
    await message.answer("История очищена.")

@router.message(F.text.startswith("/weather"))
async def cmd_weather(message):
    parts = message.text.split(maxsplit=1)
    await message.answer(await get_weather(parts[1] if len(parts) > 1 else ""), parse_mode=None)

@router.message(F.text)
async def handle_message(message):
    if not message.text or message.text.startswith("/"):
        return
    is_group = message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
    if is_group:
        save_group_message(message.chat.id, message.from_user.full_name or "User", message.text)
        if not is_bot_mentioned(message):
            return
    text = message.text.replace(f"@{BOT_USERNAME}", "").strip()
    if is_group and text.lower() in ["анализ чата", "что обсуждают"]:
        context = get_group_context(message.chat.id)
        if context:
            text = f"Проанализируй чат:\n\n{context}"
        else:
            await message.answer("Нет сообщений для анализа.")
            return
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    response = await ask_ai(f"tg_{message.from_user.id}", text)
    try:
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await message.answer(response, parse_mode=None)

async def main():
    logger.info("Бот запускается...")
    dp.include_router(router)
    await bot.set_my_commands([BotCommand(command="start", description="Начать"), BotCommand(command="help", description="Справка"), BotCommand(command="clear", description="Очистить историю"), BotCommand(command="weather", description="Погода")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
