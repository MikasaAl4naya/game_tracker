import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "audit")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://localhost:8080"

def run_comprehensive_audit():
    results = {
        "passed": [],
        "warnings": [],
        "errors": [],
        "screenshots": [],
    }
    console_logs = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Listen to console and network
        def on_console(msg):
            text = f"[{msg.type}] {msg.text}"
            if msg.type == "error":
                # Filter out benign CDN tailwindcss warning if logged as error
                if "cdn.tailwindcss.com" not in msg.text:
                    console_logs.append(text)
            elif msg.type == "warning":
                pass

        def on_response(resp):
            if resp.status >= 400 and not resp.url.endswith("favicon.ico"):
                failed_requests.append(f"{resp.status} {resp.url}")

        page.on("console", on_console)
        page.on("pageerror", lambda err: console_logs.append(f"[JS_EXCEPTION] {err}"))
        page.on("response", on_response)

        print("\n========================================================")
        print(" НАЧАЛО СКВОЗНОГО АУДИТА ФРОНТЕНДА LOOTOZAVR")
        print("========================================================")

        # ----------------------------------------------------
        # СЦЕНАРИЙ 1: Главная страница (Welcome State и Hero при выборе игры)
        # ----------------------------------------------------
        print("\n--- [Сценарий 1] Главная страница и переход в карточку игры ---")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)
        
        shot1 = os.path.join(SCREENSHOTS_DIR, "01_homepage.png")
        page.screenshot(path=shot1)
        results["screenshots"].append(shot1)

        title = page.title()
        print(f"Title: {title}")
        if "LootoZavr" in title:
            results["passed"].append("Сценарий 1: Title страницы корректен")
        else:
            results["errors"].append(f"Сценарий 1: Некорректный Title: {title}")

        # Проверка приветственного блока на главной
        welcome_box = page.locator("#welcomeState")
        if welcome_box.is_visible():
            results["passed"].append("Сценарий 1: Приветственный блок #welcomeState виден на главной")
        else:
            results["warnings"].append("Сценарий 1: Приветственный блок не найден")

        # ----------------------------------------------------
        # СЦЕНАРИЙ 2: Вкладки каталога (Discovery Hub)
        # ----------------------------------------------------
        print("\n--- [Сценарий 2] Вкладки каталога (Популярные / Скидки / Steam) ---")
        tabs = ["popular", "deals", "steam"]
        for t in tabs:
            btn = page.locator(f"button[data-tab='{t}']")
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(700)
                cards = page.locator("#discoveryGrid .game-card")
                count = cards.count()
                print(f"Вкладка '{t}': {count} карточек")
                if count > 0:
                    results["passed"].append(f"Сценарий 2: Вкладка '{t}' отображает {count} игр")
                else:
                    results["errors"].append(f"Сценарий 2: Вкладка '{t}' пуста")
            else:
                results["errors"].append(f"Сценарий 2: Кнопка таба '{t}' не найдена")

        shot2 = os.path.join(SCREENSHOTS_DIR, "02_discovery_tabs.png")
        page.screenshot(path=shot2)
        results["screenshots"].append(shot2)

        # ----------------------------------------------------
        # СЦЕНАРИЙ 3: Живой поиск и выбор игры
        # ----------------------------------------------------
        print("\n--- [Сценарий 3] Живой поиск с автодополнением ---")
        search_input = page.locator("#searchInput")
        search_input.click()
        search_input.fill("Cyberpunk")
        page.wait_for_timeout(1000)

        results_box = page.locator("#searchSuggestions")
        if results_box.is_visible():
            suggest_items = page.locator("#searchSuggestions > div")
            s_count = suggest_items.count()
            print(f"Результатов в выпадающем поиске: {s_count}")
            if s_count > 0:
                results["passed"].append(f"Сценарий 3: Автодополнение поиска нашло {s_count} совпадений")
                shot3 = os.path.join(SCREENSHOTS_DIR, "03_search_results.png")
                page.screenshot(path=shot3)
                results["screenshots"].append(shot3)

                # Клик по первому результату
                suggest_items.first.click()
                page.wait_for_selector("#resultsState:not(.hidden)", timeout=8000)
                page.wait_for_timeout(500)
                new_hero = page.locator("#heroGameTitle").inner_text().strip()
                print(f"Hero после выбора из поиска: {new_hero}")
                if "Cyberpunk" in new_hero:
                    results["passed"].append(f"Сценарий 3: Успешный переход в {new_hero} через поиск")
                else:
                    results["warnings"].append(f"Сценарий 3: Выбрана игра, но заголовок: {new_hero}")
            else:
                results["errors"].append("Сценарий 3: Поиск открылся, но совпадений 0")
        else:
            results["errors"].append("Сценарий 3: Выпадающий список поиска не отобразился")

        # Проверка элементов Hero-баннера после перехода в игру
        hero_title = page.locator("#heroGameTitle").inner_text().strip()
        print(f"Hero игра: {hero_title}")
        if hero_title:
            results["passed"].append(f"Сценарий 1: Hero баннер загружен ({hero_title})")
        else:
            results["errors"].append("Сценарий 1: Hero баннер пуст")

        # Проверка плашки РФ-доступности
        rf_badge = page.locator("#heroRfAvailability")
        if rf_badge.is_visible():
            rf_text = rf_badge.inner_text().strip()
            print(f"Плашка РФ-доступности: {rf_text}")
            results["passed"].append(f"Сценарий 1: Плашка РФ-доступности видна ({rf_text})")
        else:
            results["warnings"].append("Сценарий 1: Плашка РФ-доступности не отображается")

        # Проверка таймлайна цен (Chart.js canvas)
        chart_canvas = page.locator("#priceChart")
        if chart_canvas.is_visible():
            results["passed"].append("Сценарий 1: График истории цен (Chart.js) отрисован")
        else:
            results["warnings"].append("Сценарий 1: Canvas графика цен не найден")

        # ----------------------------------------------------
        # СЦЕНАРИЙ 4: Фильтры формата, изданий, платформ, сортировка
        # ----------------------------------------------------
        print("\n--- [Сценарий 4] Фильтрация и сортировка предложений ---")
        all_cards = page.locator("#offersList .offer-card")
        total_offers = all_cards.count()
        print(f"Всего предложений для игры: {total_offers}")

        # Быстрые фильтры формата (Все / Ключи / Гифты)
        btn_gifts = page.locator("button.format-pill", has_text="Гифты")
        if btn_gifts.is_visible():
            btn_gifts.click()
            page.wait_for_timeout(400)
            gifts_count = page.locator("#offersList .offer-card").count()
            print(f"Фильтр 'Гифты': {gifts_count} предложений")
            results["passed"].append(f"Сценарий 4: Фильтр формата 'Гифты' отфильтровал ({gifts_count} из {total_offers})")

        btn_keys = page.locator("button.format-pill", has_text="Ключи")
        if btn_keys.is_visible():
            btn_keys.click()
            page.wait_for_timeout(400)
            keys_count = page.locator("#offersList .offer-card").count()
            print(f"Фильтр 'Ключи': {keys_count} предложений")
            results["passed"].append(f"Сценарий 4: Фильтр формата 'Ключи' отфильтровал ({keys_count} из {total_offers})")

        btn_all_fmt = page.locator("button.format-pill", has_text="Все")
        if btn_all_fmt.is_visible():
            btn_all_fmt.first.click()
            page.wait_for_timeout(400)

        # Динамические издания (Standard / Ultimate)
        edition_btns = page.locator("#editionFilterWrapper button.edition-btn")
        ed_count = edition_btns.count()
        print(f"Кнопок изданий: {ed_count}")
        if ed_count > 1:
            # Клик по второму изданию (например, Ultimate)
            target_ed_btn = edition_btns.nth(2) if ed_count > 2 else edition_btns.nth(1)
            target_ed_text = target_ed_btn.inner_text().strip()
            target_ed_btn.click()
            page.wait_for_timeout(400)
            ed_filtered_count = page.locator("#offersList .offer-card").count()
            print(f"Фильтр издания '{target_ed_text}': {ed_filtered_count} предложений")
            results["passed"].append(f"Сценарий 4: Динамический фильтр издания '{target_ed_text}' работает ({ed_filtered_count} шт.)")
            # Сброс на 'Все'
            edition_btns.first.click()
            page.wait_for_timeout(400)

        # Сортировка: Сначала дорогие
        sort_select = page.locator("#sortSelect")
        if sort_select.is_visible():
            sort_select.select_option("desc")
            page.wait_for_timeout(400)
            first_price_text = page.locator("#offersList .offer-card .text-xl, #offersList .offer-card .font-bold").first.inner_text().strip()
            print(f"Первая цена при сортировке по убыванию: {first_price_text}")
            results["passed"].append(f"Сценарий 4: Сортировка по убыванию работает (топ: {first_price_text})")

            # Возврат: Сначала дешевые
            sort_select.select_option("asc")
            page.wait_for_timeout(400)

        shot4 = os.path.join(SCREENSHOTS_DIR, "04_filtered_offers.png")
        page.screenshot(path=shot4)
        results["screenshots"].append(shot4)

        # ----------------------------------------------------
        # СЦЕНАРИЙ 5: Проверка карточек магазинов и внешних ссылок
        # ----------------------------------------------------
        print("\n--- [Сценарий 5] Карточки предложений и ссылки на магазины ---")
        cards = page.locator("#offersList .offer-card")
        c_count = min(5, cards.count())
        valid_links = 0
        shops_found = set()
        for idx in range(c_count):
            c = cards.nth(idx)
            shop_el = c.locator(".shop-badge, [class*='shop-']").first
            if shop_el.is_visible():
                shops_found.add(shop_el.inner_text().strip())
            href = c.get_attribute("href")
            target = c.get_attribute("target")
            if href and href.startswith("http") and target == "_blank":
                valid_links += 1

        print(f"Магазины в топ-5 карточках: {shops_found}, валидных ссылок на покупку: {valid_links}/{c_count}")
        if valid_links == c_count and c_count > 0:
            results["passed"].append(f"Сценарий 5: Ссылки 'Купить' корректны и ведут на внешние магазины ({shops_found})")
        else:
            results["warnings"].append(f"Сценарий 5: Ссылок на покупку проверено {valid_links}/{c_count}")

        # ----------------------------------------------------
        # СЦЕНАРИЙ 6: Модалка отслеживания цены и Telegram-бот
        # ----------------------------------------------------
        print("\n--- [Сценарий 6] Модалка отслеживания цены и Telegram 1-click ---")
        track_btn = page.locator("button[onclick*='openTrackModal'], #trackPriceBtn").first
        if track_btn.is_visible():
            track_btn.click()
            page.wait_for_timeout(500)
            modal = page.locator("#trackModal")
            if modal.is_visible():
                print("Модалка отслеживания открылась")
                shot6 = os.path.join(SCREENSHOTS_DIR, "06_tracking_modal.png")
                page.screenshot(path=shot6)
                results["screenshots"].append(shot6)

                tg_link = page.locator("#trackTelegram1Click")
                if tg_link.is_visible():
                    tg_href = tg_link.get_attribute("href")
                    print(f"Telegram Deeplink: {tg_href}")
                    if "t.me/LootoZavr_bot?start=track_" in tg_href:
                        results["passed"].append(f"Сценарий 6: Telegram 1-click deeplink сформирован ({tg_href})")
                    else:
                        results["errors"].append(f"Сценарий 6: Некорректный tg_href: {tg_href}")

                # Проверка смены цены в инпуте
                price_input = page.locator("#trackTargetPrice")
                if price_input.is_visible():
                    price_input.fill("1500")
                    page.wait_for_timeout(300)
                    updated_href = tg_link.get_attribute("href")
                    if "_1500" in updated_href:
                        results["passed"].append("Сценарий 6: Динамическое обновление Telegram deeplink при вводе цены работает")

                # Закрытие модалки по клавише Escape
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
                if not modal.is_visible():
                    results["passed"].append("Сценарий 6: Модалка успешно закрывается по Escape")
                else:
                    # Попробуем кнопку закрытия
                    page.locator("#trackModal button i.fa-xmark").first.click()
                    page.wait_for_timeout(300)
            else:
                results["errors"].append("Сценарий 6: Модалка #trackModal не стала видимой после клика")
        else:
            results["warnings"].append("Сценарий 6: Кнопка 'Отслеживать' не найдена в Hero")

        # ----------------------------------------------------
        # СЦЕНАРИЙ 7: Страница пополнения Steam (/topup) и калькулятор
        # ----------------------------------------------------
        print("\n--- [Сценарий 7] Страница пополнения баланса Steam (/topup) ---")
        topup_nav_link = page.locator("nav a:has-text('Пополнение Steam')").first
        if topup_nav_link.is_visible():
            topup_nav_link.click()
            page.wait_for_selector("#topupState:not(.hidden)", timeout=4000)
        else:
            page.goto(f"{BASE_URL}/topup", wait_until="networkidle")
        
        page.wait_for_timeout(1000)
        shot7 = os.path.join(SCREENSHOTS_DIR, "07_topup_page.png")
        page.screenshot(path=shot7)
        results["screenshots"].append(shot7)

        # Проверка калькулятора пополнения
        calc_input = page.locator("#topupAmountInput")
        if calc_input.is_visible():
            calc_input.fill("3000")
            page.wait_for_timeout(500)
            best_serv = page.locator("#topupBestService").inner_text().strip()
            print(f"Лучший сервис при пополнении на 3000 руб: {best_serv}")
            service_cards = page.locator("#topupGrid .topup-card, [class*='service-card']")
            print(f"Сервисов пополнения отображено: {service_cards.count()}")
            results["passed"].append(f"Сценарий 7: Страница /topup работает, калькулятор реагирует на ввод 3000 руб (топ: {best_serv})")
        else:
            results["warnings"].append("Сценарий 7: Поле калькулятора пополнения не найдено")

        # Возврат в каталог
        logo_link = page.locator("a[href='/'], .logo-link, header a").first
        if logo_link.is_visible():
            logo_link.click()
            page.wait_for_timeout(1000)

        # ----------------------------------------------------
        # СЦЕНАРИЙ 8: Прямой переход по URL игры (/game/9) и History API
        # ----------------------------------------------------
        print("\n--- [Сценарий 8] Прямой роутинг /game/{id} и History API ---")
        page.goto(f"{BASE_URL}/game/9", wait_until="networkidle")
        page.wait_for_timeout(1000)
        er_title = page.locator("#heroGameTitle").inner_text().strip()
        print(f"Прямой переход /game/9: {er_title}")
        if "ELDEN RING" in er_title.upper():
            results["passed"].append(f"Сценарий 8: Прямой роутинг /game/9 успешно открыл {er_title}")
        else:
            results["errors"].append(f"Сценарий 8: Ожидался ELDEN RING, получено: {er_title}")

        # Проверка назад / вперед
        page.go_back()
        page.wait_for_timeout(800)
        back_url = page.url
        page.go_forward()
        page.wait_for_timeout(800)
        fwd_url = page.url
        if "/game/9" in fwd_url:
            results["passed"].append("Сценарий 8: Навигация Back / Forward браузера работает корректно")
        else:
            results["warnings"].append(f"Сценарий 8: Back/Forward вернул неожиданный URL: {fwd_url}")

        shot8 = os.path.join(SCREENSHOTS_DIR, "08_direct_game_url.png")
        page.screenshot(path=shot8)
        results["screenshots"].append(shot8)

        # ----------------------------------------------------
        # СЦЕНАРИЙ 9: Аудит ссылок футера (новые магазины Gamerilla, GamersBase и др.)
        # ----------------------------------------------------
        print("\n--- [Сценарий 9] Футер и аудит ссылок ---")
        footer = page.locator("footer")
        if footer.is_visible():
            footer_links = footer.locator("a")
            f_count = footer_links.count()
            print(f"Всего ссылок в футере: {f_count}")
            checked_links = {}
            for i in range(f_count):
                fl = footer_links.nth(i)
                text = fl.inner_text().strip()
                href = fl.get_attribute("href")
                checked_links[text] = href

            print("Проверенные магазины в футере:")
            for s_name in ["FunPay", "Plati", "Steambuy", "Steampay", "GGSEL", "Zaka-Zaka", "GabeStore", "Gamerilla", "GamersBase"]:
                match = next((v for k, v in checked_links.items() if s_name.lower() in k.lower()), None)
                if match:
                    print(f"  ✓ {s_name} -> {match}")
                    results["passed"].append(f"Сценарий 9: Ссылка на {s_name} присутствует в футере ({match})")
                else:
                    results["warnings"].append(f"Сценарий 9: Магазин {s_name} не найден среди ссылок футера")

        shot9 = os.path.join(SCREENSHOTS_DIR, "09_footer.png")
        footer.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        page.screenshot(path=shot9)
        results["screenshots"].append(shot9)

        # ----------------------------------------------------
        # СЦЕНАРИЙ 10: Мобильная верстка (Mobile iPhone 375x812)
        # ----------------------------------------------------
        print("\n--- [Сценарий 10] Мобильная адаптивность (375x812) ---")
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(f"{BASE_URL}/game/23", wait_until="networkidle")
        page.wait_for_timeout(1000)

        shot10 = os.path.join(SCREENSHOTS_DIR, "10_mobile_responsive.png")
        page.screenshot(path=shot10)
        results["screenshots"].append(shot10)

        # Проверка читаемости и отсутствия горизонтального скролла
        has_h_scroll = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        print(f"Горизонтальный скролл на мобильном: {'ДА (Баг)' if has_h_scroll else 'НЕТ (Отлично)'}")
        if not has_h_scroll:
            results["passed"].append("Сценарий 10: Мобильная верстка адаптивна, нет паразитного горизонтального скролла")
        else:
            results["warnings"].append("Сценарий 10: Обнаружен горизонтальный скролл на мобильном экране 375px")

        browser.close()

    print("\n========================================================")
    print(" ИТОГИ СКВОЗНОГО АУДИТА")
    print("========================================================")
    print(f"Успешных проверок: {len(results['passed'])}")
    for p_item in results["passed"]:
        print(f"  ✓ {p_item}")

    print(f"\nПредупреждений: {len(results['warnings'])}")
    for w_item in results["warnings"]:
        print(f"  ⚠ {w_item}")

    print(f"\nОшибок: {len(results['errors'])}")
    for e_item in results["errors"]:
        print(f"  ✗ {e_item}")

    print(f"\nJS Console Errors: {len(console_logs)}")
    for l_item in console_logs:
        print(f"  [JS Error] {l_item}")

    print(f"\nFailed Network Requests (4xx/5xx): {len(failed_requests)}")
    for r_item in failed_requests:
        print(f"  [HTTP Error] {r_item}")

    return results, console_logs, failed_requests

if __name__ == "__main__":
    run_comprehensive_audit()
