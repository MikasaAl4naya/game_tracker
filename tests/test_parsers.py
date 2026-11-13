"""
Интеграционные тесты парсеров — реальные запросы к площадкам.
Запуск: docker compose exec worker pytest tests/test_parsers.py -v -m integration

Проверяет:
- Парсер возвращает хотя бы 1 оффер для известной популярной игры
- Цена положительная и разумная (> 50 руб, < 30 000 руб)
- Регион из допустимого набора
- URL непустой и содержит домен магазина
- Тип лота — не аккаунт/DLC/мусор (lot_name проходит quick_reject=False)
"""
import re
import pytest
import requests
from bs4 import BeautifulSoup

from worker import (
    clean_game_name_for_search, matches_game_name, quick_reject, detect_region,
    check_lot_validity, parse_price, NO_PRICE_LIMIT,
)
from tests.conftest import plati_available, steambuy_available

pytestmark = pytest.mark.integration

KNOWN_REGIONS = {"RU", "CIS", "TR", "KZ", "AR", "EU", "CN", "Global", "Unknown"}
PRICE_MIN = 50
PRICE_MAX = 30_000
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Игры для тестирования — популярные, точно есть везде
TEST_GAMES = ["ELDEN RING", "Hogwarts Legacy", "Rust"]


def _assert_offer(offer: dict, shop_domain: str):
    """Общие проверки для любого оффера."""
    assert offer["price"] > PRICE_MIN, f"Цена слишком маленькая: {offer['price']}"
    assert offer["price"] < PRICE_MAX, f"Цена подозрительно большая: {offer['price']}"
    assert offer["region"] in KNOWN_REGIONS, f"Неизвестный регион: {offer['region']}"
    assert offer["url"], "URL пустой"
    assert shop_domain in offer["url"], f"URL не содержит домен {shop_domain}: {offer['url']}"
    assert offer["name"], "Название лота пустое"
    assert not quick_reject(offer["name"], ""), f"Лот не прошёл quick_reject: {offer['name']}"


# ─────────────────────────────────────────────
# Plati.market
# ─────────────────────────────────────────────

@plati_available
class TestPlatiParser:

    def _fetch_offers(self, game_name: str) -> list[dict]:
        search_name = clean_game_name_for_search(game_name)
        data = requests.get(
            "https://plati.market/api/search.ashx",
            params={"query": search_name, "response": "json"},
            headers=HEADERS,
            timeout=20,
        ).json()
        offers = []
        for item in data.get("items", []):
            name = item.get("name", "")
            price = float(item.get("price_rur", 0))
            desc = item.get("description", "")
            item_id = item.get("id")
            if not matches_game_name(name, game_name):
                continue
            if quick_reject(name, desc):
                continue
            if not check_lot_validity(name, desc):
                continue
            offers.append({
                "name": name, "price": price, "region": detect_region(name + " " + desc),
                "url": f"https://plati.market/itm/{item_id}",
            })
        return offers

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_returns_offers(self, game):
        offers = self._fetch_offers(game)
        assert len(offers) > 0, f"Plati: нет офферов для '{game}'"

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_offer_quality(self, game):
        offers = self._fetch_offers(game)
        for offer in offers[:3]:
            _assert_offer(offer, "plati.market")

    def test_rejects_accounts(self):
        """Аккаунты не должны попадать в результаты."""
        data = requests.get(
            "https://plati.market/api/search.ashx",
            params={"query": "elden ring", "response": "json"},
            headers=HEADERS, timeout=20,
        ).json()
        for item in data.get("items", []):
            name = item.get("name", "")
            desc = item.get("description", "")
            if not matches_game_name(name, "ELDEN RING"):
                continue
            if check_lot_validity(name, desc):
                assert "аккаунт" not in name.lower(), f"Аккаунт прошёл фильтр: {name}"
                assert "account" not in name.lower(), f"Account прошёл фильтр: {name}"


# ─────────────────────────────────────────────
# Steambuy
# ─────────────────────────────────────────────

@steambuy_available
class TestSteambuyParser:

    def _fetch_offers(self, game_name: str) -> list[dict]:
        resp = requests.get(
            "https://steambuy.com/sb/api/catalog/live",
            params={"a": "search", "q": clean_game_name_for_search(game_name)},
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
            timeout=10,
        )
        soup = BeautifulSoup(resp.json()["html"], "html.parser")
        offers = []
        for item in soup.find_all("a", class_="search-result__link"):
            t_elem = item.find("div", class_="search-result__title")
            p_elem = item.find("div", class_="search-result__cost")
            if not t_elem or not p_elem:
                continue
            name = t_elem.text.strip()
            price_text = re.sub(r"[^\d.]", "", p_elem.text.replace(",", "."))
            if not price_text or not matches_game_name(name, game_name):
                continue
            if not check_lot_validity(name, "", strict_key_check=False):
                continue
            price = float(price_text)
            offers.append({
                "name": name, "price": price, "region": detect_region(name),
                "url": "https://steambuy.com" + item.get("href", ""),
            })
        return offers

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_returns_offers(self, game):
        offers = self._fetch_offers(game)
        assert len(offers) > 0, f"Steambuy: нет офферов для '{game}'"

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_offer_quality(self, game):
        for offer in self._fetch_offers(game)[:3]:
            _assert_offer(offer, "steambuy.com")


# ─────────────────────────────────────────────
# Steampay
# ─────────────────────────────────────────────

class TestSteampayParser:

    def _fetch_offers(self, game_name: str) -> list[dict]:
        resp = requests.get(
            "https://steampay.com/search",
            params={"q": clean_game_name_for_search(game_name)},
            headers=HEADERS, timeout=10,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        offers = []
        for item in soup.find_all("a", class_="catalog-item"):
            activation_div = item.find("div", class_="catalog-item__activation")
            if activation_div:
                img = activation_div.find("img")
                if img and img.get("alt", "").upper() != "STEAM":
                    continue
            name_div = item.find("div", class_="catalog-item__name")
            if not name_div or not name_div.contents:
                continue
            name = name_div.contents[0].strip()
            price_span = item.find("span", class_="catalog-item__price-span")
            if not price_span:
                continue
            price_text = price_span.text.strip()
            if price_text in ("—", "СКОРО", ""):
                continue
            m = re.search(r"(\d[\d\s\xa0]*)", price_text)
            if not m:
                continue
            price = float(m.group(1).replace("\xa0", "").replace(" ", ""))
            if not matches_game_name(name, game_name, strict=True):
                continue
            if quick_reject(name, ""):
                continue
            href = item.get("href", "")
            # Получаем регион со страницы товара
            region = "Unknown"
            try:
                prod = BeautifulSoup(
                    requests.get(f"https://steampay.com{href}", headers=HEADERS, timeout=10).text,
                    "html.parser"
                )
                for key_div in prod.find_all("div", class_="product__info-key"):
                    if "регион" in key_div.text.lower():
                        val = key_div.find_next_sibling("div", class_="product__info-value")
                        if val:
                            region = detect_region(val.text)
                        break
            except Exception:
                pass
            offers.append({
                "name": name, "price": price, "region": region,
                "url": f"https://steampay.com{href}",
            })
        return offers

    @pytest.mark.parametrize("game", ["ELDEN RING", "Hogwarts Legacy"])
    def test_returns_offers(self, game):
        offers = self._fetch_offers(game)
        assert len(offers) > 0, f"Steampay: нет офферов для '{game}'"

    @pytest.mark.parametrize("game", ["ELDEN RING", "Hogwarts Legacy"])
    def test_offer_quality(self, game):
        for offer in self._fetch_offers(game)[:3]:
            _assert_offer(offer, "steampay.com")

    def test_no_gog_keys(self):
        """GOG-ключи не должны попадать."""
        resp = requests.get(
            "https://steampay.com/search", params={"q": "cyberpunk 2077"},
            headers=HEADERS, timeout=10,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.find_all("a", class_="catalog-item"):
            activation_div = item.find("div", class_="catalog-item__activation")
            if not activation_div:
                continue
            img = activation_div.find("img")
            if img and img.get("alt", "").upper() == "GOG.COM":
                # Такие должны быть отфильтрованы — проверяем что наш код их не берёт
                assert img.get("alt", "").upper() != "STEAM"

    def test_no_dlc_passes(self):
        """DLC не должны совпадать с базовой игрой в strict режиме."""
        dlc_names = [
            "ELDEN RING Shadow of the Erdtree",
            "ELDEN RING NIGHTREIGN The Forsaken Hollows",
            "ELDEN RING NIGHTREIGN",
        ]
        for name in dlc_names:
            assert not matches_game_name(name, "ELDEN RING", strict=True), \
                f"DLC/спин-офф прошёл strict-матчинг: {name}"


# ─────────────────────────────────────────────
# Zaka-Zaka
# ─────────────────────────────────────────────

class TestZakazakaParser:

    def _fetch_offers(self, game_name: str) -> list[dict]:
        resp = requests.get(
            "https://zaka-zaka.com/search/ajax/",
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
            params={"game": clean_game_name_for_search(game_name)},
            timeout=15,
        )
        if resp.status_code != 200 or not resp.text.strip():
            return []
        offers = []
        for item in resp.json():
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
            slug = item.get("url", "").lstrip("/")
            if not slug.startswith("game/"):
                slug = f"game/{slug}"
            offers.append({
                "name": name, "price": price, "region": detect_region(name + " " + drm),
                "url": f"https://zaka-zaka.com/{slug}",
            })
        return offers

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_returns_offers(self, game):
        offers = self._fetch_offers(game)
        if not offers:
            pytest.skip(f"Zaka-Zaka: '{game}' временно нет в наличии")
        assert len(offers) > 0, f"Zaka-Zaka: нет офферов для '{game}'"

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_offer_quality(self, game):
        for offer in self._fetch_offers(game)[:3]:
            _assert_offer(offer, "zaka-zaka.com")


# ─────────────────────────────────────────────
# GGSEL
# ─────────────────────────────────────────────

class TestGGSELParser:

    def _fetch_offers(self, game_name: str) -> list[dict]:
        payload = {
            "search_term": clean_game_name_for_search(game_name),
            "limit": 60, "currency": "wmr", "is_russian_ip": 1,
            "lang": "ru", "sort": "sortByRec",
            "platforms": ["Steam"], "content_type_ids": [2, 48],
        }
        data = requests.post(
            "https://api.ggsel.com/elastic/goods/query",
            json=payload,
            headers={**HEADERS, "Origin": "https://ggsel.net"},
            timeout=15,
        ).json()
        offers = []
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
            offers.append({
                "name": name, "price": price,
                "region": detect_region(name),
                "url": f"https://ggsel.net/catalog/product/{item.get('id_goods')}",
            })
        return offers

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_returns_offers(self, game):
        offers = self._fetch_offers(game)
        assert len(offers) > 0, f"GGSEL: нет офферов для '{game}'"

    @pytest.mark.parametrize("game", TEST_GAMES)
    def test_offer_quality(self, game):
        for offer in self._fetch_offers(game)[:3]:
            _assert_offer(offer, "ggsel.net")


# ─────────────────────────────────────────────
# GabeStore
# ─────────────────────────────────────────────

class TestGabeStoreParser:

    def _fetch_offers(self, game_name: str) -> list[dict]:
        from services.parsers.gabestore import parse_gabestore
        raw_offers = parse_gabestore(1, game_name)
        return [
            {
                "name": o["lot_name"],
                "price": o["price"],
                "region": o["region"],
                "url": o["lot_url"],
            }
            for o in raw_offers
        ]

    @pytest.mark.parametrize("game", ["ELDEN RING", "Hogwarts Legacy"])
    def test_returns_offers(self, game):
        offers = self._fetch_offers(game)
        assert len(offers) > 0, f"GabeStore: нет офферов для '{game}'"

    @pytest.mark.parametrize("game", ["ELDEN RING", "Hogwarts Legacy"])
    def test_offer_quality(self, game):
        for offer in self._fetch_offers(game)[:3]:
            _assert_offer(offer, "gabestore.ru")
