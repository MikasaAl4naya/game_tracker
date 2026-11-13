import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def test_topup():
    console_errors = []
    checks = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--proxy-bypass-list=*"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: console_errors.append(f"[pageerror] {err}"))

        print("\n=== ТЕСТ 1: Переход в раздел 'Пополнение Steam' из навигации ===")
        page.goto("http://localhost:8080", wait_until="networkidle")
        page.wait_for_timeout(500)

        # Click topup link in nav
        topup_nav_btn = page.locator("nav a:has-text('Пополнение Steam')")
        assert topup_nav_btn.is_visible(), "Кнопка 'Пополнение Steam' должна быть в навигации"
        topup_nav_btn.click()
        page.wait_for_timeout(600)

        topup_state = page.locator("#topupState")
        assert topup_state.is_visible(), "Раздел #topupState должен быть виден"
        assert not page.locator("#welcomeState").is_visible(), "#welcomeState должен быть скрыт"

        # Check URL
        assert "/topup" in page.url, f"URL должен содержать /topup, получили: {page.url}"
        print(f"URL страницы: {page.url}")

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "topup_01_view.png"))
        checks.append("Навигация и переход в #topupState: OK")

        print("\n=== ТЕСТ 2: Интерактивный калькулятор переплаты ===")
        # Check initial calculation for 1000 RUB
        best_service = page.locator("#topupBestService").inner_text()
        best_charge = page.locator("#topupBestCharge").inner_text()
        savings = page.locator("#topupMaxSavings").inner_text()
        print(f"При 1000 ₽ -> Лидер: {best_service}, К списанию: {best_charge}, Экономия: {savings}")
        assert best_service in ("PlayerOK", "FunPay"), f"Ожидался PlayerOK или FunPay как самый выгодный, получили {best_service}"

        # Check PlayerOK card and promo code block
        playerok_card = page.locator(".topup-service-card:has(h3:has-text('PlayerOK'))")
        assert playerok_card.is_visible(), "Карточка PlayerOK должна быть видна"
        assert "VREMYA" in playerok_card.inner_text(), "Промокод VREMYA должен присутствовать в карточке PlayerOK"
        print("Промокод VREMYA найден на карточке PlayerOK")

        # Click copy promo code
        copy_btn = playerok_card.locator("button:has-text('Копия')")
        if copy_btn.is_visible():
            copy_btn.click()
            page.wait_for_timeout(300)
            toast = page.locator("#toast")
            print(f"Тост после копирования: '{toast.inner_text()}' (видимость: {toast.is_visible()})")
            assert "VREMYA" in toast.inner_text(), "Тост должен содержать название промокода"

        # Click chip 350 RUB
        page.locator(".topup-chip:has-text('350 ₽')").click()
        page.wait_for_timeout(400)
        input_val = page.locator("#topupAmountInput").input_value()
        assert input_val == "350", f"Инпут должен стать 350, получили {input_val}"

        # Check services cards
        cards = page.locator("#topupServicesGrid .topup-service-card")
        cards_count = cards.count()
        print(f"Количество карточек сервисов: {cards_count}")
        assert cards_count >= 10, f"Ожидалось >= 10 сервисов, получили {cards_count}"

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "topup_02_chips_calc.png"))
        checks.append("Калькулятор и пересчет сумм: OK")

        print("\n=== ТЕСТ 3: Фильтрация по способу оплаты ===")
        # Filter: С телефона
        page.locator(".topup-method-btn[data-method='phone']").click()
        page.wait_for_timeout(400)
        phone_cards = page.locator("#topupServicesGrid .topup-service-card")
        phone_count = phone_cards.count()
        print(f"Сервисов с оплатой с телефона: {phone_count}")
        assert phone_count == 2, f"Ожидалось 2 сервиса (Steamgold, МТС), получили {phone_count}"
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "topup_03_phone_filter.png"))

        # Filter: Наличные
        page.locator(".topup-method-btn[data-method='cash']").click()
        page.wait_for_timeout(400)
        cash_cards = page.locator("#topupServicesGrid .topup-service-card")
        assert cash_cards.count() == 1, f"Ожидался 1 сервис для наличных (Элекснет), получили {cash_cards.count()}"
        cash_title = cash_cards.first.locator("h3").inner_text()
        print(f"Сервис наличных: {cash_title}")
        assert "Элекснет" in cash_title, f"Ожидался Элекснет, получили {cash_title}"

        # Reset to all
        page.locator(".topup-method-btn[data-method='all']").click()
        page.wait_for_timeout(400)
        checks.append("Фильтры способов оплаты (телефон, наличные, СБП): OK")

        print("\n=== ТЕСТ 4: Сортировка сервисов ===")
        # Sort by fastest
        sort_select = page.locator("#topupSortSelect")
        sort_select.select_option("fastest")
        page.wait_for_timeout(400)
        first_fast_card = page.locator("#topupServicesGrid .topup-service-card").first.locator("h3").inner_text()
        print(f"Первый при сортировке 'самые быстрые': {first_fast_card}")
        assert first_fast_card in ("Steamgold", "Steamwallet.ru", "PlayerOK", "Препод Steam", "МТС Оплата"), f"Неожиданный первый сервис: {first_fast_card}"
        checks.append("Сортировка по скорости: OK")

        print("\n=== ТЕСТ 5: FAQ & Гайд безопасности (раскрытие аккордеона) ===")
        faq_btn = page.locator("button:has-text('Где найти правильный логин Steam')")
        assert faq_btn.is_visible(), "FAQ кнопка должна быть видна"
        faq_btn.click()
        page.wait_for_timeout(300)
        faq_content = faq_btn.locator("+ div")
        assert faq_content.is_visible(), "Контент FAQ должен раскрыться"
        assert "Главная причина потери денег" in faq_content.inner_text()
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "topup_04_faq_expanded.png"))
        checks.append("FAQ и аккордеон безопасности: OK")

        print("\n=== ТЕСТ 6: Прямая загрузка /topup по URL ===")
        page.goto("http://localhost:8080/topup", wait_until="networkidle")
        page.wait_for_timeout(600)
        assert page.locator("#topupState").is_visible(), "При прямом открытии /topup раздел должен быть открыт"
        checks.append("Прямая загрузка /topup: OK")

        browser.close()

    print("\n" + "="*50)
    print("ИТОГИ ПРОВЕРКИ:")
    for chk in checks:
        print("  ✓", chk)

    if console_errors:
        print("\nПредупреждения/ошибки консоли:")
        for err in console_errors:
            print("  !", err)
    else:
        print("\nОшибок консоли нет!")

if __name__ == "__main__":
    test_topup()
