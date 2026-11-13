import json
import logging
from bs4 import BeautifulSoup

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


def parse_gamerilla(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    """
    Парсер магазина цифровых ключей Gamerilla (gamerilla.ru).
    Использует серверный Turbo-Frame эндпоинт для каталога ПК-игр.
    """
    cache_key = f"price_cache:gamerilla:{game_name}"
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
    headers = {
        "Turbo-Frame": "catalog-list-frame",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    }

    search_queries = [game_name]
    cleaned = clean_game_name_for_search(game_name)
    if cleaned and cleaned != game_name:
        search_queries.append(cleaned)

    products = []
    for query in search_queries:
        try:
            resp = session.get(
                "https://gamerilla.ru/catalog/category-pc_games",
                params={"search": query},
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200 or not resp.text.strip():
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            found = soup.select("a.product")
            if found:
                products = found
                break
        except Exception as e:
            logger.error("Gamerilla search error for '%s': %s", query, e)

    if not products:
        return []

    candidates = []
    for a in products:
        title_el = a.select_one(".product__title")
        price_el = a.select_one(".product__price")
        info_el = a.select_one(".product__info")
        if not title_el or not price_el:
            continue

        name = title_el.get_text(strip=True)
        info = info_el.get_text(strip=True) if info_el else ""

        # Пропускаем DLC / наборы костюмов, если ищем основную игру
        lower_name = name.lower()
        is_dlc = any(k in lower_name for k in ("dlc", "costume pack", "jigsaw pack", "soundtrack", "season pass"))
        if is_dlc and "dlc" not in game_name.lower() and "season pass" not in game_name.lower():
            continue

        if not matches_game_name(name, game_name, strict=True):
            continue
        if quick_reject(name, info):
            continue

        # Проверка цены из мета-тега или текста
        meta_price = price_el.select_one("meta[itemprop='price']")
        price = parse_price(meta_price.get("content")) if meta_price else parse_price(price_el.get_text())
        if price is None or price <= 0:
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        href = a.get("href", "")
        product_url = f"https://gamerilla.ru{href}" if href.startswith("/") else href

        candidates.append({
            "name": name,
            "info": info,
            "price": price,
            "url": product_url,
        })

    best_offers: dict = {}
    for cand in candidates:
        name = cand["name"]
        info = cand["info"]

        region = detect_region(f"{info} {name}")
        if region == "Unknown":
            region = "RU"

        platform = detect_platform(name, drm=info)
        if not platform or platform == "Unknown":
            platform = "Steam"

        key = (region, platform)
        if key not in best_offers or cand["price"] < best_offers[key]["price"]:
            best_offers[key] = {
                "price": cand["price"],
                "name": name,
                "url": cand["url"],
                "shop_label": "Gamerilla",
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
