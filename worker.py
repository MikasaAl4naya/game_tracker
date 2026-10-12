import hashlib
import json
import logging
import os
import re

import requests
import redis
from bs4 import BeautifulSoup
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from sqlalchemy import delete, select

from database import SyncSessionLocal
from models import GameCatalog, PriceResult, UserTask

load_dotenv()

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# ---------- КОНСТАНТЫ ----------

NO_PRICE_LIMIT: float = 99_999.0

_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
_RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//")
_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")

# Ключевые слова железячных промо — используются в двух фильтрах
_HARDWARE_KEYWORDS = (
    "nvidia", "rtx", "гпу", "gpu", "видеокарт", "radeon", "rx ", "amd ", "intel ",
)

redis_client = redis.Redis.from_url(f"{_REDIS_URL}/1", decode_responses=True)

celery_app = Celery(
    "tracker_worker",
    broker=_RABBITMQ_URL,
    backend=f"{_REDIS_URL}/0",
)


# ---------- БИЗНЕС-ЛОГИКА ----------

def check_lot_validity(name: str, props: str, strict_key_check: bool = True) -> bool:
    """Классический фильтр на регулярках (запасной вариант при недоступности LLM)."""
    name_lower = name.lower()
    text_to_check = (name + " " + props).lower()

    if any(kw in name_lower for kw in _HARDWARE_KEYWORDS):
        return False

    aggressive = (
        "аккаунт", "account", "оффлайн", "офлайн", "offline", "shared",
        "аренда", "дополнен", "улучшен", "season pass", "expansion", "dlc",
        "ps4", "ps5", "xbox", "pack", "voice", "soundtrack", "artbook",
        "points", "coins", "credits", "skin", "набор", "denuvo",
    )
    if any(kw in name_lower for kw in aggressive):
        return False

    if re.search(r"\b(guard|вход)\b", name_lower):
        return False

    desc_stop = (
        "общий аккаунт", "выданными данными", "смена пароля", "без смены данных",
        "запустите игру один раз", "логин:пароль", "смена аккаунтов",
        "переключить клиент steam",
    )
    if any(phrase in text_to_check for phrase in desc_stop):
        return False

    if strict_key_check:
        if not any(w in text_to_check for w in ("цифровой ключ", "key", "ключ", "гифт", "gift", "подарок")):
            return False

    return True


def quick_reject(name: str, props: str) -> bool:
    """Быстрый отсев очевидного мусора перед отправкой в LLM."""
    text = (name + " " + props).lower()

    if any(kw in text for kw in _HARDWARE_KEYWORDS):
        return True

    account_phrases = (
        "аккаунт", "account", "оффлайн", "офлайн", "offline", "shared",
        "аренда", "прокат", "rent", "логин", "пароль", "login", "password",
        "смена данных", "смена пароля", "доступ", "вход", "guard", "steam guard",
        "общий аккаунт", "общий доступ", "family", "совместный", "складчина",
        "без смены данных", "без смены пароля", "без гарантии", "один раз",
        "qr", "куар", "кьюар",
    )
    if any(phrase in text for phrase in account_phrases):
        return True

    services = (
        "буст", "boost", "прокачка", "leveling", "помощь", "услуг",
        "прохождение", "тренировка", "coaching", "ранг", "mmr",
    )
    if any(kw in text for kw in services):
        return True

    if any(kw in text for kw in ("кряк", "таблетка", "эмулятор", "эмул", "пиратка")):
        return True

    if re.search(r"ключ.*аккаунт|аккаунт.*ключ", text):
        return True

    return False


# ---------- ПАКЕТНАЯ ОБРАБОТКА LLM ----------

_LLM_SYSTEM_PROMPT = """Ты — классификатор товаров игрового маркетплейса.
На вход ты получишь JSON-массив объектов. Твоя задача проанализировать КАЖДЫЙ лот и вернуть JSON-МАССИВ ответов.

Правила валидности (is_valid):
- true: цифровой ключ (key), гифт (gift), код.
- false: аккаунт, аренда, услуги, буст, оффлайн, смена данных, DLC, скины.

Формат ответа — СТРОГО JSON-массив:
[
  {"id": 0, "is_valid": true, "platform": "Steam", "region": "RU"},
  {"id": 1, "is_valid": false, "platform": "Unknown", "region": "Unknown"}
]
"""


def _llm_fallback(item: dict) -> dict:
    """Применяет regex-фильтр как замену LLM для одного лота."""
    item["is_valid"] = check_lot_validity(item["name"], item.get("props", ""))
    item["platform"] = "Unknown"
    item["region"] = detect_region(item["name"] + " " + item.get("props", ""))
    return item


def process_candidates_batch(candidates: list[dict]) -> list[dict]:
    """Проверяет кэш Redis; некэшированные лоты отправляет пачками по 10 в LLM."""
    results: list[dict] = []
    to_check_llm: list[dict] = []

    for cand in candidates:
        cache_key = "llm_cache:" + hashlib.md5(
            (cand["name"] + " " + cand.get("props", "")).encode()
        ).hexdigest()
        cached = redis_client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                cand["is_valid"] = data["is_valid"]
                cand["platform"] = data["platform"]
                cand["region"] = data["region"]
                results.append(cand)
                continue
            except (KeyError, json.JSONDecodeError):
                pass
        cand["_cache_key"] = cache_key
        to_check_llm.append(cand)

    batch_size = 10
    for i in range(0, len(to_check_llm), batch_size):
        batch = to_check_llm[i : i + batch_size]
        prompt_data = [{"id": j, "name": b["name"], "props": b.get("props", "")} for j, b in enumerate(batch)]

        payload = {
            "model": "llama3.2:3b",
            "prompt": f"{_LLM_SYSTEM_PROMPT}\n\nВход:\n{json.dumps(prompt_data, ensure_ascii=False)}",
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            resp = requests.post(f"{_OLLAMA_URL}/api/generate", json=payload, timeout=60)
            resp.raise_for_status()
            llm_results = json.loads(
                re.sub(r"```json|```", "", resp.json().get("response", "")).strip()
            )

            processed_ids: set[int] = set()
            for res in llm_results:
                idx = res.get("id")
                if idx is None or not (0 <= idx < len(batch)):
                    continue
                b = batch[idx]
                b["is_valid"] = res.get("is_valid", False)
                b["platform"] = res.get("platform", "Unknown")
                b["region"] = res.get("region", "Unknown")
                redis_client.setex(
                    b["_cache_key"],
                    2_592_000,  # 30 дней
                    json.dumps({"is_valid": b["is_valid"], "platform": b["platform"], "region": b["region"]}),
                )
                results.append(b)
                processed_ids.add(idx)
                icon = "✅" if b["is_valid"] else "❌"
                logger.debug("%s ИИ [%s|%s]: %s", icon, b["region"], b["platform"], b["name"])

            # Fallback для лотов, которые LLM пропустил в ответе
            for j, b in enumerate(batch):
                if j not in processed_ids:
                    results.append(_llm_fallback(b))

        except Exception as e:
            logger.warning("Ошибка LLM (батч %d): %s — переключаюсь на regex", i // batch_size + 1, e)
            for b in batch:
                results.append(_llm_fallback(b))

    return results


# ---------- УТИЛИТЫ ----------

def clean_game_name_for_search(name: str) -> str:
    """Очищает название игры от мусора, годов в скобках и сбитой кодировки."""
    clean = name.replace("тАЩ", "'").replace("тАФ", " ").replace("тАУ", " ")
    clean = re.sub(r"\(.*?\)|\[.*?\]", "", clean)
    clean = re.sub(r"[™®©]", "", clean)
    clean = clean.replace(":", " ").replace("-", " ").replace(",", " ")
    clean = clean.replace("’", "'").replace("`", "'").replace("‘", "'")
    return " ".join(clean.split()).strip()


def matches_game_name(lot_name: str, db_game_name: str) -> bool:
    """
    Умный матчинг: прощает отсутствие маркетинговых слов ("The", "Edition",
    "Remastered"), но строго требует ключевые слова и цифры номера части.
    """
    stop_words = {
        "the", "of", "and", "edition", "game", "year", "goty",
        "remastered", "director's", "cut", "special", "definitive", "hd", "collection",
    }

    clean_query = clean_game_name_for_search(db_game_name).lower()
    clean_name = clean_game_name_for_search(lot_name).lower()

    query_words = set(clean_query.split()) - stop_words
    name_words = set(clean_name.split())

    if not query_words:
        query_words = set(clean_query.split())

    if len(query_words) == 1:
        return list(query_words)[0] in clean_name

    return query_words.issubset(name_words)


def detect_region(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(global|region free|весь мир|глобал|row|any)\b", t):
        return "Global"
    if re.search(r"\b(ru|рф|россия|russia)\b", t):
        return "RU"
    if re.search(r"\b(cis|снг)\b", t):
        return "CIS"
    if re.search(r"\b(tr|турция|turkey)\b", t):
        return "TR"
    if re.search(r"\b(kz|казахстан|kazakhstan)\b", t):
        return "KZ"
    if re.search(r"\b(ar|аргентина|argentina)\b", t):
        return "AR"
    return "Unknown"


# ---------- БД ПОМОЩНИКИ ----------

def save_prices(prices_list: list[dict]) -> None:
    """
    Сохраняет лучшие предложения, заменяя устаревшие записи для той же
    комбинации (game_id, shop_name, region).
    """
    if not prices_list:
        return
    db = SyncSessionLocal()
    try:
        for p in prices_list:
            db.execute(
                delete(PriceResult).where(
                    PriceResult.game_id == p["game_id"],
                    PriceResult.shop_name == p["shop_name"],
                    PriceResult.region == p["region"],
                )
            )
        db.add_all([PriceResult(**p) for p in prices_list])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_catalog_to_db(games_list: list[dict]) -> int:
    db = SyncSessionLocal()
    try:
        added_count = 0
        for game in games_list:
            exists = db.execute(
                select(GameCatalog).where(GameCatalog.name == game["name"])
            ).scalars().first()
            if not exists:
                db.add(GameCatalog(name=game["name"], url_funpay=game.get("url", "")))
                added_count += 1
        db.commit()
        return added_count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------- ПАРСЕРЫ ----------

@celery_app.task
def parse_funpay_task(game_id: int, url: str, target_price: float, chat_id: int):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        soup = BeautifulSoup(
            requests.get(url, headers=headers, timeout=10).text, "html.parser"
        )
        lots = soup.find_all(class_="tc-item")
    except Exception as e:
        logger.error("FunPay parse error for %s: %s", url, e)
        return

    candidates = []
    for lot in lots:
        try:
            name = lot.find("div", class_="tc-desc").text.strip()
            props_div = lot.find("div", class_="tc-props")
            props = props_div.text.strip() if props_div else ""
            price_div = lot.find("div", class_="tc-price")
            if not price_div or "data-s" not in price_div.attrs:
                continue

            price = round(float(price_div["data-s"]), 2)
            if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
                continue
            if quick_reject(name, props):
                continue

            candidates.append({"name": name, "props": props, "price": price, "url": lot.get("href", url)})
        except Exception:
            continue

    processed = process_candidates_batch(candidates)

    best_offers: dict = {}
    for r in processed:
        if not r.get("is_valid"):
            continue
        region, price = r["region"], r["price"]
        if region not in best_offers or price < best_offers[region]["price"]:
            label = f"FunPay ({r['platform']})" if r["platform"] != "Unknown" else "FunPay"
            best_offers[region] = {"price": price, "name": r["name"], "url": r["url"], "shop_label": label}

    save_prices([
        {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
         "lot_name": o["name"], "lot_url": o["url"], "region": region}
        for region, o in best_offers.items()
    ])


@celery_app.task
def parse_plati_task(game_id: int, game_name: str, target_price: float, chat_id: int):
    cache_key = f"price_cache:plati:{game_name}"
    if redis_client.get(cache_key):
        return

    search_name = clean_game_name_for_search(game_name)
    try:
        data = requests.get(
            "https://plati.market/api/search.ashx",
            params={"query": search_name, "response": "json"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        ).json()
    except Exception as e:
        logger.error("Plati search error for '%s': %s", game_name, e)
        return

    candidates = []
    for item in data.get("items", []):
        name = item.get("name", "")
        price = float(item.get("price_rur", 0))
        desc = item.get("description", "")
        item_id = item.get("id")

        if not matches_game_name(name, game_name):
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
        if region not in best_offers or price < best_offers[region]["price"]:
            label = "Plati (Gift)" if any(w in r["name"].lower() for w in ("гифт", "gift")) else "Plati (Key)"
            best_offers[region] = {"price": price, "name": r["name"], "url": r["url"], "shop_label": label}

    if best_offers:
        redis_client.setex(cache_key, 60, json.dumps(best_offers))
        save_prices([
            {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
             "lot_name": o["name"], "lot_url": o["url"], "region": region}
            for region, o in best_offers.items()
        ])


@celery_app.task
def parse_steambuy_task(game_id: int, game_name: str, target_price: float, chat_id: int):
    cache_key = f"price_cache:steambuy:{game_name}"
    if redis_client.get(cache_key):
        return

    try:
        resp = requests.get(
            "https://steambuy.com/ajax/_get.php",
            params={"a": "search", "q": clean_game_name_for_search(game_name)},
            headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"},
            timeout=10,
        )
        soup = BeautifulSoup(resp.json()["html"], "html.parser")
    except Exception as e:
        logger.error("Steambuy search error for '%s': %s", game_name, e)
        return

    best_offers: dict = {}
    for item in soup.find_all("a", class_="search-result__link"):
        t_elem = item.find("div", class_="search-result__title")
        p_elem = item.find("div", class_="search-result__cost")
        if not t_elem or not p_elem:
            continue

        name = t_elem.text.strip()
        price_text = re.sub(r"[^\d.]", "", p_elem.text.replace(",", "."))
        if not price_text or not matches_game_name(name, game_name):
            continue

        price = float(price_text)
        if not check_lot_validity(name, "", strict_key_check=False):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        region = detect_region(name)
        if region not in best_offers or price < best_offers[region]["price"]:
            best_offers[region] = {
                "price": price, "name": name,
                "url": "https://steambuy.com" + item.get("href", ""),
                "shop_label": "Steambuy",
            }

    if best_offers:
        redis_client.setex(cache_key, 60, json.dumps(best_offers))
        save_prices([
            {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
             "lot_name": o["name"], "lot_url": o["url"], "region": region}
            for region, o in best_offers.items()
        ])


@celery_app.task
def parse_zakazaka_task(game_id: int, game_name: str, target_price: float, chat_id: int):
    cache_key = f"price_cache:zakazaka:{game_name}"
    if redis_client.get(cache_key):
        return

    try:
        resp = requests.get(
            "https://zaka-zaka.com/search/ajax/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "X-Requested-With": "XMLHttpRequest",
            },
            params={"game": clean_game_name_for_search(game_name)},
            timeout=15,
        )
        if resp.status_code != 200 or not resp.text.strip():
            return
        data = resp.json()
    except Exception as e:
        logger.error("Zaka-Zaka search error for '%s': %s", game_name, e)
        return

    best_offers: dict = {}
    for item in data:
        if item.get("type") != "game" or item.get("price") == -2:
            continue

        name = item.get("name", "")
        drm = item.get("drm", "")
        if not matches_game_name(name, game_name):
            continue

        price_match = re.search(r"(\d+(?:[.,]\d+)?)", re.sub(r"<[^>]+>", "", str(item.get("price", ""))))
        if not price_match:
            continue

        price = float(price_match.group(1).replace(",", "."))
        if not check_lot_validity(name, drm, strict_key_check=False):
            continue
        if target_price != NO_PRICE_LIMIT and price < target_price * 0.1:
            continue

        region = detect_region(name + " " + drm)
        if region not in best_offers or price < best_offers[region]["price"]:
            best_offers[region] = {
                "price": price, "name": name,
                "url": "https://zaka-zaka.com" + item.get("url", ""),
                "shop_label": "Zaka-Zaka",
            }

    if best_offers:
        redis_client.setex(cache_key, 60, json.dumps(best_offers))
        save_prices([
            {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
             "lot_name": o["name"], "lot_url": o["url"], "region": region}
            for region, o in best_offers.items()
        ])


@celery_app.task
def parse_ggsel_task(game_id: int, game_name: str, target_price: float, chat_id: int):
    cache_key = f"price_cache:ggsel:{game_name}"
    if redis_client.get(cache_key):
        return

    payload = {
        "search_term": clean_game_name_for_search(game_name),
        "limit": 60,
        "currency": "wmr",
        "is_russian_ip": 1,
        "lang": "ru",
        "sort": "sortByRec",
        "platforms": ["Steam"],
        "content_type_ids": [2, 48],
    }
    try:
        data = requests.post(
            "https://api-yellow.ggsel.com/elastic/goods/query",
            json=payload,
            headers={"User-Agent": "Mozilla/5.0", "Origin": "https://ggsel.net"},
            timeout=15,
        ).json()
    except Exception as e:
        logger.error("GGSEL search error for '%s': %s", game_name, e)
        return

    candidates = []
    for item in data.get("data", {}).get("items", []):
        name = item.get("name", "")
        try:
            price = float(item.get("price_wmr", "0"))
        except (ValueError, TypeError):
            continue

        if not matches_game_name(name, game_name):
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
        if region not in best_offers or price < best_offers[region]["price"]:
            label = "GGSEL (Gift)" if any(w in r["name"].lower() for w in ("гифт", "gift")) else "GGSEL (Key)"
            best_offers[region] = {"price": price, "name": r["name"], "url": r["url"], "shop_label": label}

    if best_offers:
        redis_client.setex(cache_key, 60, json.dumps(best_offers))
        save_prices([
            {"game_id": game_id, "shop_name": o["shop_label"], "price": o["price"],
             "lot_name": o["name"], "lot_url": o["url"], "region": region}
            for region, o in best_offers.items()
        ])


# ---------- ПЛАНОВЫЕ ЗАДАЧИ ----------

@celery_app.task
def sync_top_steam_games():
    games_data = []
    try:
        for page in range(2):
            response = requests.get(
                f"https://steamspy.com/api.php?request=all&page={page}", timeout=20
            )
            data = response.json()
            for appid, info in data.items():
                if info.get("name") and str(info.get("price", "0")) != "0":
                    games_data.append({"name": info["name"], "url": ""})
        added = save_catalog_to_db(games_data)
        logger.info("Steam sync: добавлено %d игр", added)
    except Exception as e:
        logger.error("Steam sync error: %s", e)


@celery_app.task
def trigger_all_price_checks():
    db = SyncSessionLocal()
    try:
        tracked_game_ids = db.execute(select(UserTask.game_id).distinct()).scalars().all()
        if not tracked_game_ids:
            return

        games = db.execute(
            select(GameCatalog).where(GameCatalog.id.in_(tracked_game_ids))
        ).scalars().all()

        for game in games:
            parse_plati_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steambuy_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_ggsel_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_zakazaka_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            if game.url_funpay:
                parse_funpay_task.delay(game.id, game.url_funpay, NO_PRICE_LIMIT, 0)
    finally:
        db.close()


@celery_app.task
def fill_missing_prices():
    """Запускает парсинг только для игр, у которых ещё нет ни одной цены."""
    db = SyncSessionLocal()
    try:
        games_with_prices = select(PriceResult.game_id).distinct()
        empty_games = db.execute(
            select(GameCatalog).where(GameCatalog.id.not_in(games_with_prices))
        ).scalars().all()

        if not empty_games:
            logger.info("Все игры уже имеют цены — дозаполнение не требуется")
            return

        logger.info("Найдено %d игр без цен — запускаем парсинг", len(empty_games))
        for game in empty_games:
            parse_plati_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steambuy_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_ggsel_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_zakazaka_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            if game.url_funpay:
                parse_funpay_task.delay(game.id, game.url_funpay, NO_PRICE_LIMIT, 0)
    except Exception as e:
        logger.error("Ошибка при дозаполнении: %s", e)
    finally:
        db.close()


@celery_app.task
def sync_funpay_catalog():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        soup = BeautifulSoup(
            requests.get("https://funpay.com/", headers=headers, timeout=15).text,
            "html.parser",
        )
    except Exception as e:
        logger.error("FunPay catalog sync error: %s", e)
        return

    funpay_keys_map: dict[str, str] = {}
    for item in soup.find_all("div", class_="promo-game-item"):
        title_tag = item.find("div", class_="game-title")
        if not title_tag:
            continue
        target_url = next(
            (a.get("href") for a in item.find_all("a") if "ключ" in a.text.lower()),
            title_tag.a.get("href") if title_tag.a else None,
        )
        if title_tag.text.strip() and target_url:
            funpay_keys_map[clean_game_name_for_search(title_tag.text.strip()).lower()] = target_url

    db = SyncSessionLocal()
    updated_count = 0
    try:
        for game in db.execute(select(GameCatalog)).scalars().all():
            clean_db_name = clean_game_name_for_search(game.name).lower()
            matched_url = funpay_keys_map.get(clean_db_name) or next(
                (
                    fp_url for fp_name, fp_url in funpay_keys_map.items()
                    if matches_game_name(game.name, fp_name) or matches_game_name(fp_name, game.name)
                ),
                None,
            )
            if matched_url and game.url_funpay != matched_url:
                game.url_funpay = matched_url
                updated_count += 1
        db.commit()
        logger.info("FunPay sync завершён: обновлено %d ссылок", updated_count)
    finally:
        db.close()


# ---------- РАСПИСАНИЕ ----------

celery_app.conf.beat_schedule = {
    "check-prices-every-12-hours": {
        "task": "worker.trigger_all_price_checks",
        "schedule": 43_200.0,
    },
    "update-steam-top-every-night": {
        "task": "worker.sync_top_steam_games",
        "schedule": crontab(hour=3, minute=0),
    },
}
celery_app.conf.timezone = "Europe/Moscow"
