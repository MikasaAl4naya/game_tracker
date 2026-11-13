import asyncio
import os
import sys
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "browser_test")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "http://localhost:8080"

async def run_tests():
    print("=" * 60)
    print("🚀 STARTING COMPREHENSIVE BROWSER TEST FOR LOOTOZAVR")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        # -------------------------------------------------------------
        # TEST 1: HOMEPAGE DISCOVERY CARDS & PRICES
        # -------------------------------------------------------------
        print("\n[TEST 1] Checking Homepage (/)...")
        await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # Take homepage screenshot
        home_shot = os.path.join(SCREENSHOTS_DIR, "01_homepage_popular.png")
        await page.screenshot(path=home_shot, full_page=False)
        print(f"  📸 Saved homepage screenshot to {home_shot}")

        # Check title / branding
        title = await page.title()
        print(f"  Page title: {title}")
        assert "LootoZavr" in title, f"Expected LootoZavr in title, got: {title}"

        # Check popular games cards
        cards = await page.locator("#discoveryGrid .group").all()
        print(f"  Found {len(cards)} discovery game cards on 'popular' tab.")
        assert len(cards) > 0, "No discovery cards found!"

        card_prices = {}
        for card in cards[:8]:
            text = await card.inner_text()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            name = lines[1] if len(lines) > 1 else lines[0]
            price_text = [l for l in lines if "₽" in l or "от" in l]
            p_val = price_text[0] if price_text else "N/A"
            card_prices[name] = p_val
            print(f"    • Card: {name} -> {p_val}")

        # Assert no corrupt prices on popular cards
        for name, p_val in card_prices.items():
            if "Elden Ring" in name or "ELDEN RING" in name:
                assert "51" not in p_val, f"Elden Ring has corrupt price 51! Got: {p_val}"
            if "Cyberpunk" in name:
                assert "53" not in p_val, f"Cyberpunk has corrupt price 53! Got: {p_val}"
            if "Hogwarts" in name:
                assert "71" not in p_val, f"Hogwarts Legacy has corrupt price 71! Got: {p_val}"

        # Switch to "Steam" tab
        print("\n  Switching to 'Steam' tab...")
        await page.locator("button", has_text="Бестселлеры Steam").click()
        await page.wait_for_timeout(1000)
        steam_shot = os.path.join(SCREENSHOTS_DIR, "02_homepage_steam.png")
        await page.screenshot(path=steam_shot, full_page=False)
        print(f"  📸 Saved Steam tab screenshot to {steam_shot}")

        steam_cards = await page.locator("#discoveryGrid .group").all()
        print(f"  Found {len(steam_cards)} cards on Steam tab.")
        for sc in steam_cards[:6]:
            txt = await sc.inner_text()
            lines = [l.strip() for l in txt.split("\n") if l.strip()]
            name = lines[1] if len(lines) > 1 else lines[0]
            price_text = [l for l in lines if "₽" in l or "от" in l]
            print(f"    • Steam Card: {name} -> {price_text[0] if price_text else 'N/A'}")

        # -------------------------------------------------------------
        # TEST 2: HOGWARTS LEGACY (/game/25) - REGION & PLATFORM FILTERS
        # -------------------------------------------------------------
        print("\n[TEST 2] Checking Hogwarts Legacy (/game/25)...")
        await page.goto(f"{BASE_URL}/game/25", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # Check total cards with 'All' filters
        all_cards = await page.locator(".offer-card").all()
        print(f"  Initial offer cards with All filters: {len(all_cards)}")
        assert len(all_cards) > 0, "No offer cards found for Hogwarts Legacy!"

        game_shot = os.path.join(SCREENSHOTS_DIR, "03_hogwarts_all_offers.png")
        await page.screenshot(path=game_shot, full_page=False)
        print(f"  📸 Saved Hogwarts Legacy all-offers screenshot to {game_shot}")

        # --- Subtest 2.1: REGION FILTER = RU ---
        print("\n  [2.1] Testing Region Filter: RU...")
        ru_btn = page.locator("button.region-btn[data-val='RU']")
        await ru_btn.click()
        await page.wait_for_timeout(500)

        ru_cards = await page.locator(".offer-card:visible").all()
        print(f"    Visible cards with RU filter: {len(ru_cards)}")
        ru_shot = os.path.join(SCREENSHOTS_DIR, "04_hogwarts_ru_filter.png")
        await page.screenshot(path=ru_shot, full_page=False)
        print(f"    📸 Saved RU filter screenshot to {ru_shot}")

        for i, card in enumerate(ru_cards):
            text = await card.inner_text()
            text_clean = text.replace("\n", " | ")
            print(f"      [{i+1}] {text_clean[:100]}...")
            # STRICT ASSERTIONS: NO negative RF/RU markers allowed!
            assert "кроме рф" not in text.lower(), f"Found 'кроме РФ' in RU filter card: {text}"
            assert "без рф" not in text.lower(), f"Found 'без РФ' in RU filter card: {text}"
            assert "не рф" not in text.lower(), f"Found 'не РФ' in RU filter card: {text}"
            assert "399 ₽" not in text or "СНГ" not in text, f"Found stale 399 CIS lot in RU filter: {text}"

        # --- Subtest 2.2: REGION FILTER = CIS ---
        print("\n  [2.2] Testing Region Filter: CIS...")
        cis_btn = page.locator("button.region-btn[data-val='CIS']")
        await cis_btn.click()
        await page.wait_for_timeout(500)

        cis_cards = await page.locator(".offer-card:visible").all()
        print(f"    Visible cards with CIS filter: {len(cis_cards)}")
        assert len(cis_cards) > 0, "CIS filter should show valid CIS lots!"
        cis_shot = os.path.join(SCREENSHOTS_DIR, "05_hogwarts_cis_filter.png")
        await page.screenshot(path=cis_shot, full_page=False)
        print(f"    📸 Saved CIS filter screenshot to {cis_shot}")

        # Check first CIS card
        first_cis_text = await cis_cards[0].inner_text()
        print(f"    First CIS card: {first_cis_text.replace(chr(10), ' | ')[:120]}...")

        # Reset region filter back to All
        await page.locator("button.region-btn[data-val='All']").click()
        await page.wait_for_timeout(300)

        # --- Subtest 2.3: PLATFORM FILTER = Xbox ---
        print("\n  [2.3] Testing Platform Filter: Xbox...")
        xbox_btn = page.locator("button.platform-btn", has_text="Xbox")
        await xbox_btn.click()
        await page.wait_for_timeout(500)

        xbox_cards = await page.locator(".offer-card:visible").all()
        print(f"    Visible cards with Xbox filter: {len(xbox_cards)}")
        xbox_shot = os.path.join(SCREENSHOTS_DIR, "06_hogwarts_xbox_filter.png")
        await page.screenshot(path=xbox_shot, full_page=False)
        print(f"    📸 Saved Xbox filter screenshot to {xbox_shot}")

        for card in xbox_cards:
            text = await card.inner_text()
            assert "Xbox" in text, f"Card does not belong to Xbox: {text[:60]}"

        # Reset platform filter back to All
        await page.locator("button.platform-btn[data-val='All']").click()
        await page.wait_for_timeout(300)

        # --- Subtest 2.4: FORMAT FILTER = Ключ vs Гифт ---
        print("\n  [2.4] Testing Format Filter: Ключ vs Гифт...")
        key_btn = page.locator(".format-pill[data-format='key']")
        if await key_btn.count() > 0:
            await key_btn.click()
            await page.wait_for_timeout(400)
            key_cards = await page.locator(".offer-card:visible").all()
            print(f"    Visible cards with 'Ключ' format: {len(key_cards)}")

        gift_btn = page.locator(".format-pill[data-format='gift']")
        if await gift_btn.count() > 0:
            await gift_btn.click()
            await page.wait_for_timeout(400)
            gift_cards = await page.locator(".offer-card:visible").all()
            print(f"    Visible cards with 'Гифт' format: {len(gift_cards)}")

        # Reset format filter back to All
        all_fmt = page.locator(".format-pill[data-format='All']")
        if await all_fmt.count() > 0:
            await all_fmt.click()
            await page.wait_for_timeout(300)

        # --- Subtest 2.5: SORT ORDER = Price Ascending vs Descending ---
        print("\n  [2.5] Testing Sort Order...")
        sort_select = page.locator("#sortOrderSelect")
        if await sort_select.count() > 0:
            await sort_select.select_option("price_desc")
            await page.wait_for_timeout(400)
            desc_cards = await page.locator(".offer-card:visible").all()
            desc_first = await desc_cards[0].inner_text()
            print(f"    First offer (price_desc): {desc_first.replace(chr(10), ' | ')[:80]}...")

            await sort_select.select_option("price_asc")
            await page.wait_for_timeout(400)
            asc_cards = await page.locator(".offer-card:visible").all()
            asc_first = await asc_cards[0].inner_text()
            print(f"    First offer (price_asc): {asc_first.replace(chr(10), ' | ')[:80]}...")

        # -------------------------------------------------------------
        # TEST 3: PALWORLD (/game/2) - VERIFY NO 164 RUB CONSOLE ACCOUNTS
        # -------------------------------------------------------------
        print("\n[TEST 3] Checking Palworld (/game/2)...")
        await page.goto(f"{BASE_URL}/game/2", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        pal_cards = await page.locator(".offer-card:visible").all()
        print(f"  Visible offers for Palworld: {len(pal_cards)}")
        pal_shot = os.path.join(SCREENSHOTS_DIR, "07_palworld_offers.png")
        await page.screenshot(path=pal_shot, full_page=False)
        print(f"  📸 Saved Palworld screenshot to {pal_shot}")

        for card in pal_cards:
            text = await card.inner_text()
            # Assert 164.69 console account is gone
            assert "164" not in text, f"Palworld card still shows 164 RUB console account! Card: {text}"
            assert "buy-konsolnyh-akkauntov" not in text, f"Console account URL found in card text: {text}"

        # -------------------------------------------------------------
        # TEST 4: STEAM TOP-UP TAB (/topup)
        # -------------------------------------------------------------
        print("\n[TEST 4] Checking Steam Top-up (/topup)...")
        await page.goto(f"{BASE_URL}/topup", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Check topup calculators and service cards
        service_cards = await page.locator(".topup-service-card, #topupServicesGrid > div").all()
        print(f"  Found {len(service_cards)} top-up service cards.")
        assert len(service_cards) > 0, "No topup service cards found!"

        topup_shot = os.path.join(SCREENSHOTS_DIR, "08_topup_section.png")
        await page.screenshot(path=topup_shot, full_page=False)
        print(f"  📸 Saved Top-up screenshot to {topup_shot}")

        # Test Top-up Region Switch (RU -> KZ -> GLOBAL)
        region_select = page.locator("#topupRegionSelect")
        if await region_select.count() > 0:
            print("    Selecting region: KZ...")
            await region_select.select_option("KZ")
            await page.wait_for_timeout(400)
            kz_cards = await page.locator(".topup-service-card:visible, #topupServicesGrid > div:visible").all()
            print(f"    Visible services for KZ: {len(kz_cards)}")

            print("    Selecting region: RU...")
            await region_select.select_option("RU")
            await page.wait_for_timeout(400)
            ru_cards = await page.locator(".topup-service-card:visible, #topupServicesGrid > div:visible").all()
            print(f"    Visible services for RU: {len(ru_cards)}")

        # -------------------------------------------------------------
        # TEST 5: SEARCH FUNCTIONALITY AUTOCOMPLETE
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing Search Autocomplete...")
        await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        search_input = page.locator("#searchInput")
        await search_input.click()
        await search_input.press_sequentially("Cyberpunk", delay=50)
        
        try:
            await page.wait_for_selector("#searchSuggestions > div", state="visible", timeout=6000)
        except Exception as e:
            print(f"    Warning wait_for_selector: {e}")

        suggestions = page.locator("#searchSuggestions")
        is_visible = await suggestions.is_visible()
        print(f"  Suggestions box visible: {is_visible}")
        assert is_visible, "Suggestions dropdown should be visible when searching!"

        items = await suggestions.locator("> div").all()
        print(f"  Found {len(items)} suggestion items.")
        assert len(items) > 0, "No suggestion items returned for Cyberpunk!"

        first_suggestion_text = await items[0].inner_text()
        print(f"    First suggestion: {first_suggestion_text.replace(chr(10), ' | ')}")
        assert "Cyberpunk" in first_suggestion_text, f"Expected Cyberpunk in suggestion, got: {first_suggestion_text}"

        search_shot = os.path.join(SCREENSHOTS_DIR, "09_search_autocomplete.png")
        await page.screenshot(path=search_shot, full_page=False)
        print(f"  📸 Saved search autocomplete screenshot to {search_shot}")

        await browser.close()

    print("\n" + "=" * 60)
    print("✅ ALL BROWSER TESTS PASSED SUCCESSFULLY WITH 100% ACCURACY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
