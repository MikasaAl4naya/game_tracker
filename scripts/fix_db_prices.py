import logging
from database import SyncSessionLocal
from models import PriceResult
from sqlalchemy import text
from services.config import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_db_prices")

def run():
    db = SyncSessionLocal()
    try:
        # 1. Исправляем ссылки Zaka-Zaka (добавляем /game/ ко всем ссылкам, где его нет)
        res1 = db.execute(text(
            "UPDATE price_results "
            "SET lot_url = REPLACE(lot_url, 'https://zaka-zaka.com/', 'https://zaka-zaka.com/game/') "
            "WHERE shop_name = 'Zaka-Zaka' AND lot_url NOT LIKE '%/game/%'"
        ))
        logger.info("Updated Zaka-Zaka URLs: %d", res1.rowcount)

        # 2. Удаляем ошибочные предложения для ELDEN RING (id=9)
        res2 = db.execute(text(
            "DELETE FROM price_results "
            "WHERE game_id = 9 AND ("
            "  lot_name ILIKE '%nightreign%' "
            "  OR lot_name ILIKE '%erdtree%' "
            "  OR lot_name ILIKE '%forsaken%'"
            ")"
        ))
        logger.info("Deleted contaminated ELDEN RING (id=9) prices: %d", res2.rowcount)

        # 3. Удаляем ошибочные DLC-предложения для ELDEN RING NIGHTREIGN (id=351)
        res3 = db.execute(text(
            "DELETE FROM price_results "
            "WHERE game_id = 351 AND ("
            "  lot_name ILIKE '%forsaken%' "
            "  OR lot_name ILIKE '%hollows%' "
            "  OR lot_name ILIKE '%upgrade pack%'"
            ")"
        ))
        logger.info("Deleted contaminated ELDEN RING NIGHTREIGN (id=351) prices: %d", res3.rowcount)

        # 4. Также удаляем старые Zaka-Zaka цены для id=9 и id=351, чтобы они перепарсились начисто
        res4 = db.execute(text(
            "DELETE FROM price_results "
            "WHERE shop_name = 'Zaka-Zaka' AND game_id IN (9, 351)"
        ))
        logger.info("Deleted old Zaka-Zaka prices for games 9 and 351: %d", res4.rowcount)

        db.commit()

        # Очищаем кэш Redis для этих игр
        for prefix in ("zakazaka", "plati", "ggsel", "funpay", "steambuy", "steampay", "gabestore"):
            redis_client.delete(f"price_cache:{prefix}:ELDEN RING")
            redis_client.delete(f"price_cache:{prefix}:ELDEN RING NIGHTREIGN")
        logger.info("Cleared Redis price cache for ELDEN RING and ELDEN RING NIGHTREIGN")

    finally:
        db.close()

if __name__ == "__main__":
    run()
