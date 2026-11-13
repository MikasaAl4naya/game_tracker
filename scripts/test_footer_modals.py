import sys
import time
from playwright.sync_api import sync_playwright

def test_footer_modals_and_links():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        print("Navigating to http://localhost:8080...")
        page.goto("http://localhost:8080", wait_until="networkidle")
        time.sleep(1)
        
        # Test 1: Verify Telegram and GitHub and API links
        print("Checking header & footer external links...")
        tg_links = page.locator("a[href='https://t.me/LootoZavr_bot']")
        assert tg_links.count() >= 2, f"Expected at least 2 Telegram links, found {tg_links.count()}"
        print(f"PASS: Found {tg_links.count()} Telegram links.")
        
        gh_links = page.locator("a[href='https://github.com/MikasaAl4naya/game_tracker']")
        assert gh_links.count() >= 1, "Expected GitHub link in footer"
        print("PASS: GitHub link verified.")
        
        api_link = page.locator("a[href='/docs']")
        assert api_link.count() >= 1, "Expected /docs link in footer"
        print("PASS: API /docs link verified.")
        
        # Test 2: Click 'Политика конфиденциальности' and check modal
        print("Testing Privacy Policy modal...")
        page.locator("a:has-text('Политика конфиденциальности')").first.click()
        time.sleep(0.5)
        
        modal = page.locator("#infoModal")
        assert modal.is_visible(), "infoModal should be visible after clicking Privacy Policy"
        title = page.locator("#infoModalTitle").inner_text()
        assert "Политика конфиденциальности" in title, f"Unexpected title: {title}"
        body = page.locator("#infoModalBody").inner_text()
        assert "152-ФЗ" in body, "Expected 152-ФЗ in body"
        print("PASS: Privacy Policy modal opened and verified.")
        
        # Close via Escape
        page.keyboard.press("Escape")
        time.sleep(0.3)
        assert not modal.is_visible(), "infoModal should be hidden after pressing Escape"
        print("PASS: Modal closed via Escape key.")
        
        # Test 3: Click 'Регионы и цены'
        print("Testing Regions modal...")
        page.locator("a:has-text('Регионы и цены')").first.click()
        time.sleep(0.5)
        assert modal.is_visible(), "infoModal should be visible after clicking Regions"
        title = page.locator("#infoModalTitle").inner_text()
        assert "Регионы" in title, f"Unexpected title: {title}"
        body = page.locator("#infoModalBody").inner_text()
        assert "CIS" in body and "Global" in body, "Expected region details"
        print("PASS: Regions modal opened and verified.")
        
        # Close via close button
        page.locator("#infoModal button:has-text('Понятно')").click()
        time.sleep(0.3)
        assert not modal.is_visible(), "infoModal should be hidden after clicking Понятно"
        print("PASS: Modal closed via Понятно button.")
        
        # Test 4: Click 'Сообщить об ошибке'
        print("Testing Bug Report modal...")
        page.locator("a:has-text('Сообщить об ошибке')").first.click()
        time.sleep(0.5)
        assert modal.is_visible(), "infoModal should be visible"
        title = page.locator("#infoModalTitle").inner_text()
        assert "Сообщить об ошибке" in title, f"Unexpected title: {title}"
        print("PASS: Bug Report modal verified.")
        
        page.keyboard.press("Escape")
        time.sleep(0.3)
        
        # Test 5: Back to top button visibility on scroll
        print("Testing Back to top button...")
        back_btn = page.locator("#backToTopBtn")
        # Scroll down
        page.evaluate("window.scrollTo(0, 1000)")
        time.sleep(0.5)
        # Check that opacity-100 class is added
        btn_class = back_btn.get_attribute("class")
        assert "opacity-100" in btn_class, f"Expected opacity-100 on scroll, got: {btn_class}"
        
        # Click back to top
        back_btn.click()
        time.sleep(0.5)
        scroll_y = page.evaluate("window.scrollY")
        assert scroll_y < 100, f"Expected page to scroll to top, scrollY is {scroll_y}"
        print(f"PASS: Back to top button scrolled to {scroll_y}px.")
        
        # Verify no severe console errors
        filtered_errors = [e for e in console_errors if "favicon" not in e and "net::ERR_" not in e]
        assert len(filtered_errors) == 0, f"Unexpected console errors: {filtered_errors}"
        print("PASS: No console errors encountered.")
        
        browser.close()
        print("\nAll footer & modal tests passed successfully!")

if __name__ == "__main__":
    test_footer_modals_and_links()
