import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8080/topup", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 1. Services grid
        await page.evaluate("window.scrollTo(0, 600)")
        await page.wait_for_timeout(600)
        await page.screenshot(path="topup_grid_preview.png")

        # 2. Hidden fees & lifehacks
        await page.evaluate("window.scrollTo(0, 2400)")
        await page.wait_for_timeout(600)
        await page.screenshot(path="topup_lifehacks_preview.png")

        # 3. FAQ
        await page.evaluate("window.scrollTo(0, 4800)")
        await page.wait_for_timeout(600)
        await page.screenshot(path="topup_faq_preview.png")

        print("Captured all section screenshots")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
