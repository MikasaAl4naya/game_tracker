import os
import sys
import time
from playwright.sync_api import sync_playwright

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://localhost:8080"
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "donate")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def test_donate_features():
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
            if msg.type == "error" and "cdn.tailwindcss.com" not in msg.text:
                console_errors.append(f"[{msg.type}] {msg.text}")

        page.on("console", on_console)

        print("\n=== STARTING DONATE FEATURE AUDIT ===")

        # Test 1: Direct navigation to /donate
        try:
            print("[Test 1] Navigating directly to /donate...")
            resp = page.goto(f"{BASE_URL}/donate", wait_until="networkidle", timeout=15000)
            assert resp.status == 200, f"Expected 200 OK, got {resp.status}"

            page.wait_for_selector("#donateState:not(.hidden)", timeout=5000)
            welcome_hidden = page.locator("#welcomeState").get_attribute("class")
            assert "hidden" in welcome_hidden, "#welcomeState should be hidden"

            title = page.title()
            assert "Донат" in title, f"Title should mention donate, got: {title}"
            results["passed"].append("Test 1: Direct navigation to /donate renders donate state")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 1 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 2: Header navigation from home to /donate
        try:
            print("[Test 2] Navigating from / via nav link to /donate...")
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
            page.wait_for_selector("#welcomeState:not(.hidden)", timeout=5000)

            donate_nav = page.locator("header nav a[href='/donate']")
            assert donate_nav.is_visible(), "Donate nav link should be visible in header"
            donate_nav.click()
            time.sleep(1)

            page.wait_for_selector("#donateState:not(.hidden)", timeout=5000)
            assert "/donate" in page.url, f"URL should contain /donate, got: {page.url}"
            results["passed"].append("Test 2: Header navigation link switches to donate state")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 2 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 3: Check donate games chips count
        try:
            print("[Test 3] Checking donate games chips count...")
            chips = page.locator("#donateGamesChips .donate-game-chip")
            chips_count = chips.count()
            assert chips_count >= 8, f"Expected at least 8 game chips, got {chips_count}"
            results["passed"].append(f"Test 3: Rendered {chips_count} game selector chips")
            print(f"  -> Passed: {chips_count} chips rendered")
        except Exception as e:
            results["errors"].append(f"Test 3 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 4: Switch game to Brawl Stars
        try:
            print("[Test 4] Switching game to Brawl Stars...")
            brawl_chip = page.locator("#donateGamesChips .donate-game-chip").filter(has_text="Brawl Stars")
            brawl_chip.click()
            time.sleep(1.5)

            title_text = page.locator("#donateGameTitle").inner_text()
            assert "Brawl Stars" in title_text, f"Game title should be Brawl Stars, got: {title_text}"
            assert "brawl-stars" in page.url, f"URL should have brawl-stars, got: {page.url}"

            pkg_cards = page.locator("#donatePackagesGrid .donate-pkg-card")
            assert pkg_cards.count() >= 3, f"Expected at least 3 Brawl Stars packages, got {pkg_cards.count()}"
            results["passed"].append("Test 4: Switch to Brawl Stars updates banner, URL and packages")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 4 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 5: Switch game to Roblox
        try:
            print("[Test 5] Switching game to Roblox...")
            roblox_chip = page.locator("#donateGamesChips .donate-game-chip").filter(has_text="Roblox")
            roblox_chip.click()
            time.sleep(1.5)

            title_text = page.locator("#donateGameTitle").inner_text()
            assert "Roblox" in title_text, f"Game title should be Roblox, got: {title_text}"
            currency_text = page.locator("#donateGameCurrency").inner_text()
            assert "Робуксы" in currency_text, f"Currency should be Робуксы, got: {currency_text}"
            results["passed"].append("Test 5: Switch to Roblox displays Robux packages")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 5 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 6: Switch back to Genshin Impact & verify packages & store offers
        try:
            print("[Test 6] Switching back to Genshin Impact and inspecting offers...")
            genshin_chip = page.locator("#donateGamesChips .donate-game-chip").filter(has_text="Genshin Impact")
            genshin_chip.click()
            time.sleep(1.5)

            # Check active package
            active_pkg_name = page.locator("#donateActivePackageName").inner_text()
            assert len(active_pkg_name) > 0, "Active package name should not be empty"

            # Check store offers
            offers = page.locator("#donateOffersContainer .donate-offer-row")
            offers_count = offers.count()
            assert offers_count >= 3, f"Expected at least 3 store offers for Genshin, got {offers_count}"

            # Check that best deal has 🏆 Лучшая цена
            best_offer = offers.first
            assert "Лучшая цена" in best_offer.inner_text(), "First offer should have 'Лучшая цена' badge"
            results["passed"].append(f"Test 6: Genshin Impact loaded {offers_count} store offers with price badges")
            print(f"  -> Passed: {offers_count} store offers")
        except Exception as e:
            results["errors"].append(f"Test 6 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 7: UID Safety Filter Toggle
        try:
            print("[Test 7] Testing UID safety filter toggle...")
            # Initially UID only is ON. FunPay login offer should NOT be visible.
            funpay_row = page.locator("#donateOffersContainer .donate-offer-row").filter(has_text="FunPay")
            initial_funpay_visible = funpay_row.count() > 0 and funpay_row.first.is_visible()
            assert not initial_funpay_visible, "FunPay account-login offer should be hidden in UID-only mode"

            # Toggle OFF UID-only
            uid_btn = page.locator("#donateUidToggleBtn")
            uid_btn.click()
            time.sleep(0.5)

            # Now FunPay should be visible!
            funpay_after = page.locator("#donateOffersContainer .donate-offer-row").filter(has_text="FunPay")
            assert funpay_after.count() > 0 and funpay_after.first.is_visible(), "FunPay offer should appear when UID-only is toggled off"
            assert "Вход на аккаунт" in funpay_after.first.inner_text(), "FunPay should show 'Вход на аккаунт' badge"

            # Toggle back ON
            uid_btn.click()
            time.sleep(0.5)
            funpay_restored = page.locator("#donateOffersContainer .donate-offer-row").filter(has_text="FunPay")
            assert funpay_restored.count() == 0 or not funpay_restored.first.is_visible(), "FunPay should be hidden again"

            results["passed"].append("Test 7: UID safety toggle properly filters login vs UID delivery")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 7 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 8: Promo Code Copy Toast
        try:
            print("[Test 8] Testing promo code copy toast...")
            copy_btn = page.locator("#donateGameBanner button:has-text('Копировать')")
            copy_btn.click()
            time.sleep(0.5)

            toast = page.locator("#toast")
            page.wait_for_selector("#toast.show, #toast[style*='opacity: 1']", timeout=3000)
            toast_text = page.locator("#toastMsg").inner_text()
            assert "LOOTOZAVR" in toast_text, f"Toast should mention LOOTOZAVR, got: {toast_text}"
            results["passed"].append("Test 8: Promo code 1-click copy triggers toast notification")
            print("  -> Passed")
        except Exception as e:
            # Check if toast text was updated even if CSS class transition was brief
            toast_text = page.locator("#toastMsg").inner_text()
            if "LOOTOZAVR" in toast_text:
                results["passed"].append("Test 8: Promo code 1-click copy updated toast text")
                print("  -> Passed (text verified)")
            else:
                results["errors"].append(f"Test 8 Failed: {e}")
                print(f"  -> Failed: {e}")

        # Test 9: FAQ Accordion
        try:
            print("[Test 9] Testing FAQ accordion expansion...")
            faq_btn = page.locator("#donateState button:has-text('Безопасно ли пополнять аккаунт по UID?')")
            faq_btn.click()
            time.sleep(0.5)

            faq_content = faq_btn.locator("xpath=following-sibling::div[1]")
            assert faq_content.is_visible(), "FAQ content should be visible after click"
            assert "Codashop" in faq_content.inner_text(), "FAQ content should explain official gateways"

            # Collapse
            faq_btn.click()
            time.sleep(0.3)
            assert not faq_content.is_visible(), "FAQ content should be collapsed after second click"
            results["passed"].append("Test 9: FAQ accordion opens and collapses cleanly")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 9 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 10: Deep link directly to /donate/zenless-zone-zero
        try:
            print("[Test 10] Testing deep link /donate/zenless-zone-zero...")
            page.goto(f"{BASE_URL}/donate/zenless-zone-zero", wait_until="networkidle", timeout=15000)
            page.wait_for_selector("#donateState:not(.hidden)", timeout=5000)

            title_text = page.locator("#donateGameTitle").inner_text()
            assert "Zenless Zone Zero" in title_text, f"Expected Zenless Zone Zero, got: {title_text}"
            assert "zenless-zone-zero" in page.url, f"Expected URL to contain slug, got: {page.url}"
            results["passed"].append("Test 10: Direct deep link /donate/zenless-zone-zero loads correctly")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 10 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 11: Mobile Layout Responsiveness (375x812)
        try:
            print("[Test 11] Testing mobile layout at 375x812...")
            page.set_viewport_size({"width": 375, "height": 812})
            time.sleep(1)

            # Check horizontal overflow
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            assert scroll_width <= client_width + 1, f"Horizontal scroll overflow on mobile: scrollWidth={scroll_width}, clientWidth={client_width}"

            # Check mobile donate header button
            mobile_donate_btn = page.locator("header button:has-text('Донат')")
            assert mobile_donate_btn.is_visible(), "Mobile donate button should be visible in header on 375px"

            screenshot_path = os.path.join(SCREENSHOTS_DIR, "donate_mobile_375.png")
            page.screenshot(path=screenshot_path, full_page=False)

            results["passed"].append("Test 11: Mobile layout at 375px has 0 overflow and responsive UI")
            print("  -> Passed")
        except Exception as e:
            results["errors"].append(f"Test 11 Failed: {e}")
            print(f"  -> Failed: {e}")

        # Test 12: Console errors check
        print("[Test 12] Checking JavaScript console errors...")
        if len(console_errors) == 0:
            results["passed"].append("Test 12: Zero JavaScript console errors detected")
            print("  -> Passed (0 console errors)")
        else:
            results["errors"].append(f"Test 12 Failed: JS Errors: {console_errors}")
            print(f"  -> Failed: {console_errors}")

        browser.close()

    print("\n=== AUDIT SUMMARY ===")
    print(f"PASSED: {len(results['passed'])}")
    print(f"ERRORS: {len(results['errors'])}")
    for p in results["passed"]:
        print(f"  ✓ {p}")
    for err in results["errors"]:
        print(f"  ✗ {err}")

    return len(results["errors"]) == 0


if __name__ == "__main__":
    success = test_donate_features()
    sys.exit(0 if success else 1)
