from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page()
    page.goto("http://localhost:8080/game/8", wait_until="networkidle")
    time.sleep(2)

    title = page.locator("#heroGameTitle").inner_text()
    deal_price = page.locator("#heroDealPrice").inner_text()
    discount = page.locator("#heroDealDiscount").inner_text()
    shop = page.locator("#heroDealShop").inner_text()
    lot = page.locator("#heroDealLotName").inner_text()
    print(f"Title: {title}")
    print(f"Hero Deal Price: {deal_price}")
    print(f"Discount: {discount}")
    print(f"Shop: {shop}")
    print(f"Lot: {lot}")

    offers = page.evaluate("""() => {
        const cards = Array.from(document.querySelectorAll('#offersList .offer-card'));
        return cards.map(c => {
            const shop = c.querySelector('[class*="shop-"]')?.innerText?.trim();
            const lot = c.querySelector('.font-bold.text-white')?.innerText?.trim();
            const price = c.querySelector('.font-black')?.innerText?.trim();
            return { shop, lot, price };
        });
    }""")

    print(f"Total offer cards in list: {len(offers)}")
    for o in offers[:6]:
        print(" ", o)

    browser.close()
