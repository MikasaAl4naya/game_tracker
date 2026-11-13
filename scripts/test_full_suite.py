import os
import sys
import time
from playwright.sync_api import sync_playwright

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://localhost:8080"
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "full_suite")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def run_full_suite():
    results = {
        "passed": [],
        "errors": [],
        "warnings": [],
    }
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error" and "cdn.tailwindcss.com" not in msg.text and "net::ERR_" not in msg.text:
                console_errors.append(f"[{msg.type}] {msg.text}")

        page.on("console", on_console)

        print("\n==========================================")
        print(" ЗАПУСК ПОЛНОГО ТЕСТОВОГО СЬЮТА LOOTOZAVR")
        print("==========================================")

        # ----------------------------------------------------
        # БЛОК 1: Главная страница и вкладка «Скидки» с процентами
        # ----------------------------------------------------
        try:
            print("\n[Проверка 1] Переход на главную и проверка вкладки Скидки...")
            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_selector("#welcomeState:not(.hidden)", timeout=5000)

            # Переключаемся на вкладку "Скидки"
            deals_tab = page.locator(".discovery-tab[data-tab='deals']")
            deals_tab.click()
            time.sleep(1)

            # Проверяем наличие плашек со скидками вида "🔥 -XX%"
            discount_badges = page.locator("#discoveryGrid .game-card span:has-text('🔥 -')")
            badge_count = discount_badges.count()
            assert badge_count >= 5, f"Ожидалось минимум 5 плашек с процентом скидки, найдено: {badge_count}"

            first_badge_text = discount_badges.first.inner_text()
            assert "%" in first_badge_text, f"Бейдж должен содержать знак %, получено: {first_badge_text}"

            # Проверяем зачеркнутую старую цену
            crossed_prices = page.locator("#discoveryGrid .game-card .line-through")
            assert crossed_prices.count() >= 5, "Ожидались зачеркнутые старые цены на карточках скидок"

            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "deals_tab_with_percentages.png"))
            results["passed"].append(f"Проверка 1: Вкладка Скидки отображает процент скидки ({first_badge_text}) и зачеркнутую цену")
            print(f"  -> Успешно: {badge_count} карточек с бейджами скидок ({first_badge_text})")
        except Exception as e:
            results["errors"].append(f"Проверка 1 Провалена: {e}")
            print(f"  -> Ошибка: {e}")

        # ----------------------------------------------------
        # БЛОК 2: Единый живой поиск (Донат + Ключи)
        # ----------------------------------------------------
        try:
            print("\n[Проверка 2] Единый поиск по донат-игре (Genshin)...")
            search_input = page.locator("#searchInput")
            search_input.fill("Genshin")
            page.wait_for_selector("#searchSuggestions:not(.hidden)", timeout=4000)

            # Проверяем, что в подсказках есть бейдж "💎 Донат"
            donate_suggestion = page.locator("#searchSuggestions div:has-text('Донат')")
            assert donate_suggestion.count() > 0, "Подсказка с донатом не найдена при поиске 'Genshin'"

            donate_item = donate_suggestion.first
            donate_item.click()
            time.sleep(1.5)

            # Проверяем, что мы перешли в раздел доната с выбранным Genshin Impact
            assert "/donate/genshin-impact" in page.url or "/donate" in page.url, f"URL должен вести в донат, got: {page.url}"
            assert page.locator("#donateState:not(.hidden)").is_visible(), "#donateState должен быть открыт"
            assert "Genshin Impact" in page.locator("#donateGameTitle").inner_text()

            results["passed"].append("Проверка 2: Поиск 'Genshin' выдал подсказку с бейджем '💎 Донат' и открыл раздел доната")
            print("  -> Успешно: подсказка доната найдена и открыта")
        except Exception as e:
            results["errors"].append(f"Проверка 2 Провалена: {e}")
            print(f"  -> Ошибка: {e}")

        # ----------------------------------------------------
        # БЛОК 3: Поиск цифрового ключа Steam (Cyberpunk 2077)
        # ----------------------------------------------------
        try:
            print("\n[Проверка 3] Поиск игры Steam (Cyberpunk)...")
            search_input = page.locator("#searchInput")
            search_input.fill("Cyberpunk")
            page.wait_for_selector("#searchSuggestions:not(.hidden)", timeout=4000)

            cyber_suggestion = page.locator("#searchSuggestions div:has-text('Cyberpunk 2077')").first
            assert cyber_suggestion.is_visible(), "Подсказка Cyberpunk 2077 не найдена"
            cyber_suggestion.click()
            time.sleep(2)

            page.wait_for_selector("#resultsState:not(.hidden)", timeout=5000)
            assert "Cyberpunk 2077" in page.locator("#heroGameTitle").inner_text()
            assert page.locator(".offer-card").count() > 0, "Предложения магазинов для Cyberpunk должны быть отрисованы"

            results["passed"].append("Проверка 3: Поиск 'Cyberpunk' нашел игру Steam и отобразил предложения магазинов")
            print("  -> Успешно")
        except Exception as e:
            results["errors"].append(f"Проверка 3 Провалена: {e}")
            print(f"  -> Ошибка: {e}")

        # ----------------------------------------------------
        # БЛОК 4: Раздел доната: переключение игр, пакеты и защита UID
        # ----------------------------------------------------
        try:
            print("\n[Проверка 4] Раздел доната: переключение на Brawl Stars и фильтр UID...")
            page.goto(f"{BASE_URL}/donate", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_selector("#donateState:not(.hidden)", timeout=5000)

            # Переключаем на Brawl Stars
            page.locator("#donateGamesChips .donate-game-chip:has-text('Brawl Stars')").click()
            time.sleep(1)
            assert "Brawl Stars" in page.locator("#donateGameTitle").inner_text()

            # Переключаем на Roblox
            page.locator("#donateGamesChips .donate-game-chip:has-text('Roblox')").click()
            time.sleep(1)
            assert "Roblox" in page.locator("#donateGameTitle").inner_text()
            assert "Робуксы" in page.locator("#donateGameCurrency").inner_text()

            # Копирование промокода
            copy_btn = page.locator("#donateGameBanner button:has-text('Копировать')")
            copy_btn.click()
            time.sleep(0.5)
            toast_text = page.locator("#toastMsg").inner_text()
            assert "LOOTOZAVR" in toast_text, f"Toast должен содержать LOOTOZAVR, got: {toast_text}"

            results["passed"].append("Проверка 4: Раздел доната (Brawl Stars, Roblox, копирование промокода LOOTOZAVR)")
            print("  -> Успешно")
        except Exception as e:
            results["errors"].append(f"Проверка 4 Провалена: {e}")
            print(f"  -> Ошибка: {e}")

        # ----------------------------------------------------
        # БЛОК 5: Калькулятор пополнения баланса Steam (/topup)
        # ----------------------------------------------------
        try:
            print("\n[Проверка 5] Страница пополнения Steam (/topup)...")
            page.goto(f"{BASE_URL}/topup", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_selector("#topupState:not(.hidden)", timeout=10000)

            topup_input = page.locator("#topupAmountInput")
            topup_input.fill("2000")
            time.sleep(0.5)

            best_service = page.locator("#topupBestService").inner_text()
            assert len(best_service) > 0, "Лучший сервис должен быть определен"
            assert page.locator(".topup-service-card").count() >= 10, "Должно отображаться от 10 сервисов"

            results["passed"].append(f"Проверка 5: Страница /topup работает корректно (топ: {best_service})")
            print(f"  -> Успешно (топ: {best_service})")
        except Exception as e:
            results["errors"].append(f"Проверка 5 Провалена: {e}")
            print(f"  -> Ошибка: {e}")

        # ----------------------------------------------------
        # БЛОК 6: Мобильная адаптивность на 375x812 (iPhone X/13/15)
        # ----------------------------------------------------
        try:
            print("\n[Проверка 6] Мобильная адаптивность (375x812)...")
            page.set_viewport_size({"width": 375, "height": 812})

            # Проверяем все 3 главных страницы на отсутствие горизонтального скролла
            pages_to_check = ["/", "/topup", "/donate/genshin-impact"]
            for path in pages_to_check:
                page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=20000)
                time.sleep(0.5)
                scroll_w = page.evaluate("document.documentElement.scrollWidth")
                client_w = page.evaluate("document.documentElement.clientWidth")
                assert scroll_w <= client_w + 1, f"Горизонтальный скролл на {path}: scrollWidth={scroll_w}, clientWidth={client_w}"

            screenshot_path = os.path.join(SCREENSHOTS_DIR, "mobile_donate_verified.png")
            page.screenshot(path=screenshot_path)

            results["passed"].append("Проверка 6: Полная мобильная адаптивность на 375px без горизонтального скролла")
            print("  -> Успешно: 0 горизонтальных скроллов на всех разделах")
        except Exception as e:
            results["errors"].append(f"Проверка 6 Провалена: {e}")
            print(f"  -> Ошибка: {e}")

        # ----------------------------------------------------
        # БЛОК 7: Проверка консоли JavaScript
        # ----------------------------------------------------
        print("\n[Проверка 7] Проверка ошибок в консоли JavaScript...")
        if len(console_errors) == 0:
            results["passed"].append("Проверка 7: 0 ошибок в консоли JavaScript браузера")
            print("  -> Успешно: 0 JS ошибок")
        else:
            results["errors"].append(f"Проверка 7 Провалена: Ошибки JS: {console_errors}")
            print(f"  -> Ошибка: {console_errors}")

        browser.close()

    print("\n==========================================")
    print(" ИТОГИ ПОЛНОГО ТЕСТОВОГО СЬЮТА")
    print("==========================================")
    print(f"ПРОЙДЕНО ПРОВЕРОК: {len(results['passed'])}")
    print(f"ОШИБОК: {len(results['errors'])}")
    for p in results["passed"]:
        print(f"  ✓ {p}")
    for err in results["errors"]:
        print(f"  ✗ {err}")

    return len(results["errors"]) == 0


if __name__ == "__main__":
    ok = run_full_suite()
    sys.exit(0 if ok else 1)
