import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def test_features():
    console_errors = []
    checks = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: console_errors.append(f"[pageerror] {err}"))

        print("\n=== ТЕСТ 1: Hero РФ-доступность и карточка игры (Cyberpunk 2077) ===")
        page.goto("http://localhost:8080", wait_until="networkidle")
        page.wait_for_timeout(500)

        # Search for Cyberpunk 2077
        search_input = page.locator("#searchInput")
        search_input.fill("Cyberpunk 2077")
        page.wait_for_timeout(800)

        # Click suggestion or press Enter
        first_sugg = page.locator("#searchSuggestions > div").first
        if first_sugg.is_visible():
            first_sugg.click()
        else:
            search_input.press("Enter")

        page.wait_for_timeout(2500)

        # Verify Hero RF Availability Badge
        rf_badge = page.locator("#heroRfAvailability")
        assert rf_badge.is_visible(), "heroRfAvailability badge should be visible for Cyberpunk 2077"
        badge_text = rf_badge.inner_text().strip()
        badge_title = rf_badge.get_attribute("title")
        print(f"RF Badge text: {badge_text}")
        print(f"RF Badge tooltip: {badge_title}")
        assert "Недоступно в Steam РФ" in badge_text, f"Expected 'Недоступно в Steam РФ' in {badge_text}"
        checks.append("Feature 1 (Hero RF Availability Badge): OK")

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat1_hero_rf_badge.png"))

        print("\n=== ТЕСТ 2: Быстрые фильтры формата (Все / Ключи / Гифты) и Сортировка ===")
        # Verify format pills
        pills = page.locator(".format-pill")
        assert pills.count() == 3, f"Expected 3 format pills, got {pills.count()}"

        # Count total offers
        cards = page.locator("#offersList .offer-card")
        total_count = cards.count()
        print(f"Всего предложений: {total_count}")

        # Click "Гифты"
        page.locator(".format-pill[data-format='gift']").click()
        page.wait_for_timeout(500)
        gift_cards = page.locator("#offersList .offer-card")
        gift_count = gift_cards.count()
        print(f"После фильтра 'Гифты': {gift_count} предложений")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat2_filter_gifts.png"))

        # Click "Ключи"
        page.locator(".format-pill[data-format='key']").click()
        page.wait_for_timeout(500)
        key_cards = page.locator("#offersList .offer-card")
        key_count = key_cards.count()
        print(f"После фильтра 'Ключи': {key_count} предложений")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat2_filter_keys.png"))

        # Return to "Все"
        page.locator(".format-pill[data-format='All']").click()
        page.wait_for_timeout(500)

        # Test Sorting Dropdown
        sort_select = page.locator("#sortOrderSelect")
        assert sort_select.is_visible(), "sortOrderSelect should be visible"

        # Select price_desc (Сначала дороже)
        sort_select.select_option("price_desc")
        page.wait_for_timeout(500)
        def parse_price(txt):
            cleaned = txt.replace('\xa0', '').replace(' ', '').replace('₽', '').replace(',', '.').strip()
            return float(cleaned) if cleaned else 0.0

        prices_desc = [parse_price(p.inner_text()) for p in page.locator("#offersList .price-num").all() if p.inner_text().strip()]
        print(f"Цены по убыванию (первые 5): {prices_desc[:5]}")
        if len(prices_desc) >= 2:
            assert prices_desc[0] >= prices_desc[-1], f"Prices should be in descending order: first={prices_desc[0]}, last={prices_desc[-1]}"
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat2_sort_price_desc.png"))

        # Select price_asc (Сначала дешевле)
        sort_select.select_option("price_asc")
        page.wait_for_timeout(500)
        prices_asc = [parse_price(p.inner_text()) for p in page.locator("#offersList .price-num").all() if p.inner_text().strip()]
        print(f"Цены по возрастанию (первые 5): {prices_asc[:5]}")
        if len(prices_asc) >= 2:
            assert prices_asc[0] <= prices_asc[-1], f"Prices should be in ascending order: first={prices_asc[0]}, last={prices_asc[-1]}"

        checks.append("Feature 2 (Format Quick Pills & Sort Dropdown): OK")

        print("\n=== ТЕСТ 3: Telegram 1-click Deeplink в модалке отслеживания ===")
        # Open track modal
        page.locator("button:has-text('Отслеживать цену')").first.click()
        page.wait_for_timeout(500)

        track_modal = page.locator("#trackModal")
        assert track_modal.is_visible(), "trackModal should be visible"

        deeplink_btn = page.locator("#trackTelegram1Click")
        assert deeplink_btn.is_visible(), "trackTelegram1Click should be visible"
        href1 = deeplink_btn.get_attribute("href")
        print(f"Telegram 1-click href (начальный): {href1}")
        assert "t.me/LootoZavr_bot?start=track_" in href1, f"Expected deep link, got {href1}"

        # Change target price and verify href updates dynamically
        price_input = page.locator("#trackTargetPrice")
        price_input.fill("1234")
        page.wait_for_timeout(300)
        href2 = deeplink_btn.get_attribute("href")
        print(f"Telegram 1-click href (после изменения цены на 1234): {href2}")
        assert "1234" in href2, f"Expected 1234 in deep link, got {href2}"

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat3_track_modal_1click.png"))

        # Close modal
        page.locator("#trackModal button i.fa-xmark").click()
        page.wait_for_timeout(300)
        checks.append("Feature 3 (Telegram 1-Click Deeplink): OK")

        print("\n=== ТЕСТ 4: Фильтрация и бейджи изданий (Динамические издания для Cyberpunk) ===")
        edition_btns = page.locator(".edition-btn")
        btn_count = edition_btns.count()
        print(f"Динамических кнопок изданий для Cyberpunk: {btn_count} ({edition_btns.all_inner_texts()})")
        assert btn_count >= 2, f"Expected at least 2 edition buttons, got {btn_count}"

        # Click Ultimate
        page.locator(".edition-btn[data-val='ultimate']").click()
        page.wait_for_timeout(500)
        ult_cards = page.locator("#offersList .offer-card")
        print(f"Карточек Ultimate: {ult_cards.count()}")
        assert ult_cards.count() > 0, "Ожидались карточки Ultimate"
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat4_edition_ultimate.png"))

        # Click All
        page.locator(".edition-btn[data-val='All']").click()
        page.wait_for_timeout(500)

        # Check edition badges on cards in all offers
        badge_ult = page.locator("#offersList .badge-ultimate")
        print(f"Бейджей Ultimate найдено на карточках: {badge_ult.count()}")
        assert badge_ult.count() > 0, "Ожидались бейджи Ultimate на карточках"
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "feat4_edition_badges.png"))

        checks.append("Feature 4 (Dynamic Edition Filter & Badges): OK")

        browser.close()

    print("\n" + "="*50)
    print("ИТОГИ ПРОВЕРКИ:")
    for chk in checks:
        print("  ✓", chk)

    if console_errors:
        print("\nОшибки консоли браузера:")
        for err in console_errors:
            print("  !", err)
    else:
        print("\nКонсоль браузера: ошибок нет!")

if __name__ == "__main__":
    test_features()
