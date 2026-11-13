import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8080/topup", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Scroll to Hidden Fees section
        hidden_fees_el = await page.query_selector("h2:has-text('Скрытые комиссии банков')")
        if hidden_fees_el:
            await hidden_fees_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await page.screenshot(path="topup_hidden_fees_preview.png")
            print("Captured hidden fees")

        # Scroll to 7 Lifehacks
        lifehacks_el = await page.query_selector("h2:has-text('7 проверенных способов')")
        if lifehacks_el:
            await lifehacks_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await page.screenshot(path="topup_7lifehacks_preview.png")
            print("Captured 7 lifehacks")

        # Scroll to FAQ
        faq_el = await page.query_selector("h2:has-text('Гайд по безопасности')")
        if faq_el:
            await faq_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await page.screenshot(path="topup_faq_scroll_preview.png")
            print("Captured FAQ")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
