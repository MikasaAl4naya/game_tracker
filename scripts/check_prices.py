from database import SyncSessionLocal
from models import PriceResult, GameCatalog

def check():
    db = SyncSessionLocal()
    for gid, title in [(9, "ELDEN RING"), (351, "ELDEN RING NIGHTREIGN")]:
        prices = db.query(PriceResult).filter(PriceResult.game_id == gid).all()
        print(f"\n=== {title} (ID: {gid}) - Total prices: {len(prices)} ===")
        for p in prices:
            print(f"[{p.shop_name}] {p.price} ₽ | {p.region} | {p.lot_name} | {p.lot_url}")

if __name__ == "__main__":
    check()
