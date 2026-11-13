import logging
import os
import re
import sys
import time
import requests
from dotenv import load_dotenv

from database import SyncSessionLocal
from models import GameCatalog, UserTask, PriceResult

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("telegram_bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")


def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error("Error sending message to %s: %s", chat_id, e)
        return False


def answer_callback_query(callback_query_id: str, text: str = ""):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or BOT_TOKEN
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_query_id, "text": text}, timeout=5)
    except Exception:
        pass


def handle_start(chat_id: int, text: str):
    parts = text.strip().split()
    if len(parts) > 1 and parts[1].startswith("track_"):
        # Format: /start track_<game_id>_<target_price>
        m = re.match(r"^track_(\d+)_(\d+(?:\.\d+)?)$", parts[1])
        if m:
            game_id = int(m.group(1))
            target_price = float(m.group(2))
            subscribe_user(chat_id, game_id, target_price)
            return

    msg = (
        "👋 <b>Добро пожаловать в бота LootoZavr!</b>\n\n"
        "Я отслеживаю цены на цифровые ключи Steam и внутриигровой донат в 10 проверенных магазинах.\n\n"
        "⚡ <b>Как подписаться:</b>\n"
        f"1. Найдите игру на сайте <a href='{BASE_URL}'>LootoZavr</a>\n"
        "2. Нажмите <b>«Отслеживать цену»</b> и выберите <b>«Подписаться в 1 клик»</b>\n"
        "3. Я пришлю вам мгновенное уведомление со ссылкой на покупку, как только цена снизится до желаемой!\n\n"
        "🔍 <b>Вы также можете отправить мне название любой игры</b> (например, <i>Cyberpunk</i> или <i>Helldivers</i>), и я найду лучшую цену прямо здесь!\n\n"
        "<b>Команды:</b>\n"
        "/alerts — Список ваших активных подписок\n"
        "/help — Справка"
    )
    send_message(chat_id, msg)


def subscribe_user(chat_id: int, game_id: int, target_price: float):
    db = SyncSessionLocal()
    try:
        game = db.get(GameCatalog, game_id)
        if not game:
            send_message(chat_id, "❌ Игра не найдена в каталоге.")
            return

        existing = (
            db.query(UserTask)
            .filter(UserTask.chat_id == chat_id, UserTask.game_id == game_id)
            .first()
        )
        if existing:
            existing.target_price = target_price
            task_id = existing.id
            db.commit()
            action = "обновили порог цены"
        else:
            task = UserTask(chat_id=chat_id, game_id=game_id, target_price=target_price)
            db.add(task)
            db.commit()
            task_id = task.id
            action = "подписались на отслеживание"

        prices = (
            db.query(PriceResult)
            .filter(PriceResult.game_id == game_id, PriceResult.price >= 50.0, PriceResult.price <= 35000.0)
            .order_by(PriceResult.price.asc())
            .all()
        )
        current_min = prices[0].price if prices else None
        best_shop = prices[0].shop_name if prices else None

        min_info = f"\n💰 Текущая лучшая цена: <b>{current_min:.0f} ₽</b> ({best_shop})" if current_min else ""

        reply = (
            f"✅ <b>Вы успешно {action}!</b>\n\n"
            f"🎮 Игра: <b>{game.name}</b>\n"
            f"🎯 Целевая цена: <b>{target_price:.0f} ₽</b>{min_info}\n\n"
            f"Как только цена опустится ниже или сравняется с вашей целью, вы мгновенно получите уведомление со ссылкой на покупку!\n\n"
            f"Чтобы отменить подписку, отправьте: /cancel_{task_id}"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🌐 Открыть на сайте", "url": f"{BASE_URL}/game/{game_id}"},
                    {"text": "❌ Отменить подписку", "callback_data": f"cancel_{task_id}"},
                ]
            ]
        }
        send_message(chat_id, reply, reply_markup=reply_markup)
    except Exception as e:
        db.rollback()
        logger.error("subscribe_user error: %s", e)
        send_message(chat_id, "❌ Произошла ошибка при сохранении подписки. Попробуйте снова.")
    finally:
        db.close()


def handle_alerts(chat_id: int):
    db = SyncSessionLocal()
    try:
        tasks = (
            db.query(UserTask)
            .filter(UserTask.chat_id == chat_id)
            .all()
        )
        if not tasks:
            send_message(
                chat_id,
                "У вас пока нет активных подписок.\n"
                f"Найдите игру на сайте <a href='{BASE_URL}'>LootoZavr</a> или напишите мне её название!",
            )
            return

        lines = ["📋 <b>Ваши активные подписки:</b>\n"]
        buttons = []
        for t in tasks:
            game_name = t.game.name if t.game else f"Игра #{t.game_id}"
            lines.append(f"• <b>{game_name}</b> — цель: <b>{t.target_price:.0f} ₽</b> (/cancel_{t.id})")
            buttons.append([
                {"text": f"❌ {game_name[:20]}", "callback_data": f"cancel_{t.id}"},
                {"text": "🌐 На сайт", "url": f"{BASE_URL}/game/{t.game_id}"}
            ])

        lines.append("\nНажмите на кнопку ниже, чтобы отменить отслеживание:")
        send_message(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": buttons})
    finally:
        db.close()


def handle_cancel(chat_id: int, task_id: int):
    db = SyncSessionLocal()
    try:
        task = db.query(UserTask).filter(UserTask.id == task_id, UserTask.chat_id == chat_id).first()
        if not task:
            send_message(chat_id, "❌ Подписка не найдена или уже удалена.")
            return

        game_name = task.game.name if task.game else f"Игра #{task.game_id}"
        db.delete(task)
        db.commit()
        send_message(chat_id, f"🗑 Отслеживание цены для <b>{game_name}</b> отключено.")
    except Exception as e:
        db.rollback()
        logger.error("handle_cancel error: %s", e)
        send_message(chat_id, "Ошибка при отмене подписки.")
    finally:
        db.close()


def handle_search(chat_id: int, query: str):
    clean_q = query.strip()
    if len(clean_q) < 2:
        send_message(chat_id, "Введите не менее 2 символов для поиска игры.")
        return

    db = SyncSessionLocal()
    try:
        games = (
            db.query(GameCatalog)
            .filter(GameCatalog.name.ilike(f"%{clean_q}%"))
            .limit(5)
            .all()
        )
        if not games:
            send_message(
                chat_id,
                f"По запросу <i>«{clean_q}»</i> ничего не найдено в базе.\n"
                f"Попробуйте поискать на сайте <a href='{BASE_URL}'>LootoZavr</a>.",
            )
            return

        lines = [f"🔍 <b>Результаты поиска по запросу «{clean_q}»:</b>\n"]
        buttons = []
        for g in games:
            prices = (
                db.query(PriceResult)
                .filter(PriceResult.game_id == g.id, PriceResult.price >= 50.0, PriceResult.price <= 35000.0)
                .order_by(PriceResult.price.asc())
                .all()
            )
            if prices:
                best = prices[0]
                lines.append(f"🎮 <b>{g.name}</b> — от <b>{best.price:.0f} ₽</b> ({best.shop_name})")
                suggested_target = max(50, int(best.price * 0.9))
                buttons.append([
                    {"text": f"🔔 Следить ({suggested_target} ₽)", "callback_data": f"sub_{g.id}_{suggested_target}"},
                    {"text": "🌐 К предложениям", "url": f"{BASE_URL}/game/{g.id}"}
                ])
            else:
                lines.append(f"🎮 <b>{g.name}</b> — цен пока нет в базе")
                buttons.append([
                    {"text": f"🌐 Открыть {g.name[:20]}", "url": f"{BASE_URL}/game/{g.id}"}
                ])

        send_message(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        logger.error("handle_search error: %s", e)
        send_message(chat_id, "Ошибка поиска. Попробуйте снова.")
    finally:
        db.close()


def handle_callback_query(cq: dict):
    cq_id = cq.get("id")
    from_user = cq.get("from", {})
    chat_id = from_user.get("id")
    data = cq.get("data", "")

    if not chat_id or not data:
        return

    if data.startswith("cancel_"):
        try:
            task_id = int(data.replace("cancel_", ""))
            handle_cancel(chat_id, task_id)
            answer_callback_query(cq_id, "Отслеживание отменено")
        except Exception:
            answer_callback_query(cq_id, "Ошибка")
    elif data.startswith("sub_"):
        try:
            parts = data.split("_")
            game_id = int(parts[1])
            target_price = float(parts[2])
            subscribe_user(chat_id, game_id, target_price)
            answer_callback_query(cq_id, "Подписка оформлена!")
        except Exception:
            answer_callback_query(cq_id, "Ошибка")


def handle_update(update: dict):
    if "callback_query" in update:
        handle_callback_query(update["callback_query"])
        return

    msg = update.get("message")
    if not msg:
        return
    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return

    logger.info("Message from %s: %s", chat_id, text)

    if text.startswith("/start"):
        handle_start(chat_id, text)
    elif text in ("/alerts", "/list", "подписки"):
        handle_alerts(chat_id)
    elif text.startswith("/cancel_"):
        try:
            task_id = int(text.replace("/cancel_", ""))
            handle_cancel(chat_id, task_id)
        except ValueError:
            send_message(chat_id, "Неверный формат команды отмены.")
    elif text in ("/help", "помощь", "/info"):
        handle_start(chat_id, "/start")
    else:
        # Default: smart search by game title!
        handle_search(chat_id, text)


def run_bot_polling():
    global BOT_TOKEN
    offset = 0
    is_first_run = True
    logger.info("Telegram-бот LootoZavr инициализирован.")

    while True:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or BOT_TOKEN
        if not token:
            logger.info("⏳ Ожидание TELEGRAM_BOT_TOKEN в .env... (контейнер активен, перезапуск не требуется)")
            time.sleep(15)
            load_dotenv(override=True)
            continue

        if is_first_run or BOT_TOKEN != token:
            BOT_TOKEN = token
            logger.info("Бот LootoZavr успешно авторизован под токеном и запущен (getUpdates)!")
            is_first_run = False
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 25}
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("result", []):
                    offset = item["update_id"] + 1
                    handle_update(item)
            elif resp.status_code == 401:
                logger.error("Неверный токен TELEGRAM_BOT_TOKEN (401 Unauthorized). Проверьте токен в .env.")
                time.sleep(20)
                load_dotenv(override=True)
            else:
                logger.warning("getUpdates response %d: %s", resp.status_code, resp.text)
                time.sleep(5)
        except Exception as e:
            logger.error("Polling error: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    run_bot_polling()
