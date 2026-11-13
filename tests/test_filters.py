"""
Юнит-тесты для функций фильтрации: matches_game_name, detect_region, quick_reject.
Запуск: docker compose exec worker pytest tests/ -v
"""
import pytest
from bs4 import BeautifulSoup
from worker import matches_game_name, detect_region, detect_platform, quick_reject, check_lot_validity
from services.filters import (
    is_reliable_seller_funpay,
    is_reliable_seller_ggsel,
    is_reliable_seller_plati,
)


# ─────────────────────────────────────────────
# matches_game_name
# ─────────────────────────────────────────────

class TestMatchesGameName:

    # --- должно совпадать ---

    def test_exact_match(self):
        assert matches_game_name("ELDEN RING", "ELDEN RING")

    def test_edition_noise_words(self):
        # deluxe/edition — шум, не должны мешать
        assert matches_game_name("Cyberpunk 2077 Deluxe Edition", "Cyberpunk 2077")

    def test_definite_article_ignored(self):
        assert matches_game_name("The Witcher 3: Wild Hunt", "The Witcher 3: Wild Hunt")

    def test_region_in_brackets_stripped(self):
        # скобки вырезаются, остаётся чистое название
        assert matches_game_name("Hogwarts Legacy (СНГ без РФ/РБ)", "Hogwarts Legacy")

    def test_steam_noise_stripped(self):
        assert matches_game_name("Red Dead Redemption 2 Steam Key Global", "Red Dead Redemption 2")

    def test_remastered_stop_word(self):
        assert matches_game_name("Mafia Definitive Edition Remastered", "Mafia")

    def test_goty_stop_word(self):
        # GOTY edition без полного subtitle совпадает если в запросе нет subtitle
        assert matches_game_name("Red Dead Redemption 2 GOTY Edition", "Red Dead Redemption 2")

    def test_colon_game_with_same_subtitle(self):
        assert matches_game_name("Counter-Strike: Global Offensive", "Counter-Strike: Global Offensive")

    # --- должно отклоняться ---

    def test_single_word_substring_rejected(self):
        # "Rust" не должен матчиться с "Rusty Rabbit" или "The Crust"
        assert not matches_game_name("Rusty Rabbit", "Rust")
        assert not matches_game_name("The Crust", "Rust")
        assert matches_game_name("Rust", "Rust")

    def test_different_sequel_number(self):
        # Portal 2 ≠ Portal
        assert not matches_game_name("Portal 2", "Portal")

    def test_dlc_emdash(self):
        # DLC через тире
        assert not matches_game_name("The Witcher 3: Wild Hunt — Blood and Wine", "The Witcher 3: Wild Hunt")

    def test_dlc_endash(self):
        assert not matches_game_name("ELDEN RING – Shadow of the Erdtree", "ELDEN RING")

    def test_colon_different_subtitle(self):
        # CS без подзаголовка ≠ CS:GO
        assert not matches_game_name("Counter-Strike: Global Offensive", "Counter-Strike")

    def test_sequel_in_name(self):
        assert not matches_game_name("Risen 3: Titan Lords", "Risen")

    def test_different_game_same_words(self):
        assert not matches_game_name("Portal 2 Remastered", "Portal")

    def test_wrong_game_partial(self):
        # "The Escapists" не должно совпадать с "The Escapists 2"
        assert not matches_game_name("The Escapists", "The Escapists 2")

    # --- strict режим (для прямых ретейлеров) ---

    def test_strict_rejects_extra_word(self):
        # "NIGHTREIGN" — отдельная игра, не база
        assert not matches_game_name("ELDEN RING NIGHTREIGN", "ELDEN RING", strict=True)

    def test_strict_rejects_dlc_expansion(self):
        assert not matches_game_name("ELDEN RING Shadow of the Erdtree", "ELDEN RING", strict=True)

    def test_strict_allows_exact(self):
        assert matches_game_name("ELDEN RING", "ELDEN RING", strict=True)

    def test_strict_allows_edition_noise(self):
        # deluxe/edition — в noise/stop словах, strict не должен их отклонять
        assert matches_game_name("Hogwarts Legacy Deluxe Edition (СНГ)", "Hogwarts Legacy", strict=True)


# ─────────────────────────────────────────────
# detect_region
# ─────────────────────────────────────────────

class TestDetectRegion:

    def test_global(self):
        assert detect_region("Cyberpunk 2077 Steam Key Global") == "Global"

    def test_region_free(self):
        assert detect_region("game region free") == "Global"

    def test_ru_russia(self):
        assert detect_region("Ключ для России") == "RU"  # родительный падеж

    def test_ru_rossiya(self):
        assert detect_region("Steam Россия") == "RU"  # именительный падеж

    def test_ru_rossii(self):
        assert detect_region("только для России и СНГ") == "RU"

    def test_ru_abbreviation(self):
        assert detect_region("Steam Key RU") == "RU"

    def test_cis_without_rf(self):
        # "СНГ без РФ" должен давать CIS, не RU
        assert detect_region("gift СНГ без РФ") == "CIS"

    def test_cis_excl(self):
        assert detect_region("CIS excl RU") == "CIS"

    def test_cis_plain(self):
        assert detect_region("Ключ СНГ") == "CIS"

    def test_ukraine(self):
        assert detect_region("🌏Украина🌏 Steam Подарок") == "UA"

    def test_ukraine_en(self):
        assert detect_region("Ukraine gift") == "UA"

    def test_ukraine_before_cis(self):
        # "Украина" должна матчиться как UA, не как CIS
        assert detect_region("Steam Gift Украина") == "UA"

    def test_turkey(self):
        assert detect_region("Steam TR Турция") == "TR"

    def test_kazakhstan(self):
        assert detect_region("gift KZ") == "KZ"

    def test_argentina(self):
        assert detect_region("AR Argentina key") == "AR"

    def test_latam(self):
        assert detect_region("LATAM region") == "AR"

    def test_europe(self):
        assert detect_region("EU Europe key") == "EU"

    def test_europe_cyrillic(self):
        assert detect_region("Европа регион") == "EU"

    def test_china(self):
        assert detect_region("CN China") == "CN"

    def test_unknown(self):
        assert detect_region("просто ключ steam") == "Unknown"

    def test_cis_without_rf_priority_over_ru(self):
        # Если есть "без рф" — это CIS, несмотря на то что "рф" там тоже есть
        assert detect_region("СНГ без рф") == "CIS"

    def test_all_countries_detected_as_global(self):
        assert detect_region("ВСЕ СТРАНЫ New World Aeternum Steam Gift") == "Global"

    def test_negative_ru_in_description_detected_as_eu(self):
        text = "⭐ New World: Aeternum EU Steam КЛЮЧ 🔑 ЕВРОПА Регион активации : 🇪🇺 Европа (❗️Нельзя активировать в RU и СНГ❗️)"
        assert detect_region(text) == "EU"


# ─────────────────────────────────────────────
# quick_reject
# ─────────────────────────────────────────────

class TestQuickReject:

    # --- должно отклоняться ---

    def test_account(self):
        assert quick_reject("Cyberpunk 2077 аккаунт", "")

    def test_offline(self):
        assert quick_reject("Hogwarts Legacy оффлайн режим", "")

    def test_shared_account(self):
        assert quick_reject("Game Pass общий аккаунт", "")

    def test_ps5_console_account(self):
        assert quick_reject("ELDEN RING PS5 (П2)", "")
        assert quick_reject("ELDEN RING PS5 [П3]", "")
        assert quick_reject("ELDEN RING PS5 общий аккаунт", "")

    def test_xbox_console_account(self):
        assert quick_reject("Forza Horizon Xbox аккаунт", "")
        assert quick_reject("Forza Horizon Xbox оффлайн", "")

    def test_subscription_months(self):
        assert quick_reject("Game Pass 1 месяц", "")

    def test_subscription_days(self):
        assert quick_reject("EA Play 30 дней", "")

    def test_dlc(self):
        assert quick_reject("Cyberpunk DLC expansion", "")

    def test_season_pass(self):
        assert quick_reject("Far Cry 6 Season Pass", "")

    def test_boost_service(self):
        assert quick_reject("Буст аккаунта до золота", "")

    def test_in_game_currency(self):
        assert quick_reject("100 монет в игре", "")

    def test_in_game_orbs(self):
        assert quick_reject("50 orb gems pack", "")

    def test_cheat_latin(self):
        assert quick_reject("CS2 cheat aimbot", "")

    def test_cheat_homoglyph(self):
        # Нack — кириллица вместо латиницы
        assert quick_reject("CS2 Нack tool", "")

    def test_hardware_promo(self):
        assert quick_reject("Ключ для RTX 4090 nvidia", "")

    def test_qr_code(self):
        assert quick_reject("активация через qr код", "")

    def test_crack(self):
        assert quick_reject("игра кряк таблетка", "")

    # --- не должно отклоняться ---

    def test_valid_steam_key(self):
        assert not quick_reject("ELDEN RING Steam Key RU", "")

    def test_valid_gift(self):
        assert not quick_reject("Hogwarts Legacy Steam Gift CIS", "")

    def test_valid_global_key(self):
        assert not quick_reject("Cyberpunk 2077 Global Key", "")

    def test_valid_kz_key(self):
        assert not quick_reject("Red Dead Redemption 2 KZ Steam ключ", "")

    def test_valid_console_key(self):
        assert not quick_reject("ELDEN RING PS5 Ключ", "")
        assert not quick_reject("Forza Horizon 5 Xbox Ключ Global", "")


# ─────────────────────────────────────────────
# detect_platform
# ─────────────────────────────────────────────

class TestDetectPlatform:

    def test_steam(self):
        assert detect_platform("ELDEN RING Steam Key") == "Steam"
        assert detect_platform("ELDEN RING", drm="Steam") == "Steam"
        assert detect_platform("ELDEN RING", shop_name="Steambuy") == "Steam"

    def test_epic_games(self):
        assert detect_platform("Cyberpunk 2077 Epic Games Store") == "Epic Games"
        assert detect_platform("Hogwarts Legacy EGS Key") == "Epic Games"
        assert detect_platform("Hogwarts Legacy", drm="Epic Games") == "Epic Games"

    def test_xbox(self):
        assert detect_platform("Forza Horizon 5 Xbox One Series X/S Ключ") == "Xbox"
        assert detect_platform("Forza Horizon 5", drm="Xbox") == "Xbox"
        assert detect_platform("Starfield Microsoft Store Key") == "Xbox"

    def test_playstation(self):
        assert detect_platform("ELDEN RING PS5 Ключ") == "PlayStation"
        assert detect_platform("God of War Ragnarok PlayStation 4") == "PlayStation"
        assert detect_platform("Bloodborne", drm="PSN") == "PlayStation"

    def test_gog(self):
        assert detect_platform("The Witcher 3 GOG Key") == "GOG"
        assert detect_platform("The Witcher 3", drm="GOG.com") == "GOG"

    def test_other_platforms(self):
        assert detect_platform("FIFA 23 EA App Origin") == "EA App"
        assert detect_platform("Assassin's Creed Ubisoft Connect") == "Ubisoft"
        assert detect_platform("Diablo IV Battle.net Key") == "Battle.net"


# ─────────────────────────────────────────────
# check_lot_validity
# ─────────────────────────────────────────────

class TestCheckLotValidity:

    def test_valid_ru_key(self):
        assert check_lot_validity("Resident Evil 4 Steam Key", "PC, Цифровой ключ, Россия")

    def test_valid_gift(self):
        assert check_lot_validity("Elden Ring Steam Gift RU", "гифт, PC")

    def test_reject_account(self):
        assert not check_lot_validity("Cyberpunk 2077 аккаунт", "PC")

    def test_reject_dlc(self):
        assert not check_lot_validity("Witcher 3 DLC Hearts of Stone", "PC, ключ")

    def test_reject_no_key_word(self):
        # strict_key_check=True (default) — без слова "ключ/gift/key" → отклонить
        assert not check_lot_validity("Hogwarts Legacy PC Russia", "PC, Russia")

    def test_accept_non_strict(self):
        # strict_key_check=False — без слова "ключ" всё равно проходит
        assert check_lot_validity("Hogwarts Legacy PC Russia", "PC, Russia", strict_key_check=False)

    def test_reject_hardware(self):
        assert not check_lot_validity("RTX 5090 Promo Key", "GPU, nvidia")

    def test_reject_shared_desc(self):
        assert not check_lot_validity("Game X", "общий аккаунт, без смены данных")


# ─────────────────────────────────────────────
# Проверка надежности продавцов (FunPay, GGSEL, Plati)
# ─────────────────────────────────────────────

class TestReliableSellerFilters:

    def test_funpay_seller_with_zero_reviews_rejected(self):
        html = """
        <div class="tc-item" data-online="1">
            <div class="tc-user">
                <div class="media-user-name">ScamBot</div>
                <div class="media-user-reviews">
                    <span class="rating-mini-count">0</span>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser").select_one(".tc-item")
        is_trusted, is_online = is_reliable_seller_funpay(soup, min_reviews=5)
        assert not is_trusted
        assert is_online

    def test_funpay_seller_with_few_reviews_rejected(self):
        html = """
        <div class="tc-item" data-online="0">
            <div class="tc-user">
                <div class="media-user-name">NewUser</div>
                <div class="media-user-reviews">
                    <span class="rating-mini-count">3</span>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser").select_one(".tc-item")
        is_trusted, is_online = is_reliable_seller_funpay(soup, min_reviews=5)
        assert not is_trusted
        assert not is_online

    def test_funpay_seller_with_bad_rating_rejected(self):
        html = """
        <div class="tc-item" data-online="1">
            <div class="tc-user">
                <div class="media-user-name">BadSeller</div>
                <div class="media-user-reviews">
                    <div class="rating-stars rating-2"></div>
                    <span class="rating-mini-count">50</span>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser").select_one(".tc-item")
        is_trusted, is_online = is_reliable_seller_funpay(soup, min_reviews=5)
        assert not is_trusted

    def test_funpay_trusted_seller_accepted(self):
        html = """
        <div class="tc-item" data-online="1">
            <div class="tc-user">
                <div class="media-user-name">ProGamer</div>
                <div class="media-user-reviews">
                    <div class="rating-stars rating-5"></div>
                    <span class="rating-mini-count">716</span>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser").select_one(".tc-item")
        is_trusted, is_online = is_reliable_seller_funpay(soup, min_reviews=5)
        assert is_trusted
        assert is_online

    def test_ggsel_seller_with_zero_sales_rejected(self):
        item = {"seller_name": "ZeroSales", "cnt_sell": 0, "rating": 5.0}
        assert not is_reliable_seller_ggsel(item, min_sales=5)

    def test_ggsel_seller_with_low_rating_rejected(self):
        item = {"seller_name": "LowRating", "cnt_sell": 50, "rating": 3.2}
        assert not is_reliable_seller_ggsel(item, min_sales=5, min_rating=4.0)

    def test_ggsel_trusted_seller_accepted(self):
        item = {"seller_name": "LegitMarket", "cnt_sell": 661, "rating": 5.0}
        assert is_reliable_seller_ggsel(item, min_sales=5, min_rating=4.0)

    def test_ggsel_seller_profile_few_sales_and_reviews_rejected(self):
        # Реальный кейс пользователя: 5 продаж, 1 отзыв, рейтинг 4.9
        item = {"seller_name": "NoviceSeller", "cnt_sell": 5, "rating": 4.9}
        seller_info = {
            "seller_id": 999999,
            "name": "NoviceSeller",
            "total_sales": 5,
            "good_reviews": 1,
            "bad_reviews": 0,
            "rating": 4.9,
            "registered": "2026-10-01",
        }
        assert not is_reliable_seller_ggsel(item, seller_info=seller_info)

    def test_ggsel_seller_profile_brand_new_account_rejected(self):
        # Продавец-однодневка, зарегистрирован несколько дней назад
        item = {"seller_name": "ZenithShield", "cnt_sell": 0, "rating": 5.0}
        seller_info = {
            "seller_id": 173739983,
            "name": "ZenithShield",
            "total_sales": 6,
            "good_reviews": 0,
            "bad_reviews": 0,
            "rating": 5.0,
            "registered": "2026-11-05",
        }
        assert not is_reliable_seller_ggsel(item, seller_info=seller_info)

    def test_ggsel_seller_profile_trusted_accepted(self):
        # Крупный проверенный продавец
        item = {"seller_name": "LegitMarket", "cnt_sell": 1, "rating": 4.9}
        seller_info = {
            "seller_id": 1261486,
            "name": "LegitMarket",
            "total_sales": 1116724,
            "good_reviews": 51871,
            "bad_reviews": 182,
            "rating": 4.9,
            "registered": "2024-02-06",
        }
        assert is_reliable_seller_ggsel(item, seller_info=seller_info)

    def test_plati_seller_with_zero_sales_rejected(self):
        item = {"seller_name": "Novoreg", "numsold": 0, "count_positiveresponses": 0, "count_negativeresponses": 0}
        assert not is_reliable_seller_plati(item, min_sales=5)

    def test_plati_seller_with_high_negative_ratio_rejected(self):
        item = {"seller_name": "ScamPlati", "numsold": 50, "count_positiveresponses": 30, "count_negativeresponses": 20}
        assert not is_reliable_seller_plati(item, min_sales=5, min_positive_ratio=0.90)

    def test_plati_trusted_seller_accepted(self):
        item = {"seller_name": "DarkAwe", "numsold": 1094, "count_positiveresponses": 221, "count_negativeresponses": 0}
        assert is_reliable_seller_plati(item, min_sales=5, min_positive_ratio=0.90)
