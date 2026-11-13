import json
import logging
import re
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


def parse_steampay(game_id: int, game_name: str, target_price: float = NO_PRICE_LIMIT) -> list[dict]:
    cache_key = f"price_cache:steampay:{game_name}"
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
            "https://steampay.com/search",
            params={"q": clean_game_name_for_search(game_name)},
            timeout=10,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error("Steampay search error for '%s': %s", game_name, e)
        return []

    candidates = []
    for item in soup.find_all("a", class_="catalog-item"):
        # Только Steam-ключи (специализация магазина Steampay)
        activation_div = item.find("div", class_="catalog-item__activation")
        if activation_div:
            platform_img = activation_div.find("img")
            if platform_img and platform_img.get("alt", "").upper() != "STEAM":
                continue

        name_div = item.find("div", class_="catalog-item__name")
        if not name_div or not name_div.contents:
            continue
        name = name_div.contents[0].strip()

        price_span = item.find("span", class_="catalog-item__price-span")
        if not price_span:
            continue
        price = parse_price(price_span.text)
        if price is None:
            continue

        if not matches_game_name(name, game_name, strict=True):
            continue
        if quick_reject(name, ""):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        candidates.append({"name": name, "price": price, "href": item.get("href", ""), "platform": "Steam"})

    best_offers: dict = {}
    for cand in candidates:
        product_url = f"https://steampay.com{cand['href']}"
        region = "Unknown"
        try:
            prod_resp = session.get(product_url, timeout=10)
            prod_soup = BeautifulSoup(prod_resp.text, "html.parser")
            for key_div in prod_soup.find_all("div", class_="product__info-key"):
                if "регион" in key_div.text.lower():
                    val_div = key_div.find_next_sibling("div", class_="product__info-value")
                    if val_div:
                        region = detect_region(val_div.text)
                    break
        except Exception:
            pass

        platform = cand.get("platform", "Steam")
        key = (region, platform)
        if key not in best_offers or cand["price"] < best_offers[key]["price"]:
            best_offers[key] = {
                "price": cand["price"],
                "name": cand["name"],
                "url": product_url,
                "shop_label": "Steampay",
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
