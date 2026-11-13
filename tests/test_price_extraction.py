"""
Комплексные автотесты извлечения и корректности цен:
1. Юнит-тесты универсального парсера цен parse_price (разделители, форматы, валюты, HTML, копейки, скидки).
2. Юнит-тесты парсеров на мок-данных (Plati, Steambuy, Steampay, Zaka-Zaka, GGSEL, FunPay).
3. Тесты Steam API (конвертация региональных валют, бесплатные игры, недоступные регионы).
4. Интеграционные тесты на живых данных с проверкой разумных диапазонов цен.
"""
import pytest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup

from services.filters import parse_price, detect_region, matches_game_name
from services.config import NO_PRICE_LIMIT
from services.parsers.plati import parse_plati
from services.parsers.steambuy import parse_steambuy
from services.parsers.steampay import parse_steampay
from services.parsers.zakazaka import parse_zakazaka
from services.parsers.ggsel import parse_ggsel
from services.parsers.funpay import parse_funpay
from services.parsers.gabestore import parse_gabestore
from main import get_steam_regional_prices, STEAM_EXCHANGE_RATES


# ─────────────────────────────────────────────────────────────────────────────
# 1. Юнит-тесты универсального экстрактора parse_price
# ─────────────────────────────────────────────────────────────────────────────

class TestParsePriceUnit:
    """Проверка очистки и конвертации различных форматов строк с ценами."""

    def test_integers_and_floats(self):
        assert parse_price(1000) == 1000.0
        assert parse_price(1290.5) == 1290.5
        assert parse_price(45.99) == 45.99

    def test_thousands_separators_spaces(self):
        # Обычные и неразрывные пробелы между тысячами
        assert parse_price("1 290") == 1290.0
        assert parse_price("1\xa0290") == 1290.0
        assert parse_price("12 450 руб") == 12450.0
        assert parse_price(" 1  999  ₽ ") == 1999.0

    def test_thousands_dot_and_comma(self):
        assert parse_price("1.290") == 1290.0
        assert parse_price("1,290") == 1290.0
        assert parse_price("1.290 руб.") == 1290.0
        assert parse_price("1,290.50") == 1290.5
        assert parse_price("1.290,50") == 1290.5

    def test_decimal_comma_and_dot(self):
        assert parse_price("1290,50") == 1290.5
        assert parse_price("1290.50") == 1290.5
        assert parse_price("2 999,50 ₽") == 2999.5
        assert parse_price("99,99 руб.") == 99.99

    def test_currency_symbols_and_suffixes(self):
        assert parse_price("1079 р") == 1079.0
        assert parse_price("1 499 руб.") == 1499.0
        assert parse_price("2 999,50 ₽") == 2999.5
        assert parse_price("1295 c") == 1295.0
        assert parse_price("149.00 wmr") == 149.0
        assert parse_price("$45.00") == 45.0
        assert parse_price("€39.99") == 39.99
        assert parse_price("от 599 р") == 599.0

    def test_html_markup_in_price(self):
        # Zaka-Zaka и другие магазины со встроенными тегами внутри цены
        assert parse_price('1 290 <span class="rub">р.</span>') == 1290.0
        assert parse_price('1295 <i class="rouble">c</i>') == 1295.0
        assert parse_price('<span><b>3 490</b> руб</span>') == 3490.0

    def test_discount_strikethrough_handling(self):
        # Зачеркнутая старая цена вместе с новой ценой — берем только новую
        assert parse_price('<s>3997</s> 2999 руб') == 2999.0
        assert parse_price('<del>2500 руб</del> 1990 руб') == 1990.0
        assert parse_price('<strike>1000</strike> 500 ₽') == 500.0

        # Если осталась ТОЛЬКО зачеркнутая цена (товар не в наличии) — возвращаем None
        assert parse_price('<s>3997 <i class="rouble">c</i></s>') is None
        assert parse_price('<del>2500 руб</del>') is None

    def test_out_of_stock_and_placeholders(self):
        assert parse_price(-2) is None
        assert parse_price("-2") is None
        assert parse_price("—") is None
        assert parse_price("-") is None
        assert parse_price("СКОРО") is None
        assert parse_price("скоро") is None
        assert parse_price("нет в наличии") is None
        assert parse_price("out of stock") is None
        assert parse_price("Показать еще...") is None

    def test_zero_and_negative(self):
        assert parse_price(0) is None
        assert parse_price(0.0) is None
        assert parse_price("0") is None
        assert parse_price("0 ₽") is None
        assert parse_price(-500) is None
        assert parse_price("-500 руб") is None

    def test_empty_and_invalid_types(self):
        assert parse_price("") is None
        assert parse_price("   ") is None
        assert parse_price(None) is None
        assert parse_price([]) is None
        assert parse_price({}) is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Мок-тесты парсеров магазинов (проверка правильности извлечения структуры цен)
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatiPriceExtraction:
    """Тестирование парсинга цен с Plati.market на мок-ответах."""

    @patch("services.parsers.plati.get_http_session")
    def test_extracts_correct_price_types(self, mock_session):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {
                    "id": 101,
                    "name": "ELDEN RING Steam Ключ RU+CIS",
                    "price_rur": 2499.50,
                    "description": "Лицензионный ключ Steam Россия и СНГ",
                },
                {
                    "id": 102,
                    "name": "ELDEN RING Gift Global",
                    "price_rur": "2190",
                    "description": "Steam gift global",
                },
            ]
        }
        mock_session.return_value.get.return_value = mock_resp

        results = parse_plati(1, "ELDEN RING")
        assert len(results) > 0
        for r in results:
            assert isinstance(r["price"], (int, float))
            assert r["price"] > 0
            assert r["shop_name"] in ("Plati (Key)", "Plati (Gift)")
            assert r["region"] in ("RU", "CIS", "Global")

    @patch("services.parsers.plati.get_http_session")
    def test_filters_zero_and_junk_prices(self, mock_session):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {
                    "id": 103,
                    "name": "ELDEN RING Читы трейнер",
                    "price_rur": 50.0,
                    "description": "чит",
                },
                {
                    "id": 104,
                    "name": "ELDEN RING Steam Key",
                    "price_rur": 0,
                    "description": "ключ",
                },
                {
                    "id": 105,
                    "name": "ELDEN RING Steam Key",
                    "price_rur": None,
                    "description": "ключ",
                },
            ]
        }
        mock_session.return_value.get.return_value = mock_resp

        results = parse_plati(1, "ELDEN RING")
        assert len(results) == 0, "Мусорные или нулевые цены не должны попадать в результаты"


class TestSteambuyPriceExtraction:
    """Тестирование парсинга цен со Steambuy на мок-HTML."""

    @patch("services.parsers.steambuy.get_http_session")
    def test_extracts_prices_with_currency_symbols(self, mock_session):
        html_payload = """
        <div class="search-result__item">
            <a href="/steam/elden-ring-russia/" class="search-result__link">
                <div class="search-result__title">ELDEN RING Россия и СНГ</div>
                <div class="search-result__cost">2 889 р</div>
            </a>
        </div>
        <div class="search-result__item">
            <a href="/steam/elden-ring-global/" class="search-result__link">
                <div class="search-result__title">ELDEN RING Global Key</div>
                <div class="search-result__cost">3 490,50 руб.</div>
            </a>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"html": html_payload}
        mock_session.return_value.get.return_value = mock_resp

        results = parse_steambuy(1, "ELDEN RING")
        assert len(results) == 2
        prices = {r["region"]: r["price"] for r in results}
        assert prices.get("CIS") == 2889.0 or prices.get("RU") == 2889.0
        assert prices.get("Global") == 3490.5

    @patch("services.parsers.steambuy.get_http_session")
    def test_handles_out_of_stock_cleanly(self, mock_session):
        html_payload = """
        <div class="search-result__item">
            <a href="/steam/elden-ring/" class="search-result__link">
                <div class="search-result__title">ELDEN RING</div>
                <div class="search-result__cost">Нет в наличии</div>
            </a>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"html": html_payload}
        mock_session.return_value.get.return_value = mock_resp

        results = parse_steambuy(1, "ELDEN RING")
        assert len(results) == 0


class TestSteampayPriceExtraction:
    """Тестирование парсинга цен со Steampay на мок-HTML."""

    @patch("services.parsers.steampay.get_http_session")
    def test_extracts_prices_with_nbsp(self, mock_session):
        catalog_html = """
        <a class="catalog-item" href="/game/elden-ring">
            <div class="catalog-item__activation"><img alt="STEAM"></div>
            <div class="catalog-item__name">ELDEN RING</div>
            <span class="catalog-item__price-span">1&nbsp;999 ₽</span>
        </a>
        <a class="catalog-item" href="/game/elden-ring-deluxe">
            <div class="catalog-item__activation"><img alt="GOG.COM"></div>
            <div class="catalog-item__name">ELDEN RING</div>
            <span class="catalog-item__price-span">1 500 ₽</span>
        </a>
        <a class="catalog-item" href="/game/elden-ring-soon">
            <div class="catalog-item__activation"><img alt="STEAM"></div>
            <div class="catalog-item__name">ELDEN RING</div>
            <span class="catalog-item__price-span">СКОРО</span>
        </a>
        """
        product_html = """
        <div class="product__info-key">Регион активации:</div>
        <div class="product__info-value">Россия и страны СНГ</div>
        """

        mock_s = MagicMock()
        mock_resp1 = MagicMock()
        mock_resp1.text = catalog_html
        mock_resp2 = MagicMock()
        mock_resp2.text = product_html

        mock_s.get.side_effect = [mock_resp1, mock_resp2]
        mock_session.return_value = mock_s

        results = parse_steampay(1, "ELDEN RING")
        assert len(results) == 1
        assert results[0]["price"] == 1999.0
        assert results[0]["region"] in ("RU", "CIS")
        assert results[0]["shop_name"] == "Steampay"


class TestZakazakaPriceExtraction:
    """Тестирование парсинга цен с Zaka-Zaka на мок-ответах."""

    @patch("services.parsers.zakazaka.get_http_session")
    def test_regression_thousands_space_not_truncated(self, mock_session):
        """
        КРИТИЧЕСКИЙ РЕГРЕССИОННЫЙ ТЕСТ:
        Ранее '1 290 <span class="rub">р.</span>' усекалось регуляркой до 1.0 ₽!
        Убеждаемся, что парсер извлекает ровно 1290.0 ₽.
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_resp.json.return_value = [
            {
                "type": "game",
                "name": "ELDEN RING",
                "price": '1 290 <span class="rub">р.</span>',
                "drm": "Steam (Россия и СНГ)",
                "url": "/game/elden-ring",
            },
            {
                "type": "game",
                "name": "ELDEN RING NIGHTREIGN",
                "price": '2289 <i class="rouble">c</i>',
                "drm": "Steam",
                "url": "/game/elden-ring-nightreign",
            },
            {
                "type": "game",
                "name": "ELDEN RING OutOfStock",
                "price": -2,
                "drm": "Steam",
                "url": "/game/out-of-stock",
            },
            {
                "type": "game",
                "name": "ELDEN RING Strikethrough",
                "price": '<s>3997 <i class="rouble">c</i></s>',
                "drm": "Steam",
                "url": "/game/deluxe",
            },
        ]
        mock_session.return_value.get.return_value = mock_resp

        results = parse_zakazaka(1, "ELDEN RING")
        offers = {r["lot_name"]: r for r in results}
        assert "ELDEN RING" in offers
        offer = offers["ELDEN RING"]
        # Проверяем, что цена 1290.0, а не 1.0!
        assert offer["price"] == 1290.0, f"Цена искажена: {offer['price']} вместо 1290.0"
        assert offer["region"] in ("RU", "CIS")
        assert offer["lot_url"] == "https://zaka-zaka.com/game/elden-ring"
        # Убеждаемся, что не попали лоты с ценой -2, зачеркнутой ценой и другой игрой (NIGHTREIGN)
        assert "ELDEN RING OutOfStock" not in offers
        assert "ELDEN RING Strikethrough" not in offers
        assert "ELDEN RING NIGHTREIGN" not in offers

    @patch("services.parsers.zakazaka.get_http_session")
    def test_zakazaka_url_prefix_and_dlc_rejection(self, mock_session):
        """
        Проверяем:
        1. Если slug без /game/ ('elden-ring'), формируется валидный URL 'https://zaka-zaka.com/game/elden-ring' (не 404!).
        2. DLC 'Shadow of the Erdtree' отклоняется при парсинге 'ELDEN RING'.
        3. DLC 'The Forsaken Hollows' отклоняется при парсинге 'ELDEN RING NIGHTREIGN'.
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_resp.json.return_value = [
            {
                "type": "game",
                "name": "ELDEN RING",
                "price": '2889 <i class="rouble">c</i>',
                "drm": "steam",
                "url": "elden-ring",  # Zaka-Zaka возвращает slug БЕЗ game/
            },
            {
                "type": "game",
                "name": "ELDEN RING Shadow of the Erdtree",
                "price": '2095 <i class="rouble">c</i>',
                "drm": "steam",
                "url": "elden-ring-shadow-of-the-erdtree",
            },
            {
                "type": "game",
                "name": "ELDEN RING NIGHTREIGN The Forsaken Hollows",
                "price": '997 <i class="rouble">c</i>',
                "drm": "steam",
                "url": "elden-ring-nightreign-the-forsaken-hollows",
            },
        ]
        mock_session.return_value.get.return_value = mock_resp

        # 1. Запрос базовой ELDEN RING
        results_base = parse_zakazaka(1, "ELDEN RING")
        assert len(results_base) == 1
        assert results_base[0]["lot_name"] == "ELDEN RING"
        assert results_base[0]["price"] == 2889.0
        assert results_base[0]["lot_url"] == "https://zaka-zaka.com/game/elden-ring"

        # 2. Запрос ELDEN RING NIGHTREIGN — не должен брать Forsaken Hollows DLC
        mock_resp.json.return_value = [
            {
                "type": "game",
                "name": "ELDEN RING NIGHTREIGN",
                "price": '2289 <i class="rouble">c</i>',
                "drm": "steam",
                "url": "elden-ring-nightreign",
            },
            {
                "type": "game",
                "name": "ELDEN RING NIGHTREIGN The Forsaken Hollows",
                "price": '997 <i class="rouble">c</i>',
                "drm": "steam",
                "url": "elden-ring-nightreign-the-forsaken-hollows",
            },
        ]
        results_nr = parse_zakazaka(351, "ELDEN RING NIGHTREIGN")
        assert len(results_nr) == 1
        assert results_nr[0]["lot_name"] == "ELDEN RING NIGHTREIGN"
        assert results_nr[0]["price"] == 2289.0
        assert results_nr[0]["lot_url"] == "https://zaka-zaka.com/game/elden-ring-nightreign"


class TestGGSELPriceExtraction:
    """Тестирование парсинга цен с GGSEL."""

    @patch("services.parsers.ggsel.get_http_session")
    def test_extracts_price_wmr_correctly(self, mock_session):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "items": [
                    {
                        "id_goods": 555,
                        "name": "ELDEN RING Steam Gift RU",
                        "price_wmr": "1850.50",
                    },
                    {
                        "id_goods": 556,
                        "name": "ELDEN RING Steam Ключ Global",
                        "price_wmr": "2499.00",
                    },
                    {
                        "id_goods": 557,
                        "name": "ELDEN RING Некорректная цена",
                        "price_wmr": "invalid",
                    },
                ]
            }
        }
        mock_session.return_value.post.return_value = mock_resp

        results = parse_ggsel(1, "ELDEN RING")
        assert len(results) == 2
        prices = {r["region"]: r["price"] for r in results}
        assert prices.get("RU") == 1850.5
        assert prices.get("Global") == 2499.0


class TestFunPayPriceExtraction:
    """Тестирование парсинга цен с FunPay."""

    @patch("services.parsers.funpay.get_http_session")
    def test_extracts_data_s_attribute_price(self, mock_session):
        html_payload = """
        <div class="tc-item" href="https://funpay.com/lots/offer?id=1">
            <div class="tc-desc">PC\n\nELDEN RING Ключ Steam RU/СНГ</div>
            <div class="tc-price" data-s="2250.75">2 250 ₽</div>
        </div>
        <div class="tc-item" href="https://funpay.com/lots/offer?id=2">
            <div class="tc-desc">PS5\n\nELDEN RING Аккаунт PSN</div>
            <div class="tc-price" data-s="999.00">999 ₽</div>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html_payload
        mock_session.return_value.get.return_value = mock_resp

        results = parse_funpay(1, "https://funpay.com/lots/test/")
        assert len(results) == 1
        assert results[0]["price"] == 2250.75
        assert results[0]["region"] in ("RU", "CIS")

    @patch("services.parsers.funpay.get_http_session")
    def test_rejects_dlc_shadow_of_erdtree(self, mock_session):
        html_payload = """
        <div class="tc-item" href="https://funpay.com/lots/offer?id=10">
            <div class="tc-desc">PC\n\nELDEN RING Shadow of the Erdtree Steam Ключ</div>
            <div class="tc-price" data-s="1999.00">1 999 ₽</div>
        </div>
        <div class="tc-item" href="https://funpay.com/lots/offer?id=11">
            <div class="tc-desc">PC\n\nELDEN RING Standard Edition Steam Ключ RU</div>
            <div class="tc-price" data-s="2850.00">2 850 ₽</div>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html_payload
        mock_session.return_value.get.return_value = mock_resp

        results = parse_funpay(1, "https://funpay.com/lots/test/", game_name="ELDEN RING")
        assert len(results) == 1
        assert results[0]["price"] == 2850.0
        assert "Shadow" not in results[0]["lot_name"]


class TestGabeStorePriceExtraction:
    """Тестирование парсинга цен с GabeStore на мок-HTML."""

    @patch("services.parsers.gabestore.get_http_session")
    def test_extracts_prices_and_ignores_dlc_and_out_of_stock(self, mock_session):
        search_html = """
        <div class="shop-item">
            <a class="shop-item__name" href="/game/elden-ring">ELDEN RING</a>
            <div class="shop-item__price">
                <div class="shop-item__price-current">2 739 ₽</div>
            </div>
            <a class="btn btn--primary js-addToCart" href="/basket">В корзину</a>
        </div>
        <div class="shop-item">
            <div class="shop-item__label">DLC</div>
            <a class="shop-item__name" href="/game/elden-ring-dlc">ELDEN RING NIGHTREIGN The Forsaken Hollows</a>
            <div class="shop-item__price">
                <div class="shop-item__price-current">1 080 ₽</div>
            </div>
            <a class="btn btn--primary js-addToCart" href="/basket">В корзину</a>
        </div>
        <div class="shop-item">
            <a class="shop-item__name" href="/game/elden-ring-stock">ELDEN RING</a>
            <div class="shop-item__price">
                <div class="shop-item__price-current">1 299 ₽</div>
            </div>
            <a class="btn btn--primary btn--empty-item js-addToCart">Отсутствует</a>
        </div>
        """
        product_html = """
        <div class="b-card__subinfo-item">
            <div class="b-card__subinfo-head">Регион активации</div>
            <div class="b-card__subinfo-body">Россия, Украина и СНГ</div>
        </div>
        """

        mock_s = MagicMock()
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.text = search_html

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.text = product_html

        mock_s.get.side_effect = [mock_resp1, mock_resp2]
        mock_session.return_value = mock_s

        results = parse_gabestore(1, "ELDEN RING")
        assert len(results) == 1
        assert results[0]["price"] == 2739.0
        assert results[0]["lot_name"] == "ELDEN RING"
        assert results[0]["shop_name"] == "GabeStore"
        assert results[0]["region"] == "RU"
        assert results[0]["lot_url"] == "https://gabestore.ru/game/elden-ring"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Тесты Steam Official API (конвертация региональных валют)
# ─────────────────────────────────────────────────────────────────────────────

class TestSteamOfficialPriceExtraction:
    """Проверка извлечения и конвертации цен Steam Store API."""

    @pytest.mark.anyio
    async def test_steam_rub_price(self):
        """Проверка цен в рублях: делится на 100 и конвертируется по курсу 1.0."""
        search_mock = {"items": [{"id": 1245620}]}
        app_mock = {
            "1245620": {
                "success": True,
                "data": {
                    "price_overview": {
                        "final": 399900,  # 3999.00 RUB в копейках
                        "currency": "RUB",
                    }
                }
            }
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            resp_search = MagicMock()
            resp_search.json.return_value = search_mock

            resp_price = MagicMock()
            resp_price.json.return_value = app_mock

            mock_get.side_effect = [resp_search, resp_price, resp_price, resp_price]

            prices = await get_steam_regional_prices("ELDEN RING")
            assert prices["Россия"] == "~3999 ₽"
            assert prices["raw_rub"] == 3999

    @pytest.mark.anyio
    async def test_steam_regional_currencies_kzt_try(self):
        """Проверка конвертации KZT (Казахстан) и USD/TRY в рубли."""
        search_mock = {"items": [{"id": 1086940}]}
        app_kz_mock = {
            "1086940": {
                "success": True,
                "data": {
                    "price_overview": {
                        "final": 1999900,  # 19999 KZT
                        "currency": "KZT",
                    }
                }
            }
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            resp_search = MagicMock()
            resp_search.json.return_value = search_mock

            resp_price = MagicMock()
            resp_price.json.return_value = app_kz_mock

            mock_get.side_effect = [resp_search, resp_price, resp_price, resp_price]

            prices = await get_steam_regional_prices("Baldur's Gate 3")
            # 19999 * 0.20 = ~3999 ₽
            expected_rub = int((1999900 / 100) * STEAM_EXCHANGE_RATES["KZT"])
            assert prices["Казахстан"] == f"~{expected_rub} ₽"

    @pytest.mark.anyio
    async def test_steam_free_to_play_game(self):
        """Бесплатные игры не содержат price_overview — не должны вызывать ошибку."""
        search_mock = {"items": [{"id": 730}]}
        app_f2p_mock = {
            "730": {
                "success": True,
                "data": {
                    "is_free": True
                    # price_overview отсутствует
                }
            }
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            resp_search = MagicMock()
            resp_search.json.return_value = search_mock

            resp_price = MagicMock()
            resp_price.json.return_value = app_f2p_mock

            mock_get.side_effect = [resp_search, resp_price, resp_price, resp_price]

            prices = await get_steam_regional_prices("Counter-Strike 2")
            assert prices["Россия"] == "Недоступно"
            assert prices["raw_rub"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Интеграционные тесты на живых данных (проверка границ цен)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestLivePriceSanity:
    """
    Проверяет, что живые парсеры для реальных игр возвращают
    адекватные цены (не 1 рубль из-за багов парсинга, и не заоблачные миллионы).
    """

    @pytest.mark.parametrize("game_name", ["ELDEN RING", "Rust", "Hogwarts Legacy"])
    def test_live_steambuy_price_sanity(self, game_name):
        offers = parse_steambuy(1, game_name)
        if not offers:
            pytest.skip(f"Steambuy временно не имеет предложений для {game_name}")
        for offer in offers:
            price = offer["price"]
            assert isinstance(price, (int, float))
            # Цена AAA/популярной игры должна быть в разумных пределах
            assert price >= 50, f"Подозрительно низкая цена на Steambuy для {game_name}: {price} ₽ (возможный баг парсинга!)"
            assert price <= 30000, f"Слишком высокая цена: {price}"

    @pytest.mark.parametrize("game_name", ["ELDEN RING", "Rust", "Hogwarts Legacy"])
    def test_live_zakazaka_price_sanity(self, game_name):
        offers = parse_zakazaka(1, game_name)
        if not offers:
            pytest.skip(f"Zaka-Zaka временно не имеет предложений для {game_name}")
        for offer in offers:
            price = offer["price"]
            assert isinstance(price, (int, float))
            # Критическая проверка: Zaka-Zaka не должен возвращать 1.0 ₽ или 2.0 ₽ из-за пробелов!
            assert price >= 50, f"Подозрительно низкая цена на Zaka-Zaka для {game_name}: {price} ₽ (баг пробелов в тысячах!)"
            assert price <= 30000, f"Слишком высокая цена: {price}"

    @pytest.mark.parametrize("game_name", ["ELDEN RING", "Rust", "Hogwarts Legacy"])
    def test_live_ggsel_price_sanity(self, game_name):
        offers = parse_ggsel(1, game_name)
        if not offers:
            pytest.skip(f"GGSEL временно не имеет предложений для {game_name}")
        for offer in offers:
            price = offer["price"]
            assert isinstance(price, (int, float))
            assert price >= 50, f"Подозрительно низкая цена на GGSEL для {game_name}: {price} ₽"
            assert price <= 30000, f"Слишком высокая цена: {price}"

    @pytest.mark.parametrize("game_name", ["ELDEN RING", "Cyberpunk 2077", "Hogwarts Legacy"])
    def test_live_gabestore_price_sanity(self, game_name):
        offers = parse_gabestore(1, game_name)
        if not offers:
            pytest.skip(f"GabeStore временно не имеет предложений для {game_name}")
        for offer in offers:
            price = offer["price"]
            assert isinstance(price, (int, float))
            assert price >= 50, f"Подозрительно низкая цена на GabeStore для {game_name}: {price} ₽"
            assert price <= 30000, f"Слишком высокая цена: {price}"
            assert offer["region"] in {"RU", "CIS", "TR", "KZ", "AR", "EU", "Global", "Unknown"}
            assert "gabestore.ru" in offer["lot_url"]
