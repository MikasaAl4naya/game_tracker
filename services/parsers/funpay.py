import logging
from bs4 import BeautifulSoup

from services.config import NO_PRICE_LIMIT
from services.filters import quick_reject, is_reliable_seller_funpay, matches_game_name
from services.llm import process_candidates_batch
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)


def parse_funpay(game_id: int, url: str, target_price: float = NO_PRICE_LIMIT, game_name: str = "") -> list[dict]:
    session = get_http_session()
    try:
        # Force Russian Rubles (RUB) currency in FunPay session and headers
        session.cookies.set("cy", "rub", domain=".funpay.com")
        resp = session.get(
            url,
            cookies={"cy": "rub"},
            headers={"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"},
            timeout=10,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        lots = soup.find_all(class_="tc-item")
    except Exception as e:
        logger.error("FunPay parse error for %s: %s", url, e)
        return []

    candidates = []
    for lot in lots:
        try:
            is_trusted, is_online = is_reliable_seller_funpay(lot, min_reviews=20)
            if not is_trusted:
                continue

            raw_desc = lot.find("div", class_="tc-desc")
            if not raw_desc:
                continue
            raw_text = raw_desc.text.strip()

            parts = raw_text.split("\n\n", 1)
            platform_tag = parts[0].strip().upper() if len(parts) == 2 else ""
            name = parts[1].strip() if len(parts) == 2 else raw_text

            if platform_tag in ("MOBILE",) or platform_tag.startswith("MOB"):
                continue

            price_div = lot.find("div", class_="tc-price")
            if not price_div or "data-s" not in price_div.attrs:
                continue

            price = round(float(price_div["data-s"]), 2)

            # Currency unit check & conversion safeguard
            price_text = price_div.text.strip().lower()
            if "$" in price_text or "usd" in price_text:
                price = round(price * 92.0, 2)
            elif "€" in price_text or "eur" in price_text:
                price = round(price * 100.0, 2)

            # Anti-glitch sanity check: full commercial games are never sold for < 45 RUB on FunPay
            if price < 45.0:
                continue

            if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
                continue
            if quick_reject(name, platform_tag):
                continue
            if game_name and not matches_game_name(name, game_name, strict=True):
                continue

            candidates.append({
                "name": name,
                "props": platform_tag,
                "price": price,
                "url": lot.get("href", url),
                "is_online": is_online,
            })
        except Exception:
            continue

    processed = process_candidates_batch(candidates)

    best_offers: dict = {}
    for r in processed:
        if not r.get("is_valid"):
            continue
        region, price = r["region"], r["price"]
        platform = r.get("platform", "Steam")
        if not platform or platform == "Unknown":
            platform = "Steam"
        is_online = r.get("is_online", False)

        key = (region, platform)
        current = best_offers.get(key)
        should_replace = False
        if not current:
            should_replace = True
        else:
            current_online = current.get("is_online", False)
            if is_online and not current_online:
                should_replace = True
            elif is_online == current_online and price < current["price"]:
                should_replace = True

        if should_replace:
            label = f"FunPay ({platform})"
            best_offers[key] = {
                "price": price,
                "name": r["name"],
                "url": r["url"],
                "shop_label": label,
                "region": region,
                "platform": platform,
                "is_online": is_online,
            }

    return [
        {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
         "lot_name": o["name"], "lot_url": o["url"], "region": o["region"], "platform": o["platform"]}
        for o in best_offers.values()
    ]
