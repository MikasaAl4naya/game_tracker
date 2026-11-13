import asyncio
import logging
from datetime import datetime
from sqlalchemy import text
from database import AsyncSessionLocal
from services.config import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_prices")

async def run_cleanup():
    async with AsyncSessionLocal() as db:
        # 1. Clean up corrupt FunPay records from 2026-11-12 (USD currency parsed as RUB)
        res_funpay = await db.execute(text("""
            DELETE FROM price_results
            WHERE shop_name LIKE 'FunPay%'
              AND timestamp >= '2026-11-12 00:00:00'
              AND timestamp < '2026-11-13 00:00:00'
        """))
        funpay_deleted = res_funpay.rowcount
        logger.info(f"Deleted {funpay_deleted} corrupt FunPay USD records from 2026-11-12.")

        # 2. Clean up Keysforgamers console account rentals/shares
        res_kfg = await db.execute(text("""
            DELETE FROM price_results
            WHERE shop_name = 'Keysforgamers'
              AND (
                lot_url LIKE '%buy-konsolnyh-akkauntov%'
                OR lot_url LIKE '%akkaunt%'
                OR lot_url LIKE '%account%'
                OR lot_url LIKE '%arenda%'
              )
        """))
        kfg_deleted = res_kfg.rowcount
        logger.info(f"Deleted {kfg_deleted} Keysforgamers console account records.")

        # 3. Clean up any other weird price outliers (< 40 rub for non-free games)
        res_low = await db.execute(text("""
            DELETE FROM price_results
            WHERE price < 40.0
        """))
        low_deleted = res_low.rowcount
        logger.info(f"Deleted {low_deleted} PriceResult records with price < 40 RUB.")

        await db.commit()

    # 4. Flush Redis catalog cache
    try:
        keys = redis_client.keys("catalog:popular:*")
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} Redis catalog:popular cache keys.")
    except Exception as e:
        logger.warning(f"Failed to clear Redis keys: {e}")

    logger.info("Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(run_cleanup())
