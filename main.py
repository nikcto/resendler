import os
import random
import json
import re
from datetime import time
from zoneinfo import ZoneInfo

import requests
from telegram import Update, InputMediaPhoto
from telegram.error import TimedOut, RetryAfter, NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8312290025:AAGopLqsM73cT_Sxyqqpo3xpUFtY0aZ8rRI"


# публичная ссылка облака
CLOUD_LINK = "https://cloud.mail.ru/public/RMub/UFriaDgUk"

TZ_EKB = ZoneInfo("Asia/Yekaterinburg")

FUNNY_CAPTIONS = [
    "Мясо? 🔥🔥🔥",
    "Заряжаем день контентом 💥",
    "Вот это я понимаю подборочка 😎",
    "Утренний пакет счастья 📦",
    "Просыпаемся, у нас тут движ 🤟",
    "Доброе утро, блять, держись ☀️",
    "С утра уже ебашим контент 💣",
    "Пока ты спал — тут пиздец происходил 😈",
    "Проснулся? На, держи разъёб 🤯",
    "Утро начинается не с кофе, а с этого дерьма ☕",
    "Ща как зайдёт — сам охуеешь 😏",
    "Лови заряд, нахуй 🔋",
    "Это не подборка, это ебаный разнос 🚀",
    "Если день не задался — ща исправим, сука",
    "Контент, за который не стыдно, а даже наоборот 😎",
    "Утренний разъёб подоспел 💥",
    "Блять, ну это просто ахуенно",
    "Порция кайфа, без регистрации и смс 😏",
    "Щас залипнешь и не отлипнешь, отвечаю",
    "Нормально так утро начали, да? 😉",
    "Это тебе не хуйня какая-то, это уровень",
    "Смотри и не выёбывайся 👀",
    "Погнали нахуй в новый день 🚀",
    "Если не зашло — значит ты врёшь",
    "Такое утро я уважаю, бля",
    "Ебите меня семеро это че за львы",
    "Уфф бляя тигры бля",
]


def get_files():
    # Страница публичной папки, из неё достаём JSON с описанием файлов
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    }

    resp = requests.get(CLOUD_LINK, headers=headers)
    if resp.status_code != 200:
        print("Не удалось получить страницу облака, статус:", resp.status_code)
        return []

    html = resp.text

    # Универсальный способ: просто вытащим все значения поля "weblink"
    # и соберём по ним ссылки на файлы.
    weblinks = re.findall(r'"weblink"\s*:\s*"([^"]+)"', html)

    files = [
        "https://cloud.mail.ru/public/" + link
        for link in weblinks
    ]

    # Убираем дубли, если вдруг есть
    files = list(dict.fromkeys(files))

    print(f"Найдено файлов в облаке: {len(files)}")
    return files


FILES = get_files()


async def send_photos(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data or {}
    chat_id = job_data.get("chat_id")
    amount = job_data.get("amount", 10)

    if not chat_id:
        return

    if not FILES:
        return

    selected = random.sample(FILES, min(amount, len(FILES)))

    # Отправляем пачками по 10 фото (ограничение Telegram)
    for i in range(0, len(selected), 10):
        chunk = selected[i:i + 10]
        caption = random.choice(FUNNY_CAPTIONS)
        media = []
        for j, url in enumerate(chunk):
            if j == 0:
                media.append(InputMediaPhoto(url, caption=caption))
            else:
                media.append(InputMediaPhoto(url))
        await context.bot.send_media_group(chat_id, media)


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /test 10
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Использование: /test <количество>")
        return

    amount = int(context.args[0])

    if not FILES:
        await update.message.reply_text("Нет доступных файлов в облаке.")
        return

    selected = random.sample(FILES, min(amount, len(FILES)))

    # Пачками по 10 фото
    for i in range(0, len(selected), 10):
        chunk = selected[i:i + 10]
        media = [InputMediaPhoto(url) for url in chunk]
        try:
            await update.message.reply_media_group(media)
        except (TimedOut, RetryAfter, NetworkError) as e:
            # Логируем в консоль, но не роняем бота
            print(f"Ошибка отправки медиа-группы: {e}")


async def cmd_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /day 10
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Использование: /day <количество>")
        return

    amount = int(context.args[0])

    chat_id = update.effective_chat.id

    # планируем ежедневную отправку
    # Railway, как правило, работает в UTC, поэтому:
    # 07:00 по Уфе (UTC+5) = 02:00 по UTC
    context.job_queue.run_daily(
        send_photos,
        time=time(hour=2, minute=0),
        data={"chat_id": chat_id, "amount": amount},
        name=str(chat_id)
    )

    await update.message.reply_text(
        f"Ок, {amount} шт"
    )


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    # Команды работают и в ЛС, и в группах (даже с включённой privacy mode)
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("day", cmd_day))

    # при желании можно оставить обработчик обычного текста
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()
