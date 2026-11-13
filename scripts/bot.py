"""
Telegram-бот для трекера цен LootoZavr.
Позволяет подписываться на уведомления о снижении цен прямо из Telegram.

Запуск:
python scripts/bot.py
(Требуется переменная TELEGRAM_BOT_TOKEN в файле .env)
"""
import asyncio
import logging
import os
import sys

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import delete, select

from database import AsyncSessionLocal
from models import GameCatalog, PriceResult, UserTask
from services.config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

if not TELEGRAM_BOT_TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN не задан в .env! Задайте токен для запуска бота.")

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    chat_id = message.chat.id

    # Проверяем Deep Link вида: /start track_42_1500 или /start track_42
    if command.args and command.args.startswith("track_"):
        parts = command.args[len("track_"):].split("_")
        raw_game_id = parts[0]
        raw_target_price = parts[1] if len(parts) > 1 else None

        if raw_game_id.isdigit():
            game_id = int(raw_game_id)
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(GameCatalog).where(GameCatalog.id == game_id))
                game = res.scalars().first()

                if game:
                    target_price = None
                    if raw_target_price:
                        try:
                            target_price = float(raw_target_price)
                        except ValueError:
                            pass

                    # Получим минимальную цену
                    price_res = await session.execute(
                        select(PriceResult)
                        .where(PriceResult.game_id == game.id)
                        .order_by(PriceResult.price.asc())
                        .limit(1)
                    )
                    best_price = price_res.scalars().first()
                    min_price = best_price.price if best_price else 1000.0

                    if not target_price or target_price <= 0:
                        target_price = round(min_price * 0.9)

                    # Добавляем задачу отслеживания
                    task = UserTask(
                        game_id=game.id,
                        target_price=target_price,
                        chat_id=chat_id,
                    )
                    session.add(task)
                    await session.commit()

                    current_price_str = f"{best_price.price} ₽ ({best_price.shop_name})" if best_price else "нет данных"
                    await message.answer(
                        f"⚡ <b>Подписка в 1 клик оформлена!</b>\n\n"
                        f"🎮 Игра: <b>{game.name}</b>\n"
                        f"🎯 Желаемая цена: <b>{target_price} ₽</b>\n"
                        f"💰 Текущая лучшая цена: <b>{current_price_str}</b>\n\n"
                        f"Как только цена снизится до <b>{target_price} ₽</b> или ниже — я мгновенно пришлю ссылку на покупку!",
                        parse_mode=ParseMode.HTML,
                    )
                    return

    text = (
        f"👋 <b>Привет! Я бот агрегатора LootoZavr.</b>\n\n"
        f"Твой Chat ID: <code>{chat_id}</code>\n\n"
        f"Ты можешь использовать этот ID на сайте <b>LootoZavr</b> для подписки на уведомления, "
        f"либо управлять подписками прямо здесь:\n\n"
        f"🔹 <code>/track &lt;Название игры&gt; &lt;Цена&gt;</code> — подписаться на цену\n"
        f"🔹 <code>/list</code> — список моих подписок\n"
        f"🔹 <code>/search &lt;Название игры&gt;</code> — проверить текущие цены\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("track"))
async def cmd_track(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Формат команды: <code>/track &lt;Название игры&gt; &lt;Цена в рублях&gt;</code>\n"
            "Пример: <code>/track Cyberpunk 2077 1500</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw_game_name = args[1]
    raw_price = args[2]

    # Если название содержит пробелы, например /track Elden Ring 2000
    # Пробуем распарсить последнее слово как число
    parts = message.text[len("/track "):].rsplit(maxsplit=1)
    if len(parts) == 2:
        game_query = parts[0].strip()
        try:
            target_price = float(parts[1].replace(",", "."))
        except ValueError:
            await message.answer("❌ Укажите корректную числовую цену!")
            return
    else:
        await message.answer("❌ Неверный формат.")
        return

    async with AsyncSessionLocal() as session:
        # Ищем игру в БД
        res = await session.execute(
            select(GameCatalog).where(GameCatalog.name.ilike(f"%{game_query}%")).limit(1)
        )
        game = res.scalars().first()

        if not game:
            await message.answer(
                f"❌ Игра <b>'{game_query}'</b> не найдена в каталоге. Попробуйте найти её на сайте или проверьте написание.",
                parse_mode=ParseMode.HTML,
            )
            return

        # Добавляем задачу
        task = UserTask(
            game_id=game.id,
            target_price=target_price,
            chat_id=message.chat.id,
        )
        session.add(task)
        await session.commit()

        # Проверим текущую минимальную цену
        price_res = await session.execute(
            select(PriceResult)
            .where(PriceResult.game_id == game.id)
            .order_by(PriceResult.price.asc())
            .limit(1)
        )
        best_price = price_res.scalars().first()

    current_price_str = f"{best_price.price} ₽ ({best_price.shop_name})" if best_price else "нет данных"
    await message.answer(
        f"✅ <b>Подписка оформлена!</b>\n\n"
        f"🎮 Игра: <b>{game.name}</b>\n"
        f"🎯 Желаемая цена: <b>{target_price} ₽</b>\n"
        f"💰 Текущая лучшая цена: <b>{current_price_str}</b>\n\n"
        f"Как только цена снизится до указанной или ниже — я сразу пришлю уведомление со ссылкой на магазин!",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserTask, GameCatalog)
            .join(GameCatalog, UserTask.game_id == GameCatalog.id)
            .where(UserTask.chat_id == message.chat.id)
        )
        tasks = res.all()

    if not tasks:
        await message.answer("У вас пока нет активных отслеживаний цен. Используйте /track для создания.")
        return

    text = "📋 <b>Ваши активные отслеживания цен:</b>\n\n"
    for task, game in tasks:
        text += f"• <b>{game.name}</b> — до <b>{task.target_price} ₽</b> (ID: {task.id})\n"
    text += "\nЧтобы удалить подписку, используйте: <code>/untrack &lt;ID&gt;</code>"

    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("untrack"))
async def cmd_untrack(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Формат: <code>/untrack &lt;ID подписки из /list&gt;</code>", parse_mode=ParseMode.HTML)
        return

    task_id = int(args[1])
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            delete(UserTask)
            .where(UserTask.id == task_id, UserTask.chat_id == message.chat.id)
        )
        await session.commit()

        if res.rowcount > 0:
            await message.answer(f"✅ Отслеживание #{task_id} успешно удалено.")
        else:
            await message.answer(f"❌ Подписка #{task_id} не найдена среди ваших активных задач.")


@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: <code>/search &lt;Название игры&gt;</code>", parse_mode=ParseMode.HTML)
        return

    query = parts[1].strip()
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(GameCatalog).where(GameCatalog.name.ilike(f"%{query}%")).limit(1)
        )
        game = res.scalars().first()

        if not game:
            await message.answer(f"❌ Игра <b>'{query}'</b> не найдена в базе.", parse_mode=ParseMode.HTML)
            return

        prices_res = await session.execute(
            select(PriceResult)
            .where(PriceResult.game_id == game.id)
            .order_by(PriceResult.price.asc())
            .limit(5)
        )
        prices = prices_res.scalars().all()

    if not prices:
        await message.answer(f"🎮 <b>{game.name}</b> найдена, но цены пока не спарсены.", parse_mode=ParseMode.HTML)
        return

    text = f"🎮 <b>{game.name}</b> — лучшие предложения:\n\n"
    for p in prices:
        text += f"• <b>{p.price} ₽</b> — {p.shop_name} ({p.region}) | <a href='{p.lot_url}'>Ссылка</a>\n"

    await message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: задайте TELEGRAM_BOT_TOKEN в .env перед запуском бота.")
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    print("Telegram-бот запущен и слушает команды...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
