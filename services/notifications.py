import logging
import requests
from datetime import datetime
from sqlalchemy import select

from database import SyncSessionLocal
from models import GameCatalog, UserTask
from services.config import TELEGRAM_BOT_TOKEN, redis_client

logger = logging.getLogger(__name__)


def send_telegram_message(chat_id: int, text: str) -> bool:
    """Отправляет сообщение пользователю через Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.debug("TELEGRAM_BOT_TOKEN не задан, пропускаем отправку.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logger.info("Уведомление отправлено в Telegram chat_id=%s", chat_id)
            return True
        else:
            logger.warning("Ошибка отправки Telegram: %s", resp.text)
            return False
    except Exception as e:
        logger.error("Сетевая ошибка при отправке в Telegram: %s", e)
        return False


def check_and_notify_price_alerts(game_id: int, prices_list: list[dict]) -> int:
    """
    Проверяет, достигли ли цены целевого порога пользователей (UserTask),
    и отправляет уведомления с защитой от спама.
    """
    if not prices_list:
        return 0

    db = SyncSessionLocal()
    notified_count = 0
    try:
        tasks = db.execute(
            select(UserTask).where(UserTask.game_id == game_id)
        ).scalars().all()

        if not tasks:
            return 0

        game = db.get(GameCatalog, game_id)
        game_name = game.name if game else f"Game #{game_id}"

        for task in tasks:
            if not task.target_price or not task.chat_id:
                continue

            matching = [p for p in prices_list if p.get("price") and p["price"] <= task.target_price]
            if not matching:
                continue

            best = min(matching, key=lambda x: x["price"])
            lock_key = f"alert_sent:{task.chat_id}:{game_id}:{int(best['price'])}"

            # Защита от спама: не слать повторно на ту же цену чаще 1 раза в 12 часов
            if redis_client.get(lock_key):
                continue

            text = (
                f"🎯 <b>Цена снизилась!</b>\n\n"
                f"🎮 Игра: <b>{game_name}</b>\n"
                f"🏷 Магазин: <b>{best.get('shop_name', 'Магазин')}</b>\n"
                f"🌍 Регион: <b>{best.get('region', 'Unknown')}</b>\n"
                f"💰 Цена: <b>{best['price']} ₽</b> (Ваша цель: {task.target_price} ₽)\n"
                f"📦 Лот: {best.get('lot_name', '')}\n\n"
                f"🔗 <a href='{best.get('lot_url', '')}'>Перейти к предложению</a>"
            )

            if send_telegram_message(task.chat_id, text):
                redis_client.setex(lock_key, 43_200, "1")
                notified_count += 1

    except Exception as e:
        logger.error("Ошибка при проверке алертов UserTask для game_id=%s: %s", game_id, e)
    finally:
        db.close()

    return notified_count
