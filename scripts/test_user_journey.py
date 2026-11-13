import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def run_user_journey():
    console_errors = []
    issues_found = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Capture console errors
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: console_errors.append(f"[pageerror] {err}"))

        print("\n--- 1. Заход на главную страницу ---")
        page.goto("http://localhost:8080", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_homepage.png"))
        print(f"Заголовок страницы: {page.title()}")

        # Check search input
        search_input = page.locator("#searchInput")
        if not search_input.is_visible():
            issues_found.append("Поле поиска #searchInput не видимо")

        # Check discovery tabs
        print("\n--- 2. Проверка Discovery Hub и переключение вкладок ---")
        tabs = page.locator(".discovery-tab")
        tab_count = tabs.count()
        print(f"Найдено вкладок: {tab_count}")
        for i in range(tab_count):
            print(f"  Вкладка {i}: {tabs.nth(i).inner_text().strip()}")

        # Tab 1: Популярные игры
        cards_pop = page.locator("#discoveryGrid .game-card")
        cards_pop_count = cards_pop.count()
        print(f"Карточек в 'Популярные': {cards_pop_count}")
        if cards_pop_count == 0:
            issues_found.append("Вкладка 'Популярные' пуста")
        else:
            first_game = cards_pop.nth(0).locator("p").inner_text()
            print(f"Первая игра в 'Популярные': {first_game}")

        # Tab 2: Скидки
        print("Переключаем на 'Лучшие скидки'...")
        page.click("button[data-tab='deals']")
        page.wait_for_timeout(1200)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_tab_deals.png"))
        cards_deals = page.locator("#discoveryGrid .game-card")
        print(f"Карточек в 'Лучшие скидки': {cards_deals.count()}")
        if cards_deals.count() == 0:
            issues_found.append("Вкладка 'Лучшие скидки' пуста")
        else:
            print(f"Первая игра в 'Скидки': {cards_deals.nth(0).locator('p').inner_text()} ({cards_deals.nth(0).locator('.text-deal').last.inner_text()})")

        # Tab 3: Топ Steam
        print("Переключаем на 'Топ Steam'...")
        page.click("button[data-tab='steam']")
        page.wait_for_timeout(1200)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_tab_steam.png"))
        cards_steam = page.locator("#discoveryGrid .game-card")
        print(f"Карточек в 'Топ Steam': {cards_steam.count()}")
        if cards_steam.count() == 0:
            issues_found.append("Вкладка 'Топ Steam' пуста")
        else:
            sample_steam_titles = [cards_steam.nth(k).locator("p").inner_text() for k in range(min(5, cards_steam.count()))]
            print(f"Первые игры в 'Топ Steam': {sample_steam_titles}")

        # 3. Клик на игру в каталоге
        print("\n--- 3. Переход в карточку игры (клик по ELDEN RING) ---")
        # Go back to popular and find Elden ring or click first
        page.click("button[data-tab='popular']")
        page.wait_for_timeout(500)
        
        # Look for ELDEN RING card or click first card
        elden_card = page.locator("#discoveryGrid .game-card", has_text="ELDEN RING").first
        if elden_card.is_visible():
            elden_card.click()
        else:
            page.locator("#discoveryGrid .game-card").first.click()

        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_game_page_hero.png"))

        # Verify Hero Banner
        hero_title = page.locator("#heroGameTitle").inner_text()
        print(f"Заголовок в Hero баннере: {hero_title}")
        hero_offers = page.locator("#heroOffersCount").inner_text()
        print(f"Счётчик предложений в баннере: {hero_offers}")

        # Test "Поделиться" button
        share_btn = page.locator("button:has-text('Поделиться')").first
        if share_btn.is_visible():
            share_btn.click()
            page.wait_for_timeout(400)
            toast = page.locator("#toast")
            print(f"Тост виден: {toast.is_visible()}, текст: {page.locator('#toastMsg').inner_text()}")

        # Check Best Deal Box
        deal_box = page.locator("#heroBestDealBox")
        print(f"Блок 'Лучшая сделка' виден: {deal_box.is_visible()}")
        if deal_box.is_visible():
            print(f"  Магазин лучшей цены: {page.locator('#heroDealShop').inner_text()}")
            print(f"  Цена: {page.locator('#heroDealPrice').inner_text()}")
            print(f"  Ссылка: {page.locator('#heroDealButton').get_attribute('href')}")

        # Check Steam prices & Chart in Sidebar
        steam_official = page.locator("#steamPrices").inner_text()
        print(f"Steam официальные цены:\n{steam_official}")
        
        # Check Offer Cards
        offer_cards = page.locator("#offersList .offer-card")
        offer_count = offer_cards.count()
        print(f"\nНайдено карточек предложений в списке: {offer_count}")
        if offer_count == 0:
            issues_found.append("Список предложений пуст!")
        else:
            first_offer = offer_cards.nth(0)
            print(f"  Топ-1 предложение текст: {first_offer.locator('p').inner_text()}")
            print(f"  Цена: {first_offer.locator('.price-num').inner_text()}")

        # 4. Проверка фильтров платформ
        print("\n--- 4. Тестирование фильтров платформ ---")
        platforms = ["Steam", "Epic Games", "Xbox", "PlayStation", "GOG"]
        for plat in platforms:
            btn = page.locator(f".platform-btn:has-text('{plat}')")
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(300)
                filtered_cnt = page.locator("#offersList .offer-card").count()
                print(f"  Фильтр '{plat}': {filtered_cnt} предложений")

        # Reset platform filter to 'Все'
        page.locator(".platform-btn:has-text('Все')").click()
        page.wait_for_timeout(300)

        # 5. Проверка фильтров регионов
        print("\n--- 5. Тестирование фильтров регионов ---")
        regions = ["Global", "RU", "CIS", "TR"]
        for reg in regions:
            btn = page.locator(f".region-btn:has-text('{reg}')")
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(300)
                filtered_cnt = page.locator("#offersList .offer-card").count()
                print(f"  Фильтр '{reg}': {filtered_cnt} предложений")

        page.locator(".region-btn:has-text('Все')").click()
        page.wait_for_timeout(300)

        # 6. Проверка модального окна отслеживания цены
        print("\n--- 6. Тестирование модалки 'Отслеживать цену' ---")
        track_btn = page.locator("button:has-text('Отслеживать цену')").first
        track_btn.click()
        page.wait_for_timeout(500)
        modal = page.locator("#trackModal")
        print(f"Модалка открыта: {modal.is_visible()}")
        print(f"  Поле игры: {page.locator('#trackGameName').input_value()}")
        print(f"  Поле желаемой цены: {page.locator('#trackTargetPrice').input_value()}")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_track_modal.png"))
        
        # Close modal
        page.locator("#trackModal button").first.click()
        page.wait_for_timeout(400)
        print(f"Модалка закрыта: {not modal.is_visible()}")

        # 7. Проверка живого поиска с автокомплитом
        print("\n--- 7. Тестирование поиска с подсказками ---")
        search_input.fill("Cyberpunk")
        page.wait_for_timeout(600)
        suggestions = page.locator("#searchSuggestions > div")
        sug_count = suggestions.count()
        print(f"Найдено подсказок по 'Cyberpunk': {sug_count}")
        for s in range(min(4, sug_count)):
            print(f"  Подсказка: {suggestions.nth(s).inner_text().strip()}")
        
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_search_suggestions.png"))
        if sug_count > 0:
            suggestions.first.click()
            page.wait_for_selector("#resultsState:not(.hidden)", timeout=10000)
            page.wait_for_timeout(2000)
            print(f"Перешли по подсказке в: {page.locator('#heroGameTitle').inner_text()}")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06b_cyberpunk_loaded.png"))

        # 8. Возврат на главную
        print("\n--- 8. Возврат на главную по логотипу ---")
        page.click("a:has-text('LootoZavr')")
        page.wait_for_timeout(1000)
        print(f"Главная открыта: {page.locator('#welcomeState').is_visible()}")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_back_to_home.png"))

        browser.close()

    print("\n================ РЕЗЮМЕ ТЕСТА ================")
    print(f"Консольных ошибок/предупреждений: {len(console_errors)}")
    for err in console_errors:
        print(f"  {err}")
    print(f"Обнаружено критических проблем: {len(issues_found)}")
    for iss in issues_found:
        print(f"  ⚠️ {iss}")

if __name__ == "__main__":
    run_user_journey()
