import json
import logging
from bs4 import BeautifulSoup

from services.config import redis_client
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)

BATTLEPASS_SERVICE_SLUGS = {
    "genshin impact": "genshin",
    "honkai star rail": "honkai",
    "honkai: star rail": "honkai",
    "zenless zone zero": "zzz",
    "wuthering waves": "wuthering_waves",
    "marvel rivals": "marvel_rivals",
    "love and deepspace": "lovedspace",
    "love and deep space": "lovedspace",
    "free fire": "free_fire",
    "pubg mobile": "pubg_m",
    "roblox": "roblox",
    "valorant": "valorant_t",
    "mobile legends": "mobile_legends",
    "mobile legends: bang bang": "mobile_legends",
    "arena breakout": "arena_breakout",
    "arena breakout infinite": "arena_infinite",
    "delta force": "delta_force",
}


def fetch_battlepass_offers(game_name_or_slug: str) -> list[dict]:
    """
    Парсит официальные предложения и цены с витрины BattlePass.ru по Schema.org Product JSON-LD.
    Возвращает список пакетов с актуальными ценами в рублях.
    """
    clean_name = game_name_or_slug.lower().strip()
    bp_slug = BATTLEPASS_SERVICE_SLUGS.get(clean_name, clean_name.replace("-", "_"))

    cache_key = f"battlepass_offers:{bp_slug}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    session = get_http_session()
    url = f"https://battlepass.ru/service/{bp_slug}"

    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        offers = []

        for script in soup.find_all("script", {"type": "application/ld+json"}):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                if data.get("@type") == "Product" and "offers" in data:
                    for off in data["offers"]:
                        name = off.get("name", "").strip()
                        price_str = off.get("price", "0")
                        try:
                            price = float(price_str)
                        except (ValueError, TypeError):
                            price = 0.0

                        if name and price > 0:
                            offers.append({
                                "name": name,
                                "price": price,
                                "currency": off.get("priceCurrency", "RUB"),
                                "url": url,
                                "shop_name": "BattlePass",
                                "delivery_type": "uid",
                                "promo_code": "HLX",
                                "promo_discount": "0% сбор",
                            })
            except Exception:
                continue

        if offers:
            try:
                redis_client.setex(cache_key, 3600, json.dumps(offers))
            except Exception:
                pass

        return offers
    except Exception as e:
        logger.warning("BattlePass fetch error for '%s': %s", bp_slug, e)
        return []
