import time
from playwright.sync_api import sync_playwright

def test_pwa_and_wishlist():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("\n--- [TEST 1] PWA MANIFEST & ICONS ---")
        page.goto("http://localhost:8080/manifest.json")
        manifest_text = page.locator("body").inner_text()
        assert "LootoZavr" in manifest_text, "Manifest should contain LootoZavr"
        print("PASS: /manifest.json served successfully.")

        page.goto("http://localhost:8080/sw.js")
        sw_text = page.locator("body").inner_text()
        assert "lootozavr" in sw_text.lower(), "sw.js should contain service worker logic"
        print("PASS: /sw.js served successfully.")

        print("\n--- [TEST 2] HOMEPAGE & SKELETONS & TMA SCRIPT ---")
        page.goto("http://localhost:8080/", wait_until="networkidle")
        time.sleep(1.5)

        # Check PWA manifest link in head
        manifest_link = page.locator("link[rel='manifest']")
        assert manifest_link.count() == 1, "Expected <link rel='manifest'>"
        print("PASS: Manifest link present in head.")

        # Check Telegram script in head
        tg_script = page.locator("script[src*='telegram-web-app.js']")
        assert tg_script.count() == 1, "Expected Telegram WebApp SDK"
        print("PASS: Telegram WebApp SDK present in head.")

        # Check Wishlist Tab
        wishlist_tab = page.locator("button[data-tab='wishlist']")
        assert wishlist_tab.is_visible(), "Wishlist tab must be visible"
        print("PASS: Wishlist tab exists in Discovery Hub.")

        print("\n--- [TEST 3] EMPTY WISHLIST STATE ---")
        wishlist_tab.click()
        time.sleep(0.5)
        grid_text = page.locator("#discoveryGrid").inner_text()
        assert "Ваш список избранного пуст" in grid_text, "Expected empty state message"
        print("PASS: Empty wishlist state verified.")

        print("\n--- [TEST 4] ADDING GAME TO WISHLIST VIA HEART BUTTON ---")
        # Switch back to 'new' tab
        page.locator("button[data-tab='new']").click()
        time.sleep(1)

        # Find first card and its heart button
        first_card = page.locator(".game-card").first
        first_card_title = first_card.locator("p").first.inner_text()
        heart_btn = first_card.locator(".wishlist-btn").first

        print(f"Adding '{first_card_title}' to wishlist...")
        heart_btn.click()
        time.sleep(0.5)

        # Verify toast
        toast_msg = page.locator("#toastMsg").inner_text()
        assert "добавлена в избранное" in toast_msg or "❤️" in toast_msg, f"Unexpected toast: {toast_msg}"
        print(f"PASS: Toast confirmed: '{toast_msg}'")

        # Verify heart styling turned rose-500
        btn_class = heart_btn.get_attribute("class")
        assert "text-rose-500" in btn_class, "Heart button should be highlighted rose-500"

        # Check counter badge
        badge = page.locator("#wishlistCountBadge")
        assert badge.is_visible() and badge.inner_text() == "1", f"Badge should show 1, got {badge.inner_text()}"
        print("PASS: Wishlist badge shows 1.")

        print("\n--- [TEST 5] WISHLIST TAB RENDERING ---")
        wishlist_tab.click()
        time.sleep(0.5)
        wishlist_cards = page.locator("#discoveryGrid .game-card")
        assert wishlist_cards.count() == 1, f"Expected 1 game card in wishlist, found {wishlist_cards.count()}"
        wishlist_card_title = wishlist_cards.first.locator("p").first.inner_text()
        assert wishlist_card_title == first_card_title, f"Expected {first_card_title}, got {wishlist_card_title}"
        print(f"PASS: Wishlist tab successfully displays '{wishlist_card_title}'.")

        print("\n--- [TEST 6] GAME DETAIL VIEW WISHLIST BUTTON & SHARING ---")
        # Click on the card to open game detail
        wishlist_cards.first.click()
        page.wait_for_selector("#detailWishlistBtn", state="visible", timeout=15000)

        # Verify detail wishlist button says 'В избранном'
        detail_wish_btn = page.locator("#detailWishlistBtn")
        assert detail_wish_btn.is_visible(), "Detail wishlist button must be visible"
        detail_wish_text = page.locator("#detailWishlistText").inner_text()
        assert "В избранном" in detail_wish_text, f"Expected 'В избранном', got '{detail_wish_text}'"
        print("PASS: Game detail page reflects wishlist status ('В избранном').")

        # Wait for previous toast to hide
        time.sleep(3.0)

        # Test share button
        share_btn = page.locator("#shareGameBtn")
        assert share_btn.is_visible(), "Share button must be visible"
        share_btn.click()
        time.sleep(1.0)
        toast_after_share = page.locator("#toastMsg").inner_text()
        assert "скопирована" in toast_after_share or "Ссылка" in toast_after_share, f"Unexpected toast: {toast_after_share}"
        print("PASS: Share button executed successfully.")

        # Toggle wishlist off from detail page
        detail_wish_btn.click()
        time.sleep(0.5)
        detail_wish_text_after = page.locator("#detailWishlistText").inner_text()
        assert "В избранное" in detail_wish_text_after, f"Expected 'В избранное', got '{detail_wish_text_after}'"
        print("PASS: Removed from wishlist via detail page toggle.")

        # Check badge is now hidden
        assert not badge.is_visible(), "Badge should be hidden when wishlist is empty"
        print("PASS: Wishlist badge correctly hidden when empty.")

        filtered_errors = [e for e in console_errors if "favicon" not in e and "net::ERR_" not in e]
        assert len(filtered_errors) == 0, f"Unexpected console errors: {filtered_errors}"
        print("PASS: Zero console errors.")

        browser.close()
        print("\n============================================================")
        print("🎉 ALL PWA & WISHLIST & TMA TESTS PASSED WITH 100% SUCCESS!")
        print("============================================================")

if __name__ == "__main__":
    test_pwa_and_wishlist()
