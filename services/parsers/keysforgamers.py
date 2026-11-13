import json
import logging
from services.config import NO_PRICE_LIMIT, redis_client
from services.filters import (
    check_lot_validity,
    clean_game_name_for_search,
    detect_platform,
    detect_region,
    matches_game_name,
    parse_price,
)
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)


def parse_keysforgamers(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    """
    Парсер маркетплейса Keysforgamers (keysforgamers.com).
    Использует AJAX-эндпоинт поиска, парсит цены в рублях, определяет платформу и регион.
    """
    cache_key = f"price_cache:keysforgamers:{game_name}"
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
                "https://keysforgamers.com/ru/products",
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/plain, */*",
                },
                params={"name": query, "per-page": 20, "ajax": 1},
                timeout=10,
            )
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                items = data.get("products", [])
                if items:
                    products = items
                    break
        except Exception as e:
            logger.warning("Keysforgamers search error for '%s': %s", query, e)

    if not products:
        return []

    best_offers: dict = {}
    for item in products:
        title = item.get("title", "").strip()
        if not title:
            continue

        if not matches_game_name(title, game_name, strict=True):
            continue

        raw_price = item.get("cheap_offer", "")
        price = parse_price(raw_price)
        if price is None or price <= 0:
            continue
        # Гарантированная конвертация валют Keysforgamers
        if ("$" in raw_price or "usd" in raw_price.lower()) and price < 500:
            price = round(price * 100.0, 2)
        elif ("€" in raw_price or "eur" in raw_price.lower()) and price < 500:
            price = round(price * 108.0, 2)
        if price < 50:
            continue

        rel_url = item.get("url", "")
        url_lower = rel_url.lower()
        if any(ign in url_lower for ign in [
            "buy-runes", "buy-currency", "buy-coins", "buy-gold", "buy-items", "buy-boost",
            "buy-konsolnyh-akkauntov", "akkaunt", "account", "arenda"
        ]):
            continue

        if not check_lot_validity(title, "", strict_key_check=False):
            continue

        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        lot_url = f"https://keysforgamers.com{rel_url}" if rel_url.startswith("/") else rel_url

        region = detect_region(title)
        platform = detect_platform(title, shop_name="Keysforgamers")

        key = (region, platform)
        if key not in best_offers or price < best_offers[key]["price"]:
            best_offers[key] = {
                "name": title,
                "price": price,
                "url": lot_url,
                "region": region,
                "platform": platform,
                "shop_label": "Keysforgamers",
            }

    if best_offers:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(best_offers))
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
