import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update

from database import SyncSessionLocal
from models import PriceResult
from services.notifications import check_and_notify_price_alerts

logger = logging.getLogger(__name__)


def save_prices(prices_list: list[dict]) -> None:
    """
    Сохраняет предложения с поддержкой истории изменения цен.
    Если для магазина и региона цена не изменилась за последние 6 часов — обновляется timestamp,
    иначе создается новая историческая запись.
    """
    if not prices_list:
        return

    db = SyncSessionLocal()
    game_id = prices_list[0].get("game_id")
    try:
        now = datetime.utcnow()
        recent_threshold = now - timedelta(hours=6)

        to_insert = []
        for p in prices_list:
            platform = p.get("platform", "Steam") or "Steam"
            p["platform"] = platform

            # Ищем самую свежую запись для данного (game_id, shop_name, region, platform)
            latest = db.execute(
                select(PriceResult)
                .where(
                    PriceResult.game_id == p["game_id"],
                    PriceResult.shop_name == p["shop_name"],
                    PriceResult.region == p["region"],
                    PriceResult.platform == platform,
                )
                .order_by(PriceResult.timestamp.desc())
                .limit(1)
            ).scalars().first()

            if latest and latest.price == p["price"] and latest.timestamp >= recent_threshold:
                # Цена не изменилась за последние 6 часов: просто обновляем timestamp
                latest.timestamp = now
                latest.lot_name = p.get("lot_name", latest.lot_name)
                latest.lot_url = p.get("lot_url", latest.lot_url)
            else:
                # Новая запись (цена изменилась или прошло > 6 часов)
                to_insert.append(PriceResult(**p))

        if to_insert:
            db.add_all(to_insert)

        db.commit()

        # Проверяем целевые цены пользователей и шлем уведомления
        if game_id:
            check_and_notify_price_alerts(game_id, prices_list)

    except Exception as e:
        db.rollback()
        logger.error("Ошибка сохранения цен: %s", e)
        raise
    finally:
        db.close()
