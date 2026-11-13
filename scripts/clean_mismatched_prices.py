import logging
from database import SyncSessionLocal
from models import PriceResult, GameCatalog
from services.filters import matches_game_name, quick_reject
from services.config import redis_client
from sqlalchemy import select, delete

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_mismatched")

def clean_database():
    db = SyncSessionLocal()
    try:
        results = db.execute(
            select(PriceResult, GameCatalog.name).join(GameCatalog, PriceResult.game_id == GameCatalog.id)
        ).all()

        to_delete_ids = []
        for pr, gname in results:
            if quick_reject(pr.lot_name, ""):
                to_delete_ids.append(pr.id)
            elif not matches_game_name(pr.lot_name, gname, strict=True):
                to_delete_ids.append(pr.id)

        logger.info("Found %d mismatched/stale price records out of %d total", len(to_delete_ids), len(results))

        if to_delete_ids:
            # Batch delete in chunks of 500
            chunk_size = 500
            deleted = 0
            for i in range(0, len(to_delete_ids), chunk_size):
                chunk = to_delete_ids[i:i + chunk_size]
                res = db.execute(delete(PriceResult).where(PriceResult.id.in_(chunk)))
                deleted += res.rowcount
            db.commit()
            logger.info("Successfully deleted %d contaminated price records from DB", deleted)

        # Clear Redis price cache
        keys = redis_client.keys("price_cache:*")
        if keys:
            redis_client.delete(*keys)
            logger.info("Flushed %d stale price cache keys in Redis", len(keys))

    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
