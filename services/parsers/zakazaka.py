import json
import logging
import re

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


def parse_zakazaka(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    cache_key = f"price_cache:zakazaka:{game_name}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            best_offers = json.loads(cached)
            return [
                {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
                 "lot_name": o["name"], "lot_url": o["url"], "region": o.get("region", "Unknown"),
                 "platform": o.get("platform", "Steam")}
                for o in best_offers.values()
            ]
    except Exception:
        pass

    session = get_http_session()
    try:
        resp = session.get(
            "https://zaka-zaka.com/search/ajax/",
            headers={"X-Requested-With": "XMLHttpRequest"},
            params={"game": clean_game_name_for_search(game_name)},
            timeout=15,
        )
        if resp.status_code != 200 or not resp.text.strip():
            return []
        data = resp.json()
    except Exception as e:
        logger.error("Zaka-Zaka search error for '%s': %s", game_name, e)
        return []

    best_offers: dict = {}
    for item in data:
        if item.get("type") != "game" or item.get("price") == -2:
            continue

        name = item.get("name", "")
        drm = item.get("drm", "")
        if not matches_game_name(name, game_name, strict=True):
            continue

        price = parse_price(item.get("price"))
        if price is None:
            continue
        if not check_lot_validity(name, drm, strict_key_check=False):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        region = detect_region(name + " " + drm)
        platform = detect_platform(name, drm=drm, shop_name="Zaka-Zaka")
        key = (region, platform)
        if key not in best_offers or price < best_offers[key]["price"]:
            slug = item.get("url", "").lstrip("/")
            if not slug.startswith("game/"):
                slug = f"game/{slug}"
            best_offers[key] = {
                "price": price,
                "name": name,
                "url": f"https://zaka-zaka.com/{slug}",
                "shop_label": "Zaka-Zaka",
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
        {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
         "lot_name": o["name"], "lot_url": o["url"], "region": o["region"], "platform": o["platform"]}
        for o in best_offers.values()
    ]
