import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def test_dynamic_editions():
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--proxy-bypass-list=*"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("\n=== ТЕСТ 1: Elden Ring (id 9) - Проверка скрытия фильтра изданий ===")
        page.goto("http://localhost:8080/game/9", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Check Elden Ring title
        title = page.locator("#gameTitle").inner_text()
        print(f"Открыта игра: {title}")
        assert "ELDEN RING" in title.upper(), f"Ожидался ELDEN RING, получили {title}"

        # In Elden Ring, all offers are Standard -> edition filter wrapper should be hidden!
        edition_wrapper = page.locator("#editionFilterWrapper")
        is_hidden = "hidden" in (edition_wrapper.get_attribute("class") or "")
        print(f"Elden Ring: фильтр изданий скрыт: {is_hidden}")
        assert is_hidden, "Для Elden Ring (где только базовое издание) фильтр изданий должен быть скрыт!"
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "edition_01_elden_ring.png"))
        checks.append("Elden Ring: не показывает лишние кнопки (Gold/Ultimate) и скрывает блок: OK")

        print("\n=== ТЕСТ 2: Cyberpunk 2077 (id 23) - Динамические кнопки Standard и Ultimate ===")
        page.goto("http://localhost:8080/game/23", wait_until="networkidle")
        page.wait_for_timeout(1000)

        title = page.locator("#gameTitle").inner_text()
        print(f"Открыта игра: {title}")
        assert "Cyberpunk" in title, f"Ожидался Cyberpunk, получили {title}"

        # In Cyberpunk, there are Standard and Ultimate editions -> wrapper should be visible!
        is_hidden = "hidden" in (edition_wrapper.get_attribute("class") or "")
        print(f"Cyberpunk: фильтр изданий скрыт: {is_hidden} (должен быть False)")
        assert not is_hidden, "Для Cyberpunk фильтр изданий должен быть виден!"

        # Check buttons in editionButtons
        btn_texts = page.locator("#editionButtons .edition-btn").all_inner_texts()
        print(f"Кнопки изданий Cyberpunk: {btn_texts}")
        assert any("Standard" in t for t in btn_texts), "Должна быть кнопка Standard"
        assert any("Ultimate" in t for t in btn_texts), "Должна быть кнопка Ultimate"
        assert not any("Gold" in t for t in btn_texts), "НЕ должно быть кнопки Gold для Cyberpunk!"
        assert not any("Deluxe" in t for t in btn_texts), "НЕ должно быть кнопки Deluxe для Cyberpunk!"

        # Click Ultimate button
        ultimate_btn = page.locator("#editionButtons .edition-btn:has-text('Ultimate')")
        ultimate_btn.click()
        page.wait_for_timeout(400)

        filtered_cards = page.locator("#offersList .offer-card")
        count = filtered_cards.count()
        print(f"Предложений Ultimate для Cyberpunk: {count}")
        assert count > 0, "Должны отображаться предложения Ultimate"
        for i in range(count):
            card_text = filtered_cards.nth(i).inner_text()
            assert "Ultimate" in card_text, f"Карточка должна содержать Ultimate: {card_text[:60]}"

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "edition_02_cyberpunk_ultimate.png"))
        checks.append("Cyberpunk: показаны только существующие издания (Standard, Ultimate), фильтрация работает: OK")

        print("\n=== ТЕСТ 3: The Witcher 3 (id 26) - Динамические кнопки Standard и Complete ===")
        page.goto("http://localhost:8080/game/26", wait_until="networkidle")
        page.wait_for_timeout(1000)

        title = page.locator("#gameTitle").inner_text()
        print(f"Открыта игра: {title}")

        btn_texts_w3 = page.locator("#editionButtons .edition-btn").all_inner_texts()
        print(f"Кнопки изданий Witcher 3: {btn_texts_w3}")
        assert any("Complete" in t for t in btn_texts_w3), "Должна быть кнопка Complete для Witcher 3"
        assert not any("Gold" in t for t in btn_texts_w3), "НЕ должно быть кнопки Gold для Witcher 3"
        assert not any("Ultimate" in t for t in btn_texts_w3), "НЕ должно быть кнопки Ultimate для Witcher 3"

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "edition_03_witcher_complete.png"))
        checks.append("Witcher 3: показано издание Complete (без Gold и Ultimate): OK")

        browser.close()

    print("\n" + "="*50)
    print("ИТОГИ ПРОВЕРКИ ДИНАМИЧЕСКИХ ИЗДАНИЙ:")
    for chk in checks:
        print("  ✓", chk)

if __name__ == "__main__":
    test_dynamic_editions()
