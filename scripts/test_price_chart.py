import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8080"
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def test_price_chart():
    console_errors = []
    print("==========================================")
    print(" ТЕСТИРОВАНИЕ ИНТЕРАКТИВНОГО ГРАФИКА ЦЕН")
    print("==========================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("\n[Шаг 1] Открытие страницы игры Helldivers 2 (/game/8)...")
        page.goto(f"{BASE_URL}/game/8", wait_until="domcontentloaded", timeout=20000)

        print("[Шаг 2] Ожидание загрузки аналитики и предложений...")
        page.wait_for_selector("#priceAnalyticsSection:not(.hidden)", timeout=10000)
        page.wait_for_selector("#fullPriceChart", timeout=5000)

        # Проверяем KPI карточки
        atl_price = page.locator("#kpiAtlPrice").inner_text()
        curr_price = page.locator("#kpiCurrPrice").inner_text()
        avg_price = page.locator("#kpiAvgPrice").inner_text()
        print(f"  -> KPI Ист. минимум: {atl_price}")
        print(f"  -> KPI Текущая лучшая: {curr_price}")
        print(f"  -> KPI Средняя по рынку: {avg_price}")

        assert len(atl_price) > 0 and atl_price != "—", "Исторический минимум должен быть рассчитан"
        assert len(curr_price) > 0 and curr_price != "—", "Текущая лучшая цена должна быть рассчитана"

        # Проверяем клики по переключателям
        print("\n[Шаг 3] Тестирование переключения метрики (Средняя vs Мин)...")
        page.click("#chartMetricAvg")
        time.sleep(0.5)

        print("[Шаг 4] Тестирование переключения периода (7 дней / 30 дней)...")
        page.click("#chartRange7")
        time.sleep(0.5)
        page.click("#chartRangeAll")
        time.sleep(0.5)

        # Скриншот
        screenshot_path = os.path.join(SCREENSHOTS_DIR, "price_chart_verified.png")
        page.screenshot(path=screenshot_path)
        print(f"  -> Скриншот сохранен: {screenshot_path}")

        print("\n[Шаг 5] Проверка консоли JS...")
        filtered_errors = [e for e in console_errors if not any(ign in e for ign in ["favicon.ico", "ERR_ABORTED", "net::ERR"])]
        if filtered_errors:
            print(f"  -> ✗ Ошибки JS: {filtered_errors}")
            browser.close()
            return False
        else:
            print("  -> ✓ 0 ошибок в консоли JS")

        browser.close()

    print("\n✓ График истории цен и аналитика успешно работают!")
    return True

if __name__ == "__main__":
    ok = test_price_chart()
    sys.exit(0 if ok else 1)
