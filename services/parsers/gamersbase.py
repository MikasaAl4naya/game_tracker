import json
import logging

from services.config import NO_PRICE_LIMIT, redis_client
from services.filters import (
    clean_game_name_for_search,
    detect_platform,
    detect_region,
    matches_game_name,
    parse_price,
    quick_reject,
)
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)


def parse_gamersbase(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    """
    Парсер магазина цифровых ключей GamersBase / Gama-Gama (gamersbase.store).
    Использует официальный поисковый JSON API каталога.
    """
    cache_key = f"price_cache:gamersbase:{game_name}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            best_offers = json.loads(cached)
            return [
                {
                    "game_id": game_id,
                    "shop_name": o["shop_label"],
                    "price": o["price"],
                    "lot_name": o["name"],
                    "lot_url": o["url"],
                    "region": o.get("region", "Unknown"),
                    "platform": o.get("platform", "Steam"),
                }
                for o in best_offers.values()
            ]
    except Exception:
        pass

    session = get_http_session()

    search_queries = [game_name]
    cleaned = clean_game_name_for_search(game_name)
    if cleaned and cleaned != game_name:
        search_queries.append(cleaned)

    products = []
    for query in search_queries:
        try:
            resp = session.get(
                "https://gamersbase.store/api/catalogs/search/",
                params={
                    "searchQuery": query,
                    "isFullTextSearch": "false",
                    "language": "RU",
                },
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=10,
            )
            if resp.status_code != 200 or not resp.text.strip():
                continue

            data = resp.json()
            found = data.get("products", [])
            if found:
                products = found
                break
        except Exception as e:
            logger.error("GamersBase search error for query '%s': %s", query, e)

    if not products:
        return []

    candidates = []
    for p in products:
        # Пропускаем дополнения (DLC), если пользователь ищет основную игру
        prod_type = str(p.get("type", "")).lower()
        if prod_type == "dlc" and "dlc" not in game_name.lower():
            continue

        name = p.get("name", "").strip()
        if not name:
            continue

        if not matches_game_name(name, game_name, strict=True):
            continue
        if quick_reject(name, ""):
            continue

        price_str = str(p.get("actual_price_formatted") or p.get("standard_price_formatted") or "")
        price = parse_price(price_str)
        if price is None or price <= 0:
            continue
        # Гарантированная конвертация валют GamersBase ($ USD и € EUR в рубли)
        if ("$" in price_str or "usd" in price_str.lower()) and price < 500:
            price = round(price * 100.0, 2)
        elif ("€" in price_str or "eur" in price_str.lower()) and price < 500:
            price = round(price * 108.0, 2)
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        seo_code = p.get("seo_code", "")
        product_url = f"https://gamersbase.store/game/{seo_code}" if seo_code else "https://gamersbase.store"

        candidates.append({
            "name": name,
            "price": price,
            "url": product_url,
        })

    best_offers: dict = {}
    for cand in candidates:
        name = cand["name"]

        region = detect_region(name)
        if region == "Unknown":
            region = "RU"

        platform = detect_platform(name, drm="")
        if not platform or platform == "Unknown":
            platform = "Steam"

        key = (region, platform)
        if key not in best_offers or cand["price"] < best_offers[key]["price"]:
            best_offers[key] = {
                "price": cand["price"],
                "name": name,
                "url": cand["url"],
                "shop_label": "GamersBase",
                "region": region,
                "platform": platform,
            }

    if best_offers:
        try:
            serializable = {f"{k[0]}_{k[1]}": v for k, v in best_offers.items()}
            redis_client.setex(cache_key, 60, json.dumps(serializable))
        except Exception:
            pass

    return [
        {
            "game_id": game_id,
            "shop_name": o["shop_label"],
            "price": o["price"],
            "lot_name": o["name"],
            "lot_url": o["url"],
            "region": o["region"],
            "platform": o["platform"],
        }
        for o in best_offers.values()
    ]
