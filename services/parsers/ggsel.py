import json
import logging

from services.config import NO_PRICE_LIMIT, redis_client
from services.filters import (
    clean_game_name_for_search,
    is_reliable_seller_ggsel,
    matches_game_name,
    parse_price,
    quick_reject,
)
from services.llm import process_candidates_batch
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)


def get_ggsel_seller_info(seller_id: int, session=None) -> dict:
    """
    Получает и кэширует в Redis (на 3 дня) детальную статистику профиля продавца GGSEL:
    общие продажи, положительные/отрицательные отзывы, рейтинг, дату регистрации.
    """
    cache_key = f"seller_cache:ggsel:{seller_id}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    s = session or get_http_session()
    try:
        resp = s.get(
            f"https://api.ggsel.com/sellers/{seller_id}",
            headers={"Origin": "https://ggsel.net"},
            timeout=2.5,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            stats = data.get("statistics", {})
            info = {
                "seller_id": seller_id,
                "name": data.get("name_seller"),
                "total_sales": stats.get("cnt_sell", 0),
                "good_reviews": stats.get("cnt_good_responses", 0),
                "bad_reviews": stats.get("cnt_bad_responses", 0),
                "rating": float(data.get("rating") or stats.get("rating") or 0.0),
                "registered": data.get("date_registration"),
            }
            try:
                redis_client.setex(cache_key, 86400 * 3, json.dumps(info))
            except Exception:
                pass
            return info
        else:
            try:
                redis_client.setex(cache_key, 3600, json.dumps({"total_sales": 0, "rating": 0.0}))
            except Exception:
                pass
    except Exception as e:
        logger.debug("Failed to fetch GGSEL seller %s stats: %s", seller_id, e)
    return {}


def parse_ggsel(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    cache_key = f"price_cache:ggsel:{game_name}"
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

    payload = {
        "search_term": clean_game_name_for_search(game_name),
        "limit": 60,
        "currency": "wmr",
        "is_russian_ip": 1,
        "lang": "ru",
        "sort": "sortByRec",
        "content_type_ids": [2, 48],
    }
    session = get_http_session()
    try:
        resp = session.post(
            "https://api.ggsel.com/elastic/goods/query",
            json=payload,
            headers={"Origin": "https://ggsel.net"},
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        logger.error("GGSEL search error for '%s': %s", game_name, e)
        return []

    candidates = []
    for item in data.get("data", {}).get("items", []):
        seller_id = item.get("id_seller")
        seller_info = get_ggsel_seller_info(seller_id, session=session) if seller_id else None

        if not is_reliable_seller_ggsel(item, seller_info=seller_info):
            continue

        name = item.get("name", "")
        price = parse_price(item.get("price_wmr"))
        if price is None:
            continue

        if not matches_game_name(name, game_name, strict=True):
            continue
        if quick_reject(name, ""):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        candidates.append({
            "name": name, "props": "", "price": price,
            "url": f"https://ggsel.net/catalog/product/{item.get('id_goods')}",
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
            label = "GGSEL (Gift)" if is_gift else "GGSEL (Key)"
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
            serializable = {f"{k[0]}_{k[1]}": v for k, v in best_offers.items()}
            redis_client.setex(cache_key, 60, json.dumps(serializable))
        except Exception:
            pass

    return [
        {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
         "lot_name": o["name"], "lot_url": o["url"], "region": o["region"], "platform": o["platform"]}
        for o in best_offers.values()
    ]
