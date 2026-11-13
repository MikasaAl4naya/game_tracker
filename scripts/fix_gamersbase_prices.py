import asyncio
import requests
from database import AsyncSessionLocal
from sqlalchemy import text
from services.filters import parse_price

async def fix():
    session = requests.Session()
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT pr.id, pr.lot_name, pr.price, pr.lot_url FROM price_results pr WHERE pr.shop_name = 'GamersBase' AND pr.price >= 5000;"))
        rows = res.fetchall()
        print(f"Checking {len(rows)} GamersBase rows >= 5000 RUB...")
        updated = 0
        for pid, name, curr_price, url in rows:
            try:
                resp = session.get(
                    "https://gamersbase.store/api/catalogs/search/",
                    params={"searchQuery": name, "isFullTextSearch": "false", "language": "RU"},
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    prods = data.get("products", [])
                    matched = False
                    for p in prods:
                        p_name = p.get("name", "")
                        if p_name.lower() == name.lower() or name.lower() in p_name.lower():
                            p_str = p.get("actual_price_formatted") or p.get("standard_price_formatted") or ""
                            real_price = parse_price(p_str)
                            if real_price and real_price != curr_price:
                                await db.execute(text("UPDATE price_results SET price = :p WHERE id = :id"), {"p": real_price, "id": pid})
                                print(f"Fixed {name}: {curr_price} -> {real_price} (from '{p_str}')")
                                updated += 1
                                matched = True
                                break
                    if not matched and curr_price in (19900.0, 18900.0, 16000.0, 15400.0, 15000.0, 14900.0, 12900.0, 12000.0, 11000.0, 9900.0, 8300.0, 8200.0, 8000.0, 7900.0, 7000.0, 6900.0, 6400.0, 6100.0, 6000.0, 5900.0, 5300.0):
                        # Revert 100x multiplication
                        reverted = round(curr_price / 100.0, 2)
                        await db.execute(text("UPDATE price_results SET price = :p WHERE id = :id"), {"p": reverted, "id": pid})
                        print(f"Reverted {name}: {curr_price} -> {reverted}")
                        updated += 1
            except Exception as e:
                print(f"Error for {name}: {e}")
        await db.commit()
        print(f"Total updated: {updated}")

if __name__ == "__main__":
    asyncio.run(fix())
