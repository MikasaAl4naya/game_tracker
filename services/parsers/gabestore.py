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


def parse_gabestore(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    """
    Парсер магазина GabeStore (gabestore.ru).
    Ищет предложения по игре, проверяет наличие, парсит цену и определяет регион.
    """
    cache_key = f"price_cache:gabestore:{game_name}"
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

    items = []
    for query in search_queries:
        try:
            resp = session.get(
                "https://gabestore.ru/result",
                params={"ProductFilter[search]": query},
                timeout=10,
            )
            if resp.status_code != 200 or not resp.text.strip():
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            found_items = soup.select(".shop-item")
            if found_items:
                items = found_items
                break
        except Exception as e:
            logger.error("GabeStore search error for query '%s': %s", query, e)

    if not items:
        return []

    candidates = []
    for item in items:
        # Пропускаем дополнения (DLC), если пользователь ищет основную игру
        label_el = item.select_one(".shop-item__label")
        if label_el and "dlc" in label_el.get_text(strip=True).lower() and "dlc" not in game_name.lower():
            continue

        name_el = item.select_one(".shop-item__name")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)

        if not matches_game_name(name, game_name, strict=True):
            continue
        if quick_reject(name, ""):
            continue

        btn = item.select_one(".btn")
        btn_class = btn.get("class", []) if btn else []
        btn_text = btn.get_text(strip=True) if btn else ""
        if "btn--empty-item" in btn_class or "отсутствует" in btn_text.lower():
            continue

        price_el = item.select_one(".shop-item__price-current")
        if not price_el:
            continue
        price = parse_price(price_el.get_text())
        if price is None or price <= 0:
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        link = name_el.get("href", "")
        product_url = f"https://gabestore.ru{link}" if link.startswith("/") else link

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
            try:
                prod_resp = session.get(cand["url"], timeout=5)
                if prod_resp.status_code == 200:
                    prod_soup = BeautifulSoup(prod_resp.text, "html.parser")
                    for subitem in prod_soup.select(".b-card__subinfo-item"):
                        head = subitem.select_one(".b-card__subinfo-head")
                        body = subitem.select_one(".b-card__subinfo-body")
                        if head and body and "регион" in head.get_text(strip=True).lower():
                            detected = detect_region(body.get_text(strip=True))
                            if detected != "Unknown":
                                region = detected
                            break
            except Exception:
                pass

        if region == "Unknown":
            region = "RU"

        platform = detect_platform(name, shop_name="GabeStore")
        key = (region, platform)
        if key not in best_offers or cand["price"] < best_offers[key]["price"]:
            best_offers[key] = {
                "price": cand["price"],
                "name": cand["name"],
                "url": cand["url"],
                "shop_label": "GabeStore",
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
