from playwright.sync_api import sync_playwright
import time

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()

        print("=== 1. Checking /donate with new games ===")
        page.goto("http://localhost:8080/donate", wait_until="networkidle")
        time.sleep(1)

        chips = page.locator("#donateGamesChips .donate-game-chip")
        count = chips.count()
        print(f"Total donate game chips: {count} (expected 13)")
        assert count >= 13, f"Expected at least 13 chips, got {count}"

        # Test Wuthering Waves
        wuwa_chip = page.locator("#donateGamesChips .donate-game-chip:has-text('Wuthering Waves')")
        assert wuwa_chip.count() > 0, "Wuthering Waves chip not found"
        wuwa_chip.click()
        time.sleep(0.5)

        title = page.locator("#donateGameTitle").inner_text()
        print(f"Selected game title: {title}")
        assert "Wuthering Waves" in title

        pkg_cards = page.locator(".donate-pkg-card")
        print(f"WuWa packages count: {pkg_cards.count()}")
        assert pkg_cards.count() >= 5

        # Check price visibility on WuWa
        first_pkg_price = page.locator(".donate-pkg-card span.text-deal").first.inner_text()
        print(f"WuWa first package price: {first_pkg_price}")
        assert "₽" in first_pkg_price

        # Click first package to see offers
        pkg_cards.first.click()
        time.sleep(0.5)
        offers = page.locator("#donateOffersContainer > div")
        print(f"WuWa offers count: {offers.count()}")
        assert offers.count() >= 3

        # Test Standoff 2
        print("=== 2. Checking Standoff 2 ===")
        so2_chip = page.locator("#donateGamesChips .donate-game-chip:has-text('Standoff 2')")
        so2_chip.click()
        time.sleep(0.5)
        so2_title = page.locator("#donateGameTitle").inner_text()
        print(f"Selected game: {so2_title}")
        assert "Standoff 2" in so2_title

        # Test Marvel Rivals
        print("=== 3. Checking Marvel Rivals ===")
        mr_chip = page.locator("#donateGamesChips .donate-game-chip:has-text('Marvel Rivals')")
        mr_chip.click()
        time.sleep(0.5)
        mr_title = page.locator("#donateGameTitle").inner_text()
        print(f"Selected game: {mr_title}")
        assert "Marvel Rivals" in mr_title

        # Test Steam Topup
        print("=== 4. Checking /topup with BattlePass and PayBerry ===")
        page.goto("http://localhost:8080/topup", wait_until="networkidle")
        time.sleep(1)

        bp_card = page.locator(".topup-service-card:has-text('BattlePass')")
        print("BattlePass in topup count:", bp_card.count())
        assert bp_card.count() > 0, "BattlePass not found in topup"

        payberry_card = page.locator(".topup-service-card:has-text('PayBerry')")
        print("PayBerry in topup count:", payberry_card.count())
        assert payberry_card.count() > 0, "PayBerry not found in topup"

        # Test Footer Keysforgamers link
        print("=== 5. Checking Footer Keysforgamers link ===")
        kfg_link = page.locator("footer a[href*='keysforgamers.com']")
        print("Keysforgamers footer link count:", kfg_link.count())
        assert kfg_link.count() > 0, "Keysforgamers link not found in footer"

        print("=== ALL 5 VERIFICATION CHECKS PASSED SUCCESSFULLY! ===")
        browser.close()

if __name__ == "__main__":
    run_tests()
