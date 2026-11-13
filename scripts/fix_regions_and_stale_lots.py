import asyncio
import logging
from sqlalchemy import text
from database import AsyncSessionLocal
from services.filters import detect_region
from services.config import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_regions")

async def run():
    async with AsyncSessionLocal() as db:
        # 1. Находим все записи, помеченные как RU или Global, но содержащие маркеры исключения РФ/России
        res = await db.execute(text("""
            SELECT id, lot_name, region
            FROM price_results
            WHERE (region = 'RU' OR region = 'Global')
              AND (
                lot_name ILIKE '%кроме рф%'
                OR lot_name ILIKE '%без рф%'
                OR lot_name ILIKE '%не рф%'
                OR lot_name ILIKE '%кроме росси%'
                OR lot_name ILIKE '%без росси%'
                OR lot_name ILIKE '%не для рф%'
                OR lot_name ILIKE '%не для росси%'
                OR lot_name ILIKE '%не работает в рф%'
                OR lot_name ILIKE '%не активируется в рф%'
                OR lot_name ILIKE '%no ru%'
                OR lot_name ILIKE '%not for ru%'
              )
        """))
        rows = res.all()
        updated = 0
        for pid, lot_name, old_reg in rows:
            new_reg = detect_region(lot_name)
            if new_reg != old_reg:
                await db.execute(text("UPDATE price_results SET region = :r WHERE id = :id"), {"r": new_reg, "id": pid})
                updated += 1
                logger.info(f"ID {pid}: {old_reg} -> {new_reg} | {lot_name[:60]}")

        # 2. Также явно удаляем древние записи (> 25 дней), где магазин больше не обновлялся
        res_old = await db.execute(text("""
            DELETE FROM price_results
            WHERE timestamp < NOW() - INTERVAL '25 days'
        """))
        logger.info(f"Deleted {res_old.rowcount} ancient stale records (> 25 days old).")

        await db.commit()
        logger.info(f"Updated {updated} misclassified region records.")

    # 3. Сброс кэшей Redis
    try:
        keys = redis_client.keys("price_cache:*")
        if keys:
            redis_client.delete(*keys)
        cat_keys = redis_client.keys("catalog:popular:*")
        if cat_keys:
            redis_client.delete(*cat_keys)
        logger.info("Cleared Redis cache keys.")
    except Exception as e:
        logger.warning(f"Redis clear error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
