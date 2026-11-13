import json
import logging

from services.config import NO_PRICE_LIMIT, redis_client
from services.filters import (
    clean_game_name_for_search,
    is_reliable_seller_plati,
    matches_game_name,
    parse_price,
    quick_reject,
)
from services.llm import process_candidates_batch
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)


def parse_plati(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    cache_key = f"price_cache:plati:{game_name}"
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

    search_name = clean_game_name_for_search(game_name)
    session = get_http_session()
    try:
        resp = session.get(
            "https://plati.market/api/search.ashx",
            params={"query": search_name, "response": "json"},
            timeout=3.5,
        )
        data = resp.json()
    except Exception as e:
        logger.warning("Plati search skipped for '%s' (unresponsive/blocked): %s", game_name, e)
        return []

    candidates = []
    for item in data.get("items", []):
        if not is_reliable_seller_plati(item, min_sales=25, min_positive_ratio=0.95):
            continue

        name = item.get("name", "")
        price = parse_price(item.get("price_rur"))
        if price is None:
            continue
        desc = item.get("description", "")
        item_id = item.get("id")

        if not matches_game_name(name, game_name, strict=True):
            continue
        if quick_reject(name, desc):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        candidates.append({
            "name": name, "props": desc, "price": price,
            "url": f"https://plati.market/itm/{item_id}",
        })

    processed = process_candidates_batch(candidates)

    best_offers: dict = {}
    for r in processed:
        if not r.get("is_valid"):
            continue
        region, price = r["region"], r["price"]
        platform = r.get("platform", "Steam")
        if not platform or platform == "Unknown":
            platform = "Steam"

        key = (region, platform)
        if key not in best_offers or price < best_offers[key]["price"]:
            is_gift = any(w in r["name"].lower() for w in ("гифт", "gift"))
            label = "Plati (Gift)" if is_gift else "Plati (Key)"
            best_offers[key] = {
                "price": price,
                "name": r["name"],
                "url": r["url"],
                "shop_label": label,
                "region": region,
                "platform": platform,
            }

    if best_offers:
        try:
            # Преобразуем строковые ключи для сохранения в JSON Redis
            serializable = {f"{k[0]}_{k[1]}": v for k, v in best_offers.items()}
            redis_client.setex(cache_key, 60, json.dumps(serializable))
        except Exception:
            pass

    return [
        {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
         "lot_name": o["name"], "lot_url": o["url"], "region": o["region"], "platform": o["platform"]}
        for o in best_offers.values()
    ]
