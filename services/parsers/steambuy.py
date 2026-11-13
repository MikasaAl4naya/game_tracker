import json
import logging
import re
from bs4 import BeautifulSoup

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


def parse_steambuy(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    cache_key = f"price_cache:steambuy:{game_name}"
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
            "https://steambuy.com/sb/api/catalog/live",
            params={"a": "search", "q": clean_game_name_for_search(game_name)},
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=10,
        )
        soup = BeautifulSoup(resp.json().get("html", ""), "html.parser")
    except Exception as e:
        logger.error("Steambuy search error for '%s': %s", game_name, e)
        return []

    best_offers: dict = {}
    for item in soup.find_all("a", class_="search-result__link"):
        t_elem = item.find("div", class_="search-result__title")
        p_elem = item.find("div", class_="search-result__cost")
        if not t_elem or not p_elem:
            continue

        name = t_elem.text.strip()
        price = parse_price(p_elem.text)
        if price is None or not matches_game_name(name, game_name, strict=True):
            continue
        if not check_lot_validity(name, "", strict_key_check=False):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        region = detect_region(name)
        platform = detect_platform(name, shop_name="Steambuy")
        key = (region, platform)
        if key not in best_offers or price < best_offers[key]["price"]:
            best_offers[key] = {
                "price": price,
                "name": name,
                "url": "https://steambuy.com" + item.get("href", ""),
                "shop_label": "Steambuy",
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
